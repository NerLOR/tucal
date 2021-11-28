<?php

global $TITLE;
global $USER;
global $USE_PATH_INFO;

require "../.php/session.php";
force_user_login();

$parts = explode('/', $_SERVER['PATH_INFO']);
$year = date('Y');
$week = 'W' . date('W');
if (sizeof($parts) < 2 || strlen($parts[1]) === 0)
    redirect("/calendar/$USER[mnr]/$year/$week");

$subject = $parts[1];
if (sizeof($parts) < 3 || strlen($parts[2]) === 0)
    redirect("/calendar/$subject/$year/$week");

$year = $parts[2];
if (sizeof($parts) < 4 || strlen($parts[3]) === 0)
    redirect("/calendar/$subject/$year/$week");

$unit = $parts[3];

if (sizeof($parts) !== 4) {
    $STATUS = 404;
}

if (strlen($year) === 4 && is_numeric($year)) {
    $year = (string) (int) $year;
} else {
    $STATUS = 404;
}

if ($unit[0] === 'W' || $unit[0] === 'w') {
    $week = (int) substr($unit, 1);
    if ($week >= 1 && $week <= 53) {
        $unit = "W$week";
    } else {
        $STATUS = 404;
    }
} elseif (is_numeric($unit)) {
    $month = (int) $unit;
    if ($month >= 1 && $month <= 12) {
        $unit = (string) $month;
    } else {
        $STATUS = 404;
    }
} else {
    $STATUS = 404;
}

$USE_PATH_INFO = true;
require "../.php/main.php";

$wanted_uri = "/calendar/$subject/$year/$unit";
if ($_SERVER['REQUEST_URI'] !== $wanted_uri) {
    redirect($wanted_uri);
}

$TITLE = [_('Calendar')];

require "../.php/header.php";
?>
<main class="w4">

</main>
<?php
require "../.php/footer.php";
