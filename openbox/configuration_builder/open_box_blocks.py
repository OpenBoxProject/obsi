from collections import OrderedDict
import json


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


class BlockError(Exception):
    """
    Base for all Block related errors
    """
    pass


class OpenBoxBlockConfigurationError(BlockError):
    """
    An error in an OpenBox Block configuration
    """
    pass


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
        clazz = cls.blocks_registry.get(element_type)
        if clazz is None:
            raise OpenBoxBlockConfigurationError("Unknown block type %s" % block_type)
        name = config.pop('name')
        if name is None:
            raise OpenBoxBlockConfigurationError("A block must have an instance name")
        return clazz(name, **config)

    @classmethod
    def to_json_schema(cls, **kwargs):
        schema = OrderedDict()
        schema['type'] = cls.__name__
        schema['configuration'] = [field.to_dict() for field in cls.__fields__]
        schema['read_handlers'] = [field.to_dict() for field in cls.__read_handlers__]
        schema['write_handlers'] = [field.to_dict() for field in cls.__write_handlers__]
        return json.dumps(schema, **kwargs)


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

FromDevice = build_open_box_block('FromDevice',
                                  [ConfigField('devname', True, FieldType.STRING),
                                   ConfigField('sniffer', False, FieldType.BOOLEAN),
                                   ConfigField('promisc', False, FieldType.BOOLEAN),
                                   ],
                                  [HandlerField('count', FieldType.INTEGER),
                                   HandlerField('byte_count', FieldType.INTEGER),
                                   HandlerField('rate', FieldType.NUMBER),
                                   HandlerField('byte_rate', FieldType.INTEGER),
                                   HandlerField('drops', FieldType.STRING),
                                   ],
                                  [HandlerField('reset_count', FieldType.NULL)])
