#!/usr/bin/env python3.11

from __future__ import annotations

import enum
import itertools
import json
import logging
import os
import time
from collections import deque
from pathlib import Path
from typing import IO

from peering import Announcement, AnnouncementController, Update, UpdateSet

DATADIR = Path("data")
OUTDIR = Path("output")

ROUND_DURATION_SECS = 90 * 60
WITHDRAWAL_DURATION_SECS = 10 * 60

PEERING_ORIGIN = 47065
IGNORED_ASNS: set[int] = set([])

BIT_ID = 60  # Bit.BV's peer ID
RGNET_ID = 101  # RG.net's peer ID

MuxPair = tuple[str, str]


PREFIXES = [
    "184.164.224.0/24",
    "184.164.225.0/24",
]


class PeeringMux(enum.StrEnum):
    AMSTERDAM = "amsterdam01"
    CLEMSON = "clemson01"
    GATECH = "gatech01"
    ISI = "isi01"
    NEU = "neu01"
    PHOENIX = "phoenix01"
    SAOPAULO = "saopaulo01"
    SBU = "sbu01"
    SEATTLE = "seattle01"
    UFMG = "ufmg01"
    UTAH = "utah01"
    WISC = "wisc01"


class VultrMux(enum.StrEnum):
    MIAMI = "miami"
    ATLANTA = "atlanta"
    AMSTERDAM = "amsterdam"
    TOKYO = "tokyo"
    SYDNEY = "sydney"
    FRANKFURT = "frankfurt"
    SEATTLE = "seattle"
    CHICAGO = "chicago"
    PARIS = "paris"
    SINGAPORE = "singapore"
    WARSAW = "warsaw"
    NEWYORK = "newyork"
    DALLAS = "dallas"
    MEXICO = "mexico"
    TORONTO = "toronto"
    MADRID = "madrid"
    STOCKHOLM = "stockholm"
    BANGALORE = "bangalore"
    DELHI = "delhi"
    LOSANGELAS = "losangelas"
    SILICON = "silicon"
    LONDON = "london"
    MUMBAI = "mumbai"
    SEOUL = "seoul"
    MELBOURNE = "melbourne"
    SAOPAULO = "saopaulo"
    JOHANNESBURG = "johannesburg"
    OSAKA = "osaka"


def main() -> None:
    logging.basicConfig(format="%(message)s", level=logging.DEBUG)

    os.makedirs(OUTDIR, exist_ok=True)
    controller = AnnouncementController()

    def ann(mux, communities=[], prepend=[]):
        return Announcement([mux], [], communities, prepend)

    prefix2update = {
        "184.164.224.0/24": Update([], [ann("amsterdam")]),
        "184.164.225.0/24": Update([], [ann("miami")]),
        "184.164.231.0/24": Update([], [ann("tokyo")]),
        "184.164.232.0/24": Update([], [ann("seattle")]),
        "184.164.234.0/24": Update([], [ann("amsterdam")]),  # bad
        "184.164.235.0/24": Update([], [ann("amsterdam")]),  # bad
        "184.164.238.0/24": Update([], [ann("delhi")]),
        "184.164.239.0/24": Update([], [ann("saopaulo")]),
        "184.164.240.0/24": Update([], [ann("amsterdam"), ann("tokyo"), ann("seattle"), ann("saopaulo"), ann("delhi"), ann("miami")]),
        "184.164.242.0/24": Update([], [ann("amsterdam"), ann("seattle"), ann("saopaulo"), ann("delhi"), ann("miami")]),
        "184.164.243.0/24": Update([], [ann("amsterdam"), ann("tokyo"), ann("saopaulo"), ann("delhi"), ann("miami")]),
        "184.164.244.0/24": Update([], [ann("amsterdam"), ann("tokyo"), ann("seattle"), ann("delhi"), ann("miami")]),
        "184.164.245.0/24": Update([], [ann("amsterdam"), ann("tokyo"), ann("seattle"), ann("saopaulo"), ann("miami")]),
        "184.164.246.0/24": Update([], [ann("amsterdam"), ann("tokyo"), ann("seattle"), ann("saopaulo"), ann("delhi")]),
        "184.164.247.0/24": Update([], [ann("tokyo"), ann("seattle"), ann("saopaulo"), ann("delhi"), ann("miami")]),
        "184.164.248.0/24": Update([], [ann("seattle"), ann("saopaulo"), ann("delhi"), ann("miami")]),
        "184.164.249.0/24": Update([], [ann("amsterdam"), ann("tokyo"), ann("seattle"), ann("saopaulo", communities=[(20473,6003)]), ann("delhi", communities=[(20473,6003)]), ann("miami")]),
        "184.164.250.0/24": Update([], [ann("amsterdam"), ann("tokyo"), ann("seattle"), ann("saopaulo", communities=[(64603,174)]), ann("delhi", communities=[(64603, 9498)]), ann("miami")]),
        "184.164.251.0/24": Update([], [ann("amsterdam"), ann("tokyo"), ann("seattle"), ann("saopaulo"), ann("delhi", communities=[(64600, 9498)]), ann("miami")]),
        "184.164.254.0/24": Update([], [ann("amsterdam"), ann("tokyo"), ann("seattle"), ann("saopaulo"), ann("delhi", communities=[(64600, 9498)]), ann("miami")]),
    }

    us = UpdateSet(prefix2update)
    controller.validate(us)
    controller.deploy(us)


if __name__ == "__main__":
    main()
