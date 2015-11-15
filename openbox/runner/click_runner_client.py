import glob
import psutil
import subprocess
import os
import time
from runner_exceptions import EngineClientError


class ClickRunnerClient(object):
    CLICK_BIN = r'/usr/local/bin/click'
    CLICK_PATH = r'/usr/local/lib'
    CHATTER_SOCKET_PATTERN = 'ChatterSocket({proto}, {port}, RETRIES 3, RETRY_WARNINGS false, {keywords});\n'
    CONTROL_SOCKET_PATTERN = 'ControlSocket({proto}, {port}, RETRIES 3, RETRY_WARNINGS false);\n'

    def __init__(self, click_bin=CLICK_BIN, allow_reconfigure=True, click_path=None):
        self.click_bin = click_bin
        self.allow_reconfigure = allow_reconfigure
        self.click_path = click_path or self.CLICK_PATH
        self.expression = None
        self.control_socket_type = None
        self.control_socket_endpoint = None
        self.push_messages_type = None
        self.push_messages_endpoint = None
        self.push_messages_channel = None
        self.nthreads = None
        self._process = None
        self._error_messages = None
        self._last_measurement_time = None
        self._startup_time = None

    def start(self, processing_graph=None, control_socket_type=None, control_socket_endpoint=None,
              nthreads=None, push_messages_type=None, push_messages_endpoint=None, push_messages_channel=None):
        self.expression = processing_graph
        self.control_socket_type = control_socket_type
        self.control_socket_endpoint = control_socket_endpoint
        self.push_messages_channel = push_messages_channel
        self.nthreads = nthreads
        if self.control_socket_type and (self.control_socket_type not in ('TCP', 'UNIX') or
                                                 self.control_socket_endpoint is None):
            raise ValueError("ControlSocket must be of type TCP or UNIX and with a valid endpoint")
        else:
            self._add_control_socket_element()

        self.push_messages_type = push_messages_type
        self.push_messages_endpoint = push_messages_endpoint
        if self.push_messages_type and (self.push_messages_type not in ('TCP', 'UNIX') or
                                                self.push_messages_endpoint is None):
            raise ValueError("PushMessage must be of type TCP or UNIX and with a valid endpoint")
        else:
            self._add_chatter_socket_element()
        if self.is_running():
            raise EngineClientError("Engine already running")
        self._run()
        if self.is_running():
            # The cpu percent is calculated between calls, so let's do the first call on startup
            self._startup_time = time.time()
            self._process.cpu_percent()
            self._last_measurement_time = time.time()
            return True
        else:
            return False

    def suspend(self):
        if not self.is_running():
            raise EngineClientError("Process isn't running")
        self._process.suspend()

    def resume(self):
        if not self.is_running():
            raise EngineClientError("Process isn't running")
        self._process.resume()

    def stop(self):
        if not self.is_running():
            raise EngineClientError("Process isn't running")
        self._process.kill()
        self._reset_state()

    def is_running(self):
        return self._process is not None and self._process.is_running()

    def installed_packages(self):
        lib_names = glob.glob(os.path.join(self.click_path, '*.uo'))
        return [os.path.splitext(os.path.basename(lib_name))[0] for lib_name in lib_names]

    def install_package(self, name, data):
        lib_name = os.path.join(self.click_path, name + '.uo')
        with open(lib_name, 'wb') as f:
            f.write(data)

    def _run(self):
        cmd = self._build_run_command()
        self._reset_state()
        self._process = self._start_click(cmd)

    def _build_run_command(self):
        cmd = [self.click_bin]
        if self.expression:
            cmd.append('-e')
            cmd.append(self.expression)
        if self.allow_reconfigure:
            cmd.append('-R')
        if self.nthreads:
            cmd.append('-j')
            cmd.append(str(self.nthreads))
        if self.click_path:
            cmd.append('-C')
            cmd.append(self.click_path)
        return cmd

    def _reset_state(self):
        self._process = None
        self._error_messages = None

    def _start_click(self, cmd_args):
        return psutil.Popen(cmd_args, stderr=subprocess.PIPE)

    def _check(self):
        cmd = self._build_check_command()
        return_code, self._error_messages = self._start_click_check(cmd)
        print return_code
        return return_code == 0

    def _build_check_command(self):
        cmd = [self.click_bin]
        if self.expression:
            cmd.append('-e')
            cmd.append(self.expression)
        cmd.append('-q')
        return cmd

    def _start_click_check(self, cmd_args):
        process = self._start_click(cmd_args)
        process.wait()
        return_code = process.returncode
        _, err = process.communicate()
        return return_code, err

    @property
    def return_code(self):
        if self._process:
            return self._process.returncode
        else:
            return None

    def get_errors(self):
        if self.return_code is not None:
            # The program finished
            if self._error_messages is not None:
                # we did not get the errors yet
                _, self._error_messages = self._process.communicate()
        return self._error_messages or ''

    def memory_info(self):
        if not self.is_running():
            raise EngineClientError("Process isn't running")
        return self._process.memory_info()

    def memory_percent(self):
        if not self.is_running():
            raise EngineClientError("Process isn't running")
        return self._process.memory_percent()

    def cpu_times(self):
        if not self.is_running():
            raise EngineClientError("Process isn't running")
        return self._process.cpu_times()

    def cpu_percent(self):
        if not self.is_running():
            raise EngineClientError("Process isn't running")
        cpu_percent = self._process.cpu_percent()
        current_time = time.time()
        duration = current_time - self._last_measurement_time
        self._last_measurement_time = current_time
        return cpu_percent, duration

    def cpu_count(self, logical=True):
        return psutil.cpu_count(logical)

    def num_threads(self):
        if not self.is_running():
            raise EngineClientError("Process isn't running")
        return self._process.num_threads()

    def uptime(self):
        if not self.is_running():
            raise EngineClientError("Process isn't running")
        current_time = time.time()
        return current_time - self._startup_time

    def _threads(self):
        if not self.is_running():
            raise EngineClientError("Process isn't running")
        return self._process.threads()

    def wait(self):
        if self.is_running():
            self._process.wait()

    def kill(self):
        if self.is_running():
            self._process.kill()
        self._reset_state()

    def _add_chatter_socket_element(self):
        if self.expression and 'ChatterSocket' not in self.expression:
            if self.push_messages_channel:
                chatter_socket = self.CHATTER_SOCKET_PATTERN.format(proto=self.push_messages_type,
                                                                    port=self.push_messages_endpoint,
                                                                    keywords="CHANNEL {channel}".format(
                                                                        channel=self.push_messages_channel))
            else:
                chatter_socket = self.CHATTER_SOCKET_PATTERN.format(proto=self.push_messages_type,
                                                                    port=self.push_messages_endpoint,
                                                                    keywords="")
            self.expression = chatter_socket + self.expression

    def _add_control_socket_element(self):
        if self.expression and 'ControlSocket' not in self.expression:
            control_socket = self.CONTROL_SOCKET_PATTERN.format(proto=self.control_socket_type,
                                                                port=self.control_socket_endpoint)
            self.expression = control_socket + self.expression


