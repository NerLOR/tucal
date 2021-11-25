<?php

global $STATUS;
global $LOCATION;

if ((!isset($USE_PATH_INFO) || !$USE_PATH_INFO) && (isset($_SERVER['PATH_INFO']) && $_SERVER['PATH_INFO'] !== '')) {
    $STATUS = 404;
    require "header.php";
    require "footer.php";
} elseif (isset($LOCATION)) {
    header("Location: $LOCATION");
    $STATUS = (isset($STATUS)) ? $STATUS : 303;
}

if (isset($STATUS)) {
    header("Status: $STATUS");
    if ($STATUS >= 300 && $STATUS < 400) {
        // Use Necronda web server default error documents
        header("Content-Type: text/html");
        header("Content-Length: 0");
        header("Content-Security-Policy: default-src 'unsafe-inline' 'self' data:");
        tucal_exit();
    }
}
