from meerk40t.core.cutcode import PlotCut, CutCode, WaitCut
from meerk40t.core.parameters import Parameters
from meerk40t.core.units import UNITS_PER_MIL
from meerk40t.grbl.grblparser import GRBLParser
from meerk40t.kernel import Module


class GRBLEmulator(Module):
    def __init__(self, service, path):
        Module.__init__(self, service, path)

        self.parser = GRBLParser(self.plotter)

        self.design = False
        self.control = False
        self.saving = False
        self.parser.channel = service.channel("grbl_events")

        self.cutcode = CutCode()
        self.plotcut = PlotCut()

        self.spooler = None
        self.device = None

        self._use_set = None

        self._attached_device = None

    def __repr__(self):
        return f"GcodeEmulator({self.name})"

    def plotter(self, command, *args):
        if command == "move":
            x, y = args
            self.plotcut.plot_append(x, y, 0)
            ox, oy = self.context.physical_to_device_length(x, y)
            self.context.signal("emulator;position", (ox, oy, ox, ox))
        elif command in ("line", "arc"):
            # This should actually do different things if line or arc to.
            x0, y0, x1, y1, power = args
            self.plotcut.plot_append(x1, y1, power)
            ox, oy = self.context.physical_to_device_length(x0, y0)
            nx, ny = self.context.physical_to_device_length(x1, y1)
            self.context.signal("emulator;position", (ox, oy, nx, ny))
        elif command == "new":
            self.new_plot_cut()
        elif command == "coolant":
            self.spooler.laserjob(["signal", ("coolant", *args)], helper=True)
        elif command == "wait":
            self.cutcode.append(WaitCut(*args))
        elif command == "resume":
            self.spooler.laserjob("resume", helper=True)
        elif command == "pause":
            self.spooler.laserjob("pause", helper=True)
        elif command == "abort":
            self.spooler.laserjob("abort", helper=True)
        elif command == "jog_abort":
            pass

    def generate(self):
        for cutobject in self.cutcode:
            yield "plot", cutobject
        yield "plot_start"

    def new_plot_cut(self):
        if len(self.plotcut):
            self.plotcut.settings = self.cutset()
            self.plotcut.check_if_rasterable()
            self.cutcode.append(self.plotcut)
            self.plotcut = PlotCut()

    def cutset(self):
        if self._use_set is None:
            self._use_set = Parameters(dict(self.parser.settings))
        return self._use_set

    def module_open(self, *args, **kwargs):
        self._attached_device = "none"
        if hasattr(self.context, "com_port"):
            self._attached_device = self.context.com_port.lower()
        send = self.context.channel(f"send-{self._attached_device}")
        send.watch(self.parser.write)

    def module_close(self, *args, **kwargs):
        send = self.context.channel(f"send-{self._attached_device}")
        send.unwatch(self.parser.write)
