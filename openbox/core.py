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
        current_metadata._state = Container(last_processed=None)

        for block in self.blocks:
            packet, offset, current_metadata = block.process(packet, offset, current_metadata)
            if isinstance(block, ConditionalProcessingBlock):
                current_metadata._state.last_processed = block.processing_block
            else:
                current_metadata._state.last_processed = block

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


class NopProcessingBlock(ProcessingBlock):
    """
    No operation processing block
    """
    def process(self, packet, offset, metadata, *args, **kw):
        return packet, offset, metadata


class ConditionalProcessingBlock(ProcessingBlock):
    """
    Select a processing block based on the metadata extracted so far.
    The selection is done during running time when the necessary metadata is available.
    """
    def __init__(self, name, condition_func, condition_to_block_mapping, default=None):
        """
        Initialize a conditional processing block.

        The block will be chosen during runtime from the metadata.
        The condition_func will generate a value for  each condition based on the metadata,
        and each value should have mapping to a ProcessingBlock.
        If no mapping is found then a default block will be used.
        :param name: The name of the block (will not be used)
        :param condition_func: A function that generates a value based on the metadata,
                               each value can be mapped to a processing block
        :type condition_func: function
        :param condition_to_block_mapping: Map each value to a processing block
        :type condition_to_block_mapping: dict
        :param default: The default processing block to use when there is no suitable mapping
        :type default: ProcessingBlock
        """
        super(ConditionalProcessingBlock, self).__init__(name)
        self._condition_func = condition_func
        self._condition_to_block_mapping = condition_to_block_mapping
        self._default = default or NopProcessingBlock("nop")
        self.processing_block = None

    def process(self, packet, offset, metadata, *args, **kw):
        try:
            condition_type = self._condition_func(metadata)
        except AttributeError:
            # The function is trying to get a field that does not exist
            condition_type = None
        self.processing_block = self._condition_to_block_mapping.get(condition_type, self._default)
        return self.processing_block.process(packet, offset, metadata)


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

    def parse_payload(self, packet, offset, metadata):
        """
        Parse the payload of this layer.

        :param packet: The packet to do the processing on
        :type packet: str
        :param offset: The current offset in the packet where the paylaod should start
        :type offset: int
        :param metadata: The metadata for the packet, as processed so far
        :type metadata: Container
        :return: raw payload of this layer
        :rtype: str
        """
        # default implementation will be to treat the rest of the packet as the payload
        return packet[offset:]


class TransformationBlock(ProcessingBlock):
    """
    Transformation block.

    This block executes a transformation function on a buffer extracted from the packet and/or it's metadata.
    """

    def __init__(self, name, transformator):
        """
        Initialize a transformation block.

        :param name: The name of the block
        :param transformator: The transformation object that does the actuall transformation.
                              It's transform function will be called.
        """
        super(TransformationBlock, self).__init__(name)
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
        if 'transformation_block_name' not in kw:
            kw['transformation_block_name'] = self.name
        return self.transformator.transform(packet, offset, metadata, *args, **kw)


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
