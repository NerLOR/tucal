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

try {
    [$jobNr, $jobId, $pid] = schedule_job(['sync-user', 'keep', $USER['mnr']]);
} catch (RuntimeException $e) {
    $STATUS = 500;
    if (!$e->getMessage()) {
        $ERROR = _('Unknown error');
    } else {
        $ERROR = _('Error') . ": " . $e->getMessage();
    }
    goto doc;
}

redirect("/account/tu-wien-sso?job=$jobId");

doc:
require "../.php/main.php";
