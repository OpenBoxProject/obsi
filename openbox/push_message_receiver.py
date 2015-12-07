#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################

"""
An implementation of an Execution Engine Push Message Receiver.
"""
import json
import socket
import time

from tornado import gen, locks
from tornado.iostream import IOStream
from tornado.ioloop import IOLoop


class PushMessageHandler(object):
    def __init__(self, sender, buffer_size=1, buffer_timeout=0):
        self.sender = sender
        self.buffer_size = buffer_size
        self.buffer_timeout = buffer_timeout
        self._buffered_messages = []
        self._buffered_messages_lock = locks.Lock()
        self._flush_timer = None
        self._id = 0


    @gen.coroutine
    def add(self, message):
        # after decoding the JSON we get a dict with the message, specific format is different for each type
        # We need to add an ID and timestamp for the message
        message = json.loads(message)
        message['timestamp'] = time.time()
        message['id'] = self._id
        self._id += 1
        with (yield self._buffered_messages_lock.acquire()):
            self._buffered_messages.append(message)
            need_to_flush = len(self._buffered_messages) >= self.buffer_size
            first_message = len(self._buffered_messages) == 1
        if need_to_flush:
            yield self._flush_buffer()
        elif first_message:
            self._flush_timer = IOLoop.current().call_later(self.buffer_timeout, self._flush_buffer)

    @gen.coroutine
    def _flush_buffer(self):
        if self._flush_timer:
            IOLoop.current().remove_timeout(self._flush_timer)
        with (yield self._buffered_messages_lock.acquire()):
            messages = self._buffered_messages[:]
            self._buffered_messages = []

        yield self.sender(messages)

    def close(self):
        IOLoop.current().remove_timeout(self._flush_timer)


class PushMessageReceiver(object):
    def __init__(self):
        self.connected = False
        self._stream = None
        self.address = None
        self.family = None
        self.delayed_call = None
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

    def connect(self, address, family=socket.AF_INET, retry_interval=1):
        self.address = address
        self.family = family
        self.retry_interval = retry_interval
        self._connect()

    def _connect(self):
        if self.connected:
            if self.delayed_call:
                IOLoop.current().remove_timeout(self.delayed_call)
                self.delayed_call = None
            else:
                raise RuntimeError("Already connected")
        else:
            self.delayed_call = IOLoop.current().call_later(1, self._connect)
            stream_socket = socket.socket(family=self.family)
            self._stream = IOStream(stream_socket)
            self._stream.connect(self.address, self._on_connect)

    def _on_connect(self):
        self.connected = True
        self._stream.set_close_callback(self._on_closed)
        self._stream.read_until('\n', self._handle_greeting)

    def _on_closed(self):
        if self.connected:
            # The other side closed us, try to reconnect
            self.connected = False
            self.connect(self.address, self.family)

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
        if self._stream:
            self.connected = False
            self._stream.close()
            self._stream = None

if __name__ == "__main__":
    receiver = PushMessageReceiver()

    def log_handler(msg):
        print msg

    receiver.register_message_handler('LOG', log_handler)
    receiver.connect(address=('127.0.0.1', 7001))
    IOLoop.current().start()
