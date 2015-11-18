"""
Build an execution engine configuration from an open box configuration
"""
from open_box_blocks import OpenBoxBlock
from open_box_configuration import OpenBoxConfiguration


class ConfigurationBuilder(object):
    def __init__(self, engine_configuration_builder):
        self.engine_builder = engine_configuration_builder

    def supported_blocks(self):
        return self.engine_builder.supported_blocks()

    def supported_blocks_from_supported_engine_elements_types(self, elements):
        return self.engine_builder.supported_blocks_from_supported_elements_types(elements)

    def required_engine_elements(self):
        return self.engine_builder.required_elements()

    def engine_configuration_builder_from_dict(self, config, additional_requirements=None):
        open_box_configuration = OpenBoxConfiguration.from_dict(config, additional_requirements)
        engine_configuration = self.engine_builder.from_open_box_configuration(open_box_configuration)
        return engine_configuration

    def supported_match_fields(self):
        return self.engine_builder.supported_match_fields()

    def supported_protocol_analyser_protocols(self):
        return self.engine_builder.supported_protocol_analyser_protocols()


