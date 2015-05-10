"""
rules set module
"""
from openbox.core import ProcessingBlock


class RulesBlock(ProcessingBlock):
    """
    Match a set of rules against the packet and it's data
    """

    def __init__(self, name, *rules):
        """
        Initialize a processing block that will match a list of rules
        :param name: The name of the processing block
        :type name: str
        :param rules: A set of rules to match with the metadata
        :type rules: list(Rule)
        """
        super(RulesBlock, self).__init__(name)
        self.rules = rules

    def process(self, packet, offset, metadata, *args, **kw):
        """
        Try to match each rule against the metadata, add only the matched rules

        :param packet: The packet to do the processing on
        :type packet: str
        :param offset: The current offset in the packet where the processing should start
        :type offset: int
        :param metadata: The metadata for the packet, as processed so far
        :type metadata: Container
        :param args: additional args to be passed to the processing block
        :param kw: additional kw args to be passed to the processing block
        :return: (new_packet, next_offset, updated_metadata)
        :rtype: tuple(str, int, Container)
        """
        matched_rules = tuple(rule.name for rule in self.rules if rule.match(metadata))
        metadata[self.name] = matched_rules

        return packet, offset, metadata