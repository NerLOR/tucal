"use strict";

const LANG = document.documentElement.lang;
const LOCALE = LANG.startsWith("bar") ? "de" + LANG.substr(3) : LANG;

const MESSAGES = {
    "de-AT": {
        "Today": "Heute",
        "Loading...": "Laden...",
        "Error": "Fehler",
    },
    "de-DE": {
        "Today": "Heute",
        "Loading...": "Laden...",
        "Error": "Fehler",
    },
    "en-GB": {
        "Today": "Today",
        "Loading...": "Loading...",
        "Error": "Error",
    },
    "en-US": {
        "Today": "Today",
        "Loading...": "Loading...",
        "Error": "Error",
    },
    "bar-AT": {
        "Today": "Haid",
        "Loading...": "Låna...",
        "Error": "Föhla",
    },
};

function _(msgId) {
    return MESSAGES[LANG][msgId];
}
