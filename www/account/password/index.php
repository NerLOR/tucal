<?php

global $TITLE;
global $USER;
global $LOCALE;
global $LOCALES;
global $STATUS;

require "../../.php/session.php";
require "../../.php/main.php";

$tokenInvalid = false;
$error = false;
$errorMsg = null;
$errors = [
    'pwd' => null,
    'pw1' => null,
    'pw2' => null,
];

$token = $_GET['token'] ?? null;
if ($token !== null) {
    $stmt = db_exec("SELECT account_nr, usage, valid FROM tucal.v_token WHERE token = ?", [$token]);
    $rows = $stmt->fetchAll();
    if (sizeof($rows) === 0) {
        $tokenInvalid = true;
        goto doc;
    }

    $row = $rows[0];
    if ($row[1] !== 'reset-password' || !$row[2]) {
        $tokenInvalid = true;
        goto doc;
    }

    $nr = $row[0];
    if (!isset($USER) || $USER['nr'] !== $nr) {
        $USER = ['nr' => $nr];
        redirect("/account/password/?token=$token");
    }
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    force_user_login(null, false);
    $cur = $_POST['current-password'] ?? null;
    $pw1 = $_POST['new-password'] ?? null;
    $pw2 = $_POST['repeat-new-password'] ?? null;

    if ($pw1 === null || $pw2 === null || ($token === null && $cur === null)) {
        header("Status: 400");
        goto doc;
    }

    if (strlen($pw1) < 6) {
        $errors['pw1'] = 'Too short';
        $error = 400;
    }

    if ($pw1 !== $pw2) {
        $errors['pw2'] = 'Does not match';
        $error = 400;
    }

    try {
        db_transaction();

        if ($cur !== null) {
            $stmt = db_exec("
                        SELECT (pwd_hash = crypt(:pwd, pwd_salt)) AS pwd_match
                        FROM tucal.password p
                        WHERE account_nr = :nr", [
                    'pwd' => $cur,
                    'nr' => $USER['nr'],
            ]);

            $data = $stmt->fetchAll(PDO::FETCH_ASSOC);
            if (sizeof($data) === 0) {
                db_rollback();
                $errorMsg = _('Unknown error');
                header("Status: 500");
                goto doc;
            }

            $row = $data[0];
            if (!$row['pwd_match']) {
                db_rollback();
                $errors['pwd'] = 'Wrong';
                header("Status: 401");
                goto doc;
            }
        } else {
            db_exec("DELETE FROM tucal.token WHERE token = ?", [$token]);
        }

        if ($error !== false) {
            db_rollback();
            header("Status: $error");
            goto doc;
        }

        $stmt = db_exec("
                    UPDATE tucal.password
                    SET pwd_salt = gen_salt('bf'),
                        pwd_hash = NULL,
                        update_ts = now()
                    WHERE account_nr = :nr", [
                'nr' => $USER['nr'],
        ]);

        $stmt = db_exec("
                    UPDATE tucal.password
                    SET pwd_hash = crypt(:pwd, pwd_salt)
                    WHERE account_nr = :nr", [
                'nr' => $USER['nr'],
                'pwd' => $pw1,
        ]);

        if ($token !== null) $USER['verified'] = true;
        db_commit();
    } catch (Exception $e) {
        db_rollback();
        header("Status: 500");
        $errorMsg = $e->getMessage();
        goto doc;
    }

    redirect('/account/');
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET' && $_SERVER['REQUEST_METHOD'] !== 'HEAD') {
    $STATUS = 405;
    header("Allow: HEAD, GET, POST");
}

doc:
if ($tokenInvalid) {
    header("Status: 410");
}

$TITLE = [($token === null) ? _('Change Password') : _('Reset Password')];
require "../../.php/header.php";
?>
<main class="w1">
    <section>
        <h1><?php echo ($token === null) ? _('Change Password') : _('Reset Password');?></h1>
<?php if (!$tokenInvalid) { ?>

        <form name="change-password" action="/account/password/<?php if ($token !== null) echo "?token=" . htmlspecialchars($token);?>" method="post" class="panel">
<?php if ($token === null) {?>

            <div class="text<?php echo $errors['pwd'] ? " error" : "";?>">
                <input type="password" name="current-password" id="current-password" placeholder=" " value="<?php echo htmlspecialchars($_POST['current-password'] ?? '');?>" required/>
                <label for="current-password"><?php echo _('Current password');?></label>
                <label for="current-password"><?php if ($errors['pwd']) echo _($errors['pwd']);?></label>
            </div>
<?php } ?>

            <div class="text<?php echo $errors['pw1'] ? " error" : "";?>">
                <input type="password" name="new-password" id="new-password" placeholder=" " value="<?php echo htmlspecialchars($_POST['new-password'] ?? '');?>" required/>
                <label for="new-password"><?php echo _('New password');?></label>
                <label for="new-password"><?php if ($errors['pw1']) echo _($errors['pw1']);?></label>
            </div>
            <div class="text<?php echo $errors['pw2'] ? " error" : "";?>">
                <input type="password" name="repeat-new-password" id="repeat-new-password" placeholder=" " value="<?php echo htmlspecialchars($_POST['repeat-new-password'] ?? '');?>" required/>
                <label for="repeat-new-password"><?php echo _('Repeat new password');?></label>
                <label for="repeat-new-password"><?php if ($errors['pw2']) echo _($errors['pw2']);?></label>
            </div>
            <button type="submit"><?php echo ($token === null) ? _('Change password') : _('Reset password');?></button>
        </form>
<?php if ($errorMsg !== null) { ?>

        <div class="container error"><?php echo $errorMsg;?></div>
<?php } ?>
<?php } else { ?>

        <div class="container error"><?php echo _('This link is invalid. Please try again.');?></div>
<?php } ?>

        <p class="center small">
            <a href="/account/password/reset"><?php echo _('Forgot password');?></a>.
        </p>
    </section>
</main>
<?php
require "../../.php/footer.php";
