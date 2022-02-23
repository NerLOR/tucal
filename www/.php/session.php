<?php

require "default.php";
require "locale.php";

global $USER;
global $LOCALE;

$COOKIE_AGE = 15768000;  // 6 months

function tucal_exit() {
    global $USER;
    _db_exec("UPDATE tucal.session SET account_nr = :acc_nr, options = :opts WHERE session_nr = :nr", [
        'nr' => $_SESSION['nr'],
        'acc_nr' => isset($USER) ? $USER['nr'] : null,
        'opts' => json_encode($_SESSION['opts']),
    ]);
    if (isset($USER) && isset($USER['opts'])) {
        _db_exec("
            UPDATE tucal.account
            SET username = :name,
                verified = :verified,
                options = :opts
            WHERE account_nr = :nr", [
                'nr' => $USER['nr'],
                'name' => $USER['username'],
                'verified' => $USER['verified'] ? 1 : 0,
                'opts' => json_encode($USER['opts']),
        ]);
    }
    try {
        _db_commit();
    } catch (Exception $e) {}
    exit();
}

_db_transaction();
_db_exec("LOCK TABLE tucal.session IN ROW EXCLUSIVE MODE");

unset($_SESSION);
unset($USER);
if (isset($_COOKIE['tucal_session'])) {
    $stmt = _db_exec("SELECT * FROM tucal.v_session WHERE token = ?", [$_COOKIE['tucal_session']]);
    $sessions = $stmt->fetchAll(PDO::FETCH_ASSOC);

    if (sizeof($sessions) > 0) {
        $s = $sessions[0];
        $_SESSION = [
            'nr' => $s['session_nr'],
            'token' => $s['token'],
            'opts' => json_decode($s['session_opts'], true),
        ];
        if ($s['mnr'] !== null) {
            _db_exec("LOCK TABLE tucal.account IN ROW EXCLUSIVE MODE");
            $USER = [
                'nr' => $s['account_nr'],
                'id' => $s['account_id'],
                'mnr' => $s['mnr_normal'],
                'mnr_int' => $s['mnr'],
                'username' => $s['username'],
                'email_address_1' => $s['email_address_1'],
                'email_address_2' => $s['email_address_2'],
                'verified' => $s['verified'],
                'sso_credentials' => $s['sso_credentials'],
                'avatar_uri' => $s['avatar_uri'],
                'opts' => json_decode($s['account_opts'], true),
            ];
        }
    }
}

if (!isset($_SESSION)) {
    $token = generate_token(64, 'tucal.session', 'token', true);
    $stmt = _db_exec("INSERT INTO tucal.session (token) VALUES (?) RETURNING session_nr", [$token]);

    $_SESSION = [
        'nr' => $stmt->fetch()[0],
        'token' => $token,
        'opts' => json_decode('{}', true),
        'theme' => 'browser',
    ];
}

init_locale();

$timefmt = gmdate('D, d M Y H:i:s', time() + $COOKIE_AGE) . ' GMT';
header('Set-Cookie: ' . implode('; ', [
        "tucal_session=$_SESSION[token]",
        "Path=/",
        "HttpOnly",
        "Secure",
        "SameSite=Lax",
        "MaxAge=$COOKIE_AGE",
        "Expires=$timefmt",
    ]), false);
