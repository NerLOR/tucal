#!/bin/bash
dir="$1"
in="$2"
out="$3"
tmp="msgfmt.tmp.js"
tmp2="$3.tmp"
if [[ -z "$dir" || -z "$in" || -z "$out" ]]; then
  echo "msgfmtjs.sh: usage: msgfmtjs.sh <locale-dir> <input-file> <output-file>" >&2
  exit 1
fi

msgids=$(grep -ohe "_(['\"][^'\"]*['\"])" typescript/src/* | sed "s/_([\"']\|[\"'])//g" | sort | uniq)

rm -rf "$tmp"
first1="t"
msgctx=""
msgid=""
msgstr=""
for loc in "$dir"/*; do
  loc="${loc:${#dir}+1}"
  first2="t"
  if [[ -z "$first1" ]]; then echo -ne ",\n" >>"$tmp"; fi
  echo -ne "    \"${loc/_/-}\": {\n" >>"$tmp"
  { cat "$dir/$loc/LC_MESSAGES/tucal.po"; echo -ne "\n"; } | while read -r line; do
    if [[ "$line" =~ ^msgid ]]; then
      msgid="${line:7:-1}"
    elif [[ "$line" =~ ^msgctx ]]; then
      msgctx="${line:8:-1}"
    elif [[ "$line" =~ ^msgstr ]]; then
      msgstr="${line:8:-1}"
    elif [[ -z "$line" ]]; then
      if [[ -n "$msgid" && -z "$msgctx" && $(echo "$msgids" | grep -c "^${msgid}$") -gt 0 ]]; then
        if [[ -z "$first2" ]]; then echo -ne ",\n" >>"$tmp"; fi
        echo -ne "        \"$msgid\": \"$msgstr\"" >>"$tmp"
        first2=""
      fi
      msgctx=""
      msgid=""
      msgstr=""
    elif [[ "$line" =~ ^\s*\" ]]; then
      msgstr="$msgstr${line:1:-1}"
    fi
  done
  echo -ne "\n    }" >>"$tmp"
  first1=""
done
echo -ne "\n" >>"$tmp"

sed "/const MESSAGES/r $tmp" "$in" > "$tmp2"
mv "$tmp2" "$out"
rm -rf "$tmp"
