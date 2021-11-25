<?php
global $TITLE;

require "../.php/session.php";

$TITLE = [_('Sign up')];

require "../.php/main.php";
require "../.php/header.php";
?>
<main class="w1">
    <section>
        <form action="/account/sign-up" method="post">
            <h1><?php echo _('Sign up');?></h1>
            <div class="text">
                <input name="mnr" id="mnr" type="text" placeholder=" " pattern="[0-9]{7,8}" required/>
                <label for="mnr"><?php echo _('Matriculation number');?></label>
            </div>
            <div class="text">
                <input name="username" id="username" type="text" placeholder=" " pattern="\p{L}[0-9\p{L}_ -]{1,30}[0-9\p{L}]" required/>
                <label for="username"><?php echo _('Username');?></label>
            </div>
            <div class="text">
                <input name="password" id="password" type="password" placeholder=" " required/>
                <label for="password"><?php echo _('Password');?></label>
            </div>
            <div class="text">
                <input name="repeat-password" id="repeat-password" type="password" placeholder=" " required/>
                <label for="repeat-password"><?php echo _('Repeat password');?></label>
            </div>
            <button type="submit"><?php echo _('Sign up');?></button>
        </form>
    </section>
</main>
<?php
require "../.php/footer.php";
