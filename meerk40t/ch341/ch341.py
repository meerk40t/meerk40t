class CH341:
    def __init__(self, context, log):
        self.context = context
        self.log = log
        self.driver = None
        _ = self.log._
        try:
            from .libusb import CH341Driver as LibCH341Driver

            self.driver = LibCH341Driver(channel=self.log, state=self._state_change)
        except ImportError:
            self.log(_("PyUsb is not installed. Skipping."))
        try:
            from .windll import CH341Driver as WinCH341Driver

            self.driver = WinCH341Driver(channel=self.log, state=self._state_change)
        except ImportError:
            self.log(_("No Windll interfacing. Skipping."))

    def connect(self, driver_index=-1):
        """
        Requests and returns an available connection. The connection object itself has open() and close() functions and
        provides any information about the connection if available. If the connection is not opened, no resources are
        reserved.
        """
        _ = self.log._
        self.driver.open()

    def _state_change(self, state_value):
        self.context.signal("pipe;state", state_value)

