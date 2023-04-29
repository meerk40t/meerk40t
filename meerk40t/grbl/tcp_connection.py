"""
TCP Connection

Communicate with a TCP network destination with the GRBL driver.
"""

import socket
import threading
import time


class TCPOutput:
    def __init__(self, context, name=None):
        super().__init__()
        self.service = context
        self._stream = None
        self._read_buffer_size = 1024
        self.read_buffer = bytearray()
        self.name = name

    @property
    def connected(self):
        return self._stream is not None

    def connect(self):
        try:
            self._stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._stream.connect((self.service.address, self.service.port))
            self.service.signal("tcp;status", "connected")
        except TimeoutError:
            self.disconnect()
            self.service.signal("tcp;status", "timeout connect")
        except ConnectionError:
            self.disconnect()
            self.service.signal("tcp;status", "connection error")
        except socket.gaierror as e:
            self.disconnect()
            self.service.signal("tcp;status", "address resolve error")
        except socket.herror as e:
            self.disconnect()
            self.service.signal("tcp;status", f"herror: {str(e)}")
        except OSError as e:
            self.disconnect()
            self.service.signal("tcp;status", f"Host down {str(e)}")

    def disconnect(self):
        self.service.signal("tcp;status", "disconnected")
        self._stream.close()
        self._stream = None

    def write(self, data):
        self.service.signal("tcp;write", data)
        if isinstance(data, str):
            data = bytes(data, "utf-8")
        while data:
            sent = self._stream.send(data)
            if sent == len(data):
                return
            data = data[sent:]

    realtime_write = write

    def read(self):
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
