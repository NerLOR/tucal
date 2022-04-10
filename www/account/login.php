<?php

global $TITLE;
global $STATUS;

require "../.php/session.php";
if (isset($USER) && $USER['verified']) {
    redirect('/account/');
} elseif (isset($USER)) {
    redirect('/account/verify');
}

require "../.php/main.php";

$error = false;
$errorMsg = null;
$errors = [
    "subject" => null,
    "pwd" => null,
];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $subj = $_POST['subject'] ?? null;
    $pwd = $_POST['password'] ?? null;

    if ($subj === null || $pwd === null) {
        header("Status: 400");
        goto doc;
    }

    try {
        while (strlen($subj) >= 1 && $subj[0] === '0') {
            $subj = substr($subj, 1);
        }
        $stmt = db_exec("
                    SELECT a.account_nr, mnr, username, (pwd_hash = crypt(:pwd, pwd_salt)) AS pwd_match, verified
                    FROM tucal.account a
                        LEFT JOIN tucal.password p ON p.account_nr = a.account_nr
                    WHERE mnr::text = :subj OR
                          lower(username) = lower(:subj::text)", [
            'subj' => $subj,
            'pwd' => $pwd,
        ]);
        $data = $stmt->fetchAll(PDO::FETCH_ASSOC);
        if (sizeof($data) === 0) {
            $errors['subject'] = 'Does not exist';
            header("Status: 404");
            goto doc;
        }

        $row = $data[0];
        if (!$row['pwd_match']) {
            $errors['pwd'] = 'Wrong';
            header("Status: 401");
            goto doc;
        }

        $USER = ['nr' => $row['account_nr']];
        if (!$row['verified']) {
            redirect('/account/verify');
        } else {
            $redirect = $_SESSION['opts']['redirect'] ?? '/';
            unset($_SESSION['opts']['redirect']);
            redirect($redirect);
        }
    } catch (Exception $e) {
        header("Status: 500");
        $errorMsg = $e->getMessage();
        goto doc;
    }
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET' && $_SERVER['REQUEST_METHOD'] !== 'HEAD') {
    $STATUS = 405;
    header("Allow: HEAD, GET, POST");
}

doc:

$TITLE = [_('Login')];
require "../.php/header.php";
?>
<main class="w1">
    <section>
        <form name="login" action="/account/login" method="post" class="panel">
            <h1><?php echo _('Login'); ?></h1>
            <div class="text<?php echo $errors['subject'] ? " error" : ""; ?>">
                <input name="subject" id="subject" type="text" placeholder=" " value="<?php echo htmlspecialchars($_POST['subject'] ?? ''); ?>" pattern="[0-9]{7,8}|\p{L}[0-9\p{L}_ -]{1,30}[0-9\p{L}]" required/>
                <label for="subject"><?php echo _('Matriculation number or username'); ?></label>
                <label for="subject"><?php if ($errors['subject']) echo _($errors['subject']); ?></label>
            </div>
            <div class="text<?php echo $errors['pwd'] ? " error" : ""; ?>">
                <input name="password" id="password" type="password" placeholder=" " value="<?php echo htmlspecialchars($_POST['password'] ?? ''); ?>" required/>
                <label for="password"><?php echo _('Password'); ?></label>
                <label for="password"><?php if ($errors['pwd']) echo _($errors['pwd']); ?></label>
            </div>
            <button type="submit"><?php echo _('Login'); ?></button>
        </form>
<?php if ($errorMsg !== null) { ?>
        <div class="container error"><?php echo $errorMsg; ?></div>
<?php } ?>
        <p class="center small">
            <?php echo _('No account yet?'); ?> <a href="/account/sign-up"><?php echo _('Sign up'); ?></a>.
            <a href="/account/password/reset"><?php echo _('Forgot password'); ?></a>.
        </p>
    </section>
</main>
<?php
require "../.php/footer.php";
