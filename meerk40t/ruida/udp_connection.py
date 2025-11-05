"""
UDP Connection handles Ruida UDP data sending and receiving and the Ruida protocols therein.
"""

import socket
import queue
import struct

from meerk40t.ruida.rdjob import ACK, NAK, KEEP_ALIVE, ERR

class UDPConnection:
    def __init__(self, service):
        self.service = service
        name = self.service.safe_label
        self.recv = service.channel(f"{name}/recv", pure=True)
        self.send = service.channel(f"{name}/send", pure=True)
        self.events = service.channel(f"{name}/events", pure=True)
        self.is_shutdown = False
        self.recv_address = None
        self.send_port = 50200
        self.listen_port = 40200
        self.ctrl_port = 50207
        self.ctrl_listen_port = 40207
        self.socket = None
        self.swizzle = None
        self.unswizzle = None

    # Should verify type is a callable method.
    def set_swizzles(self, swizzle, unswizzle):
        """Set swizzle functions for use by the controller."""
        self.swizzle = swizzle
        self.unswizzle = unswizzle

    def open(self):
        if self.connected:
            return
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(self._s_to)
        self.socket.bind(("", self.listen_port))
        # TODO: usb_status is a misnomer.
        self.service.signal("pipe;usb_status", "connected")
        self.events("Connected")

    def close(self):
        if not self.connected:
            return
        self.socket.close()
        self.socket = None
        self.service.signal("pipe;usb_status", "disconnected")

    @property
    def is_connecting(self):
        return False

    @property
    def connected(self):
        return not self.is_shutdown and self.socket is not None

    def abort_connect(self):
        """Abort connection attempt."""
        pass

    def send(self, data):
        """Send data directly via UDP."""
        if not self.connected:
            return
        try:
            self.socket.sendto(data, (self.service.address, self.send_port))
            self.send(data)
        except (socket.error, OSError) as e:
            self.events(f"UDP send error: {e}")

    def recv(self):
        """Receive data from UDP socket."""
        if not self.connected:
            return None
        try:
            data, address = self.socket.recvfrom(1024)
            self.recv_address = address
            return data
        except socket.timeout:
            return None
        except (socket.error, OSError) as e:
            self.events(f"UDP recv error: {e}")
            return None

    def write(self, data):
        """Legacy write method for backward compatibility."""
        self.send(data)
