"use strict";

const TIMEZONE = "Europe/Vienna";
const START_TIME = 7 * 60;  // [min]
const END_TIME = 22 * 60;  // [min]
const CACHE_EVENTS = 15;  // [min]
const LOOK_AHEAD = 8;


function isoWeekFromDate(date) {
    const dayOfWeek = (date.getDay() + 6) % 7;
    const refThursday = new Date(date);
    refThursday.setDate(refThursday.getDate() - dayOfWeek + 3);

    const firstThursday = new Date(refThursday.getFullYear(), 0, 1);
    if (firstThursday.getDay() !== 4) {
        firstThursday.setMonth(0, 1 + (4 - firstThursday.getDay() + 7) % 7);
    }

    return 1 + Math.round((refThursday - firstThursday) / 604800000);
}

function isoWeekToDate(year, week) {
    const date = new Date(year, 0, 1);
    if (date.getDay() !== 4) {
        date.setMonth(0, 1 + (4 - date.getDay() + 7) % 7);
    }

    const dayOfWeek = (date.getDay() + 6) % 7;
    date.setDate(date.getDate() - dayOfWeek + (week - 1) * 7);
    return date;
}

function asTimezone(date, timezone) {
    const updated = new Date(date.toLocaleString('en-US', {
        timeZone: timezone,
    }));
    const diff = date.getTime() - updated.getTime();
    return new Date(date.getTime() - diff);
}

class Week {
    year;
    week;

    constructor(year, week) {
        this.year = year;
        this.week = week;
    }

    static fromDate(date) {
        return new Week(date.getFullYear(), isoWeekFromDate(date));
    }

    toString() {
        return `${this.year}/W${this.week}`;
    }

    valueOf() {
        return this.year * 100 + this.week;
    }

    startDate() {
        return asTimezone(isoWeekToDate(this.year, this.week), TIMEZONE);
    }

    endDate() {
        const ref = this.startDate();
        ref.setDate(ref.getDate() + 7);
        return ref;
    }

    add(n) {
        const ref = this.startDate();
        ref.setDate(ref.getDate() + 7 * n);
        return new Week(ref.getFullYear(), isoWeekFromDate(ref));
    }

    next() {
        return this.add(1);
    }

    last() {
        return this.add(-1);
    }

    iterate(n, step = 1) {
        let i;
        let end;
        if (n instanceof Week) {
            i = this.add(0);
            end = n.add(0);
        } else if (n < 0 && step > 0) {
            i = this.add(n);
            end = this.add(0);
        } else {
            i = this.add(0);
            end = this.add(n)
        }
        return {
            *[Symbol.iterator]() {
                while (true) {
                    yield i;
                    if (i.year === end.year && i.week === end.week) {
                        return;
                    }
                    i = i.add(step);
                }
            }
        }
    }
}

class WeekSchedule {
    week = null;
    cal;
    subject;
    timer = null;
    weeks = {};

