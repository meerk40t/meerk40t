from ctypes import c_byte, windll

# MIT License.


class WinCH341Driver:
    """
    This is basic interface code for a CH341 to be run in EPP 1.9 mode.
    """

    def __init__(self, channel=None, state=None):
        self.driver_index = None
        self.driver_value = None
        self.channel = channel
        self.state = state

        try:
            self.driver = windll.LoadLibrary("CH341DLL.dll")
        except FileNotFoundError as e:
            self.channel(f"{str(type(e))}: {str(e)}")
            raise ImportError(
                "FileNotFoundError for misconfigured CH341DLL.dll. See Issue #459"
            )
        except (NameError, OSError) as e:
            self.channel(str(e))
            raise ConnectionRefusedError

    def is_connected(self):
        return self.driver_value != -1 and self.driver_index is not None

    @property
    def driver_name(self):
        return "WinDll"

    @property
    def address(self):
        return None

    @property
    def bus(self):
        return None

    def open(self, usb_index):
        """
        Opens the driver for unknown criteria.
        """
        _ = self.channel._
        if self.driver_value is None:
            self.channel(_("Using CH341 Driver to connect."))
            self.channel(_("Attempting connection to USB."))
            self.state("STATE_USB_CONNECTING")
            self.driver_value = self.driver.CH341OpenDevice(usb_index)
            if self.driver_value == -2:
                self.state("STATE_DRIVER_NO_BACKEND")
                raise ConnectionRefusedError
            if self.driver_value == -1:
                self.driver_value = None
                self.channel(_("Connection to USB failed.\n"))
                self.state("STATE_CONNECTION_FAILED")
                raise ConnectionRefusedError  # No more devices.
            self.driver_index = usb_index
            self.state("STATE_USB_CONNECTED")
            self.channel(_("USB Connected."))
            self.channel(_("Sending CH341 mode change to EPP1.9."))
            success = self.driver.CH341InitParallel(
                self.driver_index, 1
            )  # 0x40, 177, 0x8800, 0, 0
            if success:
                self.channel(_("CH341 mode change to EPP1.9: Success."))
            else:
                self.channel(_("CH341 mode change to EPP1.9: Fail."))
                self.driver.CH341CloseDevice(self.driver_index)
                raise ConnectionRefusedError
            self.channel(_("Device Connected.\n"))

    def close(self):
        """
        Closes the driver for the stated device index.
        """
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
        self.driver_index = None

    def reset(self):
        _ = self.channel._
        self.channel(_("USB connection reset."))
        self.driver.CH341ResetDevice(self.driver_index)

    def release(self):
        pass

    def write(self, packet):
        """
        Writes a 32 byte packet to the device. This is typically \x00 + 30 bytes + CRC
        The driver will packetize the \0xA6 writes.

        @param packet: 32 bytes of data to be written to the CH341.
        @return:
        """
        if not self.is_connected():
            raise ConnectionError("Not connected.")
        length = len(packet)
        obuf = (c_byte * length)()
        for i in range(length):
            obuf[i] = packet[i]
        length = (c_byte * 1)()
        length[0] = len(packet)
        success = self.driver.CH341EppWriteData(self.driver_index, obuf, length)
        if not success:
            raise ConnectionError("Failed to write to CH341:Windll.")

    def write_addr(self, packet):
        """
        Writes an address byte packet to the device. This is typically 1 byte
        The driver will packetize the \0xA7 writes.

        @param packet: 1 byte of data to be written to the CH341.
        @return:
        """
        if not self.is_connected():
            raise ConnectionError("Not connected.")
        length = len(packet)
        obuf = (c_byte * length)()
        for i in range(length):
            obuf[i] = packet[i]
        length = (c_byte * 1)()
        length[0] = len(packet)
        success = self.driver.CH341EppWriteAddr(self.driver_index, packet, length)
        if not success:
            raise ConnectionError("Failed to write_addr to CH341:Windll.")

    def get_status(self):
        """
        Gets the status bytes from the CH341. This is usually 255 for the D0-D7 values
        And the state flags for the chip signals. Importantly are WAIT which means do not
        send data, and ERR which means the data sent was faulty. And PEMP which means the
        buffer is empty.

        StateBitERR     0x00000100
        StateBitPEMP    0x00000200
        StateBitINT     0x00000400
        StateBitSLCT    0x00000800
        StateBitWAIT    0x00002000
        StateBitDATAS   0x00004000
        StateBitADDRS   0x00008000
        StateBitRESET   0x00010000
        StateBitWRITE   0x00020000
        StateBitSCL     0x00400000
        StateBitSDA     0x00800000
        @return:
        """
        if not self.is_connected():
            raise ConnectionRefusedError("Not connected.")
        length = (c_byte * 1)()
        write_buffer = (c_byte * 1)()
        write_buffer[0] = 0xA0
        length[0] = len(write_buffer)
        success = self.driver.CH341WriteData(self.driver_index, write_buffer, length)
        if not success:
            raise ConnectionError("Failed to write to CH341:Windll.")
        read_buffer = (c_byte * 6)()
        length[0] = len(read_buffer)
        self.driver.CH341ReadData(self.driver_index, read_buffer, length)
        # self.driver.CH341GetStatus(self.driver_index, read_buffer)
        return [int(q & 0xFF) for q in read_buffer]

    def get_chip_version(self):
        """
        Gets the version of the CH341 chip being used.
        @return: version. Eg. 48.
        """
        if not self.is_connected():
            raise ConnectionRefusedError
        return self.driver.CH341GetVerIC(self.driver_index)