if __name__ == "__main__":
    # testing

    client = ClickRunnerClient()
    click_config = r'''require(package "openbox");
require(package "openbox");
chater_msg::ChatterMessage("LOG", "{\"type\": \"log\", \"message\": \"The is a log message\", \"sevirity\": 0, \"origin_dpid\": 123, \"origin_block\": \"block1\"}", CHANNEL test);

TimedSource(1, "blabla")
-> chater_msg
-> Discard();'''
    client.start(processing_graph=click_config, control_socket_type='TCP', control_socket_endpoint=9000,
                 nthreads=1, push_messages_type='TCP', push_messages_endpoint=7001, push_messages_channel='test')
    print client.is_running()
    print "errors:", client.get_errors()
    time.sleep(1)
    print "nthreads:", client.num_threads()
    print client.memory_info()
    print client.memory_percent()
    print client.cpu_times()
    print "cpu_percent:", client.cpu_percent()
    time.sleep(1)
    client.suspend()
    print "nthreads:", client.num_threads()
    print client.memory_info()
    print client.memory_percent()
    print client.cpu_times()
    print "cpu_percent:", client.cpu_percent()
    time.sleep(1)
    client.resume()
    time.sleep(30)
    print "nthreads:", client.num_threads()
    print client.memory_info()
    print client.memory_percent()
    print client.cpu_times()
    print "cpu_percent:", client.cpu_percent()
    client.stop()
    print client.is_running()
    try:
        client.suspend()
    except EngineClientError as e:
        print e