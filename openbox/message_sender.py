"""
Send messages to OBC
"""
import socket

from tornado import gen
from tornado.queues import Queue
from tornado.httpclient import AsyncHTTPClient, HTTPError

import config


class MessageSender(object):
    def __init__(self):
        self._queue = Queue()
        self._client = AsyncHTTPClient()

    @gen.coroutine
    def send_message(self, message):
        yield self._client.fetch(
            config.OpenBoxController.MESSAGE_ENDPOINT_PATTERN.format(message=message.type),
            method='POST',
            user_agent='OBSI',
            headers={'Content-Type': 'application/json'},
            body=message.to_json())

    @gen.coroutine
    def send_message_ignore_response(self, message):
        try:
            response = yield self.send_message(message)
            raise gen.Return(True)
        except HTTPError:
            raise gen.Return(False)
        except socket.error:
            raise gen.Return(False)

