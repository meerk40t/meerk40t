import time

from serial import SerialException


class MockConnection:
    def __init__(self, service):
        self.service = service
        self.channel = self.service.channel("grbl_state", buffer_size=20)
        self.laser = None
        self.read_buffer = bytearray()
        self.just_connected = False
        self.write_lines = 0

    @property
    def connected(self):
        return self.laser is not None

    def read(self):
        if self.just_connected:
            self.just_connected = False
            return "grbl version fake"
        if self.write_lines:
            time.sleep(0.01)  # takes some time
            self.write_lines -= 1
            return "ok"
        else:
            return ""

    def write(self, line):
        self.write_lines += 1

    def connect(self):
        if self.laser:
            self.channel("Already connected")
            return
        try:
            self.channel("Attempting to Connect...")
            self.laser = True
            self.just_connected = True
            self.channel("Connected")
            self.service.signal("serial;status", "connected")
        except ConnectionError:
            self.channel("Connection Failed.")
        except SerialException:
            self.channel("Serial connection could not be established.")

    def disconnect(self):
        self.channel("Disconnected")
        self.service.signal("serial;status", "disconnected")
