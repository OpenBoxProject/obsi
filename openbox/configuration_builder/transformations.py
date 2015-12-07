#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################

import json


def to_int(value, **kwargs):
    if value is None:
        return 0
    return int(value)


def to_float(value, **kwargs):
    return float(value)


def identity(value, **kwargs):
    return value


def to_push_message_content(name, severity, message, **kwargs):
    content = dict(origin_block=name, severity=severity, message=message, packet="%s")

    # we need to double encode for click's use
    return json.dumps(json.dumps(content))


def to_lower(value, **kwargs):
    return str(value).lower()


def _to_quoted_string(s):
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s
    return '"%s"' % str(s)


def to_quoted(value, **kwargs):
    if isinstance(value, (list, tuple)):
        return [_to_quoted_string(elem) for elem in value]
    elif isinstance(value, (str, unicode)):
        return _to_quoted_string(value)


def to_vlan_tci(vid, dei, pcp, **kwargs):
    vid = int(vid)
    dei = to_int(dei)
    pcp = to_int(pcp)
    return (vid | (dei << 12) | (pcp << 13)) & 0xffff

