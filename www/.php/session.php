<?php
require "database.php";
require "utils.php";
require "locale.php";

global $USER;
global $LOCALE;

$COOKIE_AGE = 15768000;  // 6 months

function tucal_exit(bool $db_error = false) {
    global $USER;
    if (!$db_error) {
        db_exec("UPDATE tucal.session SET account_nr = :acc_nr, options = :opts WHERE session_nr = :nr", [
            'nr' => $_SESSION['nr'],
            'acc_nr' => isset($USER) ? $USER['nr'] : null,
            'opts' => json_encode($_SESSION['opts']),
        ]);
        if (isset($USER)) {
            db_exec("UPDATE tucal.account SET options = :opts WHERE account_nr = :nr", [
                'nr' => $USER['nr'],
                'opts' => isset($USER['opts']) ? json_encode($USER['opts']) : '{}',
            ]);
        }
        try {
            db_commit();
        } catch (Exception $e) {}
    }
    exit();
}

db_transaction();
db_exec("LOCK TABLE tucal.session IN SHARE ROW EXCLUSIVE MODE");
db_exec("LOCK TABLE tucal.account IN SHARE ROW EXCLUSIVE MODE");

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
            'opts' => json_decode($s['session_opts'], true),
        ];
        if ($s['mnr'] !== null) {
            $USER = [
                'nr' => $s['account_nr'],
                'mnr' => $s['mnr_normal'],
                'mnr_int' => $s['mnr'],
                'username' => $s['username'],
                'email_address_1' => $s['email_address_1'],
                'email_address_2' => $s['email_address_2'],
                'verified' => $s['verified'],
                'avatar_uri' => $s['avatar_uri'],
                'opts' => json_decode($s['account_opts'], true),
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
        'opts' => json_decode('{}', true),
    ];
}

init_locale();

$timefmt = gmdate('D, d M Y H:i:s', time() + $COOKIE_AGE) . ' GMT';
header('Set-Cookie: ' . implode('; ', [
        "tucal_session=$_SESSION[token]",
        "Path=/",
        "HttpOnly",
        "Secure",
        "SameSite=Strict",
        "MaxAge=$COOKIE_AGE",
        "Expires=$timefmt",
    ]), false);
