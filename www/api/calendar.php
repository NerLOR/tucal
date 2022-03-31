<?php

require "../.php/session.php";

try {
    $info = $_SERVER['PATH_INFO'] ?? '';

    header('Content-Type: application/json; charset=UTF-8');
    header("Cache-Control: private, no-cache");

    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $json = file_get_contents('php://input');
        $data = json_decode($json, true);
        if ($data === null) {
            error(400, json_last_error_msg());
        }
        $_POST = $data;
    }

    switch ($info) {
        case '/calendar': calendar(); break;
        case '/update': update(); break;
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
        header("Allow: GET");
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
            SELECT e.event_nr, e.event_id, e.start_ts, e.end_ts, e.room_nr, e.data, d.data AS user_data,
                   l.course_nr, l.semester, l.name, g.group_id, g.group_name, e.deleted
            FROM tucal.event e
                LEFT JOIN tucal.external_event x ON x.event_nr = e.event_nr
                JOIN tucal.group_member m ON m.group_nr = e.group_nr
                JOIN tucal.account a ON a.account_nr = m.account_nr
                LEFT JOIN tucal.group g ON g.group_nr = e.group_nr
                LEFT JOIN tucal.group_link l ON l.group_nr = g.group_nr
                LEFT JOIN tucal.event_user_data d ON (d.event_nr, d.account_nr) = (e.event_nr, a.account_nr)
            WHERE e.start_ts >= :start AND e.start_ts < :end AND
                  a.mnr = :mnr AND
                  (e.global OR (:mnr = ANY(SELECT u.mnr FROM tuwel.event_user eu
                                           JOIN tuwel.user u ON u.user_id = eu.user_id
                                           WHERE eu.event_id::text = x.event_id))) AND
                  (m.ignore_from IS NULL OR e.start_ts < m.ignore_from) AND
                  (m.ignore_until IS NULL OR e.start_ts >= m.ignore_until)
            GROUP BY e.event_nr, e.event_id, e.start_ts, e.end_ts, e.room_nr, e.group_nr, e.data, d.data,
                     l.course_nr, l.semester, l.name, g.group_id, g.group_name
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

        $course = null;
        if ($row['course_nr'] !== null) {
            $course = [
                'nr' => $row['course_nr'],
                'semester' => $row['semester'],
                'group' => $row['name'],
            ];
        }

        $data = [
            'id' => $row['event_id'],
            'start' => date('c', $start),
            'end' => date('c', $end),
            'deleted' => $row['deleted'],
            'room_nr' => $row['room_nr'],
            'course' => $course,
            'group' => [
                'id' => $row['group_id'],
                'name' => $row['group_name'],
            ],
            'data' => json_decode($row['data']),
            'user' => $row['user_data'] ? json_decode($row['user_data']) : null,
        ];
        echo json_encode($data, JSON_FLAGS);
    }

    echo "\n]}}\n";
    tucal_exit();
}

function update() {
    global $USER;
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        header("Allow: POST");
        error(405);
    }

    $evtId = $_GET['id'] ?? null;
    $previous = ($_GET['previous'] ?? null) === 'true';
    $following = ($_GET['following'] ?? null) === 'true';

    if ($evtId === null) {
        error(400);
    } elseif (!isset($USER)) {
        error(401);
    }

    db_transaction();

    try {
        db_exec("LOCK TABLE tucal.event IN SHARE ROW EXCLUSIVE MODE");

        $stmt = db_exec("SELECT event_nr, group_nr, room_nr, start_ts, end_ts FROM tucal.event WHERE event_id = :id", [
            'id' => $evtId,
        ]);
        $rows = $stmt->fetchAll();
        if (sizeof($rows) === 0) {
            db_rollback();
            error(404);
        }

        $row = $rows[0];
        $eventNr = $row['event_nr'];
        $room = $row['room_nr'];
        $start = new DateTime($row['start_ts']);
        $end = new DateTime($row['end_ts']);
        $group = $row['group_nr'];

        $dataUserStr = '{}';
        $userStr = '{}';
        if ($_POST['data']) {
            if ($_POST['data']['user']) {
                $dataUserStr = json_encode($_POST['data']['user']);
            }
        }
        if ($_POST['user']) {
            $userStr = json_encode($_POST['user']);
        }

        // postgres DOW - sunday (0), saturday (6)
        $stmt = db_exec("
                SELECT event_nr
                FROM tucal.event
                WHERE event_nr = :enr OR (
                      group_nr = :group AND
                      room_nr IS NOT DISTINCT FROM :room AND
                      start_ts::date = end_ts::date AND
                      start_ts::time = :stime AND
                      EXTRACT(DOW FROM start_ts) = :dow AND
                      ((:prev::bool AND start_ts < :start) OR (:foll::bool AND start_ts > :start))
                    )", [
            'enr' => $eventNr,
            'group' => $group,
            'room' => $room,
            'start' => $row['start_ts'],
            'stime' => $start->format('H:i:s'),
            'dow' => $start->format('w'),
            'prev' => $previous ? 'TRUE' : 'FALSE',
            'foll' => $following ? 'TRUE' : 'FALSE',
        ]);
        $enrs = [];
        while ($row = $stmt->fetch()) {
            $enrs[] = $row[0];
        }
        $enrsStr = '{' . join(',', $enrs) . '}';

        db_exec("
                UPDATE tucal.event
                SET data = jsonb_set(data, '{\"user\"}', data -> 'user' || :data::jsonb),
                    updated = FALSE,
                    update_ts = now(),
                    update_seq = update_seq + 1
                WHERE event_nr = ANY(:enrs)", [
            'enrs' => $enrsStr,
            'data' => $dataUserStr,
        ]);

        foreach ($enrs as $enr) {
            db_exec("
                    INSERT INTO tucal.event_user_data (event_nr, account_nr, data)
                    VALUES (:enr, :anr, :data::jsonb)
                    ON CONFLICT ON CONSTRAINT pk_event_user_data DO UPDATE
                    SET data = tucal.event_user_data.data || :data::jsonb", [
                'enr' => $enr,
                'anr' => $USER['nr'],
                'data' => $userStr,
            ]);
        }
    } catch (Exception $e) {
        db_rollback();
        error(500, $e->getMessage());
    }

    db_commit();

    echo '{"status":"success","message":"work in progress","data":{}}' . "\n";
    tucal_exit();
}
