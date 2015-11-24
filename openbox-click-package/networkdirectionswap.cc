#include <click/config.h>
#include "networkdirectionswap.hh"
#include <click/args.hh>
#include <clicknet/ether.h>
#include <clicknet/ip.h>
#include <clicknet/ip6.h>
#include <clicknet/udp.h>
#include <clicknet/tcp.h>
CLICK_DECLS

NetworkDirectionSwap::NetworkDirectionSwap() :
_ethernet(false),
_ipv4(false),
_ipv6(false),
_tcp(false),
_udp(false), 
_swap_any(false),
_ethertype_8021q(htons(ETHERTYPE_8021Q)), 
_ethertype_ip(htons(ETHERTYPE_IP)), 
_ethertype_ip6(htons(ETHERTYPE_IP6))
{
}

NetworkDirectionSwap::~NetworkDirectionSwap()
{
}

int
NetworkDirectionSwap::configure(Vector<String> &conf, ErrorHandler *errh)
{
    if (Args(conf, this, errh)
    .read("ETHERNET", _ethernet)
    .read("IPV4", _ipv4)
    .read("IPV6", _ipv6)
    .read("TCP", _tcp)
    .read("UDP", _udp)
    .complete() < 0) {
    	return -1;
    } 
    _swap_any = _ethernet || _ipv4 || _ipv6 || _tcp || _udp;
    return 0;
}

Packet *
NetworkDirectionSwap::simple_action(Packet *p)
{
	if (!_swap_any) {
		return p;
	}

	if (WritablePacket *q = p->uniqueify()) {
		click_ether_vlan *ethh = reinterpret_cast<click_ether_vlan *>(q->data());
		if (_ethernet) {
			uint8_t tmpa[6];
			memcpy(tmpa, ethh->ether_dhost, 6);
			memcpy(ethh->ether_dhost, ethh->ether_shost, 6);
			memcpy(ethh->ether_shost, tmpa, 6);
		}
		bool ipv4_layer_present = ((ethh->ether_vlan_proto == _ethertype_ip) 
			|| ((ethh->ether_vlan_proto == _ethertype_8021q && 
					ethh->ether_vlan_encap_proto == _ethertype_ip)));
		bool ipv6_layer_present = ((ethh->ether_vlan_proto == _ethertype_ip6) || 
				((ethh->ether_vlan_proto == _ethertype_8021q && 
					ethh->ether_vlan_encap_proto == _ethertype_ip6))); 
		if (ipv4_layer_present && q->has_network_header()) {
			click_ip *iph = q->ip_header();
			if (_ipv4) {
				struct in_addr tmpa = iph->ip_src;
	  			iph->ip_src = iph->ip_dst;
	  			iph->ip_dst = tmpa;
			}
			if (_tcp && iph->ip_p == IP_PROTO_TCP && IP_FIRSTFRAG(iph) && (int)q->length() >= q->transport_header_offset() + 8) {
				click_tcp *tcph = q->tcp_header();
				uint16_t tmpp = tcph->th_sport;
				tcph->th_sport = tcph->th_dport;
				tcph->th_dport = tmpp;
			}
			if (_udp && iph->ip_p == IP_PROTO_UDP && IP_FIRSTFRAG(iph) && (int)q->length() >= q->transport_header_offset() + 8) {
				click_udp *udph = q->udp_header();
			    uint16_t tmpp = udph->uh_sport;
			    udph->uh_sport = udph->uh_dport;
			    udph->uh_dport = tmpp;
	  		}
		} else if (ipv6_layer_present && q->has_network_header()) {
			click_ip6 *iph = q->ip6_header();
			if (_ipv6) {
				struct in6_addr tmpa = iph->ip6_src;
	  			iph->ip6_src = iph->ip6_dst;
	  			iph->ip6_dst = tmpa;
			}
			if (_tcp && iph->ip6_nxt == IP_PROTO_TCP && (int)q->length() >= q->transport_header_offset() + 8) {
				click_tcp *tcph = q->tcp_header();
				uint16_t tmpp = tcph->th_sport;
				tcph->th_sport = tcph->th_dport;
				tcph->th_dport = tmpp;
  			}
  			if (_udp && iph->ip6_nxt == IP_PROTO_UDP  && (int)q->length() >= q->transport_header_offset() + 8) {
  				click_udp *udph = q->udp_header();
			    uint16_t tmpp = udph->uh_sport;
			    udph->uh_sport = udph->uh_dport;
			    udph->uh_dport = tmpp;
		  	}
		}
		return q;
	} else {
		return 0;
	}
	
}

CLICK_ENDDECLS
EXPORT_ELEMENT(NetworkDirectionSwap)
