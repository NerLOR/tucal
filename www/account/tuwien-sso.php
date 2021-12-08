<?php
global $TITLE;
global $USER;

require "../.php/session.php";
force_user_login(null, false);

require "../.php/main.php";

$jobId = $_GET['job'] ?? null;
$errorMsg = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $mode = $_POST['mode'] ?? null;

    if ($mode === 'store') {
        $pwd = $_POST['password-store'] ?? null;
        $tfaGen = $_POST['2fa-generator'] ?? null;
        $tfaToken = null;
    } elseif ($mode === 'no-store') {
        $pwd = $_POST['password-no-store'] ?? null;
        $tfaToken = $_POST['2fa-token'] ?? null;
        $tfaGen = null;
    } else {
        header("Status: 400");
        goto doc;
    }

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

    $pwd64 = base64_encode($pwd);
    if ($tfaGen !== null) {
        $tfa = base64_encode($tfaGen);
    } elseif ($tfaToken !== null) {
        $tfa = str_replace(' ', '', $tfaToken);
    } else {
        $tfa = '';
    }

    $data = "sync-user $USER[mnr] $pwd64 $tfa";
    fwrite($sock, "$data\n");
    $res = fread($sock, 64);

    if (substr($res, 0, 6) === 'error:') {
        header("Status: 500");
        $errorMsg = _('Error') . ": " . trim(substr($res, 6));
        goto doc;
    }

    $res = explode(' ', $res);

   redirect("/account/tuwien-sso?job=$res[1]");
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    $STATUS = 405;
    header("Allow: GET, POST");
} elseif ($jobId === null) {
    $stmt = db_exec("SELECT job_id FROM tucal.v_job WHERE (mnr, status) = (?, 'running')", [$USER['mnr']]);
    $rows = $stmt->fetchAll();
    if (sizeof($rows) > 0) {
        $jobId = $rows[0][0];
        redirect("/account/tuwien-sso?job=$jobId");
    }
}

doc:

$TITLE = [_('TU Wien SSO authentication')];
require "../.php/header.php";

if ($jobId === null) { ?>
<main class="w1">
    <section>
        <h1><?php echo _('TU Wien SSO authentication');?></h1>
        <form name="sso-store" action="/account/tuwien-sso" method="post" class="panel">
            <p><?php echo _('SSO authentication (description)');?></p>
            <div class="text">
                <input name="password-store" id="password-store" type="password" placeholder=" " value="<?php echo htmlspecialchars($_POST['password-store'] ?? '');?>" required/>
                <label for="password-store"><?php echo _('SSO password');?></label>
            </div>
            <div class="text">
                <input name="2fa-generator" id="2fa-generator" type="text" placeholder=" " value="<?php echo htmlspecialchars($_POST['2fa-generator'] ?? '');?>"/>
                <label for="2fa-generator"><?php echo _('SSO 2FA generator');?></label>
            </div>
            <div class="container red">
                <input name="sso-store" id="sso-store" type="checkbox" required/>
                <label for="sso-store"><?php echo _('SSO password storage warning');?></label>
            </div>
            <button type="submit" name="mode" value="store"><?php echo _('SSO authentication');?></button>
        </form>
        <form name="sso-no-store" action="/account/tuwien-sso" method="post" class="panel">
            <hr data-content="<?php echo strtoupper(_('or'));?>"/>
            <p><?php echo _('SSO one-time authentication (description)');?></p>
            <div class="text">
                <input name="password-no-store" id="password-no-store" type="password" placeholder=" " value="<?php echo htmlspecialchars($_POST['password-no-store'] ?? '');?>" required/>
                <label for="password-no-store"><?php echo _('SSO password');?></label>
            </div>
            <div class="text">
                <input name="2fa-token" id="2fa-token" type="text" placeholder=" " value="<?php echo htmlspecialchars($_POST['2fa-token'] ?? '');?>"/>
                <label for="2fa-token"><?php echo _('SSO 2FA token');?></label>
            </div>
            <button type="submit" name="mode" value="no-store"><?php echo _('SSO one-time authentication');?></button>
        </form>
<?php if ($errorMsg !== null) { ?>
        <div class="container error"><?php echo $errorMsg;?></div>
<?php } ?>
    </section>
</main>
<?php } else { ?>
<main class="w2">
    <section>
        <h1><?php echo _('TU Wien SSO authentication');?></h1>
        <div class="job-viewer" data-job="<?php echo $jobId;?>"></div>
    </section>
</main>
<?php }
require "../.php/footer.php";
