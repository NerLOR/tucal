<?php

global $TITLE;
global $USER;
global $STATUS;
global $TUCAL;

require "../.php/session.php";
force_user_login(null, false);
require "../.php/main.php";

if ($USER['verified']) {
    redirect('/account/tu-wien-sso');
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $token = generate_token(16, 'tucal.token');
    $stmt = db_exec("
                    INSERT INTO tucal.token (account_nr, usage, token, token_short, valid_ts)
                    VALUES (:nr, 'verify-account', :token, NULL, now() + INTERVAL '15 minutes')", [
        'nr' => $USER['nr'],
        'token' => $token,
    ]);

    $link = "https://$TUCAL[hostname]/account/verify?token=$token";
    $msg = sprintf(_ctx('email', 'Verify account'), $link);
    $res = send_email($USER['email_address_1'], '[TUcal] ' . _('Verify account'), $msg);

    redirect("/account/verify?status=" . ($res ? "sent" : "sending"));
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET' && $_SERVER['REQUEST_METHOD'] !== 'HEAD') {
    $STATUS = 405;
    header("Allow: HEAD, GET, POST");
}

$token = $_GET['token'] ?? null;
$status = $_GET['status'] ?? null;
$tokenInvalid = false;

if ($token !== null) {
    $stmt = db_exec("SELECT account_nr, usage, valid FROM tucal.v_token WHERE token = ?", [$token]);
    $rows = $stmt->fetchAll();
    if (sizeof($rows) === 0) {
        $tokenInvalid = true;
        goto doc;
    }

    $row = $rows[0];
    if ($row[1] !== 'verify-account' || !$row[2]) {
        $tokenInvalid = true;
        goto doc;
    }

    $nr = $row[0];
    if (!isset($USER) || $USER['nr'] !== $nr) {
        if ($USER['impersonated']) {
            $_SESSION['opts']['impersonate_account_nr'] = $nr;
        } else {
            $USER = ['nr' => $nr];
        }
        redirect("/account/verify?token=$token");
    }

    db_exec("DELETE FROM tucal.token WHERE token = ?", [$token]);
    $USER['verified'] = true;

    $redirect = $_SESSION['opts']['redirect'] ?? '/account/tu-wien-sso';
    unset($_SESSION['opts']['redirect']);
    redirect($redirect);
}

doc:
$TITLE = [_('Verify Account')];
require "../.php/header.php";
?>
<main class="w1">
    <section>
        <h1><?php echo _('Verify Account'); ?></h1>
<?php if ($tokenInvalid) { ?>

        <div class="container error"><?php echo _('This link is invalid. Please try again.'); ?></div>
<?php } elseif ($status === null) { ?>

        <form class="panel">
            <p><?php echo _('SSO verification (description)'); ?></p>
            <a class="button" href="/account/tu-wien-sso"><?php echo _('SSO verification'); ?></a>
        </form>
        <form action="/account/verify" method="post" class="panel">
            <hr data-content="<?php echo strtoupper(_('or')); ?>"/>
            <p><?php echo _('Email verification (description)'); ?></p>
            <div class="text">
                <input name="email-address" id="email-address" type="email" placeholder=" " value="<?php echo $USER['email_address_1']; ?>" readonly required/>
                <label for="email-address"><?php echo _('Email address'); ?></label>
            </div>
            <button type="submit" name="mode" value="email"><?php echo _('Email verification'); ?></button>
        </form>
<?php } else {
    if ($status === 'sent') {
        echo "<p class='center'>" . _('Email sent (description)') . "</p>";
    } elseif ($status === 'sending') {
        echo "<p class='center'>" . _('Email sending (description)') . "</p>";
    }
}
?>

    </section>
</main>
<?php
require "../.php/footer.php";
