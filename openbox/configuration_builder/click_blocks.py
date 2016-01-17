#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################

import functools
import re
import json
import sys

import transformations
from matching import CompoundMatch, HeaderMatch
from configuration_builder_exceptions import ClickBlockConfigurationError, ConnectionConfigurationError
from click_elements import Element, ClickElementConfigurationError
from connection import Connection, MultiConnection
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
    __multi_connections__ = ()
    __input__ = None
    __output__ = None
    __read_mapping__ = {}
    __write_mapping__ = {}

    ELEMENT_NAME_PATTERN = '{block}@_@{element}'
    VARIABLE_INDICATOR = '$'
    MULTIPLE_HANDLER_RE = re.compile(r'(?P<base>.*)\$(?P<num>\d+)')

    def __init__(self, open_box_block):
        self._block = open_box_block

    @property
    def name(self):
        return self._block.name

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
                    "Unable to build click configuration for block {name}".format(name=self._block.name)), None, \
                    sys.exc_info()[2]
        return elements

    @classmethod
    def required_element_types(cls):
        return set(element_config['type'] for element_config in cls.__elements__)

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
        field_values = [getattr(self._block, field_name, None) for field_name in fields]
        return transform_function(*field_values)

    def _to_external_element_name(self, element):
        return self.ELEMENT_NAME_PATTERN.format(block=self._block.name, element=element)

    def connections(self):
        connections = []
        for connection in self.__connections__:
            if isinstance(connection, dict):
                connection = Connection.from_dict(connection)
            connections.append(self._translate_connection(connection))
        connections.extend(self._connections_from_multi_connections())

        return connections

    def _translate_connection(self, connection):
        src_element = self._to_external_element_name(connection.src)
        dst_element = self._to_external_element_name(connection.dst)
        return Connection(src_element, dst_element, connection.src_port, connection.dst_port)

    def _translate_multi_connection(self, multi_connection):
        src = self._to_external_element_name(multi_connection.src)
        dst = self._to_external_element_name(multi_connection.dst)
        based_on = multi_connection.based_on
        new_multi_connection = MultiConnection(src, dst, based_on)
        return new_multi_connection

    def _connections_from_multi_connections(self):
        connections = []
        elements_by_names = self._elements_by_names()
        for multi_connection in self.__multi_connections__:
            if isinstance(multi_connection, dict):
                multi_connection = MultiConnection.from_dict(multi_connection)
            new_multi_connection = self._translate_multi_connection(multi_connection)
            connections.extend(new_multi_connection.to_connections(elements_by_names[new_multi_connection.src]))

        return connections

    def _elements_by_names(self):
        return dict((element.name, element) for element in self.elements())

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


def build_click_block(name, config_mapping=None, elements=None, connections=None, multi_connections=None,
                      input=None, output=None, read_mapping=None, write_mapping=None):
    if name not in OpenBoxBlock.blocks_registry:
        raise ValueError("Unknown OpenBoxBlock {name} named".format(name=name))

    config_mapping = config_mapping or {}
    elements = elements or ()
    connections = connections or ()
    multi_connections = multi_connections or ()
    read_mapping = read_mapping or {}
    write_mapping = write_mapping or {}

    config_mapping = _update_config_mapping(config_mapping)
    elements_by_names = _get_elements_by_names(elements)
    _verify_connections(connections, elements_by_names)
    _verify_multi_connection(multi_connections, elements_by_names)

    # verify input/output mapping
    if input and isinstance(input, str) and input not in elements_by_names:
        raise ValueError("Input is not a declares element")
    if input and not isinstance(input, (str, dict)):
        raise TypeError("Input is of the wrong type {type}".format(type=type(input)))

    if output and isinstance(output, str) and output not in elements_by_names:
        raise ValueError("Output is not a declares element")
    if output and not isinstance(output, (str, dict)):
        raise TypeError("Output is of the wrong type {type}".format(type=type(output)))

    read_mapping = _update_handler_mapping(elements_by_names, read_mapping, 'read')
    write_mapping = _update_handler_mapping(elements_by_names, write_mapping, 'write')

    args = dict(__config_mapping__=config_mapping,
                __elements__=elements,
                __connections__=connections,
                __multi_connections__=multi_connections,
                __input__=input, __output__=output,
                __read_mapping__=read_mapping,
                __write_mapping__=write_mapping)

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


