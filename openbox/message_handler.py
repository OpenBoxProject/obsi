from tornado import gen
from tornado.log import app_log
import messages


class MessageHandler(object):
    """
    A convenient helper class that handles all the different messages received from OBC
    """
    def __init__(self, manager):
        self.manager = manager
        self.registered_message_handlers = {
            messages.ListCapabilitiesRequest: self.handle_list_capabilities_request,
            messages.GlobalStatsRequest: self.handle_global_stats_request,
            messages.GlobalStatsReset: self.handle_global_stats_reset,
            messages.ReadRequest: self.handle_read_request,
            messages.WriteRequest: self.handle_write_request,
            messages.SetProcessingGraphRequest: self.handle_set_processing_graph_request,
            messages.BarrierRequest: self.handle_barrier_request,
            messages.Error: self.handle_error,
            messages.AddCustomModuleRequest: self.handle_add_custom_module_request
        }

    @gen.coroutine
    def default_message_handler(self, message):
        app_log.info("Received unhandled:{message}".format(message=message.to_json()))

    @gen.coroutine
    def handle_list_capabilities_request(self, message):
        app_log.debug("Handling:{message}".format(message=message.to_json()))
        pass

    @gen.coroutine
    def handle_global_stats_request(self, message):
        app_log.debug("Handling:{message}".format(message=message.to_json()))
        pass

    @gen.coroutine
    def handle_global_stats_reset(self, message):
        app_log.debug("Handling:{message}".format(message=message.to_json()))
        pass

    @gen.coroutine
    def handle_read_request(self, message):
        app_log.debug("Handling:{message}".format(message=message.to_json()))
        pass

    @gen.coroutine
    def handle_write_request(self, message):
        app_log.debug("Handling:{message}".format(message=message.to_json()))
        pass

    @gen.coroutine
    def handle_set_processing_graph_request(self, message):
        app_log.debug("Handling:{message}".format(message=message.to_json()))
        pass

    @gen.coroutine
    def handle_barrier_request(self, message):
        app_log.debug("Handling:{message}".format(message=message.to_json()))
        pass

    @gen.coroutine
    def handle_error(self, message):
        app_log.debug("Handling:{message}".format(message=message.to_json()))
        pass


    @gen.coroutine
    def handle_add_custom_module_request(self, message):
        app_log.debug("Handling:{message}".format(message=message.to_json()))
        pass