    constructor(subject, element) {
        this.subject = subject;
        this.cal = document.createElement("div");
        this.cal.classList.add("calendar");

        const table = document.createElement("table");
        const thead = table.createTHead();

        const theadTr1 = document.createElement("tr");
        for (let i = 0; i <= 7; i++) {
            const th = document.createElement("th");
            if (i === 0) {
                th.rowSpan = 2;
                th.innerHTML = `<div class="panel"><span class="year-header"></span><span class="week-header"></span></div>`;
            } else {
                th.classList.add("day-header");
            }
            theadTr1.appendChild(th);
        }
        thead.appendChild(theadTr1);

        const theadTr2 = document.createElement("tr");
        for (let j = 1; j <= 7; j++) {
            const th = document.createElement("th");
            th.rowSpan = 4;
            theadTr2.appendChild(th);
        }
        thead.appendChild(theadTr2);

        for (let i = 0; i < 3; i++) {
            const theadTr3 = document.createElement("tr");
            const th = document.createElement("th");
            switch (i) {
                case 0: th.innerHTML = '<button>HEUTE</button>'; break;
                case 1: th.innerHTML = '<button>🡄</button>'; break;
                case 2: th.innerHTML = '<button>🡆</button>'; break;
            }
            theadTr3.appendChild(th);
            thead.appendChild(theadTr3);
        }

        const tbody = table.createTBody();
        for (let i = 7.0; i <= 21.5; i += 0.5) {
            const tr = document.createElement("tr");
            const th = document.createElement("th");
            if (i >= 8 && i % 1 === 0) {
                th.innerText = `${i < 10 ? "0" + i : i}:00`;
            }
            tr.appendChild(th);
            for (let j = 0; j < 7; j++) {tr.appendChild(document.createElement("td"));}
            tbody.appendChild(tr);
        }

        const buttons = table.getElementsByTagName("button");
        buttons[0].addEventListener("click", (evt) => {
            this.now();
        });
        buttons[1].addEventListener("click", (evt) => {
            this.last();
        });
        buttons[2].addEventListener("click", (evt) => {
            this.next();
        });

        this.cal.appendChild(table);

        const wrapper = document.createElement("div");
        wrapper.classList.add("event-wrapper");
        const hr = document.createElement("hr");
        hr.style.display = "none";
        wrapper.appendChild(hr);
        this.cal.appendChild(wrapper);

        element.appendChild(this.cal);
    }

    setWeek(week, keep = false) {
        if (this.timer !== null) {
            clearInterval(this.timer);
            this.timer = null;
        }

        this.week = week;
        this.reloadEvents();

        this.cal.getElementsByClassName("year-header")[0].innerText = `${this.week.year}`;
        this.cal.getElementsByClassName("week-header")[0].innerText = `W${this.week.week}`;

        const ref = this.startDate();
        for (let th of this.cal.getElementsByClassName("day-header")) {
            th.innerText = ref.toLocaleDateString(LOCALE, {
                weekday: "short",
                day: "2-digit",
                month: "2-digit"
            });
            ref.setDate(ref.getDate() + 1);
        }

        if (!keep) {
            history.replaceState({
                year: this.week.year,
                week: this.week.week,
            }, '', `/calendar/${this.subject}/${this.week.year}/W${this.week.week}`);
        }

        this.updateTime();
        this.timer = setInterval(() => {
            this.updateTime();
        }, 1000);
    }

    updateTime() {
        const dt = asTimezone(new Date(), TIMEZONE);

        const tds = this.cal.getElementsByClassName("today");
        while (tds.length > 0) {
            tds[0].classList.remove("today");
        }

        if (dt >= this.startDate() && dt < this.endDate()) {
            const weekDay = (dt.getDay() + 6) % 7;
            const tbody = this.cal.getElementsByTagName("tbody")[0];
            for (const tr of tbody.getElementsByTagName("tr")) {
                tr.children[weekDay + 1].classList.add("today");
            }
        }

        const minutes = dt.getHours() * 60 + dt.getMinutes() - START_TIME;
        const hr = this.cal.getElementsByTagName("hr")[0];
        if (minutes >= 0 && minutes <= END_TIME - START_TIME) {
            hr.style.top = `${minutes / (END_TIME - START_TIME) * 100}%`;
            hr.style.display = null;
        } else {
            hr.style.display = "none";
        }
    }

    now() {
        this.setWeek(Week.fromDate(asTimezone(new Date())));
    }

    next() {
        this.setWeek(this.week.next());
    }

    last() {
        this.setWeek(this.week.last());
    }

    startDate() {
        return this.week.startDate();
    }

    endDate() {
        return this.week.endDate();
    }

    weekIsValid(week) {
        const ref = new Date();
        ref.setMinutes(ref.getMinutes() + CACHE_EVENTS);
        const w = week.toString();
        return w in this.weeks && this.weeks[w].date !== null && this.weeks[w].date < ref;
    }

