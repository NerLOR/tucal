<?php

global $STATUS;
global $TITLE;
global $LOCALE;

if (!isset($STATUS)) {
    require "main.php";
}

header("Cache-Control: private, no-cache");
header("Content-Security-Policy: default-src 'self'");
header("Referrer-Policy: same-origin");
header("Strict-Transport-Security: max-age=15768000");  // 6 months
header("X-Content-Type-Options: nosniff");
header("X-Frame-Options: SAMEORIGIN");
header("X-XSS-Protection: 1; mode=block");

function uri_active(string $uri, bool $exact = false): string {
    if ($exact) {
        return $_SERVER['REQUEST_URI'] === $uri ? 'active' : '';
    } else {
        return substr($_SERVER['REQUEST_URI'], 0, strlen($uri)) === $uri ? 'active' : '';
    }
}

$cal_uri = isset($USER) ? "/calendar/$USER[mnr]/" : "/calendar/";

if ($STATUS >= 400 && $STATUS < 600) {
    $msg = http_message($STATUS);
    $TITLE = ["$STATUS " . _ctx('http', $msg)];
}

?>
<!DOCTYPE html>
<html lang="<?php echo $LOCALE;?>">
<head>
    <title><?php
        $TITLE = $TITLE ?? [];
        array_push($TITLE, 'TUcal');
        echo implode(' - ', $TITLE);
    ?></title>
    <meta charset="UTF-8"/>
    <meta name="author" content="Lorenz Stechauner"/>
    <meta name="robots" content="notranslate"/>
    <meta name="description" content=""/>
    <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
    <link rel="stylesheet" href="/res/styles/styles.css" type="text/css"/>
    <script src="/res/scripts/localisation.js" type="application/javascript"></script>
    <script src="/res/scripts/calendar.js" type="application/javascript"></script>
    <script src="/res/scripts/main.js" type="application/javascript"></script>
</head>
<body>
<nav>
    <div id="nav-home"><a href="/" class="<?php echo uri_active('/', true)?>"><?php echo _('Home');?></a></div>
    <div id="nav-search">
        <form action="/search" method="get">
            <input name="q" placeholder="<?php echo _('Search (for)');?>"/>
        </form>
    </div>
    <div><a href="<?php echo $cal_uri;?>" class="<?php echo uri_active($cal_uri);?>"><?php echo _('My Calendar');?></a></div>
    <div><a href="/friends" class="<?php echo uri_active('/friends', true)?>"><?php echo _('My Friends');?></a></div>
    <div><a href="/course/" class="<?php echo uri_active('/course/')?>"><?php echo _('LVAs');?></a></div>
    <div id="nav-live">
        <a href="" class="button live" target="_blank">LIVE<span></span></a>
        <a href="" class="button live" target="_blank">LIVE<span></span></a>
        <a href="" class="button live" target="_blank">LIVE<span></span></a>
    </div>
    <div id="nav-user">
<?php if (isset($USER)) { ?>
        <div id="user-menu">
            <div>
                <img src="/res/avatars/default.png" alt="<?php echo _('Avatar');?>"/>
                <a><?php echo $USER['username'];?></a>
                <span class="arrow">▾</span>
            </div>
            <div><a href="/account/"><?php echo _('Settings');?></a></div>
            <?php if (!$USER['verified']) {?><div><a href="/account/verify"><?php echo _('Verify account');?></a></div><?php } ?>

            <hr/>
            <div><a href="/account/logout"><?php echo _('Logout');?></a></div>
        </div>
<?php } else { ?>
        <a href="/account/sign-up" class="button <?php echo uri_active('/account/sign-up', true);?>"><?php echo _('Sign up');?></a>
        <a href="/account/login" class="button <?php echo uri_active('/account/login', true);?>"><?php echo _('Login');?></a>
<?php } ?>
    </div>
</nav>
<div class="wrapper">
<?php  if ($STATUS >= 400 && $STATUS < 600) {
    $msg = http_message($STATUS); ?>
    <main class="w1">
        <section class="status error">
            <h1><?php echo $STATUS;?></h1>
            <h2><?php echo _ctx('http', $msg)?> :&#xFEFF;(</h2>
            <p><?php echo _ctx('http', "${msg} (description)")?></p>
        </section>
    </main>
<?php
    require "footer.php";
}
