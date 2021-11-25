<?php

global $USER;
global $STATUS;
global $LOCATION;

require "../.php/session.php";

$STATUS = 303;
if (!isset($USER)) {
    $LOCATION = "/account/login";
} else {
    unset($USER);
    $LOCATION = $_SERVER['HTTP_REFERER'] ?? '/';
}

require "../.php/main.php";
