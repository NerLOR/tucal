"use strict";

const TIMEZONE = "Europe/Vienna";
const START_TIME = 7 * 60;  // 07:00 [min]
const END_TIME = 22 * 60;  // 22:00 [min]
const CACHE_EVENTS = 15;  // 15 [min]
const LOOK_AHEAD = 8;  // 8 [week]

const TISS_URL = "https://tiss.tuwien.ac.at/";
const TUWEL_URL = "https://tuwel.tuwien.ac.at/";

const ZOOM_PATTERN = "https://(tuwien\\.)?zoom.us/.*";
const YOUTUBE_PATTERN = "(https://youtu\\.be/.*)|(https://www.youtube.com/.*)";

const EVENT_STATUSES: {[index: string]: string} = {
    "confirmed": "Confirmed",
    "tentative": "Tentative",
    "cancelled": "Cancelled",
}

const EVENT_MODES: {[index: string]: string} = {
    "on_site_only": "On-site-only",
    "hybrid": "Hybrid",
    "online_only": "Online-only",
}


class WeekSchedule {
    cal: HTMLElement;
    week: Week | null;
    subject: string;
    eventId: string | null;
    timer: number | null = null;
    lastReload: Date | null = null;
    weeks: {
        [index: string]: {
            promise: Promise<void> | null,
            date: Date | null,
            week: Week,
            events: TucalEvent[],
        },
    } = {};
    showHidden: boolean = false;
    planned: boolean = true;

