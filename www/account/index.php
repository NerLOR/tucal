<?php

global $TITLE;
global $USER;
global $LOCALE;
global $LOCALES;
global $STATUS;

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
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    $STATUS = 405;
    header("Allow: GET, POST");
}

doc:
$theme = $_SESSION['opts']['theme'] ?? 'light';

$TITLE = [_('Settings')];
require "../.php/header.php";
?>
<main class="w3">
    <section>
        <h1><?php echo _('Settings');?></h1>
        <form name="account-settings" action="/account/" method="post" class="table">
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
                    <option value="bar-AT"<?php echo $LOCALE === 'bar-AT' ? " selected" : "";?>>Bairisch (Östareich)</option>
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
</main>
<?php
require "../.php/footer.php";
