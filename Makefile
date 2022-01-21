
build-www:
	mkdir -p dest/
	rm -rf dest/www

	for file in $(shell find www/ -name "*.php" -type f); do \
		php -l "$$file" ;\
		if [ $$? != 0 ]; then exit 1; fi ;\
	done

	cp -pr www dest/www
	cp -pr tucal.ini dest/www/.php/

	tsc -p typescript/

	sed -i 's|"\(/res/[^"]*\)"|"\1?v=$(shell date -u +%Y%m%d-%H%M%S)"|g' dest/www/.php/header.php dest/www/.php/footer.php
	tools/minify-css.sh
	sed -i 's|/res/styles/styles.css|/res/styles/min.css|g' dest/www/.php/header.php

	convert -background none dest/www/res/svgs/tucal.svg -alpha set -define icon:auto-resize=256,128,64,32,24,16 dest/www/favicon.ico

	for locale in de de_AT de_DE en en_US en_GB bar; do \
		mkdir -p "dest/www/.php/locale/$$locale/LC_MESSAGES/" ;\
		msgfmt "locale/$$locale/LC_MESSAGES/tucal.po" -o "dest/www/.php/locale/$$locale/LC_MESSAGES/tucal.mo" ;\
	done

database:
	@read -p "Are you sure, you want to reset the specified database? [y/N] " -r ;\
		if [[ ! "$$REPLY" =~ ^[yY]$  ]]; then echo "aborting!"; exit 1; fi
	for file in $(shell find sql/ -name "*.sql" -type f); do \
		./db.sh -f "$$file" ;\
	done

clean:
	rm -rf dest/
