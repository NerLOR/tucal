<?php

global $TITLE;

require ".php/session.php";

$TITLE = [_('Imprint')];

require ".php/main.php";
require ".php/header.php";
?>
<main class="w3">
    <section class="imprint">
        <h1><?php echo _('Imprint'); ?></h1>
<?php include ".php/impressum.php"; ?>
    </section>
</main>
<?php
require ".php/footer.php";
