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
            self.context.signal(
                "emulator;position",
                (
                    x0 * UNITS_PER_MIL,
                    y0 * UNITS_PER_MIL,
                    x1 * UNITS_PER_MIL,
                    y1 * UNITS_PER_MIL,
                ),
            )

        self.parser.position = pos
        self._attached_device = None

    def __repr__(self):
        return f"GcodeEmulator({self.name})"

    def module_open(self, *args, **kwargs):
        context = self.context
        active = self.context.driver.name
        self._attached_device = active
        send = context.channel(f"{active}/usb_send")
        send.watch(self.parser.write)

    def module_close(self, *args, **kwargs):
        context = self.context
        active = self._attached_device
        send = context.channel(f"{active}/usb_send")
        send.unwatch(self.parser.write)