def _get_elements_by_names(elements):
    elements_by_names = {}
    for element in elements:
        try:
            parsed_element = Element.from_dict(element)
            elements_by_names[parsed_element.name] = parsed_element
        except ClickElementConfigurationError:
            raise ValueError('Illegal element configuration {config}'.format(config=element)), None, sys.exc_info()[2]

    return elements_by_names


def _verify_connections(connections, elements_by_names):
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
            if parsed_connection.src not in elements_by_names:
                raise ValueError(
                    'Undefined src {name} in connection'.format(name=parsed_connection.src))
            if parsed_connection.dst not in elements_by_names:
                raise ValueError('Undefined dst {name} in connection'.format(name=parsed_connection.dst))

        except ConnectionConfigurationError:
            raise ValueError('Illegal connection configuration: {config}'.format(config=connection))


def _verify_multi_connection(multi_connections, elements_by_names):
    for multi_connection in multi_connections:
        try:
            if isinstance(multi_connection, dict):
                parsed_connection = MultiConnection.from_dict(multi_connection)
            elif isinstance(multi_connection, Connection):
                parsed_connection = multi_connection
            else:
                raise TypeError(
                    "Connection must be of type dict or Connection and not {type}".format(type=type(multi_connection)))
            if parsed_connection.src not in elements_by_names:
                raise ValueError(
                    'Undefined src {name} in connection'.format(name=parsed_connection.src))
            if parsed_connection.dst not in elements_by_names:
                raise ValueError('Undefined dst {name} in connection'.format(name=parsed_connection.dst))

            if parsed_connection.based_on != elements_by_names[parsed_connection.src].__list_arguments__.name:
                raise ValueError(
                    'Based on field {field} is not a list field of {element}'.format(field=parsed_connection.based_on,
                                                                                     element=parsed_connection.src))
        except ConnectionConfigurationError:
            raise ValueError('Illegal multi connection configuration: {config}'.format(config=multi_connection))


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
    name = config.pop('name')
    return build_click_block(name, **config)


def build_click_block_from_json(json_config):
    config = json.loads(json_config)
    return build_click_block_from_dict(config)


def _no_transform(name):
    return [name], None


FromDevice = build_click_block('FromDevice',
                               config_mapping=dict(devname=_no_transform('devname'),
                                                   sniffer=_no_transform('sniffer'),
                                                   promisc=_no_transform('promisc'),
                                                   snaplen=_no_transform('snaplen')),
                               elements=[
                                   dict(name='from_device', type='FromDevice',
                                        config=dict(devname='$devname', sniffer='$sniffer', promisc='$promisc',
                                                    snaplen='$snaplen')),
                                   dict(name='mark_ip_header', type='AutoMarkIPHeader', config={}),
                                   dict(name='counter', type='Counter', config={})
                               ],
                               connections=[
                                   dict(src='from_device', dst='mark_ip_header', src_port=0, dst_port=0),
                                   dict(src='mark_ip_header', dst='counter', src_port=0, dst_port=0),
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
                                 dict(name='mark_ip_header', type='AutoMarkIPHeader', config={}),
                                 dict(name='counter', type='Counter', config={})
                             ],
                             connections=[
                                 dict(src='from_dump', dst='mark_ip_header', src_port=0, dst_port=0),
                                 dict(src='mark_ip_header', dst='counter', src_port=0, dst_port=0),
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
                               dict(name='to_dump', type='ToDump', config=dict(filename='$filename', unbuffered=True)),
                           ],
                           input='to_dump')

