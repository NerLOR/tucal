<?php

global $USER;
global $STATUS;
global $TITLE;

require "../.php/session.php";

force_user_login();
if (!$USER['administrator']) $STATUS = 403;

require "../.php/main.php";

$TITLE = [_('Admin Panel')];
require "../.php/header.php";
?>
<main class="w3">
    <section>
        <h1><?php echo _('Admin Panel'); ?></h1>
        <div class="center">
            <a class="button margin" href="/admin/accounts"><?php echo _('Accounts'); ?></a>
            <a class="button margin" href="/admin/jobs"><?php echo _('Jobs'); ?></a>
            <a class="button margin" href="/admin/acronyms"><?php echo _('Course acronyms'); ?></a>
            <a class="button margin" href="/admin/message"><?php echo _('Message all users'); ?></a>
        </div>
        <hr/>
        <div class="center">
            <a class="button margin" href="/admin/sync-courses"><?php echo _('Sync courses'); ?></a>
        </div>
    </section>
</main>
<?php
require "../.php/footer.php";
