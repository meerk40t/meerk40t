from meerk40t.kernel import Module


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("module/ch341", CH341)


class CH341(Module):
    """
    Generic CH341 Module performs the interactions between the requested operations and several delegated backend ch341
    drivers. This permits interfacing with LibUsb, Windll or Mock Ch341 backends. In use agnostic fashion, this should
    be valid and acceptable for any CH341 interactions. CH341 chip interfacing is required for Lhystudios Controllers,
    Moshiboard Controllers, and other interactions such as a plugin that uses addition CH341 devices.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.usb_context = self.context.get_context("usb")
        self.usb_log = self.context.channel("usb")
        self.driver = None

    def detect_driver_and_open(self):
        index = self.context.usb_index
        bus = self.context.usb_bus
        address = self.context.usb_address
        chipv = self.context.usb_version
        _ = self.usb_log._

        def state(state_value):
            self.context.signal("pipe;state", state_value)

        if self.context.mock:
            try:
                from src.device.ch341.mock import CH341Driver
                self.driver = driver = CH341Driver(
                    index=index,
                    bus=bus,
                    address=address,
                    serial=None,
                    chipv=chipv,
                    channel=self.usb_log,
                    state=state,
                )
                driver.open()
                chip_version = driver.get_chip_version()
                self.usb_log(_("CH341 Chip Version: %d") % chip_version)
                self.context.signal("pipe;chipv", chip_version)
                self.usb_log(_("Driver Forced: Mock"))
                state("STATE_CONNECTED")
                self.usb_log(_("Device Connected.\n"))
                return
            except ConnectionRefusedError:
                self.driver = None

        try:
            from src.device.ch341.libusb import CH341Driver

            self.driver = driver = CH341Driver(
                index=index,
                bus=bus,
                address=address,
                serial=None,
                chipv=chipv,
                channel=self.usb_log,
                state=state,
            )
            driver.open()
            chip_version = driver.get_chip_version()
            self.usb_log(_("CH341 Chip Version: %d") % chip_version)
            self.context.signal("pipe;chipv", chip_version)
            self.usb_log(_("Driver Detected: LibUsb"))
            state("STATE_CONNECTED")
            self.usb_log(_("Device Connected.\n"))
            return
        except ConnectionRefusedError:
            self.driver = None
        except ImportError:
            self.usb_log(_("PyUsb is not installed. Skipping."))

        try:
            from src.device.ch341.windll import CH341Driver

            self.driver = driver = CH341Driver(
                index=index,
                bus=bus,
                address=address,
                serial=None,
                chipv=chipv,
                channel=self.usb_log,
                state=state,
            )
            driver.open()
            chip_version = driver.get_chip_version()
            self.usb_log(_("CH341 Chip Version: %d") % chip_version)
            self.context.signal("pipe;chipv", chip_version)
            self.usb_log(_("Driver Detected: CH341"))
            state("STATE_CONNECTED")
            self.usb_log(_("Device Connected.\n"))
            return
        except ConnectionRefusedError:
            self.driver = None
        except ImportError:
            self.usb_log(_("No Windll interfacing. Skipping."))

    def try_open(self, i):
        """Tries to open device at index, with given criteria"""
        self.driver.try_open(i)

    def open(self):
        """
        Opens the driver for unknown criteria.
        """
        self.driver.open()

    def close(self):
        """
        Closes the driver for the stated device index.
        """
        self.driver.close()

    def write(self, packet):
        """
        Writes a 32 byte packet to the device. This is typically \x00 + 30 bytes + CRC
        The driver will packetize the \0xA6 writes.

        :param packet: 32 bytes of data to be written to the CH341.
        :return:
        """
        self.driver.write(packet)

    def write_addr(self, packet):
        """
        Writes an address byte packet to the device. This is typically 1 byte
        The driver will packetize the \0xA7 writes.

        :param packet: 1 byte of data to be written to the CH341.
        :return:
        """
        self.driver.write_addr(packet)

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
        return self.driver.get_status()

    def get_chip_version(self):
        """
        Gets the version of the CH341 chip being used.
        :return: version. Eg. 48.
        """
        return self.driver.get_chip_version()