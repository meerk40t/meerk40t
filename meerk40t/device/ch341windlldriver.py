from ctypes import windll, c_byte



# MIT License.


class CH341Driver:
    """
    This is basic interface code for a CH341 to be run in EPP 1.9 mode.
    """

    def __init__(self, index=-1, bus=-1, address=-1, serial=-1, chipv=-1, channel=None, state=None):
        self.channel = channel if channel is not None else lambda code: None
        self.state = state
        try:
            self.driver = windll.LoadLibrary("CH341DLL.dll")
        except (NameError, OSError) as e:
            self.channel(str(e))
            raise ConnectionRefusedError
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
        if val == -1:
            self.driver_value = None
            self.state('STATE_CONNECTION_FAILED')
            self.channel(_("Connection to USB failed.\n"))
            raise ConnectionRefusedError  # No more devices.
        # There is a device.
        if self.chipv != -1:
            chipv = self.get_chip_version()
            if self.chipv != chipv:
                # Rejected.
                self.channel(_("K40 devices were found but they were rejected."))
                self.driver.CH341CloseDevice(self.driver_index)
                return -1
        if self.bus != -1:
            pass  # Windows driver no bus check.
        if self.address != -1:
            pass  # Windows driver no address check.
        if self.serial != -1:
            pass  # No driver has a serial number.
        # The device passes our tests.
        return 0

    def open(self):
        """
        Opens the driver for unknown criteria.
        """
        _ = self.channel._
        if self.driver_value is None:
            self.channel(_("Using CH341 Driver to connect."))
            self.channel(_("Attempting connection to USB."))
            self.state('STATE_USB_CONNECTING')

            if self.index == -1:
                for i in range(0, 16):
                    if self.try_open(i) == 0:
                        break  # We have our driver.
            else:
                self.try_open(self.index)
            self.state('STATE_USB_CONNECTED')
            self.channel(_("USB Connected."))
            self.channel(_("Sending CH341 mode change to EPP1.9."))
            try:
                self.driver.CH341InitParallel(self.driver_index, 1)  # 0x40, 177, 0x8800, 0, 0
                self.channel(_("CH341 mode change to EPP1.9: Success."))
            except ConnectionError as e:
                self.channel(str(e))
                self.channel(_("CH341 mode change to EPP1.9: Fail."))
                self.driver.CH341CloseDevice(self.driver_index)
            # self.driver.CH341SetExclusive(self.driver_index, 1)
            self.channel(_("Device Connected.\n"))

    def close(self):
        """
        Closes the driver for the stated device index.
        """
        _ = self.channel._
        self.driver_value = None
        self.state('STATE_USB_SET_DISCONNECTING')
        self.channel(_("Attempting disconnection from USB."))
        if self.driver_value == -1:
            self.channel(_("USB connection did not exist."))
            raise ConnectionError
        self.driver.CH341CloseDevice(self.driver_index)
        self.state('STATE_USB_DISCONNECTED')
        self.channel(_("USB Disconnection Successful.\n"))

    def write(self, packet):
        """
        Writes a 32 byte packet to the device. This is typically \x00 + 30 bytes + CRC
        The driver will packetize the \0xA6 writes.

        :param packet: 32 bytes of data to be written to the CH341.
        :return:
        """
        if self.driver_value == -1:
            raise ConnectionError
        length = len(packet)
        obuf = (c_byte * length)()
        for i in range(length):
            obuf[i] = packet[i]
        length = (c_byte * 1)()
        length[0] = 32
        self.driver.CH341EppWriteData(self.driver_index, obuf, length)

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
        if self.driver_value == -1:
            raise ConnectionRefusedError
        obuf = (c_byte * 6)()
        self.driver.CH341GetStatus(self.driver_index, obuf)
        return [int(q & 0xff) for q in obuf]

    def get_chip_version(self):
        """
        Gets the version of the CH341 chip being used.
        :return: version. Eg. 48.
        """
        if self.driver_value == -1:
            raise ConnectionRefusedError
        return self.driver.CH341GetVerIC(self.driver_index)
