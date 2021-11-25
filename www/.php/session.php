<?php
require "database.php";
require "utils.php";
require "locale.php";

global $USER;
global $LOCALE;

$COOKIE_AGE = 15768000;  // 6 months

function tucal_exit() {
    global $USER;
    try {
        db_rollback();
    } catch (Exception $e) {}
    db_exec("UPDATE tucal.session SET last_ts = now(), mnr = :mnr, options = :opts WHERE session_nr = :nr", [
        'nr' => $_SESSION['nr'],
        'mnr' => isset($USER) ? $USER['mnr'] : null,
        'opts' => json_encode($_SESSION['opts']),
    ]);
    exit();
}

unset($_SESSION);
unset($USER);
if (isset($_COOKIE['tucal_session'])) {
    $stmt = db_exec("SELECT * FROM tucal.v_session WHERE token = ?", [$_COOKIE['tucal_session']]);
    $sessions = $stmt->fetchAll(PDO::FETCH_ASSOC);

    if (sizeof($sessions) > 0) {
        $s = $sessions[0];
        $_SESSION = [
            'nr' => $s['session_nr'],
            'token' => $s['token'],
            'opts' => json_decode($s['session_opts']),
        ];
        if ($s['mnr'] !== null) {
            $USER = [
                'mnr' => $s['mnr'],
                'username' => $s['username'],
                'opts' => json_decode($s['account_opts']),
            ];
        }
    }
}

if (!isset($_SESSION)) {
    $token = generate_token(64, 'tucal.session');
    $stmt = db_exec("INSERT INTO tucal.session (token) VALUES (?) RETURNING session_nr", [$token]);

    $_SESSION = [
        'nr' => $stmt->fetch()[0],
        'token' => $token,
        'opts' => json_decode('{}'),
    ];
}

init_locale();

header('Set-Cookie: ' . implode('; ', [
        "tucal_session=$_SESSION[token]",
        "Path=/",
        "HttpOnly",
        "Secure",
        "SameSite=Strict",
        "MaxAge=$COOKIE_AGE",
    ]), false);
