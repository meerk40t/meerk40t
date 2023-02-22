"""
Driver to Path is code adapted from jpirnay's modifications of GRBL parser to read parsed data. When the GRBLParser
was converted to a driverlike emulator, this functionality was spun off.
"""

from math import isnan

from meerk40t.core.node.node import Linecap, Linejoin
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.units import UNITS_PER_PIXEL, Length
from meerk40t.svgelements import Arc, Color, Matrix, Move, Path


class PlotterDriver:
    """
    This is a driverlike plotter that produces path and operations.
    """
    def __init__(self):
        self.last_x = 0
        self.last_y = 0
        self.power = 0
        self.speed = 0
        self.depth = 0
        self.paths = list()
        self.path = Path()
        self.operations = {}
        self.paths.append(self.path)
        self.split_path = True
        self.ignore_travel = True
        self.treat_z_as_power = True
        self.z_only_negative = True

    def check_operation_need(self):
        has_power = bool(self.power != 0)
        if self.treat_z_as_power:
            if self.z_only_negative and self.depth < 0:
                has_power = True
            elif not self.z_only_negative and self.depth != 0:
                has_power = True

        if self.speed != 0 and has_power:
            # Do we have this operation already?!
            id_string = f"{self.speed}|{self.power}|{self.depth}"
            if id_string not in self.operations:
                self.operations[id_string] = list()
            index = len(self.paths) - 1
            self.operations[id_string].append(index)

    def plotter(self, command, *args, **kwargs):
        def remove_trailing_moves():
            # Is the trailing segment a move ?
            while len(self.path) > 0 and isinstance(self.path[-1], Move):
                del self.path[-1]
            if len(self.path) == 0:
                # Degenerate...
                index = len(self.paths) - 1
                for op in self.operations:
                    if index in self.operations[op]:
                        opindex = self.operations[op].index(index)
                        self.operations[op].pop(opindex)
                if len(self.paths) > 0:
                    self.paths.pop(-1)

        def proper_z():
            res = False
            if self.treat_z_as_power:
                if self.depth < 0 and self.z_only_negative:
                    res = True
                elif self.depth != 0 and not self.z_only_negative:
                    res = True
                # print (f"only negative: {self.z_only_negative}, depth={self.depth}, res={res}")
            return res

        def needsadding(power):
            result = False
            if power is None:
                power = 0
            if self.ignore_travel:
                if power != 0 or proper_z():
                    result = True
            else:
                result = True
            return result

        # print (f"{command} - {args}")
        if command == "move":
            x0, y0, x1, y1 = args
            self.path.move((x1, y1))
        elif command == "line":
            x0, y0, x1, y1, power = args
            # Do we need it added?
            if needsadding(power):
                if not self.path:
                    self.path.move((x0, y0))
                self.path.line((x1, y1))
            else:
                self.path.move((x1, y1))
        elif command == "cw-arc":
            x0, y0, cx, cy, x1, y1, power = args
            # Do we need it added?
            if needsadding(power):
                arc = Arc(start=(x0, y0), center=(cx, cy), end=(x1, y1), ccw=False)
                if isnan(arc.sweep):
                    # This arc is not valid.
                    self.path.line((x1, y1))
                else:
                    self.path.append(arc)
            else:
                self.path.move((x1, y1))
        elif command == "ccw-arc":
            x0, y0, cx, cy, x1, y1, power = args
            # Do we need it added?
            if needsadding(power):
                arc = Arc(start=(x0, y0), center=(cx, cy), end=(x1, y1), ccw=True)
                if isnan(arc.sweep):
                    # This arc is not valid.
                    self.path.line((x1, y1))
                else:
                    self.path.append(arc)
            else:
                self.path.move((x1, y1))
        elif command == "new":
            # We break the path here and create a new one
            splitter = self.split_path
            if splitter and len(self.path):
                remove_trailing_moves()
                self.path = Path()
                self.paths.append(self.path)
                # print (f"Z at time of path start: {self.depth}")
            if len(args) > 1:
                feed = args[0]
                power = args[1]
                if feed != 0:
                    self.speed = feed
                if power != 0:
                    self.power = power
                self.check_operation_need()
        elif command == "end":
            # Is the trailing segment a move ?
            remove_trailing_moves()
        elif command == "zaxis":
            splitter = self.split_path
            if splitter and len(self.path):
                remove_trailing_moves()
                self.path = Path()
                self.paths.append(self.path)
                # print (f"Z at time of path start: {self.depth}")
            depth = args[0]
            self.depth = depth
            self.check_operation_need()
        elif command == "wait":
            pass
        elif command == "resume":
            pass
        elif command == "pause":
            pass
        elif command == "abort":
            pass
        elif command == "coolant":
            # True or False coolant.
            pass
        elif command == "jog_abort":
            pass


