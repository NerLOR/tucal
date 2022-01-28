<?php

global $CONFIG;
global $TUCAL;
$CONFIG = parse_ini_file("tucal.ini", true);
$TUCAL = $CONFIG['tucal'];

require "database.php";
require "utils.php";
