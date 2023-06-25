import requests
API_KEY = 
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

def fetch_revtr(batch_id, label):

    """
    Fetch the results of a batch of revtrs
    :param batch_id:
    :return:
    """
    # XOR
    assert(bool(batch_id is not None) ^ bool(label != ""))
    if batch_id is not None:
        url = f"https://revtr.ccs.neu.edu/api/v1/revtr?batchid={batch_id}"
    else:
        url = f"https://revtr.ccs.neu.edu/api/v1/revtr?label={label}"

    headers = {
        "Revtr-Key": API_KEY
    }
    results = requests.get(url, headers=headers)
    results_ = results.json()
    if "revtrs" in results_:
        return results_["revtrs"]
    return []