ToDevice = build_click_block('ToDevice',
                             config_mapping=dict(devname=_no_transform('devname')),
                             elements=[
                                 dict(name='queue', type='Queue', config={}),
                                 dict(name='to_device', type='ToDevice', config=dict(devname='$devname'))
                             ],
                             connections=[
                                 dict(src='queue', dst='to_device', src_port=0, dst_port=0),
                             ],
                             input='queue'
                             )

Log = build_click_block('Log',
                        config_mapping=dict(content=(['name', 'severity', 'message'], 'to_push_message_content'),
                                            attach_packet=_no_transform('attach_packet'),
                                            packet_size=_no_transform('packet_size')
                                            ),
                        elements=[
                            dict(name='push_message', type='PushMessage',
                                 config=dict(type='LOG', msg='$content', channel='openbox',
                                             attach_packet='$attach_packet', packet_size='$packet_size')),
                        ],
                        input='push_message',
                        output='push_message')

Alert = build_click_block('Alert',
                          config_mapping=dict(content=(['name', 'severity', 'message'], 'to_push_message_content'),
                                              attach_packet=_no_transform('attach_packet'),
                                              packet_size=_no_transform('packet_size')
                                              ),
                          elements=[
                              dict(name='push_message', type='PushMessage',
                                   config=dict(type='ALERT', msg='$content', channel='openbox',
                                               attach_packet='$attach_packet', packet_size='$packet_size')),
                          ],
                          input='push_message',
                          output='push_message')

ContentClassifier = build_click_block('ContentClassifier',
                                      config_mapping=dict(pattern=_no_transform('pattern')),
                                      elements=[
                                          dict(name='classifier', type='Classifier', config=dict(pattern='$pattern')),
                                          dict(name='counter', type='MultiCounter', config={})
                                      ],
                                      multi_connections=[
                                          dict(src='classifier', dst='counter', based_on='pattern')
                                      ],
                                      input='classifier',
                                      output='counter',
                                      read_mapping=dict(
                                          count=('counter', 'count', 'identity'),
                                          byte_count=('counter', 'byte_count', 'identity'),
                                          rate=('counter', 'rate', 'identity'),
                                          byte_rate=('counter', 'byte_rate', 'identity'),
                                      ),
                                      write_mapping=dict(
                                          reset_counts=('counter', 'reset_counts', 'identity'),
                                      ))


class HeaderClassifier(ClickBlock):
    """
    This is a hand made ClickBlock for HeaderClassifier OpenBox Block
    """
    __config_mapping__ = {}

    # Fake attributes used by other API functions
    __elements__ = (dict(name='counter', type='MultiCounter', config={}),
                    dict(name='classifier', type='Classifier', config=dict(pattern=[])))

    __input__ = 'classifier'
    __output__ = 'counter'
    __read_mapping__ = dict(
        count=('counter', 'count', 'identity'),
        byte_count=('counter', 'byte_count', transformations.identity),
        rate=('counter', 'rate', 'identity'),
        byte_rate=('counter', 'byte_rate', transformations.identity),
    )
    __write_mapping__ = dict(reset_counts=('counter', 'reset_counts', 'identity'))

    def __init__(self, open_box_block):
        super(HeaderClassifier, self).__init__(open_box_block)
        self._elements = []
        self._connections = []

    def elements(self):
        if not self._elements:
            self._compile_block()
        return self._elements

    def connections(self):
        if not self._connections:
            self._compile_block()
        return self._connections

    def _compile_block(self):
        self._elements.append(Element.from_dict(dict(name=self._to_external_element_name('counter'),
                                                     type='MultiCounter', config={})))
        patterns, rule_numbers = self._compile_match_patterns()
        self._elements.append(Element.from_dict(dict(name=self._to_external_element_name('classifier'),
                                                     type='Classifier', config=dict(pattern=patterns))))
        for i, rule_number in enumerate(rule_numbers):
            self._connections.append(Connection(self._to_external_element_name('classifier'),
                                                self._to_external_element_name('counter'), i, rule_number))

    def _compile_match_patterns(self):
        matches = [HeaderMatch(match) for match in self._block.match]
        patterns = []
        rule_numbers = []
        for i, match in enumerate(matches):
            for pattern in match.to_patterns():
                patterns.append(pattern)
                rule_numbers.append(i)
        return patterns, rule_numbers


