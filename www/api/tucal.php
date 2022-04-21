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
        case '/rooms': rooms(); break;
        case '/job': job(); break;
        case '/courses': courses(); break;
        case '/friends/nickname': nickname(); break;
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
    if ($_SERVER['REQUEST_METHOD'] !== 'GET' && $_SERVER['REQUEST_METHOD'] !== 'HEAD') {
        header("Allow: HEAD, GET");
        error(405);
    }

    header("Cache-Control: public, max-age=86400");

    $content = '{"status":"success","message":null,"data":{"buildings":[' . "\n";

    $res = db_exec("
                SELECT building_id, building_name, building_suffix, building_alt_name, area_name, area_suffix, address
                FROM tucal.v_building");
    $first = true;
    foreach ($res as $row) {
        $data = [
            "id" => $row["building_id"],
            "name" => $row["building_name"],
            "suffix" => $row["building_suffix"],
            "alt_name" => $row["building_alt_name"],
            "area_name" => $row["area_name"],
            "area_suffix" => $row["area_suffix"],
            "address" => $row["address"],
        ];
        if (!$first) $content .= ",\n";
        $content .= json_encode($data, JSON_FLAGS);
        $first = false;
    }

    $res = db_exec("
                SELECT r.room_nr, r.room_code, r.tiss_code, r.room_name, r.room_suffix, r.room_name_short,
                       r.room_alt_name, r.room_name_normal, lt.room_code AS lt_room_code, lt.lt_name,
                       b.building_name, b.building_suffix, b.area_name, b.area_suffix, b.address
                FROM tucal.v_room r
                    LEFT JOIN tucal.v_lecture_tube lt ON lt.room_nr = r.room_nr
                    LEFT JOIN tucal.v_building b ON b.building_id = r.building_id");

    $content .= "\n" . '],"rooms":[' . "\n";
    $first = true;
    foreach ($res as $row) {
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
        if (!$first) $content .= ",\n";
        $content .= json_encode($data, JSON_FLAGS);
        $first = false;
    }
    $content .= "\n]}}\n";
    header("Content-Length: " . strlen($content));
    echo $content;
    tucal_exit();
}

function job() {
    if ($_SERVER['REQUEST_METHOD'] !== 'GET' && $_SERVER['REQUEST_METHOD'] !== 'HEAD') {
        header("Allow: HEAD, GET");
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

    echo '{"status":"success","message":null,"data":' . "\n";
    $data = json_decode($rows[0][0], true);
    $data['status'] = $rows[0][1];
    echo json_encode($data, JSON_FLAGS);
    echo "\n}\n";

    tucal_exit();
}

function courses() {
    global $USER;

    if ($_SERVER['REQUEST_METHOD'] !== 'GET' && $_SERVER['REQUEST_METHOD'] !== 'HEAD') {
        header("Allow: HEAD, GET");
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

    function echo_course($row) {
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

    echo '{"status":"success","message":null,"data":{"personal":[' . "\n";
    $first = true;
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        if ($first) {
            $first = false;
        } else {
            echo ",\n";
        }
        echo_course($row);
    }

    echo "\n],\"friends\":[\n";

    $stmt = db_exec("SELECT account_nr_1 FROM tucal.friend WHERE account_nr_2 = :nr", ['nr' => $USER['nr']]);
    $friends = [];
    while ($row = $stmt->fetch(PDO::FETCH_NUM)) {
        $friends[] = $row[0];
    }
    $friendsStr = '{' . implode(',', $friends) . '}';

    $stmt = db_exec("
            SELECT DISTINCT c.course_nr, c.semester, c.ects, cd.type, cd.name_de, cd.name_en, ca.acronym_1,
                            ca.acronym_2, ca.short, ca.program
            FROM tucal.v_account_group m
                LEFT JOIN tiss.course c ON (c.course_nr, c.semester) = (m.course_nr, m.semester)
                LEFT JOIN tiss.course_def cd ON cd.course_nr = c.course_nr
                LEFT JOIN tucal.course_acronym ca ON ca.course_nr = c.course_nr
            WHERE m.account_nr = ANY(:friends)", [
        'friends' => $friendsStr,
    ]);
    $first = true;
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        if ($first) {
            $first = false;
        } else {
            echo ",\n";
        }
        echo_course($row);
    }

    echo "\n]}}\n";
    tucal_exit();
}

function nickname() {
    global $USER;

    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        header("Allow: POST");
        error(405);
    } elseif (!isset($USER)) {
        error(401);
    }

    $mnr = $_POST['mnr'] ?? null;
    $name = $_POST['nickname'] ?? null;
    if ($mnr === null) {
        error(400);
    } elseif ($name !== null && (strlen($name) > 24 || strlen($name) === 0)) {
        error(400);
    }

    $stmt = db_exec("
            UPDATE tucal.friend
            SET nickname = :name
            WHERE account_nr_2 = (SELECT account_nr FROM tucal.v_account WHERE mnr = :mnr) AND
                  account_nr_1 = :me", [
        'name' => $name,
        'me' => $USER['nr'],
        'mnr' => $mnr,
    ]);

    echo '{"status":"success","message":null,"data":null}' . "\n";

    tucal_exit();
}
