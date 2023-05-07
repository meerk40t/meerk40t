"""
GRBL Interpreter

The Interpreter listens to the local GRBL code being sent to the Controller and parses it. This allows it GRBL to track
position based on the data sent, and debug the device. This listens to the current device and thus must be attached
to a GRBL device.
"""
from meerk40t.grbl.emulator import GRBLEmulator
from meerk40t.kernel import Module


class GRBLInterpreter(Module):
    def __init__(self, service, path):
        Module.__init__(self, service, path)
        self.emulator = GRBLEmulator(self, service.space.display.matrix())
        self._attached_device = None

    def __repr__(self):
        return f"GcodeInterpreter({self.name})"

    def move_abs(self, x, y):
        self.context.signal("emulator;position", (x, y, x, y))

    def move_rel(self, x, y):
        self.context.signal("emulator;position", (x, y, x, y))

    def plot(self, cutobject):
        try:
            start = cutobject.start
            end = cutobject.end
        except AttributeError:
            return
        self.context.signal("emulator;position", (start[0], start[1], end[0], end[1]))

    def module_open(self, *args, **kwargs):
        self._attached_device = "none"
        if hasattr(self.context, "serial_port"):
            self._attached_device = self.context.serial_port.lower()
        send = self.context.channel(f"send-{self._attached_device}")
        send.watch(self.emulator.write)

    def module_close(self, *args, **kwargs):
        send = self.context.channel(f"send-{self._attached_device}")
        send.unwatch(self.emulator.write)
