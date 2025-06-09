"""
This module provides a set of console commands for managing branches and operations within the application.
These commands allow users to load files, manage operations, and manipulate elements in various ways.

Functions:
- plugin(kernel, lifecycle=None): Initializes the plugin and sets up branch commands.
- init_commands(kernel): Initializes the branch commands and defines the associated operations.
- load(channel, _, filename=None, **kwargs): Loads a file from the working directory and adds its contents to the application.
  Args:
    channel: The communication channel for messages.
    filename: The name of the file to load.
  Returns:
    A tuple containing the type of the file and its path.
- element(command, **kwargs): Displays information about operations in the system.
  Args:
    command: The command context.
  Returns:
    None
- operation_select(**kwargs): Selects the currently emphasized operations.
  Args:
    command: The command context.
  Returns:
    A tuple containing the type of operations and the selected operations.
- operation_all(**kwargs): Selects all operations in the system.
  Args:
    command: The command context.
  Returns:
    A tuple containing the type of operations and all operations.
- operation_invert(**kwargs): Selects all non-emphasized operations.
  Args:
    command: The command context.
  Returns:
    A tuple containing the type of operations and the non-selected operations.
- operation_base(**kwargs): Selects the currently emphasized operations.
  Args:
    command: The command context.
  Returns:
    A tuple containing the type of operations and the emphasized operations.
- operation_re(command, channel, _, **kwargs): Selects operations based on specified indices.
  Args:
    command: The command context.
    channel: The communication channel for messages.
  Returns:
    A tuple containing the type of operations and the selected operations.
- operation_select_emphasis(data=None, **kwargs): Sets the specified operations as the current selection.
  Args:
    data: The operations to select.
  Returns:
    A tuple containing the type of operations and the selected operations.
- operation_select_plus(data=None, **kwargs): Adds the specified operations to the current selection.
  Args:
    data: The operations to add.
  Returns:
    A tuple containing the type of operations and the updated selection.
- operation_select_minus(data=None, **kwargs): Removes the specified operations from the current selection.
  Args:
    data: The operations to remove.
  Returns:
    A tuple containing the type of operations and the updated selection.
- operation_select_xor(data=None, **kwargs): Toggles the specified operations in the current selection.
  Args:
    data: The operations to toggle.
  Returns:
    A tuple containing the type of operations and the updated selection.
- opelem_select_range(data=None, data_type=None, start=None, end=None, step=1, **kwargs): Subsets the current selection based on specified start, end, and step indices.
  Args:
    data: The elements to subset.
    data_type: The type of data being processed.
    start: The starting index for the subset.
    end: The ending index for the subset.
    step: The step size for the subset.
  Returns:
    A tuple containing the type of data and the subsetted elements.
- opelem_filter(channel=None, data=None, data_type=None, filter=None, **kwargs): Filters the current selection based on the provided filter string.
  Args:
    channel: The communication channel for messages.
    data: The elements to filter.
    data_type: The type of data being processed.
    filter: The filter string to apply.
  Returns:
    A tuple containing the type of data and the filtered elements.
- opelem_id(command, channel, _, id=None, data=None, data_type=None, **kwargs): Sets or retrieves the ID of the specified elements.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    id: The new ID to set.
    data: The elements to modify.
    data_type: The type of data being processed.
  Returns:
    A tuple containing the type of data and the modified elements.
- opelem_label(command, channel, _, label=None, data=None, data_type=None, **kwargs): Sets or retrieves the label of the specified elements.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    label: The new label to set.
    data: The elements to modify.
    data_type: The type of data being processed.
  Returns:
    A tuple containing the type of data and the modified elements.
- operation_empty(channel, _, data=None, data_type=None, **kwargs): Removes all elements from the specified operations.
  Args:
    channel: The communication channel for messages.
    data: The operations to clear.
    data_type: The type of data being processed.
  Returns:
    A tuple containing the type of data and the cleared operations.
- operation_list(command, channel, _, data=None, **kwargs): Lists information about the specified operations.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    data: The operations to list.
  Returns:
    A tuple containing the type of data and the listed operations.
- element_lock(data=None, **kwargs): Locks the specified elements to prevent manipulation.
  Args:
    data: The elements to lock.
  Returns:
    A tuple containing the type of data and the locked elements.
- element_unlock(data=None, **kwargs): Unlocks the specified elements to allow manipulation.
  Args:
    data: The elements to unlock.
  Returns:
    A tuple containing the type of data and the unlocked elements.
- e_copy(data=None, data_type=None, post=None, dx=None, dy=None, copies=None, **kwargs): Duplicates the specified elements a given number of times with optional offsets.
  Args:
    data: The elements to copy.
    data_type: The type of data being processed.
    post: Additional processing information.
    dx: The x-offset for the copies.
    dy: The y-offset for the copies.
    copies: The number of copies to create.
  Returns:
    A tuple containing the type of data and the copied elements.
- e_delete(command, channel, _, data=None, data_type=None, **kwargs): Deletes the specified elements or operations.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    data: The elements or operations to delete.
    data_type: The type of data being processed.
  Returns:
    A tuple containing the type of data and the deleted elements.
"""

