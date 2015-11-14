"""
An OBSI's Manager.
"""
from tornado.ioloop import IOLoop
import config
import psutil
from tornado.escape import json_decode, json_encode, url_escape
from tornado.log import app_log
from tornado import httpclient
from tornado import gen
from watchdog import ProcessWatchdog
from push_message_receiver import PushMessageReceiver
from message_router import MessageRouter


class ManagerState:
    EMPTY = 0
    INITIALIZING = 10
    INITIALIZED = 20


def _get_full_uri(base, endpoint):
    return '{base}{endpoint}'.format(base=base, endpoint=endpoint)


class Manager(object):
    def __init__(self):
        self._runner_process = None
        self._control_process = None
        self._watchdog = None
        self.push_messages_receiver = None
        self.configuration_builder = None
        self.message_router = None
        self.state = ManagerState.EMPTY
        self._http_client = httpclient.HTTPClient()
        self._alert_registered = False

    def start(self):
        app_log.info("Starting components")
        self.state = ManagerState.INITIALIZING
        self._start_runner()
        self._start_control()
        self._start_watchdog()
        self._start_push_messages_receiver()
        self._start_configuration_builder()
        self._start_message_router()
        self._start_message_sender()
        self._start_local_rest_server()
        app_log.info("All components active")
        self.state = ManagerState.INITIALIZED
        self._send_hello_message()
        app_log.info("Starting IOLoop")
        self._start_io_loop()

    def _start_runner(self):
        app_log.info("Starting EE Runner")
        self._runner_process = self._start_remote_rest_server(config.Runner.Rest.BIN, config.Runner.Rest.PORT,
                                                              config.Runner.Rest.DEBUG)
        if self._runner_process.is_running():
            app_log.info("EERunner REST Server running")
        else:
            app_log.error("EERunner REST Server not running")
            exit(1)
        if self._is_engine_supported(_get_full_uri(config.Runner.Rest.BASE_URI, config.Runner.Rest.Endpoints.ENGINES)):
            app_log.info("{engine} supported by EE Runner.".format(engine=config.Engine.NAME))
        else:
            app_log.error("{engine} is not supported by EE Runner".format(engine=config.Engine.NAME))
            exit(1)
        if self._set_engine(_get_full_uri(config.Runner.Rest.BASE_URI, config.Runner.Rest.Endpoints.ENGINES)):
            app_log.info("{engine} set".format(engine=config.Engine.NAME))
        else:
            app_log.error("{engine} not set by EERunner".format(engine=config.Engine.NAME))
            exit(1)
        if self._start_engine():
            app_log.info("{engine} started".format(engine=config.Engine.NAME))
        else:
            app_log.error("{engine} failed to start".format(engine=config.Engine.NAME))
            exit(1)
        self._alert_registered = self._register_alert_uri()
        app_log.info("Alert Registeration status: {status}".format(status=self._alert_registered))

    def _start_remote_rest_server(self, bin_path, port, debug):
        cmd = [bin_path, '--debug', str(port), '--port', str(debug)]
        return psutil.Popen(cmd)

    def _is_engine_supported(self, uri):
        engine_name = config.Engine.NAME,
        try:
            response = self._http_client.fetch(uri)
            return engine_name in json_decode(response.body)
        except httpclient.HTTPError as e:
            app_log.error(e.response)
            return False

    def _set_engine(self, uri):
        engine_name = config.Engine.NAME
        try:
            self._http_client.fetch(uri, method="POST", body=json_encode(engine_name))
            return True
        except httpclient.HTTPError as e:
            app_log.error(e.response)
            return False

    def _start_engine(self):
        params = dict(processing_graph=config.Engine.BASE_EMPTY_CONFIG,
                      control_socket_type=config.Engine.CONTROL_SOCKET_TYPE,
                      control_socket_endpoint=config.Engine.CONTROL_SOCKET_ENDPOINT,
                      nthreads=config.Engine.NTHREADS,
                      push_messages_type=config.Engine.PUSH_MESSAGES_SOCKET_TYPE,
                      push_messages_endpoint=config.Engine.PUSH_MESSAGES_SOCKET_ENDPOINT,
                      push_messages_channel=config.Engine.PUSH_MESSAGES_CHANNEL)
        uri = _get_full_uri(config.Runner.Rest.BASE_URI, config.Runner.Rest.Endpoints.START)
        try:
            self._http_client.fetch(uri, method="POST", body=json_encode(params))
            return True
        except httpclient.HTTPError as e:
            app_log.error(e.response)
            return False

    def _register_alert_uri(self):
        uri = _get_full_uri(config.RestServer.BASE_URI, config.RestServer.Endpoints.RUNNER_ALERT)
        try:
            self._http_client.fetch(uri, method='POST', body=url_escape(uri))
            return True
        except httpclient.HTTPError as e:
            app_log.error(e.response)
            return False

    def _start_control(self):
        app_log.info("Starting EE Control")
        self._control_process = self._start_remote_rest_server(config.Control.Rest.BIN, config.Control.Rest.PORT,
                                                               config.Control.Rest.DEBUG)
        if self._control_process.is_running():
            app_log.info("EEControl REST Server running")
        else:
            app_log.error("EEControl REST Server not running")
            exit(1)
        if self._is_engine_supported(
                _get_full_uri(config.Control.Rest.BASE_URI, config.Control.Rest.Endpoints.ENGINES)):
            app_log.info("{engine} supported by EE Control".format(engine=config.Engine.NAME))
        else:
            app_log.error("{engine} is not supported by EE Control".format(engine=config.Engine.NAME))
            exit(1)
        if self._set_engine(_get_full_uri(config.Control.Rest.BASE_URI, config.Control.Rest.Endpoints.ENGINES)):
            app_log.info("{engine} set by EE Control".format(engine=config.Engine.NAME))
        else:
            app_log.error("{engine} not set by EE Control".format(engine=config.Engine.NAME))
            exit(1)
        if self._connect_control():
            app_log.info("EE Control client connected to engine")
        else:
            app_log.error("EE Control client couldn't connect to engine")
            exit(1)

    def _connect_control(self):
        params = dict(address=config.Control.SOCKET_ADDRESS, type=config.Control.SOCKET_TYPE)
        uri = _get_full_uri(config.Control.Rest.BASE_URI, config.Control.Rest.Endpoints.CONNECT)
        try:
            self._http_client.fetch(uri, method="POST", body=json_encode(params))
            return True
        except httpclient.HTTPError as e:
            app_log.error(e.response)
            return False

    def _start_watchdog(self):
        app_log.info("Starting ProcessWatchdog")
        self._watchdog = ProcessWatchdog(config.Watchdog.CHECK_INTERVAL)
        self._watchdog.register_process(self._runner_process, self._process_died)
        self._watchdog.register_process(self._control_process, self._process_died)
        self._watchdog.start()

    def _process_died(self, process):
        if process == self._runner_process:
            app_log.error("EE Runner REST server has died")
            # TODO: Add real handling
        elif process == self._control_process:
            app_log.error("EE Control REST server has died")
            # TODO: Add real handling
        else:
            app_log.error("Unknown process dies")

    def _start_push_messages_receiver(self):
        app_log.info("Starting PushMessagesReceiver")
        self.push_messages_receiver = PushMessageReceiver()
        self.push_messages_receiver.connect(config.PushMessages.SOCKET_ADDRESS,
                                            config.PushMessages.SOCKET_FAMILY,
                                            config.PushMessages.RETRY_INTERVAL)

    def _start_configuration_builder(self):
        app_log.info("Starting EE Configuration Builder")
        # TODO: Add real code

    @gen.coroutine
    def _start_message_router(self):
        app_log.info("Starting MessageRouter")
        self.message_router = MessageRouter()
        self._register_messages_handler()
        yield self.message_router.start()

    def _register_messages_handler(self):
        app_log.info("Registering handlers for messages")
        # TODO: add real code

    def _start_message_sender(self):
        app_log.info("Starting MessageSender")
        # TODO: add real code

    def _start_local_rest_server(self):
        app_log.info("Starting MessageSender")
        # TODO: add real code

    def _send_hello_message(self):
        app_log.info("Creating and sending Hello Message")
        # TODO: add real code

    def _start_io_loop(self):
        app_log.info("Starting the IOLoop")
        IOLoop.current().start()


def main():
    manager = Manager()
    manager.start()


if __name__ == '__main__':
    main()