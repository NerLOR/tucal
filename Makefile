
build-www:
	rm -rf dest/www
	cp -pr www dest/www
	sed -i 's|"\(/res/[^"]*\)"|"\1?v=$(shell date -u +%Y%m%d-%H%M%S)"|g' dest/www/.php/header.php
	tools/minify-css.sh > dest/www/res/styles/min.css
	sed -i 's|/res/styles/styles.css|/res/styles/min.css|g' dest/www/.php/header.php

	for locale in de de_AT de_DE en en_US en_GB bar; do \
		mkdir -p "dest/www/.php/locale/$$locale/LC_MESSAGES" ;\
		msgfmt "locale/$$locale/LC_MESSAGES/tucal.po" -o "dest/www/.php/locale/$$locale/LC_MESSAGES/tucal.mo" ;\
	done
