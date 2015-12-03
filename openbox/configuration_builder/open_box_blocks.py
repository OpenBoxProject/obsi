#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################


import json
import capabilities
import re
from collections import OrderedDict
from configuration_builder_exceptions import OpenBoxBlockConfigurationError


class FieldType:
    BOOLEAN = 'boolean'
    ARRAY = 'array'
    INTEGER = 'integer'
    NUMBER = 'number'
    NULL = 'null'
    OBJECT = 'object'
    STRING = 'string'
    MATCH_PATTERNS = 'match_patterns'
    IPV4_TRANSLATION_RULES = 'ipv4_translator_rules'


class ConfigField(object):
    _SUPPORTED_MATCH_FIELDS = set(capabilities.SUPPORTED_MATCH_FIELDS)
    _TRANSLATION_RULES_REGEX = [re.compile(r'(drop|discard)'),
                                re.compile(r'pass \d+'),
                                re.compile(r'keep \d+ \d+'),
                                re.compile(
                                    r"pattern ((?:[0-9]{1,3}\.){3}[0-9]{1,3}|-) [0-9-#?]+ ((?:[0-9]{1,3}\.){3}[0-9]{1,3}|-) [0-9-#?]+ \d+ \d+")]

    def __init__(self, name, required, type, description=None):
        self.name = name
        self.required = required
        self.type = type
        self.description = description or ''

    def validate_value_type(self, value):
        if self.type == FieldType.NULL:
            return value is None
        elif self.type == FieldType.BOOLEAN:
            return isinstance(value, bool)
        elif self.type == FieldType.ARRAY:
            return isinstance(value, list)
        elif self.type == FieldType.INTEGER:
            return isinstance(value, (int, long))
        elif self.type == FieldType.NUMBER:
            return isinstance(value, (int, long, float))
        elif self.type == FieldType.STRING:
            return isinstance(value, basestring)
        elif self.type == FieldType.OBJECT:
            return isinstance(value, dict)
        elif self.type == FieldType.MATCH_PATTERNS:
            return (isinstance(value, (tuple, list)) and
                    all(self._is_valid_match_pattern(pattern) for pattern in value))
        elif self.type == FieldType.IPV4_TRANSLATION_RULES:
            return (isinstance(value, (tuple, list)) and
                    all(self._is_valid_ipv4_translation_rule(input_spec) for input_spec in value))

    def _is_valid_match_pattern(self, pattern):
        return isinstance(pattern, dict) and all(field in self._SUPPORTED_MATCH_FIELDS for field in pattern)

    def _is_valid_ipv4_translation_rule(self, rule):
        for regex in self._TRANSLATION_RULES_REGEX:
            if regex.match(rule):
                return True
        return False

    def to_dict(self):
        result = OrderedDict()
        result['name'] = self.name
        result['required'] = self.required
        result['type'] = self.type
        result['description'] = self.description
        return result


class HandlerField(object):
    def __init__(self, name, type, description=None):
        self.name = name
        self.type = type
        self.description = description or ''

    def to_dict(self):
        result = OrderedDict()
        result['name'] = self.name
        result['type'] = self.type
        result['description'] = self.description
        return result


class OpenBoxBlockMeta(type):
    def __init__(cls, name, bases, dct):
        if not hasattr(cls, "blocks_registry"):
            # this is the base class. Create an empty registry
            cls.blocks_registry = {}
        else:
            # this is the derived class. Add cls to the registry
            cls.blocks_registry[name] = cls

        super(OpenBoxBlockMeta, cls).__init__(name, bases, dct)


