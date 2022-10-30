from meerk40t.core.cutcode import PlotCut, CutCode, WaitCut
from meerk40t.core.parameters import Parameters
from meerk40t.grbl.grblparser import GRBLParser
from meerk40t.kernel import Module


class GRBLInterpreter(Module):
    def __init__(self, service, path):
        Module.__init__(self, service, path)

        self.parser = GRBLParser(self.plotter)

        self.design = False
        self.control = False
        self.parser.channel = service.channel("grbl_events")

        self.cutcode = CutCode()
        self.plotcut = PlotCut()

        self.spooler = None
        self.device = None

        self._use_set = None

        self._attached_device = None

    def __repr__(self):
        return f"GcodeInterpreter({self.name})"

    def plotter(self, command, *args):
        if command == "move":
            x0, y0, x1, y1 = args
            self.plotcut.plot_append(x1, y1, 0)
            ox, oy = self.context.device_to_scene_position(x0, y0)
            nx, ny = self.context.device_to_scene_position(x1, y1)
            self.context.signal("emulator;position", (ox, oy, nx, ny))
        elif command in "line":
            x0, y0, x1, y1, power = args
            self.plotcut.plot_append(x1, y1, power)
            ox, oy = self.context.device_to_scene_position(x0, y0)
            nx, ny = self.context.device_to_scene_position(x1, y1)
            self.context.signal("emulator;position", (ox, oy, nx, ny))
        elif command in "arc":
            x0, y0, cx, cy, x1, y1, power = args
            self.plotcut.plot_append(x1, y1, power)
            ox, oy = self.context.device_to_scene_position(x0, y0)
            nx, ny = self.context.device_to_scene_position(x1, y1)
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
            self.plotcut.settings = dict(self.parser.settings)
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
