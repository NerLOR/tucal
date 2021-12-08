"use strict";

class Job {
    elem;
    id;
    timer;
    onSuccess;
    onError;

    constructor(element, success = null, error = null) {
        this.elem = element;
        this.id = this.elem.getAttribute('data-job');
        this.onSuccess = success;
        this.onError = error;
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

        this.elem.innerHTML = `${job.status}<br/>${(job.progress * 100).toFixed(0)}%`;
        if (job.status === 'error' && job.error) {
            const line = job.error.split('\n').splice(-2)[0];
            const err = line.split(':').splice(-1)[0].trim();
            this.elem.innerHTML += `<br/>${err}`;
        }
    }
}
