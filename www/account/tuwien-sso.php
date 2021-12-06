<?php
global $TITLE;
global $USER;

require "../.php/session.php";
force_user_login(null, false);

require "../.php/main.php";

$TITLE = [_('TU Wien SSO authentication')];
require "../.php/header.php";
?>
    <main class="w1">
        <section>
            <h1><?php echo _('TU Wien SSO authentication');?></h1>
            <form action="/account/verify" method="post" class="panel">
                <p><?php echo _('SSO authentication (description)');?></p>
                <div class="text">
                    <input name="sso-password" id="sso-password" type="password" placeholder=" " required/>
                    <label for="sso-password"><?php echo _('SSO password');?></label>
                </div>
                <div class="container red">
                    <input name="sso-store" id="sso-store" type="checkbox"/>
                    <label for="sso-store"><?php echo _('SSO password storage warning');?></label>
                </div>
                <button type="submit" name="mode" value="sso"><?php echo _('SSO authentication');?></button>
            </form>
        </section>
    </main>
<?php
require "../.php/footer.php";