    reloadEvents() {
        const w = this.week.toString();
        let fetchCurrent = false;
        if (!this.weekIsValid(this.week)) {
            if (!(w in this.weeks) || !this.weeks[w].promise) {
                fetchCurrent = true;
                this.fetchWeeks(this.week, this.week);
            }
        } else {
            this.clearEvents();
            const week = this.weeks[w];
            for (const event of week.events) {
                this.drawEvent(event);
            }
        }

        let upcoming = null;
        for (const week of this.week.iterate(LOOK_AHEAD)) {
            const w = week.toString();
            if (!this.weekIsValid(week) && (!(w in this.weeks) || !this.weeks[w].promise)) {
                upcoming = week;
                break;
            }
        }
        if (upcoming !== null && (upcoming.valueOf() <= this.week.add(LOOK_AHEAD / 2).valueOf())) {
            this.fetchWeeks(upcoming, this.week.add(LOOK_AHEAD), fetchCurrent ? 500 : 0);
        }

        let past = null;
        for (const week of this.week.iterate(-LOOK_AHEAD, -1)) {
            const w = week.toString();
            if (!this.weekIsValid(week) && (!(w in this.weeks) || !this.weeks[w].promise)) {
                past = week;
                break;
            }
        }
        if (past !== null && (past.valueOf() >= this.week.add(-LOOK_AHEAD / 2).valueOf())) {
            this.fetchWeeks(this.week.add(-LOOK_AHEAD), past, fetchCurrent ? 1000 : 0);
        }
    }

    fetchWeeks(startWeek, endWeek, wait = 0) {
        console.log("fetch", startWeek.toString(), endWeek.toString());
        const weekStrings = [];
        for (const week of startWeek.iterate(endWeek)) {
            const w = week.toString();
            weekStrings.push(w);
            if (!(w in this.weeks)) {
                this.weeks[w] = {
                    promise: null,
                    date: null,
                    week: week,
                    events: [],
                };
            }
        }

        const promise = sleep(wait).then(() => this.fetch(startWeek.startDate(), endWeek.endDate(), weekStrings));

        for (const week of startWeek.iterate(endWeek)) {
            this.weeks[week.toString()].promise = promise;
        }
    }

    async fetch(start, end, weeks = []) {
        start = `start=${start.toISOString()}`;
        end = `end=${end.toISOString()}`;
        const req = await fetch(`/api/tucal/calendar?subject=${this.subject}&${start}&${end}`);
        const json = await req.json();

        if (req.status === 200 && json.status === "success") {
            const ts = new Date(Date.parse(json.data.timestamp));

            for (const week of weeks) {
                const w = this.weeks[week];
                if (w.date === null || w.date !== ts) {
                    w.date = ts;
                    w.events = [];
                    w.promise = null;
                }
            }

            for (const evtJson of json.data.events) {
                const evt = new Event(evtJson);
                const w = this.weeks[evt.getWeek().toString()];
                w.events.push(evt);
            }

            if (weeks.includes(this.week.toString())) {
                this.reloadEvents();
            }
        }
    }

    clearEvents() {
        const wrapper = this.cal.getElementsByClassName("event-wrapper")[0];
        const events = wrapper.getElementsByTagName("div");
        while (events.length > 0) {
            events[0].remove();
        }
    }

    drawEvent(event) {
        const wrapper = this.cal.getElementsByClassName("event-wrapper")[0];
        const evt = document.createElement("div");
        evt.classList.add("event");

        const start = event.start.getHours() * 60 + event.start.getMinutes();
        const end = event.end.getHours() * 60 + event.end.getMinutes();
        const day = (event.start.getDay() + 6) % 7;

        evt.style.left = `${day / 7 * 100}%`;
        evt.style.top = `${(start - START_TIME) / (END_TIME - START_TIME) * 100}%`;
        evt.style.height = `calc(${(end - start) / (END_TIME - START_TIME) * 100}% - var(--margin) * 2)`;
        evt.innerText = "Hey";
        wrapper.appendChild(evt);
    }
}

class Event {
    start;
    end;

    constructor(json) {
        this.start = asTimezone(new Date(Date.parse(json.start)), TIMEZONE);
        this.end = asTimezone(new Date(Date.parse(json.end)), TIMEZONE);
    }

    getWeek() {
        return Week.fromDate(this.start);
    }
}
