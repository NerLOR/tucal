
HEADER=dest/www/.php/header.php
FOOTER=dest/www/.php/footer.php

build-www:
	mkdir -p dest/
	rm -rf dest/www dest/typescript
	# check php syntax
	for file in $(shell find www/ -name "*.php" -type f); do \
		php -l "$$file" ;\
		if [ $$? != 0 ]; then exit 1; fi ;\
	done
	# copy php to dest
	cp -pr www dest/www
	cp -pr tucal.ini dest/www/.php/
	# download Europe/Vienna timezone
	wget "http://tzurl.org/zoneinfo/Europe/Vienna" -O "vienna.tmp.txt"
	tail -n +4 "vienna.tmp.txt" | head -n -1 > "dest/www/calendar/export/europe-vienna.txt"
	rm "vienna.tmp.txt"
	# compile typescript
	cp -pr typescript dest/typescript
	tools/msgfmtjs.sh locale dest/typescript/src/messages.ts dest/typescript/src/messages.ts
	tsc -p dest/typescript/
	# replace css links in php/html
	sed -i 's|"\(/res/[^"]*\)"|"\1?v=$(shell date -u +%Y%m%d-%H%M%S)"|g' ${HEADER} ${FOOTER}
	tools/minify-css.sh
	sed -i 's|/res/styles/styles.css|/res/styles/min.css|g' ${HEADER}
	# update build-id in footer
	sed -i 's/{commit}/$(shell git log --format="%H" -n 1)/g' ${FOOTER}
	sed -i 's/{short}/$(shell git log --format="%h" -n 1)/g' ${FOOTER}
	sed -i 's/{timestamp}/$(shell date -u "+%Y-%m-%d %H:%M:%S")/g' ${FOOTER}
	if [[ $(shell git status -s | wc -l) == 0 ]]; then \
		sed -i 's/{comment}/clean/g' ${FOOTER} ;\
		sed -i 's/{class}/clean/g' ${FOOTER} ;\
	else \
		sed -i 's/{comment}/uncommited changes/g' ${FOOTER} ;\
		sed -i 's/{class}/uncommited-changes/g' ${FOOTER} ;\
	fi
	# create .ico file from svg
	convert -background none dest/www/res/svgs/tucal.svg -alpha set -define icon:auto-resize=256,128,64,32,24,16 dest/www/favicon.ico
	# compile .po files
	for locale in $$(ls locale); do \
		mkdir -p "dest/www/.php/locale/$$locale/LC_MESSAGES/" ;\
		msgfmt "locale/$$locale/LC_MESSAGES/tucal.po" -o "dest/www/.php/locale/$$locale/LC_MESSAGES/tucal.mo" ;\
	done

database:
	@read -p "Are you sure, you want to reset the specified database? [y/N] " -r ;\
		if [[ ! "$$REPLY" =~ ^[yY]$  ]]; then echo "aborting!"; exit 1; fi
	for file in $$(ls sql); do \
		tools/db.sh -f "sql/$$file" ;\
	done

clean:
	rm -rf dest/
