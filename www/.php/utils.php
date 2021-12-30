<?php

const JSON_FLAGS = JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES;

/**
 * Uses random_int() to generate a cryptographically secure base58 token
 * @param int $len The length of the token to generate
 * @param null|string $table Optional name of the table to check against
 * @param string $column Optional name of the column to check against
 * @return string Returns a cryptographically secure token with length $len
 * @throws Exception If no appropriate source of randomness can be found
 */
function generate_token(int $len, string $table = null, string $column = 'token'): string {
    $ALPHA = '123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ';
    $MIN = 0;
    $MAX = strlen($ALPHA) - 1;

    $stmt = ($table !== null) ? db_prepare("SELECT COUNT(*) FROM $table WHERE $column = ?") : null;

    do {
        $token = '';
        for ($i = 0; $i < $len; $i++)
            $token .= $ALPHA[random_int($MIN, $MAX)];

        if ($stmt !== null) {
            $stmt->execute([$token]);
            if ($stmt->fetchColumn() === 0)
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

function redirect(string $location) {
    // Use Necronda web server default error documents
    header("Status: 303");
    header("Location: $location");
    header("Content-Type: text/html");
    header("Content-Length: 0");
    header("Content-Security-Policy: default-src 'unsafe-inline' 'self' data:");
    tucal_exit();
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

function echo_account($row, $mnr = false, $uri = null) {
    echo '<a class="account"';
    if ($uri !== null) {
        echo " href=\"$uri\"";
    }
    echo '><div>';
    echo '<img src="/res/avatars/default.png" alt="' . _('Avatar') . '"/>';
    echo "<span class=\"username\">$row[username]";
    if ($row['verified']) {
        echo ' <span class="verified">✓</span>';
    }
    if ($mnr) {
        echo " <span class=\"mnr\">$row[mnr]</span>";
    }
    echo "</span></div></a>";
}
