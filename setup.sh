#!/bin/bash

if [ ! -f tucal.ini ]; then
    echo "tucal.ini does not exist" >&2
    exit 1;
fi

psql -h "$host" -p "$port" "$dbname" "$user"

make build-www
