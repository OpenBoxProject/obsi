#include <click/config.h>
#include "automarkipheader.hh"
#include <click/args.hh>
#include <clicknet/ip.h>
#include <clicknet/ether.h>
CLICK_DECLS

AutoMarkIPHeader::AutoMarkIPHeader() 
: _ethertype_8021q(htons(ETHERTYPE_8021Q)), _ethertype_ip(htons(ETHERTYPE_IP))
{
}

AutoMarkIPHeader::~AutoMarkIPHeader()
{
}


Packet *
AutoMarkIPHeader::simple_action(Packet *p)
{
	assert(!p->mac_header() || p->mac_header() == p->data());
	const click_ether_vlan *vlan = reinterpret_cast<const click_ether_vlan *>(p->data());
	if (vlan->ether_vlan_proto == _ethertype_8021q) {
		if (vlan->ether_vlan_encap_proto == _ethertype_ip) {
			const click_ip *ip = reinterpret_cast<const click_ip *>(p->data() + sizeof(click_ether_vlan));
  			p->set_ip_header(ip, ip->ip_hl << 2);
		}	
	} else if (vlan->ether_vlan_proto == _ethertype_ip) {
		const click_ip *ip = reinterpret_cast<const click_ip *>(p->data() + sizeof(click_ether));
  		p->set_ip_header(ip, ip->ip_hl << 2);
  	}
	return p;
}

CLICK_ENDDECLS
EXPORT_ELEMENT(AutoMarkIPHeader)
ELEMENT_MT_SAFE(AutoMarkIPHeader)
