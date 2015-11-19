"""
The main configuration of the OBSI
"""
import os.path
import socket
from configuration_builder.click_configuration_builder import ClickConfigurationBuilder
import runner.config as runner_config
import control.config as control_config

# The base directory for all OBSI related code
BASE_PATH = os.path.dirname(os.path.realpath(__file__))

OPENBOX_VERSION = '1.0'


class Manager:
    # The number of attempts for checking if a remote REST server is listening
    CONNECTION_RETRIES = 5

    # The interval in seconds between tries for a check if a remote REST server is listening
    INTERVAL_BETWEEN_CONNECTION_TRIES = 1


class KeepAlive:
    # The interval in milliseconds between KeepAlive messages
    INTERVAL = 30 * 1000


class OpenBoxController:
    HOSTNAME = "localhost"
    PORT = 3637
    BASE_URI = "http://{host}:{port}".format(host=HOSTNAME, port=PORT)
    MESSAGE_ENDPOINT_PATTERN = BASE_URI + "/message/{message}"


class Watchdog:
    CHECK_INTERVAL = 1000  # milliseconds


class RestServer:
    DEBUG = True
    PORT = 3636
    BASE_URI = 'http://localhost:{port}'.format(port=PORT)

    class Endpoints:
        RUNNER_ALERT = '/obsi/runner_alert'
        MESSAGE = '/message/(.*)'


class Engine:
    NAME = 'click'
    CONFIGURATION_BUILDER = ClickConfigurationBuilder
    CONTROL_SOCKET_TYPE = 'TCP'
    CONTROL_SOCKET_ENDPOINT = 10001
    PUSH_MESSAGES_SOCKET_TYPE = 'TCP'
    PUSH_MESSAGES_SOCKET_ENDPOINT = 10002
    PUSH_MESSAGES_CHANNEL = 'openbox'
    NTHREADS = 2
    REQUIREMENTS = ['openbox']
    BASE_EMPTY_CONFIG = r'''ChatterSocket("{push_type}", {push_endpoint}, RETRIES 3, RETRY_WARNINGS false, CHANNEL {channel});
ControlSocket("{control_type}", {control_endpoint}, RETRIES 3, RETRY_WARNINGS false);
require(package "openbox");
chatter_msg::ChatterMessage("EMPTY_KEEP_ALIVE", "message", CHANNEL {channel});
timed_source::TimedSource(1, "base");
discard::Discard();
timed_source -> chatter_msg -> discard'''.format(push_type=PUSH_MESSAGES_SOCKET_TYPE,
                                                 push_endpoint=PUSH_MESSAGES_SOCKET_ENDPOINT,
                                                 channel=PUSH_MESSAGES_CHANNEL,
                                                 control_type=CONTROL_SOCKET_TYPE,
                                                 control_endpoint=CONTROL_SOCKET_ENDPOINT)

    class Capabilities:
        MODULE_INSTALLATION = False
        MODULE_REMOVAL = False
        COMPLEX_MATCH = False


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