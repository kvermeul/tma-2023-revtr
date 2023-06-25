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

We see that the path from the ISP back to us goes to Zayo, a major Tier-1 network.  Looking at their Looking Glass system provides verifies our diagnosis, as Zayo is choosing a route exported by AS9498:

```text
A V Destination        P Prf   Metric 1   Metric 2  Next hop        AS path
* ? 184.164.240.0/24   B 170        200                             9498 20473 47065 I
  unverified                                       >64.125.29.144
                                                    64.125.26.164
```

## Fixing the Issue

## Verify if the Issue Persists

The measurements above were run Saturday, June 24th 2023.  We can re-run the measurements now to check if the issue persists or if routes have changed since.

## Try it Yourself

Below are some other similar cases of bad routing arising from anycast:

* **TODO** Additional examples
