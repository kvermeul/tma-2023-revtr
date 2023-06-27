# Case Study 2 - Load Distribution Across PoPs

In this case study we again consider a service hosted on Vultr using prefix `184.164.240.0/24`.  We anycast the prefix `184.164.240.0/24` from six Vultr PoPs in an attempt to improve performance globally: Amsterdam, Tokyo, Seattle, São Paulo, Delhi, and Miami.

An important concept when dealing with anycast announcements is the *catchment* of each PoP, defined as the set of remote destinations that are routed back to each PoP.  After we make the anycast announcement and measure the catchments, we observe that remote endpoints are not distributed as we would like across our PoPs.

> In practice, a content provider or CDN considers network (latency and bandwidth) and compute (CPUs, memory, and storage) capacity constraints when configuring their traffic engineering systems.  Content providers and CDNs can also employ DNS-based redirection on unicast prefixes (or not so broadly anycast prefixes) to steer clients toward the intended PoPs.

As we lack empirical information to inform a realistic target load distribution, we can set any arbitrary goal for load distribution for the purposes of this tutorial.  In the examples below, we will strive to evenly balance load across different PoPs.

## Measuring Catchments

We have prepared scripts to measure catchments using pings inside [`client/utils/measure-catchments`][peering-measure-catchments].  In this tutorial, we should use the source IP ending in `.99` inside the prefix we want to measure the catchment of.

First we need to make sure to configure an egress for the `.99` IP:

```bash
~/tutorial/scripts$ ./set-egress.sh -i 184.164.240.99 -e amsterdam
```

> Here, we're using `184.164.240.0/24` as that is the anycast prefix.  You may need to change it to whatever prefix you're interested in.  When measuring catchments, the egress PoP (`amsterdam` in this case) is not important: any egress will do just fine.  What we really care about is the interface where the ICMP echo replies are received.

Second, we need to start `tcpdump` instances to monitor where the ICMP echo responses will be received:

```bash
~client/utils/measure-catchments$ ./launch-tcpdump.sh -i 184.164.240.99 -o dumps_240
```

Third, we can launch [Verfploeter][verfploeter] to measure the catchments toward a set of around 15300 select destinations covering prefixes hosting many end users:

[verfploeter]: https://ant.isi.edu/software/verfploeter/

```bash
~/client/utils/measure-catchments$ ./launch-pinger.sh \
    -i 184.164.240.99 -I 240 \
    -t ~/tutorial/resources/15300-top-rsd-ingresses.txt -I 240
```

After the catchment measurement finishes, let's kill the `tcpdump` instances launched in step 2 to free up resources:

```bash
~/client/utils/measure-catchments$ ./kill-tcpdump.sh -f dumps_240/pids.txt
```

With the measurements collected, we can now get an approximation of the catchment sizes.  The script shows the PoP, number of received ICMP replies, and relative fraction of ICMP replies:

```bash
~/client/utils/measure-catchments$ ./approximate-catchments.sh -I 240 -d dumps_240
dumps_240/seattle.tap20.pcap 894 10%
dumps_240/amsterdam.tap1.pcap 1626 19%
dumps_240/tokyo.tap26.pcap 734 8%
dumps_240/miami.tap14.pcap 1488 18%
dumps_240/delhi.tap6.pcap 1891 23%
dumps_240/saopaulo.tap19.pcap 1582 19%
```

## Identifying Upstreams Attracting Traffic

The catchment size approximations above indicate that load may not match our expectations.  In particular, São Paulo is catching 19% of the destinations while Delhi is catching 23% of the destinations.  We may want to reduce these fractions, for example due to capacity constraints at these sides.

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

> Please note that the provider catchments (directly above) are not directly comparable to the PoP catchments (further up).  Reasons include:
>
> An AS may provide transit to Vultr on multiple PoPs.  A provider's catchment above add up routes toward any Vultr PoP.
>
> The PoP catchments are measured with pings, which has broader coverage.  The provider catchments, however, are estimated with the reverse traceroutes, which may be biased toward networks with better coverage.

With the knowledge of which providers are carrying the most traffic, we can use Vultr traffic engineering communities from specific muxes to steer traffic away from specific PoPs.  To do this, we need to check the providers for each Vultr PoP, which we have made available under `~/tutorial/resources/vultr-peers`.  The first column in each file shows a Vultr peer AS, and the second number its class.  A number of 100 in the second column indicates that the AS is a transit provider, which we can then use with Vultr's BGP communities to manipulate announcement propagation.  (Documentation for other peer types is in Vultr [BGP community guide][vultr-bgp-communities].)

## Attempting to Balance Traffic

Given the results above, a first attempt to balance load is to prepend to Cogent (AS174) at São Paulo and to Bharti Airtel (AS9498) at Delhi.  We can do this by attaching community `64603:174` to the announcement from São Paulo and  community `64603:9498` to the announcement from Delhi.  We make this change to the announcement for `184.164.250.0/24`.  After changing the announcement, we need to perform the following four steps before issuing new reverse traceroute measurements:

