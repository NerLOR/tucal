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
        "Save": "Speichern",
        "Apply for all previous events": "Für alle vorhergehenden Termine übernehmen",
        "Apply for all following events": "Für alle nachfolgenden Termine übernehmen",
    },
    "en": {
        "Today": "Today",
        "Loading...": "Loading...",
        "Error": "Error",
        "Room": "Room",
        "Group": "Group",
        "Summary": "Summary",
        "Description": "Description",
        "Save": "Save",
        "Apply for all previous events": "Apply for all previous events",
        "Apply for all following events": "Apply for all following events",
    },
    "bar-AT": {
        "Today": "Haid",
        "Loading...": "Låna...",
        "Error": "Föhla",
        "Room": "Raum",
        "Group": "Gruppn",
        "Summary": "Kuazinfo",
        "Description": "Beschreibung",
        "Save": "Speichan",
        "Apply for all previous events": "Fia olle voahearign Teamine übanemma",
        "Apply for all following events": "Fia olle nochfoigendn Teamine übanemma",
    },
};

function _(msgId) {
    return MESSAGES[LANG] && MESSAGES[LANG][msgId] || MESSAGES[LANG_GROUP][msgId] || msgId;
}
