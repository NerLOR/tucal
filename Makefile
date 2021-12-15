
build-www:
	rm -rf dest/www
	cp -pr www dest/www
	sed -i 's|"\(/res/[^"]*\)"|"\1?v=$(shell date -u +%Y%m%d-%H%M%S)"|g' dest/www/.php/header.php dest/www/.php/footer.php
	tools/minify-css.sh
	sed -i 's|/res/styles/styles.css|/res/styles/min.css|g' dest/www/.php/header.php
	convert -background none dest/www/res/svgs/tucal.svg -alpha set -define icon:auto-resize=256,128,64,32,24,16 dest/www/favicon.ico

	for locale in de de_AT de_DE en en_US en_GB bar; do \
		mkdir -p "dest/www/.php/locale/$$locale/LC_MESSAGES/" ;\
		msgfmt "locale/$$locale/LC_MESSAGES/tucal.po" -o "dest/www/.php/locale/$$locale/LC_MESSAGES/tucal.mo" ;\
	done