1. Wait about 5 minutes for BGP convergence
2. Reset the Reverse Traceroute atlas toward the vantage point by running `./rtc.py atlas --reset`
3. Trigger rebuilding of the atlas by running `./rtc.py atlas --rebuild`
4. Wait for the atlas to be rebuilt (takes about 40 minutes)

Prepending to Cogent and Bharti Airtel does shift some traffic away from São Paulo and Delhi, leading to a somewhat more balanced load distribution.  Here is what the catchments look like:

```bash
# Prefix 250: Prepend to Cogent at São Paulo and Bharti Airtel at Delhi
~/client/utils/measure-catchments$ ./approximate-catchments.sh -d dumps_round2_250 -I 250
dumps_round2_250/saopaulo.tap19.pcap 2670 16%
dumps_round2_250/delhi.tap6.pcap 3201 19%
dumps_round2_250/tokyo.tap26.pcap 1594 9%
dumps_round2_250/miami.tap14.pcap 3338 20%
dumps_round2_250/amsterdam.tap1.pcap 3520 21%
dumps_round2_250/seattle.tap20.pcap 1985 12%
```

Again, issuing reverse traceroutes to the `184.164.250.0/24` prefix provides some insight on what may be going on.  Here is a look at the provider catchments:

```bash
# Prefix 250: Prepend to Cogent at São Paulo and Bharti Airtel at Delhi
~/tutorial/api-examples$ ./provider-catchments.py ../data/tma_round2_250_*
...
11537 14 0.669% (INTERNET2-RESEARCH-EDU)
64049 21 1.003% (RJIPL-SG)
201011 21 1.003% (CORE-BACKBONE)
174 26 1.242% (COGENT-174)
3257 29 1.386% (GTT-BACKBONE)
7922 31 1.481% (COMCAST-7922)
6453 41 1.959% (AS6453)
6939 62 2.962% (HURRICANE)
6057 87 4.157% (Administracion Nacional de Telecomunicaciones)
1299 129 6.163% (TWELVE99 Arelion, fka Telia Carrier)
3491 135 6.450% (BTN-ASN)
2914 223 10.655% (NTT-LTD-2914)
3356 486 23.220% (LEVEL3)
9498 512 24.462% (BBIL-AP)
```

