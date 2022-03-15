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
    const nrAbs = Math.abs(nr);

    if (LOCALE_GROUP === 'de') {
        if (nr === 0) {
            return _('Ground floor');
        } else if (nr > 0){
            return `${nr}. ${_('floor')}`;
        } else {
            return `${nrAbs}. ${_('basement floor')}`;
        }
    } else if (LOCALE_GROUP === 'en') {
        if (nr === 0) {
            return _('Ground floor');
        } else if (nr > 0) {
            if (nr >= 11 && nr <= 13)
                return `${nr}th ${_('floor')}`;
            switch (nr % 10) {
                case 1: return `${nr}st ${_('floor')}`;
                case 2: return `${nr}nd ${_('floor')}`;
                case 3: return `${nr}rd ${_('floor')}`;
                default: return `${nr}th ${_('floor')}`;
            }
        } else {
            if (nrAbs >= 11 && nrAbs <= 13)
                return `${nrAbs}th ${_('basement floor')}`;
            switch (nrAbs % 10) {
                case 1: return `${nrAbs}st ${_('basement floor')}`;
                case 2: return `${nrAbs}nd ${_('basement floor')}`;
                case 3: return `${nrAbs}rd ${_('basement floor')}`;
                default: return `${nrAbs}th ${_('basement floor')}`;
            }
        }
    } else {
        throw new Error();
    }
}
