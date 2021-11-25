<?php

require "../.php/database.php";

$info = $_SERVER['PATH_INFO'] ?? '';

header('Content-Type: application/json; charset=UTF-8');
header("Cache-Control: private, no-cache");

switch ($info) {
    case '/rooms': rooms();
}

$content = '{"status":"error","message":""}' . "\n";
header("Status: 404");
header("Content-Length: " . strlen($content));
echo $content;
exit();


function rooms() {
    $res = db_exec("SELECT r.room_nr, r.room_code, r.tiss_code, r.room_name, r.room_suffix, r.room_name_short,
                  r.room_alt_name, r.room_name_normal, lt.room_code AS lt_room_code, lt.lt_name
                  FROM tucal.v_room r LEFT JOIN tucal.v_lecture_tube lt ON lt.room_nr = r.room_nr");
    $arr = $res->fetchAll();

    $content = '{"status":"success","message":null,"data":[' . "\n";
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
        $content .= json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        if ($i !== sizeof($arr) - 1) $content .= ",";
        $content .= "\n";
    }
    $content .= "]}\n";
    header("Content-Length: " . strlen($content));
    echo $content;
    exit();
}

