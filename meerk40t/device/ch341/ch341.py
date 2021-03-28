from meerk40t.kernel import Module


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("module/ch341", CH341)


class CH341(Module):
    """
    Generic CH341 Module performs the interactions between the requested operations and several delegated backend ch341
    drivers. This permits interfacing with LibUsb, Windll or Mock Ch341 backends. In use-agnostic fashion, this should
    be valid and acceptable for any CH341 interactions. CH341 chip interfacing is required for Lhystudios Controllers,
    Moshiboard Controllers, and other interactions such as a plugin that uses addition CH341 devices.
    """
    def __init__(self, *args, **kwargs):
        Module.__init__(self, *args, **kwargs)
        self.usb_log = self.context.channel("pipe/usb")

    def state_change(self, state_value):
        self.context.signal("pipe;state", state_value)

    def connect(self, mock=False):
        """
        Requests and returns an available connection. The connection object itself has open() and close() functions and
        provides any information about the connection if available. If the connection is not opened, no resources are
        reserved.
        """
        _ = self.usb_log._

        if mock:
            try:
                from .mock import Handler
                driver_handler = Handler(channel=self.usb_log, state=self.state_change)
                for i in range(16):
                    connection = driver_handler.connect(i)
                    chip_version = connection.get_chip_version()
                    self.usb_log(_("CH341 Chip Version: %d") % chip_version)
                    self.context.signal("pipe;chipv", chip_version)
                    self.usb_log(_("Driver Forced: Mock"))
                    self.state_change("STATE_CONNECTED")
                    self.usb_log(_("Device Connected.\n"))
                    return connection
            except ConnectionRefusedError:
                pass

        try:
            from .libusb import Handler
            driver_handler = Handler(channel=self.usb_log, state=self.state_change)
            for i in range(16):
                connection = driver_handler.connect(i)
                chip_version = connection.get_chip_version()
                self.usb_log(_("CH341 Chip Version: %d") % chip_version)
                self.context.signal("pipe;chipv", chip_version)
                self.usb_log(_("Driver Detected: LibUsb"))
                self.state_change("STATE_CONNECTED")
                self.usb_log(_("Device Connected.\n"))
                return connection
        except ConnectionRefusedError:
            pass
        except ImportError:
            self.usb_log(_("PyUsb is not installed. Skipping."))

        try:
            from .windll import Handler
            driver_handler = Handler(channel=self.usb_log, state=self.state_change)
            for i in range(16):
                connection = driver_handler.connect(i)
                chip_version = connection.get_chip_version()
                self.usb_log(_("CH341 Chip Version: %d") % chip_version)
                self.context.signal("pipe;chipv", chip_version)
                self.usb_log(_("Driver Detected: CH341"))
                self.state_change("STATE_CONNECTED")
                self.usb_log(_("Device Connected.\n"))
                return connection
        except ConnectionRefusedError:
            pass
        except ImportError:
            self.usb_log(_("No Windll interfacing. Skipping."))