RegexMatcher = build_click_block('RegexMatcher',
                                 config_mapping=dict(pattern=(['pattern'], 'to_quoted_json_escaped'),
                                                     match_all=_no_transform('match_all'),
                                                     payload_only=_no_transform('payload_only')),
                                 elements=[
                                     dict(name='regex_matcher', type='RegexMatcher',
                                          config=dict(pattern='$pattern', payload_only='$payload_only',
                                                      match_all='$match_all')),
                                     dict(name='counter', type='MultiCounter', config={}),
                                 ],
                                 connections=[
                                     dict(src='regex_matcher', dst='counter', src_port=0, dst_port=0),
                                     dict(src='regex_matcher', dst='counter', src_port=1, dst_port=1),
                                 ],
                                 input='regex_matcher',
                                 output='counter',
                                 read_mapping=dict(
                                     count=('counter', 'count', 'identity'),
                                     byte_count=('counter', 'byte_count', 'identity'),
                                     rate=('counter', 'rate', 'identity'),
                                     byte_rate=('counter', 'byte_rate', 'identity'),
                                     match_all=('regex_matcher', 'match_all', 'identity'),
                                     payload_only=('regex_matcher', 'payload_only', 'identity'),
                                 ),
                                 write_mapping=dict(
                                     reset_counts=('counter', 'reset_counts', 'identity'),
                                     match_all=('regex_matcher', 'match_all', 'to_lower'),
                                     payload_only=('regex_matcher', 'payload_only', 'to_lower'),
                                 )
                                 )

RegexClassifier = build_click_block('RegexClassifier',
                                    config_mapping=dict(pattern=(['pattern'], 'to_quoted_json_escaped'),
                                                        payload_only=_no_transform('payload_only')),
                                    elements=[
                                        dict(name='regex_classifier', type='RegexClassifier',
                                             config=dict(pattern='$pattern', payload_only='$payload_only')),
                                        dict(name='counter', type='MultiCounter', config={}),
                                    ],
                                    multi_connections=[
                                        dict(src='regex_classifier', dst='counter', based_on='pattern')
                                    ],
                                    input='regex_classifier',
                                    output='counter',
                                    read_mapping=dict(
                                        count=('counter', 'count', 'identity'),
                                        byte_count=('counter', 'byte_count', 'identity'),
                                        rate=('counter', 'rate', 'identity'),
                                        byte_rate=('counter', 'byte_rate', 'identity'),
                                        payload_only=('regex_classifier', 'payload_only', 'identity'),
                                    ),
                                    write_mapping=dict(
                                        reset_counts=('counter', 'reset_counts', 'identity'),
                                        payload_only=('regex_classifier', 'payload_only', 'to_lower'),
                                    )
                                    )

VlanDecapsulate = build_click_block('VlanDecapsulate',
                                    elements=[dict(name='vlan_decap', type='VLANDecap', config={})],
                                    input='vlan_decap',
                                    output='vlan_decap',
                                    )

