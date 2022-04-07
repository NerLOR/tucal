<?php

global $TITLE;
global $STATUS;
global $CONFIG;
global $USER;

$subjects = [
    'LVA-Abkürzungen' => 'Vorschlag für LVA-Abkürzug(en) bei TUcal',
];

require ".php/session.php";

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $name = $_POST['name'] ?? null;
    $email = $_POST['email'] ?? null;
    $subject = $_POST['subject'] ?? null;
    $msg = $_POST['message'];

    if ($name === null || $subject === null || $msg === null) {
        header("Status: 400");
        goto doc;
    }
    $email = ($email === '') ? null : $email;

    $res = send_email($CONFIG['email']['contact'], $subject, $msg, $email, $name);
    redirect('/contact?status=' . ($res ? 'sent' : 'sending'));
} else if ($_SERVER['REQUEST_METHOD'] !== 'GET' && $_SERVER['REQUEST_METHOD'] !== 'HEAD') {
    header("Allow: HEAD, GET, POST");
    $STATUS = 405;
}

doc:
$TITLE = [_('Contact')];
$status = $_GET['status'] ?? null;

$mailto = $CONFIG['email']['contact_direct'];
$subj = isset($_GET['subject']) ? $subjects[$_GET['subject']] ?? null : null;
if (isset($_GET['subject']) && $subj === null) {
    redirect("/contact");
} else if ($subj !== null) {
    $mailto .= "?subject=$subj";
}

require ".php/main.php";
require ".php/header.php";

if ($status === 'sent' || $status == 'sending') { ?>
<main class="w1">
    <section>
        <h1><?php echo _('Contact request'); ?></h1>
        <p class="center"><?php
            if ($status === 'sent') {
                echo _('Contact request sent (description)');
            } else {
                echo _('Contact request sending (description)');
            }
        ?></p>
    </section>
</main>
<?php } else { ?>
<main class="w2">
    <section class="contact">
        <h1><?php echo _('Contact request'); ?></h1>
        <p class="center"><?php echo sprintf(_('Contact request (description)'), $mailto); ?></p>
        <hr/>
        <form method="post" action="/contact" name="contact">
            <div>
                <label for="contact-name"><?php echo _('Name'); ?></label>
                <input type="text" name="name" id="contact-name" placeholder="<?php echo _('(required)'); ?>" required/>
            </div>
            <div>
                <label for="contact-email"><?php echo _('Email address'); ?></label>
                <input type="email" name="email" id="contact-email" value="<?php echo (isset($USER) ? $USER['email_address_1'] : ''); ?>" placeholder="<?php echo _('(optional)'); ?>"/>
            </div>
            <div>
                <label for="contact-subject"><?php echo _('Subject'); ?></label>
                <input type="text" name="subject" id="contact-subject" value="<?php echo $subj ?? ''; ?>" placeholder="<?php echo _('(required)'); ?>" required/>
            </div>
            <div>
                <label for="contact-message"><?php echo _('Message'); ?></label>
                <textarea name="message" id="contact-message" rows="5" placeholder="<?php echo _('(required)'); ?>" required></textarea>
            </div>
            <button type="submit"><?php echo _('Submit'); ?></button>
        </form>
    </section>
</main>
<?php }
require ".php/footer.php";
