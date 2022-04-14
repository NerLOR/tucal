<?php

global $USER;
global $STATUS;
global $TITLE;
global $CONFIG;

require "../.php/session.php";

force_user_login();
if (!$USER['administrator']) $STATUS = 403;
require "../.php/main.php";

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $pwd = $_POST['password'] ?? null;
    $subject = $_POST['subject'] ?? null;
    $msg = $_POST['message'] ?? null;

    if ($pwd === null || $subject === null || $msg === null) {
        header("Status: 400");
        goto doc;
    } elseif (!check_password($pwd)) {
        header("Status: 403");
        goto doc;
    }

    send_email(null, $subject, $msg, $CONFIG['email']['contact_direct']);
    redirect("/admin/");
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET' && $_SERVER['REQUEST_METHOD'] !== 'HEAD') {
    $STATUS = 405;
    header("Allow: HEAD, GET, POST");
}

doc:
$TITLE = [_('Message all Users'), _('Admin Panel')];
require "../.php/header.php";
?>
<main class="w3">
    <section class="admin">
        <h1><?php echo _('Message all Users'); ?></h1>
        <div class="center">
            <a class="button margin" href="/admin/"><?php echo _('Back'); ?></a>
        </div>
        <hr class="narrow"/>
        <form method="post" action="/admin/message" name="message" class="message">
            <input type="password" name="password" placeholder="<?php echo _('Password'); ?>" value="<?php echo htmlentities($_POST['password'] ?? ''); ?>" required/>
            <input type="text" name="subject" placeholder="<?php echo _('Subject'); ?>" value="<?php echo htmlentities($_POST['subject'] ?? ''); ?>" required/>
            <textarea name="message" rows="5" placeholder="<?php echo _('Message'); ?>" required><?php echo htmlentities($_POST['message'] ?? ''); ?></textarea>
            <button type="submit"><?php echo _('Submit'); ?></button>
        </form>
    </section>
</main>
<?php
require "../.php/footer.php";
