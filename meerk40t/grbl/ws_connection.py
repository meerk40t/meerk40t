"""
WebSocket Connection

Communicate with a WebSocket destination with the GRBL driver.
"""

import websocket


class WSOutput:
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
            self._stream = websocket.WebSocket()
            self._stream.connect(
                "ws://%s:%d" % (self.service.address, self.service.port)
            )
            # self._stream.run_forever()
            self.service.signal("grbl;status", "connected")
        except TimeoutError:
            self.disconnect()
            self.service.signal("grbl;status", "timeout connect")
        except ConnectionError:
            self.disconnect()
            self.service.signal("grbl;status", "connection error")
        except IndexError as e:
            self.disconnect()
            self.service.signal("grbl;status", f"handshake error: {str(e)}")
        # except socket.gaierror as e:
        #     self.disconnect()
        #     self.service.signal("grbl;status", "address resolve error")
        # except socket.herror as e:
        #     self.disconnect()
        #     self.service.signal("grbl;status", f"herror: {str(e)}")
        except OSError as e:
            self.disconnect()
            self.service.signal("grbl;status", f"Host down {str(e)}")

    def disconnect(self):
        self.controller.log("Disconnected", type="connection")
        self.service.signal("grbl;status", "disconnected")
        self._stream.close()
        self._stream = None

    def write(self, data):
        self.service.signal("grbl;write", data)
        if isinstance(data, str):
            data = bytes(data, "utf-8")
        while data:
            try:
                sent = self._stream.send(data)
            except OSError as e:
                self.disconnect()
                self.service.signal("grbl;status", f"Host down {str(e)}")
                return
            if sent == len(data):
                return
            data = data[sent:]

    realtime_write = write

    def read(self):
        f = self.read_buffer.find(b"\n")

        if f == -1:
            try:
                d = self._stream.recv()
            except OSError as e:
                # Has been closed in the meantime...
                self.disconnect()
                self.service.signal("grbl;status", f"Host down {str(e)}")
                return
            if isinstance(d, str):
                self.read_buffer += d.encode("latin-1")
            else:
                self.read_buffer += d
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
            return f"WSOutput('{self.service.location()}','{self.name}')"
        return f"WSOutput('{self.service.location()}')"
