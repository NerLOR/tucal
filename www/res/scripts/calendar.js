"use strict";

const TIMEZONE = "Europe/Vienna";
const START_TIME = 7 * 60;  // 07:00 [min]
const END_TIME = 22 * 60;  // 22:00 [min]
const CACHE_EVENTS = 15;  // 15 [min]
const EVENT_PRE_LIVE = 15;  // 15 [min]
const LOOK_AHEAD = 8;  // 8 [week]


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
    lastReload = null;
    weeks = {};
    currentEvents = [];
    currentEventCb = null;

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
            th.innerHTML = `<div><ul></ul></div>`;
            th.rowSpan = 4;
            theadTr2.appendChild(th);
        }
        thead.appendChild(theadTr2);

        for (let i = 0; i < 3; i++) {
            const theadTr3 = document.createElement("tr");
            const th = document.createElement("th");
            switch (i) {
                case 0: th.innerHTML = `<button class="today-button">${_("Today").toUpperCase()}</button>`; break;
                case 1: th.innerHTML = `<button class="arrow-button">&larr;</button>`; break;
                case 2: th.innerHTML = `<button class="arrow-button">&rarr;</button>`; break;
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
            this.previous();
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
        for (let i = 0; i < 7; i++) {
            const day = document.createElement("div");
            day.classList.add("day");
            wrapper.appendChild(day);
        }
        this.cal.appendChild(wrapper);

        element.appendChild(this.cal);
    }

    setWeek(week, keep = false) {
        if (this.timer !== null) {
            clearInterval(this.timer);
            this.timer = null;
        }

        this.week = week;
        this.updateTime();
        this.lastReload = null;
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
            }, '', `/calendar/${this.subject}/${this.week.year}/W${this.week.week}/`);
        }

        this.timer = setInterval(() => {
            this.updateTime();
            this.reloadEvents();
        }, 1000);
    }

    updateTime() {
        const dt = asTimezone(new Date(), TIMEZONE);

        const tds = this.cal.getElementsByClassName("today");
        while (tds.length > 0) {
            tds[0].classList.remove("today");
        }

        const now = this.cal.getElementsByClassName("now");
        while (now.length > 0) {
            now[0].classList.remove("now");
        }
        const lastEvents = this.currentEvents;
        this.currentEvents = [];

        if (dt >= this.startDate() && dt < this.endDate()) {
            const weekDay = (dt.getDay() + 6) % 7;
            const tbody = this.cal.getElementsByTagName("tbody")[0];
            for (const tr of tbody.getElementsByTagName("tr")) {
                tr.children[weekDay + 1].classList.add("today");
            }

            const w = this.week.toString();
            if (w in this.weeks) {
                for (const evt of this.weeks[w].events) {
                    const preStart = new Date(evt.start);
                    const evtElem = document.getElementById(`event-${evt.id}`);
                    preStart.setMinutes(preStart.getMinutes() - EVENT_PRE_LIVE);
                    if (dt >= preStart && dt < evt.end) {
                        this.currentEvents.push(evt);
                    }
                    if (evtElem !== null && dt >= evt.start && dt < evt.end) {
                        evtElem.classList.add("now");
                    }
                }
            }

            if (this.currentEventCb !== null && !(lastEvents.every(item => this.currentEvents.includes(item)) &&
                    this.currentEvents.every(item => lastEvents.includes(item)))) {
                this.currentEventCb(this.currentEvents);
            }
        }

        const minutes = dt.getHours() * 60 + dt.getMinutes();
        const hr = this.cal.getElementsByTagName("hr")[0];
        if (minutes >= START_TIME && minutes <= END_TIME) {
            hr.style.setProperty("--time", `${minutes}`);
            hr.style.display = null;
        } else {
            hr.style.display = "none";
        }
    }

    setCurrentEventCb(cb) {
        this.currentEventCb = cb;
    }

    now() {
        this.setWeek(Week.fromDate(asTimezone(new Date())));
    }

    next() {
        this.setWeek(this.week.next());
    }

    previous() {
        this.setWeek(this.week.last());
    }

    startDate() {
        return this.week.startDate();
    }

    endDate() {
        return this.week.endDate();
    }

    weekIsValid(week) {
        const ref = asTimezone(new Date());
        ref.setMinutes(ref.getMinutes() - CACHE_EVENTS);
        const w = week.toString();
        return w in this.weeks && this.weeks[w].date !== null && this.weeks[w].date > ref;
    }

    reloadEvents() {
        const w = this.week.toString();
        let fetchCurrent = false;
        if (!this.weekIsValid(this.week)) {
            if (this.lastReload === null) {
                this.clearEvents(true);
            }
            if (!(w in this.weeks) || !this.weeks[w].promise) {
                fetchCurrent = true;
                this.fetchWeeks(this.week, this.week);
            }
        } else if (this.lastReload === null || this.lastReload !== this.weeks[w].date)  {
            this.clearEvents();
            const week = this.weeks[w];
            this.lastReload = week.date;
            this.drawEvents(week.events);
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

        if (json.message !== null) {
            if (json.status === "success") {
                console.warn(`API: ${json.message}`);
            } else {
                console.error(`API: ${json.message}`);
            }
        }

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

    clearEvents(loading = false) {
        const wrapper = this.cal.getElementsByClassName("event-wrapper")[0];
        const events = wrapper.getElementsByClassName("event");
        while (events.length > 0) events[0].remove();

        const theadTr = this.cal.getElementsByTagName("thead")[0].getElementsByTagName("tr")[1];
        const lis = theadTr.getElementsByTagName("li");
        while (lis.length > 0) lis[0].remove();

        const elem = wrapper.getElementsByClassName("loading");
        if (loading) {
            if (elem.length === 0) {
                const loading = document.createElement("div");
                loading.classList.add("loading");
                loading.innerText = _("Loading...");
                wrapper.appendChild(loading);
            }
        } else {
            while (elem.length > 0) elem[0].remove();
        }
    }

    drawEvents(all_events) {
        all_events.sort((a, b) => {
            return a.start - b.start;
        });

        const formatter = new Intl.DateTimeFormat('de-AT', {
            hour: "2-digit",
            minute: "2-digit",
        });

        const deadlines = [];
        const events = [[], [], [], [], [], [], []];
        for (const event of all_events) {
            const weekDay = (event.start.getDay() + 6) % 7;
            if (event.start.getTime() === event.end.getTime()) {
                deadlines.push(event);
            } else {
                events[weekDay].push(event);
            }
        }

        const theadTr = this.cal.getElementsByTagName("thead")[0].getElementsByTagName("tr")[1];
        for (const deadline of deadlines) {
            const time = deadline.start;
            const day = theadTr.getElementsByTagName("th")[(time.getDay() + 6) % 7].getElementsByTagName("ul")[0];

            const el = document.createElement("li");
            const short = getCourseName(deadline.course.nr);
            el.innerHTML = `<span class="time">${formatter.format(time)}</span> <span class="course">${short}</span> ${deadline.summary}`;
            day.appendChild(el);
        }

        for (const day of events) {
            const partList = {};
            for (let i = START_TIME; i <= END_TIME; i++) {
                let parts = 0;
                for (const evt of day) {
                    if (i > evt.getStartMinutes() && i < evt.getEndMinutes()) {
                        parts++;
                    }
                }
                partList[i] = parts;
            }

            const parsed = [];
            for (const evt of day) {
                let parts = 1;
                for (let i = evt.getStartMinutes(); i <= evt.getEndMinutes(); i++) {
                    if (partList[i] > parts) {
                        parts = partList[i];
                    }
                }
                parsed.push({
                    event: evt,
                    partsSelf: parts,
                    parts: parts,
                    part1: 0,
                    part2: 0,
                    affects: [],
                })
            }

            for (const evt1 of parsed) {
                const s1 = evt1.event.start;
                const e1 = evt1.event.end;
                for (const evt2 of parsed) {
                    const s2 = evt2.event.start;
                    const e2 = evt2.event.end;
                    if ((s2 >= s1 && s2 < e1) || (e2 > s1 && e2 <= e1) || (s2 < s1 && e2 > e1)) {
                        evt1.affects.push(evt2);
                    }
                }
            }

            let changed;
            do {
                changed = false;
                for (const evt1 of parsed) {
                    for (const evt2 of evt1.affects) {
                        if (evt2.parts > evt1.parts) {
                            evt1.parts = evt2.parts
                        }
                    }
                }
            } while (changed);

            let shift = 0;
            let p = 0;
            let last = null;
            for (const evt of parsed) {
                if (p >= evt.parts) {
                    p = 0;
                }
                evt.part1 = p;
                p += (evt.parts - evt.partsSelf);
                if (p >= evt.parts) {
                    shift = evt.parts - p + 1;
                }
                evt.part2 = p;

                const start0 = last !== null && last.event.start || null;
                const start1 = evt.event.start;
                if (last !== null && evt.affects.includes(last) && start1 > start0) {
                    last.part2 += 0.75;
                    evt.part1 -= 0.75;
                }

                last = evt;
                p++;
            }

            for (const evt of parsed) {
                evt.part1 = (evt.part1 + shift) % evt.parts;
                evt.part2 = (evt.part2 + shift) % evt.parts;
            }

            for (const eventData of parsed) {
                const event = eventData.event;
                const start = event.start;
                const end = event.end;

                const wrapper = this.cal.getElementsByClassName("event-wrapper")[0];
                const day = wrapper.getElementsByClassName("day")[(start.getDay() + 6) % 7];
                const evt = document.createElement("div");
                evt.classList.add("event");
                evt.id = `event-${event.id}`;

                const startMinute = start.getHours() * 60 + start.getMinutes();
                const endMinute = end.getHours() * 60 + end.getMinutes();

                evt.style.setProperty("--start", `${startMinute}`);
                evt.style.setProperty("--end", `${endMinute}`);
                evt.style.setProperty("--parts", `${eventData.parts}`);
                evt.style.setProperty("--part1", `${eventData.part1}`);
                evt.style.setProperty("--part2", `${eventData.part2}`)

                const startFmt = formatter.format(start);
                const endFmt = formatter.format(end);
                const short = getCourseName(event.course.nr);
                evt.innerHTML = `<span class="time">${startFmt}-${endFmt}</span><span class="course">${short}</span> ${event.summary}`;
                day.appendChild(evt);
            }
        }

        this.updateTime();
    }
}

class Event {
    start;
    end;
    id;
    course;
    semester;
    summary;
    desc;
    details;

    constructor(json) {
        this.id = json.id;
        this.start = asTimezone(new Date(Date.parse(json.start)), TIMEZONE);
        this.end = asTimezone(new Date(Date.parse(json.end)), TIMEZONE);
        this.course = json.course;
        this.semester = null;
        this.summary = json.data.summary;
        this.desc = json.data.desc;
        this.details = json.data.details;
    }

    getWeek() {
        return Week.fromDate(this.start);
    }

    getStartMinutes() {
        return this.start.getHours() * 60 + this.start.getMinutes();
    }

    getEndMinutes() {
        return this.end.getHours() * 60 + this.end.getMinutes();
    }

    isNow() {
        const dt = asTimezone(new Date());
        return dt >= this.start && dt < this.end;
    }
}
