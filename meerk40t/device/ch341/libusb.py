from .ch341libusbdriver import Ch341LibusbDriver


class CH341Driver:
    def __init__(
        self,
        index=-1,
        bus=-1,
        address=-1,
        serial=-1,
        chipv=-1,
        channel=None,
        state=None,
    ):
        self.channel = channel if channel is not None else lambda code: None
        self.state = state
        self.driver = Ch341LibusbDriver(channel=channel)
        self.driver_index = 0
        self.index = index
        self.bus = bus
        self.address = address
        self.serial = serial
        self.chipv = chipv
        self.driver_value = None

    def try_open(self, i):
        """Tries to open device at index, with given criteria"""
        _ = self.channel._
        self.driver_index = i
        val = self.driver.CH341OpenDevice(self.driver_index)
        self.driver_value = val
        if val == -2:
            self.state("STATE_DRIVER_NO_BACKEND")
            raise ConnectionRefusedError
        if val == -1:
            self.driver_value = None
            self.channel(_("Connection to USB failed.\n"))
            self.state("STATE_CONNECTION_FAILED")
            raise ConnectionRefusedError  # No more devices.
        # There is a device.
        if self.chipv != -1:
            chipv = self.get_chip_version()
            if self.chipv != chipv:
                # Rejected.
                self.channel(_("K40 devices were found but they were rejected."))
                self.driver.CH341CloseDevice(self.driver_index)
                self.driver_value = val
                return -1
        if self.bus != -1:
            bus = self.driver.devices[val].bus
            if self.bus != bus:
                # Rejected.
                self.channel(_("K40 devices were found but they were rejected."))
                self.driver.CH341CloseDevice(self.driver_index)
                self.driver_value = val
                return -1
        if self.address != -1:
            address = self.driver.devices[val].bus
            if self.address != address:
                # Rejected
                self.channel(_("K40 devices were found but they were rejected."))
                self.driver.CH341CloseDevice(self.driver_index)
                self.driver_value = val
                return -1
        if self.serial != -1:
            pass  # No driver has a serial number.
        # The device passes our tests.
        return val

    def open(self):
        """
        Opens the driver for unknown criteria.
        """
        _ = self.channel._
        if self.driver_value is None:
            self.channel(_("Using LibUSB to connect."))
            self.channel(_("Attempting connection to USB."))
            self.state("STATE_USB_CONNECTING")
            if self.index == -1:
                for i in range(0, 16):
                    if self.try_open(i) == 0:
                        break  # We have our driver.
            else:
                self.try_open(self.index)
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

    def close(self):
        self.driver.CH341CloseDevice(self.driver_index)
        self.driver_value = None

    def write(self, packet):
        self.driver.CH341EppWriteData(self.driver_index, packet, len(packet))

    def write_addr(self, packet):
        self.driver.CH341EppWriteAddr(self.driver_index, packet, len(packet))

    def get_status(self):
        return self.driver.CH341GetStatus(self.driver_index)

    def get_chip_version(self):
        return self.driver.CH341GetVerIC(
            self.driver_index
        )  # 48, reads 0xc0, 95, 0, 0 (30,00? = 48)
