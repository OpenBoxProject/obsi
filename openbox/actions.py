import sys
from openbox.core import ActionBlock
from openbox.pcap import PcapWriter


class DumpMetadataAction(ActionBlock):
    """
    Output the packet's metadata
    """

    def __init__(self, name, output=sys.stdout):
        """
        Initialize an action that will dump the metadata to output

        :param name: The actions name
        :type name: str
        :param output: The object to write to
        """
        super(DumpMetadataAction, self).__init__(name)
        self.output = output

    def process(self, packet, offset, metadata, *args, **kw):
        self.output.write(str(metadata))
        return packet, offset, metadata


class AppendToPcapAction(ActionBlock):
    """
    Append a packet to the end of the pcap of file
    """

    def __init__(self, name, filename):
        """
        Initialize an action block that writes a packet to the end of a pcap file

        :param name: The name of the action
        :type name: str
        :param filename: The pcap's file name
        :type filename: basestring
        """
        super(AppendToPcapAction, self).__init__(name)
        self.writer = PcapWriter(filename)

    def process(self, packet, offset, metadata, *args, **kw):
        self.writer.write_packet(packet)
        return packet, offset, metadata

    def __del__(self):
        self.writer.close()

    def close(self):
        self.writer.close()

class MatchedRulesActions(ActionBlock):
    """
    Do an action based on a matched rules.
    An action will be done for each matched rule, based on the order of the matched rules.
    """

    def __init__(self, name, matched_rules_field_name, mapping, default_action=None):
        """
        Initialize a mapping between matched rules names to actions to preform

        :param name: The name of the actions block
        :type name: str
        :param matched_rules_field_name: The field name in the metadata that holds the matched rules
        :type matched_rules_field_name: str
        :param mapping: A mapping between a matched rule and the action to take
        :type mapping: dict
        :param default_action: Default action to preform in case there where no matches or no action to matched rules
        :type default_action: ActionBlock
        """
        super(MatchedRulesActions, self).__init__(name)
        self.matched_rules_field_name = matched_rules_field_name
        self.mapping = mapping
        self.default_action = default_action

    def process(self, packet, offset, metadata, *args, **kw):
        matched_rules = metadata.get_path(self.matched_rules_field_name) or []
        matched_action = False
        for matched_rule in matched_rules:
            action = self.mapping.get(matched_rule, None)
            if action:
                matched_action = True
                packet, offset, metadata = action.process(packet, offset, metadata, *args, **kw)
        if not matched_action and self.default_action:
            return self.default_action.process(packet,offset, metadata)
        else:
            return packet, offset, metadata

    def close(self):
        for action in self.mapping.itervalues():
            try:
                action.close()
            except AttributeError:
                pass
        if self.default_action:
            try:
                self.default_action.close()
            except AttributeError:
                pass

