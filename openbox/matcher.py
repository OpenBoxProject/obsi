"""
Matching logic module
"""
import re
import socket
import struct
from openbox.exception import MatchInitError


class Matcher(object):
    """
    An abstract Matcher object that defines the interface for object that check if a value is matched to a rule or not
    """
    def match(self, value):
        """
        Check if the value is match to the matching rules defined by the object

        :param value: The value we need to check against the rules
        :return: True iff the value is matched by the set of rules
        :rtype: bool
        """
        raise NotImplementedError


class RangeMatcher(Matcher):
    """
    Check to see if a numeral value is between the lower and upper bound
    """

    def __init__(self, lower, upper):
        """
        Initialize a RangeMatcher object that checks if a value is between lower and upper bound

        :param lower: The lower bound of the value (including)
        :type lower: int or long or float
        :param upper: The upper bound of the value (including)
        :type upper: int or long or float
        """
        self.lower = lower
        self.upper = upper

    def match(self, value):
        return self.lower <= value <= self.upper


class ExactMatcher(Matcher):
    """
    Check if the value is an exact match to a single value.

    Because of the dynamic nature of python this support all objects that has __eq__ defined.
    """
    def __init__(self, other):
        """
        Initialize an ExactMatcher object that checks if a value is equal the other value
        :param other: The value to compare to
        """
        self.other = other

    def match(self, value):
        return value == self.other


class OneOfMatcher(Matcher):
    """
    Check if the value is one of a list of values to compare to

    Because of the dynamic nature of python this support all objects that has __eq__ defined.
    """
    def __init__(self, values):
        """
        Initialize a match that check if a value is one of the supplied values

        :param values: A list of values to compare to
        :type values: list or tuple
        """
        self.values = values

    def match(self, value):
        return value in self.values


class StringContainsMatcher(Matcher):
    """
    Check if there is a substring inside the value we check
    """

    def __init__(self, substring):
        """
        Initialize a check if the value contains a substring

        :param substring: The substring we check that is contained in the value we check
        :type substring: basestring
        """
        self.substring = substring

    def match(self, value):
        return self.substring in value


class RegexMatcher(Matcher):
    """
    Check if the value matches a RegEx
    """

    def __init__(self, regex, flags=0):
        """
        Initialize a RegEx matcher, with the regex string and regex compile flags

        :param regex: The regex to use
        :type regex: basestring
        :param flags: The flags to pass to re.compile function
        :type flags: int
        """
        self.regex = re.compile(regex, flags)

    def match(self, value):
        # if we have a match a SRE_Match object will be returned, otherwise None will be returned
        return self.regex.match(value) is not None


class Ipv4CidrMatcher(Matcher):
    """
    Check if an IPv4 address is in a belongs to a subnet represented in a CIDR representation.
    """
    def __init__(self, network):
        try:
            ip, mask = network.split('/')
        except ValueError:
            raise MatchInitError("{network} has no subnet definition. Use a.b.c.d/XX format".format(network=network))
        mask = int(mask)
        if mask < 0 or mask > 32:
            raise MatchInitError("Subnet mask value must be in the range [0, 32]")

        self.subnet_mask = (0xffffffff << (32 - mask)) & 0xffffffff
        self.network, = struct.unpack('!I', socket.inet_aton(ip))
        self.network &= self.subnet_mask

    def match(self, value):
        ip, = struct.unpack('!I', socket.inet_aton(value))
        return self.network == (ip & self.subnet_mask)


class AnySubmatch(Matcher):
    """
    Check if ANY of the submatch objects match the value.
    This can be used to implement an OR logic between Matcher objects
    """
    def __init__(self, *matchers):
        """
        Initialize a list of matchers that only one of them need to be matched.

        :param matchers: A list of matchers
        """
        self.matchers = matchers

    def match(self, value):
        return any(matcher.match(value) for matcher in self.matchers)


class AllSubmatch(Matcher):
    """
    Check if ALL of the submatch objects match the value.
    This can be used to implement an AND logic between Matcher objects
    """
    def __init__(self, *matchers):
        """
        Initialize a list of matchers that all of them need to be matched.

        :param matchers: A list of matchers
        """
        self.matchers = matchers

    def match(self, value):
        return all(matcher.match(value) for matcher in self.matchers)


class NotSubmatch(Matcher):
    """
    Allow to implement a NOT logic by negating the result of a sub matcher
    """

    def __init__(self, submatcher):
        """

        :param submatcher: The submatcher to negate it result
        """
        self.submatcher = submatcher

    def match(self, value):
        return not self.submatcher.match(value)