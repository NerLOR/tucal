<?php

const JSON_FLAGS = JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES;

/**
 * Uses random_bytes() to generate a cryptographically secure base58 token
 * @param int $len The length of the token to generate
 * @param null|string $table Optional name of the table to check against
 * @param string $column Optional name of the column to check against
 * @param bool $db_mode If true, use _DB
 * @return string Returns a cryptographically secure token with length $len
 * @throws Exception If no appropriate source of randomness can be found
 */
function generate_token(int $len, string $table = null, string $column = 'token', bool $db_mode = false): string {
    $ALPHA = '123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ';
    $MIN = 0;
    $MAX = strlen($ALPHA) - 1;

    if ($db_mode) {
        $stmt = ($table !== null) ? _db_prepare("SELECT COUNT(*) FROM $table WHERE $column = ?") : null;
    } else {
        $stmt = ($table !== null) ? db_prepare("SELECT COUNT(*) FROM $table WHERE $column = ?") : null;
    }

    do {
        $token = '';
        $bytes = random_bytes($len);
        $all = 0;
        for ($i = 0; $i < $len; $i++) {
            $all += ord($bytes[$i]);
            $token .= $ALPHA[$MIN + ($all % ($MAX - $MIN))];
        }

        if ($stmt !== null) {
            $stmt->execute([$token]);
            if ($stmt->fetchColumn() == 0)
                break;
        }
    } while ($stmt !== null);

    return $token;
}

function http_message(int $status): string {
    switch ($status) {
        case 400: return 'Bad Request';
        case 401: return 'Unauthorized';
        case 403: return 'Forbidden';
        case 404: return 'Not Found';
        case 409: return 'Conflict';
        case 410: return 'Gone';
        case 500: return 'Internal Server Error';
        case 501: return 'Not Implemented';
        default: return "$status";
    }
}

function force_user_login(string $location = null, bool $verified = true) {
    global $USER;
    if (!isset($USER) || ($verified && !$USER['verified'])) {
        $_SESSION['opts']['redirect'] = $location ?? $_SERVER['REQUEST_URI'];
        redirect(!isset($USER) ? '/account/login' : '/account/verify');
    }
}

function redirect(string $location, bool $tucal_exit = true) {
    // Use Necronda web server default error documents
    header("Status: 303");
    header("Location: $location");
    header("Content-Type: text/html");
    header("Content-Length: 0");
    header("Content-Security-Policy: default-src 'unsafe-inline' 'self' data:");
    if ($tucal_exit) {
        tucal_exit();
    } else {
        exit();
    }
}

function base32_decode(string $data): string {
    $alpha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
    $data .= '========';
    $plain = '';
    for ($i = 0; $i < strlen($data); $i += 8) {
        $block = substr($data, $i, 8);
        if ($block[0] === '=') {
            break;
        }
        $val = 0;
        $min = 0;
        for ($j = 0; $j < 8; $j++) {
            $pos = strpos($alpha, $block[$j]);
            if ($pos === false) {
                if ($j <= 3) {
                    $min = 4;
                } elseif ($j <= 4) {
                    $min = 3;
                } elseif ($j <= 6) {
                    $min = 2;
                } elseif ($j <= 7) {
                    $min = 1;
                }
                break;
            }
            $val |= $pos << ((7 - $j) * 5);
        }
        for ($j = 4; $j >= $min; $j--) {
            $plain .= chr(($val >> ($j * 8)) & 0xFF);
        }
    }
    return $plain;
}

function echo_account($row, $uri = null, $editable = false) {
    echo "<a class=\"account\" data-username=\"$row[username]\" data-nickname=\"$row[nickname]\" data-mnr=\"$row[mnr]\"";
    if ($uri !== null) echo " href=\"$uri\"";

    echo '><div>';
    echo '<img src="' . ($row['avatar_uri'] ?? '/res/avatars/default.png') . '" alt="' . _('Profile picture') . '"/>';
    echo "<div>";
    echo "<span class=\"name\"" . ($editable ? ' contenteditable="true"' : '') . ">" . htmlspecialchars($row['nickname'] ?? $row['username']) . "</span>";
    echo '<div class="sub' . ($row['nickname'] ? ' has-nickname' : '') . '">';
    echo "<span class=\"mnr\">$row[mnr]</span>";
    echo "<span class=\"username\">$row[username]</span>";
    echo "</div></div></div></a>";
}

