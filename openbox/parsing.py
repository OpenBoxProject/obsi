"""
Network Parsing Blocks
"""
import socket
import time
from openbox.container import Container
from openbox.core import ParsingBlock
from struct import Struct


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
        dst_mac, src_mac, eth_type = self._UNPACKER.unpack(packet[offset:offset + layer_length])
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
        (version_and_ihl, tos, length, ipid,
         frag, ttl, protocol, checksum, src_ip, dst_ip) = self._UNPACKER.unpack(packet[offset:offset + layer_length])

        ihl = (version_and_ihl & 0x0f) * 4
        flags = (frag >> 13) & 0x7
        frag_offset = frag & 0x1fff
        src_ip = socket.inet_ntoa(src_ip)
        dst_ip = socket.inet_ntoa(dst_ip)
        offset += ihl
        metadata[self.name] = Container(tos=tos, length=length, ipid=ipid, flags=flags, frag_offset=frag_offset,
                                        ttl=ttl, protocol=protocol, src_ip=src_ip, dst_ip=dst_ip)

        return packet, offset, metadata


class TcpParsingBlock(ParsingBlock):
    """
    Parse TCP layer information from the packet
    """
    _UNPACKER = Struct("!HHIIHHHH")

    def process(self, packet, offset, metadata, *args, **kw):
        layer_length = self._UNPACKER.size
        (src_port, dst_port, seq, ack, offset_and_flags,
         window_size, checksum, urgent) = self._UNPACKER.unpack(packet[offset:offset + layer_length])

        data_offset = ((offset_and_flags >> 12) & 0xf) * 4
        flags = offset_and_flags & 0x1ff
        offset += data_offset
        metadata[self.name] = Container(src_port=src_port, dst_port=dst_port, seq_num=seq, ack_num=ack, flags=flags)

        return packet, offset, metadata


class UdpParsingBlock(ParsingBlock):
    """
    Parse UDP layer information from the packet
    """

    def process(self, packet, offset, metadata, *args, **kw):
        layer_length = self._UNPACKER.size
        (src_port, dst_port, length, checksum) = self._UNPACKER.unpack(packet[offset:offset + layer_length])
        offset += layer_length
        metadata[self.name] = Container(src_port=src_port, dst_port=dst_port, length=length)

        return packet, offset, metadata

    _UNPACKER = Struct('!HHHH')


