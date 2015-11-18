from tornado import gen
from tornado.queues import Queue
import errors
from messages import MessageMeta, Message, Error


class MessageRouter(object):
    def __init__(self, message_sender, default_handler=None):
        self._queue = Queue()
        self.message_sender = message_sender
        self.default_handler = default_handler
        self._message_handlers = {}
        self._working = False

    def register_message_handler(self, message, handler):
        assert isinstance(message, MessageMeta)
        assert hasattr(handler, '__call__')
        self._message_handlers[message.__name__] = handler

    @gen.coroutine
    def put_message(self, message):
        assert isinstance(message, Message)
        yield self._queue.put(message)

    @gen.coroutine
    def start(self):
        self._working = True
        while self._working:
            message = yield self._queue.get()
            try:
                # TODO: Maybe we need to add special handling for BarrierRequest
                handler = self._message_handlers.get(message.type, self.default_handler)
                if handler:
                    yield handler(message)
            except Exception as e:
                error_type, error_subtype, error_message, extended_message = errors.exception_to_error_args(e)
                error_message = Error.from_request(message, error_type=error_type, error_subtype=error_subtype,
                                                   message=error_message, extended_message=extended_message)
                yield self.message_sender.send_message_ignore_response(error_message)
            finally:
                self._queue.task_done()

    def stop(self):
        self._working = False