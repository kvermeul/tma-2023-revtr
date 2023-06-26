#!/usr/bin/env python3

import logging
import pathlib
import resource
import sys
from ipaddress import IPv4Address, IPv4Network

import requests

from revtr import RevTrApi


DEFAULT_APIKEY_FILE = pathlib.Path("~/.config/revtr.apikey").expanduser()
DEFAULT_PREFIXES_FILE = pathlib.Path("./prefixes.txt").absolute()
DEFAULT_SLEEP_INTERVAL = 5
BATCH_SIZE = 1000
ROUND_NUMBER = 1
LAST_ROUND = 1


def main():
    resource.setrlimit(resource.RLIMIT_AS, (1 << 29, 1 << 29))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 32, 1 << 32))
    logging.basicConfig(format="%(message)s", level=logging.DEBUG)

    if ROUND_NUMBER == LAST_ROUND:
        logging.error(
            "Please update the round number. Rerun, and then update the last round number."
        )
        sys.exit(1)

    with open(DEFAULT_APIKEY_FILE, encoding="utf8") as fd:
        apikey = fd.read().strip()

    api = RevTrApi(apikey)

    with open(DEFAULT_PREFIXES_FILE, encoding="utf8") as fd:
        prefixes = [IPv4Network(n.strip()) for n in fd.readlines() if n[0] != "#"]
    logging.info("Read %d prefixes", len(prefixes))

    with open("resources/5000-targets.txt", encoding="utf8") as fd:
        targets = [IPv4Address(n.strip()) for n in fd.readlines() if n[0] != "#"]
    logging.info("Read %d targets", len(targets))

    for prefix in prefixes:
        vp = next(prefix.hosts())
        octet = int(prefix.network_address.packed[2])
        i = 0
        while i * BATCH_SIZE < len(targets):
            pairs = [
                (str(vp), str(t))
                for t in targets[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
            ]
            try:
                api.batch(pairs, f"tma_round{ROUND_NUMBER}_{octet}_{i}")
            except requests.HTTPError as e:
                logging.warning(
                    "Launching batch %s failed: %s", f"tma_round1_{octet}_{i}", str(e)
                )
            i += 1


if __name__ == "__main__":
    sys.exit(main())
