<?php

global $TITLE;
global $USER;
global $STATUS;

require "../.php/session.php";
force_user_login(null, false);
require "../.php/main.php";

$error = false;
$errorMsg = null;
$errors = [
    'mnr' => null,
    'pw' => null,
];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $mnr = $_POST['mnr'] ?? null;
    $pw = $_POST['password'] ?? null;
    $check = $_POST['delete-account'] ?? null;

    if ($mnr === null || $pw === null || $check !== 'accept') {
        header("Status: 400");
        goto doc;
    }

    if (((int) $mnr) !== $USER['mnr_int']) {
        $errors['mnr'] = 'Wrong';
        header("Status: 403");
        $error = true;
    }

    if (!check_password($pw)) {
        $errors['pw'] = 'Wrong';
        header("Status: 403");
        $error = true;
    }

    if ($error) goto doc;

    db_transaction();
    try {
        db_exec("DELETE FROM tucal.account WHERE account_nr = :nr", ['nr' => $USER['nr']]);
    } catch (Exception $e) {
        db_rollback();
        header("Status: 500");
        $errorMsg = $e->getMessage();
        goto doc;
    }
    db_commit();
    unset($USER);

    redirect("/");
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET' && $_SERVER['REQUEST_METHOD'] !== 'HEAD') {
    $STATUS = 405;
    header("Allow: HEAD, GET, POST");
}

doc:
$TITLE = [_('Delete Account')];
require "../.php/header.php";
?>
<main class="w1">
    <section class="red">
        <h1><?php echo _('Delete Account'); ?></h1>
        <form name="delete-account" action="/account/delete" method="post" class="panel">
            <div class="text<?php echo $errors['mnr'] ? " error" : ""; ?>">
                <input name="mnr" id="mnr" type="text" placeholder=" " pattern="[0-9]{7,8}" value="<?php echo htmlentities($_POST['mnr'] ?? ''); ?>" required/>
                <label for="mnr"><?php echo _('Matriculation number'); ?></label>
                <label for="mnr"><?php if ($errors['mnr']) echo _($errors['mnr']); ?></label>
            </div>
            <div class="text<?php echo $errors['pw'] ? " error" : ""; ?>">
                <input name="password" id="password" type="password" placeholder=" " value="<?php echo htmlentities($_POST['password'] ?? ''); ?>" required/>
                <label for="password"><?php echo _('Password'); ?></label>
                <label for="password"><?php if ($errors['pw']) echo _($errors['pw']); ?></label>
            </div>
            <div class="container red">
                <input name="delete-account" id="delete-account" type="checkbox" value="accept" required/>
                <label for="delete-account"><?php echo _('Account deletion warning (description)'); ?></label>
            </div>
            <button type="submit" class="red"><?php echo _('Delete account'); ?></button>
        </form>
<?php if ($errorMsg !== null) { ?>
        <div class="container error"><?php echo $errorMsg; ?></div>
<?php } ?>
        <p class="center small">
            <a href="/account/password/reset"><?php echo _('Forgot password'); ?></a>.
        </p>
    </section>
</main>
<?php
require "../.php/footer.php";
