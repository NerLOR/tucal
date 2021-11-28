<?php

global $TITLE;
global $USER;

require "../.php/session.php";
if (isset($USER)) {
    redirect('/account/');
}

require "../.php/main.php";

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $mnr = $_POST['mnr'] ?? null;
    $username = $_POST['username'] ?? null;

    if ($mnr === null || $username === null) {
        header("Status: 400");
        goto doc;
    }

    try {
        $stmt = db_exec("INSERT INTO tucal.account (mnr, username) VALUES (:mnr, :username) RETURNING account_nr", [
            'mnr' => $mnr,
            'username' => $username,
        ]);
        $nr = $stmt->fetch()[0];
        $USER = ['nr' => $nr];
    } catch (Exception $e) {
        db_rollback();
        header("Status: 409");
        goto doc;
    }

    header("Status: 303");
    header("Location: " . $_SESSION['opts']['login_redirect'] ?? '/');
    unset($_SESSION['opts']['login_redirect']);
    tucal_exit();
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    $STATUS = 400;
}

doc:

$TITLE = [_('Sign up')];
require "../.php/header.php";
?>
<main class="w1">
    <section>
        <form action="/account/sign-up" method="post">
            <h1><?php echo _('Sign up');?></h1>
            <div class="text">
                <input name="mnr" id="mnr" type="text" placeholder=" " value="<?php echo htmlspecialchars($_POST['mnr'] ?? '');?>" pattern="[0-9]{7,8}" required/>
                <label for="mnr"><?php echo _('Matriculation number');?></label>
            </div>
            <div class="text">
                <input name="username" id="username" type="text" placeholder=" " value="<?php echo htmlspecialchars($_POST['username'] ?? '');?>" pattern="\p{L}[0-9\p{L}_ -]{1,30}[0-9\p{L}]" required/>
                <label for="username"><?php echo _('Username');?></label>
            </div>
            <div class="text">
                <input name="password" id="password" type="password" placeholder=" " value="<?php echo htmlspecialchars($_POST['password'] ?? '');?>" required/>
                <label for="password"><?php echo _('Password');?></label>
            </div>
            <div class="text">
                <input name="repeat-password" id="repeat-password" type="password" placeholder=" " value="<?php echo htmlspecialchars($_POST['repeat-password'] ?? '');?>" required/>
                <label for="repeat-password"><?php echo _('Repeat password');?></label>
            </div>
            <button type="submit"><?php echo _('Sign up');?></button>
        </form>
    </section>
</main>
<?php
require "../.php/footer.php";
