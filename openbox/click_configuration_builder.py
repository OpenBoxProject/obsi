"""
Transforms an OpenBox configuration in to a Click's configuration
"""


class ClickConfigurationBuilder(object):
    def __init__(self):
        self.processing_blocks = []
        self.match_fields = []
        self.protocol_analyser_protocols = []