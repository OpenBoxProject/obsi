import functools
import re
import json

from exceptions import ClickBlockConfigurationError, ClickElementConfigurationError
import transformations
from click_elements import Element, ClickElementConfigurationError
from connection import Connection
from configuration_builder.exceptions import ConnectionConfigurationError
from open_box_blocks import OpenBoxBlock


class ClickBlockMeta(type):
    def __init__(cls, name, bases, dct):
        if not hasattr(cls, "blocks_registry"):
            # this is the base class. Create an empty registry
            cls.blocks_registry = {}
        else:
            # this is the derived class. Add cls to the registry
            cls.blocks_registry[name] = cls

        super(ClickBlockMeta, cls).__init__(name, bases, dct)


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
    MULTIPLE_HANDLER_RE = re.compile(r'(?P<base>.*)\$(?P<num>\d+)')

    def __init__(self, open_box_block):
        self.block = open_box_block

    @classmethod
    def from_open_box_block(cls, open_box_block):
        """
        :rtype : ClickBlock
        """
        clazz = cls.blocks_registry[open_box_block.type]
        return clazz(open_box_block)

    def elements(self):
        elements = []
        for element_config in self.__elements__:
            try:
                elements.append(self._create_element_instance(element_config))
            except (ClickElementConfigurationError, KeyError) as e:
                raise ClickBlockConfigurationError(
                    "Unable to build click configuration for block {name}".format(name=self.block.name))
        return elements

    def required_element_types(self):
        return set(element_config['type'] for element_config in self.__elements__)

    def _create_element_instance(self, element_config):
        type = element_config['type']
        name = self._to_external_element_name(element_config['name'])
        config = element_config['config']
        new_config = {}
        for field_name, field_value in config.iteritems():
            if isinstance(field_value, str) and field_value.startswith(self.VARIABLE_INDICATOR):
                new_config[field_name] = self._transform_config_field(field_value.lstrip(self.VARIABLE_INDICATOR))
            else:
                new_config[field_name] = field_value
        return Element.from_dict(dict(name=name, type=type, config=new_config))

    def _transform_config_field(self, variable_name):
        fields, transform_function = self.__config_mapping__[variable_name]
        field_values = [getattr(self.block, field_name, None) for field_name in fields]
        return transform_function(*field_values)

    def _to_external_element_name(self, element):
        return self.ELEMENT_NAME_PATTERN.format(block=self.block.name, element=element)

    def connections(self):
        connections = []
        for connection in self.__connections__:
            if isinstance(connection, dict):
                connection = Connection.from_dict(connection)
            connections.append(self._translate_connection(connection))

        return connections

    def _translate_connection(self, connection):
        src_element = self._to_external_element_name(connection.src)
        dst_element = self._to_external_element_name(connection.dst)
        return Connection(src_element, dst_element, connection.src_port, connection.dst_port)

    def input_element_and_port(self, port):
        if self.__input__ is None:
            return None, None
        elif isinstance(self.__input__, str):
            element = self._to_external_element_name(self.__input__)
            return element, port
        else:
            local_element, new_port = self.__input__[port]
            element = self._to_external_element_name(local_element)
            return element, new_port

    def output_element_and_port(self, port):
        if self.__output__ is None:
            return None, None
        elif isinstance(self.__output__, str):
            element = self._to_external_element_name(self.__output__)
            return element, port
        else:
            local_element, new_port = self.__output__[port]
            element = self._to_external_element_name(local_element)
            return element, new_port

    def translate_read_handler(self, handler_name):
        return self._translate_handler(handler_name, self.__read_mapping__)

    def translate_write_handler(self, handler_name):
        return self._translate_handler(handler_name, self.__write_mapping__)

    def _translate_handler(self, handler_name, mapping):
        try:
            local_element, local_handler_name, transform_function = mapping[handler_name]
        except KeyError:
            # maybe its a handler_$i name
            matches = self.MULTIPLE_HANDLER_RE.findall(handler_name)
            if matches:
                base, num = matches[0]
                num = int(num)
                try:
                    general_handler_name = base + '$i'
                    local_element, general_local_handler_name, transform_function = mapping[general_handler_name]
                    local_handler_name = general_local_handler_name.replace('$i', '$%d' % num)
                    transform_function = functools.partial(transform_function, num=num)
                except KeyError:
                    raise ValueError("Unknown handler name: {name}".format(name=handler_name))
            else:
                raise ValueError("Unknown handler name: {name}".format(name=handler_name))

        return self._to_external_element_name(local_element), local_handler_name, transform_function


