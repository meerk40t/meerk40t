from meerk40t.kernel import Module


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("module/ch341", CH341)


class CH341(Module):
    """
    Generic CH341 Module performs the interactions between the requested operations and several delegated backend ch341
    drivers. This permits interfacing with LibUsb, Windll or Mock Ch341 backends. In use-agnostic fashion, this should
    be valid and acceptable for any CH341 interactions. CH341 chip interfacing is required for Lhystudios Controllers,
    Moshiboard Controllers, and other interactions such as a plugin that uses addition CH341 devices.
    """
    def __init__(self, *args, **kwargs):
        Module.__init__(self, *args, **kwargs)
        self.usb_log = self.context.channel("pipe/usb")

    def state_change(self, state_value):
        self.context.signal("pipe;state", state_value)

    def connect(self, mock=False):
        """
        Requests and returns an available connection. The connection object itself has open() and close() functions and
        provides any information about the connection if available. If the connection is not opened, no resources are
        reserved.
        """
        _ = self.usb_log._

        if mock:
            try:
                from .mock import Handler
                driver_handler = Handler(channel=self.usb_log, state=self.state_change)
                for i in range(16):
                    connection = driver_handler.connect(i)
                    chip_version = connection.get_chip_version()
                    self.usb_log(_("CH341 Chip Version: %d") % chip_version)
                    self.context.signal("pipe;chipv", chip_version)
                    self.usb_log(_("Driver Forced: Mock"))
                    self.state_change("STATE_CONNECTED")
                    self.usb_log(_("Device Connected.\n"))
                    return connection
            except ConnectionRefusedError:
                pass

        try:
            from .libusb import Handler
            driver_handler = Handler(channel=self.usb_log, state=self.state_change)
            for i in range(16):
                connection = driver_handler.connect(i)
                chip_version = connection.get_chip_version()
                self.usb_log(_("CH341 Chip Version: %d") % chip_version)
                self.context.signal("pipe;chipv", chip_version)
                self.usb_log(_("Driver Detected: LibUsb"))
                self.state_change("STATE_CONNECTED")
                self.usb_log(_("Device Connected.\n"))
                return connection
        except ConnectionRefusedError:
            pass
        except ImportError:
            self.usb_log(_("PyUsb is not installed. Skipping."))

        try:
            from .windll import Handler
            driver_handler = Handler(channel=self.usb_log, state=self.state_change)
            for i in range(16):
                connection = driver_handler.connect(i)
                chip_version = connection.get_chip_version()
                self.usb_log(_("CH341 Chip Version: %d") % chip_version)
                self.context.signal("pipe;chipv", chip_version)
                self.usb_log(_("Driver Detected: CH341"))
                self.state_change("STATE_CONNECTED")
                self.usb_log(_("Device Connected.\n"))
                return connection
        except ConnectionRefusedError:
            pass
        except ImportError:
            self.usb_log(_("No Windll interfacing. Skipping."))


class Connection:
    def __init__(self, channel, state):
        self.channel = channel
        self.state = state

    def validate(self):
        """
        Opens the connection to validate that it exists.
        """
        pass

    def open(self):
        """
        Opens the connection.
        """
        pass

    def close(self):
        """
        Closes the driver for the stated device index.
        """
        pass

    def write(self, packet):
        """
        Writes a 32 byte packet to the device. This is typically \x00 + 30 bytes + CRC
        The driver will packetize the \0xA6 writes.

        :param packet: 32 bytes of data to be written to the CH341.
        :return:
        """
        pass

    def write_addr(self, packet):
        """
        Writes an address byte packet to the device. This is typically 1 byte
        The driver will packetize the \0xA7 writes.

        :param packet: 1 byte of data to be written to the CH341.
        :return:
        """
        pass

    def get_status(self):
        """
        Gets the status bytes from the CH341. This is usually 255 for the D0-D7 values
        And the state flags for the chip signals. Importantly are WAIT which means do not
        send data, and ERR which means the data sent was faulty. And PEMP which means the
        buffer is empty.

        StateBitERR		0x00000100
        StateBitPEMP	0x00000200
        StateBitINT		0x00000400
        StateBitSLCT	0x00000800
        StateBitWAIT	0x00002000
        StateBitDATAS	0x00004000
        StateBitADDRS	0x00008000
        StateBitRESET	0x00010000
        StateBitWRITE	0x00020000
        StateBitSCL	    0x00400000
        StateBitSDA		0x00800000
        :return:
        """
        raise NotImplementedError

    def get_chip_version(self):
        """
        Gets the version of the CH341 chip being used.
        :return: version. Eg. 48.
        """
        raise NotImplementedError


class Handler:
    def __init__(self, channel, state):
        self.channel = channel
        self.state = state

    def connect(self, index=0):
        pass