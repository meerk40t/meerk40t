"""
This is a giant list of console commands that deal with and often implement the elements system in the program.
"""

import os.path
import re
from copy import copy
from math import cos, gcd, isinf, pi, sin, sqrt, tau
from random import randint, shuffle

from meerk40t.kernel import CommandSyntaxError

from meerk40t.svgelements import (
    SVG_RULE_EVENODD,
    SVG_RULE_NONZERO,
    Angle,
    Close,
    Color,
    CubicBezier,
    Line,
    Matrix,
    QuadraticBezier,
    Viewbox,
)
from .element_types import *
from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.node.elem_path import PathNode
from meerk40t.core.node.node import Fillrule, Linecap, Linejoin, Node
from meerk40t.core.node.op_cut import CutOpNode
from meerk40t.core.node.op_dots import DotsOpNode
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.node.op_hatch import HatchOpNode
from meerk40t.core.node.op_image import ImageOpNode
from meerk40t.core.node.op_raster import RasterOpNode
from meerk40t.core.node.util_console import ConsoleOperation
from meerk40t.core.node.util_input import InputOperation
from meerk40t.core.node.util_output import OutputOperation
from meerk40t.core.node.util_wait import WaitOperation
from meerk40t.core.units import (
    UNITS_PER_INCH,
    UNITS_PER_MM,
    UNITS_PER_PIXEL,
    UNITS_PER_POINT,
    Length,
)


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    choices = [
        {
            "attr": "trace_start_method",
            "object": self,
            "default": 0,
            "type": int,
            "label": _("Delay hull trace"),
            "tip": _("Establish if and how an element hull trace should wait"),
            "page": "Laser",
            "section": "General",
            "style": "option",
            "display": (_("Immediate"), _("User confirmation"), _("Delay 5 seconds")),
            "choices": (0, 1, 2),
        },
    ]
    kernel.register_choices("preferences", choices)

    classify_new = self.post_classify

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
            channel(_("loading..."))
            result = self.load(new_file)
            if result:
                channel(_("Done."))
        except AttributeError:
            raise CommandSyntaxError(_("Loading files was not defined"))
        return "file", new_file

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
                channel(_("index {index} out of range").format(index=value))
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

    @self.console_argument("start", type=int, help=_("start"))
    @self.console_argument("end", type=int, help=_("end"))
    @self.console_option("step", "s", type=int, default=1, help=_("step"))
    @self.console_command(
        "range",
        help=_("Subset existing selection by begin and end indices and step"),
        input_type=("ops", "elements"),
        output_type=("ops", "elements"),
    )
    def opelem_select_range(
        data=None, data_type=None, start=None, end=None, step=1, **kwargs
    ):
        sublist = list()
        for e in range(start, end, step):
            try:
                sublist.append(data[e])
            except IndexError:
                pass
        self.set_emphasis(sublist)
        return data_type, sublist

    @self.console_argument("filter", type=str, help=_("Filter to apply"))
    @self.console_command(
        "filter",
        help=_("Filter data by given value"),
        input_type=("ops", "elements"),
        output_type=("ops", "elements"),
    )
    def opelem_filter(channel=None, data=None, data_type=None, filter=None, **kwargs):
        """
        Apply a filter string to a filter particular operations from the current data.
        Operations or elements are evaluated in an infix prioritized stack format without spaces.
        Qualified values for all node types are: id, label, len, type
        Qualified element values are stroke, fill, dpi, elem
        Qualified operation values are speed, power, frequency, dpi, acceleration, op, passes, color, overscan
        Valid operators are >, >=, <, <=, =, ==, +, -, *, /, &, &&, |, and ||
        Valid string operators are startswith, endswith, contains.
        String values require single-quotes ', because the console interface requires double-quotes.
        eg. filter speed>=10, filter speed=5+5, filter speed>power/10, filter speed==2*4+2
        eg. filter engrave=op&speed=35|cut=op&speed=10
        eg. filter len=0
        eg. operation* filter "type='op image'" list
        eg. element* filter "id startwith 'p'" list
        """
        sublist = list()
        _filter_parse = [
            ("STR", r"'([^']*)'"),
            ("SKIP", r"[ ,\t\n\x09\x0A\x0C\x0D]+"),
            ("OP20", r"(\*|/)"),
            ("OP15", r"(\+|-)"),
            ("OP11", r"(<=|>=|==|!=|startswith|endswith|contains)"),
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
                r"(raster|image|cut|engrave|dots|blob|rect|path|ellipse|point|image|line|polyline)",
            ),
            (
                "VAL",
                r"(type|op|speed|power|frequency|dpi|passes|color|overscan|len|elem|stroke|fill|id|label)",
            ),
        ]
        filter_re = re.compile("|".join("(?P<%s>%s)" % pair for pair in _filter_parse))
        operator = list()
        operand = list()

        def filter_parser(text: str):
            p = 0
            limit = len(text)
            while p < limit:
                match = filter_re.match(text, p)
                if match is None:
                    break  # No more matches.
                _kind = match.lastgroup
                _start = p
                p = match.end()
                if _kind == "SKIP":
                    continue
                _value = match.group()
                yield _kind, _value, _start, p

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
                        elif op == "startswith":
                            operand.append(str(v1).startswith(str(v2)))
                        elif op == "endswith":
                            operand.append(str(v1).endswith(str(v2)))
                        elif op == "contains":
                            operand.append(str(v2) in (str(v1)))
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
                    try:
                        if value == "type":
                            operand.append(e.type)
                        elif value == "op":
                            if e.type.startswith("op"):
                                operand.append(e.type.replace("op", "").strip())
                            else:
                                operand.append(None)
                        elif value == "speed":
                            operand.append(e.speed)
                        elif value == "power":
                            operand.append(e.power)
                        elif value == "frequency":
                            operand.append(e.frequency)
                        elif value == "dpi":
                            operand.append(e.dpi)
                        elif value == "passes":
                            operand.append(e.passes)
                        elif value == "color":
                            operand.append(e.color)
                        elif value == "len":
                            try:
                                operand.append(len(e.children))
                            except AttributeError:
                                operand.append(0)
                        elif value == "elem":
                            if e.type.startswith("elem"):
                                operand.append(e.type.replace("elem", "").strip())
                            else:
                                operand.append(None)
                        elif value == "stroke":
                            operand.append(e.stroke)
                        elif value == "fill":
                            operand.append(e.fill)
                        elif value == "stroke_width":
                            operand.append(e.stroke_width)
                        elif value == "id":
                            operand.append(e.id)
                        elif value == "label":
                            operand.append(e.label)
                        else:
                            operand.append(e.settings.get(value))
                    except AttributeError:
                        operand.append(None)
                elif kind == "NUM":
                    operand.append(float(value))
                elif kind == "TYPE":
                    operand.append(value)
                elif kind == "STR":
                    operand.append(value[1:-1])
                elif kind.startswith("OP"):
                    precedence = int(kind[2:])
                    solve_to(precedence)
                    operator.append((precedence, value))
            solve_to(0)
            if len(operand) == 1:
                if operand.pop():
                    sublist.append(e)
            else:
                raise CommandSyntaxError(_("Filter parse failed"))

        self.set_emphasis(sublist)
        return data_type, sublist

    @self.console_argument(
        "id",
        type=str,
        help=_("new id to set values to"),
    )
    @self.console_command(
        "id",
        help=_("id <id>"),
        input_type=("ops", "elements"),
        output_type=("elements", "ops"),
    )
    def opelem_id(command, channel, _, id=None, data=None, data_type=None, **kwargs):
        if id is None:
            # Display data about id.
            channel("----------")
            channel(_("ID Values:"))
            for i, e in enumerate(data):
                name = str(e)
                channel(
                    _("{index}: {name} - id = {id}").format(index=i, name=name, id=e.id)
                )
            channel("----------")
            return

        if len(data) == 0:
            channel(_("No selected nodes"))
            return
        for e in data:
            e.id = id
        self.validate_ids()
        self.signal("element_property_update", data)
        self.signal("refresh_scene", "Scene")
        return data_type, data

    @self.console_argument(
        "label",
        type=str,
        help=_("new label to set values to"),
    )
    @self.console_command(
        "label",
        help=_("label <label>"),
        input_type=("ops", "elements"),
        output_type=("elements", "ops"),
    )
    def opelem_label(
        command, channel, _, label=None, data=None, data_type=None, **kwargs
    ):
        if label is None:
            # Display data about id.
            channel("----------")
            channel(_("Label Values:"))
            for i, e in enumerate(data):
                name = str(e)
                channel(
                    _("{index}: {name} - label = {label}").format(
                        index=i, name=name, label=e.label
                    )
                )
            channel("----------")
            return

        if len(data) == 0:
            channel(_("No selected nodes"))
            return
        for e in data:
            e.label = label
        self.signal("element_property_update", data)
        self.signal("refresh_scene", "Scene")
        return data_type, data

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
            name = f"{select_piece} {i}: {str(op_obj)}"
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
                    name = f"{''.ljust(5)}{q}: {str(type(oe).__name__)}-{ident_piece} s:{stroke_piece} f:{fill_piece}"
                    channel(name)
        channel("----------")

    @self.console_option("color", "c", type=Color)
    @self.console_option("default", "D", type=bool)
    @self.console_option("speed", "s", type=float)
    @self.console_option("power", "p", type=float)
    @self.console_option("dpi", "d", type=int)
    @self.console_option("overscan", "o", type=self.length)
    @self.console_option("passes", "x", type=int)
    @self.console_option(
        "parallel",
        "P",
        type=bool,
        help=_("Creates a new operation for each element given"),
        action="store_true",
    )
    @self.console_option(
        "stroke",
        "K",
        type=bool,
        action="store_true",
        help=_(
            "Set the operation color based on the stroke if the first stroked item added to this operation"
        ),
    )
    @self.console_option(
        "fill",
        "F",
        type=bool,
        action="store_true",
        help=_(
            "Set the operation color based on the fill if the first filled item added to this operation"
        ),
    )
    @self.console_command(
        ("cut", "engrave", "raster", "imageop", "dots", "hatch"),
        help=_(
            "<cut/engrave/raster/imageop/dots/hatch> - group the elements into this operation"
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
        dpi=None,
        overscan=None,
        passes=None,
        parallel=False,
        stroke=False,
        fill=False,
        **kwargs,
    ):
        op_list = []

        def make_op():
            if command == "cut":
                return CutOpNode()
            elif command == "engrave":
                return EngraveOpNode()
            elif command == "raster":
                return RasterOpNode()
            elif command == "imageop":
                return ImageOpNode()
            elif command == "dots":
                return DotsOpNode()
            elif command == "hatch":
                return HatchOpNode()
            elif command == "waitop":
                return WaitOperation()
            elif command == "outputop":
                return OutputOperation()
            elif command == "inputop":
                return InputOperation()
            else:
                raise ValueError

        if parallel:
            if data is None:
                return "op", []
            for item in data:
                op = make_op()
                if color is not None:
                    op.color = color
                elif fill:
                    try:
                        op.color = item.fill
                    except AttributeError:
                        continue
                elif stroke:
                    try:
                        op.color = item.stroke
                    except AttributeError:
                        continue
                if default is not None:
                    op.default = default
                if speed is not None:
                    op.speed = speed
                if power is not None:
                    op.power = power
                if passes is not None:
                    op.passes_custom = True
                    op.passes = passes
                if dpi is not None:
                    op.dpi = dpi
                if overscan is not None:
                    op.overscan = overscan
                self.add_op(op)
                op.add_reference(item)
                op_list.append(op)
        else:
            op = make_op()
            if color is not None:
                op.color = color
            elif fill:
                try:
                    op.color = data[0].fill
                except (AttributeError, IndexError):
                    pass
            elif stroke:
                try:
                    op.color = data[0].stroke
                except (AttributeError, IndexError):
                    pass
            if default is not None:
                op.default = default
            if speed is not None:
                op.speed = speed
            if power is not None:
                op.power = power
            if passes is not None:
                op.passes_custom = True
                op.passes = passes
            if dpi is not None:
                op.dpi = dpi
            if overscan is not None:
                op.overscan = overscan
            self.add_op(op)
            if data is not None:
                for item in data:
                    op.add_reference(item)
            op_list.append(op)
        return "ops", op_list

    @self.console_argument(
        "time",
        type=float,
        default=5,
        help=_("Time for the given wait operation."),
    )
    @self.console_command(
        "waitop",
        help=_("<waitop> - Create new utility operation"),
        input_type=None,
        output_type="ops",
    )
    def makeop(
        command,
        time=None,
        **kwargs,
    ):
        op = self.op_branch.add(type="util wait", wait=time)
        return "ops", [op]

    @self.console_argument(
        "mask",
        type=int,
        default=0,
        help=_("binary input/output mask"),
    )
    @self.console_argument(
        "value",
        type=int,
        default=0,
        help=_("binary input/output value"),
    )
    @self.console_command(
        ("outputop", "inputop"),
        help=_("<outputop, inputop> - Create new utility operation"),
        input_type=None,
        output_type="ops",
    )
    def makeop(
        command,
        mask=None,
        value=None,
        **kwargs,
    ):
        if command == "inputop":
            op = self.op_branch.add(
                type="util input", input_mask=mask, input_value=value
            )
        else:
            op = self.op_branch.add(
                type="util output", output_mask=mask, output_value=value
            )
        return "ops", [op]

    @self.console_command(
        "consoleop",
        help=_("<consoleop> - Create new utility operation"),
    )
    def makeop(
        command,
        remainder=None,
        **kwargs,
    ):
        if remainder is not None:
            op = self.op_branch.add(type="util console", command=remainder)
            return "ops", [op]

    @self.console_argument("dpi", type=int, help=_("raster dpi"))
    @self.console_command("dpi", help=_("dpi <raster-dpi>"), input_type="ops")
    def op_dpi(command, channel, _, data, dpi=None, **kwrgs):
        if dpi is None:
            found = False
            for op in data:
                if op.type in ("op raster", "op image"):
                    dpi = op.dpi
                    channel(
                        _("Step for {name} is currently: {dpi}").format(
                            name=str(op), dpi=dpi
                        )
                    )
                    found = True
            if not found:
                channel(_("No raster operations selected."))
            return
        for op in data:
            if op.type in ("op raster", "op image"):
                op.dpi = dpi
                op.updated()
        return "ops", data

    @self.console_option(
        "difference",
        "d",
        type=bool,
        action="store_true",
        help=_("Change speed by this amount."),
    )
    @self.console_option(
        "progress",
        "p",
        type=bool,
        action="store_true",
        help=_("Change speed for each item in order"),
    )
    @self.console_argument("speed", type=str, help=_("operation speed in mm/s"))
    @self.console_command(
        "speed", help=_("speed <speed>"), input_type="ops", output_type="ops"
    )
    def op_speed(
        command,
        channel,
        _,
        speed=None,
        difference=False,
        progress=False,
        data=None,
        **kwrgs,
    ):
        if speed is None:
            for op in data:
                old = op.speed
                channel(
                    _("Speed for '{name}' is currently: {speed}").format(
                        name=str(op), speed=old
                    )
                )
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
        delta = 0
        for op in data:
            old = op.speed
            if percent and difference:
                s = old + old * (new_speed / 100.0)
            elif difference:
                s = old + new_speed
            elif percent:
                s = old * (new_speed / 100.0)
            elif progress:
                s = old + delta
                delta += new_speed
            else:
                s = new_speed
            if s < 0:
                s = 0
            op.speed = s
            channel(
                _("Speed for '{name}' updated {old_speed} -> {speed}").format(
                    name=str(op), old_speed=old, speed=s
                )
            )
            op.updated()
        return "ops", data

    @self.console_argument(
        "power", type=int, help=_("power in pulses per inch (ppi, 1000=max)")
    )
    @self.console_option(
        "difference",
        "d",
        type=bool,
        action="store_true",
        help=_("Change power by this amount."),
    )
    @self.console_option(
        "progress",
        "p",
        type=bool,
        action="store_true",
        help=_("Change power for each item in order"),
    )
    @self.console_command(
        "power", help=_("power <ppi>"), input_type="ops", output_type="ops"
    )
    def op_power(
        command,
        channel,
        _,
        power=None,
        difference=False,
        progress=False,
        data=None,
        **kwrgs,
    ):
        if power is None:
            for op in data:
                old = op.power
                channel(
                    _("Power for '{name}' is currently: {power}").format(
                        name=str(op), power=old
                    )
                )
            return
        delta = 0
        for op in data:
            old = op.power
            if progress:
                s = old + delta
                delta += power
            elif difference:
                s = old + power
            else:
                s = power
            if s > 1000:
                s = 1000
            if s < 0:
                s = 0
            op.power = s
            channel(
                _("Power for '{name}' updated {old_power} -> {power}").format(
                    name=str(op), old_power=old, power=s
                )
            )
            op.updated()
        return "ops", data

    @self.console_argument(
        "frequency", type=float, help=_("frequency set for operation")
    )
    @self.console_option(
        "difference",
        "d",
        type=bool,
        action="store_true",
        help=_("Change speed by this amount."),
    )
    @self.console_option(
        "progress",
        "p",
        type=bool,
        action="store_true",
        help=_("Change speed for each item in order"),
    )
    @self.console_command(
        "frequency", help=_("frequency <kHz>"), input_type="ops", output_type="ops"
    )
    def op_frequency(
        command,
        channel,
        _,
        frequency=None,
        difference=False,
        progress=False,
        data=None,
        **kwrgs,
    ):
        if frequency is None:
            for op in data:
                old = op.frequency
                channel(
                    _("Frequency for '{name}' is currently: {frequency}").format(
                        name=str(op), frequency=old
                    )
                )
            return
        delta = 0
        for op in data:
            old = op.frequency
            if progress:
                s = old + delta
                delta += frequency
            elif difference:
                s = old + frequency
            else:
                s = frequency
            if s < 0:
                s = 0
            op.frequency = s
            channel(
                _(
                    "Frequency for '{name}' updated {old_frequency} -> {frequency}"
                ).format(name=str(op), old_frequency=old, frequency=s)
            )
            op.updated()
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
                    _("Passes for '{name}' is currently: {passes}").format(
                        name=str(op), passes=old_passes
                    )
                )
            return
        for op in data:
            old_passes = op.passes
            op.passes = passes
            if passes >= 1:
                op.passes_custom = True
            channel(
                _("Passes for '{name}' updated {old_passes} -> {passes}").format(
                    name=str(op), old_passes=old_passes, passes=passes
                )
            )
            op.updated()
        return "ops", data

    @self.console_argument(
        "distance", type=Length, help=_("Set hatch-distance of operations")
    )
    @self.console_option(
        "difference",
        "d",
        type=bool,
        action="store_true",
        help=_("Change hatch-distance by this amount."),
    )
    @self.console_option(
        "progress",
        "p",
        type=bool,
        action="store_true",
        help=_("Change hatch-distance for each item in order"),
    )
    @self.console_command(
        "hatch-distance",
        help=_("hatch-distance <distance>"),
        input_type="ops",
        output_type="ops",
    )
    def op_hatch_distance(
        command,
        channel,
        _,
        distance=None,
        difference=False,
        progress=False,
        data=None,
        **kwrgs,
    ):
        if distance is None:
            for op in data:
                old = op.hatch_distance
                channel(
                    _("Hatch Distance for '{name}' is currently: {distance}").format(
                        name=str(op), distance=old
                    )
                )
            return
        delta = 0
        for op in data:
            old = Length(op.hatch_distance)
            if progress:
                s = float(old) + delta
                delta += float(distance)
            elif difference:
                s = float(old) + float(distance)
            else:
                s = float(distance)
            if s < 0:
                s = 0
            op.hatch_distance = Length(amount=s).length_mm
            channel(
                _(
                    "Hatch Distance for '{name}' updated {old_distance} -> {distance}"
                ).format(name=str(op), old_distance=old, distance=op.hatch_distance)
            )
            op.updated()
        return "ops", data

    @self.console_argument(
        "angle", type=Angle.parse, help=_("Set hatch-angle of operations")
    )
    @self.console_option(
        "difference",
        "d",
        type=bool,
        action="store_true",
        help=_("Change hatch-distance by this amount."),
    )
    @self.console_option(
        "progress",
        "p",
        type=bool,
        action="store_true",
        help=_("Change hatch-distance for each item in order"),
    )
    @self.console_command(
        "hatch-angle",
        help=_("hatch-angle <angle>"),
        input_type="ops",
        output_type="ops",
    )
    def op_hatch_distance(
        command,
        channel,
        _,
        angle=None,
        difference=False,
        progress=False,
        data=None,
        **kwrgs,
    ):
        if angle is None:
            for op in data:
                old = f"{Angle.parse(op.hatch_angle).as_turns:.4f}turn"
                old_hatch_angle_deg = f"{Angle.parse(op.hatch_angle).as_degrees:.4f}deg"
                channel(
                    _(
                        "Hatch Angle for '{name}' is currently: {angle} ({angle_degree})"
                    ).format(name=str(op), angle=old, angle_degree=old_hatch_angle_deg)
                )
            return
        delta = 0
        for op in data:
            old = Angle.parse(op.hatch_angle)
            if progress:
                s = old + delta
                delta += angle
            elif difference:
                s = old + angle
            else:
                s = angle
            s = Angle.radians(float(s))
            op.hatch_angle = f"{s.as_turns}turn"
            new_hatch_angle_turn = f"{s.as_turns:.4f}turn"
            new_hatch_angle_deg = f"{s.as_degrees:.4f}deg"

            channel(
                _(
                    "Hatch Angle for '{name}' updated {old_angle} -> {angle} ({angle_degree})"
                ).format(
                    name=str(op),
                    old_angle=f"{old.as_turns:.4f}turn",
                    angle=new_hatch_angle_turn,
                    angle_degree=new_hatch_angle_deg,
                )
            )
            op.updated()
        return "ops", data

    @self.console_command(
        "disable",
        help=_("Disable the given operations"),
        input_type="ops",
        output_type="ops",
    )
    def op_disable(command, channel, _, data=None, **kwrgs):
        for op in data:
            no_op = True
            if hasattr(op, "output"):
                try:
                    op.output = False
                    channel(_("Operation '{name}' disabled.").format(name=str(op)))
                    op.updated()
                    no_op = False
                except AttributeError:
                    pass
            if no_op:
                channel(_("Operation '{name}' can't be disabled.").format(name=str(op)))
        return "ops", data

    @self.console_command(
        "enable",
        help=_("Enable the given operations"),
        input_type="ops",
        output_type="ops",
    )
    def op_enable(command, channel, _, data=None, **kwrgs):
        for op in data:
            no_op = True
            if hasattr(op, "output"):
                try:
                    op.output = True
                    channel(_("Operation '{name}' enabled.").format(name=str(op)))
                    op.updated()
                    no_op = False
                except AttributeError:
                    pass
            if no_op:
                channel(_("Operation '{name}' can't be enabled.").format(name=str(op)))
        return "ops", data

    # ==========
    # ELEMENT/OPERATION SUBCOMMANDS
    # ==========
    @self.console_command(
        "lock",
        help=_("Lock element (protect from manipulation)"),
        input_type="elements",
        output_type="elements",
    )
    def e_lock(data=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        for e in data:
            e.lock = True
        self.signal("element_property_update", data)
        self.signal("refresh_scene", "Scene")
        return "elements", data

    @self.console_command(
        "unlock",
        help=_("Unlock element (allow manipulation)"),
        input_type="elements",
        output_type="elements",
    )
    def e_unlock(data=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        for e in data:
            if hasattr(e, "lock"):
                e.lock = False
        self.signal("element_property_update", data)
        self.signal("refresh_scene", "Scene")
        return "elements", data

    @self.console_option(
        "dx", "x", help=_("copy offset x (for elems)"), type=Length, default=0
    )
    @self.console_option(
        "dy", "y", help=_("copy offset y (for elems)"), type=Length, default=0
    )
    @self.console_command(
        "copy",
        help=_("Duplicate elements"),
        input_type=("elements", "ops"),
        output_type=("elements", "ops"),
    )
    def e_copy(data=None, data_type=None, post=None, dx=None, dy=None, **kwargs):
        if data is None:
            # Take tree selection for ops, scene selection for elements
            if data_type == "ops":
                data = list(self.ops(selected=True))
            else:
                data = list(self.elems(emphasized=True))

        if data_type == "ops":
            add_elem = list(map(copy, data))
            self.add_ops(add_elem)
            return "ops", add_elem
        else:
            if dx is None:
                x_pos = 0
            else:
                x_pos = dx
            if dy is None:
                y_pos = 0
            else:
                y_pos = dy
            add_elem = list(map(copy, data))
            matrix = None
            if x_pos != 0 or y_pos != 0:
                matrix = Matrix.translate(dx, dy)
            delta_wordlist = 1
            for e in add_elem:
                if matrix:
                    e.matrix *= matrix
                newnode = self.elem_branch.add_node(e)
                if self.copy_increases_wordlist_references and hasattr(newnode, "text"):
                    newnode.text = self.wordlist_delta(newnode.text, delta_wordlist)
                elif self.copy_increases_wordlist_references and hasattr(
                    newnode, "mktext"
                ):
                    newnode.mktext = self.wordlist_delta(newnode.mktext, delta_wordlist)
                    for property_op in self.kernel.lookup_all("path_updater/.*"):
                        property_op(self.kernel.root, newnode)
            # Newly created! Classification needed?
            post.append(classify_new(add_elem))
            self.signal("refresh_scene", "Scene")
            return "elements", add_elem

    @self.console_command(
        "delete", help=_("Delete elements"), input_type=("elements", "ops")
    )
    def e_delete(command, channel, _, data=None, data_type=None, **kwargs):
        channel(_("Deleting…"))
        with self.static("e_delete"):
            if data_type == "elements":
                self.remove_elements(data)
            else:
                self.remove_operations(data)

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
                channel(_("index {index} out of range").format(index=value))
        return "elements", elements_list

    # ==========
    # REGMARK COMMANDS
    # ==========
    def move_nodes_to(target, nodes):
        for elem in nodes:
            target.drop(elem)

    @self.console_argument("cmd", type=str, help=_("free, clear, add"))
    @self.console_command(
        "regmark",
        help=_("regmark cmd"),
        input_type=(None, "elements"),
        output_type="elements",
        all_arguments_required=True,
    )
    def regmark(command, channel, _, data, cmd=None, **kwargs):
        # Move regmarks into the regular element tree and vice versa
        with self.static("regmark"):
            if cmd == "free":
                target = self.elem_branch
            else:
                target = self.reg_branch

            if data is None:
                data = list()
                if cmd == "free":
                    for item in list(self.regmarks()):
                        data.append(item)
                else:
                    for item in list(self.elems(emphasized=True)):
                        data.append(item)
            if cmd in ("free", "add"):
                if len(data) == 0:
                    channel(_("No elements to transfer"))
                else:
                    move_nodes_to(target, data)
                    if cmd == "free" and self.classify_new:
                        self.classify(data)
            elif cmd == "clear":
                self.clear_regmarks()
                data = None
            else:
                # Unknown command
                channel(_("Invalid command, use one of add, free, clear"))
                data = None
        return "elements", data

    # ==========
    # ELEMENT SUBCOMMANDS
    # ==========

    # @self.console_argument("step_size", type=int, help=_("element step size"))
    # @self.console_command(
    #     "step",
    #     help=_("step <element step-size>"),
    #     input_type="elements",
    #     output_type="elements",
    # )
    # def step_command(command, channel, _, data, step_size=None, **kwrgs):
    #     if step_size is None:
    #         found = False
    #         for element in data:
    #             if isinstance(element, SVGImage):
    #                 try:
    #                     step = element.values["raster_step"]
    #                 except KeyError:
    #                     step = 1
    #                 channel(
    #                     _("Image step for %s is currently: %s")
    #                     % (str(element), step)
    #                 )
    #                 found = True
    #         if not found:
    #             channel(_("No image element selected."))
    #         return
    #     for element in data:
    #         element.values["raster_step"] = str(step_size)
    #         m = element.transform
    #         tx = m.e
    #         ty = m.f
    #         element.transform = Matrix.scale(float(step_size), float(step_size))
    #         element.transform.post_translate(tx, ty)
    #         if hasattr(element, "node"):
    #             element.node.modified()
    #         self.signal("element_property_reload", element)
    #     return ("elements",)

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
            if e.emphasized:
                channel(f"{i}: * {name}")
            else:
                channel(f"{i}: {name}")
        channel("----------")
        return "elements", data

    @self.console_command(
        "merge",
        help=_("merge elements"),
        input_type="elements",
        output_type="elements",
    )
    def element_merge(data=None, post=None, **kwargs):
        super_element = Path()
        for e in data:
            try:
                path = e.as_path()
            except AttributeError:
                continue
            try:
                if super_element.stroke is None:
                    super_element.stroke = e.stroke
            except AttributeError:
                pass
            try:
                if super_element.fill is None:
                    super_element.fill = e.fill
            except AttributeError:
                pass
            super_element += path
        self.remove_elements(data)
        node = self.elem_branch.add(path=super_element, type="elem path")
        self.set_node_emphasis(node, True)
        # Newly created! Classification needed?
        data = [node]
        post.append(classify_new(data))
        return "elements", data

    @self.console_command(
        "subpath",
        help=_("break elements"),
        input_type="elements",
        output_type="elements",
    )
    def element_subpath(data=None, post=None, **kwargs):
        if not isinstance(data, list):
            data = list(data)
        elements_nodes = []
        elements = []
        for node in data:
            oldstuff = []
            for attrib in ("stroke", "fill", "stroke_width", "stroke_scaled"):
                if hasattr(node, attrib):
                    oldval = getattr(node, attrib, None)
                    oldstuff.append([attrib, oldval])
            group_node = node.replace_node(type="group", label=node.label)
            try:
                p = node.as_path()
            except AttributeError:
                continue
            for subpath in p.as_subpaths():
                subelement = Path(subpath)
                subnode = group_node.add(path=subelement, type="elem path")
                for item in oldstuff:
                    setattr(subnode, item[0], item[1])
                elements.append(subnode)
            elements_nodes.append(group_node)
        post.append(classify_new(elements))
        return "elements", elements_nodes

    # ==========
    # GRID SUBTYPE
    # ==========

    @self.console_argument("c", type=int, help=_("Number of columns"))
    @self.console_argument("r", type=int, help=_("Number of rows"))
    @self.console_argument("x", type=str, help=_("x distance"))
    @self.console_argument("y", type=str, help=_("y distance"))
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
        x: str,
        y: str,
        origin=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if r is None:
            raise CommandSyntaxError
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No item selected."))
            return
        try:
            bounds = Node.union_bounds(data)
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
        except TypeError:
            raise CommandSyntaxError
        if x is None:
            x = "100%"
        if y is None:
            y = "100%"
        try:
            x = float(Length(x, relative_length=Length(amount=width).length_mm))
            y = float(Length(y, relative_length=Length(amount=height).length_mm))
        except ValueError:
            raise CommandSyntaxError("Length could not be parsed.")
        if origin is None:
            origin = (1, 1)
        cx, cy = origin
        data_out = list(data)
        if cx is None:
            cx = 1
        if cy is None:
            cy = 1
        start_x = -1 * x * (cx - 1)
        start_y = -1 * y * (cy - 1)
        y_pos = start_y
        for j in range(r):
            x_pos = start_x
            for k in range(c):
                if j != (cy - 1) or k != (cx - 1):
                    add_elem = list(map(copy, data))
                    for e in add_elem:
                        e.matrix *= Matrix.translate(x_pos, y_pos)
                        self.elem_branch.add_node(e)
                    data_out.extend(add_elem)
                x_pos += x
            y_pos += y
        # Newly created! Classification needed?
        post.append(classify_new(data_out))
        self.signal("refresh_scene", "Scene")
        return "elements", data_out

    @self.console_argument("repeats", type=int, help=_("Number of repeats"))
    @self.console_argument("radius", type=self.length, help=_("Radius"))
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
        post=None,
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
            radius = 0

        if startangle is None:
            startangle = Angle.parse("0deg")
        if endangle is None:
            endangle = Angle.parse("360deg")
        if rotate is None:
            rotate = False

        # print ("Segment to cover: %f - %f" % (startangle.as_degrees, endangle.as_degrees))
        bounds = Node.union_bounds(data)
        if bounds is None:
            return
        width = bounds[2] - bounds[0]

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
                    e.matrix *= f"rotate({currentangle}rad, {center_x}, {center_y})"
                else:
                    x_pos = -1 * radius + radius * cos(currentangle)
                    y_pos = radius * sin(currentangle)
                    e.matrix *= f"translate({x_pos}, {y_pos})"
                self.elem_branch.add_node(e)

            data_out.extend(add_elem)

            currentangle += segment_len

        # Newly created! Classification needed?
        post.append(classify_new(data_out))
        self.signal("refresh_scene", "Scene")
        return "elements", data_out

    @self.console_argument("copies", type=int, help=_("Number of copies"))
    @self.console_argument("radius", type=self.length, help=_("Radius"))
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
            radius = 0

        if startangle is None:
            startangle = Angle.parse("0deg")
        if endangle is None:
            endangle = Angle.parse("360deg")
        if rotate is None:
            rotate = False

        # print ("Segment to cover: %f - %f" % (startangle.as_degrees, endangle.as_degrees))
        bounds = Node.union_bounds(data)
        if bounds is None:
            return
        width = bounds[2] - bounds[0]

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
        images = []
        for cc in range(copies):
            # print ("Angle: %f rad = %f deg" % (currentangle, currentangle/pi * 180))
            add_elem = list(map(copy, data))
            for e in add_elem:
                if rotate:
                    x_pos = radius
                    y_pos = 0
                    e.matrix *= f"translate({x_pos}, {y_pos})"
                    e.matrix *= f"rotate({currentangle}rad, {center_x}, {center_y})"
                    e.modified()
                    if hasattr(e, "update"):
                        images.append(e)
                else:
                    x_pos = radius * cos(currentangle)
                    y_pos = radius * sin(currentangle)
                    e.matrix *= f"translate({x_pos}, {y_pos})"
                    e.translated(x_pos, y_pos)
                self.elem_branch.add_node(e)
            data_out.extend(add_elem)
            currentangle += segment_len
        for e in images:
            e.update(None)

        self.signal("refresh_scene", "Scene")
        return "elements", data_out

    @self.console_argument("corners", type=int, help=_("Number of corners/vertices"))
    @self.console_argument(
        "cx", type=self.length_x, help=_("X-Value of polygon's center")
    )
    @self.console_argument(
        "cy", type=self.length_y, help=_("Y-Value of polygon's center")
    )
    @self.console_argument(
        "radius",
        type=self.length_x,
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
        type=str,
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
    @self.console_option("density", "d", type=int, help=_("Amount of vertices to skip"))
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
        post=None,
        **kwargs,
    ):
        if corners is None:
            raise CommandSyntaxError

        if cx is None:
            if corners <= 2:
                raise CommandSyntaxError(
                    _(
                        "Please provide at least one additional value (which will act as radius then)"
                    )
                )
            cx = 0
        if cy is None:
            cy = 0
        if radius is None:
            radius = 0
        if corners <= 2:
            # No need to look at side_length parameter as we are considering the radius value as an edge anyway...
            if startangle is None:
                startangle = Angle.parse("0deg")

            star_points = [(cx, cy)]
            if corners == 2:
                star_points += [
                    (
                        cx + cos(startangle.as_radians) * radius,
                        cy + sin(startangle.as_radians) * radius,
                    )
                ]
        else:
            # do we have something like 'polyshape 3 4cm' ? If yes, reassign the parameters
            if radius is None:
                radius = cx
                cx = 0
                cy = 0
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
            if side_length is not None:
                # Let's recalculate the radius then...
                # d_oc = s * csc( pi / n)
                radius = 0.5 * radius / sin(pi / corners)

            if radius_inner is None:
                radius_inner = radius
            else:
                try:
                    radius_inner = float(Length(radius_inner, relative_length=radius))
                except ValueError:
                    raise CommandSyntaxError

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

            # print(
            #   "Your parameters are:\n cx=%.1f, cy=%.1f\n radius=%.1f, inner=%.1f\n corners=%d, density=%d\n seq=%d, angle=%.1f"
            #   % (cx, cy, radius, radius_inner, corners, density, alternate_seq, startangle)
            # )
            pts = []
            i_angle = startangle.as_radians
            delta_angle = tau / corners
            ct = 0
            for j in range(corners):
                if ct < alternate_seq:
                    r = radius
                #    dbg = "outer"
                else:
                    r = radius_inner
                #    dbg = "inner"
                thisx = cx + r * cos(i_angle)
                thisy = cy + r * sin(i_angle)
                # print(
                #    "pt %d, Angle=%.1f: %s radius=%.1f: (%.1f, %.1f)"
                #    % (j, i_angle / pi * 180, dbg, r, thisx, thisy)
                # )
                ct += 1
                if ct >= 2 * alternate_seq:
                    ct = 0
                if j == 0:
                    firstx = thisx
                    firsty = thisy
                i_angle += delta_angle
                pts += [(thisx, thisy)]
            # Close the path
            pts += [(firstx, firsty)]

            star_points = [(pts[0][0], pts[0][1])]
            idx = density
            while idx != 0:
                star_points += [(pts[idx][0], pts[idx][1])]
                idx += density
                if idx >= corners:
                    idx -= corners
            if len(star_points) < corners:
                ct = 0
                possible_combinations = ""
                for i in range(corners - 1):
                    j = i + 2
                    if gcd(j, corners) == 1:
                        if ct % 3 == 0:
                            possible_combinations += f"\n shape {corners} ... -d {j}"
                        else:
                            possible_combinations += f", shape {corners} ... -d {j} "
                        ct += 1
                channel(
                    _("Just for info: we have missed {count} vertices...").format(
                        count=(corners - len(star_points))
                    )
                )
                channel(
                    _(
                        "To hit all, the density parameters should be e.g. {combinations}"
                    ).format(combinations=possible_combinations)
                )

        poly_path = Polygon(star_points)
        if data is None:
            data = list()
        node = self.elem_branch.add(shape=poly_path, type="elem polyline")
        node.stroke = self.default_stroke
        node.stroke_width = self.default_strokewidth
        node.fill = self.default_fill
        node.altered()
        self.set_emphasis([node])
        node.focus()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_option("dpi", "d", default=500, type=float)
    @self.console_command(
        "render",
        help=_("Create a raster image from the given elements"),
        input_type=(None, "elements"),
        output_type="image",
    )
    def render_elements(command, channel, _, dpi=500.0, data=None, post=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        reverse = self.classify_reverse
        if reverse:
            data = list(reversed(data))
        make_raster = self.lookup("render-op/make_raster")
        if not make_raster:
            channel(_("No renderer is registered to perform render."))
            return
        bounds = Node.union_bounds(data, attr="paint_bounds")
        # bounds_regular = Node.union_bounds(data)
        # for idx in range(4):
        #     print (f"Bounds[{idx}] = {bounds_regular[idx]:.2f} vs {bounds_regular[idx]:.2f}")
        if bounds is None:
            return
        xmin, ymin, xmax, ymax = bounds
        if isinf(xmin):
            channel(_("No bounds for selected elements."))
            return
        width = xmax - xmin
        height = ymax - ymin

        dots_per_units = dpi / UNITS_PER_INCH
        new_width = width * dots_per_units
        new_height = height * dots_per_units
        new_height = max(new_height, 1)
        new_width = max(new_width, 1)

        image = make_raster(
            data,
            bounds=bounds,
            width=new_width,
            height=new_height,
        )
        matrix = Matrix.scale(width / new_width, height / new_height)
        matrix.post_translate(bounds[0], bounds[1])

        image_node = ImageNode(image=image, matrix=matrix, dpi=dpi)
        self.elem_branch.add_node(image_node)
        self.signal("refresh_scene", "Scene")
        data = [image_node]
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "image", [image_node]

    @self.console_option(
        "dpi", "d", help=_("interim image resolution"), default=500, type=float
    )
    @self.console_option(
        "turnpolicy",
        "z",
        type=str,
        default="minority",
        help=_("how to resolve ambiguities in path decomposition"),
    )
    @self.console_option(
        "turdsize",
        "t",
        type=int,
        default=2,
        help=_("suppress speckles of up to this size (default 2)"),
    )
    @self.console_option(
        "alphamax", "a", type=float, default=1, help=_("corner threshold parameter")
    )
    @self.console_option(
        "opticurve",
        "n",
        type=bool,
        action="store_true",
        help=_("turn off curve optimization"),
    )
    @self.console_option(
        "opttolerance",
        "O",
        type=float,
        help=_("curve optimization tolerance"),
        default=0.2,
    )
    @self.console_option(
        "color",
        "C",
        type=Color,
        help=_("set foreground color (default Black)"),
    )
    @self.console_option(
        "invert",
        "i",
        type=bool,
        action="store_true",
        help=_("invert bitmap"),
    )
    @self.console_option(
        "blacklevel",
        "k",
        type=float,
        default=0.5,
        help=_("blacklevel?!"),
    )
    @self.console_command(
        "vectorize",
        help=_("Convert given elements to a path"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def vectorize_elements(
        command,
        channel,
        _,
        dpi=500.0,
        turnpolicy=None,
        turdsize=None,
        alphamax=None,
        opticurve=None,
        opttolerance=None,
        color=None,
        invert=None,
        blacklevel=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if data is None:
            data = list(self.elems(emphasized=True))
        reverse = self.classify_reverse
        if reverse:
            data = list(reversed(data))
        make_raster = self.lookup("render-op/make_raster")
        make_vector = self.lookup("render-op/make_vector")
        if not make_raster:
            channel(_("No renderer is registered to perform render."))
            return
        if not make_vector:
            channel(_("No vectorization engine could be found."))
            return

        policies = {
            "black": 0,  # POTRACE_TURNPOLICY_BLACK
            "white": 1,  # POTRACE_TURNPOLICY_WHITE
            "left": 2,  # POTRACE_TURNPOLICY_LEFT
            "right": 3,  # POTRACE_TURNPOLICY_RIGHT
            "minority": 4,  # POTRACE_TURNPOLICY_MINORITY
            "majority": 5,  # POTRACE_TURNPOLICY_MAJORITY
            "random": 6,  # POTRACE_TURNPOLICY_RANDOM
        }

        if turnpolicy not in policies:
            turnpolicy = "minority"
        ipolicy = policies[turnpolicy]

        if turdsize is None:
            turdsize = 2
        if alphamax is None:
            alphamax = 1
        if opticurve is None:
            opticurve = True
        if opttolerance is None:
            opttolerance = 0.2
        if color is None:
            color = Color("black")
        if invert is None:
            invert = False
        if blacklevel is None:
            blacklevel = 0.5

        bounds = Node.union_bounds(data, attr="paint_bounds")
        if bounds is None:
            return
        xmin, ymin, xmax, ymax = bounds
        if isinf(xmin):
            channel(_("No bounds for selected elements."))
            return
        width = xmax - xmin
        height = ymax - ymin

        dots_per_units = dpi / UNITS_PER_INCH
        new_width = width * dots_per_units
        new_height = height * dots_per_units
        new_height = max(new_height, 1)
        new_width = max(new_width, 1)

        image = make_raster(
            data,
            bounds=bounds,
            width=new_width,
            height=new_height,
        )
        path = make_vector(
            image,
            interpolationpolicy=ipolicy,
            invert=invert,
            turdsize=turdsize,
            alphamax=alphamax,
            opticurve=opticurve,
            opttolerance=opttolerance,
            color=color,
            blacklevel=blacklevel,
        )
        matrix = Matrix.scale(width / new_width, height / new_height)
        matrix.post_translate(bounds[0], bounds[1])
        path.transform *= Matrix(matrix)
        node = self.elem_branch.add(
            path=abs(path),
            stroke_width=0,
            stroke_scaled=False,
            type="elem path",
            fillrule=Fillrule.FILLRULE_NONZERO,
            linejoin=Linejoin.JOIN_ROUND,
        )
        # Newly created! Classification needed?
        data_out = [node]
        post.append(classify_new(data_out))
        self.signal("refresh_scene", "Scene")

        return "elements", data_out

    @self.console_option(
        "dpi", "d", help=_("interim image resolution"), default=500, type=float
    )
    @self.console_option(
        "turnpolicy",
        "z",
        type=str,
        default="minority",
        help=_("how to resolve ambiguities in path decomposition"),
    )
    @self.console_option(
        "turdsize",
        "t",
        type=int,
        default=2,
        help=_("suppress speckles of up to this size (default 2)"),
    )
    @self.console_option(
        "alphamax", "a", type=float, default=1, help=_("corner threshold parameter")
    )
    @self.console_option(
        "opticurve",
        "n",
        type=bool,
        action="store_true",
        help=_("turn off curve optimization"),
    )
    @self.console_option(
        "opttolerance",
        "O",
        type=float,
        help=_("curve optimization tolerance"),
        default=0.2,
    )
    @self.console_option(
        "color",
        "C",
        type=Color,
        help=_("set foreground color (default Black)"),
    )
    @self.console_option(
        "invert",
        "i",
        type=bool,
        action="store_true",
        help=_("invert bitmap"),
    )
    @self.console_option(
        "blacklevel",
        "k",
        type=float,
        default=0.5,
        help=_("blacklevel?!"),
    )
    @self.console_option(
        "outer",
        "u",
        type=bool,
        action="store_true",
        help=_("Only outer line"),
    )
    @self.console_option(
        "steps",
        "x",
        type=int,
        default=1,
        help=_("How many offsetlines (default 1)"),
    )
    @self.console_option(
        "debug",
        "d",
        type=bool,
        action="store_true",
        help=_("Preserve intermediary objects"),
    )
    @self.console_argument("offset", type=Length, help="Offset distance")
    @self.console_command(
        "outline",
        help=_("Create an outline path at the inner and outer side of a path"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_outline(
        command,
        channel,
        _,
        offset=None,
        dpi=500.0,
        turnpolicy=None,
        turdsize=None,
        alphamax=None,
        opticurve=None,
        opttolerance=None,
        color=None,
        invert=None,
        blacklevel=None,
        outer=None,
        steps=None,
        debug=False,
        data=None,
        post=None,
        **kwargs,
    ):
        """
        Phase 1: We create a rendered image of the data, then we vectorize
        this representation
        Phase 2: This path will then be adjusted by applying
        altered stroke-widths and rendered and vectorized again.

        This two phase approach is required as not all nodes have
        a proper stroke-width that can be adjusted (eg text or images...)

        The subvariant --outer requires one additional pass where we disassemble
        the first outline and fill the subpaths, This will effectively deal with
        donut-type shapes

        The need for --inner was't high on my priority list (as it is somwhat
        difficult to implement, --outer just uses a clever hack to deal with
        topology edge cases. So if we are in need of inner we need to create
        the outline shape, break it in subpaths and delete the outer shapes
        manually. Sorry.
        """
        if data is None:
            data = list(self.elems(emphasized=True))
        if data is None or len(data) == 0:
            channel(_("No elements to outline."))
            return
        if debug is None:
            debug = False
        reverse = self.classify_reverse
        if reverse:
            data = list(reversed(data))
        make_raster = self.lookup("render-op/make_raster")
        make_vector = self.lookup("render-op/make_vector")
        if not make_raster:
            channel(_("No renderer is registered to perform render."))
            return
        if not make_vector:
            channel(_("No vectorization engine could be found."))
            return

        policies = {
            "black": 0,  # POTRACE_TURNPOLICY_BLACK
            "white": 1,  # POTRACE_TURNPOLICY_WHITE
            "left": 2,  # POTRACE_TURNPOLICY_LEFT
            "right": 3,  # POTRACE_TURNPOLICY_RIGHT
            "minority": 4,  # POTRACE_TURNPOLICY_MINORITY
            "majority": 5,  # POTRACE_TURNPOLICY_MAJORITY
            "random": 6,  # POTRACE_TURNPOLICY_RANDOM
        }

        if turnpolicy not in policies:
            turnpolicy = "minority"
        ipolicy = policies[turnpolicy]

        if turdsize is None:
            turdsize = 2
        if alphamax is None:
            alphamax = 1
        if opticurve is None:
            opticurve = True
        if opttolerance is None:
            opttolerance = 0.2
        if color is None:
            pathcolor = Color("blue")
        else:
            pathcolor = color
        if invert is None:
            invert = False
        if blacklevel is None:
            blacklevel = 0.5
        if offset is None:
            offset = self.length("5mm")
        else:
            offset = self.length(offset)
        if steps is None or steps < 1:
            steps = 1
        if outer is None:
            outer = False
        outputdata = []
        mydata = []
        for node in data:
            if outer and hasattr(node, "fill"):
                e = copy(node)
                e.fill = Color("black")
                if hasattr(e, "stroke"):
                    e.stroke = Color("black")
                if hasattr(e, "stroke_width") and e.stroke_width == 0:
                    e.stroke_width = UNITS_PER_PIXEL
                if hasattr(e, "fillrule"):
                    e.fillrule = 0
                mydata.append(e)
            else:
                e = copy(node)
                if hasattr(e, "stroke_width") and e.stroke_width == 0:
                    e.stroke_width = UNITS_PER_PIXEL
                mydata.append(e)
        if debug:
            for node in mydata:
                node.label = "Phase 0: Initial copy"
                self.elem_branch.add_node(node)

        ###############################################
        # Phase 1: render and vectorize first outline
        ###############################################
        bounds = Node.union_bounds(mydata, attr="paint_bounds")
        # bounds_regular = Node.union_bounds(data)
        # for idx in range(4):
        #     print (f"Bounds[{idx}] = {bounds_regular[idx]:.2f} vs {bounds_regular[idx]:.2f}")
        if bounds is None:
            return
        xmin, ymin, xmax, ymax = bounds
        if isinf(xmin):
            channel(_("No bounds for selected elements."))
            return
        width = xmax - xmin
        height = ymax - ymin

        dots_per_units = dpi / UNITS_PER_INCH
        new_width = width * dots_per_units
        new_height = height * dots_per_units
        new_height = max(new_height, 1)
        new_width = max(new_width, 1)
        dpi = 500

        data_image = make_raster(
            mydata,
            bounds=bounds,
            width=new_width,
            height=new_height,
        )
        matrix = Matrix.scale(width / new_width, height / new_height)
        matrix.post_translate(bounds[0], bounds[1])
        image_node_1 = ImageNode(
            image=data_image, matrix=matrix, dpi=dpi, label="Phase 1 render image"
        )

        path = make_vector(
            data_image,
            interpolationpolicy=ipolicy,
            invert=invert,
            turdsize=turdsize,
            alphamax=alphamax,
            opticurve=opticurve,
            opttolerance=opttolerance,
            color=color,
            blacklevel=blacklevel,
        )
        matrix = Matrix.scale(width / new_width, height / new_height)
        matrix.post_translate(bounds[0], bounds[1])
        path.transform *= Matrix(matrix)
        data_node = PathNode(
            path=abs(path),
            stroke_width=1,
            stroke=Color("black"),
            stroke_scaled=False,
            fill=None,
            # fillrule=Fillrule.FILLRULE_NONZERO,
            linejoin=Linejoin.JOIN_ROUND,
            label="Phase 1 Outline path",
        )
        data_node.fill = None
        # If you want to debug the phases then uncomment the following lines to
        # see the interim path and interim render image
        if debug:
            self.elem_branch.add_node(data_node)
            self.elem_branch.add_node(image_node_1)

        copy_data = [image_node_1, data_node]

        ################################################################
        # Phase 2: change outline witdh and render and vectorize again
        ################################################################
        for numidx in range(steps):
            data_node.stroke_width += 2 * offset
            data_node.set_dirty_bounds()
            pb = data_node.paint_bounds
            bounds = Node.union_bounds(copy_data, attr="paint_bounds")
            # print (f"{pb} - {bounds}")
            if bounds is None:
                return
            # bounds_regular = Node.union_bounds(copy_data)
            # for idx in range(4):
            #     print (f"Bounds[{idx}] = {bounds_regular[idx]:.2f} vs {bounds[idx]:.2f}")
            xmin, ymin, xmax, ymax = bounds
            if isinf(xmin):
                channel(_("No bounds for selected elements."))
                return
            width = xmax - xmin
            height = ymax - ymin

            dots_per_units = dpi / UNITS_PER_INCH
            new_width = width * dots_per_units
            new_height = height * dots_per_units
            new_height = max(new_height, 1)
            new_width = max(new_width, 1)
            dpi = 500

            image_2 = make_raster(
                copy_data,
                bounds=bounds,
                width=new_width,
                height=new_height,
            )
            matrix = Matrix.scale(width / new_width, height / new_height)
            matrix.post_translate(bounds[0], bounds[1])
            image_node_2 = ImageNode(
                image=image_2, matrix=matrix, dpi=dpi, label="Phase 2 render image"
            )

            path_2 = make_vector(
                image_2,
                interpolationpolicy=ipolicy,
                invert=invert,
                turdsize=turdsize,
                alphamax=alphamax,
                opticurve=opticurve,
                opttolerance=opttolerance,
                color=color,
                blacklevel=blacklevel,
            )
            matrix = Matrix.scale(width / new_width, height / new_height)
            matrix.post_translate(bounds[0], bounds[1])
            path_2.transform *= Matrix(matrix)
            # That's our final path (or is it? Depends on outer...)
            path_final = path_2
            data_node_2 = PathNode(
                path=abs(path_2),
                stroke_width=1,
                stroke=Color("black"),
                stroke_scaled=False,
                fill=None,
                # fillrule=Fillrule.FILLRULE_NONZERO,
                linejoin=Linejoin.JOIN_ROUND,
                label="Phase 2 Outline path",
            )
            data_node_2.fill = None

            # If you want to debug the phases then uncomment the following line to
            # see the interim image
            if debug:
                self.elem_branch.add_node(image_node_2)
                self.elem_branch.add_node(data_node_2)
            #######################################################
            # Phase 3: render and vectorize last outline for outer
            #######################################################
            if outer:
                # Generate the outline, break it into subpaths
                copy_data = []
                # Now break it into subpaths...
                for pasp in path_final.as_subpaths():
                    subpath = Path(pasp)
                    data_node = PathNode(
                        path=abs(subpath),
                        stroke_width=1,
                        stroke=Color("black"),
                        stroke_scaled=False,
                        fill=Color("black"),
                        # fillrule=Fillrule.FILLRULE_NONZERO,
                        linejoin=Linejoin.JOIN_ROUND,
                        label="Phase 3 Outline subpath",
                    )
                    # This seems to be necessary to make sure the fill sticks
                    data_node.fill = Color("black")
                    copy_data.append(data_node)
                    # If you want to debug the phases then uncomment the following lines to
                    # see the interim path nodes
                    if debug:
                        self.elem_branch.add_node(data_node)

                bounds = Node.union_bounds(copy_data, attr="paint_bounds")
                # bounds_regular = Node.union_bounds(data)
                # for idx in range(4):
                #     print (f"Bounds[{idx}] = {bounds_regular[idx]:.2f} vs {bounds_regular[idx]:.2f}")
                if bounds is None:
                    return
                xmin, ymin, xmax, ymax = bounds
                if isinf(xmin):
                    channel(_("No bounds for selected elements."))
                    return
                width = xmax - xmin
                height = ymax - ymin

                dots_per_units = dpi / UNITS_PER_INCH
                new_width = width * dots_per_units
                new_height = height * dots_per_units
                new_height = max(new_height, 1)
                new_width = max(new_width, 1)
                dpi = 500

                data_image = make_raster(
                    copy_data,
                    bounds=bounds,
                    width=new_width,
                    height=new_height,
                )
                matrix = Matrix.scale(width / new_width, height / new_height)
                matrix.post_translate(bounds[0], bounds[1])

                path_final = make_vector(
                    data_image,
                    interpolationpolicy=ipolicy,
                    invert=invert,
                    turdsize=turdsize,
                    alphamax=alphamax,
                    opticurve=opticurve,
                    opttolerance=opttolerance,
                    color=color,
                    blacklevel=blacklevel,
                )
                matrix = Matrix.scale(width / new_width, height / new_height)
                matrix.post_translate(bounds[0], bounds[1])
                path_final.transform *= Matrix(matrix)

            outline_node = self.elem_branch.add(
                path=abs(path_final),
                stroke_width=1,
                stroke_scaled=False,
                type="elem path",
                fill=None,
                stroke=pathcolor,
                # fillrule=Fillrule.FILLRULE_NONZERO,
                linejoin=Linejoin.JOIN_ROUND,
                label=f"Outline path #{numidx}",
            )
            outline_node.fill = None
            outputdata.append(outline_node)

        # Newly created! Classification needed?
        post.append(classify_new(outputdata))
        self.signal("refresh_scene", "Scene")
        if len(outputdata) > 0:
            self.signal("element_property_update", outputdata)
        return "elements", outputdata

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
                    f"{'.'.join(p).ljust(10)}: {str(n._bounds)} - {str(n._bounds_dirty)} {str(n.type)} - {str(str(n)[:16])}"
                )
                b_list(p, n)

        for d in data:
            channel("----------")
            if d.type == "root":
                channel(_("Tree:"))
            else:
                channel(f"{str(d)}:")
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
                channel(f"{'.'.join(p).ljust(10)}{j} {str(n.type)} - {str(n.label)}")
                t_list(p, n)

        for d in data:
            channel("----------")
            if d.type == "root":
                channel(_("Tree:"))
            else:
                channel(f"{d.label}:")
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
        E.g. "tree dnd 0.1 0.2" will drag node 0.1 into node 0.2
        """
        if data is None:
            data = [self._tree]
        if drop is None:
            raise CommandSyntaxError
        with self.static("tree_dnd"):
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
    def tree_menu(command, channel, _, data=None, node=None, execute=None, **kwargs):
        """
        Create menu for a particular node.
        Processes submenus, references, radio_state and check_state as needed.
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

        from meerk40t.core.treeop import get_tree_operation_for_node

        tree_operations_for_node = get_tree_operation_for_node(self)
        for func in tree_operations_for_node(menu_node):
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
                n = func.real_name
                if hasattr(func, "check_state") and func.check_state:
                    n = "✓" + n
                menu_context.append((n, menu_functions(func, menu_node)))
            if func.separate_after:
                menu_context.append(("------", None))
        if execute is not None:
            try:
                execute_command = ("menu", menu)
                for n in execute.split("."):
                    name, cmd = execute_command
                    execute_command = cmd[int(n)]
                name, cmd = execute_command
                channel(f"Executing {name}: {str(cmd)}")
                cmd()
            except (IndexError, AttributeError, ValueError, TypeError):
                raise CommandSyntaxError
        else:

            def m_list(path, _menu):
                for i, _n in enumerate(_menu):
                    p = list(path)
                    p.append(str(i))
                    _name, _submenu = _n
                    channel(f"{'.'.join(p).ljust(10)}: {str(_name)}")
                    if isinstance(_submenu, list):
                        m_list(p, _submenu)

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
        # print ("selected")
        # for n in self.flat():
        #     print ("Node: %s, selected=%s, emphasized=%s" % (n.type, n.selected, n.emphasized))
        return "tree", list(self.flat(selected=True))

    @self.console_command(
        "emphasized",
        help=_("delegate commands to focused value"),
        input_type="tree",
        output_type="tree",
    )
    def emphasized(channel, _, **kwargs):
        """
        Set tree list to emphasized node
        """
        return "tree", list(self.flat(emphasized=True))

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
        Structural nodes such as root, elements branch, and operations branch are not able to be deleted
        """
        # This is an unusually dangerous operation, so if we have multiple node types, like ops + elements
        # then we would 'only' delete those where we have the least danger, so that regmarks < operations < elements
        if len(data) == 0:
            channel(_("Nothing to delete"))
            return
        # print ("Delete called with data:")
        # for n in data:
        #     print ("Node: %s, sel=%s, emp=%s" % (n.type, n.selected, n.emphasized))
        typecount = [0, 0, 0, 0, 0]
        todelete = [[], [], [], [], []]
        nodetypes = ("Operations", "References", "Elements", "Regmarks", "Branches")
        regmk = list(self.regmarks())
        for node in data:
            if node.type in op_nodes:
                typecount[0] += 1
                todelete[0].append(node)
            elif node.type == "reference":
                typecount[1] += 1
                todelete[1].append(node)
            elif node.type in elem_group_nodes:
                if node in regmk:
                    typecount[3] += 1
                    todelete[3].append(node)
                else:
                    if hasattr(node, "lock") and node.lock:
                        # Don't delete locked nodes
                        continue
                    typecount[2] += 1
                    todelete[2].append(node)
            else:  # branches etc...
                typecount[4] += 1
        # print ("Types: ops=%d, refs=%d, elems=%d, regmarks=%d, branches=%d" %
        #     (typecount[0], typecount[1], typecount[2], typecount[3], typecount[4]))
        single = False
        if (
            typecount[0] > 0
            and typecount[1] == 0
            and typecount[2] == 0
            and typecount[3] == 0
        ):
            single = True
            entry = 0
        elif (
            typecount[1] > 0
            and typecount[0] == 0
            and typecount[2] == 0
            and typecount[3] == 0
        ):
            single = True
            entry = 1
        elif (
            typecount[2] > 0
            and typecount[0] == 0
            and typecount[1] == 0
            and typecount[3] == 0
        ):
            single = True
            entry = 2
        elif (
            typecount[3] > 0
            and typecount[0] == 0
            and typecount[1] == 0
            and typecount[2] == 0
        ):
            single = True
            entry = 3
        if not single:
            if typecount[3] > 0:
                # regmarks take precedence, the least dangereous delete
                entry = 3
            elif typecount[1] > 0:
                # refs next
                entry = 1
            elif typecount[0] > 0:
                # ops next
                entry = 0
            else:
                # Not sure why and when this supposed to happen?
                entry = 2
            channel(
                _(
                    "There were nodes across operations ({c1}), assignments ({c2}), elements ({c3}) and regmarks ({c4})."
                ).format(
                    c1=typecount[0],
                    c2=typecount[1],
                    c3=typecount[2],
                    c4=typecount[3],
                )
                + "\n"
                + _("Only nodes of type {nodetype} were deleted.").format(
                    nodetype=nodetypes[entry]
                )
                + "\n"
                + _(
                    "If you want to remove all nodes regardless of their type, consider: 'tree selected remove'"
                )
            )
        # print ("Want to delete %d" % entry)
        # for n in todelete[entry]:
        #     print ("Node to delete: %s" % n.type)
        with self.static("delete"):
            self.remove_nodes(todelete[entry])
            self.validate_selected_area()
        self.signal("refresh_scene", "Scene")
        return "tree", [self._tree]

    @self.console_command(
        "remove",
        help=_("forcefully deletes all given nodes"),
        input_type="tree",
        output_type="tree",
    )
    def remove(channel, _, data=None, **kwargs):
        """
        Delete nodes.
        Structural nodes such as root, elements branch, and operations branch are not able to be deleted
        """
        # This is an unusually dangerous operation, so if we have multiple node types, like ops + elements
        # then we would 'only' delete those where we have the least danger, so that regmarks < operations < elements
        with self.static("remove"):
            self.remove_nodes(data)
        self.signal("refresh_scene", "Scene")
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
            if item.type in elem_nodes or item.type in ("group", "file"):
                return "elements", list(self.elems(emphasized=True))

    # ==========
    # UNDO/REDO COMMANDS
    # ==========
    @self.console_command(
        "save_restore_point",
    )
    def undo_mark(data=None, **kwgs):
        self.undo.mark()

    @self.console_command(
        "undo",
    )
    def undo_undo(command, channel, _, **kwgs):
        if not self.undo.undo():
            # At bottom of stack.
            channel("No undo available.")
            return
        self.validate_selected_area()
        channel(f"Undo: {self.undo}")
        self.signal("refresh_scene", "Scene")
        self.signal("rebuild_tree")

    @self.console_command(
        "redo",
    )
    def undo_redo(command, channel, _, data=None, **kwgs):
        if not self.undo.redo():
            channel("No redo available.")
            return
        channel(f"Redo: {self.undo}")
        self.validate_selected_area()
        self.signal("refresh_scene", "Scene")
        self.signal("rebuild_tree")

    @self.console_command(
        "undolist",
    )
    def undo_list(command, channel, _, **kwgs):
        for entry in self.undo.undolist():
            channel(entry)

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
        self._clipboard[destination] = []
        for e in data:
            copy_node = copy(e)
            # Need to add stroke and fill, as copy will take the
            # default values for these attributes
            for optional in ("fill", "stroke"):
                if hasattr(e, optional):
                    setattr(copy_node, optional, getattr(e, optional))
            hadoptional = False
            for optional in ("wxfont", "mktext", "mkfont", "mkfontsize"):
                if hasattr(e, optional):
                    setattr(copy_node, optional, getattr(e, optional))
                    hadoptional = True
            self._clipboard[destination].append(copy_node)
        # Let the world know we have filled the clipboard
        self.signal("icons")
        return "elements", self._clipboard[destination]

    @self.console_option("dx", "x", help=_("paste offset x"), type=Length, default=0)
    @self.console_option("dy", "y", help=_("paste offset y"), type=Length, default=0)
    @self.console_command(
        "paste",
        help=_("clipboard paste"),
        input_type="clipboard",
        output_type="elements",
    )
    def clipboard_paste(
        command, channel, _, data=None, post=None, dx=None, dy=None, **kwargs
    ):
        destination = self._clipboard_default
        pasted = []
        try:
            for e in self._clipboard[destination]:
                copy_node = copy(e)
                # Need to add stroke and fill, as copy will take the
                # default values for these attributes
                for optional in ("fill", "stroke"):
                    if hasattr(e, optional):
                        setattr(copy_node, optional, getattr(e, optional))
                hadoptional = False
                for optional in ("wxfont", "mktext", "mkfont", "mkfontsize"):
                    if hasattr(e, optional):
                        setattr(copy_node, optional, getattr(e, optional))
                        hadoptional = True
                if hadoptional:
                    for property_op in self.kernel.lookup_all("path_updater/.*"):
                        property_op(self.kernel.root, copy_node)

                pasted.append(copy_node)
        except (TypeError, KeyError):
            channel(_("Error: Clipboard Empty"))
            return
        if len(pasted) == 0:
            channel(_("Error: Clipboard Empty"))
            return

        if dx is not None:
            dx = float(dx)
        else:
            dx = 0
        if dy is not None:
            dy = float(dy)
        else:
            dy = 0
        if dx != 0 or dy != 0:
            matrix = Matrix.translate(dx, dy)
            for node in pasted:
                node.matrix *= matrix
        if len(pasted) > 1:
            group = self.elem_branch.add(type="group", label="Group", id="Copy")
        else:
            group = self.elem_branch
        target = []
        for p in pasted:
            if hasattr(p, "label"):
                s = "Copy" if p.label is None else f"{p.label} (copy)"
                p.label = s
            group.add_node(p)
            target.append(p)
        # Make sure we are selecting the right thing...
        if len(pasted) > 1:
            self.set_emphasis([group])
        else:
            self.set_emphasis(target)

        self.signal("refresh_tree", group)
        # Newly created! Classification needed?
        post.append(classify_new(pasted))
        return "elements", pasted

    @self.console_command(
        "cut",
        help=_("clipboard cut"),
        input_type="clipboard",
        output_type="elements",
    )
    def clipboard_cut(data=None, **kwargs):
        destination = self._clipboard_default
        self._clipboard[destination] = []
        for e in data:
            copy_node = copy(e)
            for optional in ("wxfont", "mktext", "mkfont", "mkfontsize"):
                if hasattr(e, optional):
                    setattr(copy_node, optional, getattr(e, optional))
            self._clipboard[destination].append(copy_node)
        self.remove_elements(data)
        # Let the world know we have filled the clipboard
        self.signal("icons")
        return "elements", self._clipboard[destination]

    @self.console_command(
        "clear",
        help=_("clipboard clear"),
        input_type="clipboard",
        output_type="elements",
    )
    def clipboard_clear(data=None, **kwargs):
        destination = self._clipboard_default
        try:
            old = self._clipboard[destination]
        except KeyError:
            old = None
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
            channel(f"{str(v).ljust(5)}: {str(k)}")
        num = self.has_clipboard()
        channel(_("Clipboard-Entries: {index}").format(index=num))

    # ==========
    # NOTES COMMANDS
    # ==========
    @self.console_option("append", "a", type=bool, action="store_true", default=False)
    @self.console_command("note", help=_("note <note>"))
    def note(command, channel, _, append=False, remainder=None, **kwargs):
        _note = remainder
        if _note is None:
            if self.note is None:
                channel(_("No Note."))
            else:
                channel(str(self.note))
        else:
            if append:
                self.note += "\n" + _note
            else:
                self.note = _note
            self.signal("note", self.note)
            channel(_("Note Set."))
            channel(str(self.note))

    # --------------------------- END COMMANDS ------------------------------
