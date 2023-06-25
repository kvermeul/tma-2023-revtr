#!/usr/bin/env python3

import ipaddress
import json
import logging
import pathlib
import resource
import sys

import pyasn
import asnames

from revtr import RevTrApi, RevTrMeasurement


DEFAULT_APIKEY_FILE = pathlib.Path("~/.config/revtr.apikey").expanduser()
PYASN_DATA = pathlib.Path("./resources/pyasn_20230625.dat").absolute()
ASNAMES_DATA = pathlib.Path("./resources/autnums.html").absolute()
NUM_SPLITS = 5


def main():
    resource.setrlimit(resource.RLIMIT_AS, (1 << 29, 1 << 29))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 32, 1 << 32))
    logging.basicConfig(format="%(message)s", level=logging.DEBUG)

    revtrs = []
    for i in range(NUM_SPLITS):
        label = f"tma_round1_240_{i}"
        logging.info("Loading %s", label)
        d = json.load(open(f"data/{label}.json", encoding="utf8"))
        revtrs.extend(d["revtrs"])
    logging.info("Loaded %d RevTrs", len(revtrs))

    revtrs = [r for r in revtrs if r["stopReason"] != "FAILED"]
    logging.info("Got %d successfull RevTrs", len(revtrs))

    ip2asn = pyasn.pyasn(str(PYASN_DATA))
    namedb = asnames.ASNamesDB(ASNAMES_DATA)

    rtr = RevTrMeasurement(revtrs[2], ip2asn, namedb)
    print(rtr)




if __name__ == "__main__":
    sys.exit(main())
