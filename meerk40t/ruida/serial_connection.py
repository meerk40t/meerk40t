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

        name = self.service.safe_label
        self.recv = service.channel(f"{name}/recv", pure=True)
        self.send = service.channel(f"{name}/send", pure=True)
        self.events = service.channel(f"{name}/events", pure=True)
        self.is_shutdown = False

    def shutdown(self, *args, **kwargs):
        self.is_shutdown = True

    def open(self):
        if self.connected:
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

            self.service.threaded(
                self._run_serial_listener,
                thread_name=f"thread-{self.service.safe_label}",
                daemon=True,
            )
            self.service.signal("pipe;usb_status", "connected")
            self.events("Connected")

            signal_load = "connected"
        except ConnectionError:
            self.events("Connection Failed.")
        except SerialException as e:
            self.events("Serial connection could not be established.")
            self.events(str(e))

        self.service.signal("ruida;status", signal_load)

    def close(self):
        if not self.connected:
            return
        self.events("Disconnected")
        self.laser.close()
        del self.laser
        self.laser = None
        self.service.signal("pipe;usb_status", "disconnected")

    @property
    def connected(self):
        return self.laser is not None

    @property
    def is_connecting(self):
        return False

    def abort_connect(self):
        pass

    def write(self, line, retry=0):
        if not self.connected:
            self.open()
        try:
            self.laser.write(line)
            self.send(line)
        except (SerialException, PermissionError, TypeError, AttributeError) as e:
            # Type error occurs when `pipe_abort_write_r` is none, inside serialpostix.read() (out of sequence close)
            self.events(f"Error when writing '{line}: {str(e)}'")
            if retry > 5:
                return
            self.close()
            self.open()
            self.write(line, retry + 1)

    def _run_serial_listener(self):
        try:
            while self.connected and not self.is_shutdown:
                try:
                    message = self.laser.read(self.laser.in_waiting)
                    if message:
                        self.recv(message)
                except (SerialException, AttributeError, OSError, TypeError):
                    pass

        except OSError:
            pass
