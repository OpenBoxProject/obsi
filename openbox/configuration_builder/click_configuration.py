#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################


class ClickConfiguration(object):
    REQUIREMENTS_PATTERN = 'require(package "{package}");'

    def __init__(self, requirements=None, elements=None, connections=None):
        self.requirements = requirements or []
        self.elements = elements or []
        self.connections = connections or []
        self._elements_by_name = dict((element.name, element) for element in self.elements)

    def to_engine_config(self):
        config = []
        for requirement in self.requirements:
            config.append(self.REQUIREMENTS_PATTERN.format(package=requirement))

        for element in self.elements:
            config.append(element.to_click_config())

        for connection in self.connections:
            config.append(connection.to_click_config())

        return '\n'.join(config)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (self.requirements == other.requirements and
                self.elements == other.elements and
                self.connections == other.connections)

    def __ne__(self, other):
        return not self.__eq__(other)
