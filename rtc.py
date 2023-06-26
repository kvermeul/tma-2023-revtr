#!/usr/bin/env python3

import argparse
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


def create_parser():
    desc = """Reverse Traceroute Client"""
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        "--apikey",
        dest="apikey",
        action="store",
        metavar="APIKEY",
        type=str,
        required=False,
        default=None,
        help="Reverse Traceroute API key [read from ~/.config/revtr.apikey]",
    )
    sc = parser.add_subparsers(title="command", dest="command", required=True)
    _parser_sources = sc.add_parser("sources", help="List available sources")
    parser_atlas = sc.add_parser("atlas", help="Manage forward traceroute atlas")
    parser_launch = sc.add_parser("launch", help="Execute a reverse traceroute")
    parser_batch = sc.add_parser("batch", help="Execute a batch of reverse traceroutes")
    parser_fetch = sc.add_parser("fetch", help="Fetch reverse traceroutes")
    parser_print = sc.add_parser("print", help="Print reverse traceroutes from file")

    parser_atlas.add_argument(
        "--vp",
        dest="vp",
        action="store",
        metavar="IP",
        type=ipaddress.IPv4Address,
        required=True,
        help="Reverse Traceroute vantage point",
    )
    g = parser_atlas.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--reset",
        dest="atlas_operation",
        action="store_const",
        const="reset",
        help="Remove all paths from current forward traceroute atlas",
    )
    g.add_argument(
        "--rebuild",
        dest="atlas_operation",
        action="store_const",
        const="rebuild",
        help="Rebuild forward traceroute atlas",
    )

    parser_launch.add_argument(
        "--remote",
        dest="remote",
        action="store",
        metavar="IP",
        type=ipaddress.IPv4Address,
        required=True,
        help="Reverse traceroute source (remote endpoint)",
    )
    parser_launch.add_argument(
        "--vp",
        dest="vp",
        action="store",
        metavar="IP",
        type=ipaddress.IPv4Address,
        required=True,
        help="Reverse traceroute destination (controlled vantage point)",
    )
    parser_launch.add_argument(
        "--label",
        dest="label",
        action="store",
        metavar="STRING",
        type=str,
        required=True,
        help="Label to store results under",
    )

    parser_batch.add_argument(
        "--label",
        dest="label",
        action="store",
        metavar="STRING",
        type=str,
        required=True,
        help="Label to store results under",
    )
    parser_batch.add_argument(
        "--file",
        dest="file",
        action="store",
        metavar="PATH",
        type=pathlib.Path,
        required=True,
        help="File containing a VP and remote per line (space-separated)",
    )

    parser_fetch.add_argument(
        "--label",
        dest="label",
        action="store",
        metavar="STRING",
        type=str,
        required=True,
        help="Label to fetch",
    )
    parser_fetch.add_argument(
        "--print",
        dest="print",
        action="store_true",
        required=False,
        default=False,
        help="Print reverse traceroute on screen",
    )

    parser_fetch.add_argument(
        "--file",
        dest="file",
        action="store",
        metavar="PATH",
        type=pathlib.Path,
        required=True,
        help="Json file to store the revtr",
    )

    parser_print.add_argument(
        "--file",
        dest="file",
        action="store",
        metavar="JSONL",
        type=pathlib.Path,
        required=True,
        help="File containing reverse traceroute JSON (one per line)",
    )
    return parser


def main():

    # resource.setrlimit(resource.RLIMIT_AS, (1 << 29, 1 << 29))
    # resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 32, 1 << 32))
    logging.basicConfig(format="%(message)s", level=logging.DEBUG)

    parser = create_parser()
    opts = parser.parse_args()

    if opts.apikey is None:
        with open(DEFAULT_APIKEY_FILE, encoding="utf8") as fd:
            opts.apikey = fd.read().strip()

    api = RevTrApi(opts.apikey)

    if opts.command == "sources":
        r = api.sources()
    elif opts.command == "atlas":
        if opts.atlas_operation == "reset":
            r = api.atlas_reset(opts.vp)
        elif opts.atlas_operation == "rebuild":
            r = api.atlas_rebuild(opts.vp)
        else:
            raise RuntimeError("Unreachable")
    elif opts.command == "launch":
        r = api.launch(opts.vp, opts.remote, opts.label)
    elif opts.command == "batch":
        with open(opts.file, encoding="utf8") as fd:
            pairs = [tuple(line.split()) for line in fd]
        r = api.batch(pairs, opts.label)
    elif opts.command == "fetch":
        r = api.fetch(opts.label)
        if opts.print:
            ip2asn = pyasn.pyasn(str(PYASN_DATA))
            namedb = asnames.ASNamesDB(ASNAMES_DATA)
            for revtr in r["revtrs"]:
                measurement = RevTrMeasurement(revtr, ip2asn, namedb)
                print(measurement)
            r = ""
        elif opts.file:
            with open(opts.file, "w") as f:
                json.dump(r, f)
    else:
        raise RuntimeError("Unreachable")
    print(json.dumps(r))


if __name__ == "__main__":
    sys.exit(main())