We see that Cogent (AS174) is less prevalent than before, likely because its (longer) route to São Paulo attracts less traffic.  We observe, however, that
Bharti Airtel (AS9498) remains prevalent even after the prepending.  This may be because Bharti Airtel may be customers of other Tier-1 networks, which would choose routes from Bharti Airtel regardless of AS-path length.  (Remember that BGP's first criterion for choosing routes is LocalPref, usually configured such that routes from customers are preferred over routes from peers, regardless of AS-path length.)  Again, we can verify this is the case by inspecting some reverse traceroutes.  Here are examples of two Tier-1 networks choosing routes to Bharti Airtel after we prepend the AS-path:

```text
Reverse Traceroute from remote 195.66.225.104 to VP 184.164.250.1
  195.66.225.104 3491 (BTN-ASN) US DST_REV_SEGMENT
  64.125.0.161 6461 (ZAYO-6461) US SPOOF_RR_REV_SEGMENT
  10.187.33.9 None (None) None TR_TO_SRC_REV_SEGMENT_BETWEEN
  94.31.41.45 6461 (ZAYO-6461) US TR_TO_SRC_REV_SEGMENT_BETWEEN
  64.125.29.85 6461 (ZAYO-6461) US TR_TO_SRC_REV_SEGMENT_BETWEEN
  64.125.27.15 6461 (ZAYO-6461) US TR_TO_SRC_REV_SEGMENT_BETWEEN
  94.31.40.5 6461 (ZAYO-6461) US TR_TO_SRC_REV_SEGMENT_BETWEEN
  182.79.141.130 None (None) None TR_TO_SRC_REV_SEGMENT_BETWEEN
  122.184.140.154 9498 (BBIL-AP) IN TR_TO_SRC_REV_SEGMENT_BETWEEN
  69.195.152.146 19969 (JOESDATACENTER) US TR_TO_SRC_REV_SEGMENT_BETWEEN
  184.164.250.1 47065 (PEERING-RESEARCH-TESTBED-USC-UFMG-AS47065) US TR_TO_SRC_REV_SEGMENT_BETWEEN
Reverse Traceroute from remote 187.251.2.4 to VP 184.164.250.1
  187.251.2.4 32098 (TRANSTELCO-INC) US DST_REV_SEGMENT
  201.174.255.33 32098 (TRANSTELCO-INC) US SPOOF_RR_REV_SEGMENT
  201.174.250.169 32098 (TRANSTELCO-INC) US TR_TO_SRC_REV_SEGMENT
  201.174.255.32 32098 (TRANSTELCO-INC) US TR_TO_SRC_REV_SEGMENT
  206.223.123.11 None (None) None TR_TO_SRC_REV_SEGMENT
  202.84.253.85 4637 (ASN-TELSTRA-GLOBAL) HK TR_TO_SRC_REV_SEGMENT
  202.84.224.190 4637 (ASN-TELSTRA-GLOBAL) HK TR_TO_SRC_REV_SEGMENT
  210.57.30.87 4637 (ASN-TELSTRA-GLOBAL) HK TR_TO_SRC_REV_SEGMENT
  116.119.55.164 9498 (BBIL-AP) IN TR_TO_SRC_REV_SEGMENT
  122.184.140.154 9498 (BBIL-AP) IN TR_TO_SRC_REV_SEGMENT
  69.195.152.146 19969 (JOESDATACENTER) US TR_TO_SRC_REV_SEGMENT
  184.164.250.1 47065 (PEERING-RESEARCH-TESTBED-USC-UFMG-AS47065) US TR_TO_SRC_REV_SEGMENT
```

In an attempt to shift even more traffic away from São Paulo and Delhi, we can prepend to *all* Vultr peers at these PoPs by attaching community `20473:6003` to their announcements.  We make this change to the announcement for `184.164.249.0/24`.  After performing the four steps above, we find that prepending to all peers is effective in shifting more traffic away from São Paulo, but not Delhi:

```bash
# Prefix 249: Prepend to all peers at São Paulo and Delhi
~/client/utils/measure-catchments$ ./approximate-catchments.sh -d dumps_round2_249 -I 249
dumps_round2_249/saopaulo.tap19.pcap 976 11%
dumps_round2_249/amsterdam.tap1.pcap 1867 22%
dumps_round2_249/tokyo.tap26.pcap 798 9%
dumps_round2_249/delhi.tap6.pcap 1612 19%
dumps_round2_249/miami.tap14.pcap 1979 24%
dumps_round2_249/seattle.tap20.pcap 989 12%
```

Prepending to all ASes at São Paulo (`184.164.249.0/24`) may be effective because the local IXP (IX.br/SP) has the highest number of members across all ISPs in the world, with more than 2000 members.  The global prepending would make all their routes less attractive, causing an impact at the longer tail.  Again, reverse traceroute provides confirmation that some routes reach São Paulo through IX.br/SP:

```text
Reverse Traceroute from remote 191.240.111.122 to VP 184.164.250.1
  191.240.111.122 28202 (Rede Brasileira de Comunicacao SA) BR DST_REV_SEGMENT
  191.53.4.228 28202 (Rede Brasileira de Comunicacao SA) BR SPOOF_RR_REV_SEGMENT
  172.25.16.1 None (None) None SPOOF_RR_REV_SEGMENT
  187.16.216.221 None (None) None SPOOF_RR_REV_SEGMENT
  216.238.96.7 20473 (AS-CHOOPA) US SPOOF_RR_REV_SEGMENT
  179.31.59.230 6057 (Administracion Nacional de Telecomunicaciones) UY TR_TO_SRC_REV_SEGMENT_BETWEEN
  179.31.62.131 6057 (Administracion Nacional de Telecomunicaciones) UY TR_TO_SRC_REV_SEGMENT_BETWEEN
  179.31.62.41 6057 (Administracion Nacional de Telecomunicaciones) UY TR_TO_SRC_REV_SEGMENT_BETWEEN
  179.31.62.50 6057 (Administracion Nacional de Telecomunicaciones) UY TR_TO_SRC_REV_SEGMENT_BETWEEN
  179.31.62.19 6057 (Administracion Nacional de Telecomunicaciones) UY TR_TO_SRC_REV_SEGMENT_BETWEEN
  187.16.221.67 None (None) None TR_TO_SRC_REV_SEGMENT_BETWEEN
  187.16.214.112 None (None) None TR_TO_SRC_REV_SEGMENT_BETWEEN
  69.195.152.146 19969 (JOESDATACENTER) US TR_TO_SRC_REV_SEGMENT_BETWEEN
  184.164.250.1 47065 (PEERING-RESEARCH-TESTBED-USC-UFMG-AS47065) US TR_TO_SRC_REV_SEGMENT_BETWEEN
```

Where we can identify that IX.br/SP was traversed as `187.16.208.0/20` is the [prefix assigned to members in its layer-2 fabric][peeringdb-ixbr-sp].

[peeringdb-ixbr-sp]: https://www.peeringdb.com/ix/171

Finally, prepending to all peers at Delhi is not effective.  One possible explanation is that Vultr may have few peers in Delhi, which leads to most traffic arriving at Delhi through Bharti Airtel, so prepending has limited effect as there are fewer competing routes converging on Delhi.

## Try it Yourself

You can decide on your own load distribution goals and decide which announcements would be useful towards achieving them.  After deploying your announcements, you can measure catchments and use Reverse Traceroute to investigate whether your announcements had the desired effect.  Multiple iterations may be needed until you find a reasonable configuration.

[peering-measure-catchments]: https://github.com/PEERINGTestbed/client/tree/master/utils/measure-catchments
[vultr-bgp-communities]: https://github.com/vultr/vultr-docs/tree/main/faq/as20473-bgp-customer-guide#action-communities
