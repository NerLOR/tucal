<?php

require "../.php/session.php";

try {
    $info = $_SERVER['PATH_INFO'] ?? '';

    header('Content-Type: application/json; charset=UTF-8');
    header("Cache-Control: private, no-cache");

    switch ($info) {
        case '/rooms': rooms(); break;
        case '/calendar': calendar(); break;
        case '/job': job(); break;
        case '/courses': courses(); break;
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

function rooms() {
    if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
        error(405);
    }

    header("Cache-Control: public, max-age=86400");

    $res = db_exec("SELECT r.room_nr, r.room_code, r.tiss_code, r.room_name, r.room_suffix, r.room_name_short,
                  r.room_alt_name, r.room_name_normal, lt.room_code AS lt_room_code, lt.lt_name
                  FROM tucal.v_room r LEFT JOIN tucal.v_lecture_tube lt ON lt.room_nr = r.room_nr");
    $arr = $res->fetchAll();

    $content = '{"status":"success","message":null,"data":{"rooms":[' . "\n";
    for ($i = 0; $i < sizeof($arr); $i++) {
        $row = $arr[$i];
        $data = [
            "nr" => (int) $row["room_nr"],
            "room_codes" => explode('/', $row["room_code"]),
            "tiss_code" => $row["tiss_code"],
            "name" => $row["room_name"],
            "suffix" => $row["room_suffix"],
            "name_short" => $row["room_name_short"],
            "alt_name" => $row["room_alt_name"],
            "name_normalized" => $row["room_name_normal"],
            "lt_room_code" => $row["lt_room_code"],
            "lt_name" => $row["lt_name"],
        ];
        $content .= json_encode($data, JSON_FLAGS);
        if ($i !== sizeof($arr) - 1) $content .= ",";
        $content .= "\n";
    }
    $content .= "]}}\n";
    header("Content-Length: " . strlen($content));
    echo $content;
    tucal_exit();
}

function calendar() {
    if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
        error(405);
    }

    $subject = $_GET['subject'];
    $start = $_GET['start'];
    $end = $_GET['end'];

    $start = strtotime($start);
    $end = strtotime($end);

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
                  (e.global OR (:mnr IN (SELECT u.mnr FROM tuwel.event_user eu
                                         JOIN tuwel.user u ON u.user_id = eu.user_id
                                         WHERE eu.event_id::text = x.event_id))) AND
                  (m.ignore_from IS NULL OR e.start_ts < m.ignore_from) AND
                  (m.ignore_until IS NULL OR e.start_ts >= m.ignore_until)
            GROUP BY e.event_nr, e.event_id, e.start_ts, e.end_ts, e.room_nr, e.group_nr, e.data,
                     l.course_nr, l.semester, l.name, g.group_id
            ORDER BY e.start_ts, e.event_nr", [
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

function job() {
    if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
        error(405);
    }

    $jobId = $_GET['id'] ?? null;

    if ($jobId === null) {
        error(400, "missing field 'id'");
    }

    $stmt = db_exec("SELECT data, status FROM tucal.v_job WHERE job_id = ?", [$jobId]);
    $rows = $stmt->fetchAll();
    if (sizeof($rows) === 0) {
        error(404);
    }

    echo '{"status":"success","message":"work in progress","data":' . "\n";
    $data = json_decode($rows[0][0], true);
    $data['status'] = $rows[0][1];
    echo json_encode($data, JSON_FLAGS);
    echo "\n}\n";

    tucal_exit();
}

function courses() {
    global $USER;

    if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
        error(405);
    }

    $mnr = $_GET['mnr'] ?? null;
    if ($mnr === null) {
        error(501);
    }

    if (!isset($USER)) {
        error(401);
    } elseif ($USER['mnr'] !== $mnr) {
        error(403);
    }

    $stmt = db_exec("
            SELECT c.course_nr, c.semester, c.ects, cd.type, cd.name_de, cd.name_en,
                   ca.acronym_1, ca.acronym_2, ca.short, ca.program
            FROM tucal.v_account_group m
            LEFT JOIN tiss.course c ON (c.course_nr, c.semester) = (m.course_nr, m.semester)
            LEFT JOIN tiss.course_def cd ON cd.course_nr = c.course_nr
            LEFT JOIN tucal.course_acronym ca ON ca.course_nr = c.course_nr
            WHERE m.mnr = :mnr", [
        'mnr' => $mnr,
    ]);

    echo '{"status":"success","message":"work in progress","data":{"personal":[' . "\n";
    $first = true;
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        if ($first) {
            $first = false;
        } else {
            echo ",\n";
        }
        $data = [
            'nr' => $row['course_nr'],
            'semester' => $row['semester'],
            'ects' => (float) $row['ects'],
            'type' => $row['type'],
            'name_de' => $row['name_de'],
            'name_en' => $row['name_en'],
            'acronym_1' => $row['acronym_1'],
            'acronym_2' => $row['acronym_2'],
            'short' => $row['short'],
            'program' => $row['program'],
        ];
        echo json_encode($data, JSON_FLAGS);
    }

    echo "\n],\"friends\":[\n";

    echo "\n]}}\n";
    tucal_exit();
}
