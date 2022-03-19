import functools
import os.path
from os.path import realpath
import re
from copy import copy
from math import cos, gcd, pi, sin, tau

from meerk40t.core.exceptions import BadFileError
from meerk40t.kernel import CommandSyntaxError, Service, Settings
from meerk40t.tools.rastergrouping import group_overlapped_rasters

from ..svgelements import (
    PATTERN_FLOAT,
    PATTERN_LENGTH_UNITS,
    PATTERN_PERCENT,
    REGEX_LENGTH,
    Angle,
    Circle,
    Color,
    Ellipse,
    Group,
    Matrix,
    Path,
    Point,
    Polygon,
    Polyline,
    Rect,
    Shape,
    SimpleLine,
    SVGElement,
    SVGImage,
    SVGText,
    Viewbox,
)
from .cutcode import CutCode
from .node.commandop import CommandOperation
from .node.consoleop import ConsoleOperation
from .node.laserop import (
    CutOpNode,
    DotsOpNode,
    EngraveOpNode,
    ImageOpNode,
    RasterOpNode,
)
from .node.node import OP_PRIORITIES, is_dot, is_straight_line, label_truncate_re
from .node.rootnode import RootNode
from .units import UNITS_PER_INCH, UNITS_PER_PIXEL, Length


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "register":
        kernel.add_service("elements", Elemental(kernel))
        # kernel.add_service("elements", Elemental(kernel,1))
    elif lifecycle == "postboot":
        elements = kernel.elements
        choices = [
            {
                "attr": "operation_default_empty",
                "object": elements,
                "default": True,
                "type": bool,
                "label": _("Default Operation Other/Red/Blue"),
                "tip": _(
                    "Sets Operations to Other/Red/Blue if loaded with no operations."
                ),
            },
            {
                "attr": "classify_reverse",
                "object": elements,
                "default": False,
                "type": bool,
                "label": _("Classify Reversed"),
                "tip": _(
                    "Classify elements into operations in reverse order e.g. to match Inkscape's Object List"
                ),
            },
            {
                "attr": "legacy_classification",
                "object": elements,
                "default": False,
                "type": bool,
                "label": _("Legacy Classify"),
                "tip": _(
                    "Use the legacy classification algorithm rather than the modern classification algorithm."
                ),
            },
        ]
        kernel.register_choices("preferences", choices)
    elif lifecycle == "prestart":
        if hasattr(kernel.args, "input") and kernel.args.input is not None:
            # Load any input file
            elements = kernel.elements

            try:
                elements.load(realpath(kernel.args.input.name))
            except BadFileError as e:
                kernel._console_channel(
                    _("File is Malformed")
                    + ": " + str(e)
                )
            else:
                elements.classify(list(elements.elems()))
    elif lifecycle == "poststart":
        if hasattr(kernel.args, "output") and kernel.args.output is not None:
            # output the file you have at this point.
            elements = kernel.elements

            elements.save(realpath(kernel.args.output.name))


def reversed_enumerate(collection: list):
    for i in range(len(collection) - 1, -1, -1):
        yield i, collection[i]


