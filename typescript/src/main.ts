"use strict";

const STATUS: number = parseInt(document.documentElement.dataset['status'] || '0');

const _MNR: string | null = document.documentElement.dataset['mnr'] || null;
const MNR: string | null = (_MNR && _MNR.length > 0) ? _MNR : null;

const _USER_OPTS = document.getElementsByName("user-options")[0];
const USER_OPTS: {[index: string]: string} | null = _USER_OPTS && JSON.parse(_USER_OPTS.getAttribute("content") || 'null') || null;
const LT_PROVIDER: string = USER_OPTS && USER_OPTS['lt_provider'] || 'live-video-tuwien';

let COURSE_DEF: {[index: string]: CourseDef} | null = null;
let COURSES: {[index: string]: CourseDef} | null = null;
let BUILDINGS: {[index: string]: Building} | null = null;
let ROOMS: {[index: number]: Room} | null = null;
let CALENDAR: WeekSchedule | null = null;


initBrowserTheme();
initData();

window.addEventListener("DOMContentLoaded", () => {
    initNav();
    initJobs();
    initCopyLink();
    initUsernames();

    const path = window.location.pathname;
    if (STATUS === 200) {
        if (path.startsWith('/calendar/')) {
            initCalendar();
        } else if (path === '/courses/') {
            initCourseForms();
        }
    }
});

function initCalendar() {
    const main = document.getElementsByTagName("main")[0];
    if (!main) throw new Error();

    const uri = window.location.pathname;
    const parts = uri.split('/');
    if (!parts[1] || !parts[2] || !parts[3] || !parts[4]) throw new Error();

    const subject = parts[2];
    const year = parseInt(parts[3]);
    const week = parseInt(parts[4].substring(1));
    const eventId = (!parts[5] || parts[5].length === 0) ? null : parts[5];

    CALENDAR = new WeekSchedule(main, subject, eventId);
    /*CALENDAR.setCurrentEventCb((events) => {
        const navLive = document.getElementById("nav-live");
        const liveButtons = navLive.getElementsByClassName("live");
        for (const btn of liveButtons) btn.href = '';

        console.log(events);
        for (let i = 0, j = 0; i < events.length; i++) {
            const evt = events[i];
            if (evt.live && evt.liveUrl) {
                const btn = liveButtons[j++];
                btn.href = evt.liveUrl;
                btn.getElementsByTagName("span")[0].innerText = evt.courseShort || evt.courseNr;
            }
        }
    });*/
    CALENDAR.setWeek(new Week(year, week));
}

function initNav() {
    const userMenu = document.getElementById("user-menu");
    const home = document.getElementById("nav-home");
    if (!home) throw new Error();
    const menu = home.getElementsByTagName("a")[0];
    if (!menu) throw new Error();
    const nav = document.getElementsByTagName("nav")[0];
    if (!nav) throw new Error();
    const testElem = document.getElementById("nav-center");
    if (!testElem) throw new Error();

    if (userMenu) {
        const navUser = userMenu.getElementsByTagName("div")[0];
        if (!navUser) throw new Error();
        navUser.addEventListener("click", () => {
            if (userMenu.classList.contains("active")) {
                userMenu.classList.remove("active");
            } else {
                userMenu.classList.add("active");
            }
        });

        const form = document.forms.namedItem('logout');
        if (!form) throw new Error();

        const links = userMenu.getElementsByTagName("a");
        for (const a of links) {
            if (a.href.endsWith('/account/logout')) {
                a.removeAttribute("href");
                a.addEventListener("click", () => {
                    form.submit();
                });
            }
        }
    }

    menu.addEventListener("click", (evt) => {
        if (nav.classList.contains("active")) {
            nav.classList.remove("active");
            evt.preventDefault();
        } else if (window.getComputedStyle(testElem).display === 'none') {
            nav.classList.add("active");
            evt.preventDefault();
        }
    });

    window.addEventListener("click", (evt) => {
        const path = evt.composedPath();
        if (userMenu && !path.includes(userMenu)) {
            userMenu.classList.remove("active");
        }
        if (!path.includes(nav)) {
            nav.classList.remove("active");
        }
    });
}

function initJobs() {
    const jobs = document.getElementsByClassName("job-viewer");
    for (const job of jobs) {
        new Job(<HTMLElement> job);
    }
}

