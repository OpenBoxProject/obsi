#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################


class MatchField(object):
    def __init__(self, value):
        self.value = value

    def to_classifier_clause(self, offset=0):
        if self.value is None:
            return ''
        if isinstance(self.value, basestring) and '%' in self.value:
            value, mask = self.value.split('%')
            return '{offset}/{value}%{mask}'.format(offset=offset, value=self._to_output(value),
                                                    mask=self._to_output(mask))
        else:
            return '{offset}/{value}'.format(offset=offset, value=self._to_output(self.value))

    def _to_output(self, value):
        return value


class IntMatchField(MatchField):
    def __init__(self, value, bytes=1):
        super(IntMatchField, self).__init__(value)
        self._fmt = "%0{bytes}x".format(bytes=bytes * 2)

    def _to_output(self, value):
        return self._fmt % int(value)


class MacMatchField(MatchField):
    def _to_output(self, value):
        return value.replace(':', '').replace('-', '').lower()


class Ipv4MatchField(MatchField):
    def _to_output(self, value):
        return ''.join(chr(int(c)) for c in value.split('.')).encode('hex')


class BitsIntMatchField(IntMatchField):
    def __init__(self, value, bytes=1, bits=8, shift=0):
        super(BitsIntMatchField, self).__init__(value, bytes)
        self._mask = int('1' * bits, 2) << shift
        self._shift = shift

    def to_classifier_clause(self, offset=0):
        if self.value is None:
            return ''
        if '%' in self.value:
            value, mask = self.value.split('%')
            value = int(value) & int(mask)
            value <<= self._shift
            return '{offset}/{value}%{mask}'.format(offset=offset, value=self._to_output(value),
                                                    mask=self._to_output(self._mask))
        else:
            value = int(self.value) << self._shift
            return '{offset}/{value}%{mask}'.format(offset=offset, value=self._to_output(value),
                                                    mask=self._to_output(self._mask))


class HeaderMatch(dict):
    def to_patterns(self):
        patterns = []
        clauses = []
        if 'ETH_SRC' in self:
            clauses.append(MacMatchField(self['ETH_SRC']).to_classifier_clause(0))
        if 'ETH_DST' in self:
            clauses.append(MacMatchField(self['ETH_DST']).to_classifier_clause(6))
        if 'VLAN_VID' in self or 'VLAN_PCP' in self:
            clauses.append(IntMatchField(str(0x8100), 2).to_classifier_clause(12))
            if 'VLAN_VID' in self:
                clauses.append(BitsIntMatchField(self['VLAN_VID'], bytes=2, bits=12).to_classifier_clause(14))
            if 'VLAN_PCP' in self:
                clauses.append(BitsIntMatchField(self['VLAN_PCP'], bytes=1, bits=3, shift=5).to_classifier_clause(14))
            return self._compile_above_eth_type(clauses[:], 16)
        else:
            patterns.extend(self._compile_above_eth_type(clauses[:], 12))
            clauses_with_vlan = clauses[:]
            clauses_with_vlan.append(IntMatchField(str(0x8100), 2).to_classifier_clause(12))
            patterns.extend(self._compile_above_eth_type(clauses_with_vlan[:], 16))

        return patterns

    def _compile_above_eth_type(self, clauses, eth_type_offset):
        ip_offset = eth_type_offset + 2
        if 'ETH_TYPE' in self:
            clauses.append(IntMatchField(self['ETH_TYPE'], 2).to_classifier_clause(eth_type_offset))
        if 'IPV4_PROTO' in self:
            clauses.append(IntMatchField(self['IPV4_PROTO'], 1).to_classifier_clause(ip_offset + 9))
        if 'IPV4_SRC' in self:
            clauses.append(Ipv4MatchField(self['IPV4_SRC']).to_classifier_clause(ip_offset + 12))
        if 'IPV4_DST' in self:
            clauses.append(Ipv4MatchField(self['IPV4_DST']).to_classifier_clause(ip_offset + 16))

        # currently we don't support IP options
        if 'TCP_SRC' in self or 'TCP_DST' in self or 'UDP_SRC' in self or 'UDP_DST' in self:
            clauses.append(BitsIntMatchField(str(5), bytes=1, bits=4).to_classifier_clause(ip_offset))

        payload_offset = ip_offset + 20

        if 'TCP_SRC' in self:
            clauses.append(IntMatchField(self['TCP_SRC'], 2).to_classifier_clause(payload_offset))
        if 'TCP_DST' in self:
            clauses.append(IntMatchField(self['TCP_DST'], 2).to_classifier_clause(payload_offset + 2))
        if 'UDP_SRC' in self:
            clauses.append(IntMatchField(self['UDP_SRC'], 2).to_classifier_clause(payload_offset))
        if 'UDP_DST' in self:
            clauses.append(IntMatchField(self['UDP_DST'], 2).to_classifier_clause(payload_offset + 2))

        if clauses:
            return [' '.join(clauses)]
        else:
            return ['-']


class CompoundMatch(object):
    def __init__(self, header_match=None, payload_matches=None):
        self.header_match = HeaderMatch(header_match or {})
        self.payload_matches = payload_matches or {}

    @classmethod
    def from_config_dict(cls, config, match_number=0):
        header_matches = config['header_match']
        payload_patterns = config['payload_match']
        patterns = [payload_pattern['pattern'] for payload_pattern in payload_patterns]
        payload_matches = {match_number: patterns}
        return cls(header_matches, payload_matches)

    def is_combinable(self, other):
        if not isinstance(other, CompoundMatch):
            return False

        # if they have the same fields but with different values they cannot be combined
        for field in self.header_match:
            if field in other.header_match and self.header_match[field] != other.header_match[field]:
                return False

        return True

    def combine(self, other):
        assert isinstance(other, CompoundMatch)
        header_match = self.header_match.copy()
        header_match.update(other.header_match)
        payload_match = self.payload_matches.copy()
        payload_match.update(other.payload_matches)
        return CompoundMatch(header_match, payload_match)

    def __eq__(self, other):
        return self.header_match == other.header_match

    def __hash__(self):
        return hash(tuple(sorted(self.header_match.items())))

    def __repr__(self):
        return "%s(header_match=%s, payload_matches=%s)" % (self.__class__.__name__,
                                                            repr(self.header_match),
                                                            repr(self.payload_matches))


