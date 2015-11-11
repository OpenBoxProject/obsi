import tornado.web
import tornado.httpclient
import tornado.ioloop
import tornado.options
from handlers import (EnginesRequestHandler, StartRequestHandler, StopRequestHandler, SuspendRequestHandler,
                             ResumeRequestHandler, RunningRequestHandler, MemoryRequestHandler, CpuRequestHandler,
                             RegisterAlertUrlRequestHandler)
from config import RestServer, ENGINES


class ServerRunner(object):
    def __init__(self):
        self.engine = None
        self.url = None
        self._http_client = tornado.httpclient.AsyncHTTPClient()

    def get_supported_engines(self):
        return ENGINES.keys()

    def set_alert_url(self, url):
        self.url = url

    def set_engine(self, engine_name):
        try:
            engine_client_class, client_config = ENGINES[engine_name]
            self.engine = engine_client_class(**client_config)
            return True
        except KeyError:
            return False

    @property
    def engine_set(self):
        return self.engine is not None

    def alert_engine_is_not_running(self):
        if not self.url or not self.engine_set or self.engine.is_running:
            return
        errors = self.engine.get_errors()
        self._http_client.fetch(self.url, method='POST', body=errors)


def run(port, debug=False):
    server_runner = ServerRunner()
    application = tornado.web.Application([
        (RestServer.Endpoints.ENGINES, EnginesRequestHandler, dict(runner=server_runner)),
        (RestServer.Endpoints.START, StartRequestHandler, dict(runner=server_runner)),
        (RestServer.Endpoints.SUSPEND, SuspendRequestHandler, dict(runner=server_runner)),
        (RestServer.Endpoints.RESUME, ResumeRequestHandler, dict(runner=server_runner)),
        (RestServer.Endpoints.STOP, StopRequestHandler, dict(runner=server_runner)),
        (RestServer.Endpoints.RUNNING, RunningRequestHandler, dict(runner=server_runner)),
        (RestServer.Endpoints.MEMORY, MemoryRequestHandler, dict(runner=server_runner)),
        (RestServer.Endpoints.CPU, CpuRequestHandler, dict(runner=server_runner)),
        (RestServer.Endpoints.REGISTER_ALERT_URL, RegisterAlertUrlRequestHandler, dict(runner=server_runner)),
        ], debug=debug)
    sched = tornado.ioloop.PeriodicCallback(server_runner.alert_engine_is_not_running, RestServer.CLIENT_RUN_POLLING_INTERVAL)
    application.listen(port)
    sched.start()
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    tornado.options.define('port', default=RestServer.PORT, type=int, help="The server's port. ")
    tornado.options.define('debug', default=False, type=bool, help='Start the server with debug options.')
    tornado.options.parse_command_line()
    run(tornado.options.options.port, tornado.options.options.debug)
