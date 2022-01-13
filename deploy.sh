#/bin/bash

host="$1"
path="$2"

if [ -z "$host"  ] || [ -z "$path" ]; then
	echo "deploy.sh: usage: deploy.sh <host> <path>" >&2
	exit 1
fi

make build-www
ssh "$1" "cd $path; rm -rf *; rm -rf .php"
scp -rpq dest/www/* "$1:$2"
scp -rpq dest/www/.php "$1:$2"
