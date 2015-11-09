"""
An implementation of an Execution Engine Push Message Receiver.
"""
import json
import socket
from tornado.iostream import IOStream


class PushMessageReceiver(object):
    def __init__(self):
        self.connected = False
        self._stream = None
        self._registered_handlers = {}

    def register_message_handler(self, message_type, handler):
        self._registered_handlers[message_type] = handler

    def unregister_message_handler(self, message_type):
        try:
            del self._registered_handlers[message_type]
        except KeyError:
            pass

    def unregister_all(self):
        self._registered_handlers = {}

    def connect(self, tcp_address=None, unix_filename=None):
        if tcp_address is None and unix_filename is None:
            raise ValueError("At least one type of endpoint must be set")
        if self.connected:
            raise RuntimeError("Already connected")
        if tcp_address:
            stream_socket = socket.socket(family=socket.AF_INET)
            address = tcp_address
        else:
            stream_socket = socket.socket(family=socket.AF_UNIX)
            address = unix_filename
        self._stream = IOStream(stream_socket)
        self._stream.connect(address, self._on_connect)

    def _on_connect(self):
        self.connected = True
        self._stream.read_until('\n', self._handle_greeting)

    def _handle_greeting(self, greetings):
        self._stream.read_until('\n', self._handle_message)

    def _handle_message(self, raw_message):
        message = json.loads(raw_message.strip())
        try:
            handler = self._registered_handlers[message['type']]
            handler(message['content'])
        except KeyError:
            pass
        finally:
            # continue getting messages as long as we are connected
            if self.connected:
                self._stream.read_until('\n', self._handle_message)

    def close(self):
        self._stream.close()
        self.connected = False
        self._stream = None

if __name__ == "__main__":
    import tornado.ioloop
    receiver = PushMessageReceiver()
    counter = 0

    def log_handler(msg):
        global counter
        counter += 1

    def print_counter():
        print counter

    receiver.register_message_handler('LOG', log_handler)
    receiver.connect(tcp_address=('127.0.0.1', 7001))
    io_loop = tornado.ioloop.IOLoop.instance()
    io_loop.call_later(1, print_counter)
    io_loop.start()

