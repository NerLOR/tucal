<?php

global $TUCAL;

?>
</div>
<footer>
    <a href="https://<?php echo $TUCAL['hostname'];?>/"><img src="/res/svgs/tucal.svg"/></a>
    <a href="/impressum"><?php echo _('Imprint');?></a>
    <a href="/contact"><?php echo _('Contact');?></a>
    <a href="https://www.paypal.com/donate/?hosted_button_id=W2HVX7662NXCN" target="_blank"><?php echo _('Donate');?></a>
    <a href="https://github.com/NerLOR/tucal" target="_blank">GitHub</a>
    <div class="copyright">Copyright &copy; <?php $y = date('Y'); echo ($y == 2021) ? "2021" : "2021–$y";?> Lorenz Stechauner</div>
    <div class="build {class}">Build <a href="https://github.com/NerLOR/tucal/commit/{commit}" target="_blank">{short}</a>, {comment} ({timestamp})</div>
</footer>
</body>
</html>
<?php
tucal_exit();
