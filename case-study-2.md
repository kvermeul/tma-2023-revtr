# Case Study 2 - Load Distribution Across PoPs

In this case study we again consider a service hosted on Vultr using prefix `184.164.240.0/24`.  We anycast the prefix `184.164.240.0/24` from six Vultr PoPs in an attempt to improve performance globally: Amsterdam, Tokyo, Seattle, São Paulo, Delhi, and Miami.

An important concept when dealing with anycast announcements it the *catchment* of each PoP, defined as the set of remote destinations that are routed back to each PoP.  After we make the anycast announcement and measure the catchments, we observe that remote endpoints are not distributed as we would like across our PoPs.

> In practice, a content provider or CDN considers network (latency and bandwidth) and compute (CPUs, memory, and storage) capacity constraints when configuring their traffic engineering systems.  Content providers and CDNs can also employ DNS-based redirection on unicast prefixes (or not so broadly anycast prefixes) to steer clients toward the intended PoPs.

As we lack empirical information to inform a realistic target load distribution, we can set any arbitrary goal for load distribution for the purposes of this tutorial.  In the examples below, we will strive to evenly balance load across different PoPs.

## Measuring Catchments

We have prepared scripts to measure catchments using pings inside [`client/utils/measure-catchments`][peering-measure-catchments].  The [README] details how to use the scripts.  In this tutorial, we should use the source IP ending in `.99` inside the prefix we want to measure the catchment of.

First we need to make sure to configure an egress for the `.99` IP:

```bash
~/tutorial/scripts$ ./set-egress.sh -i 184.164.240.99 -e amsterdam
```

> Here, we're using `184.164.240.0/24` as that is the anycast prefix.  You may need to change it to whatever prefix you're interested in.  When measuring catchments, the egress mux (`amsterdam` in this case) is not important: any egress will do just fine.  What we really care about is the interface where the ICMP echo replies are received.

Second, we need to start `tcpdump` instances to monitor where the ICMP echo responses will be received:

```bash
~client/utils/measure-catchments$ ./launch-tcpdump.sh -i 184.164.240.99 -o dumps_240
```

Third, we can launch [Verfploeter][verfploeter] to measure the catchments toward a set of around 15300 select destinations covering prefixes hosting many end users:

```bash
~client/utils/measure-catchments$ ./launch-pinger.sh \
    -i 184.164.240.99 -I 240 \
    -t ~/tutorial/resources/15300-top-rsd-ingresses.txt -I 240
```

After the catchment measurement finishes, let's kill the `tcpdump` instances launched in step 2 to free up resources:

```bash
~client/utils/measure-catchments$ ./kill-tcpdump.sh -f dumps_240/pids.txt
```

With the measurements collected, we can now get an approximation of the catchment sizes.  The script shows the PoP, number of received ICMP replies, and relative fraction of ICMP replies:

```bash
~client/utils/measure-catchments$ ./approximate-catchments.sh -I 240 -d dumps_240
dumps_240/seattle.tap20.pcap 894 10%
dumps_240/amsterdam.tap1.pcap 1626 19%
dumps_240/tokyo.tap26.pcap 734 8%
dumps_240/miami.tap14.pcap 1488 18%
dumps_240/delhi.tap6.pcap 1891 23%
dumps_240/saopaulo.tap19.pcap 1582 19%
```

## Identifying Upstreams Attracting Traffic

The catchment size approximations above indicate that load may not match our expectations.  In particular, Sao Paulo is catching 19% of the destinations while Delhi is catching 23% of the destinations.  We may want to reduce these fractions, for example due to capacity constraints at these sides.

In an attempt to reduce a PoP's catchment, we can attempt to constrain the propagation of the BGP announcement we make to it.  Unfortunately, catchment sizes are coarse grained and do not provide enough information for targeted traffic engineering.  Without additional information we could, for example, stop announcing from a PoP (so it attracts no traffic), which is likely undesirable.  We could also make the BGP AS-path of announcements from a PoP  artificially longer to make its routes less preferable than (shorter) routes to other PoPs, a technique known as BGP prepending.

Reverse Traceroute allows us to identify Vultr which providers destinations are using to reach the service running on `184.164.240.0/24`.  We can then use more fine-grained traffic engineering solutions to achieve our goals.  In particular, we can add BGP communities to our announcements to ask Vultr to manipulate our announcements.  In particular, Vultr provides the following relevant communities:

| Description                     | Community      |
|---------------------------------|----------------|
| Do not announce to specific AS  | 64600:peer-as  |
| Prepend 1x to specific AS       | 64601:peer-as  |
| Prepend 2x to specific AS       | 64602:peer-as  |
| Prepend 3x to specific AS       | 64603:peer-as  |

> A BGP community is just a tag we can add to a BGP announcement.  The semantics are defined by the network operator.  The documentation for Vultr BGP communities is in [this document][vultr-bgp-communities].

> The more times we prepend to an AS-path, the longer and less preferable it becomes.  So an announcement prepending 3x results in a less preferable path than an announcement prepending 2x.

We can check the network immediately before the packet gets to our server (IP `69.195.152.146` in the reverse traceroutes) to approximate the fraction of destinations routing toward each Vultr provider.  We can then make the announcement to specific providers less preferable using the communities above.  In the example below, we see that the Canadian ISP is routing to Bharti Airtel (AS9498):

```bash
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

> Unfortunately, the PEERING routers are not appearing on the reverse traceroute measurements (they would normally appear between `122.184.140.154` and `69.195.152.146` in the example above).  This complicates identifying which Vultr PoP a specific traceroute is traversing.  In the example above, we can guess that the traceroute traverses Delhi because of the high latency towards the destination (see Case Study 1).

The `provider-catchments.py` script shows, for each identified Vultr upstream, its AS number, the number of reverse traceroutes through it, and the corresponding fraction of reverse traceroutes:

```bash
~/tutorial/api-examples$ ./provider-catchments.py ../data/tma_round1_240*
...
201011 16 0.737% (CORE-BACKBONE)
4230 23 1.059% (CLARO)
7922 25 1.151% (COMCAST-7922)
6453 39 1.796% (AS6453)
11537 43 1.980% (INTERNET2-RESEARCH-EDU)
140627 50 2.302% (ONEQODEASSETS-AS-AP)
174 52 2.394% (COGENT-174)
6057 76 3.499% (Administracion Nacional de Telecomunicaciones)
3491 108 4.972% (BTN-ASN)
31133 122 5.617% (MF-MGSM-AS)
1299 172 7.919% (TWELVE99 Arelion, fka Telia Carrier)
3356 297 13.674% (LEVEL3)
2914 367 16.897% (NTT-LTD-2914)
9498 619 28.499% (BBIL-AP)
```

With the knowledge of which providers are carrying the most traffic, we can use Vultr traffic engineering communities from specific muxes to steer traffic away from specific PoPs.  To do this, we need to check the providers for each Vultr PoP, which we have made available under `~/tutorial/resources/vultr-peers`.  The first column in each file shows a Vultr peer AS, and the second number its class.  A number of 100 in the second column indicates that the AS is a transit provider, which we can then use with Vultr's BGP communities to manipulate announcement propagation.  (Documentation for other peer types is in Vultr [BGP community guide][vultr-bgp-communities].)

## Attempting to Balance Traffic

Given the results above, a first attempt to balance load is to prepend to Cogent (AS174) at São Paulo and to Bharti Airtel (AS9498) at Delhi.

[peering-measure-catchments]: TODO
[vultr-bgp-communities]: https://github.com/vultr/vultr-docs/tree/main/faq/as20473-bgp-customer-guide#action-communities
