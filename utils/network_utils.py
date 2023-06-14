import sys
import socket
from collections import namedtuple

def ipItoStr(ip):
    '''
    Use this function rather than python ipaddress.ip_address, way faster
    :param ip:
    :return:
    '''
    return f"{str((ip & 0xFF000000) >> 24)}.{str((ip & 0x00FF0000) >> 16)}.{str((ip & 0x0000FF00) >> 8)}.{str(ip & 0x000000FF)}"

def ipv4_index_of( addr ):
    try:
        as_bytes = socket.inet_aton(addr)
    except OSError as e:
        sys.exit("on trying socket.inet_aton({}), received error {}".format(addr, e))
    return int.from_bytes(as_bytes, byteorder='big', signed=False)

DnetEntry = namedtuple('DnetEntry',['asn','bgp'])

def dnets_of(ip, ipasn, ip_representation = None):
    if ip_representation == "uint32":
        ip = ipItoStr(ip)
    try:
        return DnetEntry(*(ipasn.lookup(ip)))
    except:
        return DnetEntry('','',)