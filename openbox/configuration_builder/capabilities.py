#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################

SUPPORTED_MATCH_FIELDS = ['ETH_SRC', 'ETH_DST', 'ETH_TYPE',
                          'VLAN_VID', 'VLAN_PCP',
                          'IPV4_PROTO', 'IPV4_SRC', 'IPV4_DST',
                          'TCP_SRC', 'TCP_DST',
                          'UDP_SRC', 'UDP_DST']
SUPPORTED_PROTOCOLS = ['ETH', 'VLAN', 'IPV4', 'TCP', 'UDP']