class DriverToPath:
    def __init__(self, plotter=None):
        self.settings = {
            "speed": 0,
            "power": 0,
        }
        self.origin = 1  # 0 top left, 1 bottom left, 2 center
        self.split_path = True
        self.ignore_travel = True
        self.treat_z_as_power = False
        self.z_only_negative = True
        self.no_duplicates = False
        self.create_operations = True

        self.scale_speed = False
        self.scale_speed_lower = 2
        self.scale_speed_higher = 200
        self.scale_power = False
        self.scale_power_lower = 200
        self.scale_power_higher = 1000

        self.options = [
            {
                "attr": "ignore_travel",
                "object": self,
                "default": True,
                "type": bool,
                "label": "Ignore travel",
                "tip": "Try to take only 'valid' movements",
                "section": "_10_Path",
            },
            {
                "attr": "split_path",
                "object": self,
                "default": True,
                "type": bool,
                "label": "Split paths",
                "tip": "Split path into smaller chunks",
                "section": "_10_Path",
            },
            {
                "attr": "no_duplicates",
                "object": self,
                "default": True,
                "type": bool,
                "label": "Single occurence",
                "tip": "Prevent duplicate creation of segments (like in a multipass operation)",
                "section": "_10_Path",
            },
            {
                "attr": "treat_z_as_power",
                "object": self,
                "default": False,
                "type": bool,
                "label": "Treat Z-Movement as On/Off",
                "tip": "Use negative Z-Values as a Power-On indicator, positive values as travel",
                "conditional": (self, "ignore_travel"),
                "section": "_10_Path",
                "subsection": "_10_Z-Axis",
            },
            {
                "attr": "z_only_negative",
                "object": self,
                "default": False,
                "type": bool,
                "label": "Only negative",
                "tip": "Active: use positive values as travel\nInactive: use all non-zero values",
                "conditional": (self, "treat_z_as_power"),
                "section": "_10_Path",
                "subsection": "_10_Z-Axis",
            },
            {
                "attr": "origin",
                "object": self,
                "default": 1,
                "type": int,
                "style": "option",
                "choices": (0, 1, 2, 3),
                "display": (
                    "Top Left",
                    "Bottom Left",
                    "Center",
                    "Center (Y mirrored)",
                ),
                "label": "Bed-Origin",
                "tip": "Correct starting point",
                "section": "_20_Correct Orientation",
            },
            {
                "attr": "create_operations",
                "object": self,
                "default": False,
                "type": bool,
                "label": "Create operations",
                "tip": "Create corresponding operations for Power and Speed pairs",
                "section": "_30_Operation",
            },
            {
                "attr": "scale_speed",
                "object": self,
                "default": False,
                "type": bool,
                "label": "Scale Speed",
                "tip": "Set lower and higher level to scale the speed\n"
                + "Minimum speed used will be mapped to lower level\n"
                + "Maximum speed used will be mapped to upper level",
                "conditional": (self, "create_operations"),
                "section": "_30_Operation",
                "subsection": "_20_Speed",
            },
            {
                "attr": "scale_speed_lower",
                "object": self,
                "default": 2,
                "type": float,
                "label": "Lowest speed",
                "trailer": "mm/sec",
                "tip": "Minimum speed used will be mapped to lower level",
                "conditional": (self, "scale_speed"),
                "section": "_30_Operation",
                "subsection": "_20_Speed",
            },
            {
                "attr": "scale_speed_higher",
                "object": self,
                "default": 200,
                "type": float,
                "label": "Highest speed",
                "trailer": "mm/sec",
                "tip": "Maximum speed used will be mapped to upper level",
                "conditional": (self, "scale_speed"),
                "section": "_30_Operation",
                "subsection": "_20_Speed",
            },
            {
                "attr": "scale_power",
                "object": self,
                "default": False,
                "type": bool,
                "label": "Scale Power",
                "tip": "Set lower and higher level to scale the power\n"
                + "Minimum power used will be mapped to lower level\n"
                + "Maximum power used will be mapped to upper level",
                "section": "_30_Operation",
                "subsection": "_20_Power",
            },
            {
                "attr": "scale_power_lower",
                "object": self,
                "default": 200,
                "type": float,
                "label": "Lowest Power",
                "trailer": "ppi",
                "tip": "Minimum power used will be mapped to lower level",
                "conditional": (self, "scale_power"),
                "section": "_30_Operation",
                "subsection": "_20_Power",
            },
            {
                "attr": "scale_power_higher",
                "object": self,
                "default": 1000,
                "type": float,
                "label": "Highest power",
                "trailer": "",
                "tip": "Maximum power used will be mapped to upper level",
                "conditional": (self, "scale_power"),
                "section": "_30_Operation",
                "subsection": "_20_Power",
            },
        ]

    def parse(self, emulator, data, elements, options=None):
        """Parse the data with the given emulator and create and add the relevant paths.

        Args:
            emulator: the emulator to use to parse the data, suffix entry value.
            data (bytes): the grbl code to parse
            elements (class): context for elements
            options (disctionary, optional): A dictionary with settings. Defaults to None.
        """
        with elements.static("driver_to_path"):
            plotter = PlotterDriver()
            for opt in self.options:
                if hasattr(plotter, opt["attr"]):
                    setattr(plotter, opt["attr"], getattr(self, opt["attr"]))

            emulator_class = elements.lookup(f"emulator/{emulator}")
            emulator_object = emulator_class(plotter, elements.device.scene_to_show_matrix())
            emulator_object.write(data)

            op_nodes = {}
            color_index = 0
            color_array = (
                "blue",
                "lime",
                "red",
                "black",
                "magenta",
                "cyan",
                "yellow",
                "teal",
                "orange",
                "aqua",
                "fuchsia",
                "navy",
                "olive",
                "springgreen",
            )
            if self.no_duplicates:
                for idx1 in range(0, len(plotter.paths) - 1):
                    path1 = plotter.paths[idx1]
                    for idx2 in range(idx1 + 1, len(plotter.paths)):
                        path2 = plotter.paths[idx2]
                        if path1 == path2:
                            plotter.paths[idx2] = None
            minspeed = None
            maxspeed = None
            minpower = None
            maxpower = None
            if self.scale_power or self.scale_speed:
                for op in plotter.operations:
                    values = op.split("|")
                    if len(values) > 1:
                        speed = float(values[0])
                        power = float(values[1])
                        if speed != 0:
                            if minspeed is None:
                                minspeed = speed
                            else:
                                minspeed = min(minspeed, speed)
                            if maxspeed is None:
                                maxspeed = speed
                            else:
                                maxspeed = max(maxspeed, speed)
                        if power != 0:
                            if minpower is None:
                                minpower = power
                            else:
                                minpower = min(minpower, power)
                            if maxpower is None:
                                maxpower = power
                            else:
                                maxpower = max(maxpower, power)
            if minpower is None or maxpower is None:
                self.scale_power = False
            elif minpower == maxpower:
                maxpower = minpower + 1
            if minspeed is None or maxspeed is None:
                self.scale_speed = False
            elif minspeed == maxspeed:
                maxspeed = minspeed + 1

            for index, path in enumerate(plotter.paths):
                if path is None or len(path) == 0:
                    continue
                color = Color("blue")
                opnode = None
                if self.create_operations:
                    for op in plotter.operations:
                        values = op.split("|")
                        speed = float(values[0])
                        power = float(values[1])
                        zvalue = float(values[2])
                        if index in plotter.operations[op]:
                            if op in op_nodes:
                                opnode = op_nodes[op]
                            else:
                                if self.scale_power and power != 0:
                                    power = self.scale_power_lower + (
                                        power - minpower
                                    ) / (maxpower - minpower) * (
                                        self.scale_power_higher - self.scale_power_lower
                                    )
                                if self.scale_speed and speed != 0:
                                    speed = self.scale_speed_lower + (
                                        speed - minspeed
                                    ) / (maxspeed - minspeed) * (
                                        self.scale_speed_higher - self.scale_speed_lower
                                    )
                                lbl = f"Grbl - P={power}, S={speed}"
                                if zvalue != 0:
                                    # convert into a length
                                    zlen = Length(amount=zvalue, digits=4).length_mm
                                    lbl += f", Z={zlen}"
                                opnode = EngraveOpNode(label=lbl)
                                opnode.speed = speed
                                if power == 0:
                                    power = 1000
                                opnode.power = power
                                opnode.color = Color(color_array[color_index])
                                color_index = (color_index + 1) % len(color_array)

                                elements.op_branch.add_node(opnode)
                                op_nodes[op] = opnode
                            break
                if opnode is not None:
                    color = opnode.color
                node = elements.elem_branch.add(
                    type="elem path",
                    path=abs(path),
                    stroke=color,
                    stroke_width=UNITS_PER_PIXEL,
                    linejoin=Linejoin.JOIN_BEVEL,
                    linecap=Linecap.CAP_SQUARE,
                )
                if opnode is not None:
                    opnode.add_reference(node)
