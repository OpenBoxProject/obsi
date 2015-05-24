import os
import unittest
from openbox.actions import MatchedRulesActions, AppendToPcapAction
from openbox.core import Application, ProcessingGraph, ConditionalProcessingBlock
from openbox.matcher import Rule
from openbox.parsing import (FrameParsingBlock, EthernetParsingBlock, Ipv4ParsingBlock, NopParsingBlock,
                             TcpParsingBlock, UdpParsingBlock, PayloadParsingBlock)
from openbox.pcap import PcapReader
from openbox.rules import RulesBlock
from openbox.matcher import MetadataFieldMatcher, NumericExactMatcher, AnySubmatch, StringContainsMatcher


class TestLoadBalancer(unittest.TestCase):
    def setUp(self):
        header_parsing = ProcessingGraph('header',
                                         FrameParsingBlock('frame'),
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

        # create rules to match a string, udp, http and https trafic
        http_rule = Rule('http',
                         AnySubmatch(MetadataFieldMatcher('header.tcp.src_port', NumericExactMatcher(80)),
                                     MetadataFieldMatcher('header.tcp.dst_port', NumericExactMatcher(80)))
                         )
        https_rule = Rule('https',
                          AnySubmatch(MetadataFieldMatcher('header.tcp.src_port', NumericExactMatcher(443)),
                                      MetadataFieldMatcher('header.tcp.dst_port', NumericExactMatcher(443)))
                          )
        udp_rule = Rule('udp', MetadataFieldMatcher('header.ipv4.protocol', NumericExactMatcher(0x11)))
        xnet_string_rule = Rule('xnet_string', MetadataFieldMatcher('header.payload', StringContainsMatcher('xnet')))
        rules = RulesBlock('rules', xnet_string_rule, udp_rule, http_rule, https_rule)

        # create actions for rules that output to a specifiec file
        rules_mapping = {'xnet_string': AppendToPcapAction('xnet_string_action', 'pcaps/test_load_balance_xnet.pcap'),
                         'udp': AppendToPcapAction('udp', 'pcaps/test_load_balance_udp.pcap'),
                         'http': AppendToPcapAction('http', 'pcaps/test_load_balance_http.pcap'),
                         'https': AppendToPcapAction('https', 'pcaps/test_load_balance_https.pcap'),
                         }

        default_action = AppendToPcapAction('https', 'pcaps/test_load_balance_default.pcap')
        actions = MatchedRulesActions('actions', 'rules', rules_mapping, default_action=default_action)

        load_balancing = ProcessingGraph('LoadBalncer', header_parsing, rules, actions)
        
        self.lb = Application(PcapReader('pcaps/test_load_balance.pcap'), load_balancing)

    def tearDown(self):
        os.unlink('pcaps/test_load_balance_xnet.pcap')
        os.unlink('pcaps/test_load_balance_udp.pcap')
        os.unlink('pcaps/test_load_balance_http.pcap')
        os.unlink('pcaps/test_load_balance_https.pcap')
        os.unlink('pcaps/test_load_balance_default.pcap')

    def test_load_balance(self):
        self.lb.start()
        self.lb.close()

        # we assert on the amount of packets in each file
        with PcapReader('pcaps/test_load_balance_xnet.pcap') as reader:
            packets = reader.read()
            self.assertEqual(len(packets), 15)

        with PcapReader('pcaps/test_load_balance_udp.pcap') as reader:
            packets = reader.read()
            self.assertEqual(len(packets), 1667)

        with PcapReader('pcaps/test_load_balance_http.pcap') as reader:
            packets = reader.read()
            self.assertEqual(len(packets), 1456)

        with PcapReader('pcaps/test_load_balance_https.pcap') as reader:
            packets = reader.read()
            self.assertEqual(len(packets), 1079)

        with PcapReader('pcaps/test_load_balance_default.pcap') as reader:
            packets = reader.read()
            self.assertEqual(len(packets), 9)
