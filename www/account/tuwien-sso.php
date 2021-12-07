<?php
global $TITLE;
global $USER;

require "../.php/session.php";
force_user_login(null, false);

require "../.php/main.php";

$jobId = null;
$errorMsg = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $pwd = $_POST['password'] ?? null;

    if ($pwd === null) {
        header("Status: 400");
        goto doc;
    }

    $sock = fsockopen('unix:///var/tucal/scheduler.sock', -1, $errno, $errstr);
    if (!$sock) {
        header("Status: 500");
        $errorMsg = _('Unable to open unix socket') . ": $errstr";
        goto doc;
    }

    $data = "sync-user $USER[mnr] " . base64_encode($pwd);
    fwrite($sock, "$data\n");
    $res = fread($sock, 64);

    echo $res;

   // redirect('/account/tuwien-sso');
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    $STATUS = 405;
    header("Allow: GET, POST");
} else {
    $stmt = db_exec("SELECT job_id FROM tucal.v_job WHERE (mnr, status) = (?, 'running')", [$USER['mnr']]);
    $rows = $stmt->fetchAll();
    if (sizeof($rows) > 0) {
        $jobId = $rows[0][0];
    }
}

doc:

$TITLE = [_('TU Wien SSO authentication')];
require "../.php/header.php";

if ($jobId === null) { ?>
<main class="w1">
    <section>
        <h1><?php echo _('TU Wien SSO authentication');?></h1>
        <form action="/account/tuwien-sso" method="post" class="panel">
            <p><?php echo _('SSO authentication (description)');?></p>
            <div class="text">
                <input name="password" id="password" type="password" placeholder=" " value="<?php echo htmlspecialchars($_POST['password'] ?? '');?>" required/>
                <label for="password"><?php echo _('SSO password');?></label>
            </div>
            <div class="container red">
                <input name="sso-store" id="sso-store" type="checkbox"/>
                <label for="sso-store"><?php echo _('SSO password storage warning');?></label>
            </div>
            <button type="submit" name="mode" value="sso"><?php echo _('SSO authentication');?></button>
        </form>
<?php if ($errorMsg !== null) { ?>
            <div class="container error"><?php echo $errorMsg;?></div>
<?php } ?>
    </section>
</main>
<?php } else { ?>
<main class="w2">

</main>
<?php }
require "../.php/footer.php";
