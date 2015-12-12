#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################

import tornado.web
import tornado.escape
import config
from runner_exceptions import EngineClientError


class BaseRunnerRequestHandler(tornado.web.RequestHandler):
    def initialize(self, runner):
        self.runner = runner

    def _decode_json_body(self):
        body = self.request.body
        if not body:
            raise tornado.web.HTTPError(400, reason="Received no body content")
        return tornado.escape.json_decode(body)

    def _engine(self):
        if not self.runner.engine_set:
            raise tornado.web.HTTPError(400, reason="Execution engine not set")
        return self.runner.engine

    def _write(self, value):
        self.write(tornado.escape.json_encode(value))


class EnginesRequestHandler(BaseRunnerRequestHandler):
    def get(self):
        engines = self.runner.get_supported_engines()
        self._write(engines)

    def post(self, *args, **kwargs):
        engine_name = tornado.escape.json_decode(self.request.body)
        if not self.runner.engine_set:
            self._set_engine(engine_name)
        else:
            raise tornado.web.HTTPError(400, reason="Engine already set")

    def _set_engine(self, engine):
        if not self.runner.set_engine(engine):
            raise tornado.web.HTTPError(400, reason="Unknown engine (%s) request" % engine)


class StartRequestHandler(BaseRunnerRequestHandler):
    def post(self, *args, **kwargs):
        raw_parameters = self._decode_json_body()
        parameters = self._canonize_start_parameters(raw_parameters)
        engine = self._engine()
        try:
            started = engine.start(**parameters)
        except EngineClientError as e:
            raise tornado.web.HTTPError(400, reason=e.message)
        if not started:
            errors = engine.get_errors()
            raise tornado.web.HTTPError(500, reason="Unable to start execution engine: {errors}".format(errors=errors))

    def _canonize_start_parameters(self, raw_parameters):
        parameters = {}
        for param in config.RestServer.ENGINE_START_PARAMETERS:
            parameters[param] = raw_parameters.get(param, None)
        return parameters


class SuspendRequestHandler(BaseRunnerRequestHandler):
    def post(self, *args, **kwargs):
        engine = self._engine()
        try:
            engine.suspend()
        except EngineClientError as e:
            raise tornado.web.HTTPError(400, reason=e.message)


class ResumeRequestHandler(BaseRunnerRequestHandler):
    def post(self, *args, **kwargs):
        engine = self._engine()
        try:
            engine.resume()
        except EngineClientError as e:
            raise tornado.web.HTTPError(400, reason=e.message)


class StopRequestHandler(BaseRunnerRequestHandler):
    def post(self, *args, **kwargs):
        engine = self._engine()
        try:
            engine.stop()
        except EngineClientError:
            pass


class RunningRequestHandler(BaseRunnerRequestHandler):
    def get(self, *args, **kwargs):
        engine = self._engine()
        self.write(tornado.escape.json_encode(engine.is_running()))


class MemoryRequestHandler(BaseRunnerRequestHandler):
    def get(self, *args, **kwargs):
        try:
            engine = self._engine()
            mem_info = engine.memory_info()
            mem_percent = engine.memory_percent()
            self._write(dict(rss=mem_info.rss, vms=mem_info.vms, percent=mem_percent))
        except EngineClientError as e:
            raise tornado.web.HTTPError(400, reason=e.message)


class CpuRequestHandler(BaseRunnerRequestHandler):
    def get(self, *args, **kwargs):
        try:
            engine = self._engine()
            cpu_count = engine.cpu_count()
            nthreads = engine.num_threads()
            cpu_times = engine.cpu_times()
            cpu_percent, measurement_time = engine.cpu_percent()
            self._write(dict(cpu_count=cpu_count, nthreads=nthreads, cpu_user_time=cpu_times.user,
                             cpu_system_time=cpu_times.system, cpu_percent=cpu_percent,
                             measurement_time=measurement_time))
        except EngineClientError as e:
            raise tornado.web.HTTPError(400, reason=e.message)


class UptimeRequestHandler(BaseRunnerRequestHandler):
    def get(self, *args, **kwargs):
        try:
            engine = self._engine()
            uptime = engine.uptime()
            self._write(dict(uptime=uptime))
        except EngineClientError as e:
            raise tornado.web.HTTPError(400, reason=e.message)


class InstallPackageRequestHandler(BaseRunnerRequestHandler):
    def get(self, *args, **kwargs):
        try:
            engine = self._engine()
            packages = engine.installed_packages()
            self._write(packages)
        except EngineClientError as e:
            raise tornado.web.HTTPError(400, reason=e.message)

    def post(self):
        try:
            engine = self._engine()
            package = self._decode_json_body()
            engine.install_package(package['name'], package['data'].decode(package['encoding']))
        except EngineClientError as e:
            raise tornado.web.HTTPError(400, reason=e.message)


class RegisterAlertUrlRequestHandler(BaseRunnerRequestHandler):
    def post(self, *args, **kwargs):
        body = self.request.body
        if not body:
            raise tornado.web.HTTPError(400, reason="Received no body content")
        url = tornado.escape.url_unescape(body)
        self.runner.set_alert_url(url)
