<?php

require "../.php/session.php";

$info = explode('/', $_SERVER['PATH_INFO'] ?? '');

if (sizeof($info) < 2) {
    header("Status: 403");
    header("Content-Length: 0");
    exit();
} if (sizeof($info) === 2) {
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
    header("Status: 303");
    header("Location: /calendar/export/$token/");
    header("Content-Length: 0");
    exit();
}
$ext = ($file === '') ? $file_parts[1] : null;

if ($token !== 'asdf') {
    header("Status: 404");
    header("Content-Length: 0");
    exit();
}

if ($ext !== null && $file_parts[0] !== 'personal') {
    header("Status: 307");
    header("Location: /calendar/export/$token/personal.$ext");
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

echo 'Ich bin eine Datei :D';
