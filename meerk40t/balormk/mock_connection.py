import random


class MockConnection:
    def __init__(self, channel):
        self.channel = channel
        self.devices = {}
        self.interface = {}
        self.backend_error_code = None
        self.timeout = 500

    def is_open(self, index=0):
        try:
            dev = self.devices[index]
            if dev:
                return True
        except KeyError:
            pass
        return False

    def open(self, index=0):
        """Opens device, returns index."""
        _ = self.channel._
        self.channel(_("Attempting connection to Mock."))
        self.devices[index] = True
        self.channel(_("Mock Connected."))
        return index

    def close(self, index=0):
        """Closes device."""
        _ = self.channel._
        device = self.devices[index]
        self.channel(_("Attempting disconnection from Mock."))
        if device is not None:
            self.channel(_("Mock Disconnection Successful.\n"))
            del self.devices[index]

    def write(self, index=0, packet=None):
        packet_length = len(packet)
        assert(packet_length == 0x12 or packet_length == 0xC00)
        if packet is not None:
            device = self.devices[index]
            if not device:
                raise ConnectionError
            self.channel(str(packet))

    def read(self, index=0):
        read = bytearray(8)
        for r in range(len(read)):
            read[r] = random.randint(0,255)
        device = self.devices[index]
        if not device:
            raise ConnectionError
        return read
