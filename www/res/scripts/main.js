"use strict";

const STATUS = parseInt(document.documentElement.getAttribute("data-status"));
const MNR = (document.documentElement.getAttribute("data-mnr").length > 0) ? document.documentElement.getAttribute("data-mnr") : null;

let COURSE_DEF = null;
let COURSES = null;
let ROOMS = null;
let CALENDAR = null;


initData();

window.addEventListener("DOMContentLoaded", () => {
    initNav();
    initJobs();

    if (window.location.pathname.startsWith('/calendar/') && STATUS === 200) {
        initCalendar();
    }
});

function initCalendar() {
    const main = document.getElementsByTagName("main")[0];

    const uri = window.location.pathname;
    const parts = uri.split('/');

    const subject = parts[2];
    const year = parseInt(parts[3]);
    const week = parseInt(parts[4].substr(1));

    CALENDAR = new WeekSchedule(subject, main);
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
        if (userMenu && !evt.composedPath().includes(userMenu)) {
            userMenu.classList.remove("active");
        }
        if (!evt.composedPath().includes(nav)) {
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

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
}
