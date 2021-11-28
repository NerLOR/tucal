<?php

global $USER;

require "../.php/session.php";

if (!isset($USER)) {
    redirect('/account/login');
}

unset($USER);
redirect($_SERVER['HTTP_REFERER'] ?? '/');
