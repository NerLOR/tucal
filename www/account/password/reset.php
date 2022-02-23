<?php

global $USER;

require "../../.php/session.php";
force_user_login(null, false);

$success = send_email($USER['email_address_1'], 'Test email', 'Hello :D');

if ($success) {
    echo "Email successfully sent";
} else {
    echo "Waiting for email to be sent";
}

