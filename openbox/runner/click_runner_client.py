import psutil
import subprocess
import os
from runner_exceptions import EngineClientError


class ClickRunnerClient(object):
    CLICK_BIN = r'/usr/local/bin/click'
    CHATTER_SOCKET_PATTERN = 'ChatterSocket({proto}, {port}, RETRIES 3, RETRY_WARNINGS false, {keywords});\n'

    def __init__(self, click_bin=CLICK_BIN,  allow_reconfigure=True, click_path=None, cwd_same_as_config=True):
        self.click_bin = click_bin
        self.allow_reconfigure = allow_reconfigure
        self.click_path = click_path
        self.cwd_same_as_config = cwd_same_as_config
        self.config_file = None
        self.expression = None
        self.control_socket_port = None
        self.control_socket_file = None
        self.push_messages_port = None
        self.push_messages_filename = None
        self.push_messages_channel = None
        self.nthreads = None
        self._process = None
        self._error_messages = None

    def start(self, config_file=None, proccessing_graph=None, control_socket_port=None, control_socket_file=None,
              nthreads=None, push_messages_port=None, push_messages_filename=None, push_messages_channel=None):
        self.config_file = config_file
        self.expression = proccessing_graph
        self.control_socket_port = control_socket_port
        self.control_socket_file = control_socket_file
        self.push_messages_channel = push_messages_channel
        self.nthreads = nthreads
        self.push_messages_port = push_messages_port
        self.push_messages_filename = push_messages_filename
        if self.push_messages_port:
            self._add_tcp_chatter_socket_element()
        if self.push_messages_filename:
            self._add_unix_chatter_socket_element()
        if self.is_running():
            raise EngineClientError("Engine already running")
        self._run()
        if self.is_running():
            # The cpu percent is calculated between calls, so let's do the first call on startup
            self.cpu_percent()
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

    def _run(self):
        cmd = self._build_run_command()
        self._reset_state()
        self._process = self._start_click(cmd)

    def _build_run_command(self):
        cmd = [self.click_bin]
        if self.config_file:
            cmd.append('-f')
            cmd.append(self.config_file)
        if self.expression:
            cmd.append('-e')
            cmd.append(self.expression)
        if self.control_socket_port:
            cmd.append('-p')
            cmd.append(str(self.control_socket_port))
        if self.control_socket_file:
            cmd.append('-u')
            cmd.append(self.control_socket_file)
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
        if self.cwd_same_as_config and self.config_file:
            cwd = os.path.dirname(os.path.abspath(self.config_file))
        else:
            cwd = None
        return psutil.Popen(cmd_args, stderr=subprocess.PIPE, cwd=cwd)

    def _check(self):
        cmd = self._build_check_command()
        return_code, self._error_messages = self._start_click_check(cmd)
        print return_code
        return return_code == 0

    def _build_check_command(self):
        cmd = [self.click_bin]
        if self.config_file:
            cmd.append('-f')
            cmd.append(self.config_file)
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
        return self._process.cpu_percent()

    def cpu_count(self, logical=True):
        return psutil.cpu_count(logical)

    def num_threads(self):
        if not self.is_running():
            raise EngineClientError("Process isn't running")
        return self._process.num_threads()

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

    def _add_tcp_chatter_socket_element(self):
        if self.expression and 'ChatterSocket' not in self.expression:
            if self.push_messages_channel:
                chatter_socket = self.CHATTER_SOCKET_PATTERN.format(proto='TCP', port=self.push_messages_port,
                                                                    keywords="CHANNEL {channel}".format(
                                                                        channel=self.push_messages_channel))
            else:
                chatter_socket = self.CHATTER_SOCKET_PATTERN.format(proto='TCP', port=self.push_messages_port,
                                                                    keywords="")
            self.expression = chatter_socket + self.expression
        if self.config_file:
            raise NotImplementedError("Cannot add to config file")

    def _add_unix_chatter_socket_element(self):
        if self.expression and 'ChatterSocket' not in self.expression:
            if self.push_messages_channel:
                chatter_socket = self.CHATTER_SOCKET_PATTERN.format(proto='UNIX', port=self.push_messages_filename,
                                                                    keywords="CHANNEL {channel}".format(
                                                                        channel=self.push_messages_channel))
            else:
                chatter_socket = self.CHATTER_SOCKET_PATTERN.format(proto='UNIX', port=self.push_messages_filename,
                                                                    keywords="")
            self.expression = chatter_socket + self.expression
        if self.config_file:
            raise NotImplementedError("Cannot add to config file")


if __name__ == "__main__":
    # testing
    import time

    client = ClickRunnerClient()
    click_config = '''require(package "openbox");
    chater_msg::ChatterMessage("LOG", "this is a test", CHANNEL test);
    InfiniteSource("aasdf", -1, 1, true) -> chater_msg->Discard;'''
    client.start(proccessing_graph=click_config, control_socket_port=9001,
                 nthreads=2, push_messages_port=7001, push_messages_channel="test")
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