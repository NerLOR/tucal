"use strict";

const TIMEZONE = "Europe/Vienna";
const START_TIME = 7 * 60;  // 07:00 [min]
const END_TIME = 22 * 60;  // 22:00 [min]
const CACHE_EVENTS = 15;  // 15 [min]
const LOOK_AHEAD = 8;  // 8 [week]

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
        const special = [];
        const events: TucalEvent[][] = [[], [], [], [], [], [], []];
        for (const event of all_events) {
            const weekDay = (event.start.getDay() + 6) % 7;
            const day = events[weekDay];
            if (!day) throw new Error();

            if (event.start.getTime() === event.end.getTime()) {
                deadlines.push(event);
            } else if (event.end.valueOf() - event.start.valueOf() > 43_200_000) {
                special.push(event);
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
            if (deadline.type) el.classList.add(deadline.type);

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
                if (event.mode === 'online_only') evt.classList.add("online");
                if (event.status === 'cancelled') evt.classList.add("cancelled");

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

                let cGroup = event.courseGroup;
                if (cGroup === 'LVA') {
                    cGroup = null;
                } else if (cGroup !== null) {
                    cGroup = cGroup.replace('Gruppe Gruppe', 'Gruppe').replace('Gruppe Kohorte', 'Kohorte');
                }

                evt.innerHTML =
                    '<div class="pre"></div>' +
                    '<div class="post"></div>' +
                    (event.lecture_tube && ltLink ? `<a class="live" href="${ltLink}" target="_blank" title="LectureTube Livestream"><img src="/res/icons/lecturetube-live.png" alt="LectureTube"/></a>` : '') +
                    (event.zoom !== null ? `<a class="live" target="_blank" title="Zoom"><img src="/res/icons/zoom.png" alt="Zoom"/></a>` : '') +
                    `<div class="time">${startFmt}-${endFmt}</div>` +
                    `<div class="course"><span class="course">${course?.getName() || event.groupName}</span>` +
                    (room !== null ? ` - <span class="room">${room.getName()}</span>` : '') + '</div><div class="group">' +
                    (cGroup !== null ? `<span class="group">${cGroup}</span>` : '') + '</div>' +
                    (event.summary !== null ? `<div class="summary"></div>` : '');

                const aLive = evt.getElementsByClassName('live')[0];
                if (aLive && event.zoom) aLive.setAttribute('href', event.zoom);

                const divSummary = <HTMLElement> evt.getElementsByClassName('summary')[0];
                if (divSummary && event.summary !== null) divSummary.innerText = event.summary;

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

        this.clearEventDetail();
        if (eventId === null) return;

        const week = this.weeks[this.week.toString()];
        if (!week) throw new Error();

        const evt = week.events.find((evt) => evt.id === this.eventId);
        if (!evt) throw new Error();
        const course = evt.getCourse();
        const room = evt.getRoom();

        const courseName = course && (LOCALE_GROUP === 'de' ? course.name_de : course.name_en);

        const div = document.createElement("div");
        div.classList.add("event-detail");

        let html = '';

        const ltLink = room && room.getLectureTubeLink() || null;
        if (evt.lecture_tube && ltLink) {
            html += `<a class="live" href="${ltLink}" target="_blank" title="LectureTube">` +
                `<img src="/res/icons/lecturetube-live.png" alt="LectureTube"/></a>`;
        }

        if (evt.zoom) {
            html += `<a class="live" target="_blank" title="Zoom"><img src="/res/icons/zoom.png" alt="Zoom"/></a>`;
        }

        if (course) {
            html += `<h2><a href="/courses/#${course.nr}-${course.semester}">` +
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
        })

        html += `<h4>` +
            `<span class="time">${formatterTime.format(evt.start)}-${formatterTime.format(evt.end)}</span> ` +
            `<span class="day">(${formatterDay.format(evt.start)})</span>`;

        if (this.subject === MNR && evt.tissUrl) {
            html += `<a class="link" href="${evt.tissUrl}" target="_blank">TISS</a>`;
        }
        if (this.subject === MNR && evt.tuwelUrl) {
            html += `<a class="link" href="${evt.tuwelUrl}" target="_blank">TUWEL</a>`;
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

        html += '<hr/><div class="form-pre hidden">';

        html += `<div class="container"><div>${_('Live')}:</div><div>` +
            `<label class="radio"><input type="radio" name="live" value="false" checked/> ${_('Not live')}</label>` +
            `<label class="radio"><input type="radio" name="live" value="lt"/> LectureTube</label>` +
            `<label class="radio"><input type="radio" name="live" value="zoom"/> Zoom</label>` +
            `<div class="url hidden"><input type="url" name="live-url" placeholder="URL" class="line" required/></div>` +
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

        html += `<div class="container"><div>${_('Summary')}:</div><div>` +
            `<input type="text" name="summary" class="line" placeholder="${_('Summary')}"/>` +
            `</div></div>`;

        html += '</div><hr class="form-pre hidden"/><button type="button">&blacktriangledown;</button>' +
            `<div class="form-save hidden">` +
            `<label><input type="checkbox" name="all-previous"/> ${_('Apply changes for all previous events')}</label>` +
            `<label><input type="checkbox" name="all-following"/> ${_('Apply changes for all following events')}</label>` +
            `<button type="submit">${_('Apply')}</button></div>`;

        html += '</form>';

        div.innerHTML = html;

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

        const live = form['live'];
        const liveUrl = form['live-url'];
        const liveUrlDiv = liveUrl.parentElement;
        const roomSelect = form['room'];
        const summary = form['summary'];
        const status = form['status'];
        const mode = form['mode'];
        let manual = false;

        if (ROOMS) {
            for (const roomNr in ROOMS) {
                const r = ROOMS[roomNr];
                if (!r) continue;
                const opt = document.createElement("option");
                opt.innerText = `${r.getNameLong()} (${r.getCodeFormat()})`;
                opt.value = `${r.nr}`;
                roomSelect.appendChild(opt);
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

        const hasLiveChanged = (): boolean => {
            return (evt.zoom && live.value !== 'zoom') ||
                (evt.lecture_tube && live.value !== 'lt') ||
                (!evt.zoom && !evt.lecture_tube && live.value !== 'false');
        }

        const hasLiveUrlChanged = (): boolean => {
            return evt.zoom && (evt.zoom !== liveUrl.value) || false;
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

        const hasChanged = (): boolean => {
            return hasLiveChanged() ||
                hasLiveUrlChanged() ||
                hasRoomChanged() ||
                hasStatusChanged() ||
                hasModeChanged() ||
                hasSummaryChanged();
        }

        const onChange = () => {
            // disable LectureTube
            if (roomSelect.value && ROOMS) {
                const room = ROOMS[parseInt(roomSelect.value)];
                live[1].disabled = (!room || !room.ltName);
            } else {
                live[1].disabled = true;
            }

            if (live[1].disabled && live.value === 'lt') {
                live.value = 'false';
            }

            if (live.value === 'zoom') {
                if (liveUrlDiv.classList.contains('hidden')) liveUrlDiv.classList.remove('hidden');
                liveUrl.required = 'required';
            } else {
                if (!liveUrlDiv.classList.contains('hidden')) liveUrlDiv.classList.add('hidden');
                liveUrl.required = undefined;
            }

            if (hasChanged() && manual) {
                formDiv.classList.remove('hidden');
            } else {
                formDiv.classList.add('hidden');
            }

            submitButton.disabled = !hasChanged();
        }

        if (evt.zoom) {
            live.value = 'zoom';
            liveUrl.value = evt.zoom;
        } else if (evt.lecture_tube) {
            live.value = 'lt';
        } else {
            form['live'].value = 'false';
        }

        if (room) roomSelect.value = `${room.nr}`;
        if (evt.summary) summary.value = evt.summary;
        if (evt.status) status.value = evt.status;
        if (evt.mode) mode.value = evt.mode.replace(/_/g, '-');

        form.addEventListener('input', onChange);
        onChange();

        form.addEventListener('submit', (e) => {
            e.preventDefault();

            const urlData: {[index: string]: any} = {id: eventId};
            if (form['all-previous'].checked) urlData['previous'] = 'true';
            if (form['all-following'].checked) urlData['following'] = 'true';

            const data: {[index: string]: any} = {};

            if (hasLiveChanged() || hasLiveUrlChanged()) {
                if (live.value === 'lt') {
                    data['lt'] = true;
                    data['zoom'] = null;
                } else if (live.value === 'zoom') {
                    data['lt'] = false;
                    data['zoom'] = liveUrl.value.trim();
                } else {
                    data['lt'] = false;
                    data['zoom'] = null;
                }
            }

            if (hasStatusChanged()) {
                data['status'] = (status.value !== 'unknown') ? status.value : null;
            }

            if (hasModeChanged()) {
                data['mode'] = (mode.value !== 'unknown') ? mode.value.replace(/-/g, '_') : null;
            }

            if (hasSummaryChanged()) {
                data['summary'] = (summary.value !== '') ? summary.value.trim() : null;
            }

            api('/calendar/update', urlData, {'user': data}).then(() => {
                // wait for event merger to update events
                sleep(1000).then(() => {
                    if (urlData['previous'] || urlData['following']) {
                        this.weeks = {};
                    } else if (this.week) {
                        delete this.weeks[this.week.toString()];
                    }
                    this.reloadEvents();
                });
            });
        });

        this.cal.appendChild(div);
    }

    clearEventDetail() {
        const eventDetail = this.cal.getElementsByClassName("event-detail");
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
        const start1 = evt1.event.start.getTime();

        for (const evt2 of parsed) {
            if (evt2 === evt1) continue;
            const start2 = evt2.event.start.getTime();

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
