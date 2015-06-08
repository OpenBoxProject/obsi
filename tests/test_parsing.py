import unittest
import time
from openbox.container import Container
from openbox.core import ProcessingGraph, ConditionalProcessingBlock
from openbox.exception import ParsingError
from openbox.parsing import (FrameParsingBlock, EthernetParsingBlock,
                             Ipv4ParsingBlock, UdpParsingBlock, TcpParsingBlock, PayloadParsingBlock, NopParsingBlock)


class TestFrameParsing(unittest.TestCase):
    def setUp(self):
        self.pb = FrameParsingBlock('frame')

    def test_parse_no_packet_header(self):
        packet = 'b0487aeccc020c84dc9e9a6108004500003044ca400080065eaac0a80166a29ff2a51' \
                 '64e01bb7c7948b7000000007002ffff4e920000020405b401010402'.decode('hex')
        ct = time.time()
        np, off, metadata = self.pb.process(packet, 0, Container())
        self.assertAlmostEqual(ct, metadata.frame.timestamp, delta=1)
        self.assertEqual(len(packet), metadata.frame.length)
        self.assertEqual(off, 0)

    def test_parse_with_packet_header(self):
        packet = 'b0487aeccc020c84dc9e9a6108004500003044ca400080065eaac0a80166a29ff2a51' \
                 '64e01bb7c7948b7000000007002ffff4e920000020405b401010402'.decode('hex')
        header = (1000, 123000, len(packet))
        np, off, metadata = self.pb.process(packet, 0, Container(), packet_header=header)
        self.assertEqual(1000.123, metadata.frame.timestamp)
        self.assertEqual(len(packet), metadata.frame.length)
        self.assertEqual(off, 0)


class TestEthernetParsing(unittest.TestCase):
    def setUp(self):
        self.pb = EthernetParsingBlock('ethernet')

    def test_parse(self):
        packet = 'b0487aeccc020c84dc9e9a6108004500003044ca400080065eaac0a80166a29ff2a51' \
                 '64e01bb7c7948b7000000007002ffff4e920000020405b401010402'.decode('hex')
        expected = Container(ethernet=Container(dst_mac='b0487aeccc02'.decode('hex'),
                                                src_mac='0c84dc9e9a61'.decode('hex'),
                                                eth_type=0x800))
        p, off, metadata = self.pb.process(packet, 0, Container())
        self.assertEqual(off, 14)
        self.assertEqual(metadata, expected)

    def test_parsing_short(self):
        packet = 'b0487aeccc020c84dc9e9a61'.decode('hex')
        self.assertRaises(ParsingError, self.pb.process, packet, 0, Container())


class TestIpv4Parsing(unittest.TestCase):
    def setUp(self):
        self.pb = Ipv4ParsingBlock('ipv4')

    def test_parse(self):
        packet = 'b0487aeccc020c84dc9e9a6108004500003044ca400080065eaac0a80166a29ff2a51' \
                 '64e01bb7c7948b7000000007002ffff4e920000020405b401010402'.decode('hex')
        expected = Container(ipv4=Container(ihl=20, tos=0, length=48, ipid=0x44ca, flags=0x02,
                                            frag_offset=0, ttl=128, protocol=6, src_ip='192.168.1.102',
                                            dst_ip='162.159.242.165'))
        p, off, metadata = self.pb.process(packet, 14, Container())
        self.assertEqual(off, 14 + 20)
        self.assertEqual(metadata, expected)

    def test_parse_short(self):
        packet = 'b0487aeccc020c84dc9e9a610800450000'.decode('hex')
        self.assertRaises(ParsingError, self.pb.process, packet, 14, Container())


