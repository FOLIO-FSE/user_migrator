#!/bin/sh
INFILE=$1
SOURCE_NAME=$2
RES="/md/alabama/res/"
MAP="/md/alabama/hampat_user_mapping.tsv"
MAPPER="alabama_banner"
echo "Erasing results in $RES"
rm -rv $RES/*
echo "Processing $INFILE"
pipenv run python3 main.py "$INFILE" "$RES" "$MAP" $MAPPER $SOURCE_NAME
echo "DONE!"
