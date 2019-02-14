#!/bin/sh
TARGET=$1
SOURCE=$2
RES="/md/five_colleges/res/"
MAP="/md/five_colleges/fc_user_mapping.tsv"
MAPPER="five_colleges"
echo "Erasing results in $RES"
rm -vr $RES/*
echo "Processing files in $TARGET"
for i in "$TARGET"/*.json;do
	echo "Processing $i"
	pipenv run python3 main.py "$i" "$RES" "$MAP" $MAPPER $SOURCE
done
echo "DONE!"
