"use strict";

window.addEventListener("DOMContentLoaded", () => {
    const status = parseInt(document.title.split(' ')[0]) || 200;

    initNav();

    if (window.location.pathname.startsWith('/calendar/') && status === 200) {
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

    const cal = new WeekSchedule(subject, main);
    cal.setCurrentEventCb((events) => {
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
    cal.setWeek(new Week(year, week));
}

function initNav() {
    const userMenu = document.getElementById("user-menu");
    const menu = null;

    if (userMenu) {
        userMenu.addEventListener("click", (evt) => {
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

    window.addEventListener("click", (evt) => {
        if (userMenu && !evt.composedPath().includes(userMenu)) {
            userMenu.classList.remove("active");
        }
        if (menu && !evt.composedPath().includes(menu)) {
            menu.classList.remove("menu-active");
        }
    });
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
}