def build_click_block(name, config_mapping=None, elements=None, connections=None, input=None, output=None,
                      read_mapping=None, write_mapping=None):
    if name not in OpenBoxBlock.blocks_registry:
        raise ValueError("Unknown OpenBoxBlock {name} named".format(name=name))

    config_mapping = config_mapping or {}
    elements = elements or ()
    connections = connections or ()
    read_mapping = read_mapping or {}
    write_mapping = write_mapping or {}

    config_mapping = _update_config_mapping(config_mapping)
    element_names = _get_element_names(elements)
    _verify_connections(connections, element_names)

    # verify input/output mapping
    if input and not isinstance(input, (str, dict)):
        raise TypeError("Input is of the wrong type {type}".format(type=type(input)))

    if output and not isinstance(output, (str, dict)):
        raise TypeError("Output is of the wrong type {type}".format(type=type(output)))

    read_mapping = _update_handler_mapping(element_names, read_mapping, 'read')
    write_mapping = _update_handler_mapping(element_names, write_mapping, 'write')

    args = dict(__config_mapping__=config_mapping, __elements__=elements, __connections__=connections,
                __input__=input, __output__=output, __read_mapping__=read_mapping, __write_mapping__=write_mapping)

    return ClickBlockMeta(name, (ClickBlock,), args)


def _update_config_mapping(config_mapping):
    if not isinstance(config_mapping, dict):
        raise TypeError("config_mapping must be of type dict not {type}".format(type=type(config_mapping)))

    updated_config_mapping = {}
    for k, v in config_mapping.iteritems():
        try:
            fields, transform_function_name = v
            if transform_function_name is None:
                if len(fields) != 1:
                    raise TypeError(
                        "The transformation function for {name} is None but there are more then 1 field".format(
                            name=k))
                else:
                    updated_config_mapping[k] = (fields, transformations.identity)
            else:
                transform_function = getattr(transformations, transform_function_name)
                updated_config_mapping[k] = (fields, transform_function)

        except TypeError:
            raise TypeError(
                "The value for configuration mapping {name} must be (fields, transform_function_name)".format(
                    name=k))
        except AttributeError:
            raise ValueError(
                "Unknown transformation function for configuration mapping field {name}".format(name=k))
    return updated_config_mapping


def _get_element_names(elements):
    element_names = set()
    for element in elements:
        try:
            parsed_element = Element.from_dict(element)
            element_names.add(parsed_element.name)
        except ClickElementConfigurationError:
            raise ValueError('Illegal element configuration {config}'.format(config=element))

    return element_names


def _verify_connections(connections, element_names):
    # verify connections
    for connection in connections:
        try:
            if isinstance(connection, dict):
                parsed_connection = Connection.from_dict(connection)
            elif isinstance(connection, Connection):
                parsed_connection = connection
            else:
                raise TypeError(
                    "Connection must be of type dict or Connection and not {type}".format(type=type(connection)))
            if parsed_connection.src not in element_names:
                raise ValueError(
                    'Undefined src {name} in connection'.format(name=parsed_connection.src))
            if parsed_connection.dst not in element_names:
                raise ValueError('Undefined dst {name} in connection'.format(name=parsed_connection.dst))

        except ConnectionConfigurationError:
            raise ValueError('Illegal connection configuration: {config}'.format(config=connection))


