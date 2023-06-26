# Case Study 1 - Poor Anycast Performance

In this case study we consider a service hosted on Vultr using prefix `184.164.240.0/24`.  We anycast the prefix `184.164.240.0/24` from six Vultr PoPs in an attempt to improve performance globally: Amsterdam, Tokyo, Seattle, São Paulo, Delhi, and Miami.

After route convergence, the service provider gets performance complaints from a Canadian ISP.  The ISP reports that IP address `204.244.0.10` is less than 5ms from Seattle, but RTTs to services hosted on `184.164.240.0/24` are much (about 220ms) higher than expected.

## Verifying the Problem

Let's issue pings from Seattle to the destination to verify the problem.

> In this tutorial, we will not have access to the VMs running on Vultr.  Instead, we will have access to a server running on a datacenter in Texas.  The server has a somewhat complex network configuration.  To avoid further complexity on the host's network namespace, we will create containers to isolate the additional network configuration needed to run measurements.

We can use the `run-container.sh` script to launch a container using a prefix in a specified prefix:

```bash
./run-container.sh -p 184.164.240.0/24
```

> The server has an OpenVPN tunnel with each Vultr PoP.  As the server is connected to multiple Vultr PoPs (and the datacenter), we need to explicitly choose which Vultr PoP to use as egress for measurements.

We can use the `set-egress.sh` script to set the egress PoP for a given IP address.  Check the IP address inside `184.164.240/24` assigned to your container running `ip addr`, and then configure it to egress through Seattle:

```bash
./set-egress.sh -i 184.164.240.X -e seattle
```

You can then issue measurements from your container.  Running pings
indeed show a very high RTT:

```bash
root@181b0d711bb2:/# ping 204.244.0.10
PING 204.244.0.10 (204.244.0.10) 56(84) bytes of data.
64 bytes from 204.244.0.10: icmp_seq=1 ttl=45 time=287 ms
64 bytes from 204.244.0.10: icmp_seq=2 ttl=45 time=286 ms
64 bytes from 204.244.0.10: icmp_seq=3 ttl=45 time=287 ms
```

Traceroute provides additional information:

```bash
root@181b0d711bb2:/# traceroute 204.244.0.10
traceroute to 204.244.0.10 (204.244.0.10), 30 hops max, 60 byte packets
 1  184.164.240.254  0.047 ms  0.031 ms  0.029 ms
 2  * * *
 3  137.220.39.64.vultrusercontent.com (137.220.39.64)  49.860 ms  49.844 ms  49.823 ms
 4  * * *
 5  100.100.100.1  49.723 ms  49.717 ms  49.697 ms
 6  10.66.1.149  53.006 ms  49.863 ms  50.199 ms
 7  10.66.18.9  49.981 ms  49.469 ms  49.459 ms
 8  72.29.200.43  51.645 ms  51.636 ms  49.522 ms
 9  98.124.172.206  49.598 ms  49.589 ms  49.637 ms
10  64.230.125.232  54.827 ms  54.786 ms  52.604 ms
11  64.230.79.95  52.945 ms  52.785 ms  52.785 ms
12  64.230.123.249  52.828 ms  52.616 ms  52.669 ms
13  204.244.0.10  286.229 ms  286.083 ms  286.131 ms
```

First, the 50ms latency on the first hop comes from the OpenVPN tunnel between the server in Texas and the Vultr VM in Seattle (`137.220.39.64`).  Second, after getting to Seattle, all hops on the way to the destination (hops 4-12) are within 3ms.  The destination itself, however, is 286ms away.

Although no hop other than hop 3 has a reverse DNS names, we can use query the IRR for the ASNs controlling each prefix to get an idea of where the path is going:

```bash
$ whois 72.29.200.43
NetRange:       72.29.192.0 - 72.29.223.255
CIDR:           72.29.192.0/19
NetName:        AIRBAND-BALTIMORE-01
OriginAS:
Organization:   Airband Communications, Inc (AIRB)
...
$ whois 98.124.172.206
NetRange:       98.124.128.0 - 98.124.191.255
CIDR:           98.124.128.0/18
NetName:        NET-WBS-4
OriginAS:       AS19080
Organization:   GTT (GC-494)
...
$ whois 64.230.125.232
NetRange:       64.228.0.0 - 64.231.255.255
CIDR:           64.228.0.0/14
NetName:        BELLCANADA-5
OriginAS:
Organization:   Bell Canada (LINX)
...
$ whois 204.244.0.10
NetRange:       204.244.0.0 - 204.244.255.255
CIDR:           204.244.0.0/16
NetName:        WESTNETBLK
OriginAS:
Organization:   Navigata Communications Limited (CANAD-87-Z)
...
```

## Identifying the Root Cause

Given that path to the destination is well-behaved up to the destination itself (we see only a 3ms latency across all intermediate hops), we can conjecture that the problem is on the reverse path *from the destination* to our prefix.  Without a measurement point within the destination AS however, it would be impossible to measure the reverse path if not for reverse traceroute.

