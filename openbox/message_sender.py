#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################

"""
Send messages to OBC
"""
import config
import socket

from tornado import gen
from tornado.queues import Queue
from tornado.httpclient import AsyncHTTPClient, HTTPError


class MessageSender(object):
    def __init__(self):
        self._queue = Queue()
        self._client = AsyncHTTPClient()

    @gen.coroutine
    def send_message(self, message, url=None):
        url = url or config.OpenBoxController.MESSAGE_ENDPOINT_PATTERN.format(message=message.type)
        yield self._client.fetch(url, method='POST', user_agent='OBSI', headers={'Content-Type': 'application/json'},
                                 body=message.to_json())

    @gen.coroutine
    def send_message_ignore_response(self, message, url=None):
        try:
            response = yield self.send_message(message, url)
            raise gen.Return(True)
        except HTTPError:
            raise gen.Return(False)
        except socket.error:
            raise gen.Return(False)

    @gen.coroutine
    def send_push_messages(self, push_message_class, dpid, url, buffered_messages):
        message = push_message_class(origin_dpid=dpid, messages=buffered_messages)
        yield self.send_message_ignore_response(message, url)

