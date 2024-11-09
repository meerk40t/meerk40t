# MIT License.
import random
import time


class MockCH341Driver:
    """
    This is basic interface code for a mock CH341.
    """

    def __init__(self, channel=None, state=None, bulk=True):
        self.driver_index = None
        self.driver_value = None
        self.channel = channel
        self.state = state
        self.bulk = bulk

        self.mock_status = 206
        self.mock_error = 207
        self.mock_finish = 236

        self._start_time_status = None
        self._end_time_status = None
        self._time_status = None

    def is_connected(self):
        return self.driver_value != -1 and self.driver_index is not None

    @property
    def driver_name(self):
        return "Mock"

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
        self.channel(_("Using Mock Driver."))

        if self.driver_value is None:
            self.channel(_("Using Mock Driver to connect."))
            self.channel(_("Attempting connection to USB."))
            self.state("STATE_USB_CONNECTING")
            self.driver_value = 0  # Would connect here.
            self.driver_index = usb_index
            self.state("STATE_USB_CONNECTED")
            self.channel(_("USB Connected."))
            self.channel(_("Sending CH341 mode change to EPP1.9."))
            try:
                # self.driver.CH341InitParallel(self.driver_index, 1)
                self.channel(_("CH341 mode change to EPP1.9: Success."))
            except ConnectionError as e:
                self.channel(str(e))
                self.channel(_("CH341 mode change to EPP1.9: Fail."))
                raise ConnectionRefusedError
                # self.driver.CH341CloseDevice(self.driver_index)
            # self.driver.CH341SetExclusive(self.driver_index, 1)
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
        # self.driver.CH341CloseDevice(self.driver_index)
        self.state("STATE_USB_DISCONNECTED")
        self.channel(_("USB Disconnection Successful.\n"))

    def reset(self):
        pass

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
            raise ConnectionError
        if packet.startswith(b"\x00A"):
            self._start_time_status = time.time()
            self._end_time_status = self._start_time_status + 0.5
            self._time_status = 204
        if random.randint(0, 5000) == 0:
            # Write failed.
            raise ConnectionError
        time.sleep(0.04)
        # Mock

    def write_addr(self, packet):
        """
        Writes an address byte packet to the device. This is typically 1 byte
        The driver will packetize the \0xA7 writes.

        @param packet: 1 byte of data to be written to the CH341.
        @return:
        """
        if not self.is_connected():
            raise ConnectionError
        time.sleep(0.04)
        # Mock.

    def get_status(self):
        """
        Gets the status bytes from the CH341. This is usually 255 for the D0-D7 values
        And the state flags for the chip signals. Importantly are WAIT which means do not
        send data, and ERR which means the data sent was faulty. And PEMP which means the
        buffer is empty.

        StateBitERR      0x00000100
        StateBitPEMP   0x00000200
        StateBitINT      0x00000400
        StateBitSLCT   0x00000800
        StateBitWAIT   0x00002000
        StateBitDATAS   0x00004000
        StateBitADDRS   0x00008000
        StateBitRESET   0x00010000
        StateBitWRITE   0x00020000
        StateBitSCL       0x00400000
        StateBitSDA      0x00800000
        @return:
        """
        if not self.is_connected():
            raise ConnectionError
        if self._start_time_status is not None:
            if self._start_time_status <= time.time() <= self._end_time_status:
                return [255, self._time_status, 0, 0, 0, 1]
            if self._end_time_status >= time.time():
                self._start_time_status = None
                self._end_time_status = None
                self._time_status = None

        # Mock
        from random import randint

        if randint(0, 500) == 0:
            status = [255, self.mock_error, 0, 0, 0, 1]
        else:
            status = [255, self.mock_status, 0, 0, 0, 1]
        if randint(0, 1000) == 0:
            status = [255, self.mock_finish, 0, 0, 0, 1]
        time.sleep(0.01)
        return status

    def get_chip_version(self):
        """
        Gets the version of the CH341 chip being used.
        @return: version. E.g. 48.
        """
        if not self.is_connected():
            raise ConnectionError
        return 999  # MOCK.
