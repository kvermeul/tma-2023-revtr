#!/usr/bin/env python3

import argparse
import ipaddress
import json
import logging
import pathlib
import resource
import sys
from collections import Counter

import pyasn
import asnames

from revtr import RevTrApi, RevTrMeasurement


def create_parser():
    desc = """Compute provider catchment from reverse traceroutes"""
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        dest="files",
        nargs="+",
        metavar="FILE",
        type=str,
        help="List of JSON files to load",
    )

    return parser


DEFAULT_APIKEY_FILE = pathlib.Path("~/.config/revtr.apikey").expanduser()
PYASN_DATA = pathlib.Path("../resources/pyasn_20230625.dat").absolute()
ASNAMES_DATA = pathlib.Path("../resources/autnums.html").absolute()
NUM_SPLITS = 5


def main():
    logging.basicConfig(format="%(message)s", level=logging.DEBUG)

    parser = create_parser()
    opts = parser.parse_args()

    revtrs = []
    for file in opts.files:
        logging.info("Loading %s", file)
        d = json.load(open(file, encoding="utf8"))
        revtrs.extend(d["revtrs"])
    logging.info("Loaded %d RevTrs", len(revtrs))

    revtrs = [r for r in revtrs if r["stopReason"] != "FAILED"]
    logging.info("Got %d successfull RevTrs", len(revtrs))

    ip2asn = pyasn.pyasn(str(PYASN_DATA))
    namedb = asnames.ASNamesDB(ASNAMES_DATA)

    asn2cnt = Counter()
    for revtrjson in revtrs:
        revtr = RevTrMeasurement(revtrjson, ip2asn, namedb)
        if revtr.hops[-1].asn != 47065:
            continue
        if revtr.hops[-2].asn != 19969:
            continue
        for hop in reversed(revtr.hops[:-2]):
            if hop.asn == 20473:
                # Skip Vultr itself
                continue
            if hop.asn is not None:
                asn2cnt[(hop.asn, hop.asname)] += 1
                break

    total = asn2cnt.total()
    count_astuple = sorted([(cnt, ast) for ast, cnt in asn2cnt.items()])
    for count, astuple in count_astuple:
        asn, asname = astuple
        print(f"{asn} {count} {100 * count / total:.3f}% ({asname})")


if __name__ == "__main__":
    sys.exit(main())
