"""
Serial Connection

Registers the serial connection using pyserial to talk with the serial devices.
"""

import serial
from serial import SerialException


class SerialConnection:
    def __init__(self, service):
        self.service = service
        self.controller = service.driver.controller
        self.laser = None
        self.read_buffer = bytearray()

        name = self.service.label.replace(" ", "-")
        name = name.replace("/", "-")
        self.recv = service.channel(f"{name}/recv", pure=True)
        self.send = service.channel(f"{name}/send", pure=True)
        self.events = service.channel(f"{name}/events", pure=True)

    @property
    def connected(self):
        return self.laser is not None

    @property
    def is_connecting(self):
        return False

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
        self.recv(response)

    def write(self, line, retry=0):
        try:
            self.laser.write(line)
            self.send(line)
        except (SerialException, PermissionError, TypeError, AttributeError) as e:
            # Type error occurs when `pipe_abort_write_r` is none, inside serialpostix.read() (out of sequence close)
            self.events(f"Error when writing '{line}: {str(e)}'")
            if retry > 5:
                return
            self.disconnect()
            self.connect()
            self.write(line, retry + 1)
            self.read()

    def open(self):
        if self.laser:
            self.events("Already connected")
            return

        signal_load = "uninitialized"
        try:
            self.events("Attempting to Connect...")
            serial_port = self.service.serial_port
            if serial_port == "UNCONFIGURED":
                self.events("Laser port is not set.")
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
            self.events("Connected")
            signal_load = "connected"
        except ConnectionError:
            self.events("Connection Failed.")
        except SerialException as e:
            self.events("Serial connection could not be established.")
            self.events(str(e))

        self.service.signal("ruida;status", signal_load)

    def close(self):
        self.events("Disconnected")
        if self.laser:
            self.laser.close()
            del self.laser
            self.laser = None
        self.service.signal("ruida;status", "disconnected")
