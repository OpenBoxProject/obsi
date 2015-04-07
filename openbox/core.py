"""
Core classes
"""
from openbox.container import Container


class ProcessingGraph(object):
    """
    A combination of processing blocks that form a processing graph for the packet
    """
    def __init__(self, name, *blocks):
        """
        Initialize a processing graph with a list of the processing blocks

        :param name: The name of the processing block
        :type name: str
        :param blocks: The processing blocks that form the graph
        :type blocks: list(ProcessingBlock)
        """
        self.name = name
        self.blocks = blocks

    def process(self, packet, offset=0, metadata=None):
        """
        Process a packet with a processing graph

        :param packet: The packet to do the processing on
        :type packet: str
        :param offset: The current offset in the packet where the processing should start
        :type offset: int
        :param metadata: The metadata for the packet, as processed so far
        :type metadata: Container
        :return: (new_packet, next_offset, updated_metadata)
        :rtype: tuple(str, int, Container)
        """
        current_metadata = Container()

        for block in self.blocks:
            packet, offset, current_metadata = block.process(packet, offset, current_metadata)

        # create an hierarchy within the metadata
        if metadata is None:
            metadata = Container()
        metadata[self.name] = current_metadata

        return packet, offset, metadata


class ProcessingBlock(object):
    """
    An abstract block in the processing graph.

    All types of nodes/blocks should inherit from it.
    """

    def __init__(self, name):
        """
        Initialize a processing block.

        :param name: The name/identifier of the processing block
        :type name: str
        """
        self.name = name

    def process(self, packet, offset, metadata, *args, **kw):
        """
        Process a packet and it's accompanying metadata.

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
        raise NotImplementedError


class MetadataExtractingBlock(ProcessingBlock):
    """
    Base class for all processing blocks that extract metadata from the packet.
    """

    def process(self, packet, offset, metadata, *args, **kw):
        """
        Process a packet and it's accompanying metadata and extract more metadata from the packet.

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
        pass


class ParsingBlock(MetadataExtractingBlock):
    """
    Base class for all parsing block.

    Each parsing block should extract specific network layer data from the packet or session.
    """

    def process(self, packet, offset, metadata, *args, **kw):
        """
        Parse more metadata from the packet at the current offset.

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
        raise NotImplementedError


class TransformationBlock(ProcessingBlock):
    """
    Transformation block.

    This block executes a transformation function on a buffer extracted from the packet and/or it's metadata.
    """

    def __init__(self, name, transformator, pre_transformation, post_transformation):
        """
        Initialize a transformation block.

        :param name: The name of the block
        :param transformator: The transformation function or object that receives a buffer and
                              returns a transformed buffer
        :param pre_transformation: A function that will prepare the data for transformation
                                   (e.g. extract the payload fro m the packet)
        :param post_transformation: A function that will put back the transformed buffer in to the packet or metadata
        """
        super(TransformationBlock, self).__init__(name)
        self.post_transformation = post_transformation
        self.pre_transformation = pre_transformation
        self.transformator = transformator

    def process(self, packet, offset, metadata, *args, **kw):
        """
        Do a transformation on a buffer

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
        buffer = self.pre_transformation(packet, offset, metadata, *args, **kw)
        new_buffer = self.transformator(buffer)
        return self.post_transformation(new_buffer, *args, **kw)


class RulesMatchingBlock(ProcessingBlock):
    """
    Match rules based on the packet and the metadata
    """

    def process(self, packet, offset, metadata, *args, **kw):
        """
        Do rules matching on the metadata.  

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
        raise NotImplementedError


class ActionBlock(ProcessingBlock):
    """
    Action based on the packet and it's metadata
    """

    def process(self, packet, offset, metadata, *args, **kw):
        """
        Do an action based on the metadata.

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
        raise NotImplementedError
