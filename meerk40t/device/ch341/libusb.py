from .ch341 import Connection as CH341Connection
from .ch341 import Handler as CH341Handler
from .ch341libusbdriver import Ch341LibusbDriver


class CH341Driver(CH341Connection):
    def __init__(
        self,
        driver,
        driver_index=-1,
        channel=None,
        state=None,
    ):
        self.driver_name = "LibUsb"
        self.driver = driver
        self.driver_index = driver_index

        CH341Connection.__init__(self, channel, state)
        self.channel = channel if channel is not None else lambda code: None
        self.state = state

        self.driver_value = None

    def open(self):
        """
        Opens the driver for unknown criteria.
        """
        _ = self.channel._
        if self.driver_value is None:
            self.channel(_("Using LibUSB to connect."))
            self.channel(_("Attempting connection to USB."))
            self.state("STATE_USB_CONNECTING")

            self.driver_value = self.driver.CH341OpenDevice(self.driver_index)
            if self.driver_value == -2:
                self.driver_value = None
                self.state("STATE_DRIVER_NO_BACKEND")
                raise ConnectionRefusedError
            if self.driver_value == -1:
                self.driver_value = None
                self.channel(_("Connection to USB failed.\n"))
                self.state("STATE_CONNECTION_FAILED")
                raise ConnectionRefusedError  # No more devices.
            self.channel(_("USB Connected."))
            self.state("STATE_USB_CONNECTED")
            self.channel(_("Sending CH341 mode change to EPP1.9."))
            try:
                self.driver.CH341InitParallel(
                    self.driver_index, 1
                )  # 0x40, 177, 0x8800, 0, 0
                self.channel(_("CH341 mode change to EPP1.9: Success."))
            except ConnectionError:
                self.channel(_("CH341 mode change to EPP1.9: Fail."))
                self.driver.CH341CloseDevice(self.driver_index)
                raise ConnectionRefusedError
            self.channel(_("Device Connected.\n"))
            chip_version = self.get_chip_version()
            self.channel(_("CH341 Chip Version: %d") % chip_version)
            self.channel(_("Driver Detected: LibUsb"))
            self.index = self.driver_index
            self.bus = self.driver.bus(self.driver_value)
            self.address = self.driver.address(self.driver_value)
            self.state("STATE_CONNECTED")
            self.channel(_("Device Connected.\n"))

    def close(self):
        _ = self.channel._
        self.driver_value = None
        self.state("STATE_USB_SET_DISCONNECTING")
        self.channel(_("Attempting disconnection from USB."))
        if self.driver_value == -1:
            self.channel(_("USB connection did not exist."))
            raise ConnectionError
        self.driver.CH341CloseDevice(self.driver_index)
        self.state("STATE_USB_DISCONNECTED")
        self.channel(_("USB Disconnection Successful.\n"))

    def write(self, packet):
        self.driver.CH341EppWriteData(self.driver_index, packet, len(packet))

    def write_addr(self, packet):
        self.driver.CH341EppWriteAddr(self.driver_index, packet, len(packet))

    def get_status(self):
        return self.driver.CH341GetStatus(self.driver_index)

    def get_chip_version(self):
        self.chipv = self.driver.CH341GetVerIC(
            self.driver_index
        )  # 48, reads 0xc0, 95, 0, 0 (30,00? = 48)
        return self.chipv


class Handler(CH341Handler):
    def __init__(self, channel, status):
        CH341Handler.__init__(self, channel=channel, status=status)
        self.driver = Ch341LibusbDriver(channel=channel)

    def connect(self, driver_index=0, chipv=-1, bus=-1, address=-1):
        """Tries to open device at index, with given criteria"""
        connection = CH341Driver(
            self.driver, driver_index, channel=self.channel, state=self.status
        )
        _ = self.channel._
        connection.open()

        if chipv != -1:
            match_chipv = connection.get_chip_version()
            if chipv != match_chipv:
                # Rejected.
                self.channel(
                    _(
                        "K40 devices were found but they were rejected due to chip version."
                    )
                )
                connection.close()
                raise ConnectionRefusedError("Chip Version Wrong.")
        if bus != -1:
            match_bus = connection.bus
            if bus != match_bus:
                # Rejected.
                self.channel(
                    _("K40 devices were found but they were rejected due to usb bus.")
                )
                connection.close()
                raise ConnectionRefusedError("USB Bus Wrong.")
        if address != -1:
            match_address = connection.address
            if address != match_address:
                # Rejected
                self.channel(
                    _(
                        "K40 devices were found but they were rejected due to usb address."
                    )
                )
                connection.close()
                raise ConnectionRefusedError("USB Address Wrong.")
        return connection
