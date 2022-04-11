<?php

global $USER;
global $TUCAL;

require "../../.php/session.php";

if ($_SERVER['PATH_INFO']) {
    header("Status: 404");
    header("Content-Length: 0");
    tucal_exit();
} elseif ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header("Status: 405");
    header("Allow: POST");
    header("Content-Length: 0");
    tucal_exit();
}

force_user_login();

$subject = $_GET['subject'] ?? null;
if ($subject === null) {
    header("Status: 400");
    header("Content-Length: 0");
    tucal_exit();
}

db_transaction();
try {
    db_exec("LOCK TABLE tucal.calendar_export IN SHARE ROW EXCLUSIVE MODE");
    $token = generate_token(16, "tucal.calendar_export");

    db_exec("INSERT INTO tucal.calendar_export (token, account_nr, subject_mnr) VALUES (:t, :nr, :mnr)", [
        't' => $token,
        'nr' => $USER['nr'],
        'mnr' => $subject,
    ]);
} catch (Exception $e) {
    db_rollback();
    $msg = "<p>" . htmlspecialchars($e->getMessage()) . "</p>";
    header("Status: 500");
    header("Content-Length: " . strlen($msg));
    echo $msg;
    tucal_exit();
}
db_commit();

$ref = $_SERVER['HTTP_REFERER'] ?? '';
$refQuery = "https://$TUCAL[hostname]/calendar/";
if (substr($ref, 0, strlen($refQuery)) !== $refQuery) {
    $ref = '/calendar/';
} else {
    $ref = '/calendar/' . substr($ref, strlen($refQuery));
}

$ref .= '#exports';
redirect($ref);
