#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################

from collections import OrderedDict
import socket
import tornado.web
import tornado.escape
from control_exceptions import ControlError


class BaseControlRequestHandler(tornado.web.RequestHandler):
    def initialize(self, control):
        self.control = control

    def _decode_json_body(self):
        body = self.request.body
        if not body:
            raise tornado.web.HTTPError(400, reason="Received no body content")
        return tornado.escape.json_decode(body)

    def _engine(self):
        if not self.control.engine_set:
            raise tornado.web.HTTPError(400, reason="Execution engine not set")
        return self.control.engine

    def _write(self, value):
        self.write(tornado.escape.json_encode(value))


class EnginesRequestHandler(BaseControlRequestHandler):
    def get(self):
        engines = self.control.get_supported_engines()
        self._write(engines)

    def post(self, *args, **kwargs):
        engine_name = tornado.escape.json_decode(self.request.body)
        if not self.control.engine_set:
            self._set_engine(engine_name)
        else:
            raise tornado.web.HTTPError(400, reason="Engine already set")

    def _set_engine(self, engine):
        if not self.control.set_engine(engine):
            raise tornado.web.HTTPError(400, reason="Unknown engine (%s) request" % engine)


class ConnectRequestHandler(BaseControlRequestHandler):
    def post(self, *args, **kwargs):
        engine = self.control.engine
        params = self._decode_json_body()
        try:
            address = params['address']
            socket_type = params['type']
        except KeyError:
            raise tornado.web.HTTPError(400, reason="Wrong arguments for connect")
        if socket_type == 'TCP':
            family = socket.AF_INET
            address = tuple(address)
        else:
            family = socket.AF_UNIX
        if engine.connected:
            raise tornado.web.HTTPError(400, reason="Already connected")
        engine.connect(address, family)


class CloseRequestHandler(BaseControlRequestHandler):
    def post(self, *args, **kwargs):
        engine = self.control.engine
        engine.close()


class EngineVersionRequestHandler(BaseControlRequestHandler):
    def get(self, *args, **kwargs):
        engine = self.control.engine
        if not self.control.engine.connected:
            raise tornado.web.HTTPError(400, reason="Not connected")
        try:
            self._write(engine.engine_version())
        except ControlError as e:
            raise tornado.web.HTTPError(500, reason=e.message)


class LoadedPackagesRequestHandler(BaseControlRequestHandler):
    def get(self, *args, **kwargs):
        engine = self.control.engine
        if not self.control.engine.connected:
            raise tornado.web.HTTPError(400, reason="Not connected")
        try:
            self._write(engine.loaded_packages())
        except ControlError as e:
            raise tornado.web.HTTPError(500, reason=e.message)


class SupportedElementsRequestHandler(BaseControlRequestHandler):
    def get(self, *args, **kwargs):
        engine = self.control.engine
        if not self.control.engine.connected:
            raise tornado.web.HTTPError(400, reason="Not connected")
        try:
            self._write(engine.supported_elements())
        except ControlError as e:
            raise tornado.web.HTTPError(500, reason=e.message)


class ConfigRequestHandler(BaseControlRequestHandler):
    def get(self, *args, **kwargs):
        engine = self.control.engine
        if not self.control.engine.connected:
            raise tornado.web.HTTPError(400, reason="Not connected")
        try:
            self._write(engine.running_config())
        except ControlError as e:
            raise tornado.web.HTTPError(500, reason=e.message)

    def post(self, *args, **kwargs):
        engine = self.control.engine
        if not self.control.engine.connected:
            raise tornado.web.HTTPError(400, reason="Not connected")
        new_config = self._decode_json_body()
        try:
            engine.hotswap(new_config)
        except ControlError as e:
            raise tornado.web.HTTPError(500, reason=e.message)


class ListElementsRequestHandler(BaseControlRequestHandler):
    def get(self, *args, **kwargs):
        engine = self.control.engine
        if not self.control.engine.connected:
            raise tornado.web.HTTPError(400, reason="Not connected")
        try:
            self._write(engine.elements_names())
        except ControlError as e:
            raise tornado.web.HTTPError(500, reason=e.message)


class IsReadableRequestHandler(BaseControlRequestHandler):
    def get(self, element_name, handler_name):
        element_name = tornado.escape.url_unescape(element_name)
        handler_name = tornado.escape.url_unescape(handler_name)
        engine = self.control.engine
        if not self.control.engine.connected:
            raise tornado.web.HTTPError(400, reason="Not connected")
        try:
            self._write(engine.is_readable_handler(element_name, handler_name))
        except ControlError as e:
            raise tornado.web.HTTPError(500, reason=e.message)


class IsWriteableRequestHandler(BaseControlRequestHandler):
    def get(self, element_name, handler_name):
        element_name = tornado.escape.url_unescape(element_name)
        handler_name = tornado.escape.url_unescape(handler_name)
        engine = self.control.engine
        if not self.control.engine.connected:
            raise tornado.web.HTTPError(400, reason="Not connected")
        try:
            self._write(engine.is_writeable_handler(element_name, handler_name))
        except ControlError as e:
            raise tornado.web.HTTPError(500, reason=e.message)


class ElementRequestHandler(BaseControlRequestHandler):
    def get(self, element_name, handler_name=None):
        element_name = tornado.escape.url_unescape(element_name)
        engine = self.control.engine
        if not engine.connected:
            raise tornado.web.HTTPError(400, reason="Not connected")

        if handler_name is None:
            # list handlers for an element
            try:
                self._write(engine.element_handlers(element_name))
            except ControlError as e:
                raise tornado.web.HTTPError(500, reason=e.message)
        else:
            handler_name = tornado.escape.url_unescape(handler_name)
            if not self.request.body:
                params = ''
            else:
                params = tornado.escape.json_decode(self.request.body)

            try:
                self._write(engine.read_handler(element_name, handler_name, params))
            except ControlError as e:
                raise tornado.web.HTTPError(500, reason=e.message)

    def post(self, element_name, handler_name):
        element_name = tornado.escape.url_unescape(element_name)
        handler_name = tornado.escape.url_unescape(handler_name)
        if not self.request.body:
            params = ''
        else:
            params = tornado.escape.json_decode(self.request.body)

        engine = self.control.engine
        if not self.control.engine.connected:
            raise tornado.web.HTTPError(400, reason="Not connected")

        try:
            self._write(engine.write_handler(element_name, handler_name, params))
        except ControlError as e:
            raise tornado.web.HTTPError(500, reason=e.message)


class SequenceRequestHandler(BaseControlRequestHandler):
    def post(self, *args, **kwargs):
        engine = self.control.engine
        if not self.control.engine.connected:
            raise tornado.web.HTTPError(400, reason="Not connected")
        operations = self._decode_json_body()
        results = engine.operations_sequence(operations)
        fixed_up = OrderedDict()
        # fix up results which has exceptions\
        for k, v in results.iteritems():
            if v is None:
                # None is return for successful write operations
                fixed_up[k] = True
            elif isinstance(v, Exception):
                # an exception is returned in case of read/write failure
                fixed_up[k] = False
            else:
                # the rest of the results
                fixed_up[k] = v
        self._write(fixed_up)
