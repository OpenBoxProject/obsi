import unittest
from openbox.container import Container
from openbox.rules import RulesBlock
from openbox.matcher import Rule, MetadataFieldMatcher, Ipv4CidrMatcher, StringExactMatcher, NumericExactMatcher


class TestRulesBlock(unittest.TestCase):
    def setUp(self):
        self.metadata = Container(a=Container(b=Container(num=80, s="pavel", ip="8.8.8.8")))

    def test_single_rule_single_match(self):
        rules = RulesBlock('rules', Rule('match_ip', MetadataFieldMatcher('a.b.ip', Ipv4CidrMatcher('8.8.8.0/24'))))
        p, l, metadata = rules.process('', 0, self.metadata)
        self.assertEqual(metadata.rules, ['match_ip'])

    def test_single_rule_no_match(self):
        rules = RulesBlock('rules', Rule('match_ip', MetadataFieldMatcher('a.b.ip', Ipv4CidrMatcher('9.9.9.0/24'))))
        p, l, metadata = rules.process('', 0, self.metadata)
        self.assertEqual(metadata.rules, [])

    def test_multiple_rules_single_match(self):
        rules = RulesBlock('rules',
                           Rule('match_ip', MetadataFieldMatcher('a.b.ip', Ipv4CidrMatcher('8.8.8.0/24'))),
                           Rule('no_match', MetadataFieldMatcher('a.b.s', StringExactMatcher("nop")))
                           )

        p, l, metadata = rules.process('', 0, self.metadata)
        self.assertEqual(metadata.rules, ['match_ip'])

    def test_multiple_rules_multiple_matches(self):
        rules = RulesBlock('rules',
                           Rule('match_ip', MetadataFieldMatcher('a.b.ip', Ipv4CidrMatcher('8.8.8.0/24'))),
                           Rule('no_match', MetadataFieldMatcher('a.b.s', StringExactMatcher("nop"))),
                           Rule('number_match', MetadataFieldMatcher('a.b.num', NumericExactMatcher(80))),
                           )

        p, l, metadata = rules.process('', 0, self.metadata)
        self.assertEqual(metadata.rules, ['match_ip', 'number_match'])