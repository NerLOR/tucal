<?php
global $TITLE;
global $USER;

require "../.php/session.php";
force_user_login(null, false);

require "../.php/main.php";

$TITLE = [_('Verify account')];
require "../.php/header.php";
?>
<main class="w1">
    <section>
        <h1><?php echo _('Verify account');?></h1>
        <form action="/account/verify" method="post" class="panel">
            <p><?php echo _('SSO verification (description)');?></p>
            <div class="text">
                <input name="sso-password" id="sso-password" type="password" placeholder=" " required/>
                <label for="sso-password"><?php echo _('SSO password');?></label>
            </div>
            <div class="container red">
                <input name="sso-store" id="sso-store" type="checkbox"/>
                <label for="sso-store"><?php echo _('SSO password storage warning');?></label>
            </div>
            <button type="submit" name="mode" value="sso"><?php echo _('SSO verification');?></button>
        </form>
        <form action="/account/verify" method="post" class="panel">
            <hr data-content="<?php echo strtoupper(_('or'));?>"/>
            <p><?php echo _('Email verification (description)');?></p>
            <div class="text">
                <input name="email-address" id="email-address" type="email" placeholder=" " value="<?php echo $USER['email_address_1'];?>" readonly required/>
                <label for="email-address"><?php echo _('Email address');?></label>
            </div>
            <button type="submit" name="mode" value="email"><?php echo _('Email verification');?></button>
        </form>
    </section>
</main>
<?php
require "../.php/footer.php";
