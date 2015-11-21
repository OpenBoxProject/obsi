from collections import OrderedDict
import json

from configuration_builder_exceptions import OpenBoxBlockConfigurationError


class FieldType:
    BOOLEAN = 'boolean'
    ARRAY = 'array'
    INTEGER = 'integer'
    NUMBER = 'number'
    NULL = 'null'
    OBJECT = 'object'
    STRING = 'string'


class ConfigField(object):
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
                    raise TypeError("Field {field} must be of type {rtype} and not {wtype}".format(field=field.name,
                                                                                                   rtype=field.type,
                                                                                                   wtype=type(value)))
                setattr(self, field.name, value)
            except KeyError:
                if field.required:
                    raise ValueError("Required field {field} not given".format(field=field.name))

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
            if value:
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
                                      HandlerField('reset_count', FieldType.NULL)
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
                                    HandlerField('reset_count', FieldType.NULL),
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
                                   HandlerField('reset_count', FieldType.NULL),
                                   HandlerField('active', FieldType.BOOLEAN)
                               ])

ToDump = build_open_box_block('ToDump',
                              config_fields=[
                                  ConfigField('filename', True, FieldType.STRING),
                              ],
                              read_handlers=[
                              ],
                              write_handlers=[
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
                                             HandlerField('reset_count', FieldType.NULL)
                                         ])