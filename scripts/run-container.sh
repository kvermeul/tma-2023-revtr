#!/bin/bash
set -eu

source common.sh

function usage {
    cat <<HELP
usage: $0 -p <PREFIX>

    PREFIX: Prefix to run this container inside
HELP
    exit 0
}

prefix=invalid

while getopts "p:h" OPT; do
case $OPT in
p)
    prefix=$OPTARG
    ;;
h|*)
    usage
    ;;
esac
done
shift $(( OPTIND - 1 ))
OPTIND=1

if [[ $prefix == invalid ]] ; then
    usage
fi

bridge=${prefix2idx[$prefix]:-unknown}

if [[ $bridge == unknown ]] ; then
    die "Prefix $prefix not managed" 1
fi

docker run --network pbr$bridge --rm --dns 8.8.8.8 -it mdeb
