<?php

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
