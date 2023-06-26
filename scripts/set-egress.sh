#!/bin/bash
set -eu

source common.sh

function usage {
    cat <<HELP
usage: $0 -i <IP> -e <POP>

    IP: IP allocated to the container
    POP: Egress POP to route egress packets through
HELP
    exit 0
}

ip=invalid
egress=invalid

while getopts "e:i:h" OPT; do
case $OPT in
i)
    ip=$OPTARG
    ;;
e)
    egress=$OPTARG
    ;;
h|*)
    usage
    ;;
esac
done
shift $(( OPTIND - 1 ))
OPTIND=1

octet3=$(echo $ip | sed -e 's|184.164.\([0-9]*\).[0-9]*|\1|')
octet4=$(echo $ip | sed -e 's|184.164.[0-9]*.\([0-9]*\)|\1|')

prefix="184.164.$octet3.0/24"
if [[ ${prefix2idx[$prefix]:-unknown} == unknown ]] ; then
    die "Prefix $prefix is not managed" 1
fi

muxid=${mux2id[$egress]:-unknown}

if [[ $muxid == unknown ]] ; then
    die "Egress $egress is unknown" 1
fi

tableid=$((octet3 % 100))$(printf "%02d" $octet4)

echo "$ip $egress muxid=$muxid octet3=$octet3 octet4=$octet4 tableid=$tableid"

sudo ip rule add from $ip lookup $tableid prio $tableid &> /dev/null || true
sudo ip route flush table $tableid &> /dev/null || true
sudo ip route add default via 100.$((64+muxid)).128.1 table $tableid
