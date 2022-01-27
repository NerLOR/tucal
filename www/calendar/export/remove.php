<?php

global $USER;
global $CONFIG;

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

$id = $_GET['id'] ?? null;
if ($id === null) {
    header("Status: 400");
    header("Content-Length: 0");
    tucal_exit();
}

db_transaction();
try {
    db_exec("LOCK TABLE tucal.calendar_export IN SHARE ROW EXCLUSIVE MODE");

    $stmt = db_exec("SELECT account_nr FROM tucal.calendar_export WHERE export_id = :id");
    $rows = $stmt->fetchAll();
    if (sizeof($rows) === 0) {
        db_rollback();
        header("Status: 404");
        header("Content-Length: 0");
        tucal_exit();
    }
    $row = $rows[0];
    if ($row['account_nr'] !== $USER['nr']) {
        db_rollback();
        header("Status: 403");
        header("Content-Length: 0");
        tucal_exit();
    }

    db_exec("DELETE FROM tucal.calendar_export WHERE account_nr = :nr AND export_id = :id", [
        'id' => $id,
        'nr' => $USER['nr'],
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
$refQuery = "https://$CONFIG[hostname]/calendar/";
if (substr($ref, 0, strlen($refQuery)) !== $refQuery) {
    $ref = '/calendar/';
} else {
    $ref = '/calendar/' . substr($ref, strlen($refQuery));
}

header("Status: 303");
header("Location: $ref");

