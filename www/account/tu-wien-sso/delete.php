<?php

global $TITLE;
global $USER;
global $STATUS;

require "../../.php/session.php";
force_user_login(null, false);
if (!$USER['sso_credentials']) {
    redirect("/account/");
}

require "../../.php/main.php";

$errorMsg = null;
$errors = [
    'mnr' => null,
];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $mnr = $_POST['mnr'] ?? null;

    if ($mnr === null) {
        header("Status: 400");
        goto doc;
    }

    if (((int) $mnr) !== $USER['mnr_int']) {
        $errors['mnr'] = 'Wrong';
        header("Status: 403");
        goto doc;
    }

    db_transaction();
    try {
        db_exec("DELETE FROM tucal.sso_credential WHERE account_nr = :nr", ['nr' => $USER['nr']]);
    } catch (Exception $e) {
        db_rollback();
        header("Status: 500");
        $errorMsg = $e->getMessage();
        goto doc;
    }
    db_commit();

    redirect("/account/");
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET' && $_SERVER['REQUEST_METHOD'] !== 'HEAD') {
    $STATUS = 405;
    header("Allow: HEAD, GET, POST");
}

doc:
$TITLE = [_('Delete SSO Credentials')];
require "../../.php/header.php";
?>
<main class="w1">
    <section>
        <h1><?php echo _('Delete SSO Credentials'); ?></h1>
        <form name="delete-sso-credentials" action="/account/tu-wien-sso/delete" method="post" class="panel">
            <div class="text<?php echo $errors['mnr'] ? " error" : ""; ?>">
                <input name="mnr" id="mnr" type="text" placeholder=" " pattern="[0-9]{7,8}" value="<?php echo htmlentities($_POST['mnr'] ?? ''); ?>" required/>
                <label for="mnr"><?php echo _('Matriculation number'); ?></label>
                <label for="mnr"><?php if ($errors['mnr']) echo _($errors['mnr']); ?></label>
            </div>
            <button type="submit" class="red"><?php echo _('Delete SSO Credentials'); ?></button>
        </form>
        <?php if ($errorMsg !== null) { ?>
            <div class="container error"><?php echo $errorMsg; ?></div>
        <?php } ?>
    </section>
</main>
<?php
require "../../.php/footer.php";
