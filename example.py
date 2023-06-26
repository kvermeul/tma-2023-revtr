
import json

import requests
import pyasn
from processing.helpers import contains_interdomain_assume_symmetry
from revtr_api.rest import fetch_revtr, run_revtrs


API_KEY = ""
# Please use pyasn at https://github.com/hadiasghari/pyasn. From the README of the page, use the following commands
# pyasn_util_download.py --latest  # or --latestv46
# pyasn_util_convert.py --single <Downloaded RIB File> <ipasn_db_file_name> and use <ipasn_db_file_name> below
PYASN_DATA = "resources/pyasn_20230625.dat"
ip2asn = pyasn.pyasn(str(PYASN_DATA))

label_revtrs = "tma_round1_240_3"

def print_revtrs(revtrs):
    for revtr in revtrs:
        print_revtr_path(revtr)
        print()

def print_revtr_path(revtr):

    """
    Only print the information of a path useful for the tutorial, adding AS metadata
    :param revtr:
    :return:
    """
    status = revtr["status"]
    stop_reason = revtr["stopReason"]
    src = revtr["src"]
    dst = revtr["dst"]
    if stop_reason == "FAILED":
        print(f"REVTR 2.0 was unable to measure the reverse path back from {dst} to {src}")
        return

    path = revtr["path"]
    path_with_metadata = []
    for hop_info in path:
        hop = hop_info["hop"]
        hop_type = hop_info["type"]
        # asn, BGP prefix
        asn, bgp = ip2asn.lookup(hop)
        path_with_metadata.append((hop, hop_type, asn))

    for path_hop_info in path_with_metadata:
        print(path_hop_info)

def example():
    sources_response = get_sources()
    sources = sources_response.json()
    revtr_source_destination_pairs = []
    destinations = ["134.157.254.124"]
    for source in sources["srcs"][:1]:
        revtr_source_destination_pairs.append((source["ip"], destinations[0]))

    results = run_revtrs(revtr_source_destination_pairs, label_revtrs)

def example_fetch():
    revtrs = fetch_revtr(None, label_revtrs)
    is_trustworthy = contains_interdomain_assume_symmetry(revtrs[0], ip2asn)
    print_revtrs(revtrs)
    print(is_trustworthy)

if __name__ == "__main__":
    example_fetch()


