<?php

global $USER;
global $TITLE;
global $TUCAL;
global $STATUS;

require "../../.php/session.php";
require "../../.php/main.php";

$errorMsg = null;
$errors = [
    "mnr" => null,
];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $mnr = $_POST['mnr'] ?? null;

    if ($mnr === null) {
        header("Status: 400");
        goto doc;
    } elseif (isset($USER) && $USER['mnr_int'] !== (int) $mnr) {
        header("Status: 400");
        $errors['mnr'] = 'Wrong';
        goto doc;
    }

    db_transaction();
    try {
        $stmt = db_exec("
                    SELECT account_nr, email_address_1, options
                    FROM tucal.v_account
                    WHERE mnr = ?", [$mnr]);
        $data = $stmt->fetchAll();
        if (sizeof($data) === 0) {
            db_rollback();
            header("Status: 404");
            $errors['mnr'] = 'No associated account';
            goto doc;
        }
        $row = $data[0];
        $nr = $row[0];
        $email = $row[1];
        $opts = json_decode($row[2], true);

        $token = generate_token(16, 'tucal.token');
        $stmt = db_exec("
                    INSERT INTO tucal.token (account_nr, usage, token, token_short, valid_ts)
                    VALUES (:nr, 'reset-password', :token, NULL, now() + INTERVAL '15 minutes')", [
                'nr' => $nr,
                'token' => $token,
        ]);
    } catch (Exception $e) {
        db_rollback();
        header("Status: 500");
        $errorMsg = $e->getMessage();
        goto doc;
    }
    db_commit();

    $user = $USER;
    $USER = ['opts' => ['locale' => $opts['locale']]];
    init_locale();
    $USER = $user;

    $link = "https://$TUCAL[hostname]/account/password/?token=$token";
    $msg = sprintf(_ctx('email', 'Reset password'), $link);
    $res = send_email($email, '[TUcal] ' . _('Reset password'), $msg);

    redirect("/account/password/reset?status=" . ($res ? "sent" : "sending"));
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET' && $_SERVER['REQUEST_METHOD'] !== 'HEAD') {
    $STATUS = 405;
    header("Allow: HEAD, GET, POST");
}

doc:
$status = $_GET['status'] ?? null;
$TITLE = [_('Reset Password')];
require "../../.php/header.php";
?>
<main class="w1">
    <section>
        <h1><?php echo _('Reset Password');?></h1>
<?php if ($status === null) {?>

        <form class="panel" action="/account/password/reset" method="post">
            <p><?php echo _('Reset password (description)');?></p>
            <div class="text<?php echo $errors['mnr'] ? " error" : "";?>">
                <input name="mnr" id="mnr" type="text" placeholder=" " value="<?php echo htmlspecialchars($_POST['mnr'] ?? '');?>" pattern="[0-9]{7,8}" required/>
                <label for="mnr"><?php echo _('Matriculation number');?></label>
                <label for="mnr"><?php if ($errors['mnr']) echo _($errors['mnr']);?></label>
            </div>
            <button type="submit"><?php echo _('Reset password');?></button>
        </form>
<?php if ($errorMsg !== null) { ?>

        <div class="container error"><?php echo $errorMsg;?></div>
<?php } ?>
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
require "../../.php/footer.php";
