"""
The main configuration of the OBSI
"""
import os.path
import socket
import runner.config as runner_config
import control.config as control_config

BASE_PATH = os.path.dirname(os.path.realpath(__file__))


class Watchdog:
    CHECK_INTERVAL = 1000  # milliseconds


class RestServer:
    DEBUG = True
    PORT = 9000
    BASE_URI = 'http://localhost:{port}'.format(port=PORT)

    class Endpoints:
        RUNNER_ALERT = '/obsi/runner_alert'


class Engine:
    NAME = 'click'
    CONTROL_SOCKET_TYPE = 'TCP'
    CONTROL_SOCKET_ENDPOINT = 10001
    PUSH_MESSAGES_SOCKET_TYPE = 'TCP'
    PUSH_MESSAGES_SOCKET_ENDPOINT = 10002
    PUSH_MESSAGES_CHANNEL = 'openbox'
    NTHREADS = 2
    BASE_EMPTY_CONFIG = r'''ChatterSocket("{push_type}", {push_endpoint}, RETRIES 3, RETRY_WARNINGS false, CHANNEL {channel});
ControlSocket({control_type}, {control_endpoint}, RETRIES 3, RETRY_WARNINGS false);
require(package "openbox");
chatter_msg::ChatterMessage("EMPTY_KEEP_ALIVE", "message", CHANNEL {channel});
timed_source::TimedSource(1, "base");
discard::Discard();
timed_source -> chatter_msg -> discard'''.format(push_type=PUSH_MESSAGES_SOCKET_TYPE,
                                                 push_endpoint=PUSH_MESSAGES_SOCKET_ENDPOINT,
                                                 channel=PUSH_MESSAGES_CHANNEL,
                                                 control_type=CONTROL_SOCKET_TYPE,
                                                 control_endpoint=CONTROL_SOCKET_ENDPOINT)


class Runner:
    class Rest:
        BIN = os.path.join(BASE_PATH, 'runner', 'rest_server.py')
        DEBUG = True
        PORT = 9001
        BASE_URI = 'http://localhost:{port}'.format(port=PORT)
        Endpoints = runner_config.RestServer.Endpoints


class Control:
    class Rest:
        BIN = os.path.join(BASE_PATH, 'control', 'rest_server.py')
        DEBUG = True
        PORT = 9002
        BASE_URI = 'http://localhost:{port}'.format(port=PORT)
        Endpoints = control_config.RestServer.Endpoints

    SOCKET_TYPE = Engine.CONTROL_SOCKET_TYPE
    SOCKET_ADDRESS = (
        'localhost', Engine.CONTROL_SOCKET_ENDPOINT) if SOCKET_TYPE == 'TCP' else Engine.CONTROL_SOCKET_ENDPOINT


class PushMessages:
    SOCKET_FAMILY = socket.AF_INET if Engine.PUSH_MESSAGES_SOCKET_TYPE == 'TCP' else socket.AF_UNIX
    SOCKET_ADDRESS = (
        'localhost', Engine.PUSH_MESSAGES_SOCKET_ENDPOINT) if Engine.PUSH_MESSAGES_SOCKET_TYPE == 'TCP' else Engine.PUSH_MESSAGES_SOCKET_ENDPOINT
    RETRY_INTERVAL = 1