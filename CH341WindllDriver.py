from ctypes import *

# MIT License.


class CH341Driver:
    """
    This is basic interface code for a CH341 to be run in EPP 1.9 mode.
    """
    def __init__(self, driver_index):
        self.driver = windll.LoadLibrary("CH341DLL.dll")
        self.driver_index = driver_index
        self.driver_value = None

    def open(self):
        """
        Opens the driver for the stated device number.
        """
        if self.driver_value is None:
            val = self.driver.CH341OpenDevice(self.driver_index)
            self.driver_value = val
            if val == -1:
                return -1
            self.driver.CH341InitParallel(self.driver_index, 1)  # 0x40, 177, 0x8800, 0, 0

    def close(self):
        """
        Closes the driver for the stated device index.
        """
        if self.driver_value == -1:
            raise ConnectionError
        self.driver.CH341CloseDevice(self.driver_index)
        self.driver_value = None

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
            raise ConnectionError
        obuf = (c_byte * 6)()
        self.driver.CH341GetStatus(self.driver_index, obuf)
        return [int(q & 0xff) for q in obuf]

    def get_chip_version(self):
        """
        Gets the version of the CH341 chip being used.
        :return: version. Eg. 48.
        """
        if self.driver_value == -1:
            raise ConnectionError
        return self.driver.CH341GetVerIC(self.driver_index)
