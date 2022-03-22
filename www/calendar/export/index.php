<?php

global $TUCAL;

require "../../.php/default.php";


$info = explode('/', $_SERVER['PATH_INFO'] ?? '');

if (sizeof($info) < 2) {
    header("Status: 400");
    header("Content-Length: 0");
    exit();
} elseif (sizeof($info) === 2) {
    $token = $info[1];
    header("Status: 308");
    header("Location: /calendar/export/$token/");
    header("Content-Length: 0");
    exit();
} elseif (sizeof($info) > 3) {
    header("Status: 404");
    header("Content-Length: 0");
    exit();
}

$token = $info[1];
$file = $info[2];

$file_parts = explode('.', $file);
if ($file !== '' && (sizeof($file_parts) !== 2 || !in_array($file_parts[1], ['ics', 'json', 'html']))) {
    redirect("/calendar/export/$token/", false);
}
$ext = ($file !== '') ? $file_parts[1] : null;

$stmt = db_exec("SELECT * FROM tucal.calendar_export WHERE token = :t", ['t' => $token]);
$rows = $stmt->fetchAll();
if (sizeof($rows) === 0) {
    header("Status: 404");
    header("Content-Length: 0");
    exit();
}
$exp = $rows[0];
$mnr = $exp['subject_mnr'];
$opts = json_decode($exp['options'], true);

if ($ext !== null && $file_parts[0] !== 'personal') {
    header("Status: 307");
    header("Location: /calendar/export/$token/personal.$ext");
    header("Content-Length: 0");
    exit();
}

$stmt = db_exec("
            SELECT SUM((account_nr_1 = :nr)::int)
            FROM tucal.friend f
                JOIN tucal.account a ON a.account_nr = f.account_nr_2
            WHERE mnr = :mnr
            GROUP BY account_nr_2
            UNION ALL
            SELECT (account_nr = :nr)::int
            FROM tucal.account
            WHERE mnr = :mnr", [
        'nr' => $exp['account_nr'],
        'mnr' => $mnr,
]);
$rows = $stmt->fetchAll();
if (sizeof($rows) === 0) {
    header("Status: 410");
    header("Content-Length: 0");
    exit();
} elseif ($rows[0][0] !== 1 && $rows[1][0] !== 1) {
    header("Status: 403");
    header("Content-Length: 0");
    exit();
}

if ($file === '') {
    $content = "<ul>\n";
    foreach (['personal.ics', 'personal.json', 'personal.html'] as $name) {
        $content .= "\t<li><a href=\"$name\">$name</a></li>\n";
    }
    $content .= "</ul>\n";
    header("Status: 300");
    header("Content-Type: text/html; charset=UTF-8");
    header("Content-Length: " . strlen($content));
    echo $content;
    exit();
}

$rooms = [];
$stmt = db_exec("
        SELECT room_nr, room_code, room_code_long, b.building_id, tiss_code, room_name, room_suffix,
               room_name_short, room_alt_name, room_name_normal, area, capacity, b.area_name, b.address, b.building_name
        FROM tucal.v_room r
            LEFT JOIN tucal.v_building b ON b.building_id = r.building_id");
while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    $rooms[$row['room_nr']] = $row;
}

$courses = [];
$stmt = db_exec("
        SELECT c.course_nr, c.name_de, c.name_en, c.type, a.acronym_1, a.acronym_2, a.short, a.program
        FROM tiss.course_def c
            LEFT JOIN tucal.course_acronym a ON a.course_nr= c.course_nr");
while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    $courses[$row['course_nr']] = $row;
}

