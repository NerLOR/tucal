<?php

global $USER;

require "../.php/session.php";
force_user_login('/friends/');

if (!isset($_GET['id'])) {
    $STATUS = 400;
}

require "../.php/main.php";

$stmt = db_exec("
        INSERT INTO tucal.friend (account_nr_1, account_nr_2)
        VALUES (:nr, (SELECT account_nr FROM tucal.account WHERE account_id = :id))
        ON CONFLICT DO NOTHING", [
    'nr' => $USER['nr'],
    'id' => $_GET['id']
]);

redirect("/friends/");
