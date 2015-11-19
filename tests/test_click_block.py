import unittest
from configuration_builder.open_box_blocks import OpenBoxBlock
from configuration_builder.click_blocks import ClickBlock
from configuration_builder.click_elements import Element
from configuration_builder.connection import Connection
import configuration_builder.transformations as trans


class TestSingleClickBlock(unittest.TestCase):
    def setUp(self):
        self.obb = OpenBoxBlock.from_dict(dict(name='from_device', type='FromDevice',
                                               config=dict(devname='eth0', sniffer=True)))
        self.cb = ClickBlock.from_open_box_block(self.obb)

    def test_elements(self):
        expected = [Element.from_dict(dict(name='from_device@_@from_device', type='FromDevice',
                                           config=dict(devname='eth0', sniffer=True))),
                    Element.from_dict(dict(name='from_device@_@counter', type='Counter',
                                           config={}))]
        elements = self.cb.elements()
        self.assertEqual(elements, expected)

    def test_connections(self):
        expected = [Connection('from_device@_@from_device', 'from_device@_@counter', 0, 0)]
        connections = self.cb.connections()
        self.assertEqual(connections, expected)

    def test_output(self):
        expected = ('from_device@_@counter', 0)
        self.assertEqual(self.cb.output_element_and_port(0), expected)

    def test_no_input(self):
        self.assertEqual(self.cb.input_element_and_port(0), (None, None))

    def test_translate_read_handler(self):
        self.assertEqual(self.cb.translate_read_handler('count'), ('from_device@_@counter', 'count', trans.to_int))
        self.assertEqual(self.cb.translate_read_handler('byte_rate'), ('from_device@_@counter', 'byte_rate', trans.to_float))
        self.assertEqual(self.cb.translate_read_handler('drops'), ('from_device@_@from_device', 'kernel-drops', trans.identity))

    def test_non_existing_read_handler(self):
        self.assertRaises(ValueError, self.cb.translate_read_handler, 'not-exist')

    def test_translate_write_handler(self):
        self.assertEqual(self.cb.translate_write_handler('reset_counts'), ('from_device@_@counter', 'reset_counts', trans.identity))

    def test_non_existing_write_handler(self):
        self.assertRaises(ValueError, self.cb.translate_write_handler, 'not-exist')