<?php

global $CONFIG;
$CONFIG = parse_ini_file("tucal.ini", true);

require "database.php";
require "utils.php";
