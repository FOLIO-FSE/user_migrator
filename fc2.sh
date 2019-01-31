#!/bin/sh
TARGET=$1
SOURCE=$2
RES="/md/five_colleges/res/"
MAP="/md/five_colleges/hampat_user_mapping.tsv"
MAPPER="aleph"
echo "Processing files in $TARGET"
for i in "$TARGET"/*.json;do
	echo "Processing $i"
	pipenv run python3 main.py "$i" "$RES" "$MAP" $MAPPER $SOURCE
done
echo "DONE!"
