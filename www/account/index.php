<?php

global $TITLE;
global $USER;
global $LOCALE;
global $LOCALES;
global $STATUS;

$FILE_ERRORS = [
    UPLOAD_ERR_INI_SIZE => "The uploaded file exceeds the maximum upload size.",
    UPLOAD_ERR_FORM_SIZE => "The uploaded file exceeds the maximum upload size.",
    UPLOAD_ERR_PARTIAL => "The uploaded file has not been fully uploaded.",
    UPLOAD_ERR_NO_FILE => "No file has been uploaded.",
    UPLOAD_ERR_NO_TMP_DIR => "Unable to find a temporary directory.",
    UPLOAD_ERR_CANT_WRITE => "Unable to write to target directory.",
    UPLOAD_ERR_EXTENSION => "The file upload has been stopped by a PHP extension.",
];

$AVATAR_SIZE = '256x256';
$AVATAR_URI = '/upload/avatar';
$AVATAR_PATH = "$_SERVER[DOCUMENT_ROOT]$AVATAR_URI";

require "../.php/session.php";
force_user_login(null, false);

require "../.php/main.php";

$error = false;
$errorMsg = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_POST['locale'])) {
        $locale = $_POST['locale'];
        if (in_array($locale, $LOCALES)) {
            $USER['opts']['locale'] = $_POST['locale'];
            init_locale();
        } else {
            header("Status: 400");
            goto doc;
        }
    }

    if (isset($_POST['lt-provider'])) {
        $lt = $_POST['lt-provider'];
        if (in_array($lt, ['live-video-tuwien', 'hs-streamer'])) {
            $USER['opts']['lt_provider'] = $lt;
        } else {
            header("Status: 400");
            goto doc;
        }
    }

    if (isset($_POST['theme'])) {
        $theme = $_POST['theme'];
        if (in_array($theme, ['browser', 'light', 'dark', 'black'])) {
            $_SESSION['opts']['theme'] = $theme;
        } else {
            header("Status: 400");
            goto doc;
        }
    }

    if (isset($_POST['username'])) {
        $username = $_POST['username'];
        if ($username !== $USER['username']) {

            $stmt = db_exec("
                SELECT mnr, username
                FROM tucal.account
                WHERE username = ?", [$username]);
            $data = $stmt->fetchAll(PDO::FETCH_ASSOC);
            if (sizeof($data) > 0) {
                foreach ($data as $row) {
                    if (strtolower($row['username']) === strtolower($username)) {
                        $errorMsg = _('Username already in use');
                    }
                }
                $error = 409;
            }

            if ($error !== false) {
                header("Status: $error");
                goto doc;
            }

            $USER['username'] = $username;
        }
    }

    if (isset($_FILES['avatar']) && $_FILES['avatar']['error'] !== UPLOAD_ERR_NO_FILE) {
        $avatar = $_FILES['avatar'];
        if ($avatar['error'] !== UPLOAD_ERR_OK) {
            header("Status: 500");
            $errorMsg = _($FILE_ERRORS[$avatar['error']]);
            goto doc;
        }

        $parts = explode('.', $avatar['name']);
        $ext = $parts[sizeof($parts) - 1];
        if (strlen($ext) > 4 || strlen($ext) <= 1 || sizeof($parts) <= 1 || !ctype_alpha($ext)) {
            $ext = null;
        }
        $file = "$AVATAR_PATH/.tmp.$USER[id]" . ($ext !== null ? ".$ext" : "");

        if (!move_uploaded_file($avatar['tmp_name'], $file)) {
            header("Status: 500");
            goto doc;
        }

        if ((isset($avatar['type']) && $avatar['type'] === 'image/jpeg') || (!isset($avatar['type']) && ($ext === 'jpg' || $ext === 'jpeg'))) {
            $outType = 'jpg';
        } else {
            $outType = 'png';
        }
        $fileOut = "$AVATAR_PATH/.$USER[id].$outType";
        $fileFin = "$AVATAR_PATH/$USER[id].$outType";
        $uri = "$AVATAR_URI/$USER[id].$outType?v=" . gmdate("Ymd-His");
        $clean = "rm -rf $AVATAR_PATH/.tmp.$USER[id] $AVATAR_PATH/.tmp.$USER[id].* $AVATAR_PATH/.$USER[id].*";

        $res = exec("/bin/convert '$file' -resize $AVATAR_SIZE^ -gravity Center -extent $AVATAR_SIZE '$fileOut'");
        if ($res === false) {
            exec($clean);
            header("Status: 500");
            $errorMsg = _("Unable to convert profile picture.");
            goto doc;
        }

        exec("rm -rf $AVATAR_PATH/$USER[id].*");
        exec("mv '$fileOut' '$fileFin'");
        exec($clean);
        $USER['avatar_uri'] = $uri;
    }

    redirect("/account/");
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    $STATUS = 405;
    header("Allow: GET, POST");
}

doc:
$theme = $_SESSION['opts']['theme'] ?? 'light';