class TestTcpParsing(unittest.TestCase):
    def setUp(self):
        self.pb = TcpParsingBlock('tcp')

    def test_parse(self):
        packet = 'b0487aeccc020c84dc9e9a6108004500003044ca400080065eaac0a80166a29ff2a51' \
                 '64e01bb7c7948b7000000007002ffff4e920000020405b401010402'.decode('hex')
        expected = Container(tcp=Container(thl=28, src_port=5710, dst_port=443,
                                           seq_num=2088323255, ack_num=0, flags=0x002))
        p, off, metadata = self.pb.process(packet, 14 + 20, Container())
        self.assertEqual(off, 14 + 20 + 28)
        self.assertEqual(metadata, expected)

    def test_parse_short(self):
        packet = 'b0487aeccc020c84dc9e9a6108004500003044ca400080065eaac0a80166a29ff2a51' \
                 '64e01bb7c7948b7000000007002ff'.decode('hex')

        self.assertRaises(ParsingError, self.pb.process, packet, 14 + 20, Container())


class TestUdpParsing(unittest.TestCase):
    def setUp(self):
        self.pb = UdpParsingBlock('udp')

    def test_parse(self):
        packet = '0c84dc9e9a61b0487aeccc020800450000470a04000036110e14d83ad245c0a8016601bb' \
                 'ed0d00334d3a10fc08efebae2eadf5358b460e9ebdbfe23c722defe52e48384c500c43c91' \
                 '7a9f53fd5754f22e3e6cbb1b6'.decode('hex')
        expected = Container(udp=Container(src_port=443, dst_port=60685, length=51))
        p, off, metadata = self.pb.process(packet, 14 + 20, Container())
        self.assertEqual(off, 14 + 20 + 8)
        self.assertEqual(metadata, expected)

    def test_parse_short(self):
        packet = '0c84dc9e9a61b0487aeccc020800450000470a04000036110e14d83ad245c0a8016601bb'.decode('hex')

        self.assertRaises(ParsingError, self.pb.process, packet, 14 + 20, Container())


class TestEthernetIpv4HeaderParsing(unittest.TestCase):
    def setUp(self):
        self.pg = ProcessingGraph('header',
                                  # FrameParsingBlock('frame'),
                                  EthernetParsingBlock('ethernet'),
                                  ConditionalProcessingBlock('l3',
                                                             lambda metadata: metadata.ethernet.eth_type,
                                                             {0x800: Ipv4ParsingBlock('ipv4')},
                                                             NopParsingBlock('nop')))

    def test_parse_both(self):
        packet = 'b0487aeccc020c84dc9e9a6108004500003044ca400080065eaac0a80166a29ff2a51' \
                 '64e01bb7c7948b7000000007002ffff4e920000020405b401010402'.decode('hex')

        expected = Container(header=Container(ethernet=Container(dst_mac='b0487aeccc02'.decode('hex'),
                                                                 src_mac='0c84dc9e9a61'.decode('hex'),
                                                                 eth_type=0x800),
                                              ipv4=Container(ihl=20, tos=0, length=48, ipid=0x44ca, flags=0x02,
                                                             frag_offset=0, ttl=128, protocol=6, src_ip='192.168.1.102',
                                                             dst_ip='162.159.242.165')))
        p, off, metadata = self.pg.process(packet, 0, Container())
        self.assertEqual(off, 14 + 20)
        metadata.header.pop('_state')
        self.assertEqual(metadata, expected)

    def test_parse_no_ipv4(self):
        packet = '33330000000c0c84dc9e9a6186dd60000000009a1101fe800000000000004d7e532e418a807c' \
                 'ff02000000000000000000000000000ce6d0076c009a4ddb4d2d534541524348202a20485454502' \
                 'f312e310d0a486f73743a5b464630323a3a435d3a313930300d0a53543a75726e3a4d6963726f73'.decode('hex')
        expected = Container(header=Container(ethernet=Container(dst_mac='33330000000c'.decode('hex'),
                                                                 src_mac='0c84dc9e9a61'.decode('hex'),
                                                                 eth_type=0x86dd)))
        p, off, metadata = self.pg.process(packet, 0, Container())
        self.assertEqual(off, 14)
        metadata.header.pop('_state')
        self.assertEqual(metadata, expected)