    constructor(element: Element, subject: string, eventId: string | null = null) {
        this.subject = subject;
        this.eventId = eventId;
        this.week = null;
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
            th.innerHTML = `<div class="special-event-wrapper"></div><div class="deadlines"><ul></ul></div>`;
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

        const tfoot = table.createTFoot();
        tfoot.appendChild(document.createElement("th"));
        const th = document.createElement("th");
        th.colSpan = 7;
        const settings = document.createElement("div");
        settings.classList.add('settings');
        settings.innerHTML =
            `<label><input type="checkbox" id="show-hidden"/> ${_('Show hidden events')}</label>` +
            `<label><input type="checkbox" id="show-planned"/> ${_('Use c.t. times')}</label>`;
        th.appendChild(settings);
        tfoot.appendChild(th);

        const showHidden = settings.getElementsByTagName("input")[0];
        const showPlanned = settings.getElementsByTagName("input")[1];
        if (!showHidden || !showPlanned) throw new Error();
        showHidden.checked = this.showHidden;
        showPlanned.checked = this.planned;
        showHidden.addEventListener("input", () => {
            this.showHidden = showHidden.checked;
            this.reloadEvents(true);
        });
        showPlanned.addEventListener("input", () => {
            this.planned = showPlanned.checked;
            this.reloadEvents(true);
        });

        const buttons = table.getElementsByTagName("button");
        if (!buttons[0] || !buttons[1] || !buttons[2]) throw new Error();
        buttons[0].addEventListener("click", () => {
            this.now();
        });
        buttons[1].addEventListener("click", () => {
            this.previous();
        });
        buttons[2].addEventListener("click", () => {
            this.next();
        });
        document.addEventListener("keydown", (evt) => {
            const path = evt.composedPath();
            if (!path[0] || (<HTMLElement> path[0]).tagName !== 'BODY') return;
            switch (evt.code) {
                case 'ArrowLeft': this.previous(); break;
                case 'ArrowRight': this.next(); break;
                case 'Numpad0': this.now(); break;
                case 'Escape': this.setEventId(null); break;
                default: return;
            }
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

        element.insertBefore(this.cal, element.firstChild);

        detectSwipe(this.cal, (direction: string) => {
            if (direction === 'left') {
                this.previous();
            } else if (direction === 'right') {
                this.next();
            }
        });

        window.addEventListener("click", (evt) => {
            const path = evt.composedPath();
            const div = document.getElementsByClassName("event-detail")[0];
            const nav = document.getElementsByTagName("nav")[0];
            if ((div && path.includes(div)) || (nav && path.includes(nav))) {
                return;
            }
            this.setEventId(null);
        });
    }

    setWeek(week: Week, keep = false) {
        if (this.timer !== null) {
            clearInterval(this.timer);
            this.timer = null;
        }

        if (this.week !== null) {
            this.eventId = null;
        }

        this.week = week;
        this.updateTime();
        this.lastReload = null;
        this.reloadEvents();

        const yearHeader = this.cal.getElementsByClassName("year-header")[0];
        if (!yearHeader) throw new Error();
        yearHeader.innerHTML = `${this.week.year}`;

        const weekHeader = this.cal.getElementsByClassName("week-header")[0];
        if (!weekHeader) throw new Error();
        weekHeader.innerHTML = `W${this.week.week}`;

        const ref = this.startDate();
        for (let th of this.cal.getElementsByClassName("day-header")) {
            th.innerHTML = ref.toLocaleDateString(LOCALE, {
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
            }, '', `/calendar/${this.subject}/${this.week.year}/W${this.week.week}/${this.eventId ?? ''}${location.hash}`);
        }

        this.timer = setInterval(() => {
            this.updateTime();
            this.reloadEvents();
        }, 1000);
    }

    setEventId(eventId: string | null) {
        if (!this.week) return;
        if (eventId === this.eventId) return;
        this.eventId = eventId;
        history.replaceState({
            year: this.week.year,
            week: this.week.week,
        }, '', `/calendar/${this.subject}/${this.week.year}/W${this.week.week}/${this.eventId ?? ''}`);
        this.displayEventDetail();
    }

    setShowHidden(showHidden: boolean) {
        this.showHidden = showHidden;
        const showHiddenInput = <HTMLInputElement> document.getElementById("show-hidden");
        if (!showHiddenInput) throw new Error();
        showHiddenInput.checked = this.showHidden;
    }

    setPlanned(planned: boolean) {
        this.planned = planned;
        const showPlannedInput = <HTMLInputElement> document.getElementById("show-planned");
        if (!showPlannedInput) throw new Error();
        showPlannedInput.checked = this.planned;
    }

    updateTime() {
        if (!this.week) return;
        const dt = asTimezone(new Date(), TIMEZONE);

        const tds = this.cal.getElementsByClassName("today");
        while (tds[0]) tds[0].classList.remove("today");


        const now = this.cal.getElementsByClassName("now");
        while (now[0]) now[0].classList.remove("now");

        if (dt >= this.startDate() && dt < this.endDate()) {
            const weekDay = (dt.getDay() + 6) % 7;
            const tbody = this.cal.getElementsByTagName("tbody")[0];
            if (!tbody) throw new Error();

            for (const tr of tbody.getElementsByTagName("tr")) {
                const ch = tr.children[weekDay + 1];
                if (!ch) throw new Error();
                ch.classList.add("today");
            }

            const w = this.week.toString();
            const week = this.weeks[w];
            if (week) {
                for (const evt of week.events) {
                    const evtElem = document.getElementById(`event-${evt.id}`);
                    if (evtElem && dt >= evt.start && dt < evt.end) {
                        evtElem.classList.add("now");
                    }
                }
            }
        }

        const minutes = dt.getHours() * 60 + dt.getMinutes();
        const hr = this.cal.getElementsByTagName("hr")[0];
        if (!hr) throw new Error();

        if (minutes >= START_TIME && minutes <= END_TIME) {
            hr.style.setProperty("--time", `${minutes}`);
            hr.style.display = "";
        } else {
            hr.style.display = "none";
        }
    }

    now() {
        this.setWeek(Week.fromDate(asTimezone(new Date(), TIMEZONE)));
    }

    next() {
        if (!this.week) throw new Error();
        this.setWeek(this.week.next());
    }

    previous() {
        if (!this.week) throw new Error();
        this.setWeek(this.week.last());
    }

    startDate(): Date {
        if (!this.week) throw new Error();
        return this.week.startDate();
    }

    endDate(): Date {
        if (!this.week) throw new Error();
        return this.week.endDate();
    }

    weekIsValid(week: Week) {
        const ref = asTimezone(new Date(), TIMEZONE);
        ref.setMinutes(ref.getMinutes() - CACHE_EVENTS);
        const w = week.toString();
        const weekData = this.weeks[w];
        return weekData && weekData.date !== null && weekData.date > ref;
    }

    reloadEvents(forceRedraw = false) {
        if (!this.week) throw new Error();
        const w = this.week.toString();
        const weekData = this.weeks[w];
        let fetchCurrent = false;
        if (!this.weekIsValid(this.week)) {
            if (this.lastReload === null) {
                this.clearEvents(true);
            }
            if (!weekData || !weekData.promise) {
                fetchCurrent = true;
                this.fetchWeeks(this.week, this.week);
            }
        } else if (!weekData) {
            return;
        } else if (forceRedraw || this.lastReload === null || this.lastReload !== weekData.date)  {
            this.clearEvents();
            this.lastReload = weekData.date;
            this.drawEvents(weekData.events);
            this.displayEventDetail();
        }

        let upcoming = null;
        for (const week of this.week.iterate(LOOK_AHEAD)) {
            const w = week.toString();
            const weekData = this.weeks[w];
            if (!this.weekIsValid(week) && (!weekData || !weekData.promise)) {
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
            const weekData = this.weeks[w];
            if (!this.weekIsValid(week) && (!weekData || !weekData.promise)) {
                past = week;
                break;
            }
        }
        if (past !== null && (past.valueOf() >= this.week.add(-LOOK_AHEAD / 2).valueOf())) {
            this.fetchWeeks(this.week.add(-LOOK_AHEAD), past, fetchCurrent ? 1000 : 0);
        }
    }

    fetchWeeks(startWeek: Week, endWeek: Week, wait: number = 0) {
        console.log("fetch", startWeek.toString(), endWeek.toString());
        const weekStrings: string[] = [];
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
            const weekData = this.weeks[week.toString()];
            if (!weekData) throw new Error();
            weekData.promise = promise;
        }
    }

    async fetch(start: Date, end: Date, weeks: string[] = []) {
        if (!this.week) throw new Error();

        // TODO error handling for 503 error etc.
        const json = await api('/calendar/calendar', {
            'subject': this.subject,
            'start': start.toISOString(),
            'end': end.toISOString(),
        })

        const ts = new Date(Date.parse(json.data.timestamp));
        for (const week of weeks) {
            const w = this.weeks[week];
            if (!w) throw new Error();
            if (w.date === null || w.date !== ts) {
                w.date = ts;
                w.events = [];
                w.promise = null;
            }
        }

        for (const evtJson of json.data.events) {
            const evt = new TucalEvent(evtJson);
            const evtWeeks = evt.getWeeks();
            for (const week of evtWeeks) {
                const ws = week.toString();
                if (!weeks.includes(ws)) continue;
                const w = this.weeks[ws];
                if (!w) throw new Error();
                w.events.push(evt);
            }
        }

        if (weeks.includes(this.week.toString())) {
            this.reloadEvents();
        }
    }

    clearEvents(loading = false) {
        const specialEvents = this.cal.getElementsByClassName("special-event");
        while (specialEvents[0]) specialEvents[0].remove();

        for (const wrapper of this.cal.getElementsByClassName("special-event-wrapper")) {
            const p = wrapper.parentElement;
            if (!p) throw new Error();
            p.style.setProperty("--height", '0');
        }

        const wrapper = this.cal.getElementsByClassName("event-wrapper")[0];
        if (!wrapper) throw new Error();

        const events = wrapper.getElementsByClassName("event");
        while (events[0]) events[0].remove();

        const thead = this.cal.getElementsByTagName("thead")[0];
        if (!thead) throw new Error();

        const theadTr = thead.getElementsByTagName("tr")[1];
        if (!theadTr) throw new Error();

        const lis = theadTr.getElementsByTagName("li");
        while (lis[0]) lis[0].remove();

        const elem = wrapper.getElementsByClassName("loading");
        if (loading) {
            if (elem.length === 0) {
                const loading = document.createElement("div");
                loading.classList.add("loading");
                loading.innerText = _("Loading...");
                wrapper.appendChild(loading);
            }
        } else {
            while (elem[0]) elem[0].remove();
        }
    }

    drawEvents(all_events: TucalEvent[]) {
        if (!this.week) throw new Error();
        all_events.sort((a, b) => {
            const diff = a.getStart().valueOf() - b.getStart().valueOf();
            return (diff === 0) ? (a.getEnd().valueOf() - b.getStart().valueOf()) : diff;
        });

        const formatter = new Intl.DateTimeFormat('de-AT', {
            hour: "2-digit",
            minute: "2-digit",
        });

        const deadlines = [];
        const special = [];
        const events: TucalEvent[][] = [[], [], [], [], [], [], []];
        for (const event of all_events) {
            const weekDay = (event.getStart().getDay() + 6) % 7;
            const day = events[weekDay];
            if (!day) throw new Error();
            if (event.deleted || (event.userHidden && !this.showHidden)) continue;

            if (event.getStart().getTime() === event.getEnd().getTime()) {
                deadlines.push(event);
            } else if (event.isDayEvent() || event.getEnd().valueOf() - event.getStart().valueOf() >= 43_200_000) {
                special.push(event);
            } else {
                day.push(event);
            }
        }

        const thead = this.cal.getElementsByTagName("thead")[0];
        if (!thead) throw new Error();

        const theadTr = thead.getElementsByTagName("tr")[1];
        if (!theadTr) throw new Error();

        const specialParsed: {
            start: number,
            end: number,
            len: number,
            overL: boolean,
            overR: boolean,
            pos: number | null,
            event: TucalEvent,
        }[] = []
        const startDate = this.week.startDate();
        const endDate = this.week.endDate();
        for (const event of special) {
            const start = (event.getStart() < startDate) ? 0 : ((event.getStart().getDay() + 6) % 7);
            const end = (event.end > endDate) ? 6 : ((new Date(event.end.getTime() - 1).getDay() + 6) % 7);
            specialParsed.push({
                start: start,
                end: end,
                len: end - start + 1,
                overL: (event.getStart() < startDate),
                overR: (event.end > endDate),
                pos: null,
                event: event,
            });
        }
        specialParsed.sort((a, b) => {
            const d1 = b.len - a.len;
            const d2 = a.start - b.start;
            return (d1 === 0) ? (d2 === 0) ? a.event.id.localeCompare(b.event.id) : d2 : d1;
        });

        const usage = [0, 0, 0, 0, 0, 0, 0];
        for (const meta of specialParsed) {
            let max = 0;
            for (let i = meta.start; i <= meta.end; i++) {
                max = Math.max(max, usage[i] || 0);
            }
            meta.pos = max;
            for (let i = meta.start; i <= meta.end; i++) {
                usage[i] = max + 1;
            }
        }

        const specialEventWrappers = this.cal.getElementsByClassName("special-event-wrapper");
        for (let i = 0; i < 7; i++) {
            const w = <HTMLElement> specialEventWrappers[i]?.parentElement;
            if (!w) throw new Error();
            w.style.setProperty("--height", `${usage[i]}`);
        }
        for (const meta of specialParsed) {
            const event = meta.event;
            const evt = document.createElement("div");

            evt.classList.add("special-event");
            if (event.type) evt.classList.add(event.type, "explicit");
            if (meta.overL) evt.classList.add("overhang-left");
            if (meta.overR) evt.classList.add("overhang-right");
            if (event.mode === 'online_only') evt.classList.add("online");
            if (event.status === 'cancelled') evt.classList.add("cancelled");
            if (event.userHidden) evt.classList.add("hidden");

            evt.id = `event-${event.id}`;
            evt.style.setProperty("--len", `${meta.end - meta.start + 1}`);
            evt.style.setProperty("--pos", `${meta.pos}`);

            evt.addEventListener("click", (evt) => {
                for (const elem of evt.composedPath()) {
                    if ((<HTMLElement> elem).tagName === 'A') return;
                }
                evt.stopImmediatePropagation();
                this.setEventId(event.id);
            });

            const groupName = (event.courseNr === null) ? ((event.groupName === 'Holidays') ? null : event.groupName) : event.getCourse()?.getName();

            let html = '';
            if (groupName !== null) html += `<span class="course">${groupName}</span> - `;
            if (event.summary !== null) html += `<span class="summary"></span>`;
            evt.innerHTML = html;

            const spanSummary = <HTMLElement> evt.getElementsByClassName('summary')[0];
            if (spanSummary && event.summary !== null) spanSummary.innerText = event.summary;

            const wrapper = specialEventWrappers[meta.start];
            if (!wrapper) throw new Error();
            wrapper.appendChild(evt);
        }

        for (const deadline of deadlines) {
            const time = deadline.start;
            const theadTh = theadTr.getElementsByTagName("th")[(time.getDay() + 6) % 7];
            if (!theadTh) throw new Error();

            const day = theadTh.getElementsByTagName("ul")[0];
            if (!day) throw new Error();

            const el = document.createElement("li");
            const course = deadline.getCourse();
            const short = course && course.getName();
            let str = `<span class="time">${formatter.format(time)}</span> <span class="course">${short}</span> ${deadline.summary}`;
            if (deadline.url && MNR === this.subject) {
                str = `<a href="${deadline.url}" target="_blank">${str}</a>`;
            }
            el.innerHTML = str;
            if (deadline.type) el.classList.add(deadline.type);

            day.appendChild(el);
        }

        const wrapper = this.cal.getElementsByClassName("event-wrapper")[0];
        if (!wrapper) throw new Error();

        for (const day of events) {
            for (const eventData of placeDayEvents(day)) {
                const event = eventData.event;
                const start = event.getStart();
                const end = event.getEnd();

                const day = wrapper.getElementsByClassName("day")[(start.getDay() + 6) % 7];
                if (!day) throw new Error();

                const evt = document.createElement("div");
                evt.id = `event-${event.id}`;

                evt.classList.add("event");
                if (event.type) evt.classList.add(event.type, "explicit");
                if (event.mode === 'online_only') evt.classList.add("online");
                if (event.status === 'cancelled') evt.classList.add("cancelled");
                if (event.userHidden) evt.classList.add("hidden");

                const startMinute = start.getHours() * 60 + start.getMinutes();
                let endMinute = end.getHours() * 60 + end.getMinutes();
                while (endMinute < startMinute) endMinute += 24 * 60;

                evt.style.setProperty("--start", `${startMinute}`);
                evt.style.setProperty("--end", `${endMinute}`);
                evt.style.setProperty("--parts", `${eventData.parts}`);
                evt.style.setProperty("--part1", `${eventData.part1}`);
                evt.style.setProperty("--part2", `${eventData.part2}`);

                evt.addEventListener("click", (evt) => {
                    for (const elem of evt.composedPath()) {
                        if ((<HTMLElement> elem).tagName === 'A') return;
                    }
                    evt.stopImmediatePropagation();
                    this.setEventId(event.id);
                });

                const startFmt = formatter.format(this.planned && !event.isExamSlot() ? event.plannedStart || start : start);
                const endFmt = formatter.format(this.planned && !event.isExamSlot() ? event.plannedEnd || end : end);
                const course = event.getCourse();
                const room = event.getExamSlotRoom() || event.getRoom();
                const ltLink = room && room.getLectureTubeLink() || null;

                let cGroup = event.courseGroup;
                if (cGroup === 'LVA') {
                    cGroup = null;
                } else if (cGroup !== null) {
                    cGroup = cGroup.replace('Gruppe Gruppe', 'Gruppe').replace('Gruppe Kohorte', 'Kohorte');
                }

                evt.innerHTML =
                    '<div class="pre"></div>' +
                    '<div class="post"></div>' +
                    '<div class="event-data">' +
                    (event.lectureTube && ltLink ? `<a class="live lt" href="${ltLink}" target="_blank" title="${_('LectureTube livestream')}"><img src="/res/icons/lecturetube-live.png" alt="LectureTube"/></a>` : '') +
                    (event.zoom !== null ? `<a class="live zoom" target="_blank" title="Zoom"><img src="/res/icons/zoom.png" alt="${_('Zoom')}"/></a>` : '') +
                    (event.youtube !== null ? `<a class="live yt" target="_blank" title="Zoom"><img src="/res/icons/youtube.png" alt="${_('YouTube')}"/></a>` : '') +
                    `<div class="time">${startFmt}-${endFmt}</div>` +
                    `<div class="course"><span class="course">${course?.getName() || event.groupName}</span>` +
                    (room !== null ? ` - <span class="room">${room.getName()}</span>` : '') + '</div><div class="group">' +
                    (cGroup !== null ? `<span class="group">${cGroup}</span>` : '') + '</div>' +
                    (event.summary !== null ? `<div class="summary"></div>` : '') +
                    '</div>';

                const aZoom = evt.getElementsByClassName('zoom')[0];
                if (aZoom && event.zoom) aZoom.setAttribute('href', event.zoom);
                const aYt = evt.getElementsByClassName('yt')[0];
                if (aYt && event.youtube) aYt.setAttribute('href', event.youtube);

                const divSummary = <HTMLElement> evt.getElementsByClassName('summary')[0];
                if (divSummary && event.summary !== null) divSummary.innerText = event.summary;

                const evtMinutes = (end.valueOf() - start.valueOf()) / 60_000;
                const pre = <HTMLElement> evt.getElementsByClassName("pre")[0];
                const post = <HTMLElement> evt.getElementsByClassName("post")[0];
                const data = <HTMLElement> evt.getElementsByClassName("event-data")[0];
                if (!pre || !post || !data) throw new Error();

                let preMin = 0, postMin = 0;
                if (this.planned && !event.isExamSlot()) {
                    if (event.plannedStart) preMin = (event.plannedStart.getTime() - event.start.getTime()) / 60_000;
                    if (event.plannedEnd) postMin = (event.end.getTime() - event.plannedEnd.getTime()) / 60_000;
                }

                pre.style.height =`${preMin / evtMinutes * 100}%`;
                post.style.height = `${postMin / evtMinutes * 100}%`;
                data.style.height = `calc(${(evtMinutes - preMin - postMin) / evtMinutes * 100}% + 2px)`;
                data.style.top = `calc(${preMin / evtMinutes * 100}% - 1px)`;

                day.appendChild(evt);
            }
        }

        this.updateTime();
    }

    displayEventDetail() {
        const eventId = this.eventId;
        if (!this.week) throw new Error();

        this.clearEventDetail();
        if (eventId === null) return;

        const week = this.weeks[this.week.toString()];
        if (!week) throw new Error();

        const evt = week.events.find((evt) => evt.id === this.eventId);
        if (!evt) throw new Error();
        const course = evt.getCourse();
        const room = evt.getExamSlotRoom() || evt.getRoom();

        const courseName = course && (LOCALE_GROUP === 'de' ? course.name_de : course.name_en);

        const wrapper = document.createElement("div");
        wrapper.classList.add("event-detail-wrapper");
        const div = document.createElement("div");
        div.classList.add("event-detail");
        wrapper.appendChild(div);

        let html = '';

        const ltLink = room && room.getLectureTubeLink() || null;
        if (evt.lectureTube && ltLink) {
            html += `<a class="live lt" href="${ltLink}" target="_blank" title="${_('LectureTube livestream')}">` +
                `<img src="/res/icons/lecturetube-live.png" alt="${_('LectureTube livestream')}"/></a>`;
        }
        if (evt.zoom) {
            html += `<a class="live zoom" href="${evt.zoom}" target="_blank" title="${_('Zoom')}"><img src="/res/icons/zoom.png" alt="${_('Zoom')}"/></a>`;
        }
        if (evt.youtube) {
            html += `<a class="live yt" href="${evt.youtube}" target="_blank" title="${_('YouTube')}"><img src="/res/icons/youtube.png" alt="${_('YouTube')}"/></a>`;
        }

        if (course) {
            html += `<h2><a href="/courses/#${course.nr}-${evt.semester}">` +
                `<span class="course-name">${course.getName()}</span> ` +
                `<span class="course-type">(${course.type})</span> ` +
                `<span class="course-nr">${course.getCourseNr()} (${evt.semester})</span>` +
                `</h2></a><h3>${courseName}</h3>`;
        } else {
            html += `<h2><span class="course-name">${evt.groupName}</span></h2>`;
            if (evt.organizer) {
                html += `<h3>${evt.organizer}</h3>`;
            }
        }

        const formatterDay = new Intl.DateTimeFormat(LOCALE, {
            weekday: "long",
            day: "numeric",
            month: "long",
            year: "numeric",
        });
        const formatterTime = new Intl.DateTimeFormat(LOCALE, {
            hour: "2-digit",
            minute: "2-digit",
        });
        const formatterDateTime = new Intl.DateTimeFormat(LOCALE, {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
        const formatterDate = new Intl.DateTimeFormat(LOCALE, {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
        });

        html += `<h4>`;
        if (evt.isDayEvent()) {
            const start = formatterDate.format(evt.start);
            const end = formatterDate.format(new Date(Math.max(evt.end.valueOf() - 1, evt.start.valueOf())));
            if (start !== end) {
                html += `<span class="time">${start} – ${end}</span>`;
            } else {
                html += `<span class="time">${start}</span>`;
            }
        } else if (evt.isExamSlot()) {
            html += `<span class="time">${formatterDate.format(evt.start)}, Slot ${formatterTime.format(evt.getStart())}-${formatterTime.format(evt.getEnd())}</span>`;
        } else if (evt.end.valueOf() - evt.start.valueOf() >= 86_400_000) {
            html += `<span class="time">${formatterDateTime.format(evt.start)} – ${formatterDateTime.format(evt.end)}</span>`;
        } else {
            if (evt.plannedStart || evt.plannedEnd) {
                html += `<span class="time">${formatterTime.format(evt.plannedStart || evt.start)}-${formatterTime.format(evt.plannedEnd || evt.end)}</span> / `;
            }
            html +=
                `<span class="time">${formatterTime.format(evt.start)}-${formatterTime.format(evt.end)}</span> ` +
                `<span class="day">(${formatterDay.format(evt.start)})</span>`;
        }

        const tissUrl = (evt.url && evt.url.startsWith(TISS_URL)) ? evt.url : evt.tissUrl;
        const tuwelUrl = (evt.url && evt.url.startsWith(TUWEL_URL)) ? evt.url : evt.tuwelUrl;

        if (this.subject === MNR && tissUrl) {
            html += `<a class="link" href="${tissUrl}" target="_blank">TISS</a>`;
        }
        if (this.subject === MNR && tuwelUrl) {
            html += `<a class="link" href="${tuwelUrl}" target="_blank">TUWEL</a>`;
        }
        if (evt.sourceUrl) {
            html += `<a class="link" href="${evt.sourceUrl}" target="_blank">${evt.sourceName || evt.groupName}</a>`;
        }

        html += `</h4><form name="event-detail">`;

        if (room) {
            html += `<div class="container"><div>${_('Room')}:</div><div class="room">`;

            const codes = room.getCodeFormat().replace(/ /g, '&nbsp;');
            html += `<a href="https://toss.fsinf.at/?q=${room.ltRoomCode || room.roomCodes[0]}" target="_blank">` +
                `<span class="room-name">${room.getNameLong()}</span> <span class="room-codes">(${codes})</span></a><br/>` +
                `${room.getAddress().replace(/\n/g, '<br/>')}</div></div>`;
        }

        if (evt.courseGroup && evt.courseGroup !== 'LVA') {
            let group = evt.courseGroup;
            while (group.startsWith('Gruppe ')) group = group.substring(7);
            html += `<div class="container"><div>${_('Group')}:</div><div>${group}</div></div>`;
        }

        if (evt.summary) {
            html += `<div class="container"><div>${_('Summary')}:</div><div class="evt-detail-summary"></div></div>`
        }

        if (evt.status || evt.mode) {
            const status = evt.status && EVENT_STATUSES[evt.status] || 'Unknown';
            const mode = evt.mode && EVENT_MODES[evt.mode] || 'Unknown';
            html += `<div class="container"><div>${_('Status')}:</div><div>${_(status)} – ${_(mode)}</div></div>`;
        }

        if (evt.desc) {
            html += `<div class="container"><div>${_('Description')}:</div><div>${evt.desc}</div></div>`;
        }

        if (this.subject === MNR) {
            html += `<div class="container"><div>${_('Custom (settings)')}:</div><div>` +
                `<label><input type="checkbox" name="hidden"/> ${_('Hide')}</label>`;
            if (evt.type === 'exam') {
                html += `<br/>` +
                    `<label>${_('Slot times')}: ` +
                    `<input type="time" name="slot-start" class="line" pattern="[0-9]{2}:[0-9]{2}"/>` +
                    `<input type="time" name="slot-end" class="line" pattern="[0-9]{2}:[0-9]{2}"/>` +
                    `</label><br/>` +
                    `<label>${_('Slot room')}: ` +
                    `<select name="slot-room"><option value="none">${_('No room')}</option></select>` +
                    `</label>`;
            }
            html += `</div></div>`;
        }

        if (MNR !== null) {
            html += '<hr/><div class="form-pre hidden">';

            html += `<div class="container"><div>${_('Live')}:</div><div>` +
                `<label class="radio"><input type="checkbox" name="lt"/> ${_('LectureTube')}</label>` +
                `<label class="radio"><input type="checkbox" name="zoom"/> ${_('Zoom')}</label>` +
                `<label class="radio"><input type="checkbox" name="yt"/> ${_('YouTube')}</label>` +
                `<div class="url hidden"><input type="url" name="zoom-url" placeholder="${_('Zoom URL')}" class="line block" required pattern="${ZOOM_PATTERN}"/></div>` +
                `<div class="url hidden"><input type="url" name="yt-url" placeholder="${_('YouTube URL')}" class="line block" required pattern="${YOUTUBE_PATTERN}"/></div>` +
                `</div></div>`;

            html += `<div class="container"><div>${_('Status')}:</div><div>` +
                `<label class="radio"><input type="radio" name="status" value="confirmed"/> ${_('Confirmed')}</label>` +
                `<label class="radio"><input type="radio" name="status" value="tentative"/> ${_('Tentative')}</label>` +
                `<label class="radio"><input type="radio" name="status" value="cancelled"/> ${_('Cancelled')}</label>` +
                `<label class="radio"><input type="radio" name="status" value="unknown" checked/> ${_('Unknown')}</label>` +
                `</div></div>`;

            html += `<div class="container"><div>${_('Mode')}:</div><div>` +
                `<label class="radio"><input type="radio" name="mode" value="on-site-only"/> ${_('On-site-only')}</label>` +
                `<label class="radio"><input type="radio" name="mode" value="hybrid"/> ${_('Hybrid')}</label>` +
                `<label class="radio"><input type="radio" name="mode" value="online-only"/> ${_('Online-only')}</label>` +
                `<label class="radio"><input type="radio" name="mode" value="unknown" checked/> ${_('Unknown')}</label>` +
                `</div></div>`;

            html += `<div class="container"><div>${_('Room')}:</div><div>` +
                `<select name="room"><option value="none">${_('No room')}</option></select>` +
                `</div></div>`;

            html += `<div class="container"><div>${_('Planned times')}:</div><div>` +
                `<input type="time" name="planned-start" class="line" pattern="[0-9]{2}:[0-9]{2}"/>` +
                `<input type="time" name="planned-end" class="line" pattern="[0-9]{2}:[0-9]{2}"/>` +
                `</div></div>`;

            html += `<div class="container"><div>${_('Summary')}:</div><div>` +
                `<input type="text" name="summary" class="line block" placeholder="${_('Summary')}"/>` +
                `</div></div>`;

            html += '</div><hr class="form-pre hidden"/><button type="button">&blacktriangledown;</button>' +
                `<div class="form-save hidden">` +
                `<label><input type="checkbox" name="all-previous"/> ${_('Apply changes for all previous events')}</label>` +
                `<label><input type="checkbox" name="all-following"/> ${_('Apply changes for all following events')}</label>` +
                `<button type="submit">${_('Apply')}</button></div>`;
        }

        html += '</form>';
        div.innerHTML = html;

        if (MNR !== null) this.initEventDetailForm(evt, div, formatterTime);

        this.cal.appendChild(wrapper);
    }

    private initEventDetailForm(evt: TucalEvent, div: HTMLElement, formatterTime: Intl.DateTimeFormat) {
        const aLive = div.getElementsByClassName("live")[0];
        if (aLive && evt.zoom) aLive.setAttribute('href', evt.zoom.toString());

        const divSummary = <HTMLElement> div.getElementsByClassName("evt-detail-summary")[0];
        if (divSummary && evt.summary) divSummary.innerText = evt.summary;

        const button = div.getElementsByTagName("button")[0];
        const submitButton = div.getElementsByTagName("button")[1];
        const form = div.getElementsByTagName("form")[0];
        const formDiv = div.getElementsByClassName("form-save")[0];
        const formPre = div.getElementsByClassName("form-pre");
        if (!button || !submitButton || !form || !formDiv) throw new Error();

        const hidden = (<HTMLInputElement> <unknown> form['hidden']) || null;
        const slotStart = (<HTMLInputElement> <unknown> form['slot-start']) || null;
        const slotEnd = (<HTMLInputElement> <unknown> form['slot-end']) || null;
        const slotRoomSelect = (<HTMLInputElement> <unknown> form['slot-room']) || null;

        const useLt = form['lt'];
        const useZoom = form['zoom'];
        const useYt = form['yt'];
        const zoomUrl = form['zoom-url'];
        const ytUrl = form['yt-url'];
        const zoomUrlDiv = zoomUrl.parentElement;
        const ytUrlDiv = ytUrl.parentElement;
        const roomSelect = form['room'];
        const summary = form['summary'];
        const status = form['status'];
        const mode = form['mode'];
        const plannedStart = form['planned-start'];
        const plannedEnd = form['planned-end'];
        let manual = false;

        if (ROOMS) {
            const selects = [roomSelect];
            if (slotRoomSelect) selects.push(slotRoomSelect);
            for (const roomNr in ROOMS) {
                const r = ROOMS[roomNr];
                if (!r) continue;
                for (const select of selects) {
                    const opt = document.createElement("option");
                    opt.innerText = `${r.getNameLong()} (${r.getCodeFormat()})`;
                    opt.value = `${r.nr}`;
                    select.appendChild(opt);
                }
            }
        }

        button.addEventListener('click', () => {
            if (!manual) {
                button.innerHTML = '&blacktriangle;';
                if (hasChanged()) formDiv.classList.remove('hidden');
                for (const f of formPre) f.classList.remove('hidden');
                manual = true;
            } else {
                button.innerHTML = '&blacktriangledown;';
                formDiv.classList.add('hidden');
                for (const f of formPre) f.classList.add('hidden');
                manual = false;
            }
        });

        const hasHiddenChanged = (): boolean => {
            return hidden && !!evt.userHidden !== hidden.checked;
        }

        const hasSlotTimesChanged = (): boolean => {
            return slotStart && slotEnd && (
                !((evt.examSlotStart && slotStart.value && formatterTime.format(evt.examSlotStart) === slotStart.value) || (!evt.examSlotStart && !slotStart.value)) ||
                !((evt.examSlotEnd && slotEnd.value && formatterTime.format(evt.examSlotEnd) === slotEnd.value) || (!evt.examSlotEnd && !slotEnd.value))
            );
        }

        const hasSlotRoomChanged = (): boolean => {
            return slotRoomSelect && evt.examSlotRoomNr !== (parseInt(slotRoomSelect.value) || null);
        }

        const hasLiveChanged = (): boolean => {
            return (!!evt.zoom !== useZoom.checked) ||
                (useZoom.checked && evt.zoom !== zoomUrl.value) ||
                (!!evt.lectureTube !== useLt.checked) ||
                (!!evt.youtube !== useYt.checked) ||
                (useYt.checked && evt.youtube !== ytUrl.value);
        }

        const hasRoomChanged = (): boolean => {
            return evt.roomNr !== (parseInt(roomSelect.value) || null);
        }

        const hasStatusChanged = (): boolean => {
            return evt.status !== ((status.value !== 'unknown') ? status.value : null);
        }

        const hasModeChanged = (): boolean => {
            return evt.mode !== ((mode.value !== 'unknown') ? mode.value.replace(/-/g, '_') : null);
        }

        const hasSummaryChanged = (): boolean => {
            return evt.summary !== (summary.value !== '' ? summary.value : null);
        }

        const hasPlannedTimesChanged = (): boolean => {
            return (
                !((evt.plannedStart && plannedStart.value && formatterTime.format(evt.plannedStart) === plannedStart.value) || (!evt.plannedStart && !plannedStart.value)) ||
                !((evt.plannedEnd && plannedEnd.value && formatterTime.format(evt.plannedEnd) === plannedEnd.value) || (!evt.plannedEnd && !plannedEnd.value))
            );
        }

        const hasChanged = (): boolean => {
            return hasLiveChanged() ||
                hasRoomChanged() ||
                hasStatusChanged() ||
                hasModeChanged() ||
                hasSummaryChanged() ||
                hasHiddenChanged() ||
                hasPlannedTimesChanged() ||
                hasSlotRoomChanged() ||
                hasSlotTimesChanged();
        }

        const onChange = () => {
            // disable LectureTube
            if (roomSelect.value && ROOMS) {
                const room = ROOMS[parseInt(roomSelect.value)];
                useLt.disabled = (!room || !room.ltName);
            } else {
                useLt.disabled = true;
            }

            if (useZoom.checked) {
                if (zoomUrlDiv.classList.contains('hidden')) zoomUrlDiv.classList.remove('hidden');
                zoomUrl.required = 'required';
            } else {
                if (!zoomUrlDiv.classList.contains('hidden')) zoomUrlDiv.classList.add('hidden');
                zoomUrl.required = undefined;
            }
            if (useYt.checked) {
                if (ytUrlDiv.classList.contains('hidden')) ytUrlDiv.classList.remove('hidden');
                ytUrl.required = 'required';
            } else {
                if (!ytUrlDiv.classList.contains('hidden')) ytUrlDiv.classList.add('hidden');
                ytUrl.required = undefined;
            }

            if (hasChanged()) {
                formDiv.classList.remove('hidden');
            } else {
                formDiv.classList.add('hidden');
            }

            submitButton.disabled = !hasChanged();
        }

        if (evt.userHidden && hidden) hidden.checked = true;
        if (evt.examSlotStart && slotStart) slotStart.value = formatterTime.format(evt.examSlotStart);
        if (evt.examSlotEnd && slotEnd) slotEnd.value = formatterTime.format(evt.examSlotEnd);
        if (evt.examSlotRoomNr && slotRoomSelect) slotRoomSelect.value = `${evt.examSlotRoomNr}`;

        if (evt.zoom) {
            useZoom.checked = true;
            zoomUrl.value = evt.zoom;
        }
        if (evt.lectureTube) {
            useLt.checked = true;
        }
        if (evt.youtube) {
            useYt.checked = true;
            ytUrl.value = evt.youtube;
        }
        if (evt.roomNr) roomSelect.value = `${evt.roomNr}`;
        if (evt.summary) summary.value = evt.summary;
        if (evt.status) status.value = evt.status;
        if (evt.mode) mode.value = evt.mode.replace(/_/g, '-');
        if (evt.plannedStart) plannedStart.value = formatterTime.format(evt.plannedStart);
        if (evt.plannedEnd) plannedEnd.value = formatterTime.format(evt.plannedEnd);

        form.addEventListener('input', onChange);
        onChange();

        form.addEventListener('submit', (e) => {
            e.preventDefault();

            const urlData: {[index: string]: any} = {id: this.eventId};
            if (form['all-previous'].checked) urlData['previous'] = 'true';
            if (form['all-following'].checked) urlData['following'] = 'true';

            const data: {[index: string]: any} = {};
            const dataUser: {[index: string]: any} = {};
            const user: {[index: string]: any} = {};

            if (hasHiddenChanged() && hidden) {
                user['hidden'] = hidden.checked;
            }

            if ((hasSlotTimesChanged() && slotStart && slotEnd) || (hasSlotRoomChanged() && slotRoomSelect)) {
                const v = slotRoomSelect && slotRoomSelect.value || null;
                user['exam'] = {
                    'slot_start': (slotStart && slotStart.value) || evt.examSlotStart,
                    'slot_end': (slotEnd && slotEnd.value) || evt.examSlotEnd,
                    'slot_room_nr': (v !== null) ? ((v !== 'none') ? parseInt(v) : null) : evt.examSlotRoomNr,
                };
            }

            if (hasLiveChanged()) {
                dataUser['lt'] = !!useLt.checked;
                dataUser['zoom'] = (useZoom.checked) ? zoomUrl.value.trim() : null;
                dataUser['yt'] = (useYt.checked) ? ytUrl.value.trim() : null;
            }

            if (hasStatusChanged()) {
                dataUser['status'] = (status.value !== 'unknown') ? status.value : null;
            }

            if (hasModeChanged()) {
                dataUser['mode'] = (mode.value !== 'unknown') ? mode.value.replace(/-/g, '_') : null;
            }

            if (hasSummaryChanged()) {
                dataUser['summary'] = (summary.value !== '') ? summary.value.trim() : null;
            }

            if (hasPlannedTimesChanged()) {
                data['planned_start'] = plannedStart.value || null;
                data['planned_end'] = plannedEnd.value || null;
            }

            data['data'] = data['data'] || {};
            data['data']['user'] = dataUser;
            data['user'] = user
            api('/calendar/update', urlData, data).then(() => {
                // wait for backend to update events
                sleep(1000).then(() => {
                    if (urlData['previous'] || urlData['following'] || evt.getWeeks().length > 1) {
                        this.weeks = {};
                    } else if (this.week) {
                        delete this.weeks[this.week.toString()];
                    }
                    this.reloadEvents();
                });
            });
        });
    }

    clearEventDetail() {
        const eventDetail = this.cal.getElementsByClassName("event-detail-wrapper");
        while (eventDetail[0]) eventDetail[0].remove();
    }
}

function placeDayEvents(dayEvents: TucalEvent[]) {
    const parsed: {
        event: TucalEvent,
        parts: number,
        part1: number,
        part2: number,
        concurrent: any,
        placed: boolean,
    }[] = [];
    for (const evt1 of dayEvents) {
        parsed.push({
            event: evt1,
            parts: 1,
            part1: 0,
            part2: 1,
            concurrent: [],
            placed: false,
        })
    }

    const hour = 60 * 60 * 1000;
    for (const evt1 of parsed) {
        const start1 = evt1.event.getStart().getTime();
        const end1 = evt1.event.getEnd().getTime();
        const len = end1 - start1;

        for (const evt2 of parsed) {
            if (evt2 === evt1) continue;
            const start2 = evt2.event.getStart().getTime();
            const end2 = evt2.event.getEnd().getTime();

            if (Math.abs(start1 - start2) < Math.min(hour, len, end2 - start2)) {
                evt1.concurrent.push(evt2);
            }
        }
    }

    let cur = [];
    for (const evt of parsed) {
        if (evt.placed) {
            continue;
        }
        for (let i = 0; i < cur.length; i++) {
            const p = cur[i];
            if (p && p.event.getEnd() <= evt.event.getStart()) {
                cur.splice(i);
            }
        }
        let p = Math.pow(0.875, cur.length);
        if (evt.event.getEnd() > evt.event.getStart()) {
            cur.push(evt);
        }
        const f = (1 - p);
        const t = 1;
        const step = (t - f) / (evt.concurrent.length + 1);
        evt.part1 = f;
        evt.part2 = f + step;
        let l = evt.part2;
        for (let i = 0; i < evt.concurrent.length; i++) {
            const e = evt.concurrent[i];
            e.part1 = l;
            l += step;
            e.part2 = l;
            e.placed = true;
        }
        evt.placed = true;
    }

    return parsed
}
