#ifndef CLICK_NETWORKHEADERFIELDSREWRITE_HH
#define CLICK_NETWORKHEADERFIELDSREWRITE_HH
#include <click/element.hh>
#include <click/etheraddress.hh>
CLICK_DECLS

/*
 * =c
 * NetworkHeaderFieldsRewrite([ETHERNET, IPV4, IPV6, TCP, UDP])
 * =s basicmod
 * Rewrites p
 *
 * =d
 *
 * Incoming packets are Ethernet. The source and address of requested layers is swapped. 
 * Keyword arguments are:
=over 8

=item ETHERNET

Boolean. If true ethernet layer will swap direction.

=item IPV4

Boolean. If true IPv4 layer will swap direction.

=item IPV6

Boolean. If true IPv6 layer will swap direction.

=item TCP

Boolean. If true TCP layer will swap direction.

=item UDP

Boolean. If true UDP layer will swap direction.

=back
=e
 * */

class NetworkHeaderFieldsRewrite : public Element { 
public:

  NetworkHeaderFieldsRewrite() CLICK_COLD;
  ~NetworkHeaderFieldsRewrite() CLICK_COLD;

  const char *class_name() const	{ return "NetworkHeaderFieldsRewrite"; }
  const char *port_count() const	{ return PORTS_1_1; }

  int configure(Vector<String> &conf, ErrorHandler *errh) CLICK_COLD;
  bool can_live_reconfigure() const { return true; }
  void add_handlers() CLICK_COLD;
  Packet *simple_action(Packet *);

private:
  bool _eth_dst_set, _eth_src_set, _eth_type_set;
  bool _ipv4_proto_set, _ipv4_src_set, _ipv4_dst_set, _ipv4_dscp_set, _ipv4_ttl_set, _ipv4_ecn_set;
  bool _tcp_src_set, _tcp_dst_set, _udp_src_set, _udp_dst_set;
  bool _any_ipv4_set, _any_set, _any_tcp_set, _any_udp_set;
  EtherAddress _eth_dst, _eth_src;
  uint16_t _eth_type, _udp_src, _udp_dst, _tcp_src, _tcp_dst;
  uint8_t _ipv4_proto, _ipv4_ttl, _ipv4_dscp, _ipv4_ecn;
  IPAddress _ipv4_src, _ipv4_dst;

  uint16_t _ethertype_8021q;
  uint16_t _ethertype_ip;
  uint16_t _ethertype_ip6;
};

CLICK_ENDDECLS
#endif // CLICK_NETWORKHEADERFIELDSREWRITE_HH
