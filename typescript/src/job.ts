"use strict";

class JobStep {
    name: string | undefined;
    isRunning: boolean | undefined;
    time: number | undefined;
    steps: JobStep[] | null | undefined;
    comments: string[] | undefined;

    constructor(step: JobStepJSON) {
        if (!step.name) return;

        this.name = step.name;
        this.isRunning = (step.is_running === true);
        this.time = step.time || undefined;
        this.comments = step.comments || [];

        if (step.steps) {
            this.steps = [];
            for (const subStep of step.steps) {
                this.steps.push(new JobStep(subStep));
            }
        } else {
            this.steps = null;
        }
    }
}

class BaseJobStep extends JobStep {
    remaining: number | null;
    start: string;
    eta: string | null;
    progress: number;
    error: string | null;

    constructor(step: BaseJobStepJSON) {
        if (!step.start_ts) throw new Error();
        super(step);
        this.remaining = step.remaining || null;
        this.start = step.start_ts;
        this.eta = step.eta_ts || null;
        this.progress = step.progress || 0;
        this.error = step.error || null;
    }
}

class Job {
    elem: HTMLElement;
    id: string;
    timerFetch: number | null;
    timerUpdate: number | null;
    onSuccess: Function | null;
    onError: Function | null;
    lastEtas: number[];
    data: BaseJobStep | null;
    status: string | null;
    errorMsg: string | null;
    progress: number;

    constructor(element: HTMLElement, success: Function | null = null, error: Function | null = null) {
        this.elem = element;
        const id = this.elem.dataset['jobId'];
        const dataStr = this.elem.dataset['job'];
        if (!id) throw new Error();

        if (dataStr) {
            const data = <JobJSON> JSON.parse(dataStr);
            this.data = data.data ? new BaseJobStep(data.data) : null;
            this.status = data.status;
            this.errorMsg = data.error_msg;
        } else {
            this.data = null;
            this.status = null;
            this.errorMsg = null;
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

        if (!this.data || (this.data && this.status === 'running')) {
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
        let job: JobJSON;
        try {
            const json = await api('/tucal/job', {'id': this.id});
            if (json.data) {
                job = json.data;
            } else {
                job = {
                    id: this.id,
                    status: 'error',
                    error_msg: json.message,
                    data: null,
                }
            }
        } catch (e: any) {
            job = {
                id: this.id,
                status: 'error',
                error_msg: e.message,
                data: null,
            }
        }

        if (job.status !== 'running' && this.timerFetch) {
            clearInterval(this.timerFetch);
            this.timerFetch = null;
        }

        if (job.data && job.data.time && job.data.remaining && this.data) {
            const eta = job.data.time + job.data.remaining;
            if (this.lastEtas.length === 0 || job.data.time !== this.data.time) {
                this.lastEtas.push(eta);
            }
        }

        this.status = job.status;
        this.errorMsg = job.error_msg;
        this.data = job.data ? new BaseJobStep(job.data) : null;
        this.update();
    }

    update() {
        const job = this.data;
        if (!job || !this.status) return;

        const container = this.elem.getElementsByClassName("progress-bar")[0];
        if (!container) throw new Error();

        const progressBar = container.getElementsByTagName("div")[0];
        const statusText = container.getElementsByTagName("span")[0];
        if (!progressBar || !statusText) throw new Error();

        const classList = this.elem.classList;
        if (this.status !== 'running' && !classList.contains('error') && !classList.contains('success')) {
            if (this.status !== 'success') {
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

        const now = new Date();
        now.setSeconds(now.getSeconds() - 1);

        if (job.remaining) {
            const start = new Date(Date.parse(job.start));
            const elapsed = (now.valueOf() - start.valueOf()) / 1000;

            if (this.lastEtas.length > 0) {
                const max = Math.max(...this.lastEtas);
                const average = (this.lastEtas.reduce((a, b) => a + b)) / this.lastEtas.length;
                const conservativeEta = ((this.lastEtas[0] || 0) + max + average) / 3 + 1;
                const progressEstimate = elapsed / conservativeEta;
                if (progressEstimate <= 0.99 && job.progress < progressEstimate) {
                    job.progress = progressEstimate;
                }
            }
        }

        if (job.progress >= 1 || this.status === 'success') job.progress = 1;
        if (this.status !== 'running' && this.timerUpdate) {
            clearInterval(this.timerUpdate);
            this.timerUpdate = null;
        }

        if (job.progress >= this.progress) {
            this.progress = job.progress;
        } else {
            const diff = this.progress - job.progress;
            if (diff > 0.0625) {
                console.warn(`Real progress at ${(job.progress * 100).toFixed(0)}%, but displaying ${(this.progress * 100).toFixed(0)}% - Diff: ${(diff * 100).toFixed(0)}`);
            }
            if (diff > 0.25) {
                console.error(`Reverting progress from ${(this.progress * 100).toFixed((0))}% to ${(job.progress * 100).toFixed(0)}% - Diff: ${(diff * 100).toFixed(0)}`);
                this.progress = job.progress;
            }
        }

        const step = this.getCurrentStep();

        let status = `${(this.progress * 100).toFixed(0)}%`;
        let statusInfo = null;
        if (this.status === 'error') {
            const error = this.errorMsg !== '' && this.errorMsg && (_('Error') + `: ${this.errorMsg}`) || _('Unknown error');
            console.error(error);
            statusInfo = error;
        } else if (this.status === 'aborted') {
            console.error('Job aborted')
            statusInfo = _('Job has been aborted');
        } else if (step && step.name && this.progress < 1) {
            statusInfo = step.name;
        }

        if (statusInfo) {
            status += `<br/>${statusInfo}`;
            statusText.style.marginTop = '';
        } else {
            statusText.style.marginTop = '10px';
        }

        progressBar.style.width = `${this.progress * 100}%`;
        progressBar.style.display = 'unset';
        statusText.innerHTML = status;
    }

    getCurrentStep(): JobStep | null {
        if (!this.data || !this.data.steps) return null;
        const helper = (steps: JobStep[]): JobStep | null => {
            for (const s of steps) {
                if (s.isRunning) {
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
