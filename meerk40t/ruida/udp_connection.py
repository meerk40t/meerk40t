import socket


class UDPConnection:
    def __init__(self, service):
        self.service = service
        name = self.service.label.replace(" ", "-")
        name = name.replace("/", "-")
        self.usb_log = service.channel(f"{name}/ruida")
        self.is_shutdown = False

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(2)
        self.socket.bind((self.service.address, 50200))

    def shutdown(self, *args, **kwargs):
        self.is_shutdown = True

    def write(self, data):
        self.socket.send(data)

    def write_real(self, data):
        self.socket.send(data)
