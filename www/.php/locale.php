<?php

global $LOCALE;
global $LOCALES;
$LOCALES = [
    'de-AT',
    'de-DE',
    'en-GB',
    'en-US',
    'bar-AT',
];

function init_locale() {
    global $LOCALE;
    $LOCALE = get_locale();

    $locales = [str_replace('-', '_', $LOCALE) . '.UTF-8'];
    if ($LOCALE === 'bar-AT')
        $locales[] = 'de_AT.UTF-8';

    setlocale(LC_ALL, $locales);
    bindtextdomain('tucal', "$_SERVER[DOCUMENT_ROOT]/.php/locale/");
    textdomain('tucal');
}

function _ctx(string $ctx, string $msgid): string {
    $ctxStr = "${ctx}\004${msgid}";
    $translation = gettext($ctxStr);
    if ($translation === $ctxStr)
        return $msgid;
    return $translation;
}

/**
 * Gets the locale to use
 * @return string The locale to use
 */
function get_locale(): string {
    global $USER;
    global $LOCALES;

    if (isset($USER) && isset($USER['opts']['locale'])) {
        $loc = $USER['opts']['locale'];
        if (in_array($loc, $LOCALES))
            return $loc;
    }

    if (isset($_SERVER['HTTP_ACCEPT_LANGUAGE'])) {
        $http_lang = explode(',', $_SERVER['HTTP_ACCEPT_LANGUAGE']);

        foreach ($http_lang as $http) {
            $pref = explode(';', $http);
            $loc = $pref[0];

            if (in_array($loc, $LOCALES))
                return $loc;

            if (strpos($loc, '-') === false) {
                foreach ($LOCALES as $avail) {
                    if (substr($avail, 0, 2) === $loc)
                        return $avail;
                }
            }
        }

        foreach ($LOCALES as $avail) {
            foreach ($http_lang as $http) {
                if (substr($avail, 0, 2) === substr($http, 0, 2))
                    return $avail;
            }
        }
    }

    return $LOCALES[0];
}

