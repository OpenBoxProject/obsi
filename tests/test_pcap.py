import os
import unittest
from openbox.pcap import PcapReader, PcapWriter


class TestPcapReader(unittest.TestCase):
    def test_read_all_packets_iter(self):
        with PcapReader('pcaps/test_pcap_reader.pcap') as reader:
            counter = 0
            for _ in reader:
                counter += 1

            self.assertEqual(counter, 2)

    def test_read_all_packets(self):
        with PcapReader('pcaps/test_pcap_reader.pcap') as reader:
            packets = reader.read()
            counter = len(packets)
            self.assertEqual(counter, 2)

    def test_read_single_packet(self):
        with PcapReader('pcaps/test_pcap_reader.pcap') as reader:
            expected_data = 'b0487aeccc020c84dc9e9a610800450000411f260000801197ccc0a80168c0a801' \
                            '01df240035002de3a2431b01000001000000000000086163636f756e747306676f' \
                            '6f676c6503636f6d0000010001'.decode('hex')
            expected_header = (1432458294, 987197, 79)
            pkt, header = reader.read_packet()
            self.assertEqual(pkt, expected_data)
            self.assertEqual(header, expected_header)

    def test_rewind(self):
        with PcapReader('pcaps/test_pcap_reader.pcap') as reader:
            for _ in reader:
                # reads all the packets
                pass
            reader.rewind()
            counter = 0
            for _ in reader:
                counter += 1

            self.assertEqual(counter, 2)


class TestPcapWriter(unittest.TestCase):
    def tearDown(self):
        os.unlink('pcaps/test_pcap_writer.pcap')

    def test_write_single_packet(self):
        expected_data = 'b0487aeccc020c84dc9e9a610800450000411f260000801197ccc0a80168c0a801' \
                        '01df240035002de3a2431b01000001000000000000086163636f756e747306676f' \
                        '6f676c6503636f6d0000010001'.decode('hex')
        expected_header = (1432458294, 987197, 79)
        with PcapWriter('pcaps/test_pcap_writer.pcap') as writer:
            writer.write_packet(expected_data, expected_header[0], expected_header[1])
        with PcapReader('pcaps/test_pcap_reader.pcap') as reader:
            pkt, header = reader.read_packet()
            self.assertEqual(pkt, expected_data)
            self.assertEqual(header, expected_header)

    def test_write_all_packets(self):
        with PcapReader('pcaps/test_pcap_reader.pcap') as reader, PcapWriter('pcaps/test_pcap_writer.pcap') as writer:
            read_packets = reader.read()
            for pkt, (sec, usec, wirelen) in read_packets:
                writer.write_packet(pkt, sec, usec)
        with PcapReader('pcaps/test_pcap_writer.pcap') as reader:
            written_packets = reader.read()
            self.assertEqual(read_packets, written_packets)


