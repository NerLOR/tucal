<?php

global $TITLE;
global $USER;
global $LOCALE;

require "../.php/session.php";
if (isset($USER)) {
    redirect('/account/');
}

require "../.php/main.php";

$error = false;
$errorMsg = null;
$errors = [
    "mnr" => null,
    "username" => null,
    "pw1" => null,
    "pw2" => null,
];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $mnr = $_POST['mnr'] ?? null;
    $username = $_POST['username'] ?? null;
    $pw1 = $_POST['password'] ?? null;
    $pw2 = $_POST['repeat-password'] ?? null;

    if ($mnr === null || $username === null || $pw1 === null || $pw2 === null) {
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

    db_transaction();

    try {
        db_exec("LOCK TABLE tucal.account IN EXCLUSIVE MODE");

        $stmt = db_exec("
                    SELECT mnr, username
                    FROM tucal.account
                    WHERE mnr = ? OR username = ?", [$mnr, $username]);
        $data = $stmt->fetchAll(PDO::FETCH_ASSOC);
        if (sizeof($data) > 0) {
            foreach ($data as $row) {
                if (strtolower($row['username']) === strtolower($username)) {
                    $errors['username'] = 'Already in use';
                }
                if ($row['mnr'] == $mnr) {
                    $errors['mnr'] = 'Already in use';
                }
            }
            $error = 409;
        }

        if ($error !== false) {
            db_rollback();
            header("Status: $error");
            goto doc;
        }

        $stmt = db_exec("
                    INSERT INTO tucal.account (mnr, username)
                    VALUES (:mnr, :username)
                    RETURNING account_nr", [
            'mnr' => $mnr,
            'username' => $username,
        ]);
        $nr = $stmt->fetch()[0];

        $stmt = db_exec("
                    INSERT INTO tucal.password (account_nr, pwd_salt, pwd_hash)
                    VALUES (:nr, gen_salt('bf'), crypt(:pwd, pwd_salt))", [
            'nr' => $nr,
            'pwd' => $pw1,
        ]);

        $USER = [
            'nr' => $nr,
            'opts' => [
                'locale' => $LOCALE,
                'lt_provider' => 'live-video-tuwien',
            ],
        ];
    } catch (Exception $e) {
        db_rollback();
        header("Status: 500");
        $errorMsg = $e->getMessage();
        goto doc;
    }

    db_commit();

    redirect('/account/verify');
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    $STATUS = 405;
    header("Allow: GET, POST");
}

doc:

$TITLE = [_('Sign up')];
require "../.php/header.php";
?>
<main class="w1">
    <section>
        <form name="sign-up" action="/account/sign-up" method="post" class="panel">
            <h1><?php echo _('Sign up');?></h1>
            <div class="text<?php echo $errors['mnr'] ? " error" : "";?>">
                <input name="mnr" id="mnr" type="text" placeholder=" " value="<?php echo htmlspecialchars($_POST['mnr'] ?? '');?>" pattern="[0-9]{7,8}" required/>
                <label for="mnr"><?php echo _('Matriculation number');?></label>
                <label for="mnr"><?php if ($errors['mnr']) echo _($errors['mnr']);?></label>
            </div>
            <div class="text<?php echo $errors['username'] ? " error" : "";?>">
                <input name="username" id="username" type="text" placeholder=" " value="<?php echo htmlspecialchars($_POST['username'] ?? '');?>" pattern="\p{L}[0-9\p{L}_ -]{1,30}[0-9\p{L}]" required/>
                <label for="username"><?php echo _('Username');?></label>
                <label for="username"><?php if ($errors['username']) echo _($errors['username']);?></label>
            </div>
            <div class="text<?php echo $errors['pw1'] ? " error" : "";?>">
                <input name="password" id="password" type="password" placeholder=" " value="<?php echo htmlspecialchars($_POST['password'] ?? '');?>" required/>
                <label for="password"><?php echo _('Password');?></label>
                <label for="password"><?php if ($errors['pw1']) echo _($errors['pw1']);?></label>
            </div>
            <div class="text<?php echo $errors['pw2'] ? " error" : "";?>">
                <input name="repeat-password" id="repeat-password" type="password" placeholder=" " value="<?php echo htmlspecialchars($_POST['repeat-password'] ?? '');?>" required/>
                <label for="repeat-password"><?php echo _('Repeat password');?></label>
                <label for="repeat-password"><?php if ($errors['pw2']) echo _($errors['pw2']);?></label>
            </div>
            <button type="submit"><?php echo _('Sign up');?></button>
        </form>
<?php if ($errorMsg !== null) { ?>
        <div class="container error"><?php echo $errorMsg;?></div>
<?php } ?>
        <p class="center small">
            <?php echo _('Already signed up?');?> <a href="/account/login"><?php echo _('Login');?></a>.
            <a href="/account/password/reset"><?php echo _('Forgot password');?></a>.
        </p>
    </section>
</main>
<?php
require "../.php/footer.php";
