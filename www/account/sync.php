<?php

global $TITLE;
global $USER;
global $ERROR;
global $STATUS;

require "../.php/session.php";
force_user_login('/account/');

require "../.php/main.php";

$errorMsg = null;

if (!$USER['sso_credentials']) {
    redirect('/account/tu-wien-sso');
}

$stmt = db_exec("SELECT job_id FROM tucal.v_job WHERE (mnr, status, name) = (?, 'running', 'sync user')", [$USER['mnr']]);
$rows = $stmt->fetchAll();
if (sizeof($rows) > 0) {
    $jobId = $rows[0][0];
    redirect("/account/tu-wien-sso?job=$jobId");
}

$sock = fsockopen('unix:///var/tucal/scheduler.sock', -1, $errno, $errstr);
if (!$sock) {
    $STATUS = 500;
    $ERROR = _('Unable to open unix socket') . ": $errstr";
    goto doc;
}

$data = "sync-user $USER[mnr]";
fwrite($sock, "$data\n");
$res = fread($sock, 64);

if (substr($res, 0, 6) === 'error:') {
    $STATUS = 500;
    $ERROR = _('Error') . ": " . trim(substr($res, 6));
    goto doc;
}

$res = explode(' ', $res);
if (sizeof($res) < 2) {
    $STATUS = 500;
    $ERROR = _('Unknown error');
    goto doc;
}

redirect("/account/tu-wien-sso?job=$res[1]");

doc:
require "../.php/main.php";
