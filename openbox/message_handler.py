import messages
from tornado import gen
from tornado.log import app_log
from tornado.httpclient import AsyncHTTPClient


def _get_full_uri(base, endpoint):
    return '{base}{endpoint}'.format(base=base, endpoint=endpoint)


class MessageHandler(object):
    """
    A convenient helper class that handles all the different messages received from OBC
    """

    def __init__(self, manager):
        self.manager = manager
        self.http_client = AsyncHTTPClient()
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
        caps = self.manager.get_capabilities()
        response = messages.ListCapabilitiesResponse.from_request(message, capabilities=caps)
        yield self.manager.message_sender.send_message_ignore_response(response)

    @gen.coroutine
    def handle_global_stats_request(self, message):
        app_log.debug("Handling:{message}".format(message=message.to_json()))
        stats = yield self.manager.get_engine_global_stats()
        response = messages.GlobalStatsResponse.from_request(message, stats=stats)
        yield self.manager.message_sender.send_message_ignore_response(response)

    @gen.coroutine
    def handle_global_stats_reset(self, message):
        app_log.debug("Handling:{message}".format(message=message.to_json()))
        yield self.manager.reset_engine_global_stats()

    @gen.coroutine
    def handle_read_request(self, message):
        app_log.debug("Handling:{message}".format(message=message.to_json()))
        value = yield self.manager.read_block_value(message.block_id, message.read_handle)
        response = messages.ReadResponse.from_request(message, result=value)
        yield self.manager.message_sender.send_message_ignore_response(response)

    @gen.coroutine
    def handle_write_request(self, message):
        app_log.debug("Handling:{message}".format(message=message.to_json()))
        yield self.manager.write_block_value(message.block_id, message.write_handle)
        response = messages.WriteResponse.from_request(message)
        yield self.manager.message_sender.send_message_ignore_response(response)

    @gen.coroutine
    def handle_set_processing_graph_request(self, message):
        app_log.debug("Handling SetProcessingGraphRequest".format(message=message.to_json()))
        yield self.manager.set_processing_graph(message.required_modules, message.blocks, message.connectors)
        response = messages.SetProcessingGraphResponse.from_request(message)
        yield self.manager.message_sender.send_message_ignore_response(response)

    @gen.coroutine
    def handle_barrier_request(self, message):
        app_log.info("Received BarrierRequest")

    @gen.coroutine
    def handle_error(self, message):
        app_log.error("Received Error message:{message}".format(message=message.to_json()))

    @gen.coroutine
    def handle_add_custom_module_request(self, message):
        app_log.debug("Handling AddCustomModuleRequest")
        response = yield self.manager.add_custom_module(message.module_name, message.module_content,
                                                        message.content_transfer_encoding)
        response = messages.SetProcessingGraphResponse.from_request(message)
        yield self.manager.message_sender.send_message_ignore_response(response)
