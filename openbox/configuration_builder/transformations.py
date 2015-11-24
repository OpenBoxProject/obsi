import json


def to_int(value, **kwargs):
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
