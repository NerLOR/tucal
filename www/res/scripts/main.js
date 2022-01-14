"use strict";

const STATUS = parseInt(document.documentElement.getAttribute("data-status"));
const MNR = (document.documentElement.getAttribute("data-mnr").length > 0) ? document.documentElement.getAttribute("data-mnr") : null;
const USER_OPTS = JSON.parse(document.getElementsByName("user-options")[0].getAttribute("content"));
const LT_PROVIDER = USER_OPTS['lt_provider'] || 'live-video-tuwien';

let COURSE_DEF = null;
let COURSES = null;
let ROOMS = null;
let CALENDAR = null;


initBrowserTheme();
initData();

window.addEventListener("DOMContentLoaded", () => {
    initNav();
    initJobs();

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

    const uri = window.location.pathname;
    const parts = uri.split('/');

    const subject = parts[2];
    const year = parseInt(parts[3]);
    const week = parseInt(parts[4].substr(1));
    const eventId = parts[5].length === 0 ? null : parts[5];

    CALENDAR = new WeekSchedule(main, subject, eventId);
    CALENDAR.setCurrentEventCb((events) => {
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
    });
    CALENDAR.setWeek(new Week(year, week));
}

function initNav() {
    const userMenu = document.getElementById("user-menu");
    const menu = document.getElementById("nav-home").getElementsByTagName("a")[0];
    const nav = document.getElementsByTagName("nav")[0];
    //const testElem = document.getElementById("nav-search").getElementsByTagName("form")[0];
    const testElem = document.getElementById("nav-live");

    if (userMenu) {
        const navUser = userMenu.getElementsByTagName("div")[0];
        navUser.addEventListener("click", (evt) => {
            if (userMenu.classList.contains("active")) {
                userMenu.classList.remove("active");
            } else {
                userMenu.classList.add("active");
            }
        });

        const form = document.forms.logout;
        const links = userMenu.getElementsByTagName("a");
        for (const a of links) {
            if (a.href.endsWith('/account/logout')) {
                a.removeAttribute("href");
                a.addEventListener("click", (evt) => {
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
        new Job(job);
    }
}

function initData() {
    api(`/tucal/rooms`).then((res) => {
        ROOMS = {};
        for (const room of res.data.rooms) {
            ROOMS[room['nr']] = room;
        }
        if (CALENDAR) {
            CALENDAR.reloadEvents(true);
        }
    });
    if (MNR === null) return;
    api(`/tucal/courses?mnr=${MNR}`).then((res) => {
        COURSES = res.data.personal;
        COURSE_DEF = {};
        for (const course of COURSES) {
            COURSE_DEF[course['nr']] = {...course};
            delete COURSE_DEF[course['nr']].semester;
        }
        for (const course of res.data.friends) {
            COURSE_DEF[course['nr']] = {...course};
            delete COURSE_DEF[course['nr']].semester;
        }
        if (CALENDAR) {
            CALENDAR.reloadEvents(true);
        }
    });
}

function initCourseForms() {
    const forms = document.getElementsByTagName("form");
    for (const form of forms) {
        if (!form.ignore) continue;
        const dates = form.getElementsByClassName("ignore-dates")[0];
        const button = form.getElementsByTagName("button")[0];
        button.style.display = 'none';

        form.addEventListener("input", (evt) => {
            if (form.ignore.value === "partly") {
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
                body: `ignore=${form.ignore.value}&ignore-from=${form['ignore-from'].value}&ignore-until=${form['ignore-until'].value}&course=${form.course.value}`,
            }).then();
        });
    }
}

function initBrowserTheme() {
    const classes = document.documentElement.classList;
    if (classes.contains("theme-browser")) {
        const media = window.matchMedia('(prefers-color-scheme: dark)');
        const mediaHandler = (evt) => {
            if (evt.matches) {
                classes.remove("theme-light");
                classes.add("theme-dark");
            } else {
                classes.remove("theme-dark");
                classes.add("theme-light");
            }
        }
        media.addEventListener('change', mediaHandler);
        mediaHandler(media);
    }
}

async function api(endpoint, data = null) {
    let info = {};
    if (data !== null) {
        info = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify(data)
        }
    }

    const req = await fetch(`/api${endpoint}`, info);
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

function getCourseName(courseNr) {
    const fallback = courseNr.slice(0, 3) + '.' + courseNr.slice(3);
    if (COURSE_DEF === null) return fallback;

    const course = COURSE_DEF[courseNr];
    if (!course) return fallback;

    return course.acronym_1 || course.acronym_2 || course.short || course.name_de;
}

function getRoomName(roomNr) {
    const fallback = `#${roomNr}`;
    if (ROOMS === null) return fallback

    const room = ROOMS[roomNr];
    return room && (room.name_short || room.name) || fallback;
}

function getRoomNameLong(roomNr) {
    const fallback = `#${roomNr}`;
    if (ROOMS === null) return fallback

    const room = ROOMS[roomNr];
    if (!room) return fallback;

    let str = room.name;
    if (room.suffix) str += ' ' + room.suffix;
    if (room.alt_name) str += ' (' + room.alt_name + ')';
    return str;
}

function getLectureTubeLink(room_nr) {
    const room = ROOMS[room_nr];
    if (!room || !room.lt_room_code || !room.lt_name) return null;

    switch (LT_PROVIDER) {
        case 'hs-streamer': return `https://hs-streamer.fsbu.at/?hs=${room.lt_room_code}`;
        case 'live-video-tuwien': return `https://live.video.tuwien.ac.at/room/${room.lt_room_code.toLowerCase()}/player.html`;
        default: throw new Error(`Unknown LectureTube provider '${LT_PROVIDER}'`);
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
}

function detectSwipe(elem, cb) {
    const MIN_X = 30;
    const MIN_Y = 30;
    const MAX_X = 400;
    const MAX_Y = 400;

    const swipe = {
        start_x: null,
        start_y: null,
        end_x: null,
        end_y: null,
    };

    elem.addEventListener('touchstart', (evt) => {
        const t = evt.touches[0];
        swipe.start_x = t.screenX;
        swipe.start_y = t.screenY;
    });

    elem.addEventListener('touchmove', (evt) => {
        const t = evt.touches[0];
        swipe.end_x = t.screenX;
        swipe.end_y = t.screenY;
    });

    elem.addEventListener('touchend', (evt) => {
        const sx = swipe.start_x;
        const ex = swipe.end_x;
        const sy = swipe.start_y;
        const ey = swipe.end_y;

        if (sx === null || ex === null || sy === null || ey === null) return;

        if (Math.abs(ey - sy) < MIN_Y && Math.abs(ex - sx) >= MIN_X && Math.abs(ex - sx) <= MAX_X) {
            if (ex > sx) cb('left');
            else cb('right');
        } else if (Math.abs(ex - sx) < MIN_X && Math.abs(ey - sy) >= MIN_Y && Math.abs(ey - sy) <= MAX_Y) {
            if (ey > sy) cb('down');
            else cb('up');
        }

        swipe.start_x = null;
        swipe.start_y = null;
        swipe.end_x = null;
        swipe.end_y = null;
    });
}
