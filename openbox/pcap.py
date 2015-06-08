"""
PCAP related module
"""
import gzip
import struct
import time

PCAP_MAGIC_BIG_ENDIAN = "\xa1\xb2\xc3\xd4"
PCAP_MAGIC_LITTLE_ENDIAN = "\xd4\xc3\xb2\xa1"
PCAP_MAGIC_SIZE = 4
PCAP_HEADER_SIZE = 20


class PcapReader(object):
    """
    A stateful pcap reader. Each packet is returned as a string
    """

    def __init__(self, filename):
        """
        Initialize the pcap reader with PCAP file
        :param filename: The path of the capture file
        :type filename: basestring
        """
        self.filename = filename
        try:
            self.f = gzip.open(filename, "rb")
            magic = self.f.read(PCAP_MAGIC_SIZE)
        except IOError:
            self.f = open(filename, "rb")
            magic = self.f.read(PCAP_MAGIC_SIZE)
        if magic == PCAP_MAGIC_BIG_ENDIAN:  # big endian
            self.endian = ">"
        elif magic == PCAP_MAGIC_LITTLE_ENDIAN:  # little endian
            self.endian = "<"
        else:
            raise TypeError("Not a pcap capture file (bad magic)")
        hdr = self.f.read(PCAP_HEADER_SIZE)
        if len(hdr) < PCAP_HEADER_SIZE:
            raise TypeError("Invalid pcap file (too short)")
        vermaj, vermin, tz, sig, snaplen, linktype = struct.unpack(self.endian + "HHIIII", hdr)

        self.linktype = linktype

    def __iter__(self):
        return self

    def next(self):
        """
        implement the iterator protocol on a set of packets in a pcap file
        """
        pkt = self.read_packet()
        if pkt is None:
            raise StopIteration
        return pkt

    def read_packet(self):
        """
        Read a single packet from the file

        :return: (packet_data, (sec, usec, wirelen))
        :rtype: (str, (int, int, int)) or None
        """
        hdr = self.f.read(16)
        if len(hdr) < 16:
            return None
        sec, usec, caplen, wirelen = struct.unpack(self.endian + "IIII", hdr)
        s = self.f.read(caplen)
        return s, (sec, usec, wirelen)  # caplen = len(s)

    def read(self, count=-1):
        """
        Read count packets from the file.

        :param count: The amount of packets to read, if -1 read all of them.
        :type count: int
        :return: Get a list of packets read from the file
        :rtype: list
        """
        res = []
        while count != 0:
            count -= 1
            p = self.read_packet()
            if p is None:
                break
            res.append(p)
        return res

    def fileno(self):
        return self.f.fileno()

    def close(self):
        """
        Close the backing file
        """
        return self.f.close()

    def rewind(self):
        """
        Move the file to the start of the file (at the first packet)
        """
        self.f.seek(PCAP_MAGIC_SIZE + PCAP_HEADER_SIZE)

    def __enter__(self):
        return self

    # noinspection PyUnusedLocal
    def __exit__(self, exc_type, exc_value, tracback):
        self.close()


class PcapWriter(object):
    """
    A stream PCAP writer
    """
    def __init__(self, filename, linktype=1, compress=False, endianness=None):
        """
        :param linktype: force linktype to a given value.
        :type linktype: int
        :param compress: compress the capture on the fly
        :type compress: bool
        :param endianness: force an endianness (little:"<", big:">"). Default is native
        :type endianness: str
        """
        self.linktype = linktype
        self.compress = compress
        self.endian = endianness or '='
        self.filename = filename

        if self.compress:
            self.f = gzip.open(filename, 'wb')
        else:
            self.f = open(filename, 'wb')

        self._write_header()

    def fileno(self):
        return self.f.fileno()

    def _write_header(self):
        self.header_present = True

        self.f.write(struct.pack(self.endian + "IHHIIII", 0xa1b2c3d4L, 2, 4, 0, 0, 1500, self.linktype))
        self.f.flush()

    def write_packet(self, packet, sec=None, usec=None, caplen=None, wirelen=None):
        """
        Write a single packet to file

        :param packet: The packet's data
        :type packet: str
        :param sec: Packet's capture time in seconds since epoch to write to packet's header
        :type sec: int
        :param usec: microseconds resolution
        :type usec: int
        :param caplen: Packet's capture length, defaults to length of packet
        :type caplen: int
        :param wirelen: Packet's wire length, defaults to length of packet
        :type wirelen: int
        """
        if caplen is None:
            caplen = len(packet)
        if wirelen is None:
            wirelen = caplen
        if sec is None or usec is None:
            t = time.time()
            it = int(t)
            if sec is None:
                sec = it
            if usec is None:
                usec = int(round((t - it) * 1000000))

        self.f.write(struct.pack(self.endian + "IIII", sec, usec, caplen, wirelen))
        self.f.write(packet)

    def flush(self):
        return self.f.flush()

    def close(self):
        return self.f.close()

    def __enter__(self):
        return self

    # noinspection PyUnusedLocal
    def __exit__(self, exc_type, exc_value, tracback):
        self.close()