from ctypes import windll, c_byte

from ch341driverbase import *


# MIT License.


class CH341Driver:
    """
    This is basic interface code for a CH341 to be run in EPP 1.9 mode.
    """

    def __init__(self, index=-1, bus=-1, address=-1, serial=-1, chipv=-1, state_listener=None):
        if state_listener is None:
            self.state_listener = lambda code: None
        else:
            self.state_listener = state_listener
        try:
            self.driver = windll.LoadLibrary("CH341DLL.dll")
        except (NameError, OSError):
            raise ConnectionRefusedError
        self.driver_index = 0
        self.index = index
        self.bus = bus
        self.address = address
        self.serial = serial
        self.chipv = chipv
        self.driver_value = None
        self.state = None

    def set_status(self, code):
        self.state_listener(code)
        self.state = code

    def try_open(self, i):
        """Tries to open device at index, with given criteria"""
        self.driver_index = i
        val = self.driver.CH341OpenDevice(self.driver_index)
        self.driver_value = val
        if val == -1:
            self.driver_value = None
            self.set_status(STATE_CONNECTION_FAILED)
            raise ConnectionRefusedError  # No more devices.
        # There is a device.
        if self.chipv != -1:
            chipv = self.get_chip_version()
            if self.chipv != chipv:
                # Rejected.
                self.set_status(STATE_DEVICE_REJECTED)
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
        if self.driver_value is None:
            self.set_status(STATE_DRIVER_CH341)
            self.set_status(STATE_CONNECTING)
            if self.index == -1:
                for i in range(0, 16):
                    if self.try_open(i) == 0:
                        break  # We have our driver.
            else:
                self.try_open(self.index)
            self.set_status(STATE_USB_CONNECTED)
            self.set_status(STATE_CH341_PARAMODE)
            try:
                self.driver.CH341InitParallel(self.driver_index, 1)  # 0x40, 177, 0x8800, 0, 0
                self.set_status(STATE_CH341_PARAMODE_SUCCESS)
            except ConnectionError:
                self.set_status(STATE_CH341_PARAMODE_FAIL)
                self.driver.CH341CloseDevice(self.driver_index)
            # self.driver.CH341SetExclusive(self.driver_index, 1)
            self.set_status(STATE_CONNECTED)

    def close(self):
        """
        Closes the driver for the stated device index.
        """
        self.driver_value = None
        self.set_status(STATE_USB_SET_DISCONNECTING)
        if self.driver_value == -1:
            self.set_status(STATE_USB_RESET_FAIL)
            raise ConnectionError
        self.driver.CH341CloseDevice(self.driver_index)
        self.set_status(STATE_USB_DISCONNECTED)

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
