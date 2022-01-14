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

    return new Week(refThursday.getFullYear(), 1 + Math.round((refThursday - firstThursday) / 604800000));
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
        return isoWeekFromDate(date);
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
        return isoWeekFromDate(ref);
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
    cal;
    week = null;
    subject;
    eventId;
    timer = null;
    lastReload = null;
    weeks = {};
    currentEvents = [];
    currentEventCb = null;

    constructor(element, subject, eventId = null) {
        this.subject = subject;
        this.eventId = eventId;
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
        document.addEventListener("keydown", (evt) => {
            if (evt.composedPath()[0].tagName !== 'BODY') return;
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
        window.addEventListener("click", (evt) => {
            const path = evt.composedPath();
            const divs = document.getElementsByClassName("event-detail");
            const navs = document.getElementsByTagName("nav");
            if ((divs.length > 0 && path.includes(divs[0])) || (navs.length > 0 && path.includes(navs[0]))) {
                return;
            }
            this.setEventId(null);
        });
    }

    setWeek(week, keep = false) {
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
            }, '', `/calendar/${this.subject}/${this.week.year}/W${this.week.week}/${this.eventId ?? ''}`);
        }

        this.timer = setInterval(() => {
            this.updateTime();
            this.reloadEvents();
        }, 1000);
    }

    setEventId(eventId) {
        if (eventId === this.eventId) return;
        this.eventId = eventId;
        history.replaceState({
            year: this.week.year,
            week: this.week.week,
        }, '', `/calendar/${this.subject}/${this.week.year}/W${this.week.week}/${this.eventId ?? ''}`);
        if (eventId === null) {
            this.clearEventDetail();
        } else {
            this.displayEventDetail(eventId);
        }
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

    reloadEvents(forceRedraw = false) {
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
        } else if (forceRedraw || this.lastReload === null || this.lastReload !== this.weeks[w].date)  {
            this.clearEvents();
            const week = this.weeks[w];
            this.lastReload = week.date;
            this.drawEvents(week.events);
            this.displayEventDetail();
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
        const json = await api(`/calendar/calendar?subject=${this.subject}&${start}&${end}`)

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
            const diff = a.start - b.start;
            if (diff === 0) {
                return a.end - b.end;
            }
            return diff;
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

                const wrapper = this.cal.getElementsByClassName("event-wrapper")[0];
                const day = wrapper.getElementsByClassName("day")[(start.getDay() + 6) % 7];
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
                        if (elem.tagName === 'A') return;
                    }
                    evt.stopImmediatePropagation();
                    this.setEventId(event.id);
                });

                const startFmt = formatter.format(start);
                const endFmt = formatter.format(end);
                const course = event.course && getCourseName(event.course.nr) || null;
                const room = event.room_nr && getRoomName(event.room_nr) || null;
                const ltLink = event.room_nr && getLectureTubeLink(event.room_nr) || null;

                let group = event.course.group;
                if (group === 'LVA') {
                    group = null;
                } else if (group !== null) {
                    group = group.replace('Gruppe Gruppe', 'Gruppe').replace('Gruppe Kohorte', 'Kohorte');
                }

                evt.innerHTML =
                    '<div class="pre"></div>' +
                    '<div class="post"></div>' +
                    (event.lecture_tube && ltLink ? `<a href="${ltLink}" target="_blank" class="live" title="LectureTube Livestream"><img src="/res/icons/lecturetube-live.png" alt="LectureTube"/></a>` : '') +
                    (event.zoom !== null ? `<a href="${event.zoom}" target="_blank" class="live" title="Zoom"><img src="/res/icons/zoom.png" alt="Zoom"/></a>` : '') +
                    `<div class="time">${startFmt}-${endFmt}</div>` +
                    `<div><span class="course">${course}</span>` +
                    (room !== null ? ` - <span class="room">${room}</span>` : '') + '</div><div>' +
                    (group !== null ? `<span class="group">${group}</span>` : '') + '</div>' +
                    (event.summary !== null ? `<div class="summary">${event.summary}</div>` : '');

                const evtMinutes = (end - start) / 60_000;
                const pre = evt.getElementsByClassName("pre")[0];
                const post = evt.getElementsByClassName("post")[0];
                // TODO add planned_start/end_ts and real_start/end_ts
                pre.style.height =`${0 / evtMinutes * 100}%`;
                post.style.height = `${0 / evtMinutes * 100}%`;

                day.appendChild(evt);
            }
        }

        this.updateTime();
    }

    displayEventDetail() {
        this.clearEventDetail();
        if (this.eventId === null) return;

        const evt = this.weeks[this.week.toString()].events.find((evt) => evt.id === this.eventId);
        const course = COURSE_DEF[evt.course.nr];
        const room = ROOMS[evt.room_nr];
        const courseName = LOCALE.startsWith('de-') ? course.name_de : course.name_en;

        const div = document.createElement("div");
        div.classList.add("event-detail");

        let html = '';

        if (course) {
            html += `<h2>` +
                `<span class="course-name">${getCourseName(course.nr)}</span> ` +
                `<span class="course-type">(${course.type})</span> ` +
                `<span class="course-nr">${course.nr.substr(0, 3)}.${course.nr.substr(3)} (${evt.course.semester})</span>` +
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
            html += '<div><div>Raum:</div><div class="room">';
            let name = room.name;
            if (room.suffix) {
                name += ` – ${room.suffix}`;
            }
            const codes = room.room_codes.map((code) => code.substr(0, 2) + '&nbsp;' + code.substr(2, 2) + '&nbsp;' + code.substr(4));
            html += `<a href="https://tuw-maps.tuwien.ac.at/?q=${room.room_codes[0]}" target="_blank">` +
                `<span class="room-name">${name}</span> <span class="room-codes">(${codes.join(', ')})</span></a>`;

            let building = '';
            if (room.building.name) {
                if (room.building.name !== room.building.address) building += room.building.name;
                if (room.building.name !== room.building.address && room.building.suffix) building += ' – ';
                if (room.building.suffix) building += room.building.suffix;
            }
            const hasB = building.length > 0;

            if (hasB) building += ' (';
            building += room.building.area_name;
            if (room.building.area_suffix) building += ' – ' + room.building.area_suffix;
            if (hasB) building += ')';

            let address = room.building.address ? `<br/><span class="address">${room.building.address}</span>` : '';
            html += `<br/><span class="building">${building}</span>${address}`;
            html += '</div></div>';
        }

        if (evt.course.group !== 'LVA') {
            html += `<div><div>Gruppe:</div><div>${evt.course.group}</div></div>`;
        }

        if (evt.summary) {
            html += `<div><div>Beschreibung: </div><div>${evt.summary}</div></div>`
        }

        div.innerHTML = html;

        this.cal.appendChild(div);
    }

    clearEventDetail() {
        const eventDetail = this.cal.getElementsByClassName("event-detail");
        while (eventDetail.length > 0) eventDetail[0].remove();
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
    room_nr;
    zoom;
    lecture_tube;
    url;
    type;
    online;

    constructor(json) {
        this.id = json.id;
        this.start = asTimezone(new Date(Date.parse(json.start)), TIMEZONE);
        this.end = asTimezone(new Date(Date.parse(json.end)), TIMEZONE);
        this.course = json.course;
        this.semester = null;
        this.summary = json.data.summary;
        this.desc = json.data.desc;
        this.room_nr = json.room_nr;
        this.zoom = json.data.zoom;
        this.lecture_tube = json.data.lt;
        this.url = json.data.url;
        this.type = json.data.type;
        this.online = json.data.online;
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

function placeDayEvents(dayEvents) {
    const parsed = [];
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
            if (cur[i].event.end <= evt.event.start) {
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
