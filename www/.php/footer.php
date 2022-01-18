<?php

global $CONFIG;

?>
</div>
<footer>
    <a href="https://<?php echo $CONFIG['host'];?>/"><img src="/res/svgs/tucal.svg"/></a>
    <a href="/impressum"><?php echo _('Imprint');?></a>
    <a href="/contact"><?php echo _('Contact');?></a>
    <a href="https://github.com/NerLOR/tucal">GitHub</a>
    <div class="copyright">Copyright &copy; <?php $y = date('Y'); echo ($y == 2021) ? "2021" : "2021–$y";?> Lorenz Stechauner</div>
</footer>
</body>
</html>
<?php
tucal_exit();