class OpenBoxBlock(object):
    """
    The base class for all blocks
    """
    __metaclass__ = OpenBoxBlockMeta
    __fields__ = []
    __read_handlers__ = []
    __write_handlers__ = []

    def __init__(self, name, **kwargs):
        self.name = name
        for field in self.__fields__:
            try:
                value = kwargs[field.name]
                if not field.validate_value_type(value):
                    raise TypeError("Field '{field}' is not a valid '{rtype}'".format(field=field.name,
                                                                                      rtype=field.type))
                setattr(self, field.name, value)
            except KeyError:
                if field.required:
                    raise ValueError("Required field '{field}' not given".format(field=field.name))

    @classmethod
    def from_dict(cls, config):
        """
        Create an instance of an OpenBox Block from the blocks configuration dict

        :param config: The block's configuration
        :type config: dict
        :return: An instance of a specific type
        :rtype: OpenBoxBlock
        """
        block_type = config.pop('type')
        if block_type is None:
            raise OpenBoxBlockConfigurationError("No block type is given in the block's configuration")
        # noinspection PyUnresolvedReferences
        clazz = cls.blocks_registry.get(block_type)
        if clazz is None:
            raise OpenBoxBlockConfigurationError("Unknown block type %s" % block_type)
        name = config.pop('name')
        if name is None:
            raise OpenBoxBlockConfigurationError("A block must have an instance name")
        config = config.pop('config')
        return clazz(name, **config)

    @classmethod
    def to_json_schema(cls, **kwargs):
        schema = OrderedDict()
        schema['type'] = cls.__name__
        schema['configuration'] = [field.to_dict() for field in cls.__fields__]
        schema['read_handlers'] = [field.to_dict() for field in cls.__read_handlers__]
        schema['write_handlers'] = [field.to_dict() for field in cls.__write_handlers__]
        return json.dumps(schema, **kwargs)

    def to_dict(self):
        result = OrderedDict()
        result['type'] = self.__class__.__name__
        result['name'] = self.name
        config = dict()
        for field in self.__fields__:
            value = getattr(self, field.name, None)
            if value is not None:
                config[field.name] = value
        result['config'] = config
        return result

    def to_json(self, **kwargs):
        return json.dumps(self.to_dict(), **kwargs)

    def __str__(self):
        return self.to_json()

    @property
    def type(self):
        return self.__class__.__name__

    def __eq__(self, other):
        if not isinstance(self, other.__class__):
            return False

        return self.name == other.name and all(
            getattr(self, field.name, None) == getattr(other, field.name, None) for field in self.__fields__)

    def __ne__(self, other):
        return not self.__eq__(other)


def build_open_box_block(name, config_fields=None, read_handlers=None, write_handlers=None):
    """
    Create an OpenBoxBlock class based on the arguments it receives.

    :param string name: The class's name
    :param list(ConfigField) config_fields: The configuration fields
    :param list(HandlerField) read_handlers: The read handlers
    :param list(HandlerField)write_handlers: The write handlers
    :return: An OpenBoxBlock class
    :rtype: OpenBoxBlock
    """
    config_fields = config_fields or []
    read_handlers = read_handlers or []
    write_handlers = write_handlers or []
    if not all(isinstance(field, ConfigField) for field in config_fields):
        raise TypeError("All config fields must be of type ConfigField")
    if not all(isinstance(field, HandlerField) for field in read_handlers):
        raise TypeError("All read handlers must be of type HandlerField")
    if not all(isinstance(field, HandlerField) for field in write_handlers):
        raise TypeError("All write handlers must be of type HandlerField")

    args = dict(__fields__=config_fields, __read_handlers__=read_handlers, __write_handlers__=write_handlers)
    return OpenBoxBlockMeta(name, (OpenBoxBlock,), args)


def build_open_box_block_from_dict(block):
    return build_open_box_block(block['name'], block['config_fields'], block['read_handlers'], block['write_handlers'])


def build_open_box_from_json(json_block):
    return build_open_box_block_from_dict(json.loads(json_block))


FromDevice = build_open_box_block('FromDevice',
                                  config_fields=[
                                      ConfigField('devname', True, FieldType.STRING),
                                      ConfigField('sniffer', False, FieldType.BOOLEAN),
                                      ConfigField('promisc', False, FieldType.BOOLEAN),
                                  ],
                                  read_handlers=[
                                      HandlerField('count', FieldType.INTEGER),
                                      HandlerField('byte_count', FieldType.INTEGER),
                                      HandlerField('rate', FieldType.NUMBER),
                                      HandlerField('byte_rate', FieldType.INTEGER),
                                      HandlerField('drops', FieldType.STRING),
                                  ],
                                  write_handlers=[
                                      HandlerField('reset_counts', FieldType.NULL)
                                  ])

FromDump = build_open_box_block('FromDump',
                                config_fields=[
                                    ConfigField('filename', True, FieldType.STRING),
                                    ConfigField('timing', False, FieldType.BOOLEAN),
                                    ConfigField('active', False, FieldType.BOOLEAN),
                                ],
                                read_handlers=[
                                    HandlerField('count', FieldType.INTEGER),
                                    HandlerField('byte_count', FieldType.INTEGER),
                                    HandlerField('rate', FieldType.NUMBER),
                                    HandlerField('byte_rate', FieldType.INTEGER),
                                    HandlerField('drops', FieldType.STRING),
                                ],
                                write_handlers=[
                                    HandlerField('reset_counts', FieldType.NULL),
                                    HandlerField('active', FieldType.BOOLEAN)
                                ])

Discard = build_open_box_block('Discard',
                               config_fields=[
                               ],
                               read_handlers=[
                                   HandlerField('count', FieldType.INTEGER),
                                   HandlerField('byte_count', FieldType.INTEGER),
                                   HandlerField('rate', FieldType.NUMBER),
                                   HandlerField('byte_rate', FieldType.NUMBER),
                                   HandlerField('drops', FieldType.STRING),
                               ],
                               write_handlers=[
                                   HandlerField('reset_counts', FieldType.NULL),
                                   HandlerField('active', FieldType.BOOLEAN)
                               ])

