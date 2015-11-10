import tornado.web
import tornado.httpclient
import tornado.ioloop
import tornado.options
from control.handlers import (EnginesRequestHandler, CloseRequestHandler, ConfigRequestHandler,
                              ConnectRequestHandler, ElementRequestHandler, EngineVersionRequestHandler,
                              ListElementsRequestHandler, IsReadableRequestHandler, IsWriteableRequestHandler,
                              LoadedPackagesRequestHandler, SequenceRequestHandler, SupportedElementsRequestHandler)
from control.config import RestServer, ENGINES


class ServerControl(object):
    def __init__(self):
        self.engine = None
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


def run(port, debug=False):
    server_control = ServerControl()
    application = tornado.web.Application([
        (RestServer.Endpoints.ENGINES, EnginesRequestHandler, dict(control=server_control)),
        (RestServer.Endpoints.CONNECT, ConnectRequestHandler, dict(control=server_control)),
        (RestServer.Endpoints.CLOSE, CloseRequestHandler, dict(control=server_control)),
        (RestServer.Endpoints.ENGINE_VERSION, EngineVersionRequestHandler, dict(control=server_control)),
        (RestServer.Endpoints.LOADED_PACKAGES, LoadedPackagesRequestHandler, dict(control=server_control)),
        (RestServer.Endpoints.SUPPORTED_ELEMENTS, SupportedElementsRequestHandler, dict(control=server_control)),
        (RestServer.Endpoints.CONFIG, ConfigRequestHandler, dict(control=server_control)),
        (RestServer.Endpoints.LIST_ELEMENTS, ListElementsRequestHandler, dict(control=server_control)),
        (RestServer.Endpoints.IS_READABLE, IsReadableRequestHandler, dict(control=server_control)),
        (RestServer.Endpoints.IS_WRITEABLE, IsWriteableRequestHandler, dict(control=server_control)),
        (RestServer.Endpoints.HANDLER, ElementRequestHandler, dict(control=server_control)),
        (RestServer.Endpoints.LIST_HANDLERS, ElementRequestHandler, dict(control=server_control)),
        (RestServer.Endpoints.SEQUENCE, SequenceRequestHandler, dict(control=server_control)),
        ], debug=debug)
    application.listen(port)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    tornado.options.define('port', default=RestServer.PORT, type=int, help="The server's port. ")
    tornado.options.define('debug', default=False, type=bool, help='Start the server with debug options.')
    tornado.options.parse_command_line()
    run(tornado.options.options.port, tornado.options.options.debug)
