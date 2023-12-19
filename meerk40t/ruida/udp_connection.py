import time


class UDPConnection:
    def __init__(self, service):
        self.service = service
        name = self.service.label.replace(" ", "-")
        name = name.replace("/", "-")
        self.usb_log = service.channel(f"{name}/usb", buffer_size=500)
        self.usb_log.watch(lambda e: service.signal("pipe;usb_status", e))
        self.is_shutdown = False
        self._is_opening = False
        self._abort_open = False
        self._disable_connect = False
        self._machine_index = 0

    def shutdown(self, *args, **kwargs):
        self.is_shutdown = True

    def set_disable_connect(self, status):
        self._disable_connect = status

    @property
    def connected(self):
        if self.connection is None:
            return False
        return self.connection.is_open(self._machine_index)

    @property
    def is_connecting(self):
        if self.connection is None:
            return False
        return self._is_opening

    def abort_connect(self):
        self._abort_open = True
        self.usb_log("Connect Attempts Aborted")

    def disconnect(self):
        try:
            self.connection.close(self._machine_index)
        except (ConnectionError, ConnectionRefusedError, AttributeError):
            pass
        self.connection = None
        # Reset error to allow another attempt
        self.set_disable_connect(False)

    def connect_if_needed(self):
        if self._disable_connect:
            # After many failures automatic connects are disabled. We require a manual connection.
            self.abort_connect()
            self.connection = None
            raise ConnectionRefusedError(
                "Ruida device was unreachable. Explicit connect required."
            )
        if self.connection is None:
            self.connection = MockConnection(self.usb_log)
            name = self.service.label.replace(" ", "-")
            name = name.replace("/", "-")
            self.connection.send = self.service.channel(f"{name}/send")
            self.connection.recv = self.service.channel(f"{name}/recv")
            # TODO: Needs usbconnection and udp connection.
            # self.connection = USBConnection(self.usb_log)
        self._is_opening = True
        self._abort_open = False
        count = 0
        while not self.connection.is_open(self._machine_index):
            try:
                if self.connection.open(self._machine_index) < 0:
                    raise ConnectionError
                self.init_laser()
            except (ConnectionError, ConnectionRefusedError):
                time.sleep(0.3)
                count += 1
                # self.usb_log(f"Error-Routine pass #{count}")
                if self.is_shutdown or self._abort_open:
                    self._is_opening = False
                    self._abort_open = False
                    return
                if self.connection.is_open(self._machine_index):
                    self.connection.close(self._machine_index)
                if count >= 10:
                    # We have failed too many times.
                    self._is_opening = False
                    self.set_disable_connect(True)
                    self.usb_log("Could not connect to the Ruida controller.")
                    self.usb_log("Automatic connections disabled.")
                    raise ConnectionRefusedError(
                        "Could not connect to the Ruida controller."
                    )
                time.sleep(0.3)
                continue
        self._is_opening = False
        self._abort_open = False

    def send(self, data, read=True):
        if self.is_shutdown:
            return -1, -1, -1, -1
        self.connect_if_needed()
        try:
            self.connection.write(self._machine_index, data)
        except ConnectionError:
            return -1, -1, -1, -1
        if read:
            try:
                r = self.connection.read(self._machine_index)
                return struct.unpack("<4H", r)
            except ConnectionError:
                return -1, -1, -1, -1

    def status(self):
        b0, b1, b2, b3 = self.get_version()
        return b3