class TestEthernetIpv4TcpUdpHeaderParsing(unittest.TestCase):
    def setUp(self):
        self.pg = ProcessingGraph('header',
                                  # FrameParsingBlock('frame'),
                                  EthernetParsingBlock('ethernet'),
                                  ConditionalProcessingBlock('l3',
                                                             lambda metadata: metadata.ethernet.eth_type,
                                                             {0x800: Ipv4ParsingBlock('ipv4')},
                                                             NopParsingBlock('nop')),
                                  ConditionalProcessingBlock('l4',
                                                             lambda metadata: metadata.ipv4.protocol,
                                                             {0x06: TcpParsingBlock('tcp'),
                                                              0x11: UdpParsingBlock('udp')},
                                                             NopParsingBlock('nop')))

    def test_parse_ethernet_ipv4_tcp(self):
        packet = '0c84dc9e9a61b0487aeccc0208004500003458a300003906f785d4b39ad9c0a' \
                 '8016601bb19bd7286f39af2d4bf22801000f5afad00000101050af2d4bf21f2d4bf22'.decode('hex')
        expected = Container(header=Container(ethernet=Container(dst_mac='0c84dc9e9a61'.decode('hex'),
                                                                 src_mac='b0487aeccc02'.decode('hex'),
                                                                 eth_type=0x800),
                                              ipv4=Container(ihl=20, tos=0, length=52, ipid=0x58a3, flags=0x00,
                                                             frag_offset=0, ttl=57, protocol=6,
                                                             src_ip='212.179.154.217',
                                                             dst_ip='192.168.1.102'),
                                              tcp=Container(thl=32, src_port=443, dst_port=6589, seq_num=1921446810,
                                                            ack_num=4074028834, flags=0x010)))
        p, off, metadata = self.pg.process(packet, 0, Container())
        self.assertEqual(off, 14 + 20 + 32)
        metadata.header.pop('_state')
        self.assertEqual(metadata, expected)

    def test_parse_ethernet_ipv4_udp(self):
        packet = 'b0487aeccc020c84dc9e9a6108004500003538ca00008011959fc0a80166d8' \
                 '3ad205d22701bb00213a531c51d78bd61f8fc7ee500e9fbc40128e67414d2c8879b9bc69'.decode('hex')
        expected = Container(header=Container(ethernet=Container(dst_mac='b0487aeccc02'.decode('hex'),
                                                                 src_mac='0c84dc9e9a61'.decode('hex'),
                                                                 eth_type=0x800),
                                              ipv4=Container(ihl=20, tos=0, length=53, ipid=0x38ca, flags=0x00,
                                                             frag_offset=0, ttl=128, protocol=17,
                                                             src_ip='192.168.1.102',
                                                             dst_ip='216.58.210.5'),
                                              udp=Container(src_port=53799, dst_port=443, length=33)))
        p, off, metadata = self.pg.process(packet, 0, Container())
        self.assertEqual(off, 14 + 20 + 8)
        metadata.header.pop('_state')
        self.assertEqual(metadata, expected)

    def test_parse_no_ipv4(self):
        packet = '33330000000c0c84dc9e9a6186dd60000000009a1101fe800000000000004d7e532e418a807c' \
                 'ff02000000000000000000000000000ce6d0076c009a4ddb4d2d534541524348202a20485454502' \
                 'f312e310d0a486f73743a5b464630323a3a435d3a313930300d0a53543a75726e3a4d6963726f73'.decode('hex')
        expected = Container(header=Container(ethernet=Container(dst_mac='33330000000c'.decode('hex'),
                                                                 src_mac='0c84dc9e9a61'.decode('hex'),
                                                                 eth_type=0x86dd)))
        p, off, metadata = self.pg.process(packet, 0, Container())
        self.assertEqual(off, 14)
        metadata.header.pop('_state')
        self.assertEqual(metadata, expected)

    def test_parse_short(self):
        packet = '0c84dc9e9a61b0487aeccc0208004500003458a300003906f785d4b39ad9c0a' \
                 '8016601bb19bd72'.decode('hex')
        self.assertRaises(ParsingError, self.pg.process, packet, 0, Container())


