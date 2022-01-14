"use strict";

const LANG = document.documentElement.lang;
const LANG_GROUP = LANG.split('-')[0]
const LOCALE = LANG.startsWith("bar") ? "de" + LANG.substr(3) : LANG;

const MESSAGES = {
    "de": {
        "Today": "Heute",
        "Loading...": "Laden...",
        "Error": "Fehler",
        "Room": "Raum",
        "Group": "Gruppe",
        "Summary": "Kurzinfo",
        "Description": "Beschreibung",
    },
    "en": {
        "Today": "Today",
        "Loading...": "Loading...",
        "Error": "Error",
        "Room": "Room",
        "Group": "Group",
        "Summary": "Summary",
        "Description": "Description",
    },
    "bar-AT": {
        "Today": "Haid",
        "Loading...": "Låna...",
        "Error": "Föhla",
        "Room": "Raum",
        "Group": "Gruppn",
        "Summary": "Kuazinfo",
        "Description": "Beschreibung",
    },
};

function _(msgId) {
    return MESSAGES[LANG] && MESSAGES[LANG][msgId] || MESSAGES[LANG_GROUP][msgId] || msgId;
}
