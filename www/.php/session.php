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
        'acc_nr' => isset($USER) ? $USER['_nr'] : null,
        'opts' => json_encode($_SESSION['opts']),
    ]);
    if (isset($USER) && isset($USER['opts'])) {
        _db_exec("
                UPDATE tucal.account
                SET username = :name,
                    verified = :verified,
                    avatar_uri = :avatar,
                    options = :opts
                WHERE account_nr = :nr", [
            'nr' => $USER['nr'],
            'name' => $USER['username'],
            'verified' => $USER['verified'] ? 1 : 0,
            'avatar' => $USER['avatar_uri'],
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
        $a = null;
        $_SESSION = [
            'nr' => $s['session_nr'],
            'token' => $s['token'],
            'opts' => json_decode($s['session_opts'], true),
        ];

        if ($s['administrator'] && isset($_SESSION['opts']['impersonate_account_nr'])) {
            $stmt = _db_exec("SELECT * FROM tucal.v_account WHERE account_nr = ?", [$_SESSION['opts']['impersonate_account_nr']]);
            $accounts = $stmt->fetchAll(PDO::FETCH_ASSOC);
            if (sizeof($accounts) > 0) {
                $a = $accounts[0];
            }
        }

        if ($a === null) unset($_SESSION['opts']['impersonate_account_nr']);

        if (!isset($USER) && $s['account_nr'] !== null) {
            _db_exec("LOCK TABLE tucal.account IN ROW EXCLUSIVE MODE");
            $u = $a ?? $s;
            $USER = [
                'nr' => $u['account_nr'],
                '_nr' => $s['account_nr'],
                'id' => $u['account_id'],
                'mnr' => $u['mnr_normal'],
                'mnr_int' => $u['mnr'],
                'username' => $u['username'],
                'email_address_1' => $u['email_address_1'],
                'email_address_2' => $u['email_address_2'],
                'verified' => $u['verified'],
                'administrator' => $u['administrator'],
                'sso_credentials' => $u['sso_credentials'],
                'avatar_uri' => $u['avatar_uri'],
                'opts' => json_decode($u['account_opts'] ?? $u['options'], true),
                'create_ts' => $u['account_create_ts'] ?? $u['create_ts'],
                'login_ts' => $u['account_login_ts'] ?? $u['login_ts'],
                'sync_ts' => $u['account_sync_ts'] ?? $u['sync_ts'],
                'impersonated' => ($a !== null),
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
