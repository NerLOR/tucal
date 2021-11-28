<?php
require ".php/session.php";
require ".php/main.php";
require ".php/header.php";
?>
<main class="w3">
    <section>
        <h1>TUcal</h1>
        <pre><?php print_r($_SESSION);?></pre>
        <pre><?php if (isset($USER)) print_r($USER);?></pre>
    </section>
</main>
<?php
require ".php/footer.php";
