#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################

"""
Transforms an OpenBox configuration in to a Click's configuration
"""
import capabilities
from click_blocks import ClickBlock, build_click_block_from_dict
from click_configuration import ClickConfiguration
from click_elements import build_element_from_dict
from open_box_blocks import build_open_box_block_from_dict
from connection import Connection
from configuration_builder_exceptions import ClickModuleTranslationError


class ClickConfigurationBuilder(object):
    _installed_modules = {}

    def __init__(self, requirements=None, click_blocks=None, connections=None):
        self.requirements = requirements or []
        self.blocks = click_blocks or []
        self.connections = connections or []
        self._blocks_by_name = dict((block.name, block) for block in self.blocks)
        self.click_config = self._build_click_config()

    @staticmethod
    def required_elements():
        elements = set()
        for block in ClickBlock.blocks_registry.itervalues():
            elements.update(block.required_element_types())
        return elements

    @staticmethod
    def supported_blocks():
        return ClickBlock.blocks_registry.keys()

    @staticmethod
    def supported_blocks_from_supported_elements_types(elements):
        elements = set(elements)
        blocks = []
        for block_name, block in ClickBlock.blocks_registry.iteritems():
            if all(element in elements for element in block.required_element_types()):
                blocks.append(block_name)
        return blocks

    @staticmethod
    def supported_match_fields():
        return capabilities.SUPPORTED_MATCH_FIELDS

    @staticmethod
    def supported_complex_match():
        return capabilities.SUPPORTED_COMPLEX_MATCH

    @staticmethod
    def supported_protocol_analyser_protocols():
        return capabilities.SUPPORTED_PROTOCOLS

    @classmethod
    def from_open_box_configuration(cls, config):
        requirements = config.requirements
        click_blocks = [ClickBlock.from_open_box_block(block) for block in config.blocks]
        connections = config.connections
        return cls(requirements, click_blocks, connections)

    def _build_click_config(self):
        # get the local elements of each block
        elements = []
        for block in self.blocks:
            elements.extend(block.elements())

        # get the local connections from each block
        click_connections = []
        for block in self.blocks:
            click_connections.extend(block.connections())

        for connection in self.connections:
            src_block = self._blocks_by_name[connection.src]
            dst_block = self._blocks_by_name[connection.dst]
            src_element, src_element_port = src_block.output_element_and_port(connection.src_port)
            dst_element, dst_element_port = dst_block.input_element_and_port(connection.dst_port)
            click_connections.append(Connection(src_element, dst_element, src_element_port, dst_element_port))

        return ClickConfiguration(self.requirements, elements, click_connections)

    def to_engine_config(self):
        return self.click_config.to_engine_config()

    def translate_block_read_handler(self, block_name, handler_name):
        try:
            block = self._blocks_by_name[block_name]
        except KeyError:
            raise ValueError('Unknown block named: {name}'.format(name=block_name))
        return block.translate_read_handler(handler_name)

    def translate_block_write_handler(self, block_name, handler_name):
        try:
            block = self._blocks_by_name[block_name]
        except KeyError:
            raise ValueError('Unknown block named: {name}'.format(name=block_name))
        return block.translate_write_handler(handler_name)

    @classmethod
    def add_custom_module(cls, name, translation):
        translation = byteify(translation)
        try:
            open_box_blocks_defs = translation['open_box_blocks']
            click_elements_defs = translation['click_elements']
            click_blocks_defs = translation['click_blocks']
        except KeyError as e:
            raise ClickModuleTranslationError("Missing '{field}' in translation configuration".format(field=e.message))

        if not isinstance(open_box_blocks_defs, (tuple, list)):
            raise ClickModuleTranslationError("open_box_blocks must be a list of OpenBox Block Definitions")
        if not isinstance(click_elements_defs, (tuple, list)):
            raise ClickModuleTranslationError("click_elements must be a list of Click Elements Definitions")
        if not isinstance(click_blocks_defs, (tuple, list)):
            raise ClickModuleTranslationError("click_blocks must be a list of Click Block Definitions")

        open_box_blocks = [build_open_box_block_from_dict(obb) for obb in open_box_blocks_defs]
        click_elements = [build_element_from_dict(element) for element in click_elements_defs]
        click_blocks = [build_click_block_from_dict(cbd) for cbd in click_blocks_defs]

        cls._installed_modules[name] = dict(open_box_blocks=open_box_blocks,
                                            click_elements=click_elements,
                                            click_blocks=click_blocks)


def byteify(input):
    if isinstance(input, dict):
        return {byteify(key): byteify(value) for key, value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input