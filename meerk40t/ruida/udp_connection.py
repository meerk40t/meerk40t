import socket
import struct


class UDPConnection:
    def __init__(self, service):
        self.service = service
        name = self.service.label.replace(" ", "-")
        name = name.replace("/", "-")
        self.recv = service.channel(f"{name}/recv", pure=True)
        self.is_shutdown = False

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(4)
        self.socket.bind(("", 40200))
        self.service.threaded(
            self.run_udp_listener, thread_name=f"thread-{name}", daemon=True
        )
        self.recv_address = None

    def shutdown(self, *args, **kwargs):
        self.is_shutdown = True

    @property
    def connected(self):
        return not self.is_shutdown

    def write(self, data):
        data = struct.pack(">H", sum(data) & 0xFFFF) + data
        self.socket.sendto(data, (self.service.address, 50200))

    def write_real(self, data):
        data = struct.pack(">H", sum(data) & 0xFFFF) + data
        self.socket.sendto(data, (self.service.address, 50200))

    def run_udp_listener(self):
        try:
            while not self.is_shutdown:
                try:
                    message, address = self.socket.recvfrom(1024)
                except (socket.timeout, AttributeError):
                    continue
                if address is not None:
                    self.recv_address = address
                self.recv(message)
        except OSError:
            pass
