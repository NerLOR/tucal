"use strict";

let LOCALE;

window.addEventListener("DOMContentLoaded", () => {
    LOCALE = document.documentElement.lang;
    if (LOCALE.startsWith('bar')) {
        LOCALE = 'de' + LOCALE.substr(3);
    }

    const status = parseInt(document.title.split(' ')[0]) || 200;
    if (window.location.pathname.startsWith('/calendar/') && status === 200) {
        const uri = window.location.pathname;
        const parts = uri.split('/');
        const cal = new WeekSchedule(parts[2], document.getElementsByTagName("main")[0]);
        cal.setWeek(new Week(parseInt(parts[3]), parseInt(parts[4].substr(1))));
    }
});

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
}
