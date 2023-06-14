from utils.network_utils import dnets_of, ipItoStr, ipv4_index_of
from processing.revtr_hop_types import RevtrHopType

def remove_as_loop_from_revtr_path(replies, ip2asn):
   replies_filtered = replies
   hop_types = set(r[1] for r in replies)
   if RevtrHopType.TR_TO_SRC_REV_SEGMENT_BETWEEN in hop_types:
      first_hop_tr_between_index = next(i for i, r in enumerate(replies)
                                        if RevtrHopType(r[1]) == RevtrHopType.TR_TO_SRC_REV_SEGMENT_BETWEEN)

      first_hop_before_tr_between_index = first_hop_tr_between_index - 1
      first_hop_before_tr_between_asn, _ = ip2asn.lookup(ipItoStr(replies[first_hop_before_tr_between_index][0]))
      if first_hop_before_tr_between_asn is not None:
         try:
            next_hop_no_loop_index = next(i for i, r in enumerate(replies)
                                          if ip2asn.lookup(ipItoStr(r[0]))[0] == first_hop_before_tr_between_asn and i > first_hop_before_tr_between_index)
         except StopIteration as e:
            # There is no loop here
            return replies
            # next_hop_no_loop_index = first_hop_tr_between_index
         replies_filtered = replies[:first_hop_before_tr_between_index + 1]
         replies_filtered.extend(replies[next_hop_no_loop_index:])

   return replies_filtered


def contains_interdomain_assume_symmetry_impl(reverse_hops, ip2asn, ip2asn_cache=None):
   for i, (ip, hop_type, _, _, _) in enumerate(reverse_hops[:-1]):
      next_ip, next_hop_type, _, _, _ = reverse_hops[i + 1]
      if RevtrHopType(next_hop_type) != RevtrHopType.DST_SYM_REV_SEGMENT:
         continue
      if ip2asn_cache is not None:
         if ip in ip2asn_cache:
            asn = ip2asn_cache[ip]
         else:
            asn = dnets_of(ip, ip2asn, ip_representation="uint32").asn
            ip2asn_cache[ip] = asn
         if next_ip in ip2asn_cache:
            next_asn = ip2asn_cache[next_ip]
         else:
            next_asn = dnets_of(next_ip, ip2asn, ip_representation="uint32").asn
            ip2asn_cache[next_ip] = asn
      else:
         asn = dnets_of(ip, ip2asn, ip_representation="uint32").asn
         next_asn = dnets_of(next_ip, ip2asn, ip_representation="uint32").asn
      if asn != next_asn:
         return i, True
   return 0, False


def contains_interdomain_assume_symmetry(revtr, ip2asn):

   # `order`, measurement_id, rtt

   status = revtr["status"]
   stop_reason = revtr["stopReason"]
   src = revtr["src"]
   dst = revtr["dst"]
   if stop_reason == "FAILED":
      print(f"REVTR 2.0 was unable to measure the reverse path back from {dst} to {src}")
      return

   path = revtr["path"]
   path_ = [(ipv4_index_of(h["hop"]), RevtrHopType[h["type"]], None, None, None)for h in path]
   _, is_assume_interdomain_symmetry = contains_interdomain_assume_symmetry_impl(path_, ip2asn)
   return is_assume_interdomain_symmetry






