

class CH341Connection:
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
