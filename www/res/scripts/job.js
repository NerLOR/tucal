"use strict";

class Job {
    elem;
    id;
    timer;
    onSuccess;
    onError;
    lastEtas;
    firstEta;

    constructor(element, success = null, error = null) {
        this.elem = element;
        this.id = this.elem.getAttribute('data-job');
        this.onSuccess = success;
        this.onError = error;
        this.eta = null;
        this.lastEtas = [];
        this.firstEta = null;

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
        const req = await fetch(`/api/tucal/job?id=${this.id}`);
        const json = await req.json();
        const job = json.data;

        if (job.status !== 'running') {
            clearInterval(this.timer);
        }

        if (job.status === 'error') {
            if (this.onError !== null) {
                this.onError();
            }
        } else if (job.status === 'success') {
            if (this.onSuccess !== null) {
                this.onSuccess();
            }
        }

        const container = this.elem.getElementsByClassName("progress-bar")[0];
        const progBar = container.getElementsByTagName("div")[0];
        const statusText = container.getElementsByTagName("span")[0];

        let progress = job.progress || 0;
        const start = new Date(Date.parse(job.start_ts));

        if (job.remaining) {
            const elapsed = (new Date() - start) / 1000;
            const eta = job.time + job.remaining;
            if (this.lastEtas.length === 0 || eta !== this.lastEtas[this.lastEtas.length - 1]) {
                this.lastEtas.push(eta);
            }
            if (this.firstEta === null) {
                this.firstEta = eta;
            }

            const average = (this.lastEtas.reduce((a, b) => a + b)) / this.lastEtas.length;
            const conservativeEta = (this.firstEta + average) / 2 * 1.25;
            const progressEstimate = elapsed / conservativeEta;
            if (progressEstimate <= 0.99 && progress < progressEstimate) {
                progress = progressEstimate;
            }
        }

        let status = `${job.status} - ${(progress * 100).toFixed(0)}%`;
        progBar.style.width = `${progress * 100}%`;
        progBar.style.display = 'unset';

        if (job.status === 'error' && job.error) {
            const line = job.error.split('\n').splice(-2)[0];
            const err = line.split(':').splice(-1)[0].trim();
            status = `${job.status} - ${err}`;
        }

        statusText.innerText = status;
    }
}
