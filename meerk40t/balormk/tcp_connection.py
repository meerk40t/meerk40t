"""
Galvo USB Connection

Performs the required interactions with the Galvo backend through pyusb and libusb.
"""

import socket


class TCPConnection:
    def __init__(self, service, channel):
        super().__init__()

        self.channel = channel
        self.devices = {}
        self.interface = {}
        self.backend_error_code = None
        self.timeout = 100

        self.service = service
        self._stream = None
        self._read_buffer_size = 1024
        self.read_buffer = bytearray()
        self.name = service.name

    @property
    def connected(self):
        return self._stream is not None

    def open(self, index=0):
        try:
            self._stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._stream.connect((self.service.address, self.service.port))
            self.service.signal("grbl;status", "connected")
        except TimeoutError:
            self.close(index)
            self.service.signal("grbl;status", "timeout connect")
        except ConnectionError:
            self.close(index)
            self.service.signal("grbl;status", "connection error")
        except socket.gaierror as e:
            self.close(index)
            self.service.signal("grbl;status", "address resolve error")
        except socket.herror as e:
            self.close(index)
            self.service.signal("grbl;status", f"herror: {str(e)}")
        except OSError as e:
            self.close(index)
            self.service.signal("grbl;status", f"Host down {str(e)}")

    def close(self, index=0):
        self.service.signal("grbl;status", "disconnected")
        self._stream.close()
        self._stream = None

    def write(self, index=0, packet=None, attempt=0):
        while packet:
            sent = self._stream.send(packet)
            if sent == len(packet):
                return
            packet = packet[sent:]

    def read(self, index=0, attempt=0):
        f = self.read_buffer.find(b"\n")
        if f == -1:
            self.read_buffer += self._stream.recv(self._read_buffer_size)
            f = self.read_buffer.find(b"\n")
            if f == -1:
                return
        response = self.read_buffer[:f]
        self.read_buffer = self.read_buffer[f + 1 :]
        str_response = str(response, "latin-1")
        str_response = str_response.strip()
        return str_response

    def __repr__(self):
        if self.name is not None:
            return f"TCPOutput('{self.service.location()}','{self.name}')"
        return f"TCPOutput('{self.service.location()}')"
