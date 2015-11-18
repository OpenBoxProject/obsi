import unittest
from configuration_builder import ConfigurationBuilder, OpenBoxBlock
from configuration_builder.click_configuration_builder import ClickConfigurationBuilder
from configuration_builder.click_configuration import ClickConfiguration
from configuration_builder.connection import Connection
from configuration_builder.open_box_configuration import OpenBoxConfiguration
from configuration_builder.click_elements import Element


class TestBuildConfiguration(unittest.TestCase):
    def setUp(self):
        self.config = dict(requirements=['openbox'],
                           blocks=[
                               dict(name='from_device', type='FromDevice', config=dict(devname='eth0')),
                               dict(name='discard', type='Discard', config={}),
                           ],
                           connections=[
                               dict(src='from_device', dst='discard', src_port=0, dst_port=0)
                           ])
        self.expected_open_box_config = OpenBoxConfiguration(requirements=['openbox'],
                                                             blocks=[
                                                                 OpenBoxBlock.from_dict(
                                                                     dict(name='from_device', type='FromDevice',
                                                                          config=dict(devname='eth0'))),
                                                                 OpenBoxBlock.from_dict(
                                                                     dict(name='discard', type='Discard', config={})),
                                                             ],
                                                             connections=[
                                                                 Connection(src='from_device', dst='discard',
                                                                            src_port=0, dst_port=0)])
        self.expected_click_config = ClickConfiguration(requirements=['openbox'],
                                                        elements=[
                                                          Element.from_dict(dict(name='from_device@_@from_device', type='FromDevice',
                                                                                 config=dict(devname='eth0'))),
                                                          Element.from_dict(
                                                              dict(name='from_device@_@counter', type='Counter', config={})),
                                                          Element.from_dict(dict(name='discard@_@discard', type='Discard', config={})),
                                                          ],
                                                        connections=[
                                                          Connection('from_device@_@from_device', 'from_device@_@counter', 0, 0),
                                                          Connection('from_device@_@counter', 'discard@_@discard', 0, 0),
                                                          ]
                                                        )

    def test_build_open_box_configuration(self):
        self.assertEqual(self.expected_open_box_config, OpenBoxConfiguration.from_dict(self.config))

    def test_click_configuration_builedr(self):
        self.assertEqual(self.expected_click_config, ClickConfigurationBuilder.from_open_box_configuration(
            self.expected_open_box_config).click_config)

    def test_configuration_builder(self):
        config_builder = ConfigurationBuilder(ClickConfigurationBuilder)
        engine_config_builder = config_builder.engine_config_builder_from_dict(self.config)
        self.assertEqual(self.expected_click_config.to_engine_config(), engine_config_builder.to_engine_config())


