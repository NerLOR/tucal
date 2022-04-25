<?php

global $USER;
global $STATUS;
global $TITLE;

require "../.php/session.php";

force_user_login();
if (!$USER['administrator']) $STATUS = 403;
require "../.php/main.php";

$jobId = $_GET['id'] ?? null;
if ($jobId === null) {
    redirect("/admin/jobs");
}

$TITLE = [_('Job'), _('Admin Panel')];
require "../.php/header.php";
?>
<main class="w2">
    <section>
        <h1><?php echo _('Job'); ?></h1>
        <?php echo_job($jobId); ?>

    </section>
</main>
<?php
require "../.php/footer.php";
