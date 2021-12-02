"use strict";

const LANG = document.documentElement.lang;
const LOCALE = LANG.startsWith("bar") ? "de" + LANG.substr(3) : LANG;

const MESSAGES = {
    "de-AT": {
        "Today": "Heute",
        "Loading...": "Laden...",
    },
    "de-DE": {
        "Today": "Heute",
        "Loading...": "Laden...",
    },
    "en-GB": {
        "Today": "Today",
        "Loading...": "Loading...",
    },
    "en-US": {
        "Today": "Today",
        "Loading...": "Loading...",
    },
    "bar-AT": {
        "Today": "Haid",
        "Loading...": "Låna...",
    },
};

function _(msgId) {
    return MESSAGES[LANG][msgId];
}
