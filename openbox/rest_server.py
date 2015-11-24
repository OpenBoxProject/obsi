#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################

"""
The REST Server used to get messages
"""
import config
from tornado.web import Application
from request_handlers import (RunnerAlertRequestHandler, MessageRequestHandler)


def start(manager):
    application = Application([
        (config.RestServer.Endpoints.RUNNER_ALERT, RunnerAlertRequestHandler, dict(manager=manager)),
        (config.RestServer.Endpoints.MESSAGE, MessageRequestHandler, dict(manager=manager)),

    ], debug=config.RestServer.DEBUG)
    application.listen(config.RestServer.PORT)