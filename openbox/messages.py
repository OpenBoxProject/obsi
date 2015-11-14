"""
Messages between OBC and OBI
"""

import json


class MessageParsingError(Exception):
    pass


class MessageMeta(type):
    def __init__(cls, name, bases, dct):
        if not hasattr(cls, "messages_registry"):
            # this is the base class. Create an empty registry
            cls.messages_registry = {}
        else:
            # this is the derived class. Add cls to the registry
            cls.messages_registry[name] = cls

        super(MessageMeta, cls).__init__(name, bases, dct)


class Message(object):
    """
    The base class for all messages.

    Messages shouldn't derive from this class directly but from of it's subclasses.
    """
    __metaclass__ = MessageMeta

    # a list of the fields in the message, no need to put the 'type' field
    __slots__ = ['xid']

    # Global XID counter
    XID = 0

    def __init__(self, **kwargs):
        if 'xid' not in kwargs:
            kwargs['xid'] = Message.XID
            Message.XID += 1

        for field in self.__slots__:
            try:
                setattr(self, field, kwargs[field])
            except KeyError:
                raise TypeError("Field %s, not given" % field)

    @classmethod
    def from_json(cls, raw_data):
        obj = json.loads(raw_data)
        try:
            msg_type = obj.pop('type')
            clazz = cls.messages_registry[msg_type]
        except KeyError:
            raise MessageParsingError("Unknown Message Type" % raw_data)

        try:
            return clazz(**obj)
        except TypeError as e:
            raise MessageParsingError(e.message)

    def to_dict(self):
        return dict((field, getattr(self, field)) for field in self.__slots__)

    def to_json(self):
        obj_dict = self.to_dict()
        obj_dict['type'] = self.__class__.__name__
        return json.dumps(obj_dict)

    def __str__(self):
        return self.to_json()


class MessageRequest(Message):
    """
    A request message.
    """
    pass


class MessageResponse(Message):
    """
    A response message
    """
    # The fields to copy from the request
    __copy_request_fields__ = ['xid']

    # The class of the allowed request type
    __request__ = MessageRequest

    @classmethod
    def from_request(cls, request, **kwargs):
        if not isinstance(request, cls.__request__):
            raise TypeError("Can create a response only from %s, and not %s" % (cls.__request__.__name__,
                                                                                request.__class__.__name__))
        for field in cls.__copy_request_fields__:
            kwargs[field] = getattr(request, field)
        return cls(**kwargs)


class Hello(MessageRequest):
    __slots__ = ['xid', 'dpid', 'version', 'capabilities']


class KeepAlive(MessageRequest):
    __slots__ = ['xid', 'dpid']


class ListCapabilitiesRequest(MessageRequest):
    __slots__ = ['xid', ]


class ListCapabilitiesResponse(MessageResponse):
    __slots__ = ['xid', 'capabilities']
    __request__ = ListCapabilitiesRequest


class GlobalStatsRequest(MessageRequest):
    __slots__ = ['xid']


class GlobalStatsResponse(MessageResponse):
    __slots__ = ['xid', 'stats']
    __request__ = GlobalStatsRequest


class GlobalStatsReset(MessageRequest):
    __slots__ = ['xid']


class ReadRequest(MessageRequest):
    __slots__ = ['xid', 'block_id', 'read_handle']


class ReadResponse(MessageResponse):
    __slots__ = ['xid', 'block_id', 'read_handle', 'result']
    __copy_request_fields__ = ['xid', 'block_id', 'read_handle']
    __request__ = ReadRequest


class WriteRequest(MessageRequest):
    __slots__ = ['xid', 'block_id', 'write_handle', 'value']


class WriteResponse(MessageResponse):
    __slots__ = ['xid', 'block_id', 'write_handle']
    __copy_request_fields__ = ['xid', 'block_id', 'write_handle']
    __request__ = WriteRequest


class SetProcessingGraphRequest(MessageRequest):
    __slots__ = ['xid', 'required_modules', 'block', 'connectors']


class SetProcessingGraphResponse(MessageResponse):
    __slots__ = ['xid']
    __request__ = SetProcessingGraphRequest


class BarrierRequest(MessageRequest):
    __slots__ = ['xid']


class Error(MessageResponse):
    __slots__ = ['xid', 'error_type', 'error_subtype', 'message', 'extended_message']


class AddCustomModuleRequest(MessageRequest):
    __slots__ = ['xid', 'module_name', 'module_content', 'content_type', 'content_transfer_encoding', 'translation']


class AddCustomModuleResponse(MessageResponse):
    __slots__ = ['xid']
    __request__ = AddCustomModuleRequest


class RemoveCustomModuleRequest(MessageRequest):
    __slots__ = ['xid', 'module_name']


class RemoveCustomModuleResponse(MessageResponse):
    __slots__ = ['xid']
