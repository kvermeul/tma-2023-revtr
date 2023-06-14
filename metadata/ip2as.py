import pyasn

def load_ip_to_asn(ip_to_asn_file):
    ip2asn = pyasn.pyasn(ip_to_asn_file)
    return ip2asn