ToDump = build_open_box_block('ToDump',
                              config_fields=[
                                  ConfigField('filename', True, FieldType.STRING),
                              ])

Log = build_open_box_block('Log',
                           config_fields=[
                               ConfigField('message', True, FieldType.STRING),
                               ConfigField('severity', False, FieldType.INTEGER),
                               ConfigField('attach_packet', False, FieldType.BOOLEAN),
                               ConfigField('packet_size', False, FieldType.INTEGER),
                           ],
                           read_handlers=[
                           ],
                           write_handlers=[
                           ])

Alert = build_open_box_block('Alert',
                             config_fields=[
                                 ConfigField('message', True, FieldType.STRING),
                                 ConfigField('severity', False, FieldType.INTEGER),
                                 ConfigField('attach_packet', False, FieldType.BOOLEAN),
                                 ConfigField('packet_size', False, FieldType.INTEGER),
                             ],
                             read_handlers=[
                             ],
                             write_handlers=[
                             ])

ContentClassifier = build_open_box_block('ContentClassifier',
                                         config_fields=[
                                             ConfigField('pattern', True, FieldType.ARRAY)
                                         ],
                                         read_handlers=[
                                             HandlerField('count', FieldType.INTEGER),
                                             HandlerField('byte_count', FieldType.INTEGER),
                                             HandlerField('rate', FieldType.NUMBER),
                                             HandlerField('byte_rate', FieldType.NUMBER),
                                         ],
                                         write_handlers=[
                                             HandlerField('reset_counts', FieldType.NULL)
                                         ])

HeaderClassifier = build_open_box_block('HeaderClassifier',
                                        config_fields=[
                                            ConfigField('match', True, FieldType.MATCH_PATTERNS)
                                        ],
                                        read_handlers=[
                                            HandlerField('count', FieldType.INTEGER),
                                            HandlerField('byte_count', FieldType.INTEGER),
                                            HandlerField('rate', FieldType.NUMBER),
                                            HandlerField('byte_rate', FieldType.NUMBER),
                                        ],
                                        write_handlers=[
                                            HandlerField('reset_counts', FieldType.NULL)
                                        ])

RegexMatcher = build_open_box_block('RegexMatcher',
                                    config_fields=[
                                        ConfigField('pattern', True, FieldType.ARRAY),
                                        ConfigField('payload_only', False, FieldType.BOOLEAN),
                                        ConfigField('match_all', False, FieldType.BOOLEAN)
                                    ],
                                    read_handlers=[
                                        HandlerField('count', FieldType.INTEGER),
                                        HandlerField('byte_count', FieldType.INTEGER),
                                        HandlerField('rate', FieldType.NUMBER),
                                        HandlerField('byte_rate', FieldType.NUMBER),
                                        HandlerField('payload_only', FieldType.BOOLEAN),
                                        HandlerField('match_all', FieldType.BOOLEAN),
                                    ],
                                    write_handlers=[
                                        HandlerField('reset_counts', FieldType.NULL),
                                        HandlerField('payload_only', FieldType.BOOLEAN),
                                        HandlerField('match_all', FieldType.BOOLEAN),
                                    ]
                                    )

RegexClassifier = build_open_box_block('RegexClassifier',
                                       config_fields=[
                                           ConfigField('pattern', True, FieldType.ARRAY),
                                           ConfigField('payload_only', False, FieldType.BOOLEAN),
                                       ],
                                       read_handlers=[
                                           HandlerField('count', FieldType.INTEGER),
                                           HandlerField('byte_count', FieldType.INTEGER),
                                           HandlerField('rate', FieldType.NUMBER),
                                           HandlerField('byte_rate', FieldType.NUMBER),
                                           HandlerField('payload_only', FieldType.BOOLEAN),
                                       ],
                                       write_handlers=[
                                           HandlerField('reset_counts', FieldType.NULL),
                                           HandlerField('payload_only', FieldType.BOOLEAN),
                                       ]
                                       )

VlanDecapsulate = build_open_box_block('VlanDecapsulate')

