#/bin/bash
host="$1"
path="$2"
if [[ -z "$host"  || -z "$path" ]]; then
	echo "deploy.sh: usage: deploy.sh <host> <path>" >&2
	exit 1
fi

make build-www || exit
ssh "$host" "cd \"$path\" && rm -rf .php account api calendar courses friends res *.*"
scp -rpq dest/www/* "$host:$path"
scp -rpq dest/www/.php "$host:$path"
