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
        if '%' in self.value:
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
