"use strict";

interface Step {
    comments: string,
    is_running: boolean,
    name: string,
    steps: [Step] | null,
    time: number,
}

class Job {
    elem: HTMLElement;
    id: string;
    timerFetch: number | null;
    timerUpdate: number | null;
    onSuccess: Function | null;
    onError: Function | null;
    lastEtas: number[];
    data: {
        comments: string,
        eta_ts: string,
        is_running: boolean,
        name: string,
        progress: number,
        remaining: number,
        start_ts: string,
        status: string,
        steps: [Step],
        time: number,
        error: string | undefined,
    } | null;
    progress: number;

    constructor(element: HTMLElement, success: Function | null = null, error: Function | null = null) {
        this.elem = element;
        const id = this.elem.dataset['jobId'];
        const dataStr = this.elem.dataset['job'];
        if (!id) throw new Error();

        if (dataStr) {
            this.data = JSON.parse(dataStr);
        } else {
            this.data = null;
        }

        this.id = id;
        this.onSuccess = success;
        this.onError = error;
        this.lastEtas = [];
        this.progress = 0;

        const container = document.createElement("div");
        container.classList.add('progress-bar');

        const progressBar = document.createElement("div");
        progressBar.style.display = 'none';
        container.appendChild(progressBar);

        const progressStatus = document.createElement("span");
        progressStatus.innerText = '0%';
        container.appendChild(progressStatus);

        this.elem.appendChild(container);

        if (!this.data || (this.data && this.data.status === 'running')) {
            this.fetch().then();
            this.timerFetch = setInterval(() => {
                this.fetch().then();
            }, 500);

            this.update();
            this.timerUpdate = setInterval(() => {
                this.update();
            }, 125);
        } else {
            this.timerFetch = null;
            this.timerUpdate = null;
            this.update();
        }
    }

    async fetch() {
        let job;
        try {
            const json = await api('/tucal/job', {'id': this.id});
            if (json.data) {
                job = json.data;
            } else {
                job = {
                    'status': 'error',
                    'error': json.message,
                }
            }
        } catch (e: any) {
            job = {
                'status': 'error',
                'error': e.message,
            }
        }
        if (job.status !== 'running' && this.timerFetch) {
            clearInterval(this.timerFetch);
        }
        if (job.remaining && this.data) {
            const eta = job.time + job.remaining;
            if (this.lastEtas.length === 0 || job.time !== this.data.time) {
                this.lastEtas.push(eta);
            }
        }
        this.data = job;
        this.update();
    }

    update() {
        const job = this.data;
        if (!job || !job.status) return;

        const container = this.elem.getElementsByClassName("progress-bar")[0];
        if (!container) throw new Error();

        const progressBar = container.getElementsByTagName("div")[0];
        const statusText = container.getElementsByTagName("span")[0];
        if (!progressBar || !statusText) throw new Error();

        const classList = this.elem.classList;
        if (job.status !== 'running' && !classList.contains('error') && !classList.contains('success')) {
            if (job.status !== 'success') {
                classList.add('error');

                const href = this.elem.dataset['errorHref'];
                if (href && this.elem.getElementsByTagName("button").length === 0) {
                    const btn = document.createElement('a');
                    btn.classList.add('button');
                    btn.innerText = _('Back');
                    btn.href = href;
                    this.elem.appendChild(btn);
                }

                if (this.onError !== null) {
                    this.onError();
                }
            } else {
                classList.add('success');

                const href = this.elem.dataset['successHref'];
                if (href && this.elem.getElementsByTagName("button").length === 0) {
                    const btn = document.createElement('a');
                    btn.classList.add('button');
                    btn.innerText = _('Next (step)');
                    btn.href = href;
                    this.elem.appendChild(btn);
                }

                if (this.onSuccess !== null) {
                    this.onSuccess();
                }
            }
        }

        let progress = job.progress || 0;
        const now = new Date();
        now.setSeconds(now.getSeconds() - 1);

        if (job.remaining) {
            const start = new Date(Date.parse(job.start_ts));
            const elapsed = (now.valueOf() - start.valueOf()) / 1000;

            if (this.lastEtas.length > 0) {
                const max = Math.max(...this.lastEtas);
                const average = (this.lastEtas.reduce((a, b) => a + b)) / this.lastEtas.length;
                const conservativeEta = ((this.lastEtas[0] || 0) + max + average) / 3 + 1;
                const progressEstimate = elapsed / conservativeEta;
                if (progressEstimate <= 0.99 && progress < progressEstimate) {
                    progress = progressEstimate;
                }
            }
        }

        if (progress >= 1 || job.status === 'success') progress = 1;
        if (job.status !== 'running' && this.timerUpdate) clearInterval(this.timerUpdate);

        if (progress >= this.progress) {
            this.progress = progress;
        } else {
            const diff = this.progress - progress;
            if (diff > 0.0625) {
                console.warn(`Real progress at ${(progress * 100).toFixed(0)}%, but displaying ${(this.progress * 100).toFixed(0)}% - Diff: ${(diff * 100).toFixed(0)}`);
            }
            if (diff > 0.25) {
                console.error(`Reverting progress from ${(this.progress * 100).toFixed((0))}% to ${(progress * 100).toFixed(0)}% - Diff: ${(diff * 100).toFixed(0)}`);
                this.progress = progress;
            }
        }

        const step = this.getCurrentStep();

        let status = `${(this.progress * 100).toFixed(0)}%`;
        let status2 = null;
        if (job.status === 'error') {
            const error = job.error || _('Unknown error');
            console.error(error);
            status2 = _('Error') + `: ${error}`;
        } else if (job.status === 'aborted') {
            console.error('Job aborted')
            status2 = _('Job has been aborted');
        } else if (step && this.progress < 1) {
            status2 = step.name;
        }

        if (status2) {
            status += `<br/>${status2}`;
            statusText.style.marginTop = '';
        } else {
            statusText.style.marginTop = '10px';
        }

        progressBar.style.width = `${this.progress * 100}%`;
        progressBar.style.display = 'unset';
        statusText.innerHTML = status;
    }

    getCurrentStep(): Step | null {
        if (!this.data || !this.data.steps) return null;
        const helper = (steps: [Step]): Step | null => {
            for (const s of steps) {
                if (s.is_running) {
                    if (s.steps) {
                        return helper(s.steps) || s;
                    } else {
                        return s;
                    }
                }
            }
            return this.data;
        }
        return helper(this.data.steps);
    }
}