We can issue a reverse traceroute from the destination to our prefix by using the `rtc.py` front-end (the tool's documentation provides more details how to use it):

```bash
$ ./rtc.py launch --vp 184.164.240.1 --remote 204.244.0.10 --label prefix240_204_244_0_10_c1
```

The reverse traceroute takes a while to complete.  We can fetch it with the following command.  Check that the `status` of the traceroute is `COMPLETED`.

```bash
./rtc.py fetch --label prefix240_204_244_0_10_c1 --print
...
$ ./rtc.py fetch --label prefix240_204_244_0_10_c1 --print
Reverse Traceroute from remote 204.244.0.10 to VP 184.164.240.1
  204.244.0.10 5071 (WESTEL-1) CA DST_REV_SEGMENT
  204.244.0.110 5071 (WESTEL-1) CA SPOOF_RR_REV_SEGMENT
  64.125.0.185 6461 (ZAYO-6461) US SPOOF_RR_REV_SEGMENT
  64.125.0.50 6461 (ZAYO-6461) US SPOOF_RR_REV_SEGMENT
  217.31.48.15 29134 (IGNUM-AS) CZ TR_TO_SRC_REV_SEGMENT_BETWEEN
  185.116.51.134 204064 (TANET) CZ TR_TO_SRC_REV_SEGMENT_BETWEEN
  185.0.20.54 None (None) None TR_TO_SRC_REV_SEGMENT_BETWEEN
  185.1.226.123 None (None) None TR_TO_SRC_REV_SEGMENT_BETWEEN
  116.119.104.178 9498 (BBIL-AP) IN TR_TO_SRC_REV_SEGMENT_BETWEEN
  122.184.140.154 9498 (BBIL-AP) IN TR_TO_SRC_REV_SEGMENT_BETWEEN
  69.195.152.146 19969 (JOESDATACENTER) US TR_TO_SRC_REV_SEGMENT_BETWEEN
  184.164.240.1 47065 (PEERING-RESEARCH-TESTBED-USC-UFMG-AS47065) US TR_TO_SRC_REV_SEGMENT_BETWEEN
```

> Without the `--print` parameter, the `fetch` command would just print plain JSON, which you can use to create instance of the `RevTrMeasurement` and process the measurements programmatically.

The `fetch` command prints out the hops on the reverse path, the AS number controlling each prefix, the AS name, the country where the AS is registered, and the type of hop in the Reverse Traceroute measurement.  The reverse traceroute provides a strong indication of what the problem is: the route back from the ISP is choosing the route to the Vultr PoP in Delhi, an example of bad anycast routes.

> This is not specific to PEERING prefixes.  Cloud operators both "groom" bad routing decisions such as these over time by contacting operators and use advanced, dynamic traffic engineering systems to bypass them.

We see that the path from the ISP back to us goes to Zayo, a major Tier-1 network.  Looking at their [Looking Glass](https://lg.zayo.com/lg.cgi) system provides verifies our diagnosis, as Zayo is choosing a route exported by AS9498:

```text
A V Destination        P Prf   Metric 1   Metric 2  Next hop        AS path
* ? 184.164.240.0/24   B 170        200                             9498 20473 47065 I
```

## Fixing the Issue

A brute-force approach to try and fix the problem is to now announce the prefix from Delhi.  We have made an announcement from the other five PoPs using prefix `184.164.245.0/24`.  After launching a container, setting the egress to Seattle, and running traceroute towards the destination, we find that performance is as expected:

```bash
root@c4eb822d61f7:/# traceroute 204.244.0.10
traceroute to 204.244.0.10 (204.244.0.10), 30 hops max, 60 byte packets
 1  184.164.245.254  0.818 ms  0.709 ms  0.644 ms
 2  * * *
 3  137.220.39.64.vultrusercontent.com  49.616 ms  49.537 ms  49.556 ms
 4  * * *
 5  100.100.200.1  55.635 ms  55.633 ms  55.645 ms
 6  10.66.0.133  50.225 ms  50.619 ms  50.578 ms
 7  10.66.1.45  50.334 ms  50.271 ms  50.295 ms
 8  4.59.233.49  51.767 ms  49.958 ms  51.722 ms
 9  4.69.219.206  50.226 ms  54.206 ms  49.590 ms
10  64.230.125.230  58.353 ms  52.580 ms  52.547 ms
11  64.230.79.93  53.217 ms  53.226 ms  53.139 ms
12  64.230.123.251  52.911 ms  52.873 ms  52.872 ms
13  204.244.0.10  53.064 ms  52.847 ms  52.846 ms
```

> Again, note that the 50ms on the first hop is on the PEERING-required OpenVPN tunnel between the server in Texas and the Vultr VM in Seattle.

Pulling the reverse traceroute shows that the reverse path goes straight to Seattle:

```bash
$ for i in $(seq 0 4) ; do
    ./rtc.py fetch --label tma_round1_245_$i \
        | jq -c '.revtrs[] | select( .dst == "204.244.0.10" )'
  done > out.json
$ ./rtc.py print --file out.json
Reverse Traceroute from remote 204.244.0.10 to VP 184.164.245.1
  204.244.0.10 5071 (WESTEL-1) CA DST_REV_SEGMENT
  204.244.0.110 5071 (WESTEL-1) CA SPOOF_RR_REV_SEGMENT
  64.125.0.185 6461 (ZAYO-6461) US SPOOF_RR_REV_SEGMENT
  64.125.0.216 6461 (ZAYO-6461) US SPOOF_RR_REV_SEGMENT
  63.223.47.65 3491 (BTN-ASN) US SPOOF_RR_REV_SEGMENT
  205.177.32.97 3491 (BTN-ASN) US SPOOF_RR_REV_SEGMENT
  63.223.47.122 3491 (BTN-ASN) US TR_TO_SRC_REV_SEGMENT
  205.177.32.98 3491 (BTN-ASN) US TR_TO_SRC_REV_SEGMENT
  69.195.152.146 19969 (JOESDATACENTER) US TR_TO_SRC_REV_SEGMENT
  184.164.245.1 47065 (PEERING-RESEARCH-TESTBED-USC-UFMG-AS47065) US TR_TO_SRC_REV_SEGMENT
```

This brute-force approach, however, might lead to poor performance in Asia and Oceania, as we would not have a nearby PoP.  Alternatively, we can try traffic engineering techniques to induce better routing decision from the involved ASes.

One try is to set BGP communities to tune BGP's decision process in remote ASNs.  AS9498 does not seem to have publicly documented BGP communities that we could use.  AS6461 does have [publicly documented BGP communities](https://onestep.net/communities/as6461/), but setting 6461:5060 to lower AS6461's preference for routes from Delhi does not work.  Reasons include intermediate ASes removing the community from the announcement or we not being a direct customer.

Another hack we could try is to poison AS6461, artificially adding it to the announcement's AS-path to trigger BGP loop prevention and cause AS6461 to ignore the route exported from Delhi.  Unfortunately, poisoning Tier-1 ASes usually does not work as most ASes filter routes from customers that traverse Tier-1s as this is usually a sign of a route leak.

Finally, we can try using Vultr's [traffic engineering communities](https://github.com/vultr/vultr-docs/tree/main/faq/as20473-bgp-customer-guide#action-communities) to ask Vultr to *not* export our prefix to AS9498 in Delhi.  This will restrict route propagation for ASes in Asia, and is a trade-off between worsening performance for ASes who would be bette- off using AS9498 vs improving performance for networks that are incorrectly choosing the route to AS9498.  This solution could be a temporary fix until operators are contacted to search for a more definitive solution.

> We add files with lists of Vultr peers per site in the `resources/vultr-peers` folder.  AS numbers are in the first columns, and providers are marked with `100` on the second column.  To not export to a given provider, the community `64600:providerASN` can be used.

We make an announcement using prefix `184.164.254.0/24` containing the community `64600:9498`.  We observe the same performance improvement for the Canadian ISP as above, while still maintaining a presence in Asia by announcing to peers and the second Vultr provider in Delhi.  A forward traceroute shows low latency, and a reverse traceroute indicates the path goes straight to Seattle:

```bash
Reverse Traceroute from remote 204.244.0.10 to VP 184.164.254.1
  204.244.0.10 5071 (WESTEL-1) CA DST_REV_SEGMENT
  204.244.0.110 5071 (WESTEL-1) CA SPOOF_RR_REV_SEGMENT
  64.125.0.185 6461 (ZAYO-6461) US SPOOF_RR_REV_SEGMENT
  64.125.0.216 6461 (ZAYO-6461) US SPOOF_RR_REV_SEGMENT
  63.223.47.65 3491 (BTN-ASN) US SPOOF_RR_REV_SEGMENT
  205.177.32.97 3491 (BTN-ASN) US SPOOF_RR_REV_SEGMENT
  63.223.47.126 3491 (BTN-ASN) US TR_TO_SRC_REV_SEGMENT
  205.177.32.98 3491 (BTN-ASN) US TR_TO_SRC_REV_SEGMENT
  69.195.152.146 19969 (JOESDATACENTER) US TR_TO_SRC_REV_SEGMENT
  184.164.254.1 47065 (PEERING-RESEARCH-TESTBED-USC-UFMG-AS47065) US TR_TO_SRC_REV_SEGMENT
```

Again, querying AS6461's looking glass confirms it is using a more direct route to the prefix:

```text
A V Destination        P Prf   Metric 1   Metric 2  Next hop        AS path
* ? 184.164.254.0/24   B 170        100 4294967294                  3356 20473 47065 I
```

## Verify if the Issue Persists

The measurements above were run Saturday, June 24th 2023.  We can re-run the measurements now to check if the issue persists or if routes have changed since.

## Try it Yourself

Below are some other similar cases of bad routing arising from anycast:

* A German ISP operating IP 37.251.238.254 is experiencing a similar problem to that of the Canadian ISP: Performance is very poor toward services hosted in the anycast `184.164.240.0/24` prefix.

* An ISP in the Philippines operating IP 210.213.131.117 is experiencing high delays to services running on the anycast `184.164.240.9/24` prefix.
