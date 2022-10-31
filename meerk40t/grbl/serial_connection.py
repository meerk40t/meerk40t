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
            if self.laser.in_waiting:
                self.read_buffer += self.laser.readall()
        except (SerialException, AttributeError, OSError):
            return None
        f = self.read_buffer.find(b"\n")
        if f == -1:
            return None
        response = self.read_buffer[:f]
        self.read_buffer = self.read_buffer[f + 1 :]
        str_response = str(response, "utf-8")
        str_response = str_response.strip()
        return str_response

    def write(self, line):
        self.laser.write(bytes(line, "utf-8"))

    def connect(self):
        if self.laser:
            self.channel("Already connected")
            return

        try:
            self.channel("Attempting to Connect...")
            com_port = self.service.com_port
            baud_rate = self.service.baud_rate
            self.laser = serial.Serial(
                com_port,
                baud_rate,
                timeout=0,
            )
            self.channel("Connected")
            self.service.signal("serial;status", "connected")
        except ConnectionError:
            self.channel("Connection Failed.")
        except SerialException:
            self.channel("Serial connection could not be established.")

    def disconnect(self):
        self.channel("Disconnected")
        if self.laser:
            self.laser.close()
            del self.laser
            self.laser = None
        self.service.signal("serial;status", "disconnected")
