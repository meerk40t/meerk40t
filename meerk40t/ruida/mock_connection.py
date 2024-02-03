"""
Mock Connection for Ruida Devices

The mock connection is used for debug and research purposes. And simply prints the data sent to it rather than engaging
any hardware.
"""


class MockConnection:
    def __init__(self, service):
        self.service = service
        name = self.service.safe_label
        self.channel = service.channel(f"{name}/mock")
        self.send = service.channel(f"{name}/send")
        self.recv = service.channel(f"{name}/recv", pure=True)
        self.devices = {}
        self.interface = {}
        self.backend_error_code = None
        self.timeout = 500

    @property
    def connected(self):
        return self.is_open()

    @property
    def is_connecting(self):
        return False

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

    def write(self, data):
        if self.send:
            self.send(data)
