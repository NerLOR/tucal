"use strict";

class Job {
    elem;
    id;
    timer;
    onSuccess;
    onError;
    lastEtas;

    constructor(element, success = null, error = null) {
        this.elem = element;
        this.id = this.elem.getAttribute('data-job');
        this.onSuccess = success;
        this.onError = error;
        this.lastEtas = [];

        const container = document.createElement("div");
        container.classList.add('progress-bar');
        const progBar = document.createElement("div");
        progBar.style.display = 'none';
        container.appendChild(progBar);
        const progStatus = document.createElement("span");
        progStatus.innerText = '0%';
        container.appendChild(progStatus);

        this.elem.appendChild(container);

        this.update();
        this.timer = setInterval(() => {
            this.update();
        }, 500);
    }

    async update() {
        let job;
        try {
            const req = await fetch(`/api/tucal/job?id=${this.id}`);
            const json = await req.json();
            job = json.data;
        } catch (e) {
            job = {
                'status': 'error',
                'error': e.message,
            }
        }

        if (job.status !== 'running') {
            clearInterval(this.timer);
        }

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

        if (job.remaining) {
            const start = new Date(Date.parse(job.start_ts));
            const elapsed = (new Date() - start) / 1000;
            const eta = job.time + job.remaining;
            if (this.lastEtas.length === 0 || eta !== this.lastEtas[this.lastEtas.length - 1]) {
                this.lastEtas.push(eta);
            }

            const max = Math.max(this.lastEtas);
            const average = (this.lastEtas.reduce((a, b) => a + b)) / this.lastEtas.length;
            const conservativeEta = (max + average) / 2 * 1.25;
            const progressEstimate = elapsed / conservativeEta;
            if (progressEstimate <= 0.99 && progress < progressEstimate) {
                progress = progressEstimate;
            }
        }

        let status = `${(progress * 100).toFixed(0)}%`;
        progBar.style.width = `${progress * 100}%`;
        progBar.style.display = 'unset';

        if (job.status === 'error' && job.error) {
            const line = job.error.split('\n').splice(-2)[0];
            const err = line.split(':').splice(-1)[0].trim();
            status = _('Error') + `: ${err}`;
        }

        statusText.innerText = status;
    }
}
