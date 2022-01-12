<?php

global $USER;

require "../.php/session.php";
force_user_login('/courses/');

require "../.php/main.php";

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $mode = $_POST['ignore'] ?? 'never';
    $groupId = $_POST['group'] ?? null;
    $course = $_POST['course'] ?? null;
    $from = $_POST['ignore-from'] ?? '';
    $until = $_POST['ignore-until'] ?? '';

    if (($groupId === null && $course === null) || ($groupId !== null && $course !== null)) {
        header("Status: 400");
        header("Content-Length: 0");
        tucal_exit();
    }

    if ($course !== null) {
        $parts = explode('-', $course);
        $courseNr = $parts[0];
        $semester = $parts[1];
    }

    if ($mode === 'never') {
        $from = null;
        $until = null;
    } elseif ($mode === 'fully') {
        $from = '0001-01-01T00:00:00+00:00';
        $until = null;
    } else {
        $from = $from !== '' ? ($from . "T00:00:00+00:00") : null;
        $until = $until !== '' ? ($until . "T00:00:00+00:00") : null;
    }

    $data = [
        'anr' => $USER['nr'],
        'until' => $until,
        'from' => $from,
    ];

    if ($groupId !== null) {
        $data['gid'] = $groupId;
        $stmt = db_exec("
                    UPDATE tucal.group_member
                    SET ignore_until = :until, ignore_from = :from
                    WHERE account_nr = :anr AND
                          group_nr = (SELECT group_nr FROM tucal.group WHERE group_id = :gid)", $data);
    } else {
        $data['cnr'] = $courseNr ?? null;
        $data['sem'] = $semester ?? null;
        $stmt = db_exec("
                    UPDATE tucal.group_member
                    SET ignore_until = :until, ignore_from = :from
                    WHERE account_nr = :anr AND
                          group_nr = ANY(SELECT group_nr
                                         FROM tucal.group_link
                                         WHERE (course_nr, semester) = (:cnr, :sem))", $data);
    }

    redirect('/courses/');
} else {
    header("Status: 405");
    header("Content-Length: 0");
    header("Allow: POST");
    tucal_exit();
}

