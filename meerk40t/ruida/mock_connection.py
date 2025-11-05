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
        self.swizzle = None
        self.unswizzle = None

    def set_swizzles(self, swizzle, unswizzle):
        """Set swizzle functions for use by the controller."""
        self.swizzle = swizzle
        self.unswizzle = unswizzle

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

    def open(self):
        """Opens device."""
        _ = self.channel._
        self.channel(_("Attempting connection to Mock."))
        self.devices[0] = True
        self.service.signal("pipe;usb_status", "connected")
        self.channel(_("Mock Connected."))
        return 0

    def close(self):
        """Closes device."""
        _ = self.channel._
        device = self.devices.get(0)
        self.channel(_("Attempting disconnection from Mock."))
        if device is not None:
            self.service.signal("pipe;usb_status", "disconnected")
            self.channel(_("Mock Disconnection Successful.\n"))
            del self.devices[0]

    def write(self, data):
        """Write data to mock connection."""
        if self.send:
            self.send(data)

    def send(self, data):
        """Send data directly (alias for write)."""
        self.write(data)

    def recv(self):
        """Mock receive - always returns None (no incoming data)."""
        return None

    def abort_connect(self):
        """Abort connection attempt."""
        pass
