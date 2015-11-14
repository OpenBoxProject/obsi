from tornado import gen
from tornado.queues import Queue
from messages import MessageMeta, Message


class MessageRouter(object):
    def __init__(self):
        self._queue = Queue()
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
                handler = self._message_handlers[message.type]
                yield handler(message)
            finally:
                self._queue.task_done()

    def stop(self):
        self._working = False