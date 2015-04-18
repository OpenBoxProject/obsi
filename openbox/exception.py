"""
Exceptions module
"""


class OpenBoxError(Exception):
    """
    The parent of all exceptions of this module
    """
    pass


class ProcessingBlockError(OpenBoxError):
    """
    An exception in a processing block of the graph.
    """
    pass


class ProcessingGraphError(OpenBoxError):
    """
    An exception in the processing graph
    """
    pass


class MetadataExtractionError(ProcessingBlockError):
    """
    An exception has occurred in a MetadataExtractionBlock
    """
    pass


class ParsingError(MetadataExtractionError):
    """
    A parsing error has occurred
    """
    pass


class TransformationError(ProcessingBlockError):
    """
    A transformation error has occurred
    """
    pass


class RulesMatchingError(ProcessingBlockError):
    """
    A rules matching error has occurred
    """
    pass

class MatchInitError(RulesMatchingError):
    """
    An error occurred when tring to initialize a Matcher object
    """