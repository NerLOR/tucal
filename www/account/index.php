<?php

global $TITLE;
global $USER;
global $LOCALE;

require "../.php/session.php";
force_user_login(null, false);

require "../.php/main.php";

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_POST['locale'])) {
        $USER['opts']['locale'] = $_POST['locale'];
        init_locale();
    }
    if (isset($_POST['lt-provider'])) {
        $USER['opts']['lt_provider'] = $_POST['lt-provider'];
    }
} elseif ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    $STATUS = 405;
    header("Allow: GET, POST");
}

$TITLE = [_('Settings')];
require "../.php/header.php";
?>
<main class="w3">
    <section>
        <h1><?php echo _('Settings');?></h1>
        <form name="account-settings" action="/account/" method="post" class="table">
            <div class="text">
                <label for="locale"><?php echo _('Locale');?></label>
                <select name="locale" id="locale">
                    <option value="de-AT"<?php echo $LOCALE === 'de-AT' ? " selected" : "";?>>Deutsch (Österreich)</option>
                    <option value="de-DE"<?php echo $LOCALE === 'de-DE' ? " selected" : "";?>>Deutsch (Deutschland)</option>
                    <option value="en-GB"<?php echo $LOCALE === 'en-GB' ? " selected" : "";?>>English (United Kingdom)</option>
                    <option value="en-US"<?php echo $LOCALE === 'en-US' ? " selected" : "";?>>English (United Stated)</option>
                    <option value="bar-AT"<?php echo $LOCALE === 'bar-AT' ? " selected" : "";?>>Bairisch (Östareich)</option>
                </select>
            </div>
            <div class="text">
                <label for="lt-provider"><?php echo _('LectureTube provider');?></label>
                <select name="lt-provider" id="lt-provider">
                    <option value="live-video-tuwien"<?php echo $USER['opts']['lt_provider'] === "live-video-tuwien" ? " selected" : "";?>>live.video.tuwien.ac.at</option>
                    <option value="hs-streamer"<?php echo $USER['opts']['lt_provider'] === "hs-streamer" ? " selected" : "";?>>HS-Streamer</option>
                </select>
            </div>
            <button type="submit"><?php echo _('Save');?></button>
        </form>
    </section>
    <section>
        <h1>Session</h1>
        <pre><?php print_r($_SESSION);?></pre>
    </section>
    <section>
        <h1>Account</h1>
        <pre><?php print_r($USER);?></pre>
    </section>
</main>
<?php
require "../.php/footer.php";