VlanEncapsulate = build_click_block('VlanEncapsulate',
                                    config_mapping=dict(
                                        vlan_tci=(['vlan_vid', 'vlan_dei', 'vlan_pcp'], "to_vlan_tci"),
                                        vlan_pcp=(['vlan_pcp'], 'to_int'),
                                        ethertype=_no_transform('ethertype')
                                    ),
                                    elements=[dict(name='vlan_encap', type='VLANEncap',
                                                   config=dict(vlan_tci='$vlan_tci', vlan_pcp='$vlan_pcp',
                                                               ethertype='$ethertype'))],
                                    input='vlan_encap',
                                    output='vlan_encap',
                                    read_mapping=dict(
                                        vlan_vid=('vlan_encap', 'vlan_vid', 'identity'),
                                        vlan_pcp=('vlan_encap', 'vlan_pcp', 'identity'),
                                        vlan_tci=('vlan_encap', 'vlan_tci', 'identity'),
                                        ethertype=('vlan_encap', 'ethertype', 'identity'),
                                    ),
                                    write_mapping=dict(
                                        vlan_vid=('vlan_encap', 'vlan_vid', 'identity'),
                                        vlan_pcp=('vlan_encap', 'vlan_pcp', 'identity'),
                                        vlan_tci=('vlan_encap', 'vlan_tci', 'identity'),
                                        ethertype=('vlan_encap', 'ethertype', 'identity'),
                                    )
                                    )

DecIpTtl = build_click_block('DecIpTtl',
                             config_mapping=dict(active=_no_transform('active')),
                             elements=[
                                 dict(name='dec_ip_ttl', type='DecIPTTL',
                                      config=dict(active='$active')),
                                 dict(name='counter', type='MultiCounter', config={}),
                             ],
                             connections=[
                                 dict(src='dec_ip_ttl', dst='counter', src_port=0, dst_port=0),
                                 dict(src='dec_ip_ttl', dst='counter', src_port=1, dst_port=1),
                             ],
                             input='dec_ip_ttl',
                             output='counter',
                             read_mapping=dict(
                                 count=('counter', 'count', 'identity'),
                                 byte_count=('counter', 'byte_count', 'identity'),
                                 rate=('counter', 'rate', 'identity'),
                                 byte_rate=('counter', 'byte_rate', 'identity'),
                                 active=('dec_ip_ttl', 'active', 'identity'),
                             ),
                             write_mapping=dict(
                                 reset_counts=('counter', 'reset_counts', 'identity'),
                                 active=('dec_ip_ttl', 'active', 'to_lower'),
                             ))

Ipv4AddressTranslator = build_click_block('Ipv4AddressTranslator',
                                          config_mapping=dict(
                                              input_spec=_no_transform('input_spec'),
                                              tcp_timeout=_no_transform('tcp_timeout'),
                                              tcp_done_timeout=_no_transform('tcp_done_timeout'),
                                              tcp_nodata_timeout=_no_transform('tcp_nodata_timeout'),
                                              tcp_guarantee=_no_transform('tcp_guarantee'),
                                              udp_timeout=_no_transform('udp_timeout'),
                                              udp_streaming_timeout=_no_transform('udp_streaming_timeout'),
                                              udp_guarantee=_no_transform('udp_guarantee'),
                                              reap_interval=_no_transform('reap_interval'),
                                              mapping_capacity=_no_transform('mapping_capacity')
                                          ),
                                          elements=[dict(name='ip_rewriter', type='IPRewriter',
                                                         config=dict(
                                                             input_spec='$input_spec',
                                                             tcp_timeout='$tcp_timeout',
                                                             tcp_done_timeout='$tcp_done_timeout',
                                                             tcp_nodata_timeout='$tcp_nodata_timeout',
                                                             tcp_guarantee='$tcp_guarantee',
                                                             udp_timeout='$udp_timeout',
                                                             udp_streaming_timeout='$udp_streaming_timeout',
                                                             udp_guarantee='$udp_guarantee',
                                                             reap_interval='$reap_interval',
                                                             mapping_capacity='$mapping_capacity'
                                                         ))],
                                          input='ip_rewriter',
                                          output='ip_rewriter',
                                          read_mapping=dict(
                                              mapping_count=('ip_rewriter', 'nmappings', 'identity'),
                                              mapping_failures=('ip_rewriter', 'mapping_failures', 'identity'),
                                              length=('ip_rewriter', 'length', 'identity'),
                                              capacity=('ip_rewriter', 'capacity', 'identity'),
                                              tcp_mappings=('ip_rewriter', 'tcp_mappings', 'identity'),
                                              udp_mappings=('ip_rewriter', 'udp_mappings', 'identity'),
                                          ),
                                          write_mapping=dict(
                                              capacity=('ip_rewriter', 'capacity', 'identity'),
                                          )
                                          )

