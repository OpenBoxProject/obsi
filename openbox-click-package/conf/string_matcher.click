
require(package "openbox");
FromDump(test_load_balance.pcap, STOP false) -> 
sm::StringMatcher(xnet, text1, test3) -> Discard;
sm[1] -> ToDump(output_string_match.pcap, SNAPLEN 0, ENCAP ETHER);