class TestPayloadParsing(unittest.TestCase):
    def setUp(self):
        self.pg = ProcessingGraph('header',
                                  # FrameParsingBlock('frame'),
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
                                  PayloadParsingBlock('payload'))

    def test_tcp_payload_parsing(self):
        packet = 'b0487aeccc020c84dc9e9a6108004500002961a740008006678cc0a80166d4b39ad9' \
                 '19bd01bbf2d4bf217286f39a5010010249a6000000112233'.decode('hex')
        expected_payload = '00112233'.decode('hex')
        p, off, metadata = self.pg.process(packet, 0, Container())
        self.assertEqual(off, len(packet))
        self.assertEqual(expected_payload, metadata.header.payload)

    def test_udp_payload_parsing(self):
        packet = 'b0487aeccc020c84dc9e9a610800450000457fef00008011072bc0a80166adc243bdf8' \
                 '7c01bb0031611f0c2e73961b56660e14d21a2177262761365c8c0d59152cf539db77c1' \
                 'da4e09291868bcf9b350b8c703'.decode('hex')
        expected_payload = '0c2e73961b56660e14d21a2177262761365c8c0d59152cf539db77c1da4e09' \
                           '291868bcf9b350b8c703'.decode('hex')
        p, off, metadata = self.pg.process(packet, 0, Container())
        self.assertEqual(off, len(packet))
        self.assertEqual(expected_payload, metadata.header.payload)

    def test_ethernet_payload_parsing(self):
        packet = '33330000000c0c84dc9e9a6186dd60000000009a1101fe800000000000004d7e532e41' \
                 '8a807cff02000000000000000000000000000ce6d0076c009a4ddb4d2d534541524348' \
                 '202a20485454502f312e310d0a486f73743a5b464630323a3a435d3a313930300d0a53' \
                 '543a75726e3a4d6963726f736f66742057696e646f77732050656572204e616d652052' \
                 '65736f6c7574696f6e2050726f746f636f6c3a2056343a495056363a4c696e6b4c6f63' \
                 '616c0d0a4d616e3a22737364703a646973636f766572220d0a4d583a330d0a0d0a'.decode('hex')
        expected_payload = '60000000009a1101fe800000000000004d7e532e41' \
                           '8a807cff02000000000000000000000000000ce6d0076c009a4ddb4d2d534541524348' \
                           '202a20485454502f312e310d0a486f73743a5b464630323a3a435d3a313930300d0a53' \
                           '543a75726e3a4d6963726f736f66742057696e646f77732050656572204e616d652052' \
                           '65736f6c7574696f6e2050726f746f636f6c3a2056343a495056363a4c696e6b4c6f63' \
                           '616c0d0a4d616e3a22737364703a646973636f766572220d0a4d583a330d0a0d0a'.decode('hex')
        p, off, metadata = self.pg.process(packet, 0, Container())
        self.assertEqual(off, len(packet))
        self.assertEqual(expected_payload, metadata.header.payload)

    def test_ipv4_payload_parsing(self):
        packet = 'b0487aeccc020c84dc9e9a6108004500003c2cfb000080013ba7c0a801670808080808' \
                 '004d5a000100016162636465666768696a6b6c6d6e6f7071727374757677616263646566676869'.decode('hex')
        expected_payload = '08004d5a000100016162636465666768696a6b6c6d6e6f707172737475767' \
                           '7616263646566676869'.decode('hex')
        p, off, metadata = self.pg.process(packet, 0, Container())
        self.assertEqual(off, len(packet))
        self.assertEqual(expected_payload, metadata.header.payload)