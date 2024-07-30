"""
Mock Connection for GRBL


The mock connection is used for debug and research purposes. And simply prints the data sent to it rather than engaging
any hardware.
"""
from meerk40t.grbl.emulator import GRBLEmulator


class MockConnection:
    def __init__(self, service, controller):
        self.service = service
        self.controller = controller
        self.laser = None
        self.read_buffer = bytearray()
        self.emulator = GRBLEmulator(
            device=None, units_to_device_matrix=service.view.matrix, reply=self.add_read
        )

    @property
    def connected(self):
        return self.laser is not None

    def add_read(self, code):
        self.read_buffer += bytes(code, encoding="raw_unicode_escape")

    def read(self):
        f = self.read_buffer.find(b"\n")
        if f == -1:
            return None
        response = self.read_buffer[:f]
        self.read_buffer = self.read_buffer[f + 1 :]
        str_response = str(response, "raw_unicode_escape")
        str_response = str_response.strip()
        return str_response

    def write(self, line: str):
        self.emulator.write(line)

    def connect(self):
        if self.laser:
            self.controller.log("Already connected", type="connection")
            return
        try:
            self.controller.log("Attempting to Connect...", type="connection")
            self.laser = True
            self.controller.log("Connected", type="connection")
            self.service.signal("grbl;status", "connected")
        except ConnectionError:
            self.controller.log("Connection Failed.", type="connection")

    def disconnect(self):
        self.laser = None
        self.controller.log("Disconnected", type="connection")
        self.service.signal("grbl;status", "disconnected")
