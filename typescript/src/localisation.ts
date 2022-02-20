"use strict";

const LANG: string = document.documentElement.lang;
const LANG_GROUP: string = LANG.split("-")[0] || "de";
const LOCALE: string = LANG.startsWith("bar") ? "de" + LANG.substring(3) : LANG;
const LOCALE_GROUP: string = LOCALE.split("-")[0] || "de";

function _(msgId: string): string {
    const msgLang = MESSAGES[LANG];
    const msgLangGroup = MESSAGES[LANG_GROUP];
    return (msgLang && msgLang[msgId]) || (msgLangGroup && msgLangGroup[msgId]) || msgId;
}

function formatFloor(floor: string): string {
    // TODO DG/EG/SO/ZE
    const nr = (floor === 'EG') ? 0 : (floor[0] === 'U') ? -parseInt(floor.substring(1)) : parseInt(floor);

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
