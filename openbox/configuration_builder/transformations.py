import json


def to_int(value, num=None):
    return int(value)


def to_float(value, num=None):
    return float(value)


def identity(value, num=None):
    return value


def to_push_message_content(name, severity, message, num=None):
    content = dict(origin_block=name, severity=severity, message=message, packet="%s")

    # we need to double encode for click's use
    return json.dumps(json.dumps(content))
