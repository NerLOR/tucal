<?php

global $USER;
global $STATUS;
global $TITLE;

require "../.php/session.php";

force_user_login();

if (!$USER['administrator']) {
    $STATUS = 403;
} elseif ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $id = $_POST['account'] ?? null;
    if ($id === null) {
        $STATUS = 400;
    } else {
        $stmt = db_exec("SELECT account_nr FROM tucal.v_account WHERE account_id = ?", [$id]);
        $accounts = $stmt->fetchAll();
        if (sizeof($accounts) === 0) {
            $STATUS = 404;
        } else {
            $_SESSION['opts']['impersonate_account_nr'] = $accounts[0][0];
            redirect("/");
        }
    }
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET' && $_SERVER['REQUEST_METHOD'] !== 'HEAD') {
    $STATUS = 405;
    header("Allow: HEAD, GET, POST");
}

require "../.php/main.php";
