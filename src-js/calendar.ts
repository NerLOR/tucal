"use strict";

const TIMEZONE = "Europe/Vienna";
const START_TIME = 7 * 60;  // 07:00 [min]
const END_TIME = 22 * 60;  // 22:00 [min]
const CACHE_EVENTS = 15;  // 15 [min]
const EVENT_PRE_LIVE = 15;  // 15 [min]
const LOOK_AHEAD = 8;  // 8 [week]


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
        if (!buttons[0] || !buttons[1] || !buttons[2]) throw new Error();
        buttons[0].addEventListener("click", (evt) => {
            this.now();
        });
        buttons[1].addEventListener("click", (evt) => {
            this.previous();
        });
        buttons[2].addEventListener("click", (evt) => {
            this.next();
        });
        document.addEventListener("keydown", (evt) => {
            const path = evt.composedPath();
            if (!path[0] || (<HTMLElement> path[0]).tagName !== 'BODY') return;
            switch (evt.code) {
                case 'ArrowLeft': this.previous(); break;
                case 'ArrowRight': this.next(); break;
                case 'Numpad0': this.now(); break;
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
            }, '', `/calendar/${this.subject}/${this.week.year}/W${this.week.week}/${this.eventId ?? ''}`);
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
                    const preStart = new Date(evt.start);
                    const evtElem = document.getElementById(`event-${evt.id}`);
                    preStart.setMinutes(preStart.getMinutes() - EVENT_PRE_LIVE);

                    if (evtElem !== null && dt >= evt.start && dt < evt.end) {
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
            const w = this.weeks[evt.getWeek().toString()];
            if (!w) throw new Error();
            w.events.push(evt);
        }

        if (weeks.includes(this.week.toString())) {
            this.reloadEvents();
        }
    }

    clearEvents(loading = false) {
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
        all_events.sort((a, b) => {
            const diff = a.start.valueOf() - b.start.valueOf();
            if (diff === 0) {
                return a.end.valueOf() - b.end.valueOf();
            }
            return diff;
        });

        const formatter = new Intl.DateTimeFormat('de-AT', {
            hour: "2-digit",
            minute: "2-digit",
        });

        const deadlines = [];
        const events: TucalEvent[][] = [[], [], [], [], [], [], []];
        for (const event of all_events) {
            const weekDay = (event.start.getDay() + 6) % 7;
            const day = events[weekDay];
            if (!day) throw new Error();

            if (event.start.getTime() === event.end.getTime()) {
                deadlines.push(event);
            } else {
                day.push(event);
            }
        }

        const thead = this.cal.getElementsByTagName("thead")[0];
        if (!thead) throw new Error();

        const theadTr = thead.getElementsByTagName("tr")[1];
        if (!theadTr) throw new Error();

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
            day.appendChild(el);
        }

        for (const day of events) {
            for (const eventData of placeDayEvents(day)) {
                const event = eventData.event;
                const start = event.start;
                const end = event.end;

                if (event.deleted) continue;

                const wrapper = this.cal.getElementsByClassName("event-wrapper")[0];
                if (!wrapper) throw new Error();

                const day = wrapper.getElementsByClassName("day")[(start.getDay() + 6) % 7];
                if (!day) throw new Error();

                const evt = document.createElement("div");
                evt.id = `event-${event.id}`;

                evt.classList.add("event");
                if (event.type) evt.classList.add(event.type);
                if (event.online) evt.classList.add("online");

                const startMinute = start.getHours() * 60 + start.getMinutes();
                const endMinute = end.getHours() * 60 + end.getMinutes();

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

                const startFmt = formatter.format(start);
                const endFmt = formatter.format(end);
                const course = event.getCourse();
                const room = event.getRoom();
                const ltLink = room && room.getLectureTubeLink() || null;

                let group = event.courseGroup;
                if (group === 'LVA') {
                    group = null;
                } else if (group !== null) {
                    group = group.replace('Gruppe Gruppe', 'Gruppe').replace('Gruppe Kohorte', 'Kohorte');
                }

                evt.innerHTML =
                    '<div class="pre"></div>' +
                    '<div class="post"></div>' +
                    (event.lecture_tube && ltLink ? `<a class="live" href="${ltLink}" target="_blank" title="LectureTube Livestream"><img src="/res/icons/lecturetube-live.png" alt="LectureTube"/></a>` : '') +
                    (event.zoom !== null ? `<a class="live" href="${event.zoom}" target="_blank" title="Zoom"><img src="/res/icons/zoom.png" alt="Zoom"/></a>` : '') +
                    `<div class="time">${startFmt}-${endFmt}</div>` +
                    `<div class="course"><span class="course">${course?.getName()}</span>` +
                    (room !== null ? ` - <span class="room">${room.getName()}</span>` : '') + '</div><div class="group">' +
                    (group !== null ? `<span class="group">${group}</span>` : '') + '</div>' +
                    (event.summary !== null ? `<div class="summary">${event.summary}</div>` : '');

                const evtMinutes = (end.valueOf() - start.valueOf()) / 60_000;
                const pre = <HTMLElement> evt.getElementsByClassName("pre")[0];
                const post = <HTMLElement> evt.getElementsByClassName("post")[0];
                if (!pre || !post) throw new Error();

                // TODO add planned_start/end_ts and real_start/end_ts
                pre.style.height =`${0 / evtMinutes * 100}%`;
                post.style.height = `${0 / evtMinutes * 100}%`;

                day.appendChild(evt);
            }
        }

        this.updateTime();
    }

    displayEventDetail() {
        const eventId = this.eventId;
        if (!this.week) throw new Error();
        if (!COURSE_DEF || ! ROOMS) throw new Error();

        this.clearEventDetail();
        if (eventId === null) return;

        const week = this.weeks[this.week.toString()];
        if (!week) throw new Error();

        const evt = week.events.find((evt) => evt.id === this.eventId);
        if (!evt) throw new Error();
        const course = evt.getCourse();
        const room = evt.getRoom();

        const courseName = course && (LOCALE.startsWith('de-') ? course.name_de : course.name_en);

        const div = document.createElement("div");
        div.classList.add("event-detail");

        let html = '';

        const ltLink = room && room.getLectureTubeLink() || null;
        if (evt.lecture_tube && ltLink) {
            html += `<a class="live" href="${ltLink}" target="_blank" title="LectureTube">` +
                `<img src="/res/icons/lecturetube-live.png" alt="LectureTube"/></a>`;
        }

        if (evt.zoom) {
            html += `<a class="live" href="${evt.zoom}" target="_blank" title="Zoom">` +
                `<img src="/res/icons/zoom.png" alt="Zoom"/></a>`;
        }

        if (course) {
            html += `<h2>` +
                `<span class="course-name">${course.getName()}</span> ` +
                `<span class="course-type">(${course.type})</span> ` +
                `<span class="course-nr">${course.getCourseNr()} (${evt.semester})</span>` +
                `</h2><h3>${courseName}</h3>`;
        } else {

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
        })

        html += `<h4>` +
            `<span class="time">${formatterTime.format(evt.start)}-${formatterTime.format(evt.end)}</span> ` +
            `<span class="day">(${formatterDay.format(evt.start)})</span>` +
            `</h4>`;

        if (room) {
            html += `<div><div>${_('Room')}:</div><div class="room">`;
            let name = room.name;
            if (room.suffix) {
                name += ` – ${room.suffix}`;
            }
            const codes = room.roomCodes.map((code) => code.substr(0, 2) + '&nbsp;' + code.substr(2, 2) + '&nbsp;' + code.substr(4));
            html += `<a href="https://tuw-maps.tuwien.ac.at/?q=${room.roomCodes[0]}" target="_blank">` +
                `<span class="room-name">${name}</span> <span class="room-codes">(${codes.join(', ')})</span></a>`;

            let building = '';
            const b = room.getBuilding();
            if (b) {
                if (b.name !== b.address) building += b.name;
                if (b.name !== b.address && b.suffix) building += ' – ';
                if (b.suffix) building += b.suffix;
                const hasB = building.length > 0;

                if (hasB) building += ' (';
                building += b.areaName;
                if (b.areaSuffix) building += ' – ' + b.areaSuffix;
                if (hasB) building += ')';

                let address = b.address ? `<br/><span class="address">${b.address}</span>` : '';
                html += `<br/><span class="building">${building}</span>${address}`;
            }

            html += '</div></div>';
        }

        if (evt.courseGroup && evt.courseGroup !== 'LVA') {
            let group = evt.courseGroup;
            while (group.startsWith('Gruppe ')) group = group.substr(7);
            html += `<div><div>${_('Group')}:</div><div>${group}</div></div>`;
        }

        if (evt.summary) {
            html += `<div><div>${_('Summary')}:</div><div>${evt.summary}</div></div>`
        }

        if (evt.desc) {
            html += `<div><div>${_('Description')}:</div><div>${evt.desc}</div></div>`;
        }

        html += '<hr/><button>&blacktriangledown;</button>';
        html += `<form class="save hidden">` +
            `<label><input type="checkbox" name="all-previous"/> ${_('Apply changes for all previous events')}</label>` +
            `<label><input type="checkbox" name="all-following"/> ${_('Apply changes for all following events')}</label>` +
            `<button>${_('Apply')}</button></form>`;

        div.innerHTML = html;

        const button = div.getElementsByTagName("button")[0];
        const form = div.getElementsByTagName("form")[0];
        if (!button || !form) throw new Error();

        button.addEventListener('click', (e) => {
            if (form.classList.contains('hidden')) {
                button.innerHTML = '&blacktriangle;';
                form.classList.remove('hidden');
            } else {
                button.innerHTML = '&blacktriangledown;';
                form.classList.add('hidden');
            }
        });
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            console.log(form);
            const data = {};
            api('/calendar/update', {'id': eventId}, data).then(() => {
                this.weeks = {};
                this.reloadEvents();
            });
        });

        this.cal.appendChild(div);
    }

    clearEventDetail() {
        const eventDetail = this.cal.getElementsByClassName("event-detail");
        while (eventDetail[0]) eventDetail[0].remove();
    }
}

interface TucalEventJSON {
    id: string,
    deleted: boolean | null,
    start: string,
    end: string,
    course: {
        nr: string,
        group: string,
        semester: string,
    },
    room_nr: number | null,
    data: {
        summary: string | null,
        desc: string | null,
        zoom: string | null,
        lt: boolean | null,
        url: string | null,
        type: string | null,
        online: boolean | null,
    },
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
        const start1 = evt1.event.start.getTime();
        const end1 = evt1.event.end.getTime();
        for (const evt2 of parsed) {
            if (evt2 === evt1) continue;
            const start2 = evt2.event.start.getTime();
            const end2 = evt2.event.end.getTime();

            if (Math.abs(start1 - start2) < hour) {
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
            if (p && p.event.end <= evt.event.start) {
                cur.splice(i);
            }
        }
        let p = Math.pow(0.875, cur.length);
        if (evt.event.end > evt.event.start) {
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