$fmt = 'd.m.Y, H:i (P)';
$create_ts = null;
$login_ts = null;
$sync_ts = null;
if ($USER['create_ts']) $create_ts = strtotime($USER['create_ts']);
if ($USER['login_ts']) $login_ts = strtotime($USER['login_ts']);
if ($USER['sync_ts']) $sync_ts = strtotime($USER['sync_ts']);

$TITLE = [_('Settings')];
require "../.php/header.php";
?>
<main class="w3">
    <section>
        <h1><?php echo _('Settings');?></h1>
        <form name="account-settings" action="/account/" method="post" class="table" enctype="multipart/form-data">
            <div>
                <label for="username"><?php echo _('Username');?></label>
                <input name="username" id="username" type="text" value="<?php echo htmlentities($USER['username'])?>" pattern="\p{L}[0-9\p{L}_ -]{1,30}[0-9\p{L}]" required/>
            </div>
            <div>
                <label for="mnr"><?php echo _('Matriculation number');?></label>
                <input name="mnr" id="mnr" type="text" value="<?php echo htmlentities($USER['mnr'])?>" readonly disabled/>
            </div>
            <div>
                <label for="email-address-1"><?php echo _('Email address');?></label>
                <input name="email-address-1" id="email-address-1" type="text" value="<?php echo htmlentities($USER['email_address_1'])?>" readonly disabled/>
            </div>
            <div>
                <label for="locale"><?php echo _('Locale');?></label>
                <select name="locale" id="locale">
                    <option value="de-AT"<?php echo $LOCALE === 'de-AT' ? " selected" : "";?>>Deutsch (Österreich)</option>
                    <option value="de-DE"<?php echo $LOCALE === 'de-DE' ? " selected" : "";?>>Deutsch (Deutschland)</option>
                    <option value="en-GB"<?php echo $LOCALE === 'en-GB' ? " selected" : "";?>>English (United Kingdom)</option>
                    <option value="en-US"<?php echo $LOCALE === 'en-US' ? " selected" : "";?>>English (United States)</option>
                    <option value="bar-AT"<?php echo $LOCALE === 'bar-AT' ? " selected" : "";?>>BETA – Bairisch (Östareich)</option>
                </select>
            </div>
            <div>
                <label for="lt-provider"><?php echo _('LectureTube provider');?></label>
                <select name="lt-provider" id="lt-provider">
                    <option value="live-video-tuwien"<?php echo $USER['opts']['lt_provider'] === "live-video-tuwien" ? " selected" : "";?>>live.video.tuwien.ac.at</option>
                    <option value="hs-streamer"<?php echo $USER['opts']['lt_provider'] === "hs-streamer" ? " selected" : "";?>>HS-Streamer</option>
                </select>
            </div>
            <div>
                <label for="theme"><?php echo _('Theme');?></label>
                <select name="theme" id="theme">
                    <option value="browser"<?php echo $theme === 'browser' ? " selected" : "";?>><?php echo _('Browser theme');?></option>
                    <option value="light"<?php echo $theme === 'light' ? " selected" : "";?>><?php echo _('Light theme');?></option>
                    <option value="dark"<?php echo $theme === 'dark' ? " selected" : "";?>><?php echo _('Dark theme');?></option>
                    <option value="black"<?php echo $theme === 'black' ? " selected" : "";?>><?php echo _('Black theme');?></option>
                </select>
            </div>
            <div>
                <label for="avatar"><?php echo _('Profile picture');?></label>
                <input type="file" name="avatar" id="avatar" accept="image/*"/>
            </div>
            <button type="submit"><?php echo _('Save');?></button>
        </form>
<?php if ($errorMsg !== null) { ?>
        <div class="container error"><?php echo $errorMsg;?></div>
<?php } ?>
        <div class="center">
            <a class="button margin" href="/account/sync"><?php echo _('Synchronize TU account');?></a>
            <a class="button margin" href="/account/password/"><?php echo _('Change password');?></a>
        </div>
    </section>
    <section>
        <h1><?php echo _('Account statistics'); ?></h1>
        <form name="statistics" class="table">
            <div>
                <label for="create-ts"><?php echo _('Creation');?></label>
                <input name="create-ts" id="create-ts" type="text" value="<?php echo $create_ts !== null ? date($fmt, $create_ts) : _('Never'); ?>" readonly disabled/>
            </div>
            <div>
                <label for="login-ts"><?php echo _('Latest login');?></label>
                <input name="login-ts" id="login-ts" type="text" value="<?php echo $login_ts !== null ? date($fmt, $login_ts) : _('Never'); ?>" readonly disabled/>
            </div>
            <div>
                <label for="sync-ts"><?php echo _('Latest synchronization');?></label>
                <input name="sync-ts" id="sync-ts" type="text" value="<?php echo $sync_ts !== null ? date($fmt, $sync_ts) : _('Never'); ?>" readonly disabled/>
            </div>
        </form>
    </section>
</main>
<?php
require "../.php/footer.php";
