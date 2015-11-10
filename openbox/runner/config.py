"""
A configuration and definitions file used by the EE runner server and client
"""
from runner.click_runner_client import ClickRunnerClient

ENGINES = {'click': (ClickRunnerClient, dict(click_bin=r'/usr/local/bin/click', allow_reconfigure=True, click_path=None,
                                             cwd_same_as_config=True))}


class RestServer:
    ENGINE_START_PARAMETERS = ('proccessing_graph', 'control_socket_port', 'control_socket_file', 'nthreads',
                               'push_messages_port', 'push_messages_filename', 'push_messages_channel')

    PORT = 9001
    DEBUG = True
    CLIENT_RUN_POLLING_INTERVAL = 500  # Milliseconds

    class Endpoints:
        ENGINES = '/runner/engines'
        START = '/runner/start'
        SUSPEND = '/runner/suspend'
        RESUME = '/runner/resume'
        STOP = '/runner/stop'
        RUNNING = '/runner/running'
        MEMORY = '/runner/memory'
        CPU = '/runner/cpu'
        REGISTER_ALERT_URL = '/runner/register_alert_url'