import unittest
import zlib
from openbox.container import Container
from openbox.core import ProcessingGraph, ConditionalProcessingBlock, TransformationBlock
from openbox.parsing import EthernetParsingBlock, Ipv4ParsingBlock, NopParsingBlock, TcpParsingBlock, UdpParsingBlock, \
    PayloadParsingBlock
from openbox.transformation import SingleFieldTransformator


class TestSingleFieldTransformation(unittest.TestCase):
    def test_compression(self):
        pg = ProcessingGraph('header',
                             EthernetParsingBlock('ethernet'),
                             ConditionalProcessingBlock('l3',
                                                        lambda metadata: metadata.ethernet.eth_type,
                                                        {0x800: Ipv4ParsingBlock('ipv4')},
                                                        NopParsingBlock('nop')),
                             ConditionalProcessingBlock('l4',
                                                        lambda metadata: metadata.ipv4.protocol,
                                                        {0x06: TcpParsingBlock('tcp'),
                                                         0x11: UdpParsingBlock('udp')},
                                                        NopParsingBlock('nop')),
                             PayloadParsingBlock('payload'),
                             TransformationBlock('gzip_compress',
                                                 SingleFieldTransformator('payload',
                                                                          'compressed_payload',
                                                                          zlib.compress)))

        packet = 'b0487aeccc020c84dc9e9a6108004500002961a740008006678cc0a80166d4b39ad9' \
                 '19bd01bbf2d4bf217286f39a5010010249a6000000112233'.decode('hex')
        expected_payload = zlib.compress('00112233'.decode('hex'))
        p, off, metadata = pg.process(packet, 0, Container())
        self.assertEqual(off, len(packet))
        self.assertEqual(expected_payload, metadata.compressed_payload)
