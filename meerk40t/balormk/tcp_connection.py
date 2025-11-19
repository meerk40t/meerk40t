"""
Balor TCP Connection

Governs the TCP connection for the balor device. This allows the output controller to write to a particular
network location.
"""

import socket
import time


class TCPConnection:
    def __init__(self, service):
        self.service = service
        self.socket = None
        self.timeout = 5.0

    def is_open(self, index=0):
        return self.socket is not None

    def open(self, index=0):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.service.address, self.service.port))
            self.service.signal("tcp;status", "connected")
            self.socket.settimeout(self.timeout)
            return index
        except Exception as e:
            self.service.signal("tcp;status", f"error: {e}")
            self.socket = None
            return -1

    def close(self, index=0):
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
        self.service.signal("tcp;status", "disconnected")

    def write(self, index=0, packet=None, attempt=0):
        if self.socket is None:
            if attempt == 0:
                self.open(index)
                if self.socket:
                    self.write(index, packet, attempt + 1)
                    return
            raise ConnectionError("Not connected")

        try:
            if packet:
                self.socket.sendall(packet)
        except Exception as e:
            self.close()
            if attempt < 3:
                time.sleep(0.1)
                self.open(index)
                self.write(index, packet, attempt + 1)
            else:
                raise ConnectionError(f"Failed to write: {e}")

    def read(self, index=0, attempt=0):
        if self.socket is None:
            if attempt == 0:
                self.open(index)
                if self.socket:
                    return self.read(index, attempt + 1)
            raise ConnectionError("Not connected")

        try:
            data = self.socket.recv(8)
            if len(data) < 8:
                while len(data) < 8:
                    more = self.socket.recv(8 - len(data))
                    if not more:
                        break
                    data += more
            return data
        except Exception as e:
            self.close()
            if attempt < 3:
                time.sleep(0.1)
                self.open(index)
                return self.read(index, attempt + 1)
            else:
                raise ConnectionError(f"Failed to read: {e}")
