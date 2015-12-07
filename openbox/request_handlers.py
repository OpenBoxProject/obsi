#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################

"""
Endpoint handlers for the REST server
"""
from tornado.web import RequestHandler, HTTPError
from tornado.escape import json_decode
from messages import Message, MessageParsingError


class BaseRequestHandler(RequestHandler):
    def initialize(self, manager):
        self.manager = manager

    def _decoode_json_body(self):
        body = self.request.body
        if not body:
            raise HTTPError(400, reason="Received no body content")
        return json_decode(body)


class RunnerAlertRequestHandler(BaseRequestHandler):
    def post(self, *args, **kwargs):
        body = self._decoode_json_body()
        self.manager.handle_runner_alert(body)


class MessageRequestHandler(BaseRequestHandler):
    def post(self, message_type):
        message_dict = self._decoode_json_body()
        try:
            message = Message.from_dict(message_dict)
        except MessageParsingError as e:
            raise HTTPError(500, reason=e.message)
        if message_type != message.type:
            raise HTTPError(500, reason="Request message type {body_type} "
                                        "doesn't match URL {url_type}".format(body_type=message.type,
                                                                              url_type=message_type))
        self.manager.message_router.put_message(message)

