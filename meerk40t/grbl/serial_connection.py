"""
Serial Connection

Registers the serial connection using pyserial to talk with the serial devices.
"""

import serial
from serial import SerialException


class SerialConnection:
    def __init__(self, service):
        self.service = service
        self.channel = self.service.channel("grbl_state", buffer_size=20)
        self.laser = None
        self.read_buffer = bytearray()

    @property
    def connected(self):
        return self.laser is not None

    def read(self):
        try:
            self.read_buffer += self.laser.read(self.laser.in_waiting)
        except (SerialException, AttributeError, OSError, TypeError):
            pass
        f = self.read_buffer.find(b"\n")
        if f == -1:
            return None
        response = self.read_buffer[:f]
        self.read_buffer = self.read_buffer[f + 1 :]
        str_response = str(response, "raw_unicode_escape")
        str_response = str_response.strip()
        return str_response

    def write(self, line):
        try:
            self.laser.write(bytes(line, "utf-8"))
        except (SerialException, PermissionError) as e:
            self.channel(f"Error when writing '{line}: {str(e)}'")

    def connect(self):
        if self.laser:
            self.channel("Already connected")
            return

        signal_load = "uninitialized"
        try:
            self.channel("Attempting to Connect...")
            serial_port = self.service.serial_port
            if serial_port == "UNCONFIGURED":
                self.channel("Laser port is not set.")
                signal_load = "error"
                self.service.signal(
                    "warning",
                    "Serial Port is not set. Go to config, select the serial port for this device.",
                    "Serial Port: UNCONFIGURED",
                )
                return

            baud_rate = self.service.baud_rate
            self.laser = serial.Serial(
                serial_port,
                baud_rate,
                timeout=0,
            )
            self.channel("Connected")
            signal_load = "connected"
        except ConnectionError:
            self.channel("Connection Failed.")
        except SerialException:
            self.channel("Serial connection could not be established.")

        self.service.signal("grbl;status", signal_load)

    def disconnect(self):
        self.channel("Disconnected")
        if self.laser:
            self.laser.close()
            del self.laser
            self.laser = None
        self.service.signal("grbl;status", "disconnected")