Queue = build_click_block('Queue',
                          config_mapping=dict(
                              capacity=_no_transform('capacity'),
                          ),
                          elements=[dict(name='queue', type='Queue', config=dict(capacity='$capacity'))],
                          input='queue',
                          output='queue',
                          read_mapping=dict(
                              length=('queue', 'length', 'identity'),
                              highwater_length=('queue', 'highwater_length', 'identity'),
                              drops=('queue', 'drops', 'identity'),
                              capacity=('queue', 'capacity', 'identity'),

                          ),
                          write_mapping=dict(
                              capacity=('queue', 'reset_counts', 'identity'),
                              reset=('queue', 'reset', 'identity'),
                          )
                          )

NetworkDirectionSwap = build_click_block('NetworkDirectionSwap',
                                         config_mapping=dict(ethernet=_no_transform('ethernet'),
                                                             ipv4=_no_transform('ipv4'),
                                                             ipv6=_no_transform('ipv6'),
                                                             tcp=_no_transform('tcp'),
                                                             udp=_no_transform('udp')),
                                         elements=[dict(name='network_direction_swap', type='NetworkDirectionSwap',
                                                        config=dict(ethernet='$ethernet', ipv4='$ipv4', ipv6='$ipv6',
                                                                    tcp='$tcp', udp='$udp'))],
                                         input='network_direction_swap',
                                         output='network_direction_swap',
                                         read_mapping=dict(
                                             ethernet=('network_direction_swap', 'ethernet', 'identity'),
                                             ipv4=('network_direction_swap', 'ipv4', 'identity'),
                                             ipv6=('network_direction_swap', 'ipv6', 'identity'),
                                             tcp=('network_direction_swap', 'tcp', 'identity'),
                                             udp=('network_direction_swap', 'udp', 'identity'),
                                         ),
                                         write_mapping=dict(
                                             ethernet=('network_direction_swap', 'ethernet', 'identity'),
                                             ipv4=('network_direction_swap', 'ipv4', 'identity'),
                                             ipv6=('network_direction_swap', 'ipv6', 'identity'),
                                             tcp=('network_direction_swap', 'tcp', 'identity'),
                                             udp=('network_direction_swap', 'udp', 'identity'),
                                         )
                                         )