function echo_job(string $jobId, string $successUrl = null, string $errorUrl = null) {
    echo "<div class='job-viewer' data-job-id='$jobId'";

    $stmt = db_exec("SELECT job_id, status, error_msg, data FROM tucal.v_job WHERE job_id = ?", [$jobId]);
    $rows = $stmt->fetchAll();
    if (sizeof($rows) === 0) {
        echo ' data-job-invalid="1"';
    } else {
        $row = $rows[0];
        $rawData = json_decode($row[3], true);
        $data = [
            'id' => $row[0],
            'status' => $row[1],
            'error_msg' => $row[2],
            'data' => $rawData !== [] ? $rawData : null,
        ];
    }

    if ($successUrl) echo ' data-success-href="' . htmlspecialchars($successUrl) . '"';
    if ($errorUrl) echo ' data-error-href="' . htmlspecialchars($errorUrl) . '"';
    if (isset($data)) {
        echo ' data-job="' . htmlspecialchars(json_encode($data, JSON_FLAGS)) . '"';
    }
    echo '></div>';
}

function send_email(?string $address, string $subject, string $msg, string $reply_to = null, string $from_name = null, string $details = null): bool {
    global $TUCAL;

    $msg .= "\n\n-- \n" .
        "This is an automatically generated and sent message.\n" .
        "If you did not take any action to receive such a message you may safely ignore this message.\n" .
        "For more information visit https://$TUCAL[hostname]/";
    if ($details !== null) $msg .= "\n\n$details";

    $stmt = db_exec("
            INSERT INTO tucal.message (reply_to_address, to_address, from_name, subject, message)
            VALUES (:reply, :to, :from, :subj, :msg)
            RETURNING message_nr", [
        'reply' => $reply_to,
        'to' => $address,
        'from' => $from_name,
        'subj' => $subject,
        'msg' => $msg,
    ]);
    $nr = $stmt->fetchAll()[0][0];

    $stmt = db_prepare("SELECT send_ts FROM tucal.message WHERE message_nr = :nr");
    for ($i = 0; $i < 3; $i++) {
        sleep(1);
        $stmt->execute(['nr' => $nr]);
        $send = $stmt->fetchAll()[0][0];
        if ($send !== null)
            return true;
    }
    return false;
}

function check_password(string $password): bool {
    global $USER;

    $stmt = db_exec("
            SELECT (pwd_hash = crypt(:pwd, pwd_salt)) AS pwd_match
            FROM tucal.password p
            WHERE account_nr = :nr", [
        'nr' => $USER['nr'],
        'pwd' => $password,
    ]);
    $data = $stmt->fetchAll(PDO::FETCH_ASSOC);
    if (sizeof($data) === 0) {
        return false;
    }

    $row = $data[0];
    if (!$row['pwd_match']) {
        return false;
    }

    return true;
}

function login(int $accountNr) {
    global $USER;
    if (isset($USER) && $USER['administrator']) {
        $USER['opts']['impersonate_account_nr'] = $accountNr;
    } else {
        $USER = ['_nr' => $accountNr];
    }
}

function logout(): bool {
    global $USER;
    if (!isset($USER)) {
        return false;
    } elseif ($USER['impersonated']) {
        unset($_SESSION['opts']['impersonate_account_nr']);
        return true;
    } else {
        unset($GLOBALS['USER']);
        return false;
    }
}

function schedule_job(array $job_args, int $delay = 0): array {
    $sock = fsockopen('unix:///var/tucal/scheduler.sock', -1, $errno, $errstr);
    if (!$sock)
        throw new RuntimeException("Unable to contact scheduler: $errstr");

    $data = "";
    if ($delay > 0) $data .= "$delay ";
    $data .= implode(" ", $job_args);

    fwrite($sock, "$data\n");
    $res = fread($sock, 256);

    if (substr($res, 0, 6) === 'error:')
        throw new RuntimeException(trim(substr($res, 6)));

    $lines = explode("\n", $res);
    $res = explode(' ', trim($lines[0]));
    $pid = null;
    if (sizeof($lines) > 1 && strlen(trim($lines[1])) > 0) {
        $pid = (int) $lines[1];
    } elseif ($delay < 1) {
        $res = fread($sock, 256);
        $lines = array_merge($lines, explode("\n", $res));
        $pid = trim($lines[1]);
        if (strlen($pid) > 0) {
            $pid = (int) $pid;
        } else {
            $pid = null;
        }
    }

    fclose($sock);

    // job_nr, job_id, pid
    return [(int) $res[0], $res[1], $pid];
}
