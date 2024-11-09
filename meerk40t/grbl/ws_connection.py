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
            self.controller.log(
                f"Connecting to ws://{self.service.address}:{self.service.port}...",
                type="connection",
            )
            self._stream = websocket.WebSocket()
            self._stream.connect(
                "ws://%s:%d" % (self.service.address, self.service.port)
            )
            # self._stream.run_forever()
            self.service.signal("grbl;status", "connected")
        except TimeoutError:
            self.disconnect()
            self.service.signal("grbl;status", "timeout connect")
            self.controller.log("Attempt failed due to timeout", type="connection")
        except ConnectionError as e:
            self.disconnect()
            self.service.signal("grbl;status", "connection error")
            self.controller.log(f"Attempt failed: {str(e)}", type="connection")
        except IndexError as e:
            self.disconnect()
            self.service.signal("grbl;status", f"handshake error: {str(e)}")
            self.controller.log(
                f"Attempt failed due to handshake-error: {str(e)}", type="connection"
            )
        # except socket.gaierror as e:
        #     self.disconnect()
        #     self.service.signal("grbl;status", "address resolve error")
        # except socket.herror as e:
        #     self.disconnect()
        #     self.service.signal("grbl;status", f"herror: {str(e)}")
        except (websocket.WebSocketConnectionClosedException, OSError) as e:
            self.disconnect()
            self.service.signal("grbl;status", f"Host down {str(e)}")
            self.controller.log(
                f"Attempt failed: Host down {str(e)}", type="connection"
            )

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
            except (websocket.WebSocketConnectionClosedException, OSError) as e:
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
            except (websocket.WebSocketConnectionClosedException, OSError) as e:
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
