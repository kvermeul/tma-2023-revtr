#!/usr/bin/env python3

import logging
import pathlib
import resource
import sys
import time
from ipaddress import IPv4Network

import requests

from revtr import RevTrApi


DEFAULT_APIKEY_FILE = pathlib.Path("~/.config/revtr.apikey").expanduser()
DEFAULT_PREFIXES_FILE = pathlib.Path("./prefixes.txt").absolute()
DEFAULT_SLEEP_INTERVAL = 5


def main():
    resource.setrlimit(resource.RLIMIT_AS, (1 << 29, 1 << 29))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 32, 1 << 32))
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)

    with open(DEFAULT_APIKEY_FILE, encoding="utf8") as fd:
        apikey = fd.read().strip()

    api = RevTrApi(apikey)

    with open(DEFAULT_PREFIXES_FILE, encoding="utf8") as fd:
        prefixes = [IPv4Network(n.strip()) for n in fd.readlines()]

    for prefix in prefixes:
        vpaddr = next(prefix.hosts())
        logging.info("Resetting atlas for %s", vpaddr)
        api.atlas_reset(vpaddr)
        logging.info("Sleeping %ds", DEFAULT_SLEEP_INTERVAL)
        time.sleep(DEFAULT_SLEEP_INTERVAL)

    for prefix in prefixes:
        vpaddr = next(prefix.hosts())
        logging.info("Rebuilding atlas for %s", vpaddr)
        try:
            api.atlas_rebuild(vpaddr)
        except requests.HTTPError:
            # Requests run successfully but always time-out on the server side
            pass
        logging.info("Sleeping %ds", DEFAULT_SLEEP_INTERVAL)
        time.sleep(DEFAULT_SLEEP_INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
