"""
A configuration and definitions file used by the EE runner server and client
"""
from control.click_control_client import ClickControlClient

ENGINES = {'click': (ClickControlClient, {})}


class RestServer:
    PORT = 9002
    DEBUG = True

    class Endpoints:
        ENGINES = '/control/engines'
        CONNECT = '/control/connect'
        CLOSE = '/control/close'
        ENGINE_VERSION = '/control/engine_version'
        LOADED_PACKAGES = '/control/loaded_packages'
        SUPPORTED_ELEMENTS = '/control/supported_elements'
        CONFIG = '/control/config'
        LIST_ELEMENTS = '/control/elements'
        IS_READABLE = '/control/elements/(.*)/(.*)/is_read'
        IS_WRITEABLE = '/control/elements/(.*)/(.*)/is_write'
        HANDLER = '/control/elements/(.*)/(.*)'
        LIST_HANDLERS = '/control/elements/(.*)'
        SEQUENCE = '/control/sequence'


