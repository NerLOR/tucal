<?php

global $TITLE;
global $USER;
global $LOCALE;
global $LOCALES;
global $STATUS;

require "../../.php/session.php";
force_user_login(null, false);

require "../../.php/main.php";

$error = false;
$errorMsg = null;
$errors = [
    'pwd' => null,
    'pw1' => null,
    'pw2' => null,
];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $token = $_GET['token'] ?? null;
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
                $errorMsg = _('Unknown error');
                header("Status: 500");
                goto doc;
            }

            $row = $data[0];
            if (!$row['pwd_match']) {
                $errors['pwd'] = 'Wrong';
                header("Status: 401");
                goto doc;
            }
        } else {

        }

        if ($error !== false) {
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

        db_commit();
    } catch (Exception $e) {
        db_rollback();
        header("Status: 500");
        $errorMsg = $e->getMessage();
        goto doc;
    }

    redirect('/account/');
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    $STATUS = 405;
    header("Allow: GET, POST");
}

doc:
$TITLE = [_('Change Password')];
require "../../.php/header.php";
?>
<main class="w1">
    <section>
        <h1><?php echo _('Change Password');?></h1>
        <form name="change-password" action="/account/password/" method="post" class="panel">
            <div class="text<?php echo $errors['pwd'] ? " error" : "";?>">
                <input type="password" name="current-password" id="current-password" placeholder=" " value="<?php echo htmlspecialchars($_POST['current-password'] ?? '');?>" required/>
                <label for="current-password"><?php echo _('Current password');?></label>
                <label for="current-password"><?php if ($errors['pwd']) echo _($errors['pwd']);?></label>
            </div>
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
            <button type="submit"><?php echo _('Change password');?></button>
        </form>
<?php if ($errorMsg !== null) { ?>
        <div class="container error"><?php echo $errorMsg;?></div>
<?php } ?>
        <p class="center small">
            <a href="/account/password/reset"><?php echo _('Forgot password');?></a>.
        </p>
    </section>
</main>
<?php
require "../../.php/footer.php";
