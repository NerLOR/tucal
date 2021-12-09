"use strict";

class Job {
    elem;
    id;
    timerFetch;
    timerUpdate;
    onSuccess;
    onError;
    lastEtas;
    data;
    progress;

    constructor(element, success = null, error = null) {
        this.elem = element;
        this.id = this.elem.getAttribute('data-job');
        this.onSuccess = success;
        this.onError = error;
        this.lastEtas = [];
        this.data = {};
        this.progress = 0;

        const container = document.createElement("div");
        container.classList.add('progress-bar');
        const progBar = document.createElement("div");
        progBar.style.display = 'none';
        container.appendChild(progBar);
        const progStatus = document.createElement("span");
        progStatus.innerText = '0%';
        container.appendChild(progStatus);

        this.elem.appendChild(container);

        this.fetch();
        this.timerFetch = setInterval(() => {
            this.fetch();
        }, 500);

        this.update();
        this.timerUpdate = setInterval(() => {
            this.update();
        }, 125);
    }

    async fetch() {
        let job;
        try {
            const req = await fetch(`/api/tucal/job?id=${this.id}`);
            const json = await req.json();
            if (json.data) {
                job = json.data;
            } else {
                job = {
                    'status': 'error',
                    'error': json.message,
                }
            }
        } catch (e) {
            job = {
                'status': 'error',
                'error': e.message,
            }
        }
        if (job.status !== 'running') {
            clearInterval(this.timerFetch);
        }
        if (job.remaining) {
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
        if (!job.status) return;

        const container = this.elem.getElementsByClassName("progress-bar")[0];
        const progBar = container.getElementsByTagName("div")[0];
        const statusText = container.getElementsByTagName("span")[0];

        if (job.status === 'error') {
            this.elem.classList.add('error');
            if (this.onError !== null) {
                this.onError();
            }
        } else if (job.status === 'success') {
            this.elem.classList.add('success');
            if (this.onSuccess !== null) {
                this.onSuccess();
            }
        }

        let progress = job.progress || 0;
        const now = new Date();
        now.setSeconds(now.getSeconds() - 1);

        if (job.remaining) {
            const start = new Date(Date.parse(job.start_ts));
            const elapsed = (now - start) / 1000;

            const max = Math.max(...this.lastEtas);
            const average = (this.lastEtas.reduce((a, b) => a + b)) / this.lastEtas.length;
            const conservativeEta = (max + average) / 2 + 1;
            const progressEstimate = elapsed / conservativeEta;
            if (progressEstimate <= 0.99 && progress < progressEstimate) {
                progress = progressEstimate;
            }
        }

        if (progress >= 1) {
            progress = 1;
            clearInterval(this.timerUpdate);
        }


        if (progress >= this.progress) {
            this.progress = progress;
        } else {
            const diff = this.progress - progress;
            if (diff > 0.0625) {
                console.warn(`Real progress at ${(progress * 100).toFixed(0)}%, but displaying ${(this.progress * 100).toFixed(0)}% - Diff: ${(diff * 100).toFixed(0)}`);
            }
            if (diff > 0.25) {
                this.progress = progress;
            }
        }

        let status = `${(this.progress * 100).toFixed(0)}%`;
        progBar.style.width = `${this.progress * 100}%`;
        progBar.style.display = 'unset';

        if (job.status === 'error' && job.error) {
            const line = job.error.split('\n').splice(-2)[0];
            const err = line.split(':').splice(-1)[0].trim();
            status = _('Error') + `: ${err}`;
        }

        statusText.innerText = status;
    }
}
