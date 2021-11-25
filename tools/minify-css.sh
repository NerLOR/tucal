#!/bin/bash
cd 'dest/www/res/styles'
files=$(echo 'styles.css'; grep -E '^@import "(.*)";' 'styles.css' | sed 's/@import "\|";//g')
sed ':a;N;$!ba;s/[ \n]\{1,\}/ /g' $files | sed 's/ \?\([{}>;:,]\) \?/\1/g' | sed 's/@import[^;]*;\|^ \| $//g'
