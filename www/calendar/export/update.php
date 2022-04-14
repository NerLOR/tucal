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

$id = $_GET['id'] ?? null;
if ($id === null) {
    header("Status: 400");
    header("Content-Length: 0");
    tucal_exit();
}

db_transaction();
try {
    db_exec("LOCK TABLE tucal.calendar_export IN SHARE ROW EXCLUSIVE MODE");

    $stmt = db_exec("SELECT account_nr FROM tucal.calendar_export WHERE export_id = :id", ['id' => $id]);
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

    $types = [];
    foreach (['course', 'group', 'other'] as $t) {
        if (($_POST["export-$t-events"] ?? '0') === 'on')
            $types[] = $t;
    }

    $opts = [
        'event_types' => $types,
        'todos' => str_replace('-', '_', $_POST['todos'] ?? 'as-todos'),
        'location' => str_replace('-', '_', $_POST['location'] ?? 'room-abbr'),
        'location_tuw_maps' => ($_POST['tuw-maps'] ?? '0') === 'on',
        'categories' => [str_replace('-', '_', $_POST['categories'] ?? 'event-type')],
        'planned' => ($_POST['planned'] ?? '0') === 'on',
    ];

    db_exec("
            UPDATE tucal.calendar_export
            SET options = jsonb_set(jsonb_set(options, '{ical}', :opts, true), '{name}', :name, true)
            WHERE account_nr = :nr AND export_id = :id", [
        'id' => $id,
        'nr' => $USER['nr'],
        'opts' => json_encode($opts),
        'name' => json_encode($_POST['name'] ?? null),
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