NetworkHeaderFieldsRewriter = build_click_block('NetworkHeaderFieldsRewriter',
                                                config_mapping=dict(eth_src=_no_transform('eth_src'),
                                                                    eth_dst=_no_transform('eth_dst'),
                                                                    eth_type=_no_transform('eth_type'),
                                                                    ipv4_proto=_no_transform('ipv4_proto'),
                                                                    ipv4_src=_no_transform('ipv4_src'),
                                                                    ipv4_dst=_no_transform('ipv4_dst'),
                                                                    ipv4_dscp=_no_transform('ipv4_dscp'),
                                                                    ipv4_ecn=_no_transform('ipv4_ecn'),
                                                                    ipv4_ttl=_no_transform('ipv4_ttl'),
                                                                    tcp_src=_no_transform('tcp_src'),
                                                                    tcp_dst=_no_transform('tcp_dst'),
                                                                    udp_src=_no_transform('udp_src'),
                                                                    udp_dst=_no_transform('udp_dst')),
                                                elements=[
                                                    dict(name='network_rewriter', type='NetworkHeaderFieldsRewriter',
                                                         config=dict(eth_src='$eth_src',
                                                                     eth_dst='$eth_dst',
                                                                     eth_type='$eth_type',
                                                                     ipv4_proto='$ipv4_proto',
                                                                     ipv4_src='$ipv4_src',
                                                                     ipv4_dst='$ipv4_dst',
                                                                     ipv4_dscp='$ipv4_dscp',
                                                                     ipv4_ecn='$ipv4_ecn',
                                                                     ipv4_ttl='$ipv4_ttl',
                                                                     tcp_src='$tcp_src',
                                                                     tcp_dst='$tcp_dst',
                                                                     udp_src='$udp_src',
                                                                     udp_dst='$udp_dst'))
                                                ],
                                                input='network_rewriter', output='network_rewriter',
                                                read_mapping=dict(
                                                    eth_src=('network_rewriter', 'eth_src', 'identity'),
                                                    eth_dst=('network_rewriter', 'eth_dst', 'identity'),
                                                    eth_type=('network_rewriter', 'eth_type', 'identity'),
                                                    ipv4_proto=('network_rewriter', 'ipv4_proto', 'identity'),
                                                    ipv4_src=('network_rewriter', 'ipv4_src', 'identity'),
                                                    ipv4_dst=('network_rewriter', 'ipv4_dst', 'identity'),
                                                    ipv4_dscp=('network_rewriter', 'ipv4_dscp', 'identity'),
                                                    ipv4_ecn=('network_rewriter', 'ipv4_ecn', 'identity'),
                                                    ipv4_ttl=('network_rewriter', 'ipv4_ttl', 'identity'),
                                                    tcp_src=('network_rewriter', 'tcp_src', 'identity'),
                                                    tcp_dst=('network_rewriter', 'tcp_dst', 'identity'),
                                                    udp_src=('network_rewriter', 'udp_src', 'identity'),
                                                    udp_dst=('network_rewriter', 'udp_dst', 'identity')),
                                                write_mapping=dict(
                                                    eth_src=('network_rewriter', 'eth_src', 'identity'),
                                                    eth_dst=('network_rewriter', 'eth_dst', 'identity'),
                                                    eth_type=('network_rewriter', 'eth_type', 'identity'),
                                                    ipv4_proto=('network_rewriter', 'ipv4_proto', 'identity'),
                                                    ipv4_src=('network_rewriter', 'ipv4_src', 'identity'),
                                                    ipv4_dst=('network_rewriter', 'ipv4_dst', 'identity'),
                                                    ipv4_dscp=('network_rewriter', 'ipv4_dscp', 'identity'),
                                                    ipv4_ecn=('network_rewriter', 'ipv4_ecn', 'identity'),
                                                    ipv4_ttl=('network_rewriter', 'ipv4_ttl', 'identity'),
                                                    tcp_src=('network_rewriter', 'tcp_src', 'identity'),
                                                    tcp_dst=('network_rewriter', 'tcp_dst', 'identity'),
                                                    udp_src=('network_rewriter', 'udp_src', 'identity'),
                                                    udp_dst=('network_rewriter', 'udp_dst', 'identity')))


