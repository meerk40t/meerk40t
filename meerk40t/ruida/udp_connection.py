"""
UDP Connection handles Ruida UDP data sending and receiving and the Ruida protocols therein.
"""

import socket
import struct


class UDPConnection:
    def __init__(self, service):
        self.service = service
        name = self.service.safe_label
        self.recv = service.channel(f"{name}/recv", pure=True)
        self.send = service.channel(f"{name}/send", pure=True)
        self.events = service.channel(f"{name}/events", pure=True)
        self.is_shutdown = False
        self.recv_address = None
        self.socket = None

    def shutdown(self, *args, **kwargs):
        self.is_shutdown = True

    def open(self):
        if self.connected:
            return
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(4)
        self.socket.bind(("", 40200))

        name = self.service.safe_label
        self.service.threaded(
            self._run_udp_listener, thread_name=f"thread-{name}", daemon=True
        )
        self.service.signal("pipe;usb_status", "connected")
        self.events("Connected")

    def close(self):
        if not self.connected:
            return
        self.socket.close()
        self.socket = None
        self.service.signal("pipe;usb_status", "disconnected")
        self.events("Disconnected")

    @property
    def is_connecting(self):
        return False

    @property
    def connected(self):
        return not self.is_shutdown and self.socket is not None

    def abort_connect(self):
        pass

    def write(self, data):
        self.open()
        data = struct.pack(">H", sum(data) & 0xFFFF) + data
        self.socket.sendto(data, (self.service.address, 50200))
        self.send(data)

    def _run_udp_listener(self):
        try:
            while self.connected:
                try:
                    message, address = self.socket.recvfrom(1024)
                except (socket.timeout, AttributeError):
                    continue
                if address is not None:
                    self.recv_address = address
                self.recv(message)
        except OSError:
            pass
