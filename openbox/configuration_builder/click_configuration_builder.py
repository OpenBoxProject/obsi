"""
Transforms an OpenBox configuration in to a Click's configuration
"""
from open_box_blocks import OpenBoxBlock
from click_blocks import ClickBlock


class ClickConfigurationBuilder(object):
    def __init__(self):
        self.processing_blocks = []
        self.match_fields = []
        self.protocol_analyser_protocols = []

    @staticmethod
    def required_elements():
        elements = set()
        for block in ClickBlock.blocks_registry.itervalues():
            elements.update(block.required_element_types())
        return elements

    @staticmethod
    def supported_blocks():
        return ClickBlock.blocks_registry.keys()

    def from_open_box_configuration(self, config):
        raise NotImplementedError()