$stmt = db_exec("
        SELECT e.event_nr, e.event_id, e.start_ts, e.end_ts, e.create_ts, e.update_ts, e.update_seq, e.room_nr, e.data,
               d.data AS user_data, l.course_nr, l.semester, l.name, g.group_id
        FROM tucal.event e
            JOIN tucal.external_event x ON x.event_nr = e.event_nr
            JOIN tucal.group_member m ON m.group_nr = e.group_nr
            JOIN tucal.account a ON a.account_nr = m.account_nr
            LEFT JOIN tucal.group g ON g.group_nr = e.group_nr
            LEFT JOIN tucal.group_link l ON l.group_nr = g.group_nr
            LEFT JOIN tucal.event_user_data d ON (d.event_nr, d.account_nr) = (e.event_nr, a.account_nr)
        WHERE a.mnr = :mnr AND NOT e.deleted AND
              (e.global OR (:mnr = ANY(SELECT u.mnr FROM tuwel.event_user eu
                                       JOIN tuwel.user u ON u.user_id = eu.user_id
                                       WHERE eu.event_id::text = x.event_id))) AND
              (m.ignore_from IS NULL OR e.start_ts < m.ignore_from) AND
              (m.ignore_until IS NULL OR e.start_ts >= m.ignore_until)
        GROUP BY e.event_nr, e.event_id, e.start_ts, e.end_ts, e.room_nr, e.group_nr, e.data, d.data,
                 l.course_nr, l.semester, l.name, g.group_id
        ORDER BY e.start_ts, length(l.name), e.data -> 'summary'", ["mnr" => $mnr]);

header("Cache-Control: private, no-cache");
if ($ext === 'ics') {
    header("Content-Type: text/calendar; charset=UTF-8");

    ical_line("BEGIN", ["VCALENDAR"]);
    ical_line("VERSION", ["2.0"]);
    ical_line("PRODID", ["TUcal"]);
    ical_line("X-WR-CALNAME", []);
    ical_line("X-WR-CALDESC", []);
    ical_line("X-WR-TIMEZONE", ["Europe/Vienna"]);
    ical_line("X-FROM-URL", ["https://$TUCAL[hostname]/calendar/export/$token/$file"]);
    ical_line("CALSCALE", ["GREGORIAN"]);

    $fn = fopen("europe-vienna.txt", "r");
    while ($fn && !feof($fn)) {
        $result = rtrim(fgets($fn), "\r\n");
        if (strlen($result) > 0) echo "$result\r\n";
    }
    fclose($fn);

    // ical_line("METHOD", ["PUBLISH"]);
} elseif ($ext === 'json') {
    header("Content-Type: application/json; charset=UTF-8");

    echo '{"events":[' . "\n";
} elseif ($ext === 'html') {
    header("Content-Type: text/html; charset=UTF-8");

?>
<!DOCTYPE html>
<html lang="de-AT">
<head>
    <title>Calendar Export</title>
    <style>
        * {
            font-family: 'Arial', sans-serif;
        }
    </style>
</head>
<body>
<?php
}

$first = true;
while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    $start = new DateTime($row['start_ts']);
    $end = new DateTime($row['end_ts']);
    $update = new DateTime($row['update_ts']);
    $create = new DateTime($row['create_ts']);

    $utcTz = new DateTimeZone("UTC");
    $tz = new DateTimeZone("Europe/Vienna");
    $start->setTimezone($tz);
    $end->setTimezone($tz);
    $update->setTimezone($tz);
    $create->setTimezone($tz);

    $data = json_decode($row['data'], true);
    $userData = json_decode($row['user_data'], true);
    $todo = ($row['start_ts'] === $row['end_ts']);

    $courseNr = $row['course_nr'];
    if ($courseNr !== null) {
        $courseNrLong = substr($courseNr, 0, 3) . '.' . substr($courseNr, 3);
        $course = $courses[$courseNr];
        $courseName = $course['acronym_1'] ?? $course['acronym_2'] ?? $course['short'] ?? $course['name_de'] ?? $courseNrLong;
    } else {
        $courseNrLong = null;
        $course = null;
        $courseName = null;
    }

    $roomNr = $row['room_nr'];
    if ($roomNr !== null) {
        $room = $rooms[$roomNr];
        $roomNameAbbr = $room['room_name_short'] ?? "#$roomNr";
        $roomName = $room['room_name'] ?? "#$roomNr";
        $roomSuffix = $room['room_suffix'] ?? null;
        $roomLoc = explode('/', $room['room_code'])[0];
        $roomLocLong = explode('/', $room['room_code_long'])[0];
    } else {
        $room = null;
        $roomNameAbbr = null;
        $roomName = null;
        $roomSuffix = null;
        $roomLoc = null;
        $roomLocLong = null;
    }

    if ($ext === 'ics') {
        $icalOpts = $opts['ical'] ?? [];
        $format = "Ymd\\THis";
        $formatZ = "$format\\Z";

        if ($userData['hidden'] ?? false) {
            continue;
        } elseif ($end < $start || $end->getTimestamp() - $start->getTimestamp() > 43_200) {
            continue;
        }

        $type = $data['type'];
        $types = $icalOpts['event_types'] ?? ['course', 'lecture', 'group'];
        if ($type === 'course' || $type === 'lecture') {
            if (!in_array('course', $types)) continue;
        } elseif ($type === 'group') {
            if (!in_array('group', $types)) continue;
        } elseif ($type !== 'deadline' && $type !== 'assignment') {
            if (!in_array('other', $types)) continue;
        }

        $todos = $icalOpts['todos'] ?? 'as_todos';
        $isTodo = ($todo && $todos == 'as_todos');

        if ($isTodo) {
            ical_line("BEGIN", ["VTODO"]);
            ical_line("DUE", [$start->format($format)], ["TZID=Europe/Vienna"]);
        } elseif ($todo && $todos === 'omitted') {
            continue;
        } else {
            ical_line("BEGIN", ["VEVENT"]);
            ical_line("DTSTART", [$start->format($format)], ["TZID=Europe/Vienna"]);
            ical_line("DTEND", [$end->format($format)], ["TZID=Europe/Vienna"]);
        }

        $summary = "";
        $desc = "";
        if ($courseName !== null) {
            $summary .= $courseName;
        } else {
            $summary .= $data['summary'];
        }

        if ($isTodo) {
            $summary .= " - $data[summary]";
        } elseif ($courseName !== null) {
            $desc .= $data['summary'];
        }

        ical_line("SUMMARY", [$summary]);
        ical_line("DESCRIPTION", [$desc]);

        $tuwMaps = $icalOpts['location_tuw_maps'] ?? true;
        $locMode = $icalOpts['location'] ?? 'room_abbr';

        $loc = null;
        $locLink = null;
        if ($room !== null) {
            $bName = ($room['building_name']) ? "$room[building_name], " : '';
            $addr = ($room['address']) ? " ($room[address], Wien Österreich)" : '';
            $fullAddr = "Technische Universität Wien$addr";
            $locLink = "https://tuw-maps.tuwien.ac.at/?q=$roomLoc";

            if ($locMode === 'room_abbr') {
                $loc = "$roomNameAbbr ($roomLocLong)";
            } else {
                $loc = $roomName;
                if ($roomSuffix) $loc .= " - $roomSuffix";
                $loc .= " ($roomLocLong)";
                if ($locMode !== 'room_name') {
                    if ($locMode !== 'campus') {
                        $loc .= $bName;
                        if ($locMode !== 'building') $loc .= ", $fullAddr";
                    }
                    $loc .= ", $room[area_name]";
                }
            }
            if ($tuwMaps) $loc .= "\n$locLink";
        }

        if ($loc !== null) {
            $altRep = [];
            if ($locLink !== null) $altRep [] = "ALTREP=\"$locLink\"";
            ical_line("LOCATION", [$loc], $altRep);
        }

        $categories = [];
        if ($courseNrLong !== null) {
            $categories[] = "$courseNrLong $course[type] $course[name_de] ($row[semester])";
        }

        ical_line("CATEGORIES", $categories);
        ical_line("CLASS", ["PUBLIC"]);

        if ($isTodo) {
            ical_line("STATUS", ["NEEDS-ACTION"]);
        } else {
            ical_line("STATUS", [strtoupper($data['status'] ?? 'CONFIRMED')]);
        }

        $create->setTimezone($utcTz);
        $update->setTimezone($utcTz);
        ical_line("UID", ["$row[event_id]@$TUCAL[hostname]"]);
        ical_line("CREATE", [$create->format($formatZ)]);
        ical_line("DTSTAMP", [$create->format($formatZ)]);
        ical_line("LAST-MODIFIED", [$update->format($formatZ)]);
        ical_line("SEQUENCE", ["$row[update_seq]"]);

        if ($isTodo) {
            ical_line("END", ["VTODO"]);
        } else {
            ical_line("END", ["VEVENT"]);
        }
    } elseif ($ext === 'json') {
        if (!$first) {
            echo ",\n";
        }
        echo json_encode([
                "id" => $row['event_id'],
        ], JSON_FLAGS);
    } elseif ($ext === 'html') {
        echo '<div class="event">';
        echo "<span>";
        echo $start->format("d.m.Y H:i");
        if (!$todo) {
            echo "–";
            echo $end->format("H:i");
        }
        echo "</span>";
        echo "<h1></h1>";
        echo "<h6>$row[event_id]</h6>";
        echo "</div><hr/>\n";
    }
    $first = false;
}

if ($ext === 'ics') {
    ical_line("END", ["VCALENDAR"]);
} elseif ($ext === 'json') {
    echo "\n]}\n";
} elseif ($ext === 'html') {
    echo "</body>\n</html>\n";
}

function ical_line(string $param, array $value, array $opts = []) {
    $value = str_replace("\r\n", "\n", $value);
    $opts = str_replace("\r\n", "\n", $opts);
    $value = str_replace("\r", "\n", $value);
    $opts = str_replace("\r", "\n", $opts);
    $value = preg_replace("/[,;\\\\]/", "\\\\\\0", $value);
    $opts = preg_replace("/[,;\\\\]/", "\\\\\\0", $opts);
    $value = str_replace("\n", "\\n", $value);
    $opts = str_replace("\n", "\\n", $opts);

    $valueStr =  implode(',', $value);
    $optsStr = implode(';', array_merge([$param], $opts));
    $line = "$optsStr:$valueStr";
    $len = strlen($line);

    $pos = 0;
    while ($pos < $len) {
        $part = substr($line, $pos, ($pos === 0) ? 75 : 74);
        $partLen = strlen($part);
        if ($pos > 0) {
            $part = " $part";
        }
        $pos += $partLen;
        echo "$part\r\n";
    }
}
