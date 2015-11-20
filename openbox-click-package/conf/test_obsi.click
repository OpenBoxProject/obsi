ChatterSocket("TCP", 10002, RETRIES 3, RETRY_WARNINGS false, CHANNEL openbox);
ControlSocket("TCP", 10001, RETRIES 3, RETRY_WARNINGS false);
require(package "openbox");
from_device@_@from_device::FromDevice(eth0);
from_device@_@counter::Counter();
discard@_@discard::Discard();
from_device@_@from_device[0]->[0]from_device@_@counter;
from_device@_@counter[0]->[0]discard@_@discard;