import unittest
from openbox.matcher import RangeMatcher, ExactMatcher, OneOfMatcher, StringContainsMatcher, Ipv4CidrMatcher, \
    NotSubmatch, AnySubmatch, AllSubmatch, RegexMatcher


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


class TestExactMatcher(unittest.TestCase):
    def test_match_number(self):
        self.assertEqual(True, ExactMatcher(80).match(80))

    def test_no_match_number(self):
        self.assertEqual(False, ExactMatcher(80).match(90))

    def test_match_string(self):
        self.assertEqual(True, ExactMatcher('pavel').match('pavel'))

    def test_no_match_string(self):
        self.assertEqual(False, ExactMatcher('pavel').match('pavell'))


class TestOneOfMatcher(unittest.TestCase):
    def test_match_number(self):
        self.assertEqual(True, OneOfMatcher([80, 90, 100]).match(80))

    def test_no_match_number(self):
        self.assertEqual(False, OneOfMatcher([80, 90, 100]).match(200))

    def test_match_string(self):
        self.assertEqual(True, OneOfMatcher(['pavel', 'yotam']).match('pavel'))

    def test_no_match_string(self):
        self.assertEqual(False, OneOfMatcher(['pavel', 'yotam']).match('no_pavel'))


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
        self.assertEqual(False, NotSubmatch(ExactMatcher(80)).match(80))

    def test_no_match_number(self):
        self.assertEqual(True, NotSubmatch(ExactMatcher(80)).match(90))


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