class HeaderPayloadClassifier(ClickBlock):
    __config_mapping__ = {}

    # Fake attributes used by other API functions
    __elements__ = (dict(name='counter', type='MultiCounter', config={}),
                    dict(name='classifier', type='Classifier', config=dict(pattern=[])),
                    dict(name='regex_classifier', type='GroupRegexClassifier', config=dict(pattern=[]))
                    )
    __input__ = 'classifier'
    __output__ = 'counter'
    __read_mapping__ = dict(
        count=('counter', 'count', 'identity'),
        byte_count=('counter', 'byte_count', transformations.identity),
        rate=('counter', 'rate', 'identity'),
        byte_rate=('counter', 'byte_rate', transformations.identity),
    )
    __write_mapping__ = dict(reset_counts=('counter', 'reset_counts', 'identity'))

    _MULTICOUNTER = 'counter'
    _REGEX_CLASSIFIER = 'regex_classifier_{num}'
    _CLASSIFIER = 'classifier'

    def __init__(self, open_box_block):
        super(HeaderPayloadClassifier, self).__init__(open_box_block)
        self._elements = []
        self._connections = []

    def elements(self):
        if not self._elements:
            self._compile_block()
        return self._elements

    def connections(self):
        if not self._connections:
            self._compile_block()
        return self._connections

    def _compile_block(self):
        matches = self._get_matches_from_block()
        self._elements.append(Element.from_dict(dict(name=self._to_external_element_name(self._MULTICOUNTER),
                                                     type='MultiCounter', config={})))
        pattern_number = 0
        patterns = []
        for i, match in enumerate(matches):
            match_patterns = match.header_match.to_patterns()
            self._create_regex_classifier_element_for_match(match, i)
            for _ in match_patterns:
                self._create_content_classifier_to_regex_classifier_connection(pattern_number, i)
                pattern_number += 1
            patterns.extend(match_patterns)
            self._create_regex_classifier_to_counter_connections(match, i)
        self._elements.append(Element.from_dict(dict(name=self._to_external_element_name(self._CLASSIFIER),
                                                     type='Classifier',
                                                     config=dict(pattern=patterns))))

    def _get_matches_from_block(self):
        matches = [CompoundMatch.from_config_dict(match, i) for i, match in enumerate(self._block.match)]
        # keep expanding and combining rules until there are no more options
        previous_size = 0
        while previous_size < len(matches):
            previous_size = len(matches)
            matches = self._expand_matches(matches)
        return matches

    def _expand_matches(self, matches):
        expanded_matches = []
        expanded_matches_set = set(matches)

        # for each match check if it can be combined with lower ranked match,
        # insert the combined match in front of this match.
        # We always add the original rule after all the combined matches that include this match
        for i, this in enumerate(matches, 1):
            for other in matches[i:]:
                if this.is_combinable(other):
                    combined = this.combine(other)
                    if combined not in expanded_matches_set:
                        expanded_matches.append(combined)
                        expanded_matches_set.add(combined)
            expanded_matches.append(this)
        return expanded_matches

    def _create_regex_classifier_element_for_match(self, match, match_number):
        patterns = []
        for i, original_match_number in enumerate(sorted(match.payload_matches)):
            for pattern in match.payload_matches[original_match_number]:
                # escape pattern before passing it to the classifier
                pattern = json.dumps(pattern)
                patterns.append('"{pattern}" {group_number}'.format(pattern=pattern, group_number=i))
        self._elements.append(
            Element.from_dict(dict(name=self._to_external_element_name(self._REGEX_CLASSIFIER.format(num=match_number)),
                                   type='GroupRegexClassifier', config=dict(pattern=patterns))))

    def _create_content_classifier_to_regex_classifier_connection(self, pattern_number, match_number):
        self._connections.append(
            Connection(src=self._to_external_element_name(self._CLASSIFIER),
                       dst=self._to_external_element_name(self._REGEX_CLASSIFIER.format(num=match_number)),
                       src_port=pattern_number, dst_port=0))

    def _create_regex_classifier_to_counter_connections(self, match, match_number):
        for i, original_match_number in enumerate(sorted(match.payload_matches)):
            self._connections.append(
                Connection(src=self._to_external_element_name(self._REGEX_CLASSIFIER.format(num=match_number)),
                           dst=self._to_external_element_name(self._MULTICOUNTER),
                           src_port=i, dst_port=original_match_number))


SetTimestamp = build_click_block('SetTimestamp',
                                 config_mapping=dict(timestamp=_no_transform('timestamp')),
                                 elements=[dict(name='set_timestamp', type='SetTimestamp',
                                                config=dict(timestamp='$timestamp'))],
                                 input='set_timestamp',
                                 output='set_timestamp',
                                 )

SetTimestampDelta = build_click_block('SetTimestampDelta',
                                      config_mapping=dict(type=_no_transform('type')),
                                      elements=[dict(name='set_timestamp_delta', type='SetTimestampDelta',
                                                     config=dict(type='$type'))],
                                      input='set_timestamp_delta',
                                      output='set_timestamp_delta',
                                      )