<?php

require "../.php/session.php";

const FLAGS = JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES;

try {
    $info = $_SERVER['PATH_INFO'] ?? '';

    header('Content-Type: application/json; charset=UTF-8');
    header("Cache-Control: private, no-cache");

    switch ($info) {
        case '/rooms': rooms(); break;
        case '/calendar': calendar(); break;
        case '/job': job(); break;
        default: error(404);
    }
} catch (Exception $e) {
    error(500, $e->getMessage(), $e instanceof PDOException);
}

function error(int $status, string $message = null, bool $db_error = false) {
    $content = '{"status":"error","message":' . json_encode($message, FLAGS) .'}' . "\n";
    header("Status: $status");
    header("Content-Length: " . strlen($content));
    echo $content;
    tucal_exit($db_error);
}

function rooms() {
    if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
        error(405);
    }

    $res = db_exec("SELECT r.room_nr, r.room_code, r.tiss_code, r.room_name, r.room_suffix, r.room_name_short,
                  r.room_alt_name, r.room_name_normal, lt.room_code AS lt_room_code, lt.lt_name
                  FROM tucal.v_room r LEFT JOIN tucal.v_lecture_tube lt ON lt.room_nr = r.room_nr");
    $arr = $res->fetchAll();

    $content = '{"status":"success","message":null,"data":{"rooms":[' . "\n";
    for ($i = 0; $i < sizeof($arr); $i++) {
        $row = $arr[$i];
        $data = [
            "room_nr" => (int) $row["room_nr"],
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
        $content .= json_encode($data, FLAGS);
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

    $stmt = db_exec("SELECT * FROM tiss.event WHERE room_code = 'AUDI' AND start_ts >= :start AND end_ts < :end", [
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
        ];
        echo json_encode($data, FLAGS);
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
    echo json_encode($data, FLAGS);
    echo "\n}\n";

    tucal_exit();
}
