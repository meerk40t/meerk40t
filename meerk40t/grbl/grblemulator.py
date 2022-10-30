from meerk40t.core.units import UNITS_PER_MIL
from meerk40t.grbl.grblparser import GRBLParser
from meerk40t.kernel import Module


class GRBLEmulator(Module):
    def __init__(self, context, path):
        Module.__init__(self, context, path)
        self.parser = GRBLParser()
        self.parser.channel = self.context.channel("grbl_events")

        def pos(p):
            if p is None:
                return
            x0, y0, x1, y1 = p
            if x0 is None:
                return
            if y0 is None:
                return
            if x1 is None:
                return
            if y1 is None:
                return

            self.context.signal(
                "emulator;position",
                (
                    x0,
                    y0,
                    x1,
                    y1,
                ),
            )

        self.parser.position = pos
        self._attached_device = None

    def __repr__(self):
        return f"GcodeEmulator({self.name})"

    def module_open(self, *args, **kwargs):
        self._attached_device = "none"
        if hasattr(self.context, "com_port"):
            self._attached_device = self.context.com_port.lower()
        send = self.context.channel(f"send-{self._attached_device}")
        send.watch(self.parser.write)

    def module_close(self, *args, **kwargs):
        send = self.context.channel(f"send-{self._attached_device}")
        send.unwatch(self.parser.write)
