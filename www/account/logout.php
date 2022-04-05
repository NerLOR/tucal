<?php

global $USER;
global $STATUS;

require "../.php/session.php";
if (!isset($USER)) {
    redirect('/account/login');
}

require "../.php/main.php";

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    unset($USER);
    redirect($_SERVER['HTTP_REFERER'] ?? '/');
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET' && $_SERVER['REQUEST_METHOD'] !== 'HEAD') {
    $STATUS = 405;
    header("Allow: HEAD, GET, POST");
}

$TITLE = [_('Logout')];
require "../.php/header.php";
?>
    <main class="w1">
        <section>
            <form name="logout" action="/account/logout" method="post" class="panel">
                <h1><?php echo _('Logout'); ?></h1>
                <button type="submit"><?php echo _('Logout'); ?></button>
            </form>
        </section>
    </main>
<?php
require "../.php/footer.php";
