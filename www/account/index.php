<?php

global $TITLE;

require "../.php/session.php";
force_user_login();

require "../.php/main.php";

$TITLE = [_('Account overview')];
require "../.php/header.php";
?>
<main class="w3">

</main>
<?php
require "../.php/footer.php";
