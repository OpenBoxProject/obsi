"""
The REST Server used to get messages
"""
import config
from tornado.web import Application
from handlers import (RunnerAlertRequestHandler)


def start(manager):
    application = Application([
        (config.RestServer.Endpoints.RUNNER_ALERT, RunnerAlertRequestHandler, dict(manager=manager))
    ], debug=config.RestServer.DEBUG)
    application.listen(config.RestServer.PORT)