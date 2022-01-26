"use strict";

const LANG: string = document.documentElement.lang;
const LANG_GROUP: string = LANG.split("-")[0] || "de";
const LOCALE: string = LANG.startsWith("bar") ? "de" + LANG.substr(3) : LANG;
const LOCALE_GROUP: string = LOCALE.split("-")[0] || "de";

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
        "floor": "Stock",
        "ground floor": "Erdgeschoss",
        "basement floor": "Untergeschoss",
        "Status": "Status",
        "Live": "Live",
        "Not live": "Nicht live",
        "No room": "Kein Raum",
        "Confirmed": "Bestätigt",
        "Tentative": "Vorläufig",
        "Cancelled": "Abgesagt",
        "Unknown": "Unbekannt",
        "Mode": "Modus",
        "On-site-only": "Nur vor Ort",
        "Hybrid": "Hybrid",
        "Online-only": "Nur online",
        "Copy link": "Link kopieren",
    },
    "de-AT": {
        "ground floor": "Erdgeschoß",
        "basement floor": "Untergeschoß",
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
        "floor": "floor",
        "ground floor": "ground floor",
        "basement floor": "basement",
        "Status": "Status",
        "Live": "Live",
        "Not live": "Not Live",
        "No room": "No room",
        "Confirmed": "Confirmed",
        "Tentative": "Tentative",
        "Cancelled": "Cancelled",
        "Unknown": "Unknown",
        "Mode": "Mode",
        "On-site-only": "On-site-only",
        "Hybrid": "Hybrid",
        "Online-only": "Online-only",
        "Copy link": "Copy link",
    },
    "bar-AT": {
        "Today": "Haid",
        "Loading...": "Lona...",
        "Error": "Föhla",
        "Room": "Raum",
        "Group": "Gruppn",
        "Summary": "Kuazinfo",
        "Description": "Beschreibung",
        "Apply": "Übanemma",
        "Apply changes for all previous events": "Ändarungen fia olle voahearign Teamine übanemma",
        "Apply changes for all following events": "Ändarungen fia olle nochfoigendn Teamine übanemma",
        "floor": "Stook",
        "ground floor": "Eadgschoss",
        "basement floor": "Untagschoss",
        "Status": "Status",
        "Live": "Leif",
        "Not live": "Ned Leif",
        "No room": "Ka Raum",
        "Confirmed": "Bestätigt",
        "Tentative": "Voaläffig",
        "Cancelled": "Ogsogt",
        "Unknown": "Was ma ned",
        "Mode": "Modus",
        "On-site-only": "Nua vua Uat",
        "Hybrid": "Hübrid",
        "Online-only": "Nua onlein",
        "Copy link": "Link kopian",
    },
};

function _(msgId: string): string {
    const msgLang = MESSAGES[LANG];
    const msgLangGroup = MESSAGES[LANG_GROUP];
    return (msgLang && msgLang[msgId]) || (msgLangGroup && msgLangGroup[msgId]) || msgId;
}

function formatFloor(floor: string): string {
    const nr = (floor === 'EG') ? 0 : (floor[0] === 'U') ? -parseInt(floor.substr(1)) : parseInt(floor);

    if (LOCALE_GROUP === 'de') {
        if (nr === 0) {
            return _('ground floor');
        } else if (nr > 0){
            return `${nr}. ${_('floor')}`;
        } else {
            return `${-nr}. ${_('basement floor')}`;
        }
    } else if (LOCALE_GROUP === 'en') {
        if (nr === 0) {
            return _('ground floor');
        } else if (nr > 0) {
            switch (nr % 10) {
                case 1: return `${nr}st ${_('floor')}`;
                case 2: return `${nr}nd ${_('floor')}`;
                case 3: return `${nr}rd ${_('floor')}`;
                default: return `${nr}th ${_('floor')}`;
            }
        } else {
            switch (nr % 10) {
                case 1: return `${nr}st ${_('basement floor')}`;
                case 2: return `${nr}nd ${_('basement floor')}`;
                case 3: return `${nr}rd ${_('basement floor')}`;
                default: return `${nr}th ${_('basement floor')}`;
            }
        }
    } else {
        throw new Error();
    }
}
