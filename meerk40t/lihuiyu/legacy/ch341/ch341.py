

class Connection:
    """
    A single connection to an CH341 device.
    """

    def __init__(self, channel, state):
        self.channel = channel
        self.state = state

        self.index = None
        self.chipv = None
        self.bus = None
        self.address = None

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

        StateBitERR          0x00000100
        StateBitPEMP     0x00000200
        StateBitINT          0x00000400
        StateBitSLCT     0x00000800
        StateBitWAIT     0x00002000
        StateBitDATAS     0x00004000
        StateBitADDRS     0x00008000
        StateBitRESET     0x00010000
        StateBitWRITE     0x00020000
        StateBitSCL         0x00400000
        StateBitSDA          0x00800000
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
    """
    Handlers provide an implementation of a particular backend tasked with providing connections.
    """

    def __init__(self, channel, status):
        self.channel = channel
        self.status = status

    def connect(self, driver_index=0, chipv=-1, bus=-1, address=-1):
        pass


class CH341(Handler):
    """
    Generic CH341 Module performs the interactions between the requested operations and several delegated backend ch341
    drivers. This permits interfacing with LibUsb, Windll or Mock Ch341 backends. In use-agnostic fashion, this should
    be valid and acceptable for any CH341 interactions. CH341 chip interfacing is required for Lhystudios Controllers,
    Moshiboard Controllers, and other interactions such as a plugin that uses addition CH341 devices.
    """

    def __init__(self, context, **kwargs):
        self.context = context
        if "log" in kwargs:
            channel = kwargs["log"]
            if isinstance(channel, str):
                channel = self.context.channel(channel, buffer_size=500)
        else:
            channel = self.context.channel("ch341/usb", buffer_size=500)
        Handler.__init__(self, channel, self._state_change)

    def connect(self, driver_index=-1, chipv=-1, bus=-1, address=-1, mock=False):
        """
        Requests and returns an available connection. The connection object itself has open() and close() functions and
        provides any information about the connection if available. If the connection is not opened, no resources are
        reserved.
        """
        _ = self.channel._
        if mock:
            return self._connect_mock(driver_index, chipv, bus, address)
        handlers = []
        try:
            from .libusb import Handler as LibUsbHandler

            handlers.append(LibUsbHandler(channel=self.channel, status=self.status))
        except ImportError:
            self.channel(_("PyUsb is not installed. Skipping."))
        try:
            from .windll import Handler as WinHandler

            handlers.append(WinHandler(channel=self.channel, status=self.status))
        except ImportError:
            self.channel(_("No Windll interfacing. Skipping."))

        if driver_index != -1:  # Match one specific index.
            for driver_handler in handlers:
                try:
                    return self._connect_attempt(
                        driver_handler, driver_index, chipv, bus, address
                    )
                except ConnectionRefusedError:
                    pass
        else:
            for i in range(16):
                for driver_handler in handlers:
                    try:
                        connection = self._connect_attempt(
                            driver_handler, i, chipv, bus, address
                        )
                        return connection
                    except ConnectionRefusedError:
                        pass
                    except PermissionError:
                        return  # OS denied permissions, no point checking anything else.

    def _state_change(self, state_value):
        self.context.signal("pipe;state", state_value)

    def _connect_attempt(self, handler, driver_index=-1, chipv=-1, bus=-1, address=-1):
        _ = self.channel._
        connection = handler.connect(
            driver_index=driver_index, chipv=chipv, bus=bus, address=address
        )
        try:
            chip_version = connection.get_chip_version()
        except AttributeError:
            return connection
        self.channel(_("CH341 Chip Version: %d") % chip_version)
        self.context.signal("pipe;index", connection.index)
        self.context.signal("pipe;chipv", chip_version)
        self.context.signal("pipe;bus", connection.bus)
        self.context.signal("pipe;address", connection.address)
        self.channel(_("Driver Detected: %s") % connection.driver_name)
        self._state_change("STATE_CONNECTED")
        self.channel(_("Device Connected.\n"))
        return connection

    def _connect_mock(self, driver_index=-1, chipv=-1, bus=-1, address=-1):
        from .mock import Handler

        driver_handler = Handler(channel=self.channel, status=self.status)
        if driver_index != -1:
            try:
                return self._connect_attempt(
                    driver_handler, driver_index, chipv, bus, address
                )
            except ConnectionRefusedError:
                pass
        else:
            for i in range(16):
                try:
                    return self._connect_attempt(driver_handler, i, chipv, bus, address)
                except ConnectionRefusedError:
                    pass
