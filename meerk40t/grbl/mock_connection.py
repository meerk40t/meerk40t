"""
Mock Connection for GRBL


The mock connection is used for debug and research purposes. And simply prints the data sent to it rather than engaging
any hardware.
"""
import time


class MockConnection:
    def __init__(self, service):
        self.service = service
        self.channel = self.service.channel("grbl_state", buffer_size=20)
        self.laser = None
        self.read_buffer = bytearray()
        self.just_connected = False

    @property
    def connected(self):
        return self.laser is not None

    @property
    def _index_of_read_line(self):
        try:
            r = self.read_buffer.index(b"\r")
        except ValueError:
            r = -1
        try:
            n = self.read_buffer.index(b"\n")
        except ValueError:
            n = -1

        if n != -1:
            return min(n, r) if r != -1 else n
        else:
            return r

    def read_buffer_command(self):
        q = self._index_of_read_line
        if q == -1:
            raise ValueError("No forward command exists.")
        cmd_issued = self.read_buffer[: q + 1]
        self.read_buffer = self.read_buffer[q + 1 :]
        return cmd_issued

    def read(self):
        if self.just_connected:
            self.just_connected = False
            return "Grbl 1.1f ['$' for help]\r\n" "[MSG:’$H’|’$X’ to unlock]\r\n"
        try:
            cmd = self.read_buffer_command()
            return "ok"
        except ValueError:
            return ""

    def write(self, line: str):
        self.read_buffer += line.encode(encoding="latin-1")

    def connect(self):
        if self.laser:
            self.channel("Already connected")
            return
        try:
            self.channel("Attempting to Connect...")
            self.laser = True
            self.just_connected = True
            self.channel("Connected")
            self.service.signal("grbl;status", "connected")
        except ConnectionError:
            self.channel("Connection Failed.")

    def disconnect(self):
        self.laser = None
        self.channel("Disconnected")
        self.service.signal("grbl;status", "disconnected")