function initData() {
    api(`/tucal/rooms`).then((res) => {
        BUILDINGS = {};
        ROOMS = {};
        for (const building of res.data.buildings) {
            BUILDINGS[building['id']] = new Building(building);
        }
        for (const room of res.data.rooms) {
            ROOMS[room['nr']] = new Room(room);
        }
        if (CALENDAR) {
            CALENDAR.reloadEvents(true);
        }
    });
    if (MNR === null) return;
    api('/tucal/courses', {'mnr': MNR}).then((res) => {
        COURSES = {};
        COURSE_DEF = {};
        for (const course of res.data.personal) {
            COURSE_DEF[course['nr']] = new CourseDef(course);
            COURSES[course['nr']] = new CourseDef(course);
        }
        for (const course of res.data.friends) {
            COURSE_DEF[course['nr']] = new CourseDef(course);
        }
        if (CALENDAR) {
            CALENDAR.reloadEvents(true);
        }
    });
}

function initCourseForms() {
    const forms = document.getElementsByTagName("form");
    for (const form of forms) {
        if (!form['ignore']) continue;
        const dates = form.getElementsByClassName("ignore-dates")[0];
        const button = form.getElementsByTagName("button")[0];
        if (!dates || !button) throw new Error();

        button.style.display = 'none';

        form.addEventListener("input", () => {
            if (form['ignore'].value === "partly") {
                dates.classList.add("show");
            } else {
                dates.classList.remove("show");
            }

            fetch('/courses/update', {
                method: 'POST',
                redirect: 'manual',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                },
                body: `ignore=${form['ignore'].value}&ignore-from=${form['ignore-from'].value}&ignore-until=${form['ignore-until'].value}&course=${form['course'].value}`,
            }).then();
        });
    }
}

function initBrowserTheme() {
    const classes = document.documentElement.classList;
    if (classes.contains("theme-browser")) {
        const media = window.matchMedia('(prefers-color-scheme: dark)');
        const mediaHandler = (evt: MediaQueryListEvent) => {
            if (evt.matches) {
                classes.remove("theme-light");
                classes.add("theme-dark");
            } else {
                classes.remove("theme-dark");
                classes.add("theme-light");
            }
        }
        media.addEventListener('change', mediaHandler);
        mediaHandler(new MediaQueryListEvent('', media));
    }
}

function initCopyLink() {
    const links = document.getElementsByTagName("a");
    for (const a of links) {
        if (!a.classList.contains("copy-link")) continue;
        const link = a.href;
        a.innerText = _("Copy link");

        a.addEventListener('click', (evt) => {
            evt.preventDefault();
            navigator.clipboard.writeText(link).then();
        });
    }
}

function initUsernames() {
    const accounts = document.getElementsByClassName("account");
    for (const a of accounts) {
        if (a.tagName !== "A") continue;
        const name = a.getElementsByClassName("name")[0];
        const mnr = parseInt((<HTMLElement> a).dataset['mnr'] || '');
        const username = (<HTMLElement> a).dataset['username'] || null;
        if (!name || !mnr) continue;

        // FIXME Firefox: click into field does not align cursor

        if (name.getAttribute('contenteditable')) {
            a.addEventListener('click', (evt) => {
                if (evt.composedPath().includes(name))
                    evt.preventDefault();
            });
        }

        let timer: number | null = null;
        name.addEventListener('input', () => {
            const oldText = name.innerHTML;
            const newText = oldText.replace(/<[^>]*>/g, '');
            if (newText.length !== oldText.length)
                name.innerHTML = newText;

            if (oldText.includes('<br/>') || oldText.includes('<br>')) {
                return;
            }

            const doc = new DOMParser().parseFromString(newText, "text/html");
            let value = doc.documentElement.textContent;
            if (value === '' || value === username)
                value = null;

            if (timer) clearTimeout(timer)
            timer = setTimeout(() => {
                timer = null;
                api('/tucal/friends/nickname', null, {'mnr': mnr, 'nickname': value}).then();
            }, 500);
        });
    }
}

async function api(endpoint: string,
                   urlData: {[index: string]: any} | null = null,
                   data: {[index: string]: any} | null = null) {
    let info = {};
    if (data !== null) {
        info = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify(data),
        }
    }

    let suffix = '';
    if (urlData !== null) {
        const query = Object.keys(urlData).map((k) =>
            encodeURIComponent(k) + '=' + encodeURIComponent(urlData[k] || '')
        ).join('&');
        suffix = (endpoint.includes('?') ? '&' : '?' ) + query;
    }

    const req = await fetch(`/api${endpoint}${suffix}`, info);
    const json = await req.json();

    if (json.message !== null) {
        if (json.status === "success") {
            console.warn(`API: ${json.message}`);
        } else {
            console.error(`API: ${json.message}`);
        }
    }

    if (req.status === 200 && json.status === "success") {
        return json;
    } else {
        throw new Error(json.message);
    }
}

