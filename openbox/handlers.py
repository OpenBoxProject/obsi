"""
Endpoint handlers for the REST server
"""
from tornado.web import RequestHandler, HTTPError
from tornado.escape import json_decode


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