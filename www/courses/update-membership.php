<?php

global $USER;

require "../.php/session.php";
force_user_login('/courses/');
require "../.php/main.php";

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $stmt = db_exec("SELECT group_nr, group_id FROM tucal.group WHERE public = TRUE");
    $groups = [];
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        $groups[$row['group_id']] = $row['group_nr'];
    }

    db_exec("
            DELETE FROM tucal.group_member m
            WHERE account_nr = :nr AND (SELECT public FROM tucal.group g WHERE g.group_nr = m.group_nr)", [
        'nr' => $USER['nr'],
    ]);

    foreach ($_POST as $group => $member) {
        if ($member !== 'member' || substr($group, 0, 6) !== 'group-') continue;
        $groupId = substr($group, 6);
        if (!isset($groups[$groupId])) continue;
        db_exec("INSERT INTO tucal.group_member (account_nr, group_nr) VALUES (:anr, :gnr)", [
            'anr' => $USER['nr'],
            'gnr' => $groups[$groupId],
        ]);
    }

    redirect('/courses/');
} else {
    header("Status: 405");
    header("Content-Length: 0");
    header("Allow: POST");
    tucal_exit();
}
