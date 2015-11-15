"""
Send messages to OBC
"""
from tornado import gen
from tornado.queues import Queue
from tornado.httpclient import AsyncHTTPClient

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