class Elemental(Service):
    """
    The elemental service is governs all the interactions with the various elements,
    operations, and filenodes. Handling structure change and selection, emphasis, and
    highlighting changes. The goal of this module is to make sure that the life cycle
    of the elements is strictly enforced. For example, every element that is removed
    must have had the .cache deleted. And anything selecting an element must propagate
    that information out to inform other interested modules.
    """

    def __init__(self, kernel, index=None, *args, **kwargs):
        Service.__init__(
            self, kernel, "elements" if index is None else "elements%d" % index
        )
        self._clipboard = {}
        self._clipboard_default = "0"
        self.units = "nm"
        self.unitless = UNITS_PER_PIXEL

        self.note = None
        self._emphasized_bounds = None
        self._emphasized_bounds_dirty = True
        self._tree = RootNode(self)

        self.setting(bool, "classify_reverse", False)
        self.setting(bool, "legacy_classification", False)
        self.setting(bool, "auto_note", True)
        self.setting(bool, "uniform_svg", False)
        self.setting(float, "svg_ppi", 96.0)
        self.setting(bool, "operation_default_empty", True)

        self.op_data = Settings(self.kernel.name, "operations.cfg")

        self._init_commands(kernel)
        self._init_tree(kernel)
        self.load_persistent_operations("previous")

        ops = list(self.ops())
        if not len(ops) and self.operation_default_empty:
            self.load_default()

    def _init_commands(self, kernel):

        _ = kernel.translation

        @self.console_argument("filename")
        @self.console_command(
            "load",
            help=_("loads file from working directory"),
            input_type=None,
            output_type="file",
        )
        def load(channel, _, filename=None, **kwargs):
            import os

            if filename is None:
                channel(_("No file specified."))
                return
            new_file = os.path.join(self.kernel.current_directory, filename)
            if not os.path.exists(new_file):
                channel(_("No such file."))
                return
            try:
                result = self.load(new_file)
                if result:
                    channel(_("loading..."))
            except AttributeError:
                raise CommandSyntaxError(_("Loading files was not defined"))
            return "file", new_file

        # ==========
        # MATERIALS COMMANDS
        # ==========

        @self.console_command(
            "material",
            help=_("material base operation"),
            input_type=(None, "ops"),
            output_type="materials",
        )
        def materials(command, channel, _, data=None, remainder=None, **kwargs):
            if data is None:
                data = list(self.ops(emphasized=True))
            if remainder is None:
                channel("----------")
                channel(_("Materials:"))
                secs = self.op_data.section_set()
                for section in secs:
                    channel(section)
                channel("----------")
            return "materials", data

        @self.console_argument("name", help=_("Name to save the materials under"))
        @self.console_command(
            "save",
            help=_("Save current materials to persistent settings"),
            input_type="materials",
            output_type="materials",
        )
        def save_materials(command, channel, _, data=None, name=None, **kwargs):
            if name is None:
                raise CommandSyntaxError
            self.save_persistent_operations(name)
            return "materials", data

        @self.console_argument("name", help=_("Name to load the materials from"))
        @self.console_command(
            "load",
            help=_("Load materials from persistent settings"),
            input_type="materials",
            output_type="ops",
        )
        def load_materials(name=None, **kwargs):
            if name is None:
                raise CommandSyntaxError
            self.load_persistent_operations(name)
            return "ops", list(self.ops())

        @self.console_argument("name", help=_("Name to delete the materials from"))
        @self.console_command(
            "delete",
            help=_("Delete materials from persistent settings"),
            input_type="materials",
            output_type="materials",
        )
        def load_materials(name=None, **kwargs):
            if name is None:
                raise CommandSyntaxError
            self.clear_persistent_operations(name)
            return "materials", list(self.ops())

        @self.console_argument("name", help=_("Name to display the materials from"))
        @self.console_command(
            "list",
            help=_("Show information about materials"),
            input_type="materials",
            output_type="materials",
        )
        def materials_list(channel, _, data=None, name=None, **kwargs):
            channel("----------")
            channel(_("Materials Current:"))
            secs = self.op_data.section_set()
            for section in secs:
                subsection = self.op_data.derivable(section)
                for subsect in subsection:
                    label = self.op_data.read_persistent(str, subsect, "label", "-")
                    channel(
                        "{subsection}: {label}".format(
                            section=section, subsection=subsect, label=label
                        )
                    )
            channel("----------")

        # ==========
        # OPERATION BASE
        # ==========

        @self.console_command("operations", help=_("Show information about operations"))
        def element(**kwargs):
            self(".operation* list\n")

        @self.console_command(
            "operation.*", help=_("operation.*: selected operations"), output_type="ops"
        )
        def operation(**kwargs):
            return "ops", list(self.ops(emphasized=True))

        @self.console_command(
            "operation*", help=_("operation*: all operations"), output_type="ops"
        )
        def operation(**kwargs):
            return "ops", list(self.ops())

        @self.console_command(
            "operation~",
            help=_("operation~: non selected operations."),
            output_type="ops",
        )
        def operation(**kwargs):
            return "ops", list(self.ops(emphasized=False))

        @self.console_command(
            "operation", help=_("operation: selected operations."), output_type="ops"
        )
        def operation(**kwargs):
            return "ops", list(self.ops(emphasized=True))

        @self.console_command(
            r"operation([0-9]+,?)+",
            help=_("operation0,2: operation #0 and #2"),
            regex=True,
            output_type="ops",
        )
        def operation(command, channel, _, **kwargs):
            arg = command[9:]
            op_values = []
            for value in arg.split(","):
                try:
                    value = int(value)
                except ValueError:
                    continue
                try:
                    op = self.get_op(value)
                    op_values.append(op)
                except IndexError:
                    channel(_("index %d out of range") % value)
            return "ops", op_values

        @self.console_command(
            "select",
            help=_("Set these values as the selection."),
            input_type="ops",
            output_type="ops",
        )
        def operation_select(data=None, **kwargs):
            self.set_emphasis(data)
            return "ops", data

        @self.console_command(
            "select+",
            help=_("Add the input to the selection"),
            input_type="ops",
            output_type="ops",
        )
        def operation_select_plus(data=None, **kwargs):
            ops = list(self.ops(emphasized=True))
            ops.extend(data)
            self.set_emphasis(ops)
            return "ops", ops

        @self.console_command(
            "select-",
            help=_("Remove the input data from the selection"),
            input_type="ops",
            output_type="ops",
        )
        def operation_select_minus(data=None, **kwargs):
            ops = list(self.ops(emphasized=True))
            for e in data:
                try:
                    ops.remove(e)
                except ValueError:
                    pass
            self.set_emphasis(ops)
            return "ops", ops

        @self.console_command(
            "select^",
            help=_("Toggle the input data in the selection"),
            input_type="ops",
            output_type="ops",
        )
        def operation_select_xor(data=None, **kwargs):
            ops = list(self.ops(emphasized=True))
            for e in data:
                try:
                    ops.remove(e)
                except ValueError:
                    ops.append(e)
            self.set_emphasis(ops)
            return "ops", ops

        @self.console_argument("start", type=int, help=_("operation start"))
        @self.console_argument("end", type=int, help=_("operation end"))
        @self.console_argument("step", type=int, help=_("operation step"))
        @self.console_command(
            "range",
            help=_("Subset existing selection by begin and end indices and step"),
            input_type="ops",
            output_type="ops",
        )
        def operation_select_range(data=None, start=None, end=None, step=1, **kwargs):
            subops = list()
            for e in range(start, end, step):
                try:
                    subops.append(data[e])
                except IndexError:
                    pass
            self.set_emphasis(subops)
            return "ops", subops

        @self.console_argument("filter", type=str, help=_("Filter to apply"))
        @self.console_command(
            "filter",
            help=_("Filter data by given value"),
            input_type="ops",
            output_type="ops",
        )
        def operation_filter(channel=None, data=None, filter=None, **kwargs):
            """
            Apply a filter string to a filter particular operations from the current data.
            Operations are evaluated in an infix prioritized stack format without spaces.
            Qualified values are speed, power, step, acceleration, passes, color, op, overscan, len
            Valid operators are >, >=, <, <=, =, ==, +, -, *, /, &, &&, |, and ||
            eg. filter speed>=10, filter speed=5+5, filter speed>power/10, filter speed==2*4+2
            eg. filter engrave=op&speed=35|cut=op&speed=10
            eg. filter len=0
            """
            subops = list()
            _filter_parse = [
                ("SKIP", r"[ ,\t\n\x09\x0A\x0C\x0D]+"),
                ("OP20", r"(\*|/)"),
                ("OP15", r"(\+|-)"),
                ("OP11", r"(<=|>=|==|!=)"),
                ("OP10", r"(<|>|=)"),
                ("OP5", r"(&&)"),
                ("OP4", r"(&)"),
                ("OP3", r"(\|\|)"),
                ("OP2", r"(\|)"),
                ("NUM", r"([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)"),
                (
                    "COLOR",
                    r"(#[0123456789abcdefABCDEF]{6}|#[0123456789abcdefABCDEF]{3})",
                ),
                (
                    "TYPE",
                    r"(raster|image|cut|engrave|dots|unknown|command|cutcode|lasercode)",
                ),
                (
                    "VAL",
                    r"(speed|power|step|acceleration|passes|color|op|overscan|len)",
                ),
            ]
            filter_re = re.compile(
                "|".join("(?P<%s>%s)" % pair for pair in _filter_parse)
            )
            operator = list()
            operand = list()

            def filter_parser(text: str):
                pos = 0
                limit = len(text)
                while pos < limit:
                    match = filter_re.match(text, pos)
                    if match is None:
                        break  # No more matches.
                    kind = match.lastgroup
                    start = pos
                    pos = match.end()
                    if kind == "SKIP":
                        continue
                    value = match.group()
                    yield kind, value, start, pos

            def solve_to(order: int):
                try:
                    while len(operator) and operator[0][0] >= order:
                        _p, op = operator.pop()
                        v2 = operand.pop()
                        v1 = operand.pop()
                        try:
                            if op == "==" or op == "=":
                                operand.append(v1 == v2)
                            elif op == "!=":
                                operand.append(v1 != v2)
                            elif op == ">":
                                operand.append(v1 > v2)
                            elif op == "<":
                                operand.append(v1 < v2)
                            elif op == "<=":
                                operand.append(v1 <= v2)
                            elif op == ">=":
                                operand.append(v1 >= v2)
                            elif op == "&&" or op == "&":
                                operand.append(v1 and v2)
                            elif op == "||" or op == "|":
                                operand.append(v1 or v2)
                            elif op == "*":
                                operand.append(v1 * v2)
                            elif op == "/":
                                operand.append(v1 / v2)
                            elif op == "+":
                                operand.append(v1 + v2)
                            elif op == "-":
                                operand.append(v1 - v2)
                        except TypeError:
                            raise CommandSyntaxError("Cannot evaluate expression")
                        except ZeroDivisionError:
                            operand.append(float("inf"))
                except IndexError:
                    pass

            for e in data:
                for kind, value, start, pos in filter_parser(filter):
                    if kind == "COLOR":
                        operand.append(Color(value))
                    elif kind == "VAL":
                        if value == "step":
                            operand.append(e.raster_step)
                        elif value == "color":
                            operand.append(e.color)
                        elif value == "op":
                            operand.append(e.type.remove("op").strip())
                        elif value == "len":
                            operand.append(len(e.children))
                        else:
                            operand.append(e.settings.get(value))

                    elif kind == "NUM":
                        operand.append(float(value))
                    elif kind == "TYPE":
                        operand.append(value)
                    elif kind.startswith("OP"):
                        prec = int(kind[2:])
                        solve_to(prec)
                        operator.append((prec, value))
                solve_to(0)
                if len(operand) == 1:
                    if operand.pop():
                        subops.append(e)
                else:
                    raise CommandSyntaxError(_("Filter parse failed"))

            self.set_emphasis(subops)
            return "ops", subops

        @self.console_command(
            "list",
            help=_("Show information about the chained data"),
            input_type="ops",
            output_type="ops",
        )
        def operation_list(channel, _, data=None, **kwargs):
            channel("----------")
            channel(_("Operations:"))
            index_ops = list(self.ops())
            for op_obj in data:
                i = index_ops.index(op_obj)
                select_piece = "*" if op_obj.emphasized else " "
                name = "%s %d: %s" % (select_piece, i, str(op_obj))
                channel(name)
                if isinstance(op_obj, list):
                    for q, oe in enumerate(op_obj):
                        stroke_piece = (
                            "None"
                            if (not hasattr(oe, "stroke") or oe.stroke) is None
                            else oe.stroke.hex
                        )
                        fill_piece = (
                            "None"
                            if (not hasattr(oe, "stroke") or oe.fill) is None
                            else oe.fill.hex
                        )
                        ident_piece = str(oe.id)
                        name = "%s%d: %s-%s s:%s f:%s" % (
                            "".ljust(5),
                            q,
                            str(type(oe).__name__),
                            ident_piece,
                            stroke_piece,
                            fill_piece,
                        )
                        channel(name)
            channel("----------")

        @self.console_option("color", "c", type=Color)
        @self.console_option("default", "d", type=bool)
        @self.console_option("speed", "s", type=float)
        @self.console_option("power", "p", type=float)
        @self.console_option("step", "S", type=int)
        @self.console_option("overscan", "o", type=str)
        @self.console_option("passes", "x", type=int)
        @self.console_command(
            ("cut", "engrave", "raster", "imageop", "dots"),
            help=_(
                "<cut/engrave/raster/imageop/dots> - group the elements into this operation"
            ),
            input_type=(None, "elements"),
            output_type="ops",
        )
        def makeop(
            command,
            data=None,
            color=None,
            default=None,
            speed=None,
            power=None,
            step=None,
            overscan=None,
            passes=None,
            **kwargs,
        ):
            if command == "cut":
                op = CutOpNode()
            elif command == "engrave":
                op = EngraveOpNode()
            elif command == "raster":
                op = RasterOpNode()
            elif command == "imageop":
                op = ImageOpNode()
            elif command == "dots":
                op = DotsOpNode()
            else:
                return

            if color is not None:
                op.color = color
            if default is not None:
                op.default = default
            if speed is not None:
                op.speed = speed
            if power is not None:
                op.power = power
            if passes is not None:
                op.passes_custom = True
                op.passes = passes
            if step is not None:
                op.raster_step = step
            if overscan is not None:
                op.overscan = self.device.length(overscan, -1)
            self.add_op(op)
            if data is not None:
                for item in data:
                    op.add(item, type="ref elem")
            return "ops", [op]

        @self.console_argument("step_size", type=int, help=_("raster step size"))
        @self.console_command(
            "step", help=_("step <raster-step-size>"), input_type="ops"
        )
        def op_step(command, channel, _, data, step_size=None, **kwrgs):
            if step_size is None:
                found = False
                for op in data:
                    if op.type in ("op raster", "op image"):
                        step = op.raster_step
                        channel(_("Step for %s is currently: %d") % (str(op), step))
                        found = True
                if not found:
                    channel(_("No raster operations selected."))
                return
            for op in data:
                if op.type in ("op raster", "op image"):
                    op.raster_step = step_size
                    op.notify_update()
            return "ops", data

        @self.console_option(
            "difference",
            "d",
            type=bool,
            action="store_true",
            help=_("Change speed by this amount."),
        )
        @self.console_argument("speed", type=str, help=_("operation speed in mm/s"))
        @self.console_command(
            "speed", help=_("speed <speed>"), input_type="ops", output_type="ops"
        )
        def op_speed(
            command, channel, _, speed=None, difference=None, data=None, **kwrgs
        ):
            if speed is None:
                for op in data:
                    old_speed = op.speed
                    channel(_("Speed for '%s' is currently: %f") % (str(op), old_speed))
                return
            if speed.endswith("%"):
                speed = speed[:-1]
                percent = True
            else:
                percent = False

            try:
                new_speed = float(speed)
            except ValueError:
                channel(_("Not a valid speed or percent."))
                return

            for op in data:
                old_speed = op.speed
                if percent and difference:
                    s = old_speed + old_speed * (new_speed / 100.0)
                elif difference:
                    s = old_speed + new_speed
                elif percent:
                    s = old_speed * (new_speed / 100.0)
                else:
                    s = new_speed
                op.speed = s
                channel(
                    _("Speed for '%s' updated %f -> %f")
                    % (str(op), old_speed, new_speed)
                )
                op.notify_update()
            return "ops", data

        @self.console_argument(
            "power", type=int, help=_("power in pulses per inch (ppi, 1000=max)")
        )
        @self.console_command(
            "power", help=_("power <ppi>"), input_type="ops", output_type="ops"
        )
        def op_power(command, channel, _, power=None, data=None, **kwrgs):
            if power is None:
                for op in data:
                    old_ppi = op.power
                    channel(_("Power for '%s' is currently: %d") % (str(op), old_ppi))
                return
            for op in data:
                old_ppi = op.power
                op.power = power
                channel(
                    _("Power for '%s' updated %d -> %d") % (str(op), old_ppi, power)
                )
                op.notify_update()
            return "ops", data

        @self.console_argument("passes", type=int, help=_("Set operation passes"))
        @self.console_command(
            "passes", help=_("passes <passes>"), input_type="ops", output_type="ops"
        )
        def op_passes(command, channel, _, passes=None, data=None, **kwrgs):
            if passes is None:
                for op in data:
                    old_passes = op.passes
                    channel(
                        _("Passes for '%s' is currently: %d") % (str(op), old_passes)
                    )
                return
            for op in data:
                old_passes = op.passes
                op.passes = passes
                if passes >= 1:
                    op.passes_custom = True
                channel(
                    _("Passes for '%s' updated %d -> %d")
                    % (str(op), old_passes, passes)
                )
                op.notify_update()
            return "ops", data

        @self.console_command(
            "disable",
            help=_("Disable the given operations"),
            input_type="ops",
            output_type="ops",
        )
        def op_disable(command, channel, _, data=None, **kwrgs):
            for op in data:
                op.output = False
                channel(_("Operation '%s' disabled.") % str(op))
                op.notify_update()
            return "ops", data

        @self.console_command(
            "enable",
            help=_("Enable the given operations"),
            input_type="ops",
            output_type="ops",
        )
        def op_enable(command, channel, _, data=None, **kwrgs):
            for op in data:
                op.output = True
                channel(_("Operation '%s' enabled.") % str(op))
                op.notify_update()
            return "ops", data

        # ==========
        # ELEMENT/OPERATION SUBCOMMANDS
        # ==========
        @self.console_command(
            "copy",
            help=_("Duplicate elements"),
            input_type=("elements", "ops"),
            output_type=("elements", "ops"),
        )
        def e_copy(data=None, data_type=None, **kwargs):
            add_elem = list(map(copy, data))
            if data_type == "ops":
                self.add_ops(add_elem)
            else:
                self.add_elems(add_elem)
            return data_type, add_elem

        @self.console_command(
            "delete", help=_("Delete elements"), input_type=("elements", "ops")
        )
        def e_delete(command, channel, _, data=None, data_type=None, **kwargs):
            channel(_("Deleting…"))
            if data_type == "elements":
                self.remove_elements(data)
            else:
                self.remove_operations(data)
            self.signal("tree_changed")

        # ==========
        # ELEMENT BASE
        # ==========

        @self.console_command(
            "elements",
            help=_("Show information about elements"),
        )
        def element(**kwargs):
            self(".element* list\n")

        @self.console_command(
            "element*",
            help=_("element*, all elements"),
            output_type="elements",
        )
        def element_star(**kwargs):
            return "elements", list(self.elems())

        @self.console_command(
            "element~",
            help=_("element~, all non-selected elements"),
            output_type="elements",
        )
        def element_not(**kwargs):
            return "elements", list(self.elems(emphasized=False))

        @self.console_command(
            "element",
            help=_("element, selected elements"),
            output_type="elements",
        )
        def element_base(**kwargs):
            return "elements", list(self.elems(emphasized=True))

        @self.console_command(
            r"element([0-9]+,?)+",
            help=_("element0,3,4,5: chain a list of specific elements"),
            regex=True,
            output_type="elements",
        )
        def element_chain(command, channel, _, **kwargs):
            arg = command[7:]
            elements_list = []
            for value in arg.split(","):
                try:
                    value = int(value)
                except ValueError:
                    continue
                try:
                    e = self.get_elem(value)
                    elements_list.append(e)
                except IndexError:
                    channel(_("index %d out of range") % value)
            return "elements", elements_list

        # ==========
        # ELEMENT SUBCOMMANDS
        # ==========

        @self.console_argument("step_size", type=int, help=_("element step size"))
        @self.console_command(
            "step",
            help=_("step <element step-size>"),
            input_type="elements",
            output_type="elements",
        )
        def step_command(command, channel, _, data, step_size=None, **kwrgs):
            if step_size is None:
                found = False
                for element in data:
                    if isinstance(element, SVGImage):
                        try:
                            step = element.values["raster_step"]
                        except KeyError:
                            step = 1
                        channel(
                            _("Image step for %s is currently: %s")
                            % (str(element), step)
                        )
                        found = True
                if not found:
                    channel(_("No image element selected."))
                return
            for element in data:
                element.values["raster_step"] = str(step_size)
                m = element.transform
                tx = m.e
                ty = m.f
                element.transform = Matrix.scale(float(step_size), float(step_size))
                element.transform.post_translate(tx, ty)
                if hasattr(element, "node"):
                    element.node.modified()
                self.signal("element_property_reload", element)
            return ("elements",)

        @self.console_command(
            "select",
            help=_("Set these values as the selection."),
            input_type="elements",
            output_type="elements",
        )
        def element_select_base(data=None, **kwargs):
            self.set_emphasis(data)
            return "elements", data

        @self.console_command(
            "select+",
            help=_("Add the input to the selection"),
            input_type="elements",
            output_type="elements",
        )
        def element_select_plus(data=None, **kwargs):
            elems = list(self.elems(emphasized=True))
            elems.extend(data)
            self.set_emphasis(elems)
            return "elements", elems

        @self.console_command(
            "select-",
            help=_("Remove the input data from the selection"),
            input_type="elements",
            output_type="elements",
        )
        def element_select_minus(data=None, **kwargs):
            elems = list(self.elems(emphasized=True))
            for e in data:
                try:
                    elems.remove(e)
                except ValueError:
                    pass
            self.set_emphasis(elems)
            return "elements", elems

        @self.console_command(
            "select^",
            help=_("Toggle the input data in the selection"),
            input_type="elements",
            output_type="elements",
        )
        def element_select_xor(data=None, **kwargs):
            elems = list(self.elems(emphasized=True))
            for e in data:
                try:
                    elems.remove(e)
                except ValueError:
                    elems.append(e)
            self.set_emphasis(elems)
            return "elements", elems

        @self.console_command(
            "list",
            help=_("Show information about the chained data"),
            input_type="elements",
            output_type="elements",
        )
        def element_list(command, channel, _, data=None, **kwargs):
            channel("----------")
            channel(_("Graphical Elements:"))
            index_list = list(self.elems())
            for e in data:
                i = index_list.index(e)
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                if e.node.emphasized:
                    channel("%d: * %s" % (i, name))
                else:
                    channel("%d: %s" % (i, name))
            channel("----------")
            return "elements", data

        @self.console_argument("start", type=int, help=_("elements start"))
        @self.console_argument("end", type=int, help=_("elements end"))
        @self.console_argument("step", type=int, help=_("elements step"))
        @self.console_command(
            "range",
            help=_("Subset selection by begin & end indices and step"),
            input_type="elements",
            output_type="elements",
        )
        def element_select_range(data=None, start=None, end=None, step=1, **kwargs):
            subelem = list()
            for e in range(start, end, step):
                try:
                    subelem.append(data[e])
                except IndexError:
                    pass
            self.set_emphasis(subelem)
            return "elements", subelem

        @self.console_command(
            "merge",
            help=_("merge elements"),
            input_type="elements",
            output_type="elements",
        )
        def element_merge(data=None, **kwargs):
            super_element = Path()
            for e in data:
                if not isinstance(e, Shape):
                    continue
                if super_element.stroke is None:
                    super_element.stroke = e.stroke
                if super_element.fill is None:
                    super_element.fill = e.fill
                super_element += abs(e)
            self.remove_elements(data)
            self.add_elem(super_element).emphasized = True
            self.classify([super_element])
            return "elements", [super_element]

        @self.console_command(
            "subpath",
            help=_("break elements"),
            input_type="elements",
            output_type="elements",
        )
        def element_subpath(data=None, **kwargs):
            if not isinstance(data, list):
                data = list(data)
            elements_nodes = []
            elements = []
            for e in data:
                node = e.node
                group_node = node.replace_node(type="group", label=node.label)
                if isinstance(e, Shape) and not isinstance(e, Path):
                    e = Path(e)
                elif isinstance(e, SVGText):
                    continue
                p = abs(e)
                for subpath in p.as_subpaths():
                    subelement = Path(subpath)
                    elements.append(subelement)
                    group_node.add(subelement, type="elem")
                elements_nodes.append(group_node)
                self.classify(elements)
            return "elements", elements_nodes

        # ==========
        # ALIGN SUBTYPE
        # Align consist of top level node objects that can be manipulated within the scene.
        # ==========

        @self.console_command(
            "align",
            help=_("align selected elements"),
            input_type=("elements", None),
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, remainder=None, **kwargs):
            if not remainder:
                channel(
                    "top\nbottom\nleft\nright\ncenter\ncenterh\ncenterv\nspaceh\nspacev\n"
                    "<any valid svg:Preserve Aspect Ratio, eg xminymin>"
                )
                return
            if data is None:
                data = list(self.elems(emphasized=True))

            # Element conversion.
            d = list()
            elem_branch = self.elem_branch
            for elem in data:
                node = elem.node
                while node.parent and node.parent is not elem_branch:
                    node = node.parent
                if node not in d:
                    d.append(node)
            data = d
            return "align", data

        @self.console_command(
            "top",
            help=_("align elements at top"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            top_edge = min([e[1] for e in boundary_points])
            for node in data:
                subbox = node.bounds
                top = subbox[1] - top_edge
                matrix = "translate(0, %f)" % -top
                if top != 0:
                    for q in node.flat(types="elem"):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
            return "align", data

        @self.console_command(
            "bottom",
            help=_("align elements at bottom"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            bottom_edge = max([e[3] for e in boundary_points])
            for node in data:
                subbox = node.bounds
                bottom = subbox[3] - bottom_edge
                matrix = "translate(0, %f)" % -bottom
                if bottom != 0:
                    for q in node.flat(types="elem"):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
            return "align", data

        @self.console_command(
            "left",
            help=_("align elements at left"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            left_edge = min([e[0] for e in boundary_points])
            for node in data:
                subbox = node.bounds
                left = subbox[0] - left_edge
                matrix = "translate(%f, 0)" % -left
                if left != 0:
                    for q in node.flat(types="elem"):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
            return "align", data

        @self.console_command(
            "right",
            help=_("align elements at right"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            right_edge = max([e[2] for e in boundary_points])
            for node in data:
                subbox = node.bounds
                right = subbox[2] - right_edge
                matrix = "translate(%f, 0)" % -right
                if right != 0:
                    for q in node.flat(types="elem"):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
            return "align", data

        @self.console_command(
            "center",
            help=_("align elements at center"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            left_edge = min([e[0] for e in boundary_points])
            top_edge = min([e[1] for e in boundary_points])
            right_edge = max([e[2] for e in boundary_points])
            bottom_edge = max([e[3] for e in boundary_points])
            for node in data:
                subbox = node.bounds
                dx = (subbox[0] + subbox[2] - left_edge - right_edge) / 2.0
                dy = (subbox[1] + subbox[3] - top_edge - bottom_edge) / 2.0
                matrix = "translate(%f, %f)" % (-dx, -dy)
                for q in node.flat(types="elem"):
                    obj = q.object
                    if obj is not None:
                        obj *= matrix
                    q.modified()
            return "align", data

        @self.console_command(
            "centerv",
            help=_("align elements at center vertical"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            left_edge = min([e[0] for e in boundary_points])
            right_edge = max([e[2] for e in boundary_points])
            for node in data:
                subbox = node.bounds
                dx = (subbox[0] + subbox[2] - left_edge - right_edge) / 2.0
                matrix = "translate(%f, 0)" % -dx
                for q in node.flat(types="elem"):
                    obj = q.object
                    if obj is not None:
                        obj *= matrix
                    q.modified()
            return "align", data

        @self.console_command(
            "centerh",
            help=_("align elements at center horizontal"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            top_edge = min([e[1] for e in boundary_points])
            bottom_edge = max([e[3] for e in boundary_points])
            for node in data:
                subbox = node.bounds
                dy = (subbox[1] + subbox[3] - top_edge - bottom_edge) / 2.0
                matrix = "translate(0, %f)" % -dy
                for q in node.flat(types="elem"):
                    obj = q.object
                    if obj is not None:
                        obj *= matrix
                    q.modified()
            return "align", data

        @self.console_command(
            "spaceh",
            help=_("align elements across horizontal space"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            if len(data) <= 2:  # Cannot distribute 2 or fewer items.
                return "align", data
            left_edge = min([e[0] for e in boundary_points])
            right_edge = max([e[2] for e in boundary_points])
            dim_total = right_edge - left_edge
            dim_available = dim_total
            for node in data:
                bounds = node.bounds
                dim_available -= bounds[2] - bounds[0]
            distributed_distance = dim_available / (len(data) - 1)
            data.sort(key=lambda n: n.bounds[0])  # sort by left edge
            dim_pos = left_edge
            for node in data:
                subbox = node.bounds
                delta = subbox[0] - dim_pos
                matrix = "translate(%f, 0)" % -delta
                if delta != 0:
                    for q in node.flat(types="elem"):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
                dim_pos += subbox[2] - subbox[0] + distributed_distance
            return "align", data

        @self.console_command(
            "spacev",
            help=_("align elements down vertical space"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            if len(data) <= 2:  # Cannot distribute 2 or fewer items.
                return "align", data
            top_edge = min([e[1] for e in boundary_points])
            bottom_edge = max([e[3] for e in boundary_points])
            dim_total = bottom_edge - top_edge
            dim_available = dim_total
            for node in data:
                bounds = node.bounds
                dim_available -= bounds[3] - bounds[1]
            distributed_distance = dim_available / (len(data) - 1)
            data.sort(key=lambda n: n.bounds[1])  # sort by top edge
            dim_pos = top_edge
            for node in data:
                subbox = node.bounds
                delta = subbox[1] - dim_pos
                matrix = "translate(0, %f)" % -delta
                if delta != 0:
                    for q in node.flat(types="elem"):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
                dim_pos += subbox[3] - subbox[1] + distributed_distance
            return "align", data

        @self.console_command(
            "bedcenter",
            help=_("align elements to bedcenter"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(command, channel, _, data=None, **kwargs):
            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            left_edge = min([e[0] for e in boundary_points])
            top_edge = min([e[1] for e in boundary_points])
            right_edge = max([e[2] for e in boundary_points])
            bottom_edge = max([e[3] for e in boundary_points])
            for node in data:
                device_width = self.device.width
                device_height = self.device.height
                dx = (device_width - left_edge - right_edge) / 2.0
                dy = (device_height - top_edge - bottom_edge) / 2.0
                matrix = "translate(%f, %f)" % (dx, dy)
                for q in node.flat(types="elem"):
                    obj = q.object
                    if obj is not None:
                        obj *= matrix
                    q.modified()
            self.signal("tree_changed")
            return "align", data

        @self.console_argument(
            "preserve_aspect_ratio",
            type=str,
            default="none",
            help="preserve aspect ratio value",
        )
        @self.console_command(
            "view",
            help=_("align elements within viewbox"),
            input_type="align",
            output_type="align",
        )
        def subtype_align(
            command, channel, _, data=None, preserve_aspect_ratio="none", **kwargs
        ):
            """
            Align the elements to within the bed according to SVG Viewbox rules. The following aspect ratios
            are valid. These should define all the valid methods of centering data within the laser bed.
            "xminymin",
            "xmidymin",
            "xmaxymin",
            "xminymid",
            "xmidymid",
            "xmaxymid",
            "xminymax",
            "xmidymax",
            "xmaxymax",
            "xminymin meet",
            "xmidymin meet",
            "xmaxymin meet",
            "xminymid meet",
            "xmidymid meet",
            "xmaxymid meet",
            "xminymax meet",
            "xmidymax meet",
            "xmaxymax meet",
            "xminymin slice",
            "xmidymin slice",
            "xmaxymin slice",
            "xminymid slice",
            "xmidymid slice",
            "xmaxymid slice",
            "xminymax slice",
            "xmidymax slice",
            "xmaxymax slice",
            "none"
            """

            boundary_points = []
            for node in data:
                boundary_points.append(node.bounds)
            if not len(boundary_points):
                return
            left_edge = min([e[0] for e in boundary_points])
            top_edge = min([e[1] for e in boundary_points])
            right_edge = max([e[2] for e in boundary_points])
            bottom_edge = max([e[3] for e in boundary_points])

            if preserve_aspect_ratio in (
                "xminymin",
                "xmidymin",
                "xmaxymin",
                "xminymid",
                "xmidymid",
                "xmaxymid",
                "xminymax",
                "xmidymax",
                "xmaxymax",
                "xminymin meet",
                "xmidymin meet",
                "xmaxymin meet",
                "xminymid meet",
                "xmidymid meet",
                "xmaxymid meet",
                "xminymax meet",
                "xmidymax meet",
                "xmaxymax meet",
                "xminymin slice",
                "xmidymin slice",
                "xmaxymin slice",
                "xminymid slice",
                "xmidymid slice",
                "xmaxymid slice",
                "xminymax slice",
                "xmidymax slice",
                "xmaxymax slice",
                "none",
            ):
                for node in data:
                    device_width = self.device.width
                    device_height = self.device.height

                    matrix = Viewbox.viewbox_transform(
                        0,
                        0,
                        device_width,
                        device_height,
                        left_edge,
                        top_edge,
                        right_edge - left_edge,
                        bottom_edge - top_edge,
                        preserve_aspect_ratio,
                    )
                    for q in node.flat(types="elem"):
                        obj = q.object
                        if obj is not None:
                            obj *= matrix
                        q.modified()
                    for q in node.flat(types=("file", "group")):
                        q.modified()
            return "align", data

        @self.console_argument("c", type=int, help=_("Number of columns"))
        @self.console_argument("r", type=int, help=_("Number of rows"))
        @self.console_argument("x", type=Length, help=_("x distance"))
        @self.console_argument("y", type=Length, help=_("y distance"))
        @self.console_option(
            "origin",
            "o",
            type=int,
            nargs=2,
            help=_("Position of original in matrix (e.g '2,2' or '4,3')"),
        )
        @self.console_command(
            "grid",
            help=_("grid <columns> <rows> <x_distance> <y_distance> <origin>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_grid(
            command,
            channel,
            _,
            c: int,
            r: int,
            x: Length,
            y: Length,
            origin=None,
            data=None,
            **kwargs,
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0 and self._emphasized_bounds is None:
                channel(_("No item selected."))
                return
            if r is None:
                raise CommandSyntaxError
            if x is None:
                x = "100%"
            if y is None:
                y = "100%"
            try:
                bounds = self._emphasized_bounds
                width = bounds[2] - bounds[0]
                height = bounds[3] - bounds[1]
            except Exception:
                raise CommandSyntaxError
            x = self.device.length(x, 0, relative_length=width)
            y = self.device.length(y, 1, relative_length=height)
            # TODO: Check lengths do not accept gibberish.
            y_pos = 0
            if origin is None:
                origin = (1, 1)
            cx, cy = origin
            data_out = list(data)
            if cx is None:
                cx = 1
            if cy is None:
                cy = 1
            # Tell whether original is at the left / middle / or right
            start_x = -1 * x * (cx - 1)
            start_y = -1 * y * (cy - 1)
            y_pos = start_y
            for j in range(r):
                x_pos = start_x
                for k in range(c):
                    if j != (cy - 1) or k != (cx - 1):
                        add_elem = list(map(copy, data))
                        for e in add_elem:
                            e *= "translate(%f, %f)" % (x_pos, y_pos)
                        self.add_elems(add_elem)
                        data_out.extend(add_elem)
                    x_pos += x
                y_pos += y

            self.signal("refresh_scene")
            return "elements", data_out

        @self.console_argument("repeats", type=int, help=_("Number of repeats"))
        @self.console_argument("radius", type=Length, help=_("Radius"))
        @self.console_argument("startangle", type=Angle.parse, help=_("Start-Angle"))
        @self.console_argument("endangle", type=Angle.parse, help=_("End-Angle"))
        @self.console_option(
            "rotate",
            "r",
            type=bool,
            action="store_true",
            help=_("Rotate copies towards center?"),
        )
        @self.console_option(
            "deltaangle",
            "d",
            type=Angle.parse,
            help=_("Delta-Angle (if omitted will take (end-start)/repeats )"),
        )
        @self.console_command(
            "radial",
            help=_("radial <repeats> <radius> <startangle> <endangle> <rotate>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_radial(
            command,
            channel,
            _,
            repeats: int,
            radius=None,
            startangle=None,
            endangle=None,
            rotate=None,
            deltaangle=None,
            data=None,
            **kwargs,
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0 and self._emphasized_bounds is None:
                channel(_("No item selected."))
                return

            if repeats is None:
                raise CommandSyntaxError
            if repeats <= 1:
                raise CommandSyntaxError(_("repeats should be greater or equal to 2"))
            if radius is None:
                radius = Length(0)
            else:
                if not radius.is_valid_length:
                    raise CommandSyntaxError("radius: " + _("This is not a valid length"))
            if startangle is None:
                startangle = Angle.parse("0deg")
            if endangle is None:
                endangle = Angle.parse("360deg")
            if rotate is None:
                rotate = False

            # print ("Segment to cover: %f - %f" % (startangle.as_degrees, endangle.as_degrees))
            bounds = Group.union_bbox(data, with_stroke=True)
            if bounds is None:
                return
            width = bounds[2] - bounds[0]
            radius = radius.value(ppi=1000, relative_length=width)
            if isinstance(radius, Length):
                raise CommandSyntaxError

            data_out = list(data)
            if deltaangle is None:
                segment_len = (endangle.as_radians - startangle.as_radians) / repeats
            else:
                segment_len = deltaangle.as_radians
            # Notabene: we are following the cartesian system here, but as the Y-Axis is top screen to bottom screen,
            # the perceived angle travel is CCW (which is counter-intuitive)
            currentangle = startangle.as_radians
            # bounds = self._emphasized_bounds
            center_x = (bounds[2] + bounds[0]) / 2.0 - radius
            center_y = (bounds[3] + bounds[1]) / 2.0

            # print ("repeats: %d, Radius: %.1f" % (repeats, radius))
            # print ("Center: %.1f, %.1f" % (center_x, center_y))
            # print ("Startangle, Endangle, segment_len: %.1f, %.1f, %.1f" % (180 * startangle.as_radians / pi, 180 * endangle.as_radians / pi, 180 * segment_len / pi))

            currentangle = segment_len
            for cc in range(1, repeats):
                # print ("Angle: %f rad = %f deg" % (currentangle, currentangle/pi * 180))
                add_elem = list(map(copy, data))
                for e in add_elem:
                    if rotate:
                        x_pos = -1 * radius
                        y_pos = 0
                        # e *= "translate(%f, %f)" % (x_pos, y_pos)
                        e *= "rotate(%frad, %f, %f)" % (
                            currentangle,
                            center_x,
                            center_y,
                        )
                    else:
                        x_pos = -1 * radius + radius * cos(currentangle)
                        y_pos = radius * sin(currentangle)
                        e *= "translate(%f, %f)" % (x_pos, y_pos)

                self.add_elems(add_elem)
                data_out.extend(add_elem)

                currentangle += segment_len

            self.signal("refresh_scene")
            return "elements", data_out

        @self.console_argument("copies", type=int, help=_("Number of copies"))
        @self.console_argument("radius", type=Length, help=_("Radius"))
        @self.console_argument("startangle", type=Angle.parse, help=_("Start-Angle"))
        @self.console_argument("endangle", type=Angle.parse, help=_("End-Angle"))
        @self.console_option(
            "rotate",
            "r",
            type=bool,
            action="store_true",
            help=_("Rotate copies towards center?"),
        )
        @self.console_option(
            "deltaangle",
            "d",
            type=Angle.parse,
            help=_("Delta-Angle (if omitted will take (end-start)/copies )"),
        )
        @self.console_command(
            "circ_copy",
            help=_("circ_copy <copies> <radius> <startangle> <endangle> <rotate>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_circularcopies(
            command,
            channel,
            _,
            copies: int,
            radius=None,
            startangle=None,
            endangle=None,
            rotate=None,
            deltaangle=None,
            data=None,
            **kwargs,
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0 and self._emphasized_bounds is None:
                channel(_("No item selected."))
                return

            if copies is None:
                raise CommandSyntaxError
            if copies <= 0:
                copies = 1
            if radius is None:
                radius = Length(0)
            else:
                if not radius.is_valid_length:
                    raise CommandSyntaxError("radius: " + _("This is not a valid length"))
            if startangle is None:
                startangle = Angle.parse("0deg")
            if endangle is None:
                endangle = Angle.parse("360deg")
            if rotate is None:
                rotate = False

            # print ("Segment to cover: %f - %f" % (startangle.as_degrees, endangle.as_degrees))
            bounds = Group.union_bbox(data, with_stroke=True)
            if bounds is None:
                return
            width = bounds[2] - bounds[0]
            radius = radius.value(ppi=1000, relative_length=width)
            if isinstance(radius, Length):
                raise CommandSyntaxError

            data_out = list(data)
            if deltaangle is None:
                segment_len = (endangle.as_radians - startangle.as_radians) / copies
            else:
                segment_len = deltaangle.as_radians
            # Notabene: we are following the cartesian system here, but as the Y-Axis is top screen to bottom screen,
            # the perceived angle travel is CCW (which is counter-intuitive)
            currentangle = startangle.as_radians
            # bounds = self._emphasized_bounds
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            for cc in range(copies):
                # print ("Angle: %f rad = %f deg" % (currentangle, currentangle/pi * 180))
                add_elem = list(map(copy, data))
                for e in add_elem:
                    if rotate:
                        x_pos = radius
                        y_pos = 0
                        e *= "translate(%f, %f)" % (x_pos, y_pos)
                        e *= "rotate(%frad, %f, %f)" % (
                            currentangle,
                            center_x,
                            center_y,
                        )
                    else:
                        x_pos = radius * cos(currentangle)
                        y_pos = radius * sin(currentangle)
                        e *= "translate(%f, %f)" % (x_pos, y_pos)

                self.add_elems(add_elem)
                data_out.extend(add_elem)
                currentangle += segment_len

            self.signal("refresh_scene")
            return "elements", data_out

        @self.console_argument(
            "corners", type=int, help=_("Number of corners/vertices")
        )
        @self.console_argument("cx", type=Length, help=_("X-Value of polygon's center"))
        @self.console_argument("cy", type=Length, help=_("Y-Value of polygon's center"))
        @self.console_argument(
            "radius",
            type=Length,
            help=_("Radius (length of side if --side_length is used)"),
        )
        @self.console_option("startangle", "s", type=Angle.parse, help=_("Start-Angle"))
        @self.console_option(
            "inscribed",
            "i",
            type=bool,
            action="store_true",
            help=_("Shall the polygon touch the inscribing circle?"),
        )
        @self.console_option(
            "side_length",
            "l",
            type=bool,
            action="store_true",
            help=_(
                "Do you want to treat the length value for radius as the length of one edge instead?"
            ),
        )
        @self.console_option(
            "radius_inner",
            "r",
            type=Length,
            help=_("Alternating radius for every other vertex"),
        )
        @self.console_option(
            "alternate_seq",
            "a",
            type=int,
            help=_(
                "Length of alternating sequence (1 for starlike figures, >=2 for more gear-like patterns)"
            ),
        )
        @self.console_option(
            "density", "d", type=int, help=_("Amount of vertices to skip")
        )
        @self.console_command(
            "shape",
            help=_(
                "shape <corners> <x> <y> <r> <startangle> <inscribed> or shape <corners> <r>"
            ),
            input_type=("elements", None),
            output_type="elements",
        )
        def element_shape(
            command,
            channel,
            _,
            corners,
            cx,
            cy,
            radius,
            startangle=None,
            inscribed=None,
            side_length=None,
            radius_inner=None,
            alternate_seq=None,
            density=None,
            data=None,
            **kwargs,
        ):
            if corners is None:
                raise CommandSyntaxError
            if corners <= 2:
                if cx is None:
                    cx = Length(0)
                elif not cx.is_valid_length:
                    raise CommandSyntaxError("cx: " + _("This is not a valid length"))
                if cy is None:
                    cy = Length(0)
                elif not cy.is_valid_length:
                    raise CommandSyntaxError("cy: " + _("This is not a valid length"))
                cx = cx.value(ppi=1000, relative_length=bed_dim.bed_width * MILS_IN_MM)
                cy = cy.value(ppi=1000, relative_length=bed_dim.bed_width * MILS_IN_MM)
                if radius is None:
                    radius = Length(0)
                radius = radius.value(
                    ppi=1000, relative_length=bed_dim.bed_width * MILS_IN_MM
                )
                # No need to look at side_length parameter as we are considering the radius value as an edge anyway...
                if startangle is None:
                    startangle = Angle.parse("0deg")

                starpts = [(cx, cy)]
                if corners == 2:
                    starpts += [
                        (
                            cx + cos(startangle.as_radians) * radius,
                            cy + sin(startangle.as_radians) * radius,
                        )
                    ]

            else:
                if cx is None:
                    raise CommandSyntaxError(
                        _(
                            "Please provide at least one additional value (which will act as radius then)"
                        )
                    )
                else:
                    if not cx.is_valid_length:
                        raise CommandSyntaxError("cx: " + _("This is not a valid length"))

                if cy is None:
                    cy = Length(0)
                else:
                    if not cy.is_valid_length:
                        raise CommandSyntaxError("cy: " + _("This is not a valid length"))
                # do we have something like 'polyshape 3 4cm' ? If yes, reassign the parameters
                if radius is None:
                    radius = cx
                    cx = Length(0)
                    cy = Length(0)
                else:
                    if not radius.is_valid_length:
                        raise CommandSyntaxError("radius: " + _("This is not a valid length"))

                cx = cx.value(ppi=1000, relative_length=bed_dim.bed_width * MILS_IN_MM)
                cy = cy.value(ppi=1000, relative_length=bed_dim.bed_width * MILS_IN_MM)
                radius = radius.value(
                    ppi=1000, relative_length=bed_dim.bed_width * MILS_IN_MM
                )

                if (
                    isinstance(radius, Length)
                    or isinstance(cx, Length)
                    or isinstance(cy, Length)
                ):
                    raise CommandSyntaxError

                if startangle is None:
                    startangle = Angle.parse("0deg")

                if alternate_seq is None:
                    if radius_inner is None:
                        alternate_seq = 0
                    else:
                        alternate_seq = 1

                if density is None:
                    density = 1
                if density < 1 or density > corners:
                    density = 1

                # Do we have to consider the radius value as the length of one corner?
                if not side_length is None:
                    # Let's recalculate the radius then...
                    # d_oc = s * csc( pi / n)
                    radius = 0.5 * radius / sin(pi / corners)

                if radius_inner is None:
                    radius_inner = radius
                else:
                    radius_inner = radius_inner.value(ppi=1000, relative_length=radius)
                    if not radius_inner.is_valid_length:
                        raise CommandSyntaxError(
                            "radius_inner: " + _("This is not a valid length")
                        )
                    if isinstance(radius_inner, Length):
                        radius_inner = radius

                if inscribed:
                    if side_length is None:
                        radius = radius / cos(pi / corners)
                    else:
                        channel(
                            _(
                                "You have as well provided the --side_length parameter, this takes precedence, so --inscribed is ignored"
                            )
                        )

                if alternate_seq < 1:
                    radius_inner = radius

                # print("These are your parameters:")
                # print("Vertices: %d, Center: X=%.2f Y=%.2f" % (corners, cx, cy))
                # print("Radius: Outer=%.2f Inner=%.2f" % (radius, radius_inner))
                # print("Inscribe: %s" % inscribed)
                # print(
                #    "Startangle: %.2f, Alternate-Seq: %d"
                #    % (startangle.as_degrees, alternate_seq)
                # )

                pts = []
                myangle = startangle.as_radians
                deltaangle = tau / corners
                ct = 0
                for j in range(corners):
                    if ct < alternate_seq:
                        # print("Outer: Ct=%d, Radius=%.2f, Angle=%.2f" % (ct, radius, 180 * myangle / pi) )
                        thisx = cx + radius * cos(myangle)
                        thisy = cy + radius * sin(myangle)
                    else:
                        # print("Inner: Ct=%d, Radius=%.2f, Angle=%.2f" % (ct, radius_inner, 180 * myangle / pi) )
                        thisx = cx + radius_inner * cos(myangle)
                        thisy = cy + radius_inner * sin(myangle)
                    ct += 1
                    if ct >= 2 * alternate_seq:
                        ct = 0
                    if j == 0:
                        firstx = thisx
                        firsty = thisy
                    myangle += deltaangle
                    pts += [(thisx, thisy)]
                # Close the path
                pts += [(firstx, firsty)]

                starpts = [(pts[0][0], pts[0][1])]
                idx = density
                while idx != 0:
                    starpts += [(pts[idx][0], pts[idx][1])]
                    idx += density
                    if idx >= corners:
                        idx -= corners
                if len(starpts) < corners:
                    ct = 0
                    possible_combinations = ""
                    for i in range(corners - 1):
                        j = i + 2
                        if gcd(j, corners) == 1:
                            if ct % 3 == 0:
                                possible_combinations += "\n shape %d ... -d %d" % (
                                    corners,
                                    j,
                                )
                            else:
                                possible_combinations += ", shape %d ... -d %d " % (
                                    corners,
                                    j,
                                )
                            ct += 1
                    channel(
                        _("Just for info: we have missed %d vertices...")
                        % (corners - len(starpts))
                    )
                    channel(
                        _("To hit all, the density parameters should be e.g. %s")
                        % possible_combinations
                    )

            poly_path = Polygon(starpts)
            self.add_element(poly_path)
            if data is None:
                return "elements", [poly_path]
            else:
                data.append(poly_path)
                return "elements", data

        @self.console_option("step", "s", default=2.0, type=float)
        @self.console_command(
            "render",
            help=_("Convert given elements to a raster image"),
            input_type=(None, "elements"),
            output_type="image",
        )
        def make_raster_image(command, channel, _, step=2.0, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            reverse = self.classify_reverse
            if reverse:
                data = list(reversed(data))
            make_raster = self.lookup("render-op/make_raster")
            if not make_raster:
                channel(_("No renderer is registered to perform render."))
                return
            bounds = Group.union_bbox(data, with_stroke=True)
            if bounds is None:
                return
            if step <= 0:
                step = 1
            xmin, ymin, xmax, ymax = bounds

            image = make_raster(
                [n.node for n in data],
                bounds,
                step=step,
            )
            image_element = SVGImage(image=image)
            image_element.transform.post_scale(step, step)
            image_element.transform.post_translate(xmin, ymin)
            image_element.values["raster_step"] = step
            self.add_elem(image_element)
            return "image", [image_element]

        # ==========
        # ELEMENT/SHAPE COMMANDS
        # ==========
        @self.console_argument("x_pos", type=str)
        @self.console_argument("y_pos", type=str)
        @self.console_argument("r_pos", type=str)
        @self.console_command(
            "circle",
            help=_("circle <x> <y> <r> or circle <r>"),
            input_type=("elements", None),
            output_type="elements",
        )
        def element_circle(x_pos, y_pos, r_pos, data=None, **kwargs):
            if x_pos is None:
                raise CommandSyntaxError
            else:
                if r_pos is None:
                    r_pos = x_pos
                    x_pos = 0
                    y_pos = 0

            x_pos = self.device.length(x_pos, 0)
            y_pos = self.device.length(y_pos, 1)
            r_pos = self.device.length(r_pos, -1)
            circ = Circle(cx=x_pos, cy=y_pos, r=r_pos)
            self.add_element(circ)
            if data is None:
                return "elements", [circ]
            else:
                data.append(circ)
                return "elements", data

        @self.console_argument("x_pos", type=str)
        @self.console_argument("y_pos", type=str)
        @self.console_argument("rx_pos", type=str)
        @self.console_argument("ry_pos", type=str)
        @self.console_command(
            "ellipse",
            help=_("ellipse <cx> <cy> <rx> <ry>"),
            input_type=("elements", None),
            output_type="elements",
        )
        def element_ellipse(x_pos, y_pos, rx_pos, ry_pos, data=None, **kwargs):
            if ry_pos is None:
                raise CommandSyntaxError
            x_pos = self.device.length(x_pos, 0)
            y_pos = self.device.length(y_pos, 1)
            rx_pos = self.device.length(rx_pos, 0)
            ry_pos = self.device.length(ry_pos, 1)
            ellip = Ellipse(cx=x_pos, cy=y_pos, rx=rx_pos, ry=ry_pos)
            self.add_element(ellip)
            if data is None:
                return "elements", [ellip]
            else:
                data.append(ellip)
                return "elements", data

        @self.console_argument(
            "x_pos", type=str, help=_("x position for top left corner of rectangle.")
        )
        @self.console_argument(
            "y_pos", type=str, help=_("y position for top left corner of rectangle.")
        )
        @self.console_argument("width", type=str, help=_("width of the rectangle."))
        @self.console_argument("height", type=str, help=_("height of the rectangle."))
        @self.console_option("rx", "x", type=str, help=_("rounded rx corner value."))
        @self.console_option("ry", "y", type=str, help=_("rounded ry corner value."))
        @self.console_command(
            "rect",
            help=_("adds rectangle to scene"),
            input_type=("elements", None),
            output_type="elements",
        )
        def element_rect(
            x_pos, y_pos, width, height, rx=None, ry=None, data=None, **kwargs
        ):
            """
            Draws an svg rectangle with optional rounded corners.
            """
            if x_pos is None:
                raise CommandSyntaxError
            x_pos = self.device.length(x_pos, 0)
            y_pos = self.device.length(y_pos, 1)
            rx_pos = self.device.length(rx, 0)
            ry_pos = self.device.length(ry, 1)
            width = self.device.length(width, 0)
            height = self.device.length(height, 1)
            rect = Rect(
                x=x_pos, y=y_pos, width=width, height=height, rx=rx_pos, ry=ry_pos
            )

            self.add_element(rect)
            if data is None:
                return "elements", [rect]
            else:
                data.append(rect)
                return "elements", data

        @self.console_argument("x0", type=str, help=_("start x position"))
        @self.console_argument("y0", type=str, help=_("start y position"))
        @self.console_argument("x1", type=str, help=_("end x position"))
        @self.console_argument("y1", type=str, help=_("end y position"))
        @self.console_command(
            "line",
            help=_("adds line to scene"),
            input_type=("elements", None),
            output_type="elements",
        )
        def element_line(command, x0, y0, x1, y1, data=None, **kwargs):
            """
            Draws an svg line in the scene.
            """
            if y1 is None:
                raise CommandSyntaxError
            x0 = self.device.length(x0, 0)
            y0 = self.device.length(y0, 1)
            x1 = self.device.length(x1, 0)
            y1 = self.device.length(y1, 1)
            simple_line = SimpleLine(x0, y0, x1, y1)
            self.add_element(simple_line)
            if data is None:
                return "elements", [simple_line]
            else:
                data.append(simple_line)
                return "elements", data

        @self.console_option("size", "s", type=float, help=_("font size to for object"))
        @self.console_argument("text", type=str, help=_("quoted string of text"))
        @self.console_command(
            "text",
            help=_("text <text>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_text(
            command, channel, _, data=None, text=None, size=None, **kwargs
        ):
            if text is None:
                channel(_("No text specified"))
                return
            svg_text = SVGText(text)
            if size is not None:
                svg_text.font_size = size
            svg_text *= "Scale({scale})".format(scale=UNITS_PER_PIXEL)
            self.add_element(svg_text)
            if data is None:
                return "elements", [svg_text]
            else:
                data.append(svg_text)
                return "elements", data

        @self.console_command(
            "polygon", help=_("polygon (float float)*"), input_type=("elements", None)
        )
        def element_polygon(args=tuple(), data=None, **kwargs):
            try:
                mlist = list(map(str, args))
                # TODO: Scale Physical to Scene.
                for ct, e in enumerate(mlist):
                    ll = Length(e)
                    # print("e=%s, ll=%s, valid=%s" % (e, ll, ll.is_valid_length))
                    if ct % 2 == 0:
                        x = ll.value(
                            ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                        )
                    else:
                        x = ll.value(
                            ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
                        )
                    mlist[ct] = x
                    ct += 1
                element = Polygon(mlist)
                # element *= "Scale({scale})".format(scale=UNITS_PER_PIXEL)
            except ValueError:
                raise CommandSyntaxError(_("Must be a list of spaced delimited length pairs."))
            self.add_element(element)
            if data is None:
                return "elements", [element]
            else:
                data.append(element)
                return "elements", data

        @self.console_command(
            "polyline",
            help=_("polyline (Length Length)*"),
            input_type=("elements", None),
        )
        def element_polyline(command, channel, _, args=tuple(), data=None, **kwargs):
            pcol = None
            pstroke = Color()
            try:
                mlist = list(map(str, args))
                for ct, e in enumerate(mlist):
                    ll = Length(e)
                    if ct % 2 == 0:
                        x = ll.value(
                            ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
                        )
                    else:
                        x = ll.value(
                            ppi=1000.0,
                            relative_length=bed_dim.bed_height * MILS_IN_MM,
                        )
                    mlist[ct] = x

                    ct += 1

                element = Polyline(mlist)
                element.fill = pcol
            except ValueError:
                raise CommandSyntaxError(_("Must be a list of spaced delimited length pairs."))
            self.add_element(element)
            if data is None:
                return "elements", [element]
            else:
                data.append(element)
                return "elements", data

        @self.console_command(
            "path", help=_("Convert any shapes to paths"), input_type="elements"
        )
        def element_path_convert(data, **kwargs):
            for e in data:
                try:
                    node = e.node
                    node.replace_object(abs(Path(node.object)))
                    node.altered()
                except AttributeError:
                    pass

        @self.console_argument(
            "path_d", type=str, help=_("svg path syntax command (quoted).")
        )
        @self.console_command(
            "path",
            help=_("path <svg path>"),
            output_type="elements",
        )
        def element_path(path_d, data, **kwargs):
            try:
                path = Path(path_d)
                path *= "Scale({scale})".format(scale=UNITS_PER_PIXEL)
            except ValueError:
                raise CommandSyntaxError(_("Not a valid path_d string (try quotes)"))

            self.add_element(path)
            if data is None:
                return "elements", [path]
            else:
                data.append(path)
                return "elements", data

        @self.console_argument(
            "stroke_width", type=str, help=_("Stroke-width for the given stroke")
        )
        @self.console_command(
            "stroke-width",
            help=_("stroke-width <length>"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_stroke_width(
            command, channel, _, stroke_width, data=None, **kwargs
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
            if stroke_width is None:
                channel("----------")
                channel(_("Stroke-Width Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    if e.stroke is None or e.stroke == "none":
                        channel(_("%d: stroke = none - %s") % (i, name))
                    else:
                        channel(_("%d: stroke = %s - %s") % (i, e.stroke_width, name))
                    i += 1
                channel("----------")
                return
            else:
                if not stroke_width.is_valid_length:
                    raise CommandSyntaxError(
                        "stroke-width: " + _("This is not a valid length")
                    )

            if len(data) == 0:
                channel(_("No selected elements."))
                return
            stroke_width = self.device.length(stroke_width, -1)
            for e in data:
                e.stroke_width = stroke_width
                if hasattr(e, "node"):
                    e.node.altered()
            return "elements", data

        @self.console_option("filter", "f", type=str, help="Filter indexes")
        @self.console_argument(
            "color", type=Color, help=_("Color to color the given stroke")
        )
        @self.console_command(
            "stroke",
            help=_("stroke <svg color>"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_stroke(
            command, channel, _, color, data=None, filter=None, **kwargs
        ):
            if data is None:
                data = list(self.elems(emphasized=True))
            apply = data
            if filter is not None:
                apply = list()
                for value in filter.split(","):
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                    try:
                        apply.append(data[value])
                    except IndexError:
                        channel(_("index %d out of range") % value)
            if color is None:
                channel("----------")
                channel(_("Stroke Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    if e.stroke is None or e.stroke == "none":
                        channel(_("%d: stroke = none - %s") % (i, name))
                    else:
                        channel(_("%d: stroke = %s - %s") % (i, e.stroke.hex, name))
                    i += 1
                channel("----------")
                return
            elif color == "none":
                for e in apply:
                    e.stroke = None
                    if hasattr(e, "node"):
                        e.node.altered()
            else:
                for e in apply:
                    e.stroke = Color(color)
                    if hasattr(e, "node"):
                        e.node.altered()
            return "elements", data

        @self.console_option("filter", "f", type=str, help="Filter indexes")
        @self.console_argument("color", type=Color, help=_("Color to set the fill to"))
        @self.console_command(
            "fill",
            help=_("fill <svg color>"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_fill(command, channel, _, color, data=None, filter=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            apply = data
            if filter is not None:
                apply = list()
                for value in filter.split(","):
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                    try:
                        apply.append(data[value])
                    except IndexError:
                        channel(_("index %d out of range") % value)
            if color is None:
                channel("----------")
                channel(_("Fill Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    if e.fill is None or e.fill == "none":
                        channel(_("%d: fill = none - %s") % (i, name))
                    else:
                        channel(_("%d: fill = %s - %s") % (i, e.fill.hex, name))
                    i += 1
                channel("----------")
                return "elements", data
            elif color == "none":
                for e in apply:
                    e.fill = None
                    if hasattr(e, "node"):
                        e.node.altered()
            else:
                for e in apply:
                    e.fill = Color(color)
                    if hasattr(e, "node"):
                        e.node.altered()
            return "elements", data

        @self.console_argument("x_offset", type=str, help=_("x offset."))
        @self.console_argument("y_offset", type=str, help=_("y offset"))
        @self.console_command(
            "outline",
            help=_("outline the current selected elements"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_outline(
            command,
            channel,
            _,
            x_offset=None,
            y_offset=None,
            data=None,
            **kwargs,
        ):
            """
            Draws an outline of the current shape.
            """
            if x_offset is None:
                raise CommandSyntaxError
            bounds = self.selected_area()
            if bounds is None:
                channel(_("Nothing Selected"))
                return
            x_pos = bounds[0]
            y_pos = bounds[1]
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]

            offset_x = self.device.length(x_offset, 0) if x_offset is not None else 0
            offset_y = (
                self.device.length(y_offset, 1) if y_offset is not None else offset_x
            )

            x_pos -= offset_x
            y_pos -= offset_y
            width += offset_x * 2
            height += offset_y * 2
            element = Path(Rect(x=x_pos, y=y_pos, width=width, height=height))
            self.add_element(element, "red")
            self.classify([element])
            if data is None:
                return "elements", [element]
            else:
                data.append(element)
                return "elements", data

        @self.console_argument("angle", type=Angle.parse, help=_("angle to rotate by"))
        @self.console_option("cx", "x", type=str, help=_("center x"))
        @self.console_option("cy", "y", type=str, help=_("center y"))
        @self.console_option(
            "absolute",
            "a",
            type=bool,
            action="store_true",
            help=_("angle_to absolute angle"),
        )
        @self.console_command(
            "rotate",
            help=_("rotate <angle>"),
            input_type=(
                None,
                "elements",
            ),
            output_type="elements",
        )
        def element_rotate(
            command,
            channel,
            _,
            angle,
            cx=None,
            cy=None,
            absolute=False,
            data=None,
            **kwargs,
        ):
            if angle is None:
                channel("----------")
                channel(_("Rotate Values:"))
                i = 0
                for element in self.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    channel(
                        _("%d: rotate(%fturn) - %s")
                        % (i, element.rotation.as_turns, name)
                    )
                    i += 1
                channel("----------")
                return
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            self.validate_selected_area()
            bounds = self.selected_area()
            if bounds is None:
                channel(_("No selected elements."))
                return
            rot = angle.as_degrees

            if cx is not None:
                cx = self.device.length(cx, 0)
            else:
                cx = (bounds[2] + bounds[0]) / 2.0
            if cy is not None:
                cy = self.device.length(cy, 1)
            else:
                cy = (bounds[3] + bounds[1]) / 2.0
            matrix = Matrix("rotate(%fdeg,%f,%f)" % (rot, cx, cy))
            try:
                if not absolute:
                    for element in data:
                        try:
                            if element.lock:
                                continue
                        except AttributeError:
                            pass

                        element *= matrix
                        if hasattr(element, "node"):
                            element.node.modified()
                else:
                    for element in data:
                        start_angle = element.rotation
                        amount = rot - start_angle
                        matrix = Matrix(
                            "rotate(%f,%f,%f)" % (Angle(amount).as_degrees, cx, cy)
                        )
                        element *= matrix
                        if hasattr(element, "node"):
                            element.node.modified()
            except ValueError:
                raise CommandSyntaxError
            return "elements", data

        @self.console_argument("scale_x", type=float, help=_("scale_x value"))
        @self.console_argument("scale_y", type=float, help=_("scale_y value"))
        @self.console_option("px", "x", type=str, help=_("scale x origin point"))
        @self.console_option("py", "y", type=str, help=_("scale y origin point"))
        @self.console_option(
            "absolute",
            "a",
            type=bool,
            action="store_true",
            help=_("scale to absolute size"),
        )
        @self.console_command(
            "scale",
            help=_("scale <scale> [<scale-y>]?"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_scale(
            command,
            channel,
            _,
            scale_x=None,
            scale_y=None,
            px=None,
            py=None,
            absolute=False,
            data=None,
            **kwargs,
        ):
            if scale_x is None:
                channel("----------")
                channel(_("Scale Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    channel(
                        "%d: scale(%f, %f) - %s"
                        % (
                            i,
                            e.transform.value_scale_x(),
                            e.transform.value_scale_x(),
                            name,
                        )
                    )
                    i += 1
                channel("----------")
                return
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            bounds = Group.union_bbox(data)
            if scale_y is None:
                scale_y = scale_x
            if px is not None:
                center_x = self.device.length(px, 0)
            else:
                center_x = (bounds[2] + bounds[0]) / 2.0
            if py is not None:
                center_y = self.device.length(py, 1)
            else:
                center_y = (bounds[3] + bounds[1]) / 2.0
            if scale_x == 0 or scale_y == 0:
                channel(_("Scaling by Zero Error"))
                return
            m = Matrix("scale(%f,%f,%f,%f)" % (scale_x, scale_y, center_x, center_y))
            try:
                if not absolute:
                    for e in data:
                        try:
                            if e.lock:
                                continue
                        except AttributeError:
                            pass

                        e *= m
                        if hasattr(e, "node"):
                            e.node.modified()
                else:
                    for e in data:
                        try:
                            if e.lock:
                                continue
                        except AttributeError:
                            pass

                        osx = e.transform.value_scale_x()
                        osy = e.transform.value_scale_y()
                        nsx = scale_x / osx
                        nsy = scale_y / osy
                        m = Matrix(
                            "scale(%f,%f,%f,%f)" % (nsx, nsy, center_x, center_x)
                        )
                        e *= m
                        if hasattr(e, "node"):
                            e.node.modified()
            except ValueError:
                raise CommandSyntaxError
            return "elements", data

        @self.console_argument("tx", type=str, help=_("translate x value"))
        @self.console_argument("ty", type=str, help=_("translate y value"))
        @self.console_option(
            "absolute",
            "a",
            type=bool,
            action="store_true",
            help=_("translate to absolute position"),
        )
        @self.console_command(
            "translate",
            help=_("translate <tx> <ty>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_translate(
            command, channel, _, tx, ty, absolute=False, data=None, **kwargs
        ):
            if tx is None:
                channel("----------")
                channel(_("Translate Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    channel(
                        _("%d: translate(%f, %f) - %s")
                        % (
                            i,
                            e.transform.value_trans_x(),
                            e.transform.value_trans_y(),
                            name,
                        )
                    )
                    i += 1
                channel("----------")
                return
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            if tx is not None:
                tx = self.device.length(tx, 0)
            else:
                tx = 0
            if ty is not None:
                ty = self.device.length(ty, 0)
            else:
                ty = 0
            m = Matrix("translate(%f,%f)" % (tx, ty))
            try:
                if not absolute:
                    for e in data:
                        e *= m
                        if hasattr(e, "node"):
                            e.node.modified()
                else:
                    for e in data:
                        otx = e.transform.value_trans_x()
                        oty = e.transform.value_trans_y()
                        ntx = tx - otx
                        nty = ty - oty
                        m = Matrix("translate(%f,%f)" % (ntx, nty))
                        e *= m
                        if hasattr(e, "node"):
                            e.node.modified()
            except ValueError:
                raise CommandSyntaxError
            return "elements", data

        @self.console_command(
            "move_to_laser",
            help=_("translates the selected element to the laser head"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_move_to_laser(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            tx, ty = self.device.current
            try:
                bounds = Group.union_bbox([abs(e) for e in data])
                otx = bounds[0]
                oty = bounds[1]
                ntx = tx - otx
                nty = ty - oty
                for e in data:
                    e.transform.post_translate(ntx, nty)
                    if hasattr(e, "node"):
                        e.node.modified()
            except ValueError:
                raise CommandSyntaxError
            return "elements", data

        @self.console_argument(
            "x_pos", type=str, help=_("x position for top left corner")
        )
        @self.console_argument(
            "y_pos", type=str, help=_("y position for top left corner")
        )
        @self.console_argument("width", type=str, help=_("new width of selected"))
        @self.console_argument("height", type=str, help=_("new height of selected"))
        @self.console_command(
            "resize",
            help=_("resize <x-pos> <y-pos> <width> <height>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_resize(
            command, channel, _, x_pos, y_pos, width, height, data=None, **kwargs
        ):
            if height is None:
                raise CommandSyntaxError
            try:
                area = self.selected_area()
                if area is None:
                    channel(_("resize: nothing selected"))
                    return
                x_pos = self.device.length(x_pos, 0)
                y_pos = self.device.length(y_pos, 1)
                width = self.device.length(width, 0)
                height = self.device.length(height, 1)
                x, y, x1, y1 = area
                w, h = x1 - x, y1 - y
                if w == 0 or h == 0:  # dot
                    channel(_("resize: cannot resize a dot"))
                    return
                sx = width / w
                sy = height / h
                # Don't do anything if scale is 1
                if sx == 1.0 and sy == 1.0:
                    channel(_("resize: nothing to do - scale factors 1"))
                    return

                m = Matrix(
                    "translate(%f,%f) scale(%f,%f) translate(%f,%f)"
                    % (x_pos, y_pos, sx, sy, -x, -y)
                )
                if data is None:
                    data = list(self.elems(emphasized=True))
                for e in data:
                    try:
                        if e.lock:
                            channel(_("resize: cannot resize a locked image"))
                            return
                    except AttributeError:
                        pass
                for e in data:
                    e *= m
                    if hasattr(e, "node"):
                        e.node.modified()
                return "elements", data
            except (ValueError, ZeroDivisionError, TypeError):
                raise CommandSyntaxError

        @self.console_argument("sx", type=float, help=_("scale_x value"))
        @self.console_argument("kx", type=float, help=_("skew_x value"))
        @self.console_argument("ky", type=float, help=_("skew_y value"))
        @self.console_argument("sy", type=float, help=_("scale_y value"))
        @self.console_argument("tx", type=str, help=_("translate_x value"))
        @self.console_argument("ty", type=str, help=_("translate_y value"))
        @self.console_command(
            "matrix",
            help=_("matrix <sx> <kx> <ky> <sy> <tx> <ty>"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_matrix(
            command, channel, _, sx, kx, ky, sy, tx, ty, data=None, **kwargs
        ):
            if ty is None:
                channel("----------")
                channel(_("Matrix Values:"))
                i = 0
                for e in self.elems():
                    name = str(e)
                    if len(name) > 50:
                        name = name[:50] + "…"
                    channel("%d: %s - %s" % (i, str(e.transform), name))
                    i += 1
                channel("----------")
                return
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            try:
                # SVG 7.15.3 defines the matrix form as:
                # [a c  e]
                # [b d  f]
                m = Matrix(
                    sx,
                    kx,
                    ky,
                    sy,
                    self.device.length(tx, 0),
                    self.device.length(ty, 1),
                )
                for e in data:
                    try:
                        if e.lock:
                            continue
                    except AttributeError:
                        pass

                    e.transform = Matrix(m)
                    if hasattr(e, "node"):
                        e.node.modified()
            except ValueError:
                raise CommandSyntaxError
            return

        @self.console_command(
            "reset",
            help=_("reset affine transformations"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def reset(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            for e in data:
                try:
                    if e.lock:
                        continue
                except AttributeError:
                    pass

                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(_("reset - %s") % name)
                e.transform.reset()
                if hasattr(e, "node"):
                    e.node.modified()
            return "elements", data

        @self.console_command(
            "reify",
            help=_("reify affine transformations"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_reify(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            for e in data:
                try:
                    if e.lock:
                        continue
                except AttributeError:
                    pass

                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(_("reified - %s") % name)
                e.reify()
                if hasattr(e, "node"):
                    e.node.altered()
            return "elements", data

        @self.console_command(
            "classify",
            help=_("classify elements into operations"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_classify(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            self.classify(data)
            return "elements", data

        @self.console_command(
            "declassify",
            help=_("declassify selected elements"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def declassify(command, channel, _, data=None, **kwargs):
            if data is None:
                data = list(self.elems(emphasized=True))
            if len(data) == 0:
                channel(_("No selected elements."))
                return
            self.remove_elements_from_operations(data)
            return "elements", data

        # ==========
        # TREE BASE
        # ==========
        @self.console_command(
            "tree", help=_("access and alter tree elements"), output_type="tree"
        )
        def tree(**kwargs):
            return "tree", [self._tree]

        @self.console_command(
            "bounds", help=_("view tree bounds"), input_type="tree", output_type="tree"
        )
        def tree_bounds(command, channel, _, data=None, **kwargs):
            if data is None:
                data = [self._tree]

            def b_list(path, node):
                for i, n in enumerate(node.children):
                    p = list(path)
                    p.append(str(i))
                    channel(
                        "%s: %s - %s %s - %s"
                        % (
                            ".".join(p).ljust(10),
                            str(n._bounds),
                            str(n._bounds_dirty),
                            str(n.type),
                            str(n.label[:16]),
                        )
                    )
                    b_list(p, n)

            for d in data:
                channel("----------")
                if d.type == "root":
                    channel(_("Tree:"))
                else:
                    channel("%s:" % d.label)
                b_list([], d)
                channel("----------")

            return "tree", data

        @self.console_command(
            "list", help=_("view tree"), input_type="tree", output_type="tree"
        )
        def tree_list(command, channel, _, data=None, **kwargs):
            if data is None:
                data = [self._tree]

            def t_list(path, node):
                for i, n in enumerate(node.children):
                    p = list(path)
                    p.append(str(i))
                    if n.targeted:
                        j = "+"
                    elif n.emphasized:
                        j = "~"
                    elif n.highlighted:
                        j = "-"
                    else:
                        j = ":"
                    channel(
                        "%s%s %s - %s"
                        % (".".join(p).ljust(10), j, str(n.type), str(n.label))
                    )
                    t_list(p, n)

            for d in data:
                channel("----------")
                if d.type == "root":
                    channel(_("Tree:"))
                else:
                    channel("%s:" % d.label)
                t_list([], d)
                channel("----------")

            return "tree", data

        @self.console_argument("drag", help="Drag node address")
        @self.console_argument("drop", help="Drop node address")
        @self.console_command(
            "dnd", help=_("Drag and Drop Node"), input_type="tree", output_type="tree"
        )
        def tree_dnd(command, channel, _, data=None, drag=None, drop=None, **kwargs):
            """
            Drag and Drop command performs a console based drag and drop operation
            Eg. "tree dnd 0.1 0.2" will drag node 0.1 into node 0.2
            """
            if data is None:
                data = [self._tree]
            if drop is None:
                raise CommandSyntaxError
            try:
                drag_node = self._tree
                for n in drag.split("."):
                    drag_node = drag_node.children[int(n)]
                drop_node = self._tree
                for n in drop.split("."):
                    drop_node = drop_node.children[int(n)]
                drop_node.drop(drag_node)
            except (IndexError, AttributeError, ValueError):
                raise CommandSyntaxError
            return "tree", data

        @self.console_argument("node", help="Node address for menu")
        @self.console_argument("execute", help="Command to execute")
        @self.console_command(
            "menu",
            help=_("Load menu for given node"),
            input_type="tree",
            output_type="tree",
        )
        def tree_menu(
            command, channel, _, data=None, node=None, execute=None, **kwargs
        ):
            """
            Create menu for a particular node.
            Processes submenus, references, radio_state as needed.
            """
            try:
                menu_node = self._tree
                for n in node.split("."):
                    menu_node = menu_node.children[int(n)]
            except (IndexError, AttributeError, ValueError):
                raise CommandSyntaxError

            menu = []
            submenus = {}

            def menu_functions(f, cmd_node):
                func_dict = dict(f.func_dict)

                def specific(event=None):
                    f(cmd_node, **func_dict)

                return specific

            for func in self.tree_operations_for_node(menu_node):
                submenu_name = func.submenu
                submenu = None
                if submenu_name in submenus:
                    submenu = submenus[submenu_name]
                elif submenu_name is not None:
                    submenu = list()
                    menu.append((submenu_name, submenu))
                    submenus[submenu_name] = submenu

                menu_context = submenu if submenu is not None else menu
                if func.reference is not None:
                    pass
                if func.radio_state is not None:
                    if func.separate_before:
                        menu_context.append(("------", None))
                    n = func.real_name
                    if func.radio_state:
                        n = "✓" + n
                    menu_context.append((n, menu_functions(func, menu_node)))
                else:
                    if func.separate_before:
                        menu_context.append(("------", None))
                    menu_context.append(
                        (func.real_name, menu_functions(func, menu_node))
                    )
                if func.separate_after:
                    menu_context.append(("------", None))
            if execute is not None:
                try:
                    execute_command = ("menu", menu)
                    for n in execute.split("."):
                        name, cmd = execute_command
                        execute_command = cmd[int(n)]
                    name, cmd = execute_command
                    channel("Executing %s: %s" % (name, str(cmd)))
                    cmd()
                except (IndexError, AttributeError, ValueError, TypeError):
                    raise CommandSyntaxError
            else:

                def m_list(path, menu):
                    for i, n in enumerate(menu):
                        p = list(path)
                        p.append(str(i))
                        name, submenu = n
                        channel("%s: %s" % (".".join(p).ljust(10), str(name)))
                        if isinstance(submenu, list):
                            m_list(p, submenu)

                m_list([], menu)

            return "tree", data

        @self.console_command(
            "selected",
            help=_("delegate commands to focused value"),
            input_type="tree",
            output_type="tree",
        )
        def selected(channel, _, **kwargs):
            """
            Set tree list to selected node
            """
            return "tree", list(self.flat(selected=True))

        @self.console_command(
            "highlighted",
            help=_("delegate commands to sub-focused value"),
            input_type="tree",
            output_type="tree",
        )
        def highlighted(channel, _, **kwargs):
            """
            Set tree list to highlighted nodes
            """
            return "tree", list(self.flat(highlighted=True))

        @self.console_command(
            "targeted",
            help=_("delegate commands to sub-focused value"),
            input_type="tree",
            output_type="tree",
        )
        def targeted(channel, _, **kwargs):
            """
            Set tree list to highlighted nodes
            """
            return "tree", list(self.flat(targeted=True))

        @self.console_command(
            "delete",
            help=_("delete the given nodes"),
            input_type="tree",
            output_type="tree",
        )
        def delete(channel, _, data=None, **kwargs):
            """
            Delete nodes.
            Structural nodes such as root, elements, and operations are not able to be deleted
            """
            for n in data:
                # Cannot delete structure nodes.
                if n.type not in ("root", "branch elems", "branch ops"):
                    if n._parent is not None:
                        n.remove_node()
            return "tree", [self._tree]

        @self.console_command(
            "delegate",
            help=_("delegate commands to focused value"),
            input_type="tree",
            output_type=("op", "elements"),
        )
        def delegate(channel, _, **kwargs):
            """
            Delegate to either ops or elements depending on the current node emphasis
            """
            for item in self.flat(emphasized=True):
                if item.type.startswith("op"):
                    return "ops", list(self.ops(emphasized=True))
                if item.type in ("elem", "group", "file"):
                    return "elements", list(self.elems(emphasized=True))

        # ==========
        # CLIPBOARD COMMANDS
        # ==========
        @self.console_option("name", "n", type=str)
        @self.console_command(
            "clipboard",
            help=_("clipboard"),
            input_type=(None, "elements"),
            output_type="clipboard",
        )
        def clipboard_base(data=None, name=None, **kwargs):
            """
            Clipboard commands. Applies to current selected elements to
            make a copy of those elements. Paste a copy of those elements
            or cut those elements. Clear clears the clipboard.

            The list command will list them but this is only for debug.
            """
            if name is not None:
                self._clipboard_default = name
            if data is None:
                return "clipboard", list(self.elems(emphasized=True))
            else:
                return "clipboard", data

        @self.console_command(
            "copy",
            help=_("clipboard copy"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_copy(data=None, **kwargs):
            destination = self._clipboard_default
            self._clipboard[destination] = [copy(e) for e in data]
            return "elements", self._clipboard[destination]

        @self.console_option("dx", "x", help=_("paste offset x"), type=str)
        @self.console_option("dy", "y", help=_("paste offset y"), type=str)
        @self.console_command(
            "paste",
            help=_("clipboard paste"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_paste(command, channel, _, data=None, dx=None, dy=None, **kwargs):
            destination = self._clipboard_default
            try:
                pasted = [copy(e) for e in self._clipboard[destination]]
            except KeyError:
                channel(_("Error: Clipboard Empty"))
                return
            if dx is not None or dy is not None:
                if dx is None:
                    dx = 0
                else:
                    dx = self.device.length(dx, 0)
                if dy is None:
                    dy = 0
                else:
                    dy = self.device.length(dy, 1)
                m = Matrix("translate(%s, %s)" % (dx, dy))
                for e in pasted:
                    e *= m
            group = self.elem_branch.add(type="group", label="Group")
            for p in pasted:
                group.add(p, type="elem")
            self.set_emphasis([group])
            return "elements", pasted

        @self.console_command(
            "cut",
            help=_("clipboard cut"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_cut(data=None, **kwargs):
            destination = self._clipboard_default
            self._clipboard[destination] = [copy(e) for e in data]
            self.remove_elements(data)
            return "elements", self._clipboard[destination]

        @self.console_command(
            "clear",
            help=_("clipboard clear"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_clear(data=None, **kwargs):
            destination = self._clipboard_default
            old = self._clipboard[destination]
            self._clipboard[destination] = None
            return "elements", old

        @self.console_command(
            "contents",
            help=_("clipboard contents"),
            input_type="clipboard",
            output_type="elements",
        )
        def clipboard_contents(**kwargs):
            destination = self._clipboard_default
            return "elements", self._clipboard[destination]

        @self.console_command(
            "list",
            help=_("clipboard list"),
            input_type="clipboard",
        )
        def clipboard_list(command, channel, _, **kwargs):
            for v in self._clipboard:
                k = self._clipboard[v]
                channel("%s: %s" % (str(v).ljust(5), str(k)))

        # ==========
        # NOTES COMMANDS
        # ==========
        @self.console_option(
            "append", "a", type=bool, action="store_true", default=False
        )
        @self.console_command("note", help=_("note <note>"))
        def note(command, channel, _, append=False, remainder=None, **kwargs):
            note = remainder
            if note is None:
                if self.note is None:
                    channel(_("No Note."))
                else:
                    channel(str(self.note))
            else:
                if append:
                    self.note += "\n" + note
                else:
                    self.note = note
                channel(_("Note Set."))
                channel(str(self.note))

        # ==========
        # TRACE OPERATIONS
        # ==========
        @self.console_command(
            "trace_hull",
            help=_("trace the convex hull of current elements"),
            input_type=(None, "elements"),
        )
        def trace_trace_hull(command, channel, _, data=None, **kwargs):
            spooler = self.device.spooler
            if data is None:
                data = list(self.elems(emphasized=True))
            pts = []
            for obj in data:
                if isinstance(obj, Path):
                    epath = abs(obj)
                    pts += [q for q in epath.as_points()]
                elif isinstance(obj, SVGImage):
                    bounds = obj.bbox()
                    pts += [
                        (bounds[0], bounds[1]),
                        (bounds[0], bounds[3]),
                        (bounds[2], bounds[1]),
                        (bounds[2], bounds[3]),
                    ]
            hull = [p for p in Point.convex_hull(pts)]
            if len(hull) == 0:
                channel(_("No elements bounds to trace."))
                return
            hull.append(hull[0])  # loop

            def trace_hull():
                yield "wait_finish"
                yield "rapid_mode"
                for p in hull:
                    yield (
                        "move_abs",
                        "{x}{units}".format(x=p[0], units=self.units),
                        "{y}{units}".format(y=p[1], units=self.units),
                    )

            spooler.job(trace_hull)

        @self.console_command(
            "trace_quick", help=_("quick trace the bounding box of current elements")
        )
        def trace_trace_quick(command, channel, _, **kwargs):
            spooler = self.device.spooler
            bbox = self.selected_area()
            if bbox is None:
                channel(_("No elements bounds to trace."))
                return

            def trace_quick():
                yield "rapid_mode"
                yield (
                    "move_abs",
                    "{x}{units}".format(x=bbox[0], units=self.units),
                    "{y}{units}".format(y=bbox[1], units=self.units),
                )
                yield (
                    "move_abs",
                    "{x}{units}".format(x=bbox[2], units=self.units),
                    "{y}{units}".format(y=bbox[1], units=self.units),
                )
                yield (
                    "move_abs",
                    "{x}{units}".format(x=bbox[2], units=self.units),
                    "{y}{units}".format(y=bbox[3], units=self.units),
                )
                yield (
                    "move_abs",
                    "{x}{units}".format(x=bbox[0], units=self.units),
                    "{y}{units}".format(y=bbox[3], units=self.units),
                )
                yield (
                    "move_abs",
                    "{x}{units}".format(x=bbox[0], units=self.units),
                    "{y}{units}".format(y=bbox[1], units=self.units),
                )

            spooler.job(trace_quick)

        # --------------------------- END COMMANDS ------------------------------

    def _init_tree(self, kernel):

        _ = kernel.translation
        # --------------------------- TREE OPERATIONS ---------------------------

        non_structural_nodes = (
            "op cut",
            "op raster",
            "op image",
            "op engrave",
            "op dots",
            "ref elem",
            "cmdop",
            "consoleop",
            "lasercode",
            "cutcode",
            "blob",
            "elem",
            "file",
            "group",
        )
        operate_nodes = (
            "op cut",
            "op raster",
            "op image",
            "op engrave",
            "op dots",
            "cmdop",
            "consoleop",
        )
        op_nodes = (
            "op cut",
            "op raster",
            "op image",
            "op engrave",
            "op dots",
            "cmdop",
            "consoleop",
        )

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: len(list(self.ops(emphasized=True))) == 1)
        @self.tree_operation(
            _("Operation properties"), node_type=operate_nodes, help=""
        )
        def operation_property(node, **kwargs):
            activate = self.kernel.lookup("function/open_property_window_for_node")
            if activate is not None:
                activate(node)

        @self.tree_separator_after()
        @self.tree_operation(_("Edit"), node_type="consoleop", help="")
        def edit_console_command(node, **kwargs):
            self.context.open("window/ConsoleProperty", self.context.gui, node=node)

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: isinstance(node.object, Shape))
        @self.tree_operation(_("Element properties"), node_type="elem", help="")
        def path_property(node, **kwargs):
            activate = self.kernel.lookup("function/open_property_window_for_node")
            if activate is not None:
                activate(node)

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: isinstance(node.object, Group))
        @self.tree_operation(_("Group properties"), node_type="group", help="")
        def group_property(node, **kwargs):
            activate = self.kernel.lookup("function/open_property_window_for_node")
            if activate is not None:
                activate(node)

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: isinstance(node.object, SVGText))
        @self.tree_operation(_("Text properties"), node_type="elem", help="")
        def text_property(node, **kwargs):
            activate = self.kernel.lookup("function/open_property_window_for_node")
            if activate is not None:
                activate(node)

        @self.tree_separator_after()
        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_operation(_("Image properties"), node_type="elem", help="")
        def image_property(node, **kwargs):
            activate = self.kernel.lookup("function/open_property_window_for_node")
            if activate is not None:
                activate(node)

        @self.tree_operation(
            _("Ungroup elements"), node_type=("group", "file"), help=""
        )
        def ungroup_elements(node, **kwargs):
            for n in list(node.children):
                node.insert_sibling(n)
            node.remove_node()  # Removing group/file node.

        @self.tree_operation(_("Group elements"), node_type="elem", help="")
        def group_elements(node, **kwargs):
            # group_node = node.parent.add_sibling(node, type="group", name="Group")
            group_node = node.parent.add(type="group", label="Group")
            for e in list(self.elems(emphasized=True)):
                node = e.node
                group_node.append_child(node)

        @self.tree_operation(_("Enable/Disable ops"), node_type=op_nodes, help="")
        def toggle_n_operations(node, **kwargs):
            for n in self.ops(emphasized=True):
                n.output = not n.output
                n.notify_update()

        # TODO: Restore convert node type ability
        #
        # @self.tree_submenu(_("Convert operation"))
        # @self.tree_operation(_("Convert to Image"), node_type=operate_nodes, help="")
        # def convert_operation_image(node, **kwargs):
        #     for n in self.ops(emphasized=True):
        #         n.operation = "Image"
        #
        # @self.tree_submenu(_("Convert operation"))
        # @self.tree_operation(_("Convert to Raster"), node_type=operate_nodes, help="")
        # def convert_operation_raster(node, **kwargs):
        #     for n in self.ops(emphasized=True):
        #         n.operation = "Raster"
        #
        # @self.tree_submenu(_("Convert operation"))
        # @self.tree_operation(_("Convert to Engrave"), node_type=operate_nodes, help="")
        # def convert_operation_engrave(node, **kwargs):
        #     for n in self.ops(emphasized=True):
        #         n.operation = "Engrave"
        #
        # @self.tree_submenu(_("Convert operation"))
        # @self.tree_operation(_("Convert to Cut"), node_type=operate_nodes, help="")
        # def convert_operation_cut(node, **kwargs):
        #     for n in self.ops(emphasized=True):
        #         n.operation = "Cut"

        def radio_match(node, speed=0, **kwargs):
            return node.speed == float(speed)

        @self.tree_submenu(_("Speed"))
        @self.tree_radio(radio_match)
        @self.tree_values("speed", (50, 75, 100, 150, 200, 250, 300, 350))
        @self.tree_operation(
            _("%smm/s") % "{speed}", node_type=("op raster", "op image"), help=""
        )
        def set_speed_raster(node, speed=150, **kwargs):
            node.speed = float(speed)
            self.signal("element_property_reload", node)

        @self.tree_submenu(_("Speed"))
        @self.tree_radio(radio_match)
        @self.tree_values("speed", (5, 10, 15, 20, 25, 30, 35, 40))
        @self.tree_operation(
            _("%smm/s") % "{speed}", node_type=("op cut", "op engrave"), help=""
        )
        def set_speed_vector(node, speed=35, **kwargs):
            node.speed = float(speed)
            self.signal("element_property_reload", node)

        def radio_match(node, power=0, **kwargs):
            return node.power == float(power)

        @self.tree_submenu(_("Power"))
        @self.tree_radio(radio_match)
        @self.tree_values("power", (100, 250, 333, 500, 666, 750, 1000))
        @self.tree_operation(
            _("%sppi") % "{power}",
            node_type=("op cut", "op raster", "op image", "op engrave"),
            help="",
        )
        def set_power(node, power=1000, **kwargs):
            node.power = float(power)
            self.signal("element_property_reload", node)

        def radio_match(node, i=1, **kwargs):
            return node.raster_step == i

        @self.tree_submenu(_("Step"))
        @self.tree_radio(radio_match)
        @self.tree_iterate("i", 1, 10)
        @self.tree_operation(
            _("Step %s") % "{i}",
            node_type="op raster",
            help=_("Change raster step values of operation"),
        )
        def set_step_n(node, i=1, **kwargs):
            node.raster_step = i
            self.signal("element_property_reload", node)

        def radio_match(node, passvalue=1, **kwargs):
            return (node.passes_custom and passvalue == node.passes) or (
                not node.passes_custom and passvalue == 1
            )

        @self.tree_submenu(_("Set operation passes"))
        @self.tree_radio(radio_match)
        @self.tree_iterate("passvalue", 1, 10)
        @self.tree_operation(
            _("Passes %s") % "{passvalue}", node_type=operate_nodes, help=""
        )
        def set_n_passes(node, passvalue=1, **kwargs):
            node.passes = passvalue
            node.passes_custom = passvalue != 1
            self.signal("element_property_reload", node)

        @self.tree_separator_after()
        @self.tree_operation(
            _("Execute operation(s)"),
            node_type=operate_nodes,
            help=_("Execute Job for the selected operation(s)."),
        )
        def execute_job(node, **kwargs):
            node.emphasized = True
            self("plan0 clear copy-selected\n")
            self("window open ExecuteJob 0\n")

        @self.tree_separator_after()
        @self.tree_operation(
            _("Simulate operation(s)"),
            node_type=operate_nodes,
            help=_("Run simulation for the selected operation(s)"),
        )
        def compile_and_simulate(node, **kwargs):
            node.emphasized = True
            self("plan0 copy-selected preprocess validate blob preopt optimize\n")
            self("window open Simulation 0\n")

        @self.tree_operation(_("Clear all"), node_type="branch ops", help="")
        def clear_all(node, **kwargs):
            self("operation* delete\n")

        @self.tree_operation(_("Clear all"), node_type="branch elems", help="")
        def clear_all_ops(node, **kwargs):
            self("element* delete\n")
            self.elem_branch.remove_all_children()

        # ==========
        # REMOVE MULTI (Tree Selected)
        # ==========
        @self.tree_conditional(
            lambda cond: len(
                list(
                    self.flat(selected=True, cascade=False, types=non_structural_nodes)
                )
            )
            > 1
        )
        @self.tree_calc(
            "ecount",
            lambda i: len(
                list(
                    self.flat(selected=True, cascade=False, types=non_structural_nodes)
                )
            ),
        )
        @self.tree_operation(
            _("Remove %s selected items") % "{ecount}",
            node_type=non_structural_nodes,
            help="",
        )
        def remove_multi_nodes(node, **kwargs):
            nodes = list(
                self.flat(selected=True, cascade=False, types=non_structural_nodes)
            )
            for node in nodes:
                if node.parent is not None:  # May have already removed.
                    node.remove_node()
            self.set_emphasis(None)

        # ==========
        # REMOVE SINGLE (Tree Selected)
        # ==========
        @self.tree_conditional(
            lambda cond: len(
                list(
                    self.flat(selected=True, cascade=False, types=non_structural_nodes)
                )
            )
            == 1
        )
        @self.tree_operation(
            _("Remove '%s'") % "{name}",
            node_type=non_structural_nodes,
            help="",
        )
        def remove_type_op(node, **kwargs):
            node.remove_node()
            self.set_emphasis(None)

        # ==========
        # Remove Operations (If No Tree Selected)
        # Note: This code would rarely match anything since the tree selected will almost always be true if we have
        # match this conditional. The tree-selected delete functions are superior.
        # ==========
        @self.tree_conditional(
            lambda cond: len(
                list(
                    self.flat(selected=True, cascade=False, types=non_structural_nodes)
                )
            )
            == 0
        )
        @self.tree_conditional(lambda node: len(list(self.ops(emphasized=True))) > 1)
        @self.tree_calc("ecount", lambda i: len(list(self.ops(emphasized=True))))
        @self.tree_operation(
            _("Remove %s operations") % "{ecount}",
            node_type=(
                "op cut",
                "op raster",
                "op image",
                "op engrave",
                "op dots",
                "cmdop",
                "consoleop",
                "lasercode",
                "cutcode",
                "blob",
            ),
            help="",
        )
        def remove_n_ops(node, **kwargs):
            self("operation delete\n")

        # ==========
        # REMOVE ELEMENTS
        # ==========
        @self.tree_conditional(lambda node: len(list(self.elems(emphasized=True))) > 0)
        @self.tree_calc("ecount", lambda i: len(list(self.elems(emphasized=True))))
        @self.tree_operation(
            _("Remove %s elements") % "{ecount}",
            node_type=(
                "elem",
                "file",
                "group",
            ),
            help="",
        )
        def remove_n_elements(node, **kwargs):
            self("element delete\n")

        # ==========
        # CONVERT TREE OPERATIONS
        # ==========
        @self.tree_operation(
            _("Convert to Cutcode"),
            node_type="lasercode",
            help="",
        )
        def lasercode2cut(node, **kwargs):
            node.replace_node(CutCode.from_lasercode(node.object), type="cutcode")

        @self.tree_conditional_try(lambda node: hasattr(node.object, "as_cutobjects"))
        @self.tree_operation(
            _("Convert to Cutcode"),
            node_type="blob",
            help="",
        )
        def blob2cut(node, **kwargs):
            node.replace_node(node.object.as_cutobjects(), type="cutcode")

        @self.tree_operation(
            _("Convert to Path"),
            node_type="cutcode",
            help="",
        )
        def cutcode2pathcut(node, **kwargs):
            cutcode = node.object
            elements = list(cutcode.as_elements())
            n = None
            for element in elements:
                n = self.elem_branch.add(element, type="elem")
            node.remove_node()
            if n is not None:
                n.focus()

        @self.tree_submenu(_("Clone reference"))
        @self.tree_operation(_("Make 1 copy"), node_type="ref elem", help="")
        def clone_single_element_op(node, **kwargs):
            clone_element_op(node, copies=1, **kwargs)

        @self.tree_submenu(_("Clone reference"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(
            _("Make %s copies") % "{copies}", node_type="ref elem", help=""
        )
        def clone_element_op(node, copies=1, **kwargs):
            index = node.parent.children.index(node)
            for i in range(copies):
                node.parent.add(node.object, type="ref elem", pos=index)
            node.modified()
            self.signal("rebuild_tree")

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_operation(
            _("Reverse subitems order"),
            node_type=(
                "op cut",
                "op raster",
                "op image",
                "op engrave",
                "op dots",
                "group",
                "branch elems",
                "file",
                "branch ops",
            ),
            help=_("Reverse the items within this subitem"),
        )
        def reverse_layer_order(node, **kwargs):
            node.reverse()
            self.signal("rebuild_tree")

        @self.tree_separator_after()
        @self.tree_operation(
            _("Refresh classification"), node_type="branch ops", help=""
        )
        def refresh_clasifications(node, **kwargs):
            self.remove_elements_from_operations(list(self.elems()))
            self.classify(list(self.elems()))
            self.signal("rebuild_tree")

        materials = [
            _("Wood"),
            _("Acrylic"),
            _("Foam"),
            _("Leather"),
            _("Cardboard"),
            _("Cork"),
            _("Textiles"),
            _("Paper"),
            _("Save-1"),
            _("Save-2"),
            _("Save-3"),
        ]

        def union_materials_saved():
            union = [
                d
                for d in self.op_data.section_set()
                if d not in materials and d != "previous"
            ]
            union.extend(materials)
            return union

        def difference_materials_saved():
            secs = self.op_data.section_set()
            difference = [m for m in materials if m not in secs]
            return difference

        @self.tree_submenu(_("Load"))
        @self.tree_values("opname", values=self.op_data.section_set)
        @self.tree_operation(_("%s") % "{opname}", node_type="branch ops", help="")
        def load_ops(node, opname, **kwargs):
            self("material load %s\n" % opname)

        @self.tree_separator_before()
        @self.tree_submenu(_("Load"))
        @self.tree_operation(_("Other/Blue/Red"), node_type="branch ops", help="")
        def default_classifications(node, **kwargs):
            self.load_default()

        @self.tree_submenu(_("Load"))
        @self.tree_separator_after()
        @self.tree_operation(_("Basic"), node_type="branch ops", help="")
        def basic_classifications(node, **kwargs):
            self.load_default2()

        @self.tree_submenu(_("Save"))
        @self.tree_values("opname", values=self.op_data.section_set)
        @self.tree_operation("{opname}", node_type="branch ops", help="")
        def save_materials(node, opname="saved", **kwargs):
            self("material save %s\n" % opname)

        @self.tree_separator_before()
        @self.tree_submenu(_("Save"))
        @self.tree_prompt("opname", _("Name to store current operations under?"))
        @self.tree_operation("New", node_type="branch ops", help="")
        def save_material_custom(node, opname, **kwargs):
            if opname is not None:
                self("material save %s\n" % opname.replace(" ", "_"))

        @self.tree_submenu(_("Delete"))
        @self.tree_values("opname", values=self.op_data.section_set)
        @self.tree_operation("{opname}", node_type="branch ops", help="")
        def remove_ops(node, opname="saved", **kwargs):
            self("material delete %s\n" % opname)

        @self.tree_separator_before()
        @self.tree_submenu(_("Append operation"))
        @self.tree_operation(_("Append Image"), node_type="branch ops", help="")
        def append_operation_image(node, pos=None, **kwargs):
            self.add_op(ImageOpNode(), pos=pos)

        @self.tree_submenu(_("Append operation"))
        @self.tree_operation(_("Append Raster"), node_type="branch ops", help="")
        def append_operation_raster(node, pos=None, **kwargs):
            self.add_op(RasterOpNode(), pos=pos)

        @self.tree_submenu(_("Append operation"))
        @self.tree_operation(_("Append Engrave"), node_type="branch ops", help="")
        def append_operation_engrave(node, pos=None, **kwargs):
            self.add_op(EngraveOpNode(), pos=pos)

        @self.tree_submenu(_("Append operation"))
        @self.tree_operation(_("Append Cut"), node_type="branch ops", help="")
        def append_operation_cut(node, pos=None, **kwargs):
            self.add_op(CutOpNode(), pos=pos)

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(_("Append Home"), node_type="branch ops", help="")
        def append_operation_home(node, pos=None, **kwargs):
            self.op_branch.add(CommandOperation("Home", "home"), type="cmdop", pos=pos)

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(
            _("Append Return to Origin"), node_type="branch ops", help=""
        )
        def append_operation_origin(node, pos=None, **kwargs):
            self.op_branch.add(
                CommandOperation("Origin", "home", 0, 0), type="cmdop", pos=pos
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(_("Append Beep"), node_type="branch ops", help="")
        def append_operation_beep(node, pos=None, **kwargs):
            self.op_branch.add(CommandOperation("Beep", "beep"), type="cmdop", pos=pos)

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(
            _("Append Interrupt (console)"), node_type="branch ops", help=""
        )
        def append_operation_interrupt_console(node, pos=None, **kwargs):
            self.op_branch.add(
                ConsoleOperation('interrupt "Spooling was interrupted"'),
                type="consoleop",
                pos=pos,
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(_("Append Interrupt"), node_type="branch ops", help="")
        def append_operation_interrupt(node, pos=None, **kwargs):
            self.op_branch.add(
                CommandOperation(
                    "Interrupt",
                    "function",
                    self.lookup("function/interrupt"),
                ),
                type="cmdop",
                pos=pos,
            )

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(
            _("Append Home/Beep/Interrupt"), node_type="branch ops", help=""
        )
        def append_operation_home_beep_interrupt(node, **kwargs):
            append_operation_home(node, **kwargs)
            append_operation_beep(node, **kwargs)
            append_operation_interrupt(node, **kwargs)
            append_operation_interrupt_console(node, **kwargs)

        @self.tree_submenu(_("Append special operation(s)"))
        @self.tree_operation(_("Append Shutdown"), node_type="branch ops", help="")
        def append_operation_shutdown(node, pos=None, **kwargs):
            self.op_branch.add(
                CommandOperation(
                    "Shutdown",
                    "function",
                    self.console_function("quit\n"),
                ),
                type="cmdop",
                pos=pos,
            )

        @self.tree_operation(
            _("Reclassify operations"), node_type="branch elems", help=""
        )
        def reclassify_operations(node, **kwargs):
            elems = list(self.elems())
            self.remove_elements_from_operations(elems)
            self.classify(list(self.elems()))
            self.signal("rebuild_tree")

        @self.tree_operation(
            _("Duplicate operation(s)"),
            node_type=operate_nodes,
            help=_("duplicate operation element nodes"),
        )
        def duplicate_operation(node, **kwargs):
            operations = self._tree.get(type="branch ops").children
            for op in self.ops(emphasized=True):
                try:
                    pos = operations.index(op) + 1
                except ValueError:
                    pos = None
                copy_op = copy(op)
                self.add_op(copy_op, pos=pos)
                for child in op.children:
                    try:
                        copy_op.add(child.object, type="ref elem")
                    except AttributeError:
                        pass

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_submenu(_("Passes"))
        @self.tree_operation(
            _("Add 1 pass"), node_type=("op image", "op engrave", "op cut"), help=""
        )
        def add_1_pass(node, **kwargs):
            add_n_passes(node, copies=1, **kwargs)

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_submenu(_("Passes"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(
            _("Add %s passes") % "{copies}",
            node_type=("op image", "op engrave", "op cut"),
            help="",
        )
        def add_n_passes(node, copies=1, **kwargs):
            add_elements = [
                child.object for child in node.children if child.object is not None
            ]
            removed = False
            for i in range(0, len(add_elements)):
                for q in range(0, i):
                    if add_elements[q] is add_elements[i]:
                        add_elements[i] = None
                        removed = True
            if removed:
                add_elements = [c for c in add_elements if c is not None]
            add_elements *= copies
            node.add_all(add_elements, type="ref elem")
            self.signal("rebuild_tree")

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_submenu(_("Duplicate element(s)"))
        @self.tree_operation(
            _("Duplicate elements 1 time"),
            node_type=("op image", "op engrave", "op cut"),
            help="",
        )
        def dup_1_copy(node, **kwargs):
            dup_n_copies(node, copies=1, **kwargs)

        @self.tree_conditional(lambda node: node.count_children() > 1)
        @self.tree_submenu(_("Duplicate element(s)"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(
            _("Duplicate elements %s times") % "{copies}",
            node_type=("op image", "op engrave", "op cut"),
            help="",
        )
        def dup_n_copies(node, copies=1, **kwargs):
            add_elements = [
                child.object for child in node.children if child.object is not None
            ]
            add_elements *= copies
            node.add_all(add_elements, type="ref elem")
            self.signal("rebuild_tree")

        @self.tree_operation(
            _("Make raster image"),
            node_type=("op image", "op raster"),
            help=_("Convert a vector element into a raster element."),
        )
        def make_raster_image(node, **kwargs):
            subitems = list(node.flat(types=("elem", "ref elem")))
            reverse = self.classify_reverse
            if reverse:
                subitems = list(reversed(subitems))
            make_raster = self.lookup("render-op/make_raster")
            bounds = Group.union_bbox([s.object for s in subitems], with_stroke=True)
            if bounds is None:
                return
            step = float(node.raster_step)
            if step == 0:
                step = 1
            xmin, ymin, xmax, ymax = bounds

            image = make_raster(
                subitems,
                bounds,
                step=step,
            )
            image_element = SVGImage(image=image)
            image_element.transform.post_scale(step, step)
            image_element.transform.post_translate(xmin, ymin)
            image_element.values["raster_step"] = step
            self.add_elem(image_element)

        def add_after_index(self):
            try:
                operations = self._tree.get(type="branch ops").children
                return operations.index(list(self.ops(emphasized=True))[-1]) + 1
            except ValueError:
                return None

        @self.tree_separator_before()
        @self.tree_submenu(_("Add operation"))
        @self.tree_operation(_("Add Image"), node_type=operate_nodes, help="")
        def add_operation_image(node, **kwargs):
            append_operation_image(node, pos=add_after_index(self), **kwargs)

        @self.tree_submenu(_("Add operation"))
        @self.tree_operation(_("Add Raster"), node_type=operate_nodes, help="")
        def add_operation_raster(node, **kwargs):
            append_operation_raster(node, pos=add_after_index(self), **kwargs)

        @self.tree_submenu(_("Add operation"))
        @self.tree_operation(_("Add Engrave"), node_type=operate_nodes, help="")
        def add_operation_engrave(node, **kwargs):
            append_operation_engrave(node, pos=add_after_index(self), **kwargs)

        @self.tree_submenu(_("Add operation"))
        @self.tree_operation(_("Add Cut"), node_type=operate_nodes, help="")
        def add_operation_cut(node, **kwargs):
            append_operation_cut(node, pos=add_after_index(self), **kwargs)

        @self.tree_submenu(_("Add special operation(s)"))
        @self.tree_operation(_("Add Home"), node_type=op_nodes, help="")
        def add_operation_home(node, **kwargs):
            append_operation_home(node, pos=add_after_index(self), **kwargs)

        @self.tree_submenu(_("Add special operation(s)"))
        @self.tree_operation(_("Add Return to Origin"), node_type=op_nodes, help="")
        def add_operation_origin(node, **kwargs):
            append_operation_origin(node, pos=add_after_index(self), **kwargs)

        @self.tree_submenu(_("Add special operation(s)"))
        @self.tree_operation(_("Add Beep"), node_type=op_nodes, help="")
        def add_operation_beep(node, **kwargs):
            append_operation_beep(node, pos=add_after_index(self), **kwargs)

        @self.tree_submenu(_("Add special operation(s)"))
        @self.tree_operation(_("Add Interrupt"), node_type=op_nodes, help="")
        def add_operation_interrupt(node, **kwargs):
            append_operation_interrupt(node, pos=add_after_index(self), **kwargs)

        @self.tree_submenu(_("Add special operation(s)"))
        @self.tree_operation(_("Add Interrupt (console)"), node_type=op_nodes, help="")
        def add_operation_interrupt_console(node, **kwargs):
            append_operation_interrupt_console(
                node, pos=add_after_index(self), **kwargs
            )

        @self.tree_submenu(_("Add special operation(s)"))
        @self.tree_operation(_("Add Home/Beep/Interrupt"), node_type=op_nodes, help="")
        def add_operation_home_beep_interrupt(node, **kwargs):
            pos = add_after_index(self)
            append_operation_home(node, pos=pos, **kwargs)
            if pos:
                pos += 1
            append_operation_beep(node, pos=pos, **kwargs)
            if pos:
                pos += 1
            append_operation_interrupt(node, pos=pos, **kwargs)

        @self.tree_operation(_("Reload '%s'") % "{name}", node_type="file", help="")
        def reload_file(node, **kwargs):
            filepath = node.filepath
            node.remove_node()
            self.load(filepath)

        @self.tree_operation(
            _("Open in System: '{name}'"),
            node_type="file",
            help=_(
                "Open this file in the system application associated with this type of file"
            ),
        )
        def open_system_file(node, **kwargs):
            filepath = node.filepath
            normalized = os.path.realpath(filepath)

            import platform

            system = platform.system()
            if system == "Darwin":
                from os import system as open_in_shell

                open_in_shell("open '{file}'".format(file=normalized))
            elif system == "Windows":
                from os import startfile as open_in_shell

                open_in_shell('"{file}"'.format(file=normalized))
            else:
                from os import system as open_in_shell

                open_in_shell("xdg-open '{file}'".format(file=normalized))

        @self.tree_submenu(_("Duplicate element(s)"))
        @self.tree_operation(_("Make 1 copy"), node_type="elem", help="")
        def duplicate_element_1(node, **kwargs):
            duplicate_element_n(node, copies=1, **kwargs)

        @self.tree_submenu(_("Duplicate element(s)"))
        @self.tree_iterate("copies", 2, 10)
        @self.tree_operation(
            _("Make %s copies") % "{copies}", node_type="elem", help=""
        )
        def duplicate_element_n(node, copies, **kwargs):
            adding_elements = [
                copy(e) for e in list(self.elems(emphasized=True)) * copies
            ]
            self.add_elems(adding_elements)
            self.classify(adding_elements)
            self.set_emphasis(None)

        @self.tree_conditional(
            lambda node: isinstance(node.object, Shape)
            and not isinstance(node.object, Path)
        )
        @self.tree_operation(_("Convert to path"), node_type=("elem",), help="")
        def convert_to_path(node, copies=1, **kwargs):
            node.replace_object(abs(Path(node.object)))
            node.altered()

        @self.tree_submenu(_("Flip"))
        @self.tree_separator_before()
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(
            _("Horizontally"),
            node_type=("elem", "group", "file"),
            help=_("Mirror Horizontally"),
        )
        def mirror_elem(node, **kwargs):
            child_objects = Group()
            child_objects.extend(node.objects_of_children(SVGElement))
            bounds = child_objects.bbox()
            if bounds is None:
                return
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            self("scale -1 1 %f %f\n" % (center_x, center_y))

        @self.tree_submenu(_("Flip"))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(
            _("Vertically"),
            node_type=("elem", "group", "file"),
            help=_("Flip Vertically"),
        )
        def flip_elem(node, **kwargs):
            child_objects = Group()
            child_objects.extend(node.objects_of_children(SVGElement))
            bounds = child_objects.bbox()
            if bounds is None:
                return
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            self("scale 1 -1 %f %f\n" % (center_x, center_y))

        # @self.tree_conditional(lambda node: isinstance(node.object, SVGElement))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Scale"))
        @self.tree_iterate("scale", 25, 1, -1)
        @self.tree_calc("scale_percent", lambda i: "%0.f" % (600.0 / float(i)))
        @self.tree_operation(
            _("Scale %s%%") % "{scale_percent}",
            node_type=("elem", "group", "file"),
            help=_("Scale Element"),
        )
        def scale_elem_amount(node, scale, **kwargs):
            scale = 6.0 / float(scale)
            child_objects = Group()
            child_objects.extend(node.objects_of_children(SVGElement))
            bounds = child_objects.bbox()
            if bounds is None:
                return
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            self("scale %f %f %f %f\n" % (scale, scale, center_x, center_y))

        # @self.tree_conditional(lambda node: isinstance(node.object, SVGElement))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_submenu(_("Rotate"))
        @self.tree_values(
            "angle",
            (
                180,
                150,
                135,
                120,
                90,
                60,
                45,
                30,
                20,
                15,
                10,
                9,
                8,
                7,
                6,
                5,
                4,
                3,
                2,
                1,
                -1,
                -2,
                -3,
                -4,
                -5,
                -6,
                -7,
                -8,
                -9,
                -10,
                -15,
                -20,
                -30,
                -45,
                -60,
                -90,
                -120,
                -135,
                -150,
            ),
        )
        @self.tree_operation(
            _("Rotate %s°") % ("{angle}"), node_type=("elem", "group", "file"), help=""
        )
        def rotate_elem_amount(node, angle, **kwargs):
            turns = float(angle) / 360.0
            child_objects = Group()
            child_objects.extend(node.objects_of_children(SVGElement))
            bounds = child_objects.bbox()
            if bounds is None:
                return
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            self("rotate %fturn %f %f\n" % (turns, center_x, center_y))

        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(
            _("Reify User Changes"), node_type=("elem", "group", "file"), help=""
        )
        def reify_elem_changes(node, **kwargs):
            self("reify\n")

        @self.tree_conditional(lambda node: isinstance(node.object, Path))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(_("Break Subpaths"), node_type="elem", help="")
        def break_subpath_elem(node, **kwargs):
            self("element subpath\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGElement))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(
            _("Reset user changes"), node_type=("branch elem", "elem"), help=""
        )
        def reset_user_changes(node, copies=1, **kwargs):
            self("reset\n")

        @self.tree_operation(
            _("Merge items"),
            node_type="group",
            help=_("Merge this node's children into 1 path."),
        )
        def merge_elements(node, **kwargs):
            self("element merge\n")

        def radio_match(node, i=0, **kwargs):
            if "raster_step" in node.object.values:
                step = float(node.object.values["raster_step"])
            else:
                step = 1.0
            if i == step:
                m = node.object.transform
                if m.a == step or m.b == 0.0 or m.c == 0.0 or m.d == step:
                    return True
            return False

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_separator_before()
        @self.tree_submenu(_("Step"))
        @self.tree_radio(radio_match)
        @self.tree_iterate("i", 1, 10)
        @self.tree_operation(_("Step %s") % "{i}", node_type="elem", help="")
        def set_step_n_elem(node, i=1, **kwargs):
            step_value = i
            element = node.object
            element.values["raster_step"] = str(step_value)
            m = element.transform
            tx = m.e
            ty = m.f
            element.transform = Matrix.scale(float(step_value), float(step_value))
            element.transform.post_translate(tx, ty)
            if hasattr(element, "node"):
                element.node.modified()
            self.signal("element_property_reload", node.object)

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_conditional_try(lambda node: not node.object.lock)
        @self.tree_operation(_("Actualize pixels"), node_type="elem", help="")
        def image_actualize_pixels(node, **kwargs):
            self("image resample\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Z-depth divide"))
        @self.tree_iterate("divide", 2, 10)
        @self.tree_operation(
            _("Divide into %s images") % "{divide}", node_type="elem", help=""
        )
        def image_zdepth(node, divide=1, **kwargs):
            element = node.object
            if not isinstance(element, SVGImage):
                return
            if element.image.mode != "RGBA":
                element.image = element.image.convert("RGBA")
            band = 255 / divide
            for i in range(0, divide):
                threshold_min = i * band
                threshold_max = threshold_min + band
                self("image threshold %f %f\n" % (threshold_min, threshold_max))

        def is_locked(node):
            try:
                obj = node.object
                return obj.lock
            except AttributeError:
                return False

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_conditional(is_locked)
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Unlock manipulations"), node_type="elem", help="")
        def image_unlock_manipulations(node, **kwargs):
            self("image unlock\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Dither to 1 bit"), node_type="elem", help="")
        def image_dither(node, **kwargs):
            self("image dither\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Invert image"), node_type="elem", help="")
        def image_invert(node, **kwargs):
            self("image invert\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Mirror horizontal"), node_type="elem", help="")
        def image_mirror(node, **kwargs):
            self("image mirror\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Flip vertical"), node_type="elem", help="")
        def image_flip(node, **kwargs):
            self("image flip\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Rotate 90° CW"), node_type="elem", help="")
        def image_cw(node, **kwargs):
            self("image cw\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Rotate 90° CCW"), node_type="elem", help="")
        def image_ccw(node, **kwargs):
            self("image ccw\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Image"))
        @self.tree_operation(_("Save output.png"), node_type="elem", help="")
        def image_save(node, **kwargs):
            self("image save output.png\n")

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("RasterWizard"))
        @self.tree_values(
            "script", values=list(self.match("raster_script", suffix=True))
        )
        @self.tree_operation(
            _("RasterWizard: %s") % "{script}", node_type="elem", help=""
        )
        def image_rasterwizard_open(node, script=None, **kwargs):
            self("window open RasterWizard %s\n" % script)

        @self.tree_conditional(lambda node: isinstance(node.object, SVGImage))
        @self.tree_submenu(_("Apply raster script"))
        @self.tree_values(
            "script", values=list(self.match("raster_script", suffix=True))
        )
        @self.tree_operation(_("Apply: %s") % "{script}", node_type="elem", help="")
        def image_rasterwizard_apply(node, script=None, **kwargs):
            self("image wizard %s\n" % script)

        @self.tree_conditional_try(lambda node: hasattr(node.object, "as_elements"))
        @self.tree_operation(_("Convert to SVG"), node_type="elem", help="")
        def cutcode_convert_svg(node, **kwargs):
            self.add_elems(list(node.object.as_elements()))

        @self.tree_conditional_try(lambda node: hasattr(node.object, "generate"))
        @self.tree_operation(_("Process as Operation"), node_type="elem", help="")
        def cutcode_operation(node, **kwargs):
            self.add_op(node.object)

        @self.tree_conditional(lambda node: len(node.children) > 0)
        @self.tree_separator_before()
        @self.tree_operation(
            _("Expand all children"),
            node_type=(
                "op cut",
                "op raster",
                "op image",
                "op engrave",
                "op dots",
                "branch elems",
                "branch ops",
                "group",
                "file",
                "root",
            ),
            help="Expand all children of this given node.",
        )
        def expand_all_children(node, **kwargs):
            node.notify_expand()

        @self.tree_conditional(lambda node: len(node.children) > 0)
        @self.tree_operation(
            _("Collapse all children"),
            node_type=(
                "op cut",
                "op raster",
                "op image",
                "op engrave",
                "op dots",
                "branch elems",
                "branch ops",
                "group",
                "file",
                "root",
            ),
            help="Collapse all children of this given node.",
        )
        def collapse_all_children(node, **kwargs):
            node.notify_collapse()

        @self.tree_reference(lambda node: node.object.node)
        @self.tree_operation(_("Element"), node_type="ref elem", help="")
        def reference_refelem(node, **kwargs):
            pass

    def service_detach(self, *args, **kwargs):
        self.unlisten_tree(self)

    def service_attach(self, *args, **kwargs):
        self.listen_tree(self)

    def shutdown(self, *args, **kwargs):
        self.save_persistent_operations("previous")
        self.op_data.write_configuration()
        for e in self.flat():
            e.unregister()

    def save_persistent_operations(self, name):
        settings = self.op_data
        settings.clear_persistent(name)
        for i, op in enumerate(self.ops()):
            section = "%s %06i" % (name, i)
            settings.write_persistent(section, "type", op.type)
            op.save(settings, section)

        settings.write_configuration()

    def clear_persistent_operations(self, name):
        settings = self.op_data
        subitems = list(settings.derivable(name))
        for section in subitems:
            settings.clear_persistent(section)
        settings.write_configuration()

    def load_persistent_operations(self, name):
        self.clear_operations()
        settings = self.op_data
        subitems = list(settings.derivable(name))
        operation_branch = self._tree.get(type="branch ops")
        for section in subitems:
            op_type = settings.read_persistent(str, section, "type")
            if op_type in ("op", "ref elem"):
                continue
            op = operation_branch.add(None, type=op_type)
            op.load(settings, section)
        self.classify(list(self.elems()))

    def emphasized(self, *args):
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None

    def altered(self, *args):
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None

    def modified(self, *args):
        self._emphasized_bounds_dirty = True
        self._emphasized_bounds = None

    def listen_tree(self, listener):
        self._tree.listen(listener)

    def unlisten_tree(self, listener):
        self._tree.unlisten(listener)

    def add_element(self, element, stroke="black"):
        if (
            not isinstance(element, SVGText)
            and hasattr(element, "__len__")
            and len(element) == 0
        ):
            return  # No empty elements.
        if hasattr(element, "stroke") and element.stroke is None:
            element.stroke = Color(stroke)
        node = self.add_elem(element)
        self.set_emphasis([element])
        node.focus()
        return node

    def load_default(self):
        self.clear_operations()
        self.add_op(
            ImageOpNode(
                color="black",
                speed=140.0,
                power=1000.0,
                raster_step=3,
            )
        )
        self.add_op(RasterOpNode())
        self.add_op(EngraveOpNode())
        self.add_op(CutOpNode())
        self.classify(list(self.elems()))

    def load_default2(self):
        self.clear_operations()
        self.add_op(
            ImageOpNode(
                color="black",
                speed=140.0,
                power=1000.0,
                raster_step=3,
            )
        )
        self.add_op(RasterOpNode())
        self.add_op(EngraveOpNode(color="blue"))
        self.add_op(EngraveOpNode(color="green"))
        self.add_op(EngraveOpNode(color="magenta"))
        self.add_op(EngraveOpNode(color="cyan"))
        self.add_op(EngraveOpNode(color="yellow"))
        self.add_op(CutOpNode())
        self.classify(list(self.elems()))

    def tree_operations_for_node(self, node):
        for func, m, sname in self.find("tree", node.type, ".*"):
            reject = False
            for cond in func.conditionals:
                if not cond(node):
                    reject = True
                    break
            if reject:
                continue
            for cond in func.try_conditionals:
                try:
                    if not cond(node):
                        reject = True
                        break
                except Exception:
                    continue
            if reject:
                continue
            func_dict = {
                "name": label_truncate_re.sub("", str(node.label)),
                "label": str(node.label),
            }

            iterator = func.values
            if iterator is None:
                iterator = [0]
            else:
                try:
                    iterator = list(iterator())
                except TypeError:
                    pass
            for i, value in enumerate(iterator):
                func_dict["iterator"] = i
                func_dict["value"] = value
                try:
                    func_dict[func.value_name] = value
                except AttributeError:
                    pass

                for calc in func.calcs:
                    key, c = calc
                    value = c(value)
                    func_dict[key] = value
                if func.radio is not None:
                    try:
                        func.radio_state = func.radio(node, **func_dict)
                    except:
                        func.radio_state = False
                else:
                    func.radio_state = None
                name = func.name.format_map(func_dict)
                func.func_dict = func_dict
                func.real_name = name

                yield func

    def flat(self, **kwargs):
        yield from self._tree.flat(**kwargs)

    @staticmethod
    def tree_calc(value_name, calc_func):
        def decor(func):
            func.calcs.append((value_name, calc_func))
            return func

        return decor

    @staticmethod
    def tree_values(value_name, values):
        def decor(func):
            func.value_name = value_name
            func.values = values
            return func

        return decor

    @staticmethod
    def tree_iterate(value_name, start, stop, step=1):
        def decor(func):
            func.value_name = value_name
            func.values = range(start, stop, step)
            return func

        return decor

    @staticmethod
    def tree_radio(radio_function):
        def decor(func):
            func.radio = radio_function
            return func

        return decor

    @staticmethod
    def tree_submenu(submenu):
        def decor(func):
            func.submenu = submenu
            return func

        return decor

    @staticmethod
    def tree_prompt(attr, prompt, data_type=str):
        def decor(func):
            func.user_prompt.append(
                {
                    "attr": attr,
                    "prompt": prompt,
                    "type": data_type,
                }
            )
            return func

        return decor

    @staticmethod
    def tree_conditional(conditional):
        def decor(func):
            func.conditionals.append(conditional)
            return func

        return decor

    @staticmethod
    def tree_conditional_try(conditional):
        def decor(func):
            func.try_conditionals.append(conditional)
            return func

        return decor

    @staticmethod
    def tree_reference(node):
        def decor(func):
            func.reference = node
            return func

        return decor

    @staticmethod
    def tree_separator_after():
        def decor(func):
            func.separate_after = True
            return func

        return decor

    @staticmethod
    def tree_separator_before():
        def decor(func):
            func.separate_before = True
            return func

        return decor

    def tree_operation(self, name, node_type=None, help=None, **kwargs):
        def decorator(func):
            @functools.wraps(func)
            def inner(node, **ik):
                returned = func(node, **ik, **kwargs)
                return returned

            if isinstance(node_type, tuple):
                ins = node_type
            else:
                ins = (node_type,)

            # inner.long_help = func.__doc__
            inner.help = help
            inner.node_type = ins
            inner.name = name
            inner.radio = None
            inner.submenu = None
            inner.reference = None
            inner.separate_after = False
            inner.separate_before = False
            inner.conditionals = list()
            inner.try_conditionals = list()
            inner.user_prompt = list()
            inner.calcs = list()
            inner.values = [0]
            registered_name = inner.__name__

            for _in in ins:
                p = "tree/%s/%s" % (_in, registered_name)
                if p in self._registered:
                    raise NameError(
                        "A function of this name was already registered: %s" % p
                    )
                self.register(p, inner)
            return inner

        return decorator

    @property
    def op_branch(self):
        return self._tree.get(type="branch ops")

    @property
    def elem_branch(self):
        return self._tree.get(type="branch elems")

    def ops(self, **kwargs):
        operations = self._tree.get(type="branch ops")
        for item in operations.flat(depth=1, **kwargs):
            if item.type.startswith("branch") or item.type.startswith("ref"):
                continue
            yield item

    def elems(self, **kwargs):
        elements = self._tree.get(type="branch elems")
        for item in elements.flat(types=("elem",), **kwargs):
            yield item.object

    def elems_nodes(self, depth=None, **kwargs):
        elements = self._tree.get(type="branch elems")
        for item in elements.flat(
            types=("elem", "group", "file"), depth=depth, **kwargs
        ):
            yield item

    def top_element(self, **kwargs):
        """
        Returns the first matching node via a depth first search.
        """
        for e in self.elem_branch.flat(**kwargs):
            return e
        return None

    def first_element(self, **kwargs):
        """
        Returns the first matching element node via a depth first search. Elements must be type elem.
        """
        for e in self.elems(**kwargs):
            return e
        return None

    def has_emphasis(self):
        """
        Returns whether any element is emphasized
        """
        for e in self.elems_nodes(emphasized=True):
            return True
        return False

    def count_elems(self, **kwargs):
        return len(list(self.elems(**kwargs)))

    def count_op(self, **kwargs):
        return len(list(self.ops(**kwargs)))

    def get(self, obj=None, type=None):
        return self._tree.get(obj=obj, type=type)

    def get_op(self, index, **kwargs):
        for i, op in enumerate(self.ops(**kwargs)):
            if i == index:
                return op
        raise IndexError

    def get_elem(self, index, **kwargs):
        for i, elem in enumerate(self.elems(**kwargs)):
            if i == index:
                return elem
        raise IndexError

    def get_elem_node(self, index, **kwargs):
        for i, elem in enumerate(self.elems_nodes(**kwargs)):
            if i == index:
                return elem
        raise IndexError

    def add_op(self, op, pos=None):
        """
        Add an operation. Wraps it within a node, and appends it to the tree.

        :param element:
        :param classify: Should this element be automatically classified.
        :return:
        """
        operation_branch = self._tree.get(type="branch ops")
        op.set_label(str(op))
        operation_branch.add(op, type=op.type, pos=pos)

    def add_ops(self, adding_ops):
        operation_branch = self._tree.get(type="branch ops")
        items = []
        for op in adding_ops:
            op.set_label(str(op))
            operation_branch.add(op, type=op.type)
            items.append(op)
        return items

    def add_elem(self, element, classify=False):
        """
        Add an element. Wraps it within a node, and appends it to the tree.

        :param element:
        :param classify: Should this element be automatically classified.
        :return:
        """
        element_branch = self._tree.get(type="branch elems")
        node = element_branch.add(element, type="elem")
        self.signal("element_added", element)
        if classify:
            self.classify([element])
        return node

    def add_elems(self, adding_elements):
        element_branch = self._tree.get(type="branch elems")
        items = []
        for element in adding_elements:
            items.append(element_branch.add(element, type="elem"))
        self.signal("element_added", adding_elements)
        return items

    def clear_operations(self):
        operations = self._tree.get(type="branch ops")
        operations.remove_all_children()

    def clear_elements(self):
        elements = self._tree.get(type="branch elems")
        elements.remove_all_children()

    def clear_files(self):
        pass

    def clear_elements_and_operations(self):
        self.clear_elements()
        self.clear_operations()

    def clear_all(self):
        self.clear_elements()
        self.clear_operations()
        self.clear_files()
        self.clear_note()
        self.validate_selected_area()

    def clear_note(self):
        self.note = None

    def remove_elements(self, elements_list):
        for elem in elements_list:
            for i, e in enumerate(self.elems()):
                if elem is e:
                    e.node.remove_node()
        self.remove_elements_from_operations(elements_list)
        self.validate_selected_area()

    def remove_operations(self, operations_list):
        for op in operations_list:
            for i, o in enumerate(list(self.ops())):
                if o is op:
                    o.remove_node()
            self.signal("operation_removed", op)

    def remove_elements_from_operations(self, elements_list):
        for i, op in enumerate(self.ops()):
            for e in list(op.children):
                for q in elements_list:
                    if q is e.object:
                        e.remove_node()
                        break

    def selected_area(self):
        if self._emphasized_bounds_dirty:
            self.validate_selected_area()
        return self._emphasized_bounds

    def validate_selected_area(self):
        boundary_points = []
        for e in self.elem_branch.flat(
            types="elem",
            emphasized=True,
        ):
            if e.bounds is None:
                continue
            box = e.bounds
            top_left = [box[0], box[1]]
            top_right = [box[2], box[1]]
            bottom_left = [box[0], box[3]]
            bottom_right = [box[2], box[3]]
            boundary_points.append(top_left)
            boundary_points.append(top_right)
            boundary_points.append(bottom_left)
            boundary_points.append(bottom_right)

        if len(boundary_points) == 0:
            new_bounds = None
        else:
            xmin = min([e[0] for e in boundary_points])
            ymin = min([e[1] for e in boundary_points])
            xmax = max([e[0] for e in boundary_points])
            ymax = max([e[1] for e in boundary_points])
            new_bounds = [xmin, ymin, xmax, ymax]
        self._emphasized_bounds_dirty = False
        if self._emphasized_bounds != new_bounds:
            self._emphasized_bounds = new_bounds
            self.signal("selected_bounds", self._emphasized_bounds)

    def highlight_children(self, node_context):
        """
        Recursively highlight the children.
        :param node_context:
        :return:
        """
        for child in node_context.children:
            child.highlighted = True
            self.highlight_children(child)

    def target_clones(self, node_context, node_exclude, object_search):
        """
        Recursively highlight the children.

        :param node_context: context node to search from
        :param node_exclude: excluded nodes
        :param object_search: Specific searched for object.
        :return:
        """
        for child in node_context.children:
            self.target_clones(child, node_exclude, object_search)
            if child is node_exclude:
                continue
            if child.object is None:
                continue
            if object_search is child.object:
                child.targeted = True

    def set_selected(self, selected):
        """
        Selected is the sublist of specifically selected nodes.
        """
        for s in self._tree.flat():
            in_list = selected is not None and (
                s in selected or (hasattr(s, "object") and s.object in selected)
            )
            if s.selected:
                if not in_list:
                    s.selected = False
            else:
                if in_list:
                    s.selected = True
        if selected is not None:
            for e in selected:
                e.selected = True

    def set_emphasis(self, emphasize):
        """
        If any operation is selected, all sub-operations are highlighted.
        If any element is emphasized, all copies are highlighted.
        If any element is emphasized, all operations containing that element are targeted.
        """
        for s in self._tree.flat():
            if s.highlighted:
                s.highlighted = False
            if s.targeted:
                s.targeted = False

            in_list = emphasize is not None and (
                s in emphasize or (hasattr(s, "object") and s.object in emphasize)
            )
            if s.emphasized:
                if not in_list:
                    s.emphasized = False
            else:
                if in_list:
                    s.emphasized = True
        if emphasize is not None:
            for e in emphasize:
                e.emphasized = True
                if hasattr(e, "object"):
                    self.target_clones(self._tree, e, e.object)
                if hasattr(e, "node"):
                    e = e.node
                self.highlight_children(e)

    def center(self):
        bounds = self._emphasized_bounds
        return (bounds[2] + bounds[0]) / 2.0, (bounds[3] + bounds[1]) / 2.0

    def ensure_positive_bounds(self):
        b = self._emphasized_bounds
        if b is None:
            return
        self._emphasized_bounds = [
            min(b[0], b[2]),
            min(b[1], b[3]),
            max(b[0], b[2]),
            max(b[1], b[3]),
        ]
        self.signal("selected_bounds", self._emphasized_bounds)

    def update_bounds(self, b):
        self._emphasized_bounds = [b[0], b[1], b[2], b[3]]
        self.signal("selected_bounds", self._emphasized_bounds)

    def move_emphasized(self, dx, dy):
        for obj in self.elems(emphasized=True):
            obj.transform.post_translate(dx, dy)
            obj.node.modified()

    def set_emphasized_by_position(self, position):
        def contains(box, x, y=None):
            if y is None:
                y = x[1]
                x = x[0]
            return box[0] <= x <= box[2] and box[1] <= y <= box[3]

        if self.has_emphasis():
            if self._emphasized_bounds is not None and contains(
                self._emphasized_bounds, position
            ):
                return  # Select by position aborted since selection position within current select bounds.
        for e in self.elems_nodes(depth=1, cascade=False):
            try:
                bounds = e.bounds
            except AttributeError:
                continue  # No bounds.
            if bounds is None:
                continue
            if contains(bounds, position):
                e_list = [e]
                self._emphasized_bounds = bounds
                self.set_emphasis(e_list)
                return
        self._emphasized_bounds = None
        self.set_emphasis(None)

    def classify_legacy(self, elements, operations=None, add_op_function=None):
        """
        Classify does the placement of elements within operations.
        "Image" is the default for images.
        Typically,
        If element strokes are red they get classed as cut operations
        If they are otherwise they get classed as engrave.
        However, this differs based on the ops in question.
        :param elements: list of elements to classify.
        :param operations: operations list to classify into.
        :param add_op_function: function to add a new operation, because of a lack of classification options.
        :return:
        """
        if elements is None:
            return

        # Use of Classify in reverse is new functionality in 0.7.1
        # So using it is incompatible, but not using it would be inconsistent
        # Perhaps classify_reverse should be cleared and disabled if classify_legacy is set.
        reverse = self.classify_reverse
        if reverse:
            elements = reversed(elements)
        if operations is None:
            operations = list(self.ops())
        if add_op_function is None:
            add_op_function = self.add_op
        for element in elements:
            # Following lines added to handle 0.7 special ops added to ops list
            if hasattr(element, "operation"):
                add_op_function(element)
                continue
            # Following lines added that are not in 0.6
            if element is None:
                continue
            was_classified = False
            # image_added code removed because it could never be used
            for op in operations:
                if op.type == "op raster" and not op.default:
                    if element.stroke is not None and op.color == abs(element.stroke):
                        op.add(element, type="ref elem")
                        was_classified = True
                    elif isinstance(element, SVGImage):
                        op.add(element, type="ref elem")
                        was_classified = True
                    elif isinstance(element, SVGText):
                        op.add(element)
                        was_classified = True
                    elif element.fill is not None and element.fill.argb is not None:
                        op.add(element, type="ref elem")
                        was_classified = True
                elif (
                    op.type in ("op engrave", "op cut")
                    and element.stroke is not None
                    and op.color == abs(element.stroke)
                    and not op.default
                ):
                    op.add(element, type="ref elem")
                    was_classified = True
                elif op.type == "op image" and isinstance(element, SVGImage):
                    op.add(element, type="ref elem")
                    was_classified = True
                    break  # May only classify in one image operation.
                elif op.type == "op dots" and is_dot(element):
                    op.add(element, type="ref elem")
                    was_classified = True
                    break  # May only classify in Dots.

            if not was_classified:
                # Additional code over and above 0.6.23 to add new DISABLED operations
                # so that all elements are classified.
                # This code definitely classifies more elements, and should classify all, however
                # it is not guaranteed to classify all elements as this is not explicitly checked.
                op = None
                if isinstance(element, SVGImage):
                    op = ImageOpNode(output=False)
                elif is_dot(element):
                    op = DotsOpNode(output=False)
                elif (
                    # test for Shape or SVGText instance is probably unnecessary,
                    # but we should probably not test for stroke without ensuring
                    # that the object has a stroke attribute.
                    isinstance(element, (Shape, SVGText))
                    and element.stroke is not None
                    and element.stroke.value is not None
                ):
                    op = EngraveOpNode(color=element.stroke, speed=35.0)
                # This code is separated out to avoid duplication
                if op is not None:
                    add_op_function(op)
                    op.add(element, type="ref elem")
                    operations.append(op)

                # Seperate code for Raster ops because we might add a Raster op
                # and a vector op for same element.
                if (
                    isinstance(element, (Shape, SVGText))
                    and element.fill is not None
                    and element.fill.argb is not None
                    and not is_dot(element)
                ):
                    op = RasterOpNode(color=0, output=False)
                    add_op_function(op)
                    op.add(element, type="ref elem")
                    operations.append(op)

    def add_classify_op(self, op):
        """
        Ops are added as part of classify as elements are iterated that need a new op.
        Rather than add them at the end, creating a random sequence of Engrave and Cut operations
        perhaps with an Image or Raster or Dots operation in there as well, instead  we need to try
        to group operations together, adding the new operation:
        1. After the last operation of the same type if one exists; or if not
        2. After the last operation of the highest priority existing operation (where Dots is the lowest priority and Cut is the highest.
        """
        operations = self._tree.get(type="branch ops").children
        for pos, old_op in reversed_enumerate(operations):
            if op.type == old_op.type:
                return self.add_op(op, pos=pos + 1)

        # No operation of same type found. So we will look for last operation of a lower priority and add after it.
        try:
            priority = OP_PRIORITIES.index(op.type)
        except ValueError:
            return self.add_op(op)

        for pos, old_op in reversed_enumerate(operations):
            try:
                if OP_PRIORITIES.index(old_op.type) < priority:
                    return self.add_op(op, pos=pos + 1)
            except ValueError:
                pass
        return self.add_op(op, pos=0)

    def classify(self, elements, operations=None, add_op_function=None):
        """
        Classify does the placement of elements within operations.
        In the future, we expect to be able to save and reload the mapping of
        elements to operations, but at present classification is the only means
        of assigning elements to operations.

        This classification routine ensures that every element is assigned
        to at least one operation - the user does NOT have to check whether
        some elements have not been assigned (which was an issue with 0.6.x).

        Because of how overlaying raster elements can have white areas masking
        underlying non-white areas, the classification of raster elements is complex,
        and indeed deciding whether elements should be classified as vector or raster
        has edge case complexities.

        SVGImage is classified as Image.
        Dots are a special type of Path
        All other SVGElement types are Shapes / Text

        Paths consisting of a move followed by a single stright line segment
        are never Raster (since no width) - testing for more complex stright line
        path-segments and that multiple-such-segments are also straight-line is complex,

        Shapes/Text with grey (R=G=B) strokes are raster by default regardless of fill

        Shapes/Text with non-transparent Fill are raster by default - except for one
        edge case: Elements with white fill, non-grey stroke and no raster elements behind
        them are considered vector elements.

        Shapes/Text with no fill and non-grey strokes are vector by default - except
        for one edge case: Elements with strokes that have other raster elements
        overlaying the stroke should in some cases be considered raster elements,
        but there are serveral use cases and counter examples are likely easy to create.
        The algorithm below tries to be conservative in deciding whether to switch a default
        vector to a raster due to believing it is part of raster combined with elements on top.
        In essence, if there are raster elements on top (later in the list of elements) that
        have the given vector element's stroke colour as either a stroke or fill colour, then the
        probability is that this vector element should be considered a raster instead.

        RASTER ELEMENTS
        Because rastering of overlapping elements depends on the sequence of the elements
        (think of the difference between a white fill above or below a black fill)
        it is essential that raster elements are added to operations in the same order
        that they exist in the file/elements branch.

        Raster elements are handled differently depending on whether existing
        Raster operations are simple or complex:
            1.  Simple - all existing raster ops have the same color
                (default being a different colour to any other); or
            2.  Complex - there are existing raster ops of two different colors
                (default being a different colour to any other)

        Simple - Raster elements are matched immediately to all Raster operations.
        Complex - Raster elements are processed in a more complex second pass (see below)

        VECTOR ELEMENTS
        Vector Shapes/Text are attempted to match to Cut/Engrave/Raster operations of
        exact same color (regardless of default raster or vector)

        If not matched to exact colour, vector elements are classified based on colour:
            1. Redish strokes are considered cuts
            2. Other colours are considered engraves
        If a default Cut/Engrave operation exists then the element is classified to it.
        Otherwise a new operation of matching color and type is created.
        New White Engrave operations are created disabled by default.

        SIMPLE RASTER CLASSIFICATION
        All existing raster ops are of the same color (or there are no existing raster ops)

        In this case all raster operations will be assigned either to:
            A. all existing raster ops (if there are any); or
            B. to a new Default Raster operation we create in a similar way as vector elements

        Because raster elements are all added to the same operations in pass 1 and without being
        grouped, the sequence of elements is retained by default, and no special handling is needed.

        COMPLEX RASTER CLASSIFICATION
        There are existing raster ops of at least 2 different colours.

        In this case we are going to try to match raster elements to raster operations by colour.
        But this is complicated as we need to keep overlapping raster elements together in the
        sae operations because raster images are generated within each operation.

        So in this case we classify vector and special elements in a first pass,
        and then analyse and classify raster operations in a special second pass.

        Because we have to analyse all raster elements together, when you load a new file
        Classify has to be called once with all elements in the file
        rather than on an element-by-element basis.

        In the second pass, we do the following:

        1.  Group rasters by whether they have overlapping bounding boxes.
            After this, if rasters are in separate groups then they are in entirely separate
            areas of the burn which do not overlap. Consequently they can be allocated
            to different operations without causing incorrect results.

            Note 1: It is difficult to ensure that elements are retained in sequence when doing
            grouping. Before adding to the raster operations, we sort back into the
            original element sequence.

            Note 2: The current algorithm uses bounding-boxes. One edge case is to have two
            separate raster patterns of different colours that do NOT overlap but whose
            bounding-boxes DO overlap. In these cases they will both be allocated to the same
            raster Operations whereas they potentially could be allocated to different Operations.

        2.  For each group of raster objects, determine whether there are existing Raster operations
            of the same colour as at least one element in the group.
            If any element in a group matches the color of an operation, then
            all the raster elements of the group will be added to that operation.

        3.  If there are any raster elements that are not classified in this way, then:
            A)  If there are Default Raster Operation(s), then the remaining raster elements are
                allocated to those.
            B)  Otherwise, if there are any non-default raster operations that are empty and those
                raster operations are all of the same colour, then the remaining raster operations
                will be allocated to those Raster operations.
            C)  Otherwise, a new Default Raster operation will be created and remaining
                Raster elements will be added to that.

        LIMITATIONS: The current code does NOT do the following:

        a.  Handle rasters in second or later files which overlap elements from earlier files which
            have already been classified into operations. It is assumed that if they happen to
            overlap that is coincidence. After all the files could have been added in a different
            order and then would have a different result.
        b.  Handle the reclassifications of single elements which have e.g. had their colour
            changed. (The multitude of potential use cases are many and varied, and difficult or
            impossible comprehensively to predict.)

        It may be that we will need to:

        1.  Use the total list of Shape / Text elements loaded in the Elements Branch sequence
            to keep elements in the correct sequence in an operation.
        2.  Handle cases where the user resequences elements by ensuring that a drag and drop
            of elements in the Elements branch of the tree is reflected in the sequence in Operations
            and vice versa. This could, however, get messy.


        :param elements: list of elements to classify.
        :param operations: operations list to classify into.
        :param add_op_function: function to add a new operation, because of a lack of classification options.
        :return:
        """
        debug = self.kernel.channel("classify", timestamp=True)

        if self.legacy_classification:
            debug("classify: legacy")
            self.classify_legacy(elements, operations, add_op_function)
            return

        if elements is None:
            return

        if operations is None:
            operations = list(self.ops())
        if add_op_function is None:
            add_op_function = self.add_classify_op

        reverse = self.classify_reverse
        # If reverse then we insert all elements into operations at the beginning rather than appending at the end
        # EXCEPT for Rasters which have to be in the correct sequence.
        element_pos = 0 if reverse else None

        vector_ops = []
        raster_ops = []
        special_ops = []
        new_ops = []
        default_cut_ops = []
        default_engrave_ops = []
        default_raster_ops = []
        rasters_one_pass = None

        for op in operations:
            if not op.type.startswith("op "):
                continue
            if op.default:
                if op.type == "op cut":
                    default_cut_ops.append(op)
                if op.type == "op engrave":
                    default_engrave_ops.append(op)
                if op.type == "op raster":
                    default_raster_ops.append(op)
            if op.type in ("op cut", "op engrave"):
                vector_ops.append(op)
            elif op.type == "op raster":
                raster_ops.append(op)
                op_color = op.color.rgb if not op.default else "default"
                if rasters_one_pass is not False:
                    if rasters_one_pass is not None:
                        if str(rasters_one_pass) != str(op_color):
                            rasters_one_pass = False
                    else:
                        rasters_one_pass = op_color
            else:
                special_ops.append(op)
        if rasters_one_pass is not False:
            rasters_one_pass = True

        debug(
            "classify: ops: {passes}, {v} vectors, {r} rasters, {s} specials".format(
                passes="one pass" if rasters_one_pass else "two passes",
                v=len(vector_ops),
                r=len(raster_ops),
                s=len(special_ops),
            )
        )

        elements_to_classify = []
        for element in elements:
            if element is None:
                debug("classify: not classifying -  element is None")
                continue
            if hasattr(element, "operation"):
                add_op_function(element)
                debug(
                    "classify: added element as op: {op}".format(
                        op=str(op),
                    )
                )
                continue

            dot = is_dot(element)
            straight_line = is_straight_line(element)
            # print(element.stroke, element.fill, element.fill.alpha, is_straight_line, is_dot)

            # Check for default vector operations
            element_vector = False
            if isinstance(element, (Shape, SVGText)) and not dot:
                # Vector if not filled
                if (
                    element.fill is None
                    or element.fill.rgb is None
                    or (element.fill.alpha is not None and element.fill.alpha == 0)
                    or straight_line
                ):
                    element_vector = True

                # Not vector if grey stroke
                if (
                    element_vector
                    and element.stroke is not None
                    and element.stroke.rgb is not None
                    and element.stroke.red == element.stroke.green
                    and element.stroke.red == element.stroke.blue
                ):
                    element_vector = False

            elements_to_classify.append(
                (
                    element,
                    element_vector,
                    dot,
                    straight_line,
                )
            )

        debug(
            "classify: elements: {e} elements to classify".format(
                e=len(elements_to_classify),
            )
        )

        # Handle edge cases
        # Convert raster elements with white fill and no raster elements behind to vector
        # Because the white fill is not hiding anything.
        for i, (
            element,
            element_vector,
            dot,
            straight_line,
        ) in enumerate(elements_to_classify):
            if (
                # Raster?
                not element_vector
                and isinstance(element, (Shape, SVGText))
                and not dot
                # White non-transparent fill?
                and element.fill is not None
                and element.fill.rgb is not None
                and element.fill.rgb == 0xFFFFFF
                and element.fill.alpha is not None
                and element.fill.alpha != 0
                # But not grey stroke?
                and (
                    element.stroke is None
                    or element.stroke.rgb is None
                    or element.stroke.red != element.stroke.green
                    or element.stroke.red != element.stroke.blue
                )
            ):
                bbox = element.bbox()
                # Now check for raster elements behind
                for e2 in elements_to_classify[:i]:
                    # Ignore vectors
                    if e2[1]:
                        continue
                    # If underneath then stick with raster?
                    if self.bbox_overlap(bbox, e2[0].bbox()):
                        break
                else:
                    # No rasters underneath - convert to vector
                    debug(
                        "classify: edge-case: treating raster as vector: {label}".format(
                            label=self.element_label_id(element),
                        )
                    )

                    element_vector = True
                    elements_to_classify[i] = (
                        element,
                        element_vector,
                        dot,
                        straight_line,
                    )

        # Convert vector elements with element in front crossing the stroke to raster
        for i, (
            element,
            element_vector,
            dot,
            straight_line,
        ) in reversed_enumerate(elements_to_classify):
            if (
                element_vector
                and element.stroke is not None
                and element.stroke.rgb is not None
                and element.stroke.rgb != 0xFFFFFF
            ):
                bbox = element.bbox()
                color = element.stroke.rgb
                # Now check for raster elements in front whose path crosses over this path
                for e in elements_to_classify[i + 1 :]:
                    # Raster?
                    if e[1]:
                        continue
                    # Stroke or fill same colour?
                    if (
                        e[0].stroke is None
                        or e[0].stroke.rgb is None
                        or e[0].stroke.rgb != color
                    ) and (
                        e[0].fill is None
                        or e[0].fill.alpha is None
                        or e[0].fill.alpha == 0
                        or e[0].fill.rgb is None
                        or e[0].fill.rgb != color
                    ):
                        continue
                    # We have an element with a matching color
                    if self.bbox_overlap(bbox, e[0].bbox()):
                        # Rasters on top - convert to raster
                        debug(
                            "classify: edge-case: treating vector as raster: {label}".format(
                                label=self.element_label_id(element),
                            )
                        )

                        element_vector = False
                        elements_to_classify[i] = (
                            element,
                            element_vector,
                            dot,
                            straight_line,
                        )
                        break

        raster_elements = []
        for (
            element,
            element_vector,
            dot,
            straight_line,
        ) in elements_to_classify:

            element_color = self.element_classify_color(element)
            if isinstance(element, (Shape, SVGText)) and (
                element_color is None or element_color.rgb is None
            ):
                debug(
                    "classify: not classifying -  no stroke or fill color: {e}".format(
                        e=self.element_label_id(element, short=False),
                    )
                )
                continue

            element_added = False
            if dot or isinstance(element, SVGImage):
                for op in special_ops:
                    if (dot and op.type == "op dots") or (
                        isinstance(element, SVGImage) and op.type == "op image"
                    ):
                        op.add(element, type="ref elem", pos=element_pos)
                        element_added = True
                        break  # May only classify in one Dots or Image operation and indeed in one operation
            elif element_vector:
                # Vector op (i.e. no fill) with exact colour match to Raster Op will be rastered
                for op in raster_ops:
                    if (
                        op.color is not None
                        and op.color.rgb == element_color.rgb
                        and op not in default_raster_ops
                    ):
                        if not rasters_one_pass:
                            op.add(element, type="ref elem", pos=element_pos)
                        elif not element_added:
                            raster_elements.append((element, element.bbox()))
                        element_added = True

                for op in vector_ops:
                    if (
                        op.color is not None
                        and op.color.rgb == element_color.rgb
                        and op not in default_cut_ops
                        and op not in default_engrave_ops
                    ):
                        op.add(element, type="ref elem", pos=element_pos)
                        element_added = True
                if (
                    element.stroke is None
                    or element.stroke.rgb is None
                    or element.stroke.rgb == 0xFFFFFF
                ):
                    debug(
                        "classify: not classifying - white element at back: {e}".format(
                            e=self.element_label_id(element, short=False),
                        )
                    )
                    continue

            elif rasters_one_pass:
                for op in raster_ops:
                    if op.color is not None and op.color.rgb == element_color.rgb:
                        op.add(element, type="ref elem", pos=element_pos)
                        element_added = True
            else:
                raster_elements.append((element, element.bbox()))
                continue

            if element_added:
                continue

            if element_vector:
                is_cut = Color.distance_sq("red", element_color) <= 18825
                if is_cut:
                    for op in default_cut_ops:
                        op.add(element, type="ref elem", pos=element_pos)
                        element_added = True
                else:
                    for op in default_engrave_ops:
                        op.add(element, type="ref elem", pos=element_pos)
                        element_added = True
            elif (
                rasters_one_pass
                and isinstance(element, (Shape, SVGText))
                and not dot
                and raster_ops
            ):
                for op in raster_ops:
                    op.add(element, type="ref elem", pos=element_pos)
                element_added = True

            if element_added:
                continue

            # Need to add a new operation to classify into
            op = None
            if dot:
                op = DotsOpNode(default=True)
                special_ops.append(op)
            elif isinstance(element, SVGImage):
                op = ImageOpNode(default=True)
                special_ops.append(op)
            elif isinstance(element, (Shape, SVGText)):
                if element_vector:
                    if (
                        is_cut
                    ):  # This will be initialised because criteria are same as above
                        op = CutOpNode(color=abs(element_color))
                    else:
                        op = EngraveOpNode(
                            operation="Engrave", color=abs(element_color)
                        )
                        if element_color == Color("white"):
                            op.output = False
                    vector_ops.append(op)
                elif rasters_one_pass:
                    op = RasterOpNode(color="Transparent", default=True)
                    default_raster_ops.append(op)
                    raster_ops.append(op)
            if op is not None:
                new_ops.append(op)
                add_op_function(op)
                # element cannot be added to op before op is added to operations - otherwise refelem is not created.
                op.add(element, type="ref elem", pos=element_pos)
                debug(
                    "classify: added op: {op}".format(
                        op=str(op),
                    )
                )

        # End loop "for element in elements"

        if rasters_one_pass:
            return

        # Now deal with two-pass raster elements
        # It is ESSENTIAL that elements are added to operations in the same order as original.
        # The easiest way to ensure this is to create groups using a copy of raster_elements and
        # then ensure that groups have elements in the same order as in raster_elements.
        debug(
            "classify: raster pass two: {n} elements".format(
                n=len(raster_elements),
            )
        )

        # Debugging print statements have been left in as comments as this code can
        # be complex to debug and even print statements can be difficult to craft

        # This is a list of groups, where each group is a list of tuples, each an element and its bbox.
        # Initial list has a separate group for each element.
        raster_groups = group_overlapped_rasters([(e, e.bbox()) for e in raster_elements])

        debug(
            "classify: condensed to {n} raster groups".format(
                n=len(raster_groups),
            )
        )

        # Remove bbox and add element colour from groups
        # Change list to groups which are a list of tuples, each tuple being element and its classification color
        raster_groups = list(
            map(
                lambda g: tuple(((e[0], self.element_classify_color(e[0])) for e in g)),
                raster_groups,
            )
        )

        # print("grouped", list(map(lambda g: list(map(lambda e: e[0].id,g)), raster_groups)))

        # Add groups to operations of matching colour (and remove from list)
        # groups added to at least one existing raster op will not be added to default raster ops.
        groups_added = []
        for op in raster_ops:
            if (
                op not in default_raster_ops
                and op.color is not None
                and op.color.rgb is not None
            ):
                # Make a list of elements to add (same tupes)
                elements_to_add = []
                groups_count = 0
                for group in raster_groups:
                    for e in group:
                        if e[1].rgb == op.color.rgb:
                            # An element in this group matches op color
                            # So add elements to list
                            elements_to_add.extend(group)
                            if group not in groups_added:
                                groups_added.append(group)
                            groups_count += 1
                            break  # to next group
                if elements_to_add:
                    debug(
                        "classify: adding {e} elements in {g} groups to {label}".format(
                            e=len(elements_to_add),
                            g=groups_count,
                            label=str(op),
                        )
                    )
                    # Create simple list of elements sorted by original element order
                    elements_to_add = sorted(
                        [e[0] for e in elements_to_add], key=raster_elements.index
                    )
                    for element in elements_to_add:
                        op.add(element, type="ref elem", pos=element_pos)

        # Now remove groups added to at least one op
        for group in groups_added:
            raster_groups.remove(group)

        if not raster_groups:  # added all groups
            return

        #  Because groups don't matter further simplify back to a simple element_list
        elements_to_add = []
        for g in raster_groups:
            elements_to_add.extend(g)
        elements_to_add = sorted(
            [e[0] for e in elements_to_add], key=raster_elements.index
        )

        debug(
            "classify: {e} elements in {g} raster groups to add to default raster op(s)".format(
                e=len(elements_to_add),
                g=len(raster_groups),
            )
        )

        # Remaining elements are added to one of the following groups of operations:
        # 1. to default raster ops if they exist; otherwise
        # 2. to empty raster ops if they exist and are all of same color; otherwise to
        # 3. a new default Raster operation.
        if not default_raster_ops:
            # Because this is a check for an empty operation, this functionality relies on all elements being classified at the same time.
            # If you add elements individually, after the first raster operation the empty ops will no longer be empty and a default Raster op will be created instead.
            default_raster_ops = [op for op in raster_ops if len(op.children) == 0]
            color = False
            for op in default_raster_ops:
                if op.color is None or op.color.rgb is None:
                    op_color = "None"
                else:
                    op_color = op.color.rgb
                if color is False:
                    color = op_color
                elif color != op_color:
                    default_raster_ops = []
                    break
        if not default_raster_ops:
            op = RasterOpNode(color="Transparent", default=True)
            default_raster_ops.append(op)
            add_op_function(op)
            debug(
                "classify: default raster op added: {op}".format(
                    op=str(op),
                )
            )
        else:
            for op in default_raster_ops:
                debug("classify: default raster op selected: {op}".format(op=str(op)))

        for element in elements_to_add:
            for op in default_raster_ops:
                op.add(element, type="ref elem", pos=element_pos)

    @staticmethod
    def element_label_id(element, short=True):
        if element.node is None:
            if short:
                return element.id
            return "{id}: {path}".format(id=element.id, path=str(element))
        elif ":" in element.node.label and short:
            return element.node.label.split(":", 1)[0]
        else:
            return element.node.label

    @staticmethod
    def bbox_overlap(b1, b2):
        if b1[0] <= b2[2] and b1[2] >= b2[0] and b1[1] <= b2[3] and b1[3] >= b2[1]:
            return True
        return False

    def group_elements_overlap(self, g1, g2):
        for e1 in g1:
            for e2 in g2:
                if self.bbox_overlap(e1[1], e2[1]):
                    return True
        return False

    @staticmethod
    def element_classify_color(element: SVGElement):
        element_color = element.stroke
        if element_color is None or element_color.rgb is None:
            element_color = element.fill
        return element_color

    def load(self, pathname, **kwargs):
        kernel = self.kernel
        _ = kernel.translation
        for loader, loader_name, sname in kernel.find("load"):
            for description, extensions, mimetype in loader.load_types():
                if str(pathname).lower().endswith(extensions):
                    try:
                        results = loader.load(self, self, pathname, **kwargs)
                    except FileNotFoundError:
                        return False
                    except BadFileError as e:
                        kernel._console_channel(
                            _("File is Malformed")
                            + ": " + str(e)
                        )
                    except OSError:
                        return False
                    else:
                        if results:
                            self.signal("tree_changed\n")
                            return True
        return False

    def load_types(self, all=True):
        kernel = self.kernel
        _ = kernel.translation
        filetypes = []
        if all:
            filetypes.append(_("All valid types"))
            exts = []
            for loader, loader_name, sname in kernel.find("load"):
                for description, extensions, mimetype in loader.load_types():
                    for ext in extensions:
                        exts.append("*.%s" % ext)
            filetypes.append(";".join(exts))
        for loader, loader_name, sname in kernel.find("load"):
            for description, extensions, mimetype in loader.load_types():
                exts = []
                for ext in extensions:
                    exts.append("*.%s" % ext)
                filetypes.append("%s (%s)" % (description, extensions[0]))
                filetypes.append(";".join(exts))
        return "|".join(filetypes)

    def save(self, pathname):
        kernel = self.kernel
        for saver, save_name, sname in kernel.find("save"):
            for description, extension, mimetype in saver.save_types():
                if pathname.lower().endswith(extension):
                    saver.save(self, pathname, "default")
                    return True
        return False

    def save_types(self):
        kernel = self.kernel
        filetypes = []
        for saver, save_name, sname in kernel.find("save"):
            for description, extension, mimetype in saver.save_types():
                filetypes.append("%s (%s)" % (description, extension))
                filetypes.append("*.%s" % extension)
        return "|".join(filetypes)
