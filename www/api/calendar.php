<?php

require "../.php/session.php";

try {
    $info = $_SERVER['PATH_INFO'] ?? '';

    header('Content-Type: application/json; charset=UTF-8');
    header("Cache-Control: private, no-cache");

    switch ($info) {
        case '/calendar': calendar(); break;
        default: error(404);
    }
} catch (Exception $e) {
    error(500, $e->getMessage(), $e instanceof PDOException);
}

function error(int $status, string $message = null, bool $db_error = false) {
    $content = '{"status":"error","message":' . json_encode($message, JSON_FLAGS) .'}' . "\n";
    header("Status: $status");
    header("Content-Length: " . strlen($content));
    echo $content;
    tucal_exit($db_error);
}


function calendar() {
    global $USER;
    if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
        error(405);
    }

    $subject = $_GET['subject'];
    $start = $_GET['start'];
    $end = $_GET['end'];

    $start = strtotime($start);
    $end = strtotime($end);

    if (!isset($USER)) {
        error(401);
    } elseif ($USER['mnr'] !== $subject) {
        $stmt = db_exec("
            SELECT a.username
            FROM tucal.friend f
                JOIN tucal.v_account a ON a.account_nr = f.account_nr_1
            WHERE (a.mnr, account_nr_2) = (:mnr, :nr)", [
            'mnr' => $subject,
            'nr' => $USER['nr'],
        ]);
        $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
        if (sizeof($rows) === 0) {
            error(403);
        }
    }

    $stmt = db_exec("
            SELECT e.event_nr, e.event_id, e.start_ts, e.end_ts, e.room_nr, e.data,
                   l.course_nr, l.semester, l.name, g.group_id
            FROM tucal.event e
                JOIN tucal.external_event x ON x.event_nr = e.event_nr
                JOIN tucal.group_member m ON m.group_nr = e.group_nr
                JOIN tucal.account a ON a.account_nr = m.account_nr
                LEFT JOIN tucal.group g ON g.group_nr = e.group_nr
                LEFT JOIN tucal.group_link l ON l.group_nr = g.group_nr
            WHERE e.start_ts >= :start AND e.start_ts < :end AND
                  a.mnr = :mnr AND NOT e.deleted AND
                  (e.global OR (:mnr = ANY(SELECT u.mnr FROM tuwel.event_user eu
                                           JOIN tuwel.user u ON u.user_id = eu.user_id
                                           WHERE eu.event_id::text = x.event_id))) AND
                  (m.ignore_from IS NULL OR e.start_ts < m.ignore_from) AND
                  (m.ignore_until IS NULL OR e.start_ts >= m.ignore_until)
            GROUP BY e.event_nr, e.event_id, e.start_ts, e.end_ts, e.room_nr, e.group_nr, e.data,
                     l.course_nr, l.semester, l.name, g.group_id
            ORDER BY e.start_ts, length(l.name), e.data -> 'summary'", [
        'mnr' => $subject,
        'start' => date('c', $start),
        'end' => date('c', $end),
    ]);

    echo '{"status":"success","message":"work in progress","data":{' . "\n";
    echo '"timestamp":"' . date('c') .
        '","start":"' . date('c', $start) .
        '","end":"' . date('c', $end) .
        '","events":[' . "\n";

    $first = true;
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        if ($first) {
            $first = false;
        } else {
            echo ",\n";
        }
        $start = strtotime($row['start_ts']);
        $end = strtotime($row['end_ts']);
        $data = [
            'id' => $row['event_id'],
            'start' => date('c', $start),
            'end' => date('c', $end),
            'room_nr' => $row['room_nr'],
            'course' => [
                'nr' => $row['course_nr'],
                'semester' => $row['semester'],
                'group' => $row['name'],
            ],
            'group_id' => $row['group_id'],
            'data' => json_decode($row['data']),
        ];
        echo json_encode($data, JSON_FLAGS);
    }

    echo "\n]}}\n";
    tucal_exit();
}