VlanEncapsulate = build_open_box_block('VlanEncapsulate',
                                       config_fields=[
                                           ConfigField('vlan_vid', True, FieldType.INTEGER),
                                           ConfigField('vlan_dei', False, FieldType.INTEGER),
                                           ConfigField('vlan_pcp', False, FieldType.INTEGER),
                                           ConfigField('ethertype', False, FieldType.INTEGER),
                                       ],
                                       read_handlers=[
                                           HandlerField('vlan_vid', FieldType.INTEGER),
                                           HandlerField('vlan_dei', FieldType.INTEGER),
                                           HandlerField('vlan_pcp', FieldType.INTEGER),
                                           HandlerField('vlan_tci', FieldType.INTEGER),
                                           HandlerField('ethertype', FieldType.INTEGER),
                                       ],
                                       write_handlers=[
                                           HandlerField('vlan_vid', FieldType.INTEGER),
                                           HandlerField('vlan_dei', FieldType.INTEGER),
                                           HandlerField('vlan_pcp', FieldType.INTEGER),
                                           HandlerField('vlan_tci', FieldType.INTEGER),
                                           HandlerField('ethertype', FieldType.INTEGER),
                                       ])

DecIpTtl = build_open_box_block('DecIpTtl',
                                config_fields=[
                                    ConfigField('active', False, FieldType.BOOLEAN),
                                ],
                                read_handlers=[
                                    HandlerField('count', FieldType.INTEGER),
                                    HandlerField('byte_count', FieldType.INTEGER),
                                    HandlerField('rate', FieldType.NUMBER),
                                    HandlerField('byte_rate', FieldType.NUMBER),
                                    HandlerField('active', FieldType.BOOLEAN),
                                ],
                                write_handlers=[
                                    HandlerField('reset_counts', FieldType.NULL),
                                    HandlerField('active', FieldType.BOOLEAN),
                                ])

Ipv4AddressTranslator = build_open_box_block('Ipv4AddressTranslator',
                                             config_fields=[
                                                 ConfigField('input_spec', True, FieldType.IPV4_TRANSLATION_RULES),
                                                 ConfigField('tcp_done_timeout', False, FieldType.INTEGER),
                                                 ConfigField('tcp_nodata_timeout', False, FieldType.INTEGER),
                                                 ConfigField('tcp_guarantee', False, FieldType.INTEGER),
                                                 ConfigField('udp_timeout', False, FieldType.INTEGER),
                                                 ConfigField('udp_streaming_timeout', False, FieldType.INTEGER),
                                                 ConfigField('udp_guarantee', False, FieldType.INTEGER),
                                                 ConfigField('reap_interval', False, FieldType.INTEGER),
                                                 ConfigField('mapping_capacity', False, FieldType.INTEGER)
                                             ],
                                             read_handlers=[
                                                 HandlerField('mapping_count', FieldType.INTEGER),
                                                 HandlerField('mapping_failures', FieldType.INTEGER),
                                                 HandlerField('length', FieldType.INTEGER),
                                                 HandlerField('capacity', FieldType.INTEGER),
                                                 HandlerField('tcp_mapping', FieldType.STRING),
                                                 HandlerField('udp_mapping', FieldType.STRING),
                                             ],
                                             write_handlers=[
                                                 HandlerField('capacity', FieldType.INTEGER)
                                             ])

Queue = build_open_box_block('Queue',
                             config_fields=[
                                 ConfigField('capacity', False, FieldType.INTEGER),
                             ],
                             read_handlers=[
                                 HandlerField('length', FieldType.INTEGER),
                                 HandlerField('highwater_length', FieldType.INTEGER),
                                 HandlerField('drops', FieldType.INTEGER),
                                 HandlerField('capacity', FieldType.INTEGER),
                                 ],
                             write_handlers=[
                                 HandlerField('reset_counts', FieldType.INTEGER),
                                 HandlerField('reset', FieldType.INTEGER)
                             ]
                             )

NetworkDirectionSwap = build_open_box_block('NetworkDirectionSwap',
                                            config_fields=[
                                                ConfigField('ethernet', False, FieldType.BOOLEAN),
                                                ConfigField('ipv4', False, FieldType.BOOLEAN),
                                                ConfigField('ipv6', False, FieldType.BOOLEAN),
                                                ConfigField('tcp', False, FieldType.BOOLEAN),
                                                ConfigField('udp', False, FieldType.BOOLEAN),
                                            ],
                                            read_handlers=[
                                                HandlerField('ethernet', FieldType.BOOLEAN),
                                                HandlerField('ipv4', FieldType.BOOLEAN),
                                                HandlerField('ipv6', FieldType.BOOLEAN),
                                                HandlerField('tcp', FieldType.BOOLEAN),
                                                HandlerField('udp', FieldType.BOOLEAN),
                                            ],
                                            write_handlers=[
                                                HandlerField('ethernet', FieldType.BOOLEAN),
                                                HandlerField('ipv4', FieldType.BOOLEAN),
                                                HandlerField('ipv6', FieldType.BOOLEAN),
                                                HandlerField('tcp', FieldType.BOOLEAN),
                                                HandlerField('udp', FieldType.BOOLEAN),
                                            ])