def _update_handler_mapping(element_names, mapping, handler_type):
    if not isinstance(mapping, dict):
        raise TypeError("{handler_type} mapping is of the wrong type {type}".format(type=type(mapping),
                                                                                    handler_type=handler_type))
    new_mapping = {}
    for k, v in mapping.iteritems():
        try:
            element_name, handler_name, transform_function_name = v
            if element_name not in element_names:
                raise ValueError("Mapping for {handler_type} handler {name}"
                                 " refers to unknown element {element}".format(name=k,
                                                                               element=element_name,
                                                                               handler_type=handler_type))
            transform_function = getattr(transformations, transform_function_name, None)
            new_mapping[k] = (element_name, handler_name, transform_function)
        except TypeError:
            raise ValueError("Mapping for {handler_type} handler {name} "
                             "is not a tuple of correct size".format(name=k, handler_type=handler_type))
    return new_mapping


def build_click_block_from_dict(config):
    name = config.pop('type')
    return build_click_block(name, **config)


def build_click_block_from_json(json_config):
    config = json.loads(json_config)
    return build_click_block_from_dict(config)


def _no_transform(name):
    return [name], None


FromDevice = build_click_block('FromDevice',
                               config_mapping=dict(devname=_no_transform('devname'),
                                                   sniffer=_no_transform('sniffer'),
                                                   promisc=_no_transform('promisc')),
                               elements=[
                                   dict(name='from_device', type='FromDevice',
                                        config=dict(devname='$devname', sniffer='$sniffer', promisc='$promisc')),
                                   dict(name='counter', type='Counter', config={})
                               ],
                               connections=[
                                   dict(src='from_device', dst='counter', src_port=0, dst_port=0),
                               ],
                               output='counter',
                               read_mapping=dict(count=('counter', 'count', 'to_int'),
                                                 byte_count=('counter', 'byte_count', 'to_int'),
                                                 rate=('counter', 'rate', 'to_float'),
                                                 byte_rate=('counter', 'byte_rate', 'to_float'),
                                                 drops=('from_device', 'kernel-drops', 'identity')),
                               write_mapping=dict(reset_counts=('counter', 'reset_counts', 'identity')))

FromDump = build_click_block('FromDump',
                             config_mapping=dict(filename=_no_transform('filename'),
                                                 timing=_no_transform('timing'),
                                                 active=_no_transform('active')),
                             elements=[
                                 dict(name='from_dump', type='FromDump',
                                      config=dict(filename='$filename', timing='$timing', active='$active')),
                                 dict(name='counter', type='Counter', config={})
                             ],
                             connections=[
                                 dict(src='from_dump', dst='counter', src_port=0, dst_port=0),
                             ],
                             output='counter',
                             read_mapping=dict(
                                 count=('counter', 'count', 'to_int'),
                                 byte_count=('counter', 'byte_count', 'to_int'),
                                 rate=('counter', 'rate', 'to_float'),
                                 byte_rate=('counter', 'byte_rate', 'to_float'),
                             ),
                             write_mapping=dict(
                                 reset_counts=('counter', 'reset_counts', 'identity'),
                                 active=('from_dump', 'active', 'identity'),
                             ))

Discard = build_click_block('Discard',
                            elements=[
                                dict(name='discard', type='Discard', config=dict()),
                            ],
                            input='discard',
                            read_mapping=dict(
                                count=('discard', 'count', 'to_int'),
                            ),
                            write_mapping=dict(
                                reset_counts=('discard', 'reset_counts', 'identity'),
                            ))

ToDump = build_click_block('ToDump',
                           config_mapping=dict(filename=_no_transform('filename')),
                           elements=[
                               dict(name='to_dump', type='ToDump', config=dict(filename='$filename')),
                           ],
                           input='to_dump')