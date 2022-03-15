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
            return _('Ground floor');
        } else if (nr > 0){
            return `${nr}. ${_('Floor')}`;
        } else {
            return `${-nr}. ${_('Basement floor')}`;
        }
    } else if (LOCALE_GROUP === 'en') {
        if (nr === 0) {
            return _('Ground floor');
        } else if (nr > 0) {
            switch (nr % 10) {
                case 1: return `${nr}st ${_('Floor')}`;
                case 2: return `${nr}nd ${_('Floor')}`;
                case 3: return `${nr}rd ${_('Floor')}`;
                default: return `${nr}th ${_('Floor')}`;
            }
        } else {
            switch (nr % 10) {
                case 1: return `${nr}st ${_('Basement floor')}`;
                case 2: return `${nr}nd ${_('Basement floor')}`;
                case 3: return `${nr}rd ${_('Basement floor')}`;
                default: return `${nr}th ${_('Basement floor')}`;
            }
        }
    } else {
        throw new Error();
    }
}
