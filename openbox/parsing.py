"""
Network Parsing Blocks
"""
import socket
import time
import struct
from openbox.container import Container
from openbox.core import ParsingBlock, NopProcessingBlock
from struct import Struct
from openbox.exception import ParsingError


class FrameParsingBlock(ParsingBlock):
    """
    Addes initial metadata about the frame, such it's full captured length and timestamp
    """

    def process(self, packet, offset, metadata, *args, **kw):
        metadata[self.name] = Container(timestamp=time.time(), length=(len(packet) - offset))
        return packet, offset, metadata


class EthernetParsingBlock(ParsingBlock):
    """
    Parse Ethernet layer information from the packet
    """
    _UNPACKER = Struct('!6s6sH')

    def process(self, packet, offset, metadata, *args, **kw):
        layer_length = self._UNPACKER.size
        try:
            dst_mac, src_mac, eth_type = self._UNPACKER.unpack(packet[offset:offset + layer_length])
        except struct.error:
            raise ParsingError('Packet too short for Ethernet parsing from offset %d' % offset)
        offset += layer_length
        metadata[self.name] = Container(dst_mac=dst_mac, src_mac=src_mac, eth_type=eth_type)
        return packet, offset, metadata


class Ipv4ParsingBlock(ParsingBlock):
    """
    Parse IPv4 layer information from the packet
    """
    _UNPACKER = Struct("!BBHHHBBH4s4s")

    def process(self, packet, offset, metadata, *args, **kw):
        layer_length = self._UNPACKER.size
        try:
            (version_and_ihl, tos, length, ipid, frag, ttl,
             protocol, checksum, src_ip, dst_ip) = self._UNPACKER.unpack(packet[offset:offset + layer_length])
        except struct.error:
            raise ParsingError('Packet too short for IPv4 parsing from offset %d' % offset)

        ihl = (version_and_ihl & 0x0f) * 4
        flags = (frag >> 13) & 0x7
        frag_offset = frag & 0x1fff
        src_ip = socket.inet_ntoa(src_ip)
        dst_ip = socket.inet_ntoa(dst_ip)
        offset += ihl
        metadata[self.name] = Container(tos=tos, ihl=ihl, length=length, ipid=ipid, flags=flags,
                                        frag_offset=frag_offset,
                                        ttl=ttl, protocol=protocol, src_ip=src_ip, dst_ip=dst_ip)

        return packet, offset, metadata

    def parse_payload(self, packet, offset, metadata):
        ipv4_metadata = metadata.get(self.name, None)
        if ipv4_metadata is None:
            return None

        declared_payload_length = ipv4_metadata.length - ipv4_metadata.ihl

        # in python if you try to read more then the buffer holds the result will be trunked
        return packet[offset:offset + declared_payload_length]


class TcpParsingBlock(ParsingBlock):
    """
    Parse TCP layer information from the packet
    """
    _UNPACKER = Struct("!HHIIHHHH")

    def process(self, packet, offset, metadata, *args, **kw):
        layer_length = self._UNPACKER.size
        try:
            (src_port, dst_port, seq, ack, offset_and_flags,
             window_size, checksum, urgent) = self._UNPACKER.unpack(packet[offset:offset + layer_length])
        except struct.error:
            raise ParsingError('Packet too short for Tcp parsing from offset %d' % offset)

        thl = ((offset_and_flags >> 12) & 0xf) * 4
        flags = offset_and_flags & 0x1ff
        offset += thl
        metadata[self.name] = Container(thl=thl, src_port=src_port, dst_port=dst_port, seq_num=seq, ack_num=ack,
                                        flags=flags)

        return packet, offset, metadata


class UdpParsingBlock(ParsingBlock):
    """
    Parse UDP layer information from the packet
    """
    _UNPACKER = Struct('!HHHH')

    def process(self, packet, offset, metadata, *args, **kw):
        layer_length = self._UNPACKER.size
        try:
            (src_port, dst_port, length, checksum) = self._UNPACKER.unpack(packet[offset:offset + layer_length])
        except struct.error:
            raise ParsingError

        offset += layer_length
        metadata[self.name] = Container(src_port=src_port, dst_port=dst_port, length=length)

        return packet, offset, metadata

    def parse_payload(self, packet, offset, metadata):
        udp_metadata = metadata.get(self.name, None)
        if udp_metadata is None:
            return None

        maximum_declared_length = udp_metadata.length - self._UNPACKER.size

        # in python if you try to read more then the buffer holds the result will be trunked
        return packet[offset:offset + maximum_declared_length]


class NopParsingBlock(ParsingBlock, NopProcessingBlock):
    """
    No operation parsing block
    """
    def process(self, packet, offset, metadata, *args, **kw):
        return packet, offset, metadata


class PayloadParsingBlock(ParsingBlock):
    """
    Parse packet payload based on the packet structure.
    """

    def process(self, packet, offset, metadata, *args, **kw):
        last_processed = metadata._state.last_processed
        if last_processed:
            payload = last_processed.parse_payload(packet, offset, metadata)
        else:
            # nothing was processed so get the entire packet as payload
            payload = packet[offset:]
        metadata[self.name] = payload
        offset += len(payload)
        return packet, offset, metadata
