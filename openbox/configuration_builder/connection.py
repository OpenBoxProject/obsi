#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################


from configuration_builder_exceptions import ConnectionConfigurationError


class Connection(object):
    """
    A connection between two elements.
    """

    __CONNECTION_PATTERN = "{from_element}[{from_port}]->[{to_port}]{to_element};"

    def __init__(self, src, dst, src_port=0, dst_port=0):
        self.src = src
        self.dst = dst
        self.src_port = src_port
        self.dst_port = dst_port

    @classmethod
    def from_dict(cls, config):
        src = config.get("src")
        if src is None:
            raise ConnectionConfigurationError("Connection has no 'src' element in configuration")
        dst = config.get("dst")
        if dst is None:
            raise ConnectionConfigurationError("Connection has no 'dst' element in configuration")

        try:
            src_port = int(config.get('src_port', '0'))
        except ValueError:
            raise ConnectionConfigurationError("src_port must be an integer")
        try:
            dst_port = int(config.get('dst_port', '0'))
        except ValueError:
            raise ConnectionConfigurationError("dst_port must be an integer")

        return cls(src, dst, src_port, dst_port)

    def to_click_config(self):
        return self.__CONNECTION_PATTERN.format(from_element=self.src, to_element=self.dst,
                                                from_port=self.src_port, to_port=self.dst_port)

    def to_dict(self):
        return dict(src=self.src, dst=self.dst, src_port=self.src_port, dst_port=self.dst_port)

    def __str__(self):
        return str(self.to_dict())

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (self.src == other.src and
                self.dst == other.dst and
                self.src_port == other.src_port and
                self.dst_port == other.dst_port)

    def __ne__(self, other):
        return not self.__eq__(other)


class MultiConnection(object):
    """
    Multiple connections between two elements where the amount of connections
    is based on the size of some field of the input
    """
    def __init__(self, src, dst, based_on):
        self.src = src
        self.dst = dst
        self.based_on = based_on

    @classmethod
    def from_dict(cls, config):
        src = config.get("src")
        if src is None:
            raise ConnectionConfigurationError("Connection has no 'src' element in configuration")
        dst = config.get("dst")
        if dst is None:
            raise ConnectionConfigurationError("Connection has no 'dst' element in configuration")
        based_on = config.get('based_on')
        if based_on is None:
            raise ConnectionConfigurationError("Connection has no 'based_on' element in configuration")

        return cls(src, dst, based_on)

    def to_dict(self):
        return dict(src=self.src, dst=self.dst, based_on=self.based_on)

    def to_connections(self, element):
        try:
            field = getattr(element, self.based_on)
        except AttributeError:
            raise ConnectionConfigurationError("Element {element} has no field named {name}".format(element=element.name,
                                                                                                    name=self.based_on))
        if not isinstance(field, (tuple, list)):
            raise ConnectionConfigurationError("Field {name} need to be a list/tuple not {type}".format(name=self.based_on,
                                                                                                        type=type(field)))
        connections = []
        for i in xrange(len(field)):
            connections.append(Connection(self.src, self.dst, i, i))

        return connections