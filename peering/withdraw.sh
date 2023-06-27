#!/bin/bash
set -eu

PREFIXFILE=../../prefixes.txt

while read -r prefix ; do
    sudo ../../peering prefix withdraw "$prefix"
done < $PREFIXFILE
