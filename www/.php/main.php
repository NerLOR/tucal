<?php

global $STATUS;
global $USE_PATH_INFO;

if ((isset($STATUS) && $STATUS >= 400 && $STATUS < 600) || ((!isset($USE_PATH_INFO) || !$USE_PATH_INFO) && (isset($_SERVER['PATH_INFO']) && $_SERVER['PATH_INFO'] !== ''))) {
    $STATUS = $STATUS ?? 404;
    header("Status: $STATUS");
    require "header.php";
    require "footer.php";
}

if (isset($STATUS)) {
    header("Status: $STATUS");
}