import re
from copy import copy

from meerk40t.core.node.effect_hatch import HatchEffectNode
from meerk40t.core.node.op_cut import CutOpNode
from meerk40t.core.node.op_dots import DotsOpNode
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.node.op_image import ImageOpNode
from meerk40t.core.node.op_raster import RasterOpNode
from meerk40t.core.units import Angle, Length
from meerk40t.kernel import CommandSyntaxError
from meerk40t.svgelements import Color, Matrix
from meerk40t.core.elements.element_types import op_nodes
from meerk40t.tools.geomstr import NON_GEOMETRY_TYPES
def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

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
            result = self.load(new_file, svg_ppi=self.svg_ppi)
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
    def operation_select(**kwargs):
        return "ops", list(self.ops(emphasized=True))

    @self.console_command(
        "operation*", help=_("operation*: all operations"), output_type="ops"
    )
    def operation_all(**kwargs):
        return "ops", list(self.ops())

    @self.console_command(
        "operation~",
        help=_("operation~: non selected operations."),
        output_type="ops",
    )
    def operation_invert(**kwargs):
        return "ops", list(self.ops(emphasized=False))

    @self.console_command(
        "operation", help=_("operation: selected operations."), output_type="ops"
    )
    def operation_base(**kwargs):
        return "ops", list(self.ops(emphasized=True))

    @self.console_command(
        r"operation([0-9]+,?)+",
        help=_("operation0,2: operation #0 and #2"),
        regex=True,
        output_type="ops",
    )
    def operation_re(command, channel, _, **kwargs):
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
    def operation_select_emphasis(data=None, **kwargs):
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
        e.g. filter speed>=10, filter speed=5+5, filter speed>power/10, filter speed==2*4+2
        e.g. filter engrave=op&speed=35|cut=op&speed=10
        e.g. filter len=0
        e.g. operation* filter "type='op image'" list
        e.g. element* filter "id startswith 'p'" list
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
        "empty",
        help=_("Remove all elements from provided operations"),
        input_type="ops",
        output_type="ops",
    )
    def operation_empty(channel, _, data=None, **kwargs):
        if data is None:
            data = list()
            for item in list(self.flat(selected=True, cascade=False, types=op_nodes)):
                data.append(item)
        # _("Clear operations")
        with self.undoscope("Clear operations"):
            index_ops = list(self.ops())
            for item in data:
                i = index_ops.index(item)
                select_piece = "*" if item.emphasized else " "
                name = f"{select_piece} {i}: {str(item)}"
                channel(f"{name}: {len(item.children)}")
                item.remove_all_children()
        self.signal("rebuild_tree", "operations")

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
                parent_node = EngraveOpNode()
                parent_node.add_node(HatchEffectNode())
                return parent_node
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
    def waitop(
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
    def io_op(
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

    @self.console_argument(
        "x",
        type=Length,
        default=0,
        help=_("X-Coordinate of Goto?"),
    )
    @self.console_argument(
        "y",
        type=Length,
        default=0,
        help=_("Y-Coordinate of Goto?"),
    )
    @self.console_command(
        "gotoop",
        help=_("<gotoop> <x> <y> - Create new utility operation"),
        input_type=None,
        output_type="ops",
    )
    def gotoop(
        command,
        x=0,
        y=0,
        **kwargs,
    ):
        op = self.op_branch.add(type="util goto", x=str(x), y=str(y))
        return "ops", [op]

    @self.console_command(
        "consoleop",
        help=_("<consoleop> - Create new utility operation"),
    )
    def consoleop(
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

    @self.console_argument("angle", type=Angle, help=_("Set hatch-angle of operations"))
    @self.console_option(
        "difference",
        "d",
        type=bool,
        action="store_true",
        help=_("Change hatch-angle by this amount."),
    )
    @self.console_option(
        "progress",
        "p",
        type=bool,
        action="store_true",
        help=_("Change hatch-angle for each item in order"),
    )
    @self.console_command(
        "hatch-angle",
        help=_("hatch-angle <angle>"),
        input_type="ops",
        output_type="ops",
    )
    def op_hatch_angle(
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
                old = Angle(op.hatch_angle, digits=4).angle_turns
                old_hatch_angle_deg = Angle(op.hatch_angle, digits=4).angle_degrees
                channel(
                    _(
                        "Hatch Angle for '{name}' is currently: {angle} ({angle_degree})"
                    ).format(name=str(op), angle=old, angle_degree=old_hatch_angle_deg)
                )
            return
        delta = 0
        for op in data:
            try:
                old = Angle(op.hatch_angle)
            except AttributeError:
                # Console-Op or other non-angled op.
                continue
            if progress:
                s = old + delta
                delta += angle
            elif difference:
                s = old + angle
            else:
                s = angle
            s = Angle.from_radians(float(s))
            op.hatch_angle = s.angle_turns
            new_hatch_angle_turn = s.angle_turns
            new_hatch_angle_deg = s.angle_degrees

            channel(
                _(
                    "Hatch Angle for '{name}' updated {old_angle} -> {angle} ({angle_degree})"
                ).format(
                    name=str(op),
                    old_angle=old.angle_turns,
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
    @self.console_option(
        "copies", "c", help=_("amount of copies to be created"), type=int, default=1
    )
    @self.console_command(
        "copy",
        help=_("Duplicate elements"),
        input_type=("elements", "ops"),
        output_type=("elements", "ops"),
    )
    def e_copy(data=None, data_type=None, post=None, dx=None, dy=None, copies=None, **kwargs):
        if data is None:
            # Take tree selection for ops, scene selection for elements
            if data_type == "ops":
                data = list(self.ops(selected=True))
            else:
                data = list(self.elems(emphasized=True))
        if copies is None:
            copies = 1
        if copies < 1:
            copies = 1

        if data_type == "ops":
            add_ops = list()
            for idx in range(copies):
                add_ops.extend(list(map(copy, data)))
            # print (f"Add ops contains now: {len(add_ops)} operations")
            self.add_ops(add_ops)
            return "ops", add_ops
        else:
            if dx is None:
                x_pos = 0
            else:
                x_pos = float(dx)
            if dy is None:
                y_pos = 0
            else:
                y_pos = float(dy)
            add_elem = list()
            shift = list()
            tx = 0
            ty = 0
            for idx in range(copies):
                tx += x_pos
                ty += y_pos
                this_shift = [(tx, ty)] * len(data)
                add_elem.extend(list(map(copy, data)))
                shift.extend(this_shift)
            # print (f"Add elem contains now: {len(add_elem)} elements")
            delta_wordlist = 1
            for e, delta in zip(add_elem, shift):
                tx, ty = delta
                if tx != 0 or ty != 0:
                    matrix = Matrix.translate(tx, ty)
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
        with self.undoscope("Deleting"):
            if data_type == "elements":
                self.remove_elements(data)
            else:
                self.remove_operations(data)
        self.signal("update_group_labels")

    @self.console_command(
        "clear_all", help=_("Clear all content"), input_type=("elements", "ops")
    )
    def e_clear(command, channel, _, data=None, data_type=None, **kwargs):
        channel(_("Deleting…"))
        fast = True
        with self.undoscope("Deleting"):
            if data_type == "elements":
                self.clear_elements(fast=fast)
                self.emphasized()
            else:
                self.clear_operations(fast=fast)
        self.signal("rebuild_tree", "all")

    # ==========
    # ELEMENT BASE
    # ==========

    @self.console_command(
        "elements",
        help=_("Show information about elements"),
    )
    def elements(**kwargs):
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
        # _("Regmarks -> Elements") + _("Elements -> Regmarks")
        if cmd == "free":
            target = self.elem_branch
            scope = "Regmarks -> Elements"
        else:
            target = self.reg_branch
            scope = "Elements -> Regmarks"

        with self.undoscope(scope):
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

    @kernel.console_option("stitchtolerance", "s", type=Length, help=_("By default elements will be stitched together if they have common end/start points, this option allows to set a tolerance"))
    @kernel.console_option("nostitch", "n", type=bool, action="store_true", help=_("By default elements will be stitched together if they have a common end/start point, this option prevents that and real subpaths will be created"))
    @self.console_command(
        "merge",
        help=_("merge elements"),
        input_type="elements",
        output_type="elements",
    )
    def element_merge(command, channel, _, data=None, post=None, nostitch=None, stitchtolerance=None, **kwargs):
        """
        Merge combines the geometries of the inputs. This matters in some cases where fills are used. Such that two
        nested circles forms a toroid rather two independent circles.
        """
        def set_nonset_attributes(node, e):
            try:
                if node.stroke is None:
                    node.stroke = e.stroke
            except AttributeError:
                pass
            try:
                if node.fill is None:
                    node.fill = e.fill
            except AttributeError:
                pass
            try:
                if node.stroke_width is None:
                    node.stroke_width = e.stroke_width
            except AttributeError:
                pass

        def merge_paths(other, path, nocase, tolerance):
            def segments_can_stitch(aseg, bseg, starta, startb):
                def segtype(info):
                    return int(info[2].real) & 0xFF

                if segtype(aseg) not in NON_GEOMETRY_TYPES and segtype(bseg) not in NON_GEOMETRY_TYPES:
                    s1, _dummy2, _dummy3, _dummy4, e1 = aseg
                    s2, _dummy2, _dummy3, _dummy4, e2 = bseg
                    c1 = s1 if starta else e1
                    c2 = s2 if startb else e2
                    if abs(c1 - c2) <= tolerance + 1E-6:
                        return True
                return False


            seg1_start = other.segments[0]
            seg1_end = other.segments[other.index - 1]
            seg2_start = path.segments[0]
            seg2_end = path.segments[path.index - 1]
            # We have six cases: forbidden, s1.end=s2.start, s1.start=s2.end, s1.start=s2.start, s2.end=s1.end, anything else

            if nocase:
                # ignore, path after other, proper orientation, disjoint
                separate = True
                orientation = True
                path_before = False
                to_set_seg, to_set_idx, from_seg, from_idx = None, None, None, None
            elif segments_can_stitch(seg1_end, seg2_start, False, True):
                # s1.end = s2.start, path after other, proper orientation
                orientation = True
                path_before = False
                separate = False
                to_set_seg, to_set_idx, from_seg, from_idx = 0, 0, other.index - 1, 4
            elif segments_can_stitch(seg1_start, seg2_end, True, False):
                # s1.start = s2.end, path before other, proper orientation, joint
                orientation = True
                path_before = True
                separate = False
                to_set_seg, to_set_idx, from_seg, from_idx = path.index - 1, 4, 0, 0
            elif segments_can_stitch(seg1_start, seg2_start, True, True):
                # s1.start = s2.start, path before other, wrong orientation, joint
                orientation = False
                path_before = True
                separate = False
                to_set_seg, to_set_idx, from_seg, from_idx = 0, 0, 0, 0
            elif segments_can_stitch(seg1_end, seg2_end, False, False):
                # s1.end = s2. end, path after other, wrong orientation, joint
                orientation = False
                path_before = False
                separate = False
                to_set_seg, to_set_idx, from_seg, from_idx = path.index - 1, 4, other.index - 1, 4
            else:
                # ignore, path after other, proper orientation, disjoint
                separate = True
                orientation = True
                path_before = False
                to_set_seg, to_set_idx, from_seg, from_idx = None, None, None, None

            return separate, orientation, path_before, to_set_seg, to_set_idx, from_seg, from_idx


        if nostitch is None:
            nostitch = False
        tolerance = 0
        if stitchtolerance is not None:
            try:
                tolerance = float(Length(stitchtolerance))
            except ValueError:
                channel(_("Invalid tolerance distance provided"))
                return
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No item selected."))
            return
        node_label = None
        for e in data:
            if e.label is not None:
                el = e.label
                idx = el.rfind("-")
                if idx > 0:
                    el = el[:idx]
                node_label = el
                break
        node = self.elem_branch.add(type="elem path", label=node_label)
        first = True
        for e in data:
            try:
                if hasattr(e, "final_geometry"):
                    path = e.final_geometry()
                else:
                    path = e.as_geometry()
            except AttributeError:
                continue

            set_nonset_attributes(node, e)

            if first:
                node.geometry = path
                first = False
            else:
                other = node.geometry

                separate, orientation, path_before, to_set_seg, to_set_idx, from_seg, from_idx = merge_paths(other, path, nostitch, tolerance)
                if to_set_seg is not None:
                    path.segments[to_set_seg, to_set_idx] = other.segments[from_seg, from_idx]
                actionstr = 'Insert' if path_before else 'Append'
                typestr = 'regular' if orientation else 'reversed'
                channel(f"{actionstr} a {typestr} path - separate: {separate}")
                if not orientation:
                    path.reverse()
                if path_before:
                    node.geometry.insert(0, path.segments[:path.index])
                else:
                    node.geometry.append(path, end=separate)

        self.remove_elements(data)
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
        """
        Subpath is the opposite of merge. It divides non-attached paths into different node objects.
        """
        if not isinstance(data, list):
            data = list(data)
        if not data:
            return
        elements_nodes = []
        elems = []
        groups= []
        # _("Break elements")
        with self.undoscope("Break elements"):
            for node in data:
                node_label = node.label
                node_attributes = {}
                for attrib in ("stroke", "fill", "stroke_width", "stroke_scaled"):
                    if hasattr(node, attrib):
                        oldval = getattr(node, attrib, None)
                        node_attributes[attrib] = oldval
                group_node = node.replace_node(type="group", label=node_label, expanded=True)
                groups.append(group_node)
                try:
                    if hasattr(node, "final_geometry"):
                        geometry = node.final_geometry()
                    else:
                        geometry = node.as_geometry()
                    geometry.ensure_proper_subpaths()
                except AttributeError:
                    continue
                idx = 0
                for subpath in geometry.as_subpaths():
                    subpath.ensure_proper_subpaths()
                    idx += 1
                    subnode = group_node.add(
                        geometry=subpath,
                        type="elem path",
                        label=f"{node_label}-{idx}",
                        stroke=node_attributes.get("stroke", None),
                        fill=node_attributes.get("fill", None),
                    )
                    for key, value in node_attributes.items():
                        setattr(subnode, key, value)

                    elems.append(subnode)
                elements_nodes.append(group_node)
        post.append(classify_new(elems))
        self.signal("element_property_reload", groups)
        return "elements", elements_nodes

    # --------------------------- END COMMANDS ------------------------------
