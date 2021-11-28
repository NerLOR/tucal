<?php

global $TITLE;

require "../.php/session.php";
if (isset($USER)) {
    redirect('/account/');
}

require "../.php/main.php";

$TITLE = [_('Login')];
require "../.php/header.php";
?>
<main class="w1">
    <section>
        <form action="/account/login" method="post">
            <h1><?php echo _('Login');?></h1>
            <div class="text">
                <input name="subject" id="subject" type="text" placeholder=" " pattern="[0-9]{7,8}|\p{L}[0-9\p{L}_ -][0-9\p{L}]" required/>
                <label for="subject"><?php echo _('Matriculation number or username');?></label>
            </div>
            <div class="text">
                <input name="password" id="password" type="password" placeholder=" " required/>
                <label for="password"><?php echo _('Password');?></label>
            </div>
            <button type="submit"><?php echo _('Login');?></button>
        </form>
    </section>
</main>
<?php
require "../.php/footer.php";
