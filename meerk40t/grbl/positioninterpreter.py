"""
GRBL Interpreter

The Interpreter listens to the local GRBL code being sent to the Controller and parses it. This allows it GRBL to track
position based on the data sent, and debug the device. This listens to the current device and thus must be attached
to a GRBL device.
"""

from meerk40t.grbl.parser import GRBLParser
from meerk40t.kernel import Module


class GRBLPositionInterpreter(Module):
    def __init__(self, service, path):
        Module.__init__(self, service, path)

        self.parser = GRBLParser(self.plotter)

        self._attached_device = None

    def __repr__(self):
        return f"GcodeInterpreter({self.name})"

    def plotter(self, command, *args):
        if command == "move":
            x0, y0, x1, y1 = args
            ox, oy = self.context.device_to_scene_position(x0, y0)
            nx, ny = self.context.device_to_scene_position(x1, y1)
            self.context.signal("emulator;position", (ox, oy, nx, ny))
        elif command in "line":
            x0, y0, x1, y1, power = args
            ox, oy = self.context.device_to_scene_position(x0, y0)
            nx, ny = self.context.device_to_scene_position(x1, y1)
            self.context.signal("emulator;position", (ox, oy, nx, ny))
        elif command in "arc":
            x0, y0, cx, cy, x1, y1, power = args
            ox, oy = self.context.device_to_scene_position(x0, y0)
            nx, ny = self.context.device_to_scene_position(x1, y1)
            self.context.signal("emulator;position", (ox, oy, nx, ny))
        elif command == "new":
            pass

    def module_open(self, *args, **kwargs):
        self._attached_device = "none"
        if hasattr(self.context, "serial_port"):
            self._attached_device = self.context.serial_port.lower()
        send = self.context.channel(f"send-{self._attached_device}")
        send.watch(self.parser.write)

    def module_close(self, *args, **kwargs):
        send = self.context.channel(f"send-{self._attached_device}")
        send.unwatch(self.parser.write)
