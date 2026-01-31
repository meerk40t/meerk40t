"""
TCP Connection

Communicate with a TCP network destination with the GRBL driver.
"""

import socket


class TCPOutput:
    def __init__(self, service, controller, name=None):
        self.service = service
        self.controller = controller
        self._stream = None
        self._read_buffer_size = 1024
        self.read_buffer = bytearray()
        self.name = name

    @property
    def connected(self):
        return self._stream is not None

    def connect(self):
        try:
            self.controller.log("Attempting to Connect...", type="connection")
            self._stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Enable TCP keep-alive to prevent connection timeouts
            self._stream.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            # Set keep-alive parameters (platform-dependent)
            try:
                # TCP_KEEPIDLE: Time before sending keep-alive probes
                self._stream.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                # TCP_KEEPINTVL: Interval between keep-alive probes
                self._stream.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 30)
                # TCP_KEEPCNT: Number of failed probes before connection is closed
                self._stream.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
            except (AttributeError, OSError):
                # TCP keep-alive parameters may not be available on all platforms
                # Basic SO_KEEPALIVE should still work
                pass
            # Make sure port is in a valid range...
            port = min(65535, max(0, self.service.port))
            self._stream.connect((self.service.address, port))
            self.service.signal("grbl;status", "connected")
        except TimeoutError:
            self.disconnect()
            self.service.signal("grbl;status", "timeout connect")
        except ConnectionError:
            self.disconnect()
            self.service.signal("grbl;status", "connection error")
        except (socket.gaierror, OverflowError) as e:
            self.disconnect()
            self.service.signal("grbl;status", f"address resolve error: {str(e)}")
        except socket.herror as e:
            self.disconnect()
            self.service.signal("grbl;status", f"herror: {str(e)}")
        except OSError as e:
            self.disconnect()
            self.service.signal("grbl;status", f"Host down {str(e)}")
        except Exception as e:
            self.disconnect()
            self.service.signal("grbl;status", f"unknown error on connect: {str(e)}")

    def disconnect(self):
        self.controller.log("Disconnected", type="connection")
        self.service.signal("grbl;status", "disconnected")
        if self._stream is not None:
            self._stream.close()
        self._stream = None

    def write(self, data):
        self.service.signal("grbl;write", data)
        if isinstance(data, str):
            data = bytes(data, "utf-8")
        while data:
            try:
                sent = self._stream.send(data)
            except Exception as e:
                self.disconnect()
                self.service.signal("grbl;status", f"unknown error on write: {str(e)}")
                return
            if sent == len(data):
                return
            data = data[sent:]

    realtime_write = write

    def read(self):
        f = self.read_buffer.find(b"\n")
        if f == -1:
            try:
                self.read_buffer += self._stream.recv(self._read_buffer_size)
            except Exception as e:
                self.disconnect()
                self.service.signal("grbl;status", f"unknown error on read: {str(e)}")
                return
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
