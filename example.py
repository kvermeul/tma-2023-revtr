
import json

import requests
from metadata.ip2as import load_ip_to_asn
from processing.helpers import contains_interdomain_assume_symmetry

API_KEY = ""
# Please use pyasn at https://github.com/hadiasghari/pyasn. From the README of the page, use the following commands
# pyasn_util_download.py --latest  # or --latestv46
# pyasn_util_convert.py --single <Downloaded RIB File> <ipasn_db_file_name> and use <ipasn_db_file_name> below
ip2asn = load_ip_to_asn("resources/bgpdumps/2023_05_05.dat")


def get_sources():

    """
    Fetch the M-Lab sources that you can use to measure reverse traceroutes
    from arbitrary destinations back to these sources.
    :return:
    """

    url = "https://revtr.ccs.neu.edu/api/v1/sources"
    headers = {
        "Revtr-Key": API_KEY
    }
    results = requests.get(url, headers=headers)

    return results

def run_revtrs(source_destination_pair, label):

    """
    Run a list of reverse traceroutes with the given label
    :param source_destination_pair:
    :param label:
    :return:
    """

    url = "https://revtr.ccs.neu.edu/api/v1/revtr"

    headers = {
        "Revtr-Key": API_KEY
    }

    revtrs = []
    for source, destination in source_destination_pair:
        revtrs.append({"src": source, "dst": destination, "label": label})
    data = {
        "revtrs": revtrs
    }
    results = requests.post(url=url, data=json.dumps(data), headers=headers)
    print(results.json())
    return results

def fetch_revtr(batch_id):

    """
    Fetch the results of a batch of revtrs
    :param batch_id:
    :return:
    """

    url = f"https://revtr.ccs.neu.edu/api/v1/revtr?batchid={batch_id}"
    headers = {
        "Revtr-Key": API_KEY
    }
    results = requests.get(url, headers=headers)
    results_ = results.json()
    if "revtrs" in results_:
        return results_["revtrs"]
    return []

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

    label = "debug_tma"
    results = run_revtrs(revtr_source_destination_pairs, label)

def example_fetch():
    revtrs = fetch_revtr(86)
    is_trustworthy = contains_interdomain_assume_symmetry(revtrs[0], ip2asn)
    print_revtrs(revtrs)
    print(is_trustworthy)

if __name__ == "__main__":
    example_fetch()


