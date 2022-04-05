<?php

global $STATUS;
global $USE_PATH_INFO;

if ((isset($STATUS) && $STATUS >= 400 && $STATUS < 600) || ((!isset($USE_PATH_INFO) || !$USE_PATH_INFO) && (isset($_SERVER['PATH_INFO']) && $_SERVER['PATH_INFO'] !== ''))) {
    $STATUS = $STATUS ?? 404;
    header("Status: $STATUS");
    require "header.php";
    require "footer.php";
}

$sent = false;
foreach (headers_list() as $h) {
    if (strtolower(substr($h, 0, 7)) === 'status:') {
        $STATUS = (int) substr($h, 7);
        $sent = true;
        break;
    }
}

if (!$sent) {
    $STATUS = $STATUS ?? 200;
    header("Status: $STATUS");
}
