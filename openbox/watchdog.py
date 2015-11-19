import logging
from tornado.ioloop import PeriodicCallback
from tornado.log import app_log


class ProcessWatchdog(object):
    def __init__(self, interval=1000):
        self.interval = interval
        self._process_to_check = {}
        self._periodic_callback = PeriodicCallback(self._check_processes, self.interval)

    def register_process(self, process, on_dead_callback):
        self._process_to_check[process] = on_dead_callback

    def start(self):
        if not self._periodic_callback.is_running():
            self._periodic_callback.start()

    def stop(self):
        if self._periodic_callback.is_running():
            self._periodic_callback.stop()

    def _check_processes(self):
        for process in self._process_to_check:
            if not process.is_running():
                self._process_to_check[process](process)
