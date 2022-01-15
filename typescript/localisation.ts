"use strict";

const LANG: string = document.documentElement.lang;
const LANG_GROUP: string = LANG.split("-")[0] || "de";
const LOCALE: string = LANG.startsWith("bar") ? "de" + LANG.substr(3) : LANG;

const MESSAGES: {readonly [index: string]: {readonly [index: string]: string}} = {
    "de": {
        "Today": "Heute",
        "Loading...": "Laden...",
        "Error": "Fehler",
        "Room": "Raum",
        "Group": "Gruppe",
        "Summary": "Kurzinfo",
        "Description": "Beschreibung",
        "Apply": "Übernehmen",
        "Apply changes for all previous events": "Änderungen für alle vorhergehenden Termine übernehmen",
        "Apply changes for all following events": "Änderungen für alle nachfolgenden Termine übernehmen",
        "Details": "Details",
    },
    "en": {
        "Today": "Today",
        "Loading...": "Loading...",
        "Error": "Error",
        "Room": "Room",
        "Group": "Group",
        "Summary": "Summary",
        "Description": "Description",
        "Apply": "Apply",
        "Apply changes for all previous events": "Apply changes for all previous events",
        "Apply changes for all following events": "Apply changes for all following events",
        "Details": "Details",
    },
    "bar-AT": {
        "Today": "Haid",
        "Loading...": "Låna...",
        "Error": "Föhla",
        "Room": "Raum",
        "Group": "Gruppn",
        "Summary": "Kuazinfo",
        "Description": "Beschreibung",
        "Apply": "Übanemma",
        "Apply changes for all previous events": "Ändarungen fia olle voahearign Teamine übanemma",
        "Apply changes for all following events": "Ändarungen fia olle nochfoigendn Teamine übanemma",
        "Details": "Dedais",
    },
};

function _(msgId: string): string {
    const msgLang = MESSAGES[LANG];
    const msgLangGroup = MESSAGES[LANG_GROUP];
    return (msgLang && msgLang[msgId]) || (msgLangGroup && msgLangGroup[msgId]) || msgId;
}
