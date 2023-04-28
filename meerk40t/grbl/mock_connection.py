"""
Mock Connection for GRBL


The mock connection is used for debug and research purposes. And simply prints the data sent to it rather than engaging
any hardware.
"""
import time

from serial import SerialException


class MockConnection:
    def __init__(self, service):
        self.service = service
        self.channel = self.service.channel("grbl_state", buffer_size=20)
        self.laser = None
        self.read_buffer = bytearray()
        self.just_connected = False
        self.time_stamps = []

    @property
    def connected(self):
        return self.laser is not None

    def read(self):
        if self.just_connected:
            self.just_connected = False
            return "grbl version fake"
        if self.time_stamps:
            if self.time_stamps[0] < (time.time() - 0.3):
                self.time_stamps.pop(0)
                return "ok"
        return ""

    def write(self, line):
        self.time_stamps.append(time.time())

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
        self.laser = None
        self.channel("Disconnected")
        self.service.signal("serial;status", "disconnected")