function sleep(ms: number) {
    return new Promise(resolve => setTimeout(resolve, ms))
}

function detectSwipe(elem: HTMLElement, cb: Function) {
    const MIN_X = 50;
    const MIN_Y = 50;
    const MAX_X = 400;
    const MAX_Y = 400;
    const MAX_DIFF = 25;

    let dir: string | null = null;
    let sx: number = 0;
    let sy: number = 0;
    let lx: number | null = null;
    let ly: number | null = null;
    let ex: number = 0;
    let ey: number = 0;

    elem.addEventListener('touchstart', (evt) => {
        if (evt.touches.length !== 1) {
            dir = null;
            return;
        }

        const t = evt.touches[0];
        if (!t) return;
        sx = t.clientX;
        sy = t.clientY;
    });

    elem.addEventListener('touchmove', (evt) => {
        if (evt.touches.length !== 1) {
            dir = null;
            return;
        }

        const t = evt.touches[0];
        if (!t) return;
        ex = t.clientX;
        ey = t.clientY;

        if (lx && ly) {
            switch (dir) {
                case 'left':
                    if (ex < lx) dir = 'invalid'; break;
                case 'right':
                    if (ex > lx) dir ='invalid'; break;
                case 'down':
                    if (ey < ly) dir = 'invalid'; break;
                case 'up':
                    if (ey > ly) dir = 'invalid'; break;
                default: break;
            }
        }

        if (dir === 'left' || dir === 'right') {
            if (Math.abs(ey - sy) > MAX_DIFF) {
                dir = 'invalid';
            }
        } else if (dir === 'down' || dir === 'up') {
            if (Math.abs(ex - sx) > MAX_DIFF) {
                dir = 'invalid';
            }
        }

        if (Math.abs(ey - sy) < MIN_Y && Math.abs(ex - sx) >= MIN_X && Math.abs(ex - sx) <= MAX_X) {
            if (ex > sx) {
                if (dir && dir !== 'left') dir = 'invalid';
                else dir = 'left'
            } else {
                if (dir && dir !== 'right') dir = 'invalid';
                else dir = 'right';
            }
        } else if (Math.abs(ex - sx) < MIN_X && Math.abs(ey - sy) >= MIN_Y && Math.abs(ey - sy) <= MAX_Y) {
            if (ey > sy) {
                if (dir && dir !== 'down') dir = 'invalid';
                else dir = 'down';
            } else {
                if (dir && dir !== 'up') dir = 'invalid';
                dir = 'up';
            }
        }

        lx = ex;
        ly = ey;
    });

    elem.addEventListener('touchend', () => {
        if (dir && dir !== 'invalid') cb(dir);
        dir = null;
        lx = null;
        ly = null;
    });
}

function isoWeekFromDate(date: Date): Week {
    const dayOfWeek = (date.getDay() + 6) % 7;
    const refThursday = new Date(date);
    refThursday.setDate(refThursday.getDate() - dayOfWeek + 3);

    const firstThursday = new Date(refThursday.getFullYear(), 0, 1);
    if (firstThursday.getDay() !== 4) {
        firstThursday.setMonth(0, 1 + (4 - firstThursday.getDay() + 7) % 7);
    }

    return new Week(
        refThursday.getFullYear(),
        1 + Math.round((refThursday.valueOf() - firstThursday.valueOf()) / 604_800_000)
    );
}

function isoWeekToDate(year: number, week: number): Date {
    const date = new Date(year, 0, 1);
    if (date.getDay() !== 4) {
        date.setMonth(0, 1 + (4 - date.getDay() + 7) % 7);
    }

    const dayOfWeek = (date.getDay() + 6) % 7;
    date.setDate(date.getDate() - dayOfWeek + (week - 1) * 7);
    return date;
}

function asTimezone(date: Date, timezone: string): Date {
    const updated = new Date(date.toLocaleString('en-US', {
        timeZone: timezone,
    }));
    const diff = date.getTime() - updated.getTime();
    return new Date(date.getTime() - diff);
}
