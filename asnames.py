'''AS names database

This module parses a file with information about AS names.  The current
parser works with the information at bgp.potaroo.net/cidr/autnums.html,
which looks like

<a href="/cgi-bin/as-report?as=AS0&view=2.0">AS0    </a> -Reserved AS-, ZZ
<a href="/cgi-bin/as-report?as=AS1&view=2.0">AS1    </a> LVLT-1, US
<a href="/cgi-bin/as-report?as=AS2&view=2.0">AS2    </a> UDEL-DCN, US
<a href="/cgi-bin/as-report?as=AS3&view=2.0">AS3    </a> MIT-GATEWAYS, US
<a href="/cgi-bin/as-report?as=AS4&view=2.0">AS4    </a> ISI-AS, US
<a href="/cgi-bin/as-report?as=AS5&view=2.0">AS5    </a> SYMBOLICS, US
...
<a href="/cgi-bin/as-report?as=AS400802&view=2.0">AS400802</a> RAYNET-FIBER, US
<a href="/cgi-bin/as-report?as=AS400803&view=2.0">AS400803</a> AS-TORIX-TIME, CA
<a href="/cgi-bin/as-report?as=AS400804&view=2.0">AS400804</a> AQUEOUS-CLOUD, US
<a href="/cgi-bin/as-report?as=AS400805&view=2.0">AS400805</a> DS-BACKBONE, US
<a href="/cgi-bin/as-report?as=AS400806&view=2.0">AS400806</a> SHAKEN-ANYCAST, US
<a href="/cgi-bin/as-report?as=AS400807&view=2.0">AS400807</a> BMU-GW-01, US

The first token contains the AS number.  The rest of the line is the AS
name and country code.  If the first token of the AS name contains only
capital letters or dashes, then we call that the "short" name of the AS.

Standard use goes like:

    db = ASNamesDB(path_to_file)
    assert db[2].full() == 'UDEL-DCN'
    assert db[2].short() == 'UDEL-DCN'
    assert db[2].cc() == 'US'

Author: Italo Cunha <cunha@dcc.ufmg.br>
License: Latest version of the GPL.
'''

import re
import logging

_shortname_regex_string = r'^([-A-Z]+)\s+.*$'
_shortname_regexp = re.compile(_shortname_regex_string)
def _full2short(string):
    m = _shortname_regexp.match(string)
    return string if m is None else m.group(1)


UNKNOWN_FULL = 'UNKNOWN-NAMESDB - ASNamesDB unknown AS number'
UNKNOWN_SHORT = _full2short(UNKNOWN_FULL)
UNKNOWN_CC_STR = "ZZ"


def str2asn(string):
    if isinstance(string, int):
        return string
    if '.' in string:
        first, second = string.split('.')
        return int(first) * (1<<16) + int(second)
    return int(string)

# <a href="/cgi-bin/as-report?as=AS5&view=2.0">AS5    </a> SYMBOLICS, US

_parse_regexp_string = r'>AS(\d+|\d+\.\d+)\s*</a> (.*), (..)$'
_parse_regexp = re.compile(_parse_regexp_string)
def _parse(line):
    m = _parse_regexp.search(line)
    if m is None:
        return None
    return str2asn(m.group(1)), m.group(2), m.group(3)


class ASNamesDB:
    def __init__(self, fn):
        self.asn2full = {}
        self.asn2short = {}
        self.asn2cc = {}
        fd = open(fn, encoding="utf8")
        for line in fd:
            line = line.strip()
            t = _parse(line)
            if t is None:
                continue
            asn, full, cc = t
            self.asn2full[asn] = full
            self.asn2short[asn] = _full2short(full)
            self.asn2cc[asn] = cc
        fd.close()
        logging.info('ASNamesDB %d ASes from %s', len(self.asn2full), fn)

    def full(self, asn):
        if asn is None:
            return None
        return self.asn2full.get(int(asn), UNKNOWN_FULL)

    def short(self, asn):
        if asn is None:
            return None
        return self.asn2short.get(int(asn), self.full(asn))

    def cc(self, asn: int) -> str:
        return self.asn2cc.get(int(asn), UNKNOWN_CC_STR)
