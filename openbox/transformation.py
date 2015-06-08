"""
Doing transformation on buffers (e.g. compress, decompress, encrypt, etc)
"""
import zlib

from openbox.container import Container


class Transformator(object):
    """
    Abstract helper class to allow the creation of transformation blocks easily.

    Most implementations will need to override the 3 private methods:
    _prepare_buffer, _transform_buffer, _post_transform
    """
    def _prepare_buffer(self, packet, offset, metadata, *args, **kw):
        """
        Prepare the buffer for transformation.

        Extract the relevant part to be transformed from the packet or metadata
        :param packet: The packet to do the processing on
        :type packet: str
        :param offset: The current offset in the packet where the processing should start
        :type offset: int
        :param metadata: The metadata for the packet, as processed so far
        :type metadata: Container
        :param args: additional args to be passed from the processing block
        :param kw: additional kw args to be passed from the processing block
        :return: buffer to do the transformation on
        :rtype: str
        """
        raise NotImplementedError

    def _transform_buffer(self, buffer):
        """
        Do a transformation on the buffer

        :param buffer: The buffer to the transformation on
        :type buffer: str
        :return: Transformed buffer
        :rtype: str
        """
        raise NotImplementedError

    def _post_transform(self, packet, offset, metadata, transformed_buffer, *args, **kw):
        """
        Update the metadata or the packet for the rest of the processing chain

        :param packet: The packet to do the processing on
        :type packet: str
        :param offset: The current offset in the packet where the processing should start
        :type offset: int
        :param metadata: The metadata for the packet, as processed so far
        :type metadata: Container
        :param transformed_buffer: The transformed buffer
        :type: str
        :param args: additional args to be passed from the processing block
        :param kw: additional kw args to be passed from the processing block
        :return: (updated_packet, updated_offset, updated_metadata
        :rtype: tuple(str, int, Container)
        """
        raise NotImplementedError

    def transform(self, packet, offset, metadata, *args, **kw):
        """
        The transformation function that will be called by the transformation block.

        Usually you will not want to overwrite the default implementation but one of the internal helper functions.

        :param packet: The packet to do the processing on
        :type packet: str
        :param offset: The current offset in the packet where the processing should start
        :type offset: int
        :param metadata: The metadata for the packet, as processed so far
        :type metadata: Container
        :param args: additional args to be passed from the processing block
        :param kw: additional kw args to be passed from the processing block
        :return: (updated_packet, updated_offset, updated_metadata
        :rtype: tuple(str, int, Container)
        """
        buffer_to_transform = self._prepare_buffer(packet, offset, metadata, *args, **kw)
        transformed_buffer = self._transform_buffer(buffer_to_transform)
        return self._post_transform(packet, offset, metadata, transformed_buffer, *args, **kw)


class SingleFieldTransformator(Transformator):
    """
    Take a single field from the metadata and apply a simple function on it.
    """

    def __init__(self, input_field, output_field, transformation_func):
        self.input_field = input_field
        self.output_field = output_field
        self.transformation_func = transformation_func

    def _prepare_buffer(self, packet, offset, metadata, *args, **kw):
        return metadata.get(self.input_field, None)

    def _transform_buffer(self, buffer):
        return self.transformation_func(buffer)

    def _post_transform(self, packet, offset, metadata, transformed_buffer, *args, **kw):
        metadata.set_path(self.output_field, transformed_buffer)
        return packet, offset, metadata


class GzipCompress(SingleFieldTransformator):
    """
    Compress a single field using gzip
    """

    def __init__(self, input_field, output_field):
        transformation_func = zlib.compress
        super(GzipCompress, self).__init__(input_field, output_field, transformation_func)


class GzipDecompress(SingleFieldTransformator):
    """
    Decompress a single field using gzip
    """
    def __init__(self, input_field, output_field):
        transformation_func = zlib.decompress
        super(GzipDecompress, self).__init__(input_field, output_field, transformation_func)