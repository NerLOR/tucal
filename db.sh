#!/bin/bash
db=$(grep '\[database\]' -A 10 tucal.ini)
host=$(echo "$db" | grep "^host *=" | grep -o '[^= ]*$')
port=$(echo "$db" | grep "^port *=" | grep -o '[^= ]*$')
user=$(echo "$db" | grep "^user *=" | grep -o '[^= ]*$')
name=$(echo "$db" | grep "^name *=" | grep -o '[^= ]*$')
pwd=$(echo "$db" | grep "^password *=" | grep -o '[^= ]*$')
PGPASSWORD="$pwd" psql -h "$host" -p "$port" "$name" "$user" $@
