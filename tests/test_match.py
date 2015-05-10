import unittest
from openbox.container import Container
from openbox.matcher import RangeMatcher, NumericExactMatcher, NumericOneOfMatcher, StringContainsMatcher, Ipv4CidrMatcher, \
    NotSubmatch, AnySubmatch, AllSubmatch, RegexMatcher, StringExactMatcher, StringOneOfMatcher, MetadataFieldMatcher


class TestRangeMatcher(unittest.TestCase):
    def setUp(self):
        self.match = RangeMatcher(80, 1024)

    def test_in_range(self):
        self.assertEqual(True, self.match.match(100))

    def test_in_range_lower_bound(self):
        self.assertEqual(True, self.match.match(80))

    def test_in_range_upper_bound(self):
        self.assertEqual(True, self.match.match(1024))

    def test_above_range(self):
        self.assertEqual(False, self.match.match(2000))

    def test_below_range(self):
        self.assertEqual(False, self.match.match(2))


class TestNumericExactMatcher(unittest.TestCase):
    def test_match_number(self):
        self.assertEqual(True, NumericExactMatcher(80).match(80))

    def test_no_match_number(self):
        self.assertEqual(False, NumericExactMatcher(80).match(90))


class TestStringExactMatcher(unittest.TestCase):
    def test_match_string(self):
        self.assertEqual(True, StringExactMatcher('pavel').match('pavel'))

    def test_no_match_string(self):
        self.assertEqual(False, StringExactMatcher('pavel').match('pavell'))


class TestNumericOneOfMatcher(unittest.TestCase):
    def test_match_number(self):
        self.assertEqual(True, NumericOneOfMatcher([80, 90, 100]).match(80))

    def test_no_match_number(self):
        self.assertEqual(False, NumericOneOfMatcher([80, 90, 100]).match(200))


class TestStringOneOfMatcher(unittest.TestCase):
    def test_match_string(self):
        self.assertEqual(True, StringOneOfMatcher(['pavel', 'yotam']).match('pavel'))

    def test_no_match_string(self):
        self.assertEqual(False, StringOneOfMatcher(['pavel', 'yotam']).match('no_pavel'))


class TestStringContainsMatcher(unittest.TestCase):
    def test_match_full_string(self):
        self.assertEqual(True, StringContainsMatcher('pavel').match('pavel'))

    def test_match_substring(self):
        self.assertEqual(True, StringContainsMatcher('ave').match('pavel'))

    def test_no_match(self):
        self.assertEqual(False, StringContainsMatcher('pavelll').match('pavel'))


class TestIpv4CidrMatcher(unittest.TestCase):
    # TODO: add exception tests for illegal IPv4 or subnet
    def test_match(self):
        self.assertEqual(True, Ipv4CidrMatcher("127.0.0.0/8").match('127.0.0.1'))

    def test_no_match(self):
        self.assertEqual(False, Ipv4CidrMatcher('8.8.0.0/16').match('8.9.1.1'))


class TestNotSubmatch(unittest.TestCase):
    def test_match_number(self):
        self.assertEqual(False, NotSubmatch(NumericExactMatcher(80)).match(80))

    def test_no_match_number(self):
        self.assertEqual(True, NotSubmatch(NumericExactMatcher(80)).match(90))


class TestAnySubmatch(unittest.TestCase):
    def setUp(self):
        self.matcher = AnySubmatch(RangeMatcher(80, 110), RangeMatcher(100, 200))

    def test_match_matcher1(self):
        self.assertEqual(True, self.matcher.match(80))

    def test_match_matcher2(self):
        self.assertEqual(True, self.matcher.match(150))

    def test_both_match(self):
        self.assertEqual(True, self.matcher.match(105))

    def test_no_match(self):
        self.assertEqual(False, self.matcher.match(300))


class TestRegexMatcher(unittest.TestCase):
    def setUp(self):
        self.matcher = RegexMatcher("pavel.*yotam")

    def test_match_both(self):
        self.assertEqual(True, self.matcher.match('pavel and yotam'))

    def test_no_match_matcher1(self):
        self.assertEqual(False, self.matcher.match('pavel working hard'))

    def test_no_match_matcher2(self):
        self.assertEqual(False, self.matcher.match('so is yotam'))

    def test_no_match_any_matcher(self):
        self.assertEqual(False, self.matcher.match('and no one else'))


class TestAllMatch(unittest.TestCase):
    def setUp(self):
        self.matcher = AllSubmatch(StringContainsMatcher("pavel"), StringContainsMatcher('yotam'))

    def test_match_both(self):
        self.assertEqual(True, self.matcher.match('pavel and yotam'))

    def test_no_match_matcher1(self):
        self.assertEqual(False, self.matcher.match('pavel working hard'))

    def test_no_match_matcher2(self):
        self.assertEqual(False, self.matcher.match('so is yotam'))

    def test_no_match_any_matcher(self):
        self.assertEqual(False, self.matcher.match('and no one else'))


class TestMetadataFieldMatch(unittest.TestCase):
    def setUp(self):
        self.mtd = Container(a=Container(b=Container(num=80, s="pavel", ip="8.8.8.8")))

    def test_match_numeric(self):
        self.assertEqual(True, MetadataFieldMatcher("a.b.num", NumericExactMatcher(80)).match(self.mtd))

    def test_match_string(self):
        self.assertEqual(True, MetadataFieldMatcher("a.b.s", StringExactMatcher('pavel')).match(self.mtd))

    def test_no_match(self):
        self.assertEqual(False, MetadataFieldMatcher('a.b.num', NumericExactMatcher(90)).match(self.mtd))

    def test_no_field(self):
        self.assertEqual(False, MetadataFieldMatcher('no.field.here', NumericExactMatcher(80)).match(self.mtd))


class TestCompositeMetadataMatch(unittest.TestCase):
    def setUp(self):
        self.mtd = Container(a=Container(b=Container(num=80, s="pavel", ip="8.8.8.8")))

    def test_any_match(self):
        matcher1 = MetadataFieldMatcher("a.b.num", NumericExactMatcher(80))
        matcher2 = MetadataFieldMatcher('a.b.s', StringExactMatcher('pavel'))
        self.assertEqual(True, AnySubmatch(matcher1, matcher2).match(self.mtd))

    def test_any_no_match(self):
        matcher1 = MetadataFieldMatcher("a.b.num", NumericExactMatcher(90))
        matcher2 = MetadataFieldMatcher('a.b.s', StringExactMatcher('adsf'))
        self.assertEqual(False, AnySubmatch(matcher1, matcher2).match(self.mtd))

    def test_all_match(self):
        matcher1 = MetadataFieldMatcher("a.b.num", NumericExactMatcher(80))
        matcher2 = MetadataFieldMatcher('a.b.s', StringExactMatcher('pavel'))
        self.assertEqual(True, AllSubmatch(matcher1, matcher2).match(self.mtd))

    def test_all_no_match(self):
        matcher1 = MetadataFieldMatcher("a.b.num", NumericExactMatcher(88))
        matcher2 = MetadataFieldMatcher('a.b.s', StringExactMatcher('pavel'))
        self.assertEqual(False, AllSubmatch(matcher1, matcher2).match(self.mtd))

