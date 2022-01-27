#!/bin/bash
regex="s/^[^=]\+=\\s*['\"]\?\(.*\)['\"]\?\\s*$/\\1/"
db=$(grep '\[database\]' -A 10 tucal.ini)
host=$(echo "$db" | grep "^host *=" | sed "$regex")
port=$(echo "$db" | grep "^port *=" | sed "$regex")
user=$(echo "$db" | grep "^user *=" | sed "$regex")
name=$(echo "$db" | grep "^name *=" | sed "$regex")
pwd=$(echo "$db" | grep "^password *=" | sed "$regex")
echo "$host"
PGPASSWORD="$pwd" psql -h "$host" -p "$port" "$name" "$user" $@
