from click_elements import Element, ElementConfigurationError
from connection import Connection


class ClickBlockMeta(type):
    def __init__(cls, name, bases, dct):
        if not hasattr(cls, "blocks_registry"):
            # this is the base class. Create an empty registry
            cls.blocks_registry = {}
        else:
            # this is the derived class. Add cls to the registry
            cls.blocks_registry[name] = cls

        super(ClickBlockMeta, cls).__init__(name, bases, dct)


class ClickBlockError(Exception):
    """
    Base class for all errors related to Click Blocks
    """
    pass


class ClickBlockConfigurationError(ClickBlockError):
    pass


class ClickBlock(object):
    __metaclass__ = ClickBlockMeta
    __config_mapping__ = {}
    __elements__ = ()
    __connections__ = ()
    __input__ = None
    __output__ = None
    __read_mapping__ = {}
    __write_mapping__ = {}

    ELEMENT_NAME_PATTERN = '{block}@_@{element}'
    VARIABLE_INDICATOR = '$'

    def __init__(self, open_box_block):
        self.block = open_box_block

    def elements(self):
        elements = []
        for element_config in self.__elements__:
            try:
                elements.append(self._create_element_instance(element_config))
            except (ElementConfigurationError, KeyError) as e:
                raise ClickBlockConfigurationError(
                    "Unable to build click configuration for block {name}".format(name=self.block.name))
        return elements

    def _create_element_instance(self, element_config):
        new_config = {'type': element_config.pop('type'),
                      'name': self.ELEMENT_NAME_PATTERN.format(block=self.block.name,
                                                               element=element_config.pop('name'))}
        for field_name, field_value in element_config.iteritems():
            if isinstance(field_value, str) and field_value.startswith(self.VARIABLE_INDICATOR):
                new_config[field_name] = self._transform_config_field(field_value.lstrip(self.VARIABLE_INDICATOR))
            else:
                new_config[field_name] = field_value
        return Element.from_dict(new_config)

    def _transform_config_field(self, variable_name):
        fields, transform_function = self.__config_mapping__[variable_name]
        if transform_function is None:
            if len(fields) != 1:
                raise ClickBlockConfigurationError(
                    "Incorrect definition for Click block {block}".format(block=self.block.name))
            else:
                return getattr(self.block, fields[0])
        else:
            field_values = [getattr(self.block, field_name, None) for field_name in fields]
            return transform_function(*field_values)

    def connections(self):
        connections = []
        for connection in self.__connections__:
            connections.append(self._translate_connection(connection))

        return connections

    def _translate_connection(self, connection):
        from_element = self.ELEMENT_NAME_PATTERN.format(block=self.block, element=connection.from_element)
        to_element = self.ELEMENT_NAME_PATTERN.format(block=self.block, element=connection.to_element)
        return Connection(from_element, to_element, connection.from_port, connection.to_port)

    def input_element_and_port(self, port):
        if self.__input__ is None:
            return None, None
        elif isinstance(self.__input__, str):
            element = self.ELEMENT_NAME_PATTERN.format(block=self.block.name, element=self.__input__)
            return element, port
        else:
            local_element, new_port = self.__input__[port]
            element = self.ELEMENT_NAME_PATTERN.format(block=self.block.name, element=local_element)
            return element, new_port

    def output_element_and_port(self, port):
        if self.__output__ is None:
            return None, None
        elif isinstance(self.__output__, str):
            element = self.ELEMENT_NAME_PATTERN.format(block=self.block.name, element=self.__output__)
            return element, port
        else:
            local_element, new_port = self.__output__[port]
            element = self.ELEMENT_NAME_PATTERN.format(block=self.block.name, element=local_element)
            return element, new_port








