<?php

global $TITLE;
global $USER;
global $STATUS;

require "../.php/session.php";
force_user_login(null, false);

require "../.php/main.php";

$jobId = $_GET['job'] ?? null;
$errorMsg = null;
$mode = null;
$errors = [
    "2fa-gen" => null,
];

if ($jobId === null) {
    $stmt = db_exec("SELECT job_id FROM tucal.v_job WHERE (mnr, status, name) = (?, 'running', 'sync user')", [$USER['mnr']]);
    $rows = $stmt->fetchAll();
    if (sizeof($rows) > 0) {
        $jobId = $rows[0][0];
        redirect("/account/tu-wien-sso?job=$jobId");
    }
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $mode = $_POST['mode'] ?? null;

    if ($mode === 'store') {
        $checkbox = $_POST['sso-store'] ?? null;
        if ($checkbox !== 'accept') {
            header("Status: 400");
            goto doc;
        }
        $pwd = $_POST['password-store'] ?? null;
        $tfaGen = $_POST['2fa-generator'] ?? null;
        $tfaToken = null;
        $store = 'store';
    } elseif ($mode === 'no-store') {
        $pwd = $_POST['password-no-store'] ?? null;
        $tfaToken = $_POST['2fa-token'] ?? null;
        $tfaGen = null;
        $store = '';
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
        $len = strlen($tfaGen);
        if ($len >= 103 && $len <= 109) {
            // Base32
            $tfaGen = base32_decode($tfaGen);
        } elseif ($len >= 86 && $len <= 88) {
            // Base64
            $tfaGen = base64_decode($tfaGen);
        } elseif ($len === 128) {
            // Hex
            $tfaGen = hex2bin($tfaGen);
        } elseif ($len !== 0) {
            header("Status: 400");
            $errors['2fa-gen'] = _('Invalid format');
            goto doc;
        }
        $tfa = base64_encode($tfaGen);
    } elseif ($tfaToken !== null) {
        $tfa = str_replace(' ', '', $tfaToken);
    } else {
        $tfa = '';
    }

    $data = "sync-user $store keep $USER[mnr] $pwd64 $tfa";
    fwrite($sock, "$data\n");
    $res = fread($sock, 64);

    if (substr($res, 0, 6) === 'error:') {
        header("Status: 500");
        $errorMsg = _('Error') . ": " . trim(substr($res, 6));
        goto doc;
    }

    $res = explode(' ', $res);
    if (sizeof($res) < 2) {
        header("Status: 500");
        $errorMsg = _('Unknown error');
        goto doc;
    }

   redirect("/account/tu-wien-sso?job=$res[1]");
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET' && $_SERVER['REQUEST_METHOD'] !== 'HEAD') {
    $STATUS = 405;
    header("Allow: HEAD, GET, POST");
}

doc:

$TITLE = [_('TU Wien account synchronization')];
require "../.php/header.php";

if ($jobId === null) { ?>
<main class="w1">
    <section>
        <h1><?php echo _('TU Wien account synchronization');?></h1>
        <form name="sso-store" action="/account/tu-wien-sso" method="post" class="panel">
            <p><?php echo _('Account synchronization (description)');?></p>
            <p><?php echo _('Automatic account synchronization (description)');?></p>
            <div class="text">
                <input name="password-store" id="password-store" type="password" placeholder=" " value="<?php echo htmlspecialchars($_POST['password-store'] ?? '');?>" required/>
                <label for="password-store"><?php echo _('SSO password');?></label>
                <label for="password-store"></label>
            </div>
            <div class="text <?php echo $errors['2fa-gen'] ? " error" : "";?>">
                <input name="2fa-generator" id="2fa-generator" type="text" placeholder=" " value="<?php echo htmlspecialchars($_POST['2fa-generator'] ?? '');?>"/>
                <label for="2fa-generator"><?php echo _('SSO 2FA generator (optional)');?></label>
                <label for="2fa-generator"><?php if ($errors['2fa-gen']) echo _($errors['2fa-gen']);?></label>
            </div>
            <div class="container red">
                <input name="sso-store" id="sso-store" type="checkbox" value="accept" required/>
                <label for="sso-store"><?php echo _('SSO password storage warning (description)');?></label>
                <label for="sso-store"></label>
            </div>
            <button type="submit" name="mode" value="store"><?php echo _('Automatic account synchronization');?></button>
        </form>
<?php if ($errorMsg !== null && $mode === 'store') { ?>
        <div class="container error"><?php echo $errorMsg;?></div>
<?php } ?>
        <form name="sso-no-store" action="/account/tu-wien-sso" method="post" class="panel">
            <hr data-content="<?php echo strtoupper(_('or'));?>"/>
            <p><?php echo _('One-time account synchronization (description)');?></p>
            <div class="text">
                <input name="password-no-store" id="password-no-store" type="password" placeholder=" " value="<?php echo htmlspecialchars($_POST['password-no-store'] ?? '');?>" required/>
                <label for="password-no-store"><?php echo _('SSO password');?></label>
                <label for="password-no-store"></label>
            </div>
            <div class="text">
                <input name="2fa-token" id="2fa-token" type="text" placeholder=" " value="<?php echo htmlspecialchars($_POST['2fa-token'] ?? '');?>"/>
                <label for="2fa-token"><?php echo _('SSO 2FA token (optional)');?></label>
                <label for="2fa-token"></label>
            </div>
            <button type="submit" name="mode" value="no-store"><?php echo _('One-time account synchronization');?></button>
        </form>
<?php if ($errorMsg !== null && ($mode === 'no-store' || $mode === null)) { ?>
        <div class="container error"><?php echo $errorMsg;?></div>
<?php } ?>
    </section>
</main>
<?php } else { ?>
<main class="w2">
    <section>
        <h1><?php echo _('TU Wien account synchronization');?></h1>
        <?php echo_job($jobId, "/calendar/$USER[mnr]", "/account/tu-wien-sso");?>

    </section>
</main>
<?php }
require "../.php/footer.php";
