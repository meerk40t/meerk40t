"""
GRBL Emulator

Provides Emulation for GRBL devices. Allows MeerK40t to pretend to be a GRBL device and accept data from other programs
and treat that data as commands to control the current device.
"""
from meerk40t.core.cutcode.cutcode import CutCode
from meerk40t.core.cutcode.plotcut import PlotCut
from meerk40t.core.cutcode.waitcut import WaitCut

from meerk40t.core.node.cutnode import CutNode
from meerk40t.core.parameters import Parameters
from meerk40t.grbl.parser import GRBLParser
from meerk40t.kernel import Module
from meerk40t.svgelements import Arc


class GRBLEmulator(Module):
    def __init__(self, service, path):
        Module.__init__(self, service, path)

        self.parser = GRBLParser(self.plotter)

        self.design = False
        self.control = False
        self.parser.channel = service.channel("grbl_events")

        self.cutcode = CutCode()
        self.plotcut = PlotCut()

        self.device = service

        self._use_set = None

        self._attached_device = None

    def __repr__(self):
        return f"GcodeEmulator({self.name})"

    def set_reply(self, reply):
        self.parser.reply = reply

    def plotter(self, command, *args):
        if command == "move":
            x0, y0, x1, y1 = args
            self.plotcut.plot_append(x1, y1, 0)
        elif command in "line":
            x0, y0, x1, y1, power = args
            self.plotcut.plot_append(x1, y1, power)
        elif command in "arc":
            x0, y0, cx, cy, x1, y1, power = args
            a = Arc(start=(x0, y0), end=(x1, y1), control=(cx, cy))
            for p in range(51):
                # Do 50 interpolations of the arc.
                x, y = a.point(p / 50)
                self.plotcut.plot_append(x, y, power)
        elif command == "new":
            self.new_plot_cut()
        elif command == "end":
            self.spool_plot()
        elif command == "wait":
            # Time in seconds to wait.
            self.cutcode.append(WaitCut(*args))
        elif command == "resume":
            self.context("resume\n")
        elif command == "pause":
            self.context("pause\n")
        elif command == "abort":
            self.context("estop\n")
        elif command == "coolant":
            # True or False coolant.
            self.context.signal("coolant", *args)
        elif command == "jog_abort":
            pass

    def spool_plot(self):
        if not len(self.cutcode):
            # Nothing to spool.
            return
        matrix = self.context.device.scene_to_device_matrix()
        for plot in self.cutcode:
            try:
                for i in range(len(plot.plot)):
                    x, y, laser = plot.plot[i]
                    x, y = matrix.transform_point([x, y])
                    plot.plot[i] = int(x), int(y), laser
            except AttributeError:
                # This may be a WaitCut and has no plot.
                pass
        if self.control:
            self.context.device.spooler.laserjob([self.cutcode])
        if self.design:
            elements = self.context.elements
            node = CutNode(cutcode=self.cutcode)
            elements.op_branch.add_node(node)
        self.cutcode = CutCode()
        self.plotcut = PlotCut()

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

    def write(self, data):
        self.parser.write(data)
