import os.path
import re
from copy import copy
from math import cos, gcd, isinf, pi, sin, sqrt, tau
from random import randint, shuffle

from meerk40t.kernel import CommandSyntaxError

from ..svgelements import (
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
from .node.elem_image import ImageNode
from .node.elem_path import PathNode
from .node.node import Fillrule, Linecap, Linejoin, Node
from .node.op_cut import CutOpNode
from .node.op_dots import DotsOpNode
from .node.op_engrave import EngraveOpNode
from .node.op_hatch import HatchOpNode
from .node.op_image import ImageOpNode
from .node.op_raster import RasterOpNode
from .node.util_console import ConsoleOperation
from .node.util_input import InputOperation
from .node.util_output import OutputOperation
from .node.util_wait import WaitOperation
from .units import (
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
            "display": ("Immediate", "User confirmation", "Delay 5 seconds"),
            "choices": (0, 1, 2),
        },
    ]
    kernel.register_choices("preferences", choices)



    def classify_new(data):
        """
        Why are we doing it here? An immediate classification
        at the end of the element creation might not provide
        the right assignment as additional commands might be
        chained to it:

        e.g. "circle 1cm 1cm 1cm" will classify differently than
        "circle 1cm 1cm 1cm stroke red"

        So we apply the classify_new to the post commands.

        @return: post classification function.
        """
        def post_classify_function(**kwargs):
            if self.classify_new and len(data) > 0:
                self.classify(data)
                self.signal("tree_changed")
        return post_classify_function

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
    # WORDLISTS COMMANDS
    # ==========

    @self.console_command(
        "wordlist",
        help=_("Wordlist base operation"),
        output_type="wordlist",
    )
    def wordlist_base(command, channel, _, remainder=None, **kwargs):
        return "wordlist", ""

    @self.console_argument("key", help=_("Wordlist value"))
    @self.console_argument("value", help=_("Content"))
    @self.console_command(
        "add",
        help=_("add value to wordlist"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_add(command, channel, _, key=None, value=None, **kwargs):
        if key is not None:
            if value is None:
                value = ""
            self.mywordlist.add(key, value)
        return "wordlist", key

    @self.console_argument("key", help=_("Wordlist value"))
    @self.console_argument("value", help=_("Content"))
    @self.console_command(
        "addcounter",
        help=_("add numeric counter to wordlist"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_addcounter(command, channel, _, key=None, value=None, **kwargs):
        if key is not None:
            if value is None:
                value = 1
            else:
                try:
                    value = int(value)
                except ValueError:
                    value = 1
            self.mywordlist.add(key, value, 2)
        return "wordlist", key

    @self.console_argument("key", help=_("Wordlist value"))
    @self.console_argument("index", help=_("index to use"))
    @self.console_command(
        "get",
        help=_("get current value from wordlist"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_get(command, channel, _, key=None, index=None, **kwargs):
        if key is not None:
            result = self.mywordlist.fetch_value(skey=key, idx=index)
            channel(str(result))
        else:
            channel(_("Missing key"))
            result = ""
        return "wordlist", result

    @self.console_argument("key", help=_("Wordlist value"))
    @self.console_argument("value", help=_("Wordlist value"))
    @self.console_argument("index", help=_("index to use"))
    @self.console_command(
        "set",
        help=_("set value to wordlist"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_set(command, channel, _, key=None, value=None, index=None, **kwargs):
        if key is not None and value is not None:
            self.mywordlist.set_value(skey=key, value=value, idx=index)
        else:
            channel(_("Not enough parameters given"))
        return "wordlist", key

    @self.console_argument(
        "key", help=_("Individual wordlist value (use @ALL for all)")
    )
    @self.console_argument("index", help=_("index to use, or +2 to increment by 2"))
    @self.console_command(
        "index",
        help=_("sets index in wordlist"),
        input_type="wordlist",
        output_type="wordlist",
        all_arguments_required=True,
    )
    def wordlist_index(command, channel, _, key=None, index=None, **kwargs):
        self.mywordlist.set_index(skey=key, idx=index)
        return "wordlist", key

    @self.console_argument(
        "filename", help=_("Wordlist file (if empty use mk40-default)")
    )
    @self.console_command(
        "restore",
        help=_("Loads a previously saved wordlist"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_restore(command, channel, _, filename=None, remainder=None, **kwargs):
        new_file = filename
        if filename is not None:
            new_file = os.path.join(self.kernel.current_directory, filename)
            if not os.path.exists(new_file):
                channel(_("No such file."))
                return
        self.mywordlist.load_data(new_file)
        return "wordlist", ""

    @self.console_argument(
        "filename", help=_("Wordlist file (if empty use mk40-default)")
    )
    @self.console_command(
        "backup",
        help=_("Saves the current wordlist"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_backup(command, channel, _, filename=None, remainder=None, **kwargs):
        new_file = filename
        if filename is not None:
            new_file = os.path.join(self.kernel.current_directory, filename)

        self.mywordlist.save_data(new_file)
        return "wordlist", ""

    @self.console_argument("key", help=_("Wordlist value"))
    @self.console_command(
        "list",
        help=_("list wordlist values"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_list(command, channel, _, key=None, **kwargs):
        channel("----------")
        if key is None:
            for skey in self.mywordlist.content:
                channel(str(skey))
        else:
            if key in self.mywordlist.content:
                wordlist = self.mywordlist.content[key]
                channel(
                    _("Wordlist {name} (Type={type}, Index={index}):").format(
                        name=key, type=wordlist[0], index=wordlist[1] - 2
                    )
                )
                for idx, value in enumerate(wordlist[2:]):
                    channel(f"#{idx}: {str(value)}")
            else:
                channel(_("There is no such pattern {name}").format(name=key))
        channel("----------")
        return "wordlist", key

    @self.console_argument("filename", help=_("CSV file"))
    @self.console_command(
        "load",
        help=_("Attach a csv-file to the wordlist"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_load(command, channel, _, filename=None, **kwargs):
        if filename is None:
            channel(_("No file specified."))
            return
        new_file = os.path.join(self.kernel.current_directory, filename)
        if not os.path.exists(new_file):
            channel(_("No such file."))
            return

        rows, columns, names = self.mywordlist.load_csv_file(new_file)
        channel(_("Rows added: {rows}").format(rows=rows))
        channel(_("Values added: {values}").format(columns=columns))
        for name in names:
            channel("  " + name)
        return "wordlist", names

    # ==========
    # PENBOX COMMANDS
    # ==========

    @self.console_argument("key", help=_("Penbox key"))
    @self.console_command(
        "penbox",
        help=_("Penbox base operation"),
        input_type=None,
        output_type="penbox",
    )
    def penbox(command, channel, _, key=None, remainder=None, **kwargs):
        if remainder is None or key is None:
            channel("----------")
            if key is None:
                for key in self.penbox:
                    channel(str(key))
            else:
                try:
                    for i, value in enumerate(self.penbox[key]):
                        channel(f"{i}: {str(value)}")
                except KeyError:
                    channel(_("penbox does not exist"))
            channel("----------")
        return "penbox", key

    @self.console_argument("count", help=_("Penbox count"), type=int)
    @self.console_command(
        "add",
        help=_("add pens to the chosen penbox"),
        input_type="penbox",
        output_type="penbox",
    )
    def penbox_add(
        command, channel, _, count=None, data=None, remainder=None, **kwargs
    ):
        if count is None:
            raise CommandSyntaxError
        current = self.penbox.get(data)
        if current is None:
            current = list()
            self.penbox[data] = current
        current.extend([dict() for _ in range(count)])
        return "penbox", data

    @self.console_argument("count", help=_("Penbox count"), type=int)
    @self.console_command(
        "del",
        help=_("delete pens to the chosen penbox"),
        input_type="penbox",
        output_type="penbox",
    )
    def penbox_del(
        command, channel, _, count=None, data=None, remainder=None, **kwargs
    ):
        if count is None:
            raise CommandSyntaxError
        current = self.penbox.get(data)
        if current is None:
            current = list()
            self.penbox[data] = current
        for _ in range(count):
            try:
                del current[-1]
            except IndexError:
                break
        return "penbox", data

    @self.console_argument("index", help=_("Penbox index"), type=self.index_range)
    @self.console_argument("key", help=_("Penbox key"), type=str)
    @self.console_argument("value", help=_("Penbox key"), type=str)
    @self.console_command(
        "set",
        help=_("set value in penbox"),
        input_type="penbox",
        output_type="penbox",
    )
    def penbox_set(
        command,
        channel,
        _,
        index=None,
        key=None,
        value=None,
        data=None,
        remainder=None,
        **kwargs,
    ):
        if not value:
            raise CommandSyntaxError
        current = self.penbox.get(data)
        if current is None:
            current = list()
            self.penbox[data] = current
        rex = re.compile(r"([+-]?[0-9]+)(?:[,-]([+-]?[0-9]+))?")
        m = rex.match(value)
        if not m:
            raise CommandSyntaxError
        value = float(m.group(1))
        end = m.group(2)
        if end:
            end = float(end)

        if not end:
            for i in index:
                try:
                    current[i][key] = value
                except IndexError:
                    pass
        else:
            r = len(index)
            try:
                s = (end - value) / (r - 1)
            except ZeroDivisionError:
                s = 0
            d = 0
            for i in index:
                try:
                    current[i][key] = value + d
                except IndexError:
                    pass
                d += s
        return "penbox", data

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
            for section in self.op_data.section_set():
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
        for section in self.op_data.section_set():
            for subsect in self.op_data.derivable(section):
                label = self.op_data.read_persistent(str, subsect, "label", "-")
                channel(f"{subsect}: {label}")
        channel("----------")

    # ==========
    # PENBOX OPERATION COMMANDS
    # ==========

    @self.console_argument("key", help=_("Penbox key"))
    @self.console_command(
        "penbox_pass",
        help=_("Set the penbox_pass for the given operation"),
        input_type="ops",
        output_type="ops",
    )
    def penbox_pass(command, channel, _, key=None, remainder=None, data=None, **kwargs):
        if data is not None:
            if key is not None:
                for op in data:
                    try:
                        op.settings["penbox_pass"] = key
                        channel(f"{str(op)} penbox_pass changed to {key}.")
                    except AttributeError:
                        pass
            else:
                if key is None:
                    channel("----------")
                    for op in data:
                        try:
                            key = op.settings.get("penbox_pass")
                            if key is None:
                                channel(f"{str(op)} penbox_pass is not set.")
                            else:
                                channel(f"{str(op)} penbox_pass is set to {key}.")
                        except AttributeError:
                            pass  # No op.settings.
                    channel("----------")
        return "ops", data

    @self.console_argument("key", help=_("Penbox key"))
    @self.console_command(
        "penbox_value",
        help=_("Set the penbox_value for the given operation"),
        input_type="ops",
        output_type="ops",
    )
    def penbox_value(
        command, channel, _, key=None, remainder=None, data=None, **kwargs
    ):
        if data is not None:
            if key is not None:
                for op in data:
                    try:
                        op.settings["penbox_value"] = key
                        channel(f"{str(op)} penbox_value changed to {key}.")
                    except AttributeError:
                        pass
            else:
                if key is None:
                    channel("----------")
                    for op in data:
                        try:
                            key = op.settings.get("penbox_value")
                            if key is None:
                                channel(f"{str(op)} penbox_value is not set.")
                            else:
                                channel(f"{str(op)} penbox_value is set to {key}.")
                        except AttributeError:
                            pass  # No op.settings.
                    channel("----------")
        return "ops", data

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
                    if value == "dpi":
                        operand.append(e.dpi)
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
            # Newly created! Classification needed?
            post.append(classify_new(add_elem))
            self.signal("refresh_scene", "Scene")
            return "elements", add_elem

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
        self.signal("tree_changed")
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
    # ALIGN SUBTYPE
    # Align consist of top level node objects that can be manipulated within the scene.
    # ==========

    def _align_xy(
        channel,
        _,
        mode,
        bounds,
        elements,
        align_x=None,
        align_y=None,
        asgroup=None,
        **kwargs,
    ):
        """
        This routine prepares the data according to some validation.

        The complete validation stuff...
        """
        if elements is None:
            return
        if align_x is None or align_y is None:
            channel(_("You need to provide parameters for both x and y"))
            return
        align_bounds = None
        align_x = align_x.lower()
        align_y = align_y.lower()

        if align_x not in ("min", "max", "center", "none"):
            channel(_("Invalid alignment parameter for x"))
            return
        if align_y not in ("min", "max", "center", "none"):
            channel(_("Invalid alignment parameter for y"))
            return
        if mode == "default":
            if len(elements) < 2:
                channel(_("No sense in aligning an element to itself"))
                return
            # boundaries are the selection boundaries,
            # will be calculated later
        elif mode == "first":
            if len(elements) < 2:
                channel(_("No sense in aligning an element to itself"))
                return
            elements.sort(key=lambda n: n.emphasized_time)
            # Is there a noticeable difference?!
            # If not then we fall back to default
            if elements[0].emphasized_time != elements[1].emphasized_time:
                align_bounds = elements[0].bounds
                elements.pop(0)
        elif mode == "last":
            if len(elements) < 2:
                channel(_("No sense in aligning an element to itself"))
                return
            elements.sort(reverse=True, key=lambda n: n.emphasized_time)
            # Is there a noticeable difference?!
            # If not then we fall back to default
            if elements[0].emphasized_time != elements[1].emphasized_time:
                align_bounds = elements[0].bounds
                elements.pop(0)
        elif mode == "bed":
            align_bounds = bounds
        elif mode == "ref":
            align_bounds = bounds
        self.align_elements(
            data=elements,
            alignbounds=align_bounds,
            positionx=align_x,
            positiony=align_y,
            as_group=asgroup,
        )

    @self.console_command(
        "push",
        help=_("pushes the current align mode to the stack"),
        input_type="align",
        output_type="align",
    )
    def alignmode_push(channel, _, data, **kwargs):
        """
        Special command to push the current values on the stack
        """
        mode, group, bound, elements = data
        self._align_stack.append((mode, group, bound))
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "pop",
        help=_("pushes the current align mode to the stack"),
        input_type="align",
        output_type="align",
    )
    def alignmode_pop(channel, _, data, **kwargs):
        """
        Special command to push the current values on the stack
        """
        mode, group, bound, elements = data
        if len(self._align_stack) > 0:
            (
                self._align_mode,
                self._align_group,
                self._align_boundaries,
            ) = self._align_stack.pop()
            mode = self._align_mode
            group = self._align_group
            bound = self._align_boundaries
        channel(_("New alignmode = {mode}").format(mode=self._align_mode))
        if self._align_boundaries is not None:
            channel(
                _("Align boundaries = {bound}").format(
                    bound=str(self._align_boundaries)
                )
            )
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "group",
        help=_("Set the requested alignment to treat selection as group"),
        input_type="align",
        output_type="align",
    )
    def alignmode_first(command, channel, _, data, **kwargs):
        mode, group, bound, elements = data
        group = True
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "individual",
        help=_("Set the requested alignment to treat selection as individuals"),
        input_type="align",
        output_type="align",
    )
    def alignmode_first(command, channel, _, data, **kwargs):
        mode, group, bound, elements = data
        group = False
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "default",
        help=_("align within selection - all equal"),
        input_type="align",
        output_type="align",
    )
    def alignmode_default(channel, _, data, **kwargs):
        """
        Set the alignment mode to default
        """
        mode, group, bound, elements = data
        mode = "default"
        bound = None
        self._align_mode = mode
        self._align_boundaries = bound
        channel(_("New alignmode = {mode}").format(mode=self._align_mode))
        if self._align_boundaries is not None:
            channel(
                _("Align boundaries = {bound}").format(
                    bound=str(self._align_boundaries)
                )
            )
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "first",
        help=_("Set the requested alignment to first element selected"),
        input_type="align",
        output_type="align",
    )
    def alignmode_first(command, channel, _, data, **kwargs):
        mode, group, bound, elements = data
        mode = "first"
        bound = None
        self._align_mode = mode
        self._align_boundaries = bound
        channel(_("New alignmode = {mode}").format(mode=self._align_mode))
        if self._align_boundaries is not None:
            channel(
                _("Align boundaries = {bound}").format(
                    bound=str(self._align_boundaries)
                )
            )
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "last",
        help=_("Set the requested alignment to last element selected"),
        input_type="align",
        output_type="align",
    )
    def alignmode_last(command, channel, _, data, **kwargs):
        mode, group, bound, elements = data
        mode = "last"
        bound = None
        self._align_mode = mode
        self._align_boundaries = bound
        channel(_("New alignmode = {mode}").format(mode=self._align_mode))
        if self._align_boundaries is not None:
            channel(
                _("Align boundaries = {bound}").format(
                    bound=str(self._align_boundaries)
                )
            )
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "bed",
        help=_("Set the requested alignment to within the bed"),
        input_type="align",
        output_type="align",
    )
    def alignmode_bed(channel, _, data, **kwargs):
        mode, group, bound, elements = data
        mode = "bed"
        device_width = self.length_x("100%")
        device_height = self.length_y("100%")
        bound = (0, 0, device_width, device_height)
        self._align_mode = mode
        self._align_boundaries = bound
        channel(_("New alignmode = {mode}").format(mode=self._align_mode))
        if self._align_boundaries is not None:
            channel(
                _("Align boundaries = {bound}").format(
                    bound=str(self._align_boundaries)
                )
            )
        return "align", (mode, group, bound, elements)

    @self.console_option(
        "boundaries", "b", type=self.bounds, parallel_cast=True, nargs=4
    )
    @self.console_command(
        "ref",
        help=_("Set the requested alignment to the reference object"),
        input_type="align",
        output_type="align",
    )
    def alignmode_ref(channel, _, data, boundaries, **kwargs):
        mode, group, bound, elements = data
        if boundaries is None:
            channel(
                _("You need to provide the boundaries for align-mode {mode}").format(
                    mode="ref"
                )
            )
            return
        mode = "ref"
        bound = boundaries
        self._align_mode = mode
        self._align_boundaries = bound
        channel(_("New alignmode = {mode}").format(mode=self._align_mode))
        if self._align_boundaries is not None:
            channel(
                _("Align boundaries = {bound}").format(
                    bound=str(self._align_boundaries)
                )
            )
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "align",
        help=_("align selected elements"),
        input_type=("elements", None),
        output_type="align",
    )
    def align_elements_base(command, channel, _, data=None, remainder=None, **kwargs):
        """
        Base align commands. Triggers other base commands within the command context
        'align'.
        """
        if not remainder:
            channel(
                "top\nbottom\nleft\nright\ncenter\ncenterh\ncenterv\nspaceh\nspacev\n"
                "<any valid svg:Preserve Aspect Ratio, eg xminymin>"
            )
            # Bunch of other things.
            return
        if data is None:
            data = list(self.elems(emphasized=True))
        # Element conversion.
        # We need to establish, if for a given node within a group
        # all it's siblings are selected as well, if that's the case
        # then use the parent instead - unless there are no other elements
        # selected ie all selected belong to the same group...
        d = list()
        elem_branch = self.elem_branch
        for node in data:
            snode = node
            if snode.parent and snode.parent is not elem_branch:
                # I need all other siblings
                singular = False
                for n in list(node.parent.children):
                    if n not in data:
                        singular = True
                        break
                if not singular:
                    while (
                        snode.parent
                        and snode.parent is not elem_branch
                        and snode.parent.type != "file"
                    ):
                        snode = snode.parent
            if snode is not None and snode not in d:
                d.append(snode)
        if len(d) == 1 and d[0].type == "group":
            # This is just on single group - expand...
            data = list(d[0].flat(emphasized=True, types=elem_nodes))
            for n in data:
                n._emphasized_time = d[0]._emphasized_time
        else:
            data = d
        return "align", (
            self._align_mode,
            self._align_group,
            self._align_boundaries,
            data,
        )

    @self.console_argument(
        "alignx", type=str, help=_("One of 'min', 'center', 'max', 'none'")
    )
    @self.console_argument(
        "aligny", type=str, help=_("One of 'min', 'center', 'max', 'none'")
    )
    @self.console_command(
        "xy",
        help=_("align elements in x and y"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_xy(
        command,
        channel,
        _,
        data=None,
        alignx=None,
        aligny=None,
        **kwargs,
    ):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, alignx, aligny, group)
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "top",
        help=_("align elements at top"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_top(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, "none", "min", group)
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "bottom",
        help=_("align elements at bottom"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_bottom(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, "none", "max", group)
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "left",
        help=_("align elements at left"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_left(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, "min", "none", group)
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "right",
        help=_("align elements at right"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_right(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, "max", "none", group)
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "center",
        help=_("align elements at center"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_center(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, "center", "center", group)
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "centerh",
        help=_("align elements at center horizontally"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_centerh(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, "center", "none", group)
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "centerv",
        help=_("align elements at center vertically"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_centerv(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, "none", "center", group)
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "spaceh",
        help=_("align elements across horizontal space"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_spaceh(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        boundary_points = []
        for node in elements:
            boundary_points.append(node.bounds)
        if not len(boundary_points):
            return
        if len(elements) <= 2:  # Cannot distribute 2 or fewer items.
            return "align", (mode, group, bound, elements)
        left_edge = min([e[0] for e in boundary_points])
        right_edge = max([e[2] for e in boundary_points])
        dim_total = right_edge - left_edge
        dim_available = dim_total
        for node in elements:
            bounds = node.bounds
            dim_available -= bounds[2] - bounds[0]
        distributed_distance = dim_available / (len(elements) - 1)
        elements.sort(key=lambda n: n.bounds[0])  # sort by left edge
        dim_pos = left_edge

        haslock = False
        for node in elements:
            if hasattr(node, "lock") and node.lock and not self.lock_allows_move:
                haslock = True
                break
        if haslock:
            channel(_("Your selection contains a locked element, that cannot be moved"))
            return
        for node in elements:
            subbox = node.bounds
            delta = subbox[0] - dim_pos
            matrix = f"translate({-delta}, 0)"
            if delta != 0:
                for q in node.flat(types=elem_nodes):
                    try:
                        q.matrix *= matrix
                        q.modified()
                    except AttributeError:
                        continue
            dim_pos += subbox[2] - subbox[0] + distributed_distance
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "spacev",
        help=_("align elements down vertical space"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_spacev(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        boundary_points = []
        for node in elements:
            boundary_points.append(node.bounds)
        if not len(boundary_points):
            return
        if len(elements) <= 2:  # Cannot distribute 2 or fewer items.
            return "align", (mode, group, bound, elements)
        top_edge = min([e[1] for e in boundary_points])
        bottom_edge = max([e[3] for e in boundary_points])
        dim_total = bottom_edge - top_edge
        dim_available = dim_total
        for node in elements:
            bounds = node.bounds
            dim_available -= bounds[3] - bounds[1]
        distributed_distance = dim_available / (len(elements) - 1)
        elements.sort(key=lambda n: n.bounds[1])  # sort by top edge
        dim_pos = top_edge

        haslock = False
        for node in elements:
            if hasattr(node, "lock") and node.lock and not self.lock_allows_move:
                haslock = True
                break
        if haslock:
            channel(_("Your selection contains a locked element, that cannot be moved"))
            return
        for node in elements:
            subbox = node.bounds
            delta = subbox[1] - dim_pos
            matrix = f"translate(0, {-delta})"
            if delta != 0:
                for q in node.flat(types=elem_nodes):
                    try:
                        q.matrix *= matrix
                        q.modified()
                    except AttributeError:
                        continue
            dim_pos += subbox[3] - subbox[1] + distributed_distance
        return "align", (mode, group, bound, elements)

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
        mode, group, bound, elements = data
        boundary_points = []
        for node in elements:
            boundary_points.append(node.bounds)
        if not len(boundary_points):
            return

        haslock = False
        for node in elements:
            if hasattr(node, "lock") and node.lock and not self.lock_allows_move:
                haslock = True
                break
        if haslock:
            channel(_("Your selection contains a locked element, that cannot be moved"))
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
            for node in elements:
                device_width = self.length_x("100%")
                device_height = self.length_y("100%")

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
                for q in node.flat(types=elem_nodes):
                    try:
                        q.matrix *= matrix
                        q.modified()
                    except AttributeError:
                        continue
                for q in node.flat(types=("file", "group")):
                    q.modified()
        return "align", (mode, group, bound, elements)

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
        x = float(Length(x, relative_length=Length(amount=width).length_mm))
        y = float(Length(y, relative_length=Length(amount=height).length_mm))
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
                    e.modified()
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
                if hasattr(e, "fillrule"):
                    e.fillrule = 0
                mydata.append(e)
            else:
                mydata.append(node)

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

        # self.elem_branch.add_node(data_node)
        # self.elem_branch.add_node(image_node_1)

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
            # self.elem_branch.add_node(image_node_2)
            # self.elem_branch.add_node(data_node_2)
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
                    # self.elem_branch.add_node(data_node)
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
    # ELEMENT/SHAPE COMMANDS
    # ==========
    @self.console_argument("x_pos", type=Length)
    @self.console_argument("y_pos", type=Length)
    @self.console_argument("r_pos", type=Length)
    @self.console_command(
        "circle",
        help=_("circle <x> <y> <r>"),
        input_type=("elements", None),
        output_type="elements",
        all_arguments_required=True,
    )
    def element_circle(channel, _, x_pos, y_pos, r_pos, data=None, post=None, **kwargs):
        circ = Ellipse(cx=float(x_pos), cy=float(y_pos), r=float(r_pos))
        if circ.is_degenerate():
            channel(_("Shape is degenerate."))
            return "elements", data
        node = self.elem_branch.add(
            shape=circ,
            type="elem ellipse",
            stroke=self.default_stroke,
            fill=self.default_fill,
        )
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument("r_pos", type=Length)
    @self.console_command(
        "circle_r",
        help=_("circle_r <r>"),
        input_type=("elements", None),
        output_type="elements",
        all_arguments_required=True,
    )
    def element_circle_r(channel, _, r_pos, data=None, post=None, **kwargs):
        circ = Ellipse(r=float(r_pos))
        if circ.is_degenerate():
            channel(_("Shape is degenerate."))
            return "elements", data
        node = self.elem_branch.add(shape=circ, type="elem ellipse")
        node.stroke = self.default_stroke
        node.fill = self.default_fill
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument("x_pos", type=Length)
    @self.console_argument("y_pos", type=Length)
    @self.console_argument("rx_pos", type=Length)
    @self.console_argument("ry_pos", type=Length)
    @self.console_command(
        "ellipse",
        help=_("ellipse <cx> <cy> <rx> <ry>"),
        input_type=("elements", None),
        output_type="elements",
        all_arguments_required=True,
    )
    def element_ellipse(channel, _, x_pos, y_pos, rx_pos, ry_pos, data=None, post=None, **kwargs):
        ellip = Ellipse(
            cx=float(x_pos), cy=float(y_pos), rx=float(rx_pos), ry=float(ry_pos)
        )
        if ellip.is_degenerate():
            channel(_("Shape is degenerate."))
            return "elements", data
        node = self.elem_branch.add(shape=ellip, type="elem ellipse")
        node.stroke = self.default_stroke
        node.fill = self.default_fill
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument(
        "x_pos",
        type=self.length_x,
        help=_("x position for top left corner of rectangle."),
    )
    @self.console_argument(
        "y_pos",
        type=self.length_y,
        help=_("y position for top left corner of rectangle."),
    )
    @self.console_argument(
        "width", type=self.length_x, help=_("width of the rectangle.")
    )
    @self.console_argument(
        "height", type=self.length_y, help=_("height of the rectangle.")
    )
    @self.console_option(
        "rx", "x", type=self.length_x, help=_("rounded rx corner value.")
    )
    @self.console_option(
        "ry", "y", type=self.length_y, help=_("rounded ry corner value.")
    )
    @self.console_command(
        "rect",
        help=_("adds rectangle to scene"),
        input_type=("elements", None),
        output_type="elements",
        all_arguments_required=True,
    )
    def element_rect(
        channel,
        _,
        x_pos,
        y_pos,
        width,
        height,
        rx=None,
        ry=None,
        data=None,
        post=None,
        **kwargs,
    ):
        """
        Draws a svg rectangle with optional rounded corners.
        """
        rect = Rect(x=x_pos, y=y_pos, width=width, height=height, rx=rx, ry=ry)
        if rect.is_degenerate():
            channel(_("Shape is degenerate."))
            return "elements", data
        node = self.elem_branch.add(shape=rect, type="elem rect")
        node.stroke = self.default_stroke
        node.fill = self.default_fill
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument("x0", type=self.length_x, help=_("start x position"))
    @self.console_argument("y0", type=self.length_y, help=_("start y position"))
    @self.console_argument("x1", type=self.length_x, help=_("end x position"))
    @self.console_argument("y1", type=self.length_y, help=_("end y position"))
    @self.console_command(
        "line",
        help=_("adds line to scene"),
        input_type=("elements", None),
        output_type="elements",
        all_arguments_required=True,
    )
    def element_line(command, x0, y0, x1, y1, data=None, post=None, **kwargs):
        """
        Draws a svg line in the scene.
        """
        simple_line = SimpleLine(x0, y0, x1, y1)
        node = self.elem_branch.add(shape=simple_line, type="elem line")
        node.stroke = self.default_stroke
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_option(
        "size", "s", type=float, default=16, help=_("font size to for object")
    )
    @self.console_argument("text", type=str, help=_("quoted string of text"))
    @self.console_command(
        "text",
        help=_("text <text>"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_text(command, channel, _, data=None, text=None, size=None, post=None,  **kwargs):
        if text is None:
            channel(_("No text specified"))
            return
        node = self.elem_branch.add(
            text=text, matrix=Matrix(f"scale({UNITS_PER_PIXEL})"), type="elem text"
        )
        node.font_size = size
        node.stroke = self.default_stroke
        node.fill = self.default_fill
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument(
        "anchor", type=str, default="start", help=_("set text anchor")
    )
    @self.console_command(
        "text-anchor",
        help=_("set text object text-anchor; start, middle, end"),
        input_type=(
            None,
            "elements",
        ),
        hidden=True,
        output_type="elements",
    )
    def element_text_anchor(command, channel, _, data, anchor=None, **kwargs):
        if anchor not in ("start", "middle", "end"):
            raise CommandSyntaxError(
                _("Only 'start', 'middle', and 'end' are valid anchors.")
            )
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        for e in data:
            if hasattr(e, "lock") and e.lock:
                channel(_("Can't modify a locked element: {name}").format(name=str(e)))
                continue
            if e.type == "elem text":
                old_anchor = e.anchor
                e.anchor = anchor
                channel(f"Node {e} anchor changed from {old_anchor} to {anchor}")

            e.altered()
        return "elements", data

    @self.console_command("simplify", input_type=("elements", None), output_type="elements")
    def simplify_path(command, channel, _,  data=None, post=None, **kwargs):

        if data is None:
            data = list(self.elems(emphasized=True))
        data_changed = list()
        if len(data) == 0:
            channel("Requires a selected polygon")
            return None
        for node in data:
            changed, before, after = self.simplify_node(node)
            if changed:
                s = node.type
                channel(f"Simplified {s} ({node.label}): from {before} to {after}")
                node.altered()
                data_changed.append(node)
        if len(data_changed)>0:
            self.signal("element_property_update", data_changed)
            self.signal("refresh_scene", "Scene")
        return "elements", data

    @self.console_command("polycut", input_type=("elements", None), output_type="elements")
    def create_pattern(command, channel, _,  data=None, post=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) <= 1:
            channel("Requires a selected cutter polygon")
            return None
        data.sort(key=lambda n: n.emphasized_time)
        outer_path = data[0].as_path()
        inner_path = data[1].as_path()
        data[1].remove_node()

        from meerk40t.tools.pathtools import VectorMontonizer
        vm = VectorMontonizer()
        outer_path = Polygon(
            [outer_path.point(i / 1000.0, error=1e4) for i in range(1001)]
        )
        vm.add_polyline(outer_path)
        path = Path()
        for sub_inner in inner_path.as_subpaths():
            sub_inner = Path(sub_inner)
            pts_sub = [sub_inner.point(i / 1000.0, error=1e4) for i in range(1001)]
            for i in range(len(pts_sub)-1, -1, -1):
                pt = pts_sub[i]
                if not vm.is_point_inside(pt[0], pt[1]):
                    del pts_sub[i]
            path += Path(Polyline(pts_sub))
        node = self.elem_branch.add(path=path, type="elem path")
        data.append(node)
        node.stroke = self.default_stroke
        node.fill = self.default_fill
        node.altered()
        node.focus()
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument("mlist", type=Length, help=_("list of positions"), nargs="*")
    @self.console_command(
        ("polygon", "polyline"),
        help=_("poly(gon|line) (Length Length)*"),
        input_type=("elements", None),
        output_type="elements",
        all_arguments_required=True,
    )
    def element_poly(command, channel, _, mlist, data=None, post=None, **kwargs):
        try:
            pts = [float(Length(p)) for p in mlist]
            if command == "polygon":
                shape = Polygon(pts)
            else:
                shape = Polyline(pts)
        except ValueError:
            raise CommandSyntaxError(
                _("Must be a list of spaced delimited length pairs.")
            )
        if shape.is_degenerate():
            channel(_("Shape is degenerate."))
            return "elements", data
        node = self.elem_branch.add(shape=shape, type="elem polyline")
        node.stroke = self.default_stroke
        node.fill = self.default_fill
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_command(
        "path",
        help=_("Convert any shapes to paths"),
        input_type="shapes",
        output_type="shapes",
    )
    def element_path_convert(data, **kwargs):
        paths = []
        for e in data:
            paths.append(abs(Path(e)))
        return "shapes", paths

    @self.console_command(
        "geomstr",
        help=_("Convert any element nodes to geomstr nodes"),
        input_type="elements",
        output_type="elements",
    )
    def element_path_convert(data, **kwargs):
        if data is None:
            return "elements", data
        if len(data) == 0:
            return "elements", data

        from meerk40t.tools.geomstr import Geomstr
        geomstr = Geomstr()
        for node in data:
            try:
                e = node.as_path()
            except AttributeError:
                continue
            for seg in e:
                if isinstance(seg, Line):
                    geomstr.line(complex(seg.start), complex(seg.end))
                elif isinstance(seg, QuadraticBezier):
                    geomstr.quad(
                        complex(seg.start), complex(seg.control), complex(seg.end)
                    )
                elif isinstance(seg, CubicBezier):
                    geomstr.cubic(
                        complex(seg.start),
                        complex(seg.control1),
                        complex(seg.control2),
                        complex(seg.end),
                    )
                elif isinstance(seg, Close):
                    geomstr.close()
                    geomstr.end()
            geomstr.end()
        if len(geomstr) == 0:
            return "elements", data
        try:
            fillrule = data[0].fillrule
        except AttributeError:
            fillrule = None
        try:
            cap = data[0].linecap
        except AttributeError:
            cap = None
        try:
            join = data[0].linejoin
        except AttributeError:
            join = None
        node = self.elem_branch.add(
            path=geomstr,
            type="elem geomstr",
            stroke=data[0].stroke,
            fill=data[0].fill,
            fillrule=fillrule,
            linecap=cap,
            linejoin=join,
        )
        self.set_emphasis([node])
        node.focus()
        data.append(node)
        return "elements", data

    @self.console_command(
        "path",
        help=_("Convert any element nodes to paths"),
        input_type="elements",
        output_type="shapes",
    )
    def element_path_convert(data, **kwargs):
        paths = []
        for node in data:
            try:
                e = node.as_path()
            except AttributeError:
                continue
            paths.append(e)
        return "shapes", paths

    @self.console_option(
        "real",
        "r",
        action="store_true",
        type=bool,
        help="Display non-transformed path",
    )
    @self.console_command(
        "path_d_info",
        help=_("List the path_d of any recognized paths"),
        input_type="elements",
    )
    def element_pathd_info(command, channel, _, data, real=True, **kwargs):
        for node in data:
            try:
                if node.path.transform.is_identity():
                    channel(
                        f"{str(node)} (Identity): {node.path.d(transformed=not real)}"
                    )
                else:
                    channel(f"{str(node)}: {node.path.d(transformed=not real)}")
            except AttributeError:
                channel(f"{str(node)}: Invalid")

    @self.console_argument(
        "path_d", type=str, help=_("svg path syntax command (quoted).")
    )
    @self.console_command(
        "path",
        help=_("path <svg path>"),
        output_type="elements",
    )
    def element_path(path_d, data, post=None, **kwargs):
        if path_d is None:
            raise CommandSyntaxError(_("Not a valid path_d string"))
        try:
            path = Path(path_d)
            path *= f"Scale({UNITS_PER_PIXEL})"
        except ValueError:
            raise CommandSyntaxError(_("Not a valid path_d string (try quotes)"))

        node = self.elem_branch.add(path=path, type="elem path")
        node.stroke = self.default_stroke
        node.fill = self.default_fill
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument(
        "stroke_width",
        type=self.length,
        help=_("Stroke-width for the given stroke"),
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
    def element_stroke_width(command, channel, _, stroke_width, data=None, **kwargs):
        def width_string(value):
            if value is None:
                return "-"
            res = ""
            display_units = (
                (1, ""),
                (UNITS_PER_PIXEL, "px"),
                (UNITS_PER_POINT, "pt"),
                (UNITS_PER_MM, "mm"),
            )
            for unit in display_units:
                unit_value = value / unit[0]
                if res != "":
                    res += ", "
                res += f"{unit_value:.3f}{unit[1]}"
            return res

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
                if not hasattr(e, "stroke_width"):
                    pass
                elif not hasattr(e, "stroke_scaled"):
                    channel(
                        _(
                            "{index}: {name} - {typename}\n   stroke-width = {stroke_width}\n   scaled-width = {scaled_stroke_width}"
                        ).format(
                            index=i,
                            typename="scaled-stroke",
                            stroke_width=width_string(e.stroke_width),
                            scaled_stroke_width=width_string(None),
                            name=name,
                        )
                    )
                else:
                    if e.stroke_scaled:
                        typename = "scaled-stroke"
                        factor = sqrt(e.matrix.determinant)
                    else:
                        typename = "non-scaling-stroke"
                        factor = 1.0
                    implied_value = factor * e.stroke_width
                    channel(
                        _(
                            "{index}: {name} - {typename}\n   stroke-width = {stroke_width}\n   scaled-width = {scaled_stroke_width}"
                        ).format(
                            index=i,
                            typename=typename,
                            stroke_width=width_string(e.stroke_width),
                            scaled_stroke_width=width_string(implied_value),
                            name=name,
                        )
                    )
                i += 1
            channel("----------")
            return

        if len(data) == 0:
            channel(_("No selected elements."))
            return
        for e in data:
            if hasattr(e, "lock") and e.lock:
                channel(_("Can't modify a locked element: {name}").format(name=str(e)))
                continue
            stroke_scale = sqrt(e.matrix.determinant) if e.stroke_scaled else 1.0
            e.stroke_width = stroke_width / stroke_scale
            e.altered()
        return "elements", data

    @self.console_command(
        ("enable_stroke_scale", "disable_stroke_scale"),
        help=_("stroke-width <length>"),
        input_type=(
            None,
            "elements",
        ),
        hidden=True,
        output_type="elements",
    )
    def element_stroke_scale_enable(command, channel, _, data=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        for e in data:
            if hasattr(e, "lock") and e.lock:
                channel(_("Can't modify a locked element: {name}").format(name=str(e)))
                continue
            e.stroke_scaled = command == "enable_stroke_scale"
            e.altered()
        return "elements", data

    @self.console_option("filter", "f", type=str, help="Filter indexes")
    @self.console_argument(
        "cap",
        type=str,
        help=_("Linecap to apply to the path (one of butt, round, square)"),
    )
    @self.console_command(
        "linecap",
        help=_("linecap <cap>"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
    )
    def element_cap(command, channel, _, cap=None, data=None, filter=None, **kwargs):
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
                    channel(_("index {index} out of range").format(index=value))
        if cap is None:
            channel("----------")
            channel(_("Linecaps:"))
            i = 0
            for e in self.elems():
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                if hasattr(e, "linecap"):
                    if e.linecap == Linecap.CAP_SQUARE:
                        capname = "square"
                    elif e.linecap == Linecap.CAP_BUTT:
                        capname = "butt"
                    else:
                        capname = "round"
                    channel(
                        _("{index}: linecap = {linecap} - {name}").format(
                            index=i, linecap=capname, name=name
                        )
                    )
                i += 1
            channel("----------")
            return
        else:
            capvalue = None
            if cap.lower() == "butt":
                capvalue = Linecap.CAP_BUTT
            elif cap.lower() == "round":
                capvalue = Linecap.CAP_ROUND
            elif cap.lower() == "square":
                capvalue = Linecap.CAP_SQUARE
            if capvalue is not None:
                for e in apply:
                    if hasattr(e, "linecap"):
                        if hasattr(e, "lock") and e.lock:
                            channel(
                                _("Can't modify a locked element: {name}").format(
                                    name=str(e)
                                )
                            )
                            continue
                        e.linecap = capvalue
                        e.altered()
            return "elements", data

    @self.console_option("filter", "f", type=str, help="Filter indexes")
    @self.console_argument(
        "join",
        type=str,
        help=_(
            "jointype to apply to the path (one of arcs, bevel, miter, miter-clip, round)"
        ),
    )
    @self.console_command(
        "linejoin",
        help=_("linejoin <join>"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
    )
    def element_join(command, channel, _, join=None, data=None, filter=None, **kwargs):
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
                    channel(_("index {index} out of range").format(index=value))
        if join is None:
            channel("----------")
            channel(_("Linejoins:"))
            i = 0
            for e in self.elems():
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                if hasattr(e, "linejoin"):
                    if e.linejoin == Linejoin.JOIN_ARCS:
                        joinname = "arcs"
                    elif e.linejoin == Linejoin.JOIN_BEVEL:
                        joinname = "bevel"
                    elif e.linejoin == Linejoin.JOIN_MITER_CLIP:
                        joinname = "miter-clip"
                    elif e.linejoin == Linejoin.JOIN_MITER:
                        joinname = "miter"
                    elif e.linejoin == Linejoin.JOIN_ROUND:
                        joinname = "round"
                    channel(
                        _("{index}: linejoin = {linejoin} - {name}").format(
                            index=i, linejoin=joinname, name=name
                        )
                    )
                i += 1
            channel("----------")
            return
        else:
            joinvalue = None
            if join.lower() == "arcs":
                joinvalue = Linejoin.JOIN_ARCS
            elif join.lower() == "bevel":
                joinvalue = Linejoin.JOIN_BEVEL
            elif join.lower() == "miter":
                joinvalue = Linejoin.JOIN_MITER
            elif join.lower() == "miter-clip":
                joinvalue = Linejoin.JOIN_MITER_CLIP
            elif join.lower() == "round":
                joinvalue = Linejoin.JOIN_ROUND
            if joinvalue is not None:
                for e in apply:
                    if hasattr(e, "linejoin"):
                        if hasattr(e, "lock") and e.lock:
                            channel(
                                _("Can't modify a locked element: {name}").format(
                                    name=str(e)
                                )
                            )
                            continue
                        e.linejoin = joinvalue
                        e.altered()
            return "elements", data

    @self.console_option("filter", "f", type=str, help="Filter indexes")
    @self.console_argument(
        "rule",
        type=str,
        help=_("rule to apply to fill the path (one of {nonzero}, {evenodd})").format(
            nonzero=SVG_RULE_NONZERO, evenodd=SVG_RULE_EVENODD
        ),
    )
    @self.console_command(
        "fillrule",
        help=_("fillrule <rule>"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
    )
    def element_rule(command, channel, _, rule=None, data=None, filter=None, **kwargs):
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
                    channel(_("index {index} out of range").format(index=value))
        if rule is None:
            channel("----------")
            channel(_("fillrules:"))
            i = 0
            for e in self.elems():
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                if hasattr(e, "fillrule"):
                    if e.fillrule == Fillrule.FILLRULE_EVENODD:
                        rulename = SVG_RULE_EVENODD
                    elif e.fillrule == Fillrule.FILLRULE_NONZERO:
                        rulename = SVG_RULE_NONZERO
                    channel(
                        _("{index}: fillrule = {fillrule} - {name}").format(
                            index=i, fillrule=rulename, name=name
                        )
                    )
                i += 1
            channel("----------")
            return
        else:
            rulevalue = None
            if rule.lower() == SVG_RULE_EVENODD:
                rulevalue = Fillrule.FILLRULE_EVENODD
            elif rule.lower() == SVG_RULE_NONZERO:
                rulevalue = Fillrule.FILLRULE_NONZERO
            if rulevalue is not None:
                for e in apply:
                    if hasattr(e, "fillrule"):
                        if hasattr(e, "lock") and e.lock:
                            channel(
                                _("Can't modify a locked element: {name}").format(
                                    name=str(e)
                                )
                            )
                            continue
                        e.fillrule = rulevalue
                        e.altered()
            return "elements", data

    @self.console_option(
        "classify", "c", type=bool, action="store_true", help="Reclassify element"
    )
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
        command, channel, _, color, data=None, classify=None, filter=None, **kwargs
    ):
        if data is None:
            data = list(self.elems(emphasized=True))
            was_emphasized = True
            old_first = self.first_emphasized
        else:
            was_emphasized = False
            old_first = None
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
                    channel(_("index {index} out of range").format(index=value))
        if color is None:
            channel("----------")
            channel(_("Stroke Values:"))
            i = 0
            for e in self.elems():
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                if not hasattr(e, "stroke"):
                    pass
                elif hasattr(e, "stroke") and e.stroke is None or e.stroke == "none":
                    channel(f"{i}: stroke = none - {name}")
                else:
                    channel(f"{i}: stroke = {e.stroke.hex} - {name}")
                i += 1
            channel("----------")
            return
        elif color == "none":
            for e in apply:
                if hasattr(e, "lock") and e.lock:
                    channel(
                        _("Can't modify a locked element: {name}").format(name=str(e))
                    )
                    continue
                e.stroke = None
                e.altered()
        else:
            for e in apply:
                if hasattr(e, "lock") and e.lock:
                    channel(
                        _("Can't modify a locked element: {name}").format(name=str(e))
                    )
                    continue
                e.stroke = Color(color)
                e.altered()
        if classify is None:
            classify = False
        if classify:
            self.remove_elements_from_operations(apply)
            self.classify(apply)
            if was_emphasized:
                for e in apply:
                    e.emphasized = True
                if len(apply) == 1:
                    apply[0].focus()
            if old_first is not None and old_first in apply:
                self.first_emphasized = old_first
            else:
                self.first_emphasized = None
            # self.signal("rebuild_tree")
            self.signal("refresh_tree", apply)
        return "elements", data

    @self.console_option(
        "classify", "c", type=bool, action="store_true", help="Reclassify element"
    )
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
    def element_fill(
        command, channel, _, color, data=None, classify=None, filter=None, **kwargs
    ):
        if data is None:
            data = list(self.elems(emphasized=True))
            was_emphasized = True
            old_first = self.first_emphasized
        else:
            was_emphasized = False
            old_first = None
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
                    channel(_("index {index} out of range").format(index=value))
        if color is None:
            channel("----------")
            channel(_("Fill Values:"))
            i = 0
            for e in self.elems():
                name = str(e)
                if len(name) > 50:
                    name = name[:50] + "…"
                if not hasattr(e, "fill"):
                    pass
                elif e.fill is None or e.fill == "none":
                    channel(
                        _("{index}: fill = none - {name}").format(index=i, name=name)
                    )
                else:
                    channel(
                        _("{index}: fill = {fill} - {name}").format(
                            index=i, fill=e.fill.hex, name=name
                        )
                    )
                i += 1
            channel("----------")
            return "elements", data
        elif color == "none":
            for e in apply:
                if hasattr(e, "lock") and e.lock:
                    channel(
                        _("Can't modify a locked element: {name}").format(name=str(e))
                    )
                    continue
                e.fill = None
                e.altered()
        else:
            for e in apply:
                if hasattr(e, "lock") and e.lock:
                    channel(
                        _("Can't modify a locked element: {name}").format(name=str(e))
                    )
                    continue
                e.fill = Color(color)
                e.altered()
        if classify is None:
            classify = False
        if classify:
            self.remove_elements_from_operations(apply)
            self.classify(apply)
            if was_emphasized:
                for e in apply:
                    e.emphasized = True
                if len(apply) == 1:
                    apply[0].focus()
            if old_first is not None and old_first in apply:
                self.first_emphasized = old_first
            else:
                self.first_emphasized = None
            self.signal("refresh_tree", apply)
        #                self.signal("rebuild_tree")
        return "elements", data

    @self.console_argument(
        "x_offset", type=self.length_x, help=_("x offset."), default="0"
    )
    @self.console_argument(
        "y_offset", type=self.length_y, help=_("y offset"), default="0"
    )
    @self.console_command(
        "frame",
        help=_("Draws a frame the current selected elements"),
        input_type=(
            None,
            "elements",
        ),
        output_type="elements",
    )
    def element_frame(
        command,
        channel,
        _,
        x_offset=None,
        y_offset=None,
        data=None,
        post=None,
        **kwargs,
    ):
        """
        Draws an outline of the current shape.
        """
        bounds = self.selected_area()
        if bounds is None:
            channel(_("Nothing Selected"))
            return
        x_pos = bounds[0]
        y_pos = bounds[1]
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        x_pos -= x_offset
        y_pos -= y_offset
        width += x_offset * 2
        height += y_offset * 2
        _element = Rect(x=x_pos, y=y_pos, width=width, height=height)
        node = self.elem_branch.add(shape=_element, type="elem rect")
        node.stroke = Color("red")
        node.altered()
        self.set_emphasis([node])
        node.focus()
        if data is None:
            data = list()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    @self.console_argument("angle", type=Angle.parse, help=_("angle to rotate by"))
    @self.console_option("cx", "x", type=self.length_x, help=_("center x"))
    @self.console_option("cy", "y", type=self.length_y, help=_("center y"))
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
            for node in self.elems():
                name = str(node)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(
                    _("{index}: rotate({angle}turn) - {name}").format(
                        index=i, angle=node.matrix.rotation.as_turns, name=name
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
        self.validate_selected_area()
        bounds = self.selected_area()
        if bounds is None:
            channel(_("No selected elements."))
            return
        rot = angle.as_degrees

        if cx is None:
            cx = (bounds[2] + bounds[0]) / 2.0
        if cy is None:
            cy = (bounds[3] + bounds[1]) / 2.0
        matrix = Matrix(f"rotate({rot}deg,{cx},{cy})")
        images = []
        try:
            if not absolute:
                for node in data:
                    if hasattr(node, "lock") and node.lock:
                        continue

                    node.matrix *= matrix
                    node.modified()
                    if hasattr(node, "update"):
                        images.append(node)
            else:
                for node in data:
                    start_angle = node.matrix.rotation
                    amount = rot - start_angle
                    matrix = Matrix(f"rotate({Angle(amount).as_degrees},{cx},{cy})")
                    node.matrix *= matrix
                    node.modified()
                    if hasattr(node, "update"):
                        images.append(node)
        except ValueError:
            raise CommandSyntaxError
        for node in images:
            node.update(None)
        self.signal("refresh_scene", "Scene")
        return "elements", data

    @self.console_argument("scale_x", type=str, help=_("scale_x value"))
    @self.console_argument("scale_y", type=str, help=_("scale_y value"))
    @self.console_option("px", "x", type=self.length_x, help=_("scale x origin point"))
    @self.console_option("py", "y", type=self.length_y, help=_("scale y origin point"))
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
            for node in self.elems():
                name = str(node)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(
                    f"{i}: scale({node.matrix.value_scale_x()}, {node.matrix.value_scale_y()}) - {name}"
                )
                i += 1
            channel("----------")
            return
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        # print (f"Start: {scale_x} ({type(scale_x).__name__}), {scale_y} ({type(scale_y).__name__})")
        factor = 1
        if scale_x.endswith("%"):
            factor = 0.01
            scale_x = scale_x[:-1]
        try:
            scale_x = factor * float(scale_x)
        except ValueError:
            scale_x = 1
        if scale_y is None:
            scale_y = scale_x
        else:
            factor = 1
            if scale_y.endswith("%"):
                factor = 0.01
                scale_y = scale_y[:-1]
            try:
                scale_y = factor * float(scale_y)
            except ValueError:
                scale_y = 1
        # print (f"End: {scale_x} ({type(scale_x).__name__}), {scale_y} ({type(scale_y).__name__})")

        bounds = Node.union_bounds(data)
        if px is None:
            px = (bounds[2] + bounds[0]) / 2.0
        if py is None:
            py = (bounds[3] + bounds[1]) / 2.0
        if scale_x == 0 or scale_y == 0:
            channel(_("Scaling by Zero Error"))
            return
        matrix = Matrix(f"scale({scale_x},{scale_y},{px},{py})")
        images = []
        try:
            if not absolute:
                for node in data:
                    if hasattr(node, "lock") and node.lock:
                        continue
                    node.matrix *= matrix
                    node.modified()
                    if hasattr(node, "update"):
                        images.append(node)
            else:
                for node in data:
                    if hasattr(node, "lock") and node.lock:
                        continue
                    osx = node.matrix.value_scale_x()
                    osy = node.matrix.value_scale_y()
                    nsx = scale_x / osx
                    nsy = scale_y / osy
                    matrix = Matrix(f"scale({nsx},{nsy},{px},{px})")
                    node.matrix *= matrix
                    node.modified()
                    if hasattr(node, "update"):
                        images.append(node)
        except ValueError:
            raise CommandSyntaxError
        for node in images:
            node.update(None)
        self.signal("refresh_scene", "Scene")
        return "elements", data

    @self.console_option(
        "new_area", "n", type=self.area, help=_("provide a new area to cover")
    )
    @self.console_option(
        "density", "d", type=int, help=_("Defines the interpolation density")
    )
    @self.console_command(
        "area",
        help=_("provides information about/changes the area of a selected element"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_area(
        command,
        channel,
        _,
        new_area=None,
        density=None,
        data=None,
        **kwargs,
    ):
        if density is None:
            density = 200
        if new_area is None:
            display_only = True
        else:
            if new_area == 0:
                channel(_("You shouldn't collapse a shape to a zero-sized thing"))
                return
            display_only = False
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        total_area = 0
        if display_only:
            channel("----------")
            channel(_("Area values (Density={density})").format(density=density))

        units = ("mm", "cm", "in")
        square_unit = [0] * len(units)
        for idx, u in enumerate(units):
            value = float(Length(f"1{u}"))
            square_unit[idx] = value * value

        i = 0
        for elem in data:
            this_area, this_length = self.get_information(elem, density=density)

            if display_only:
                name = str(elem)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(f"{i}: {name}")
                for idx, u in enumerate(units):
                    this_area_local = this_area / square_unit[idx]
                    channel(
                        _(" Area= {area:.3f} {unit}²").format(
                            area=this_area_local, unit=u
                        )
                    )
            i += 1
            total_area += this_area
        if display_only:
            channel("----------")
        else:
            if total_area == 0:
                channel(_("You can't reshape a zero-sized shape"))
                return

            ratio = sqrt(new_area / total_area)
            self(f"scale {ratio}\n")

        return "elements", data
        # Do we have a new value to set? If yes scale by sqrt(of the fraction)

    @self.console_argument("tx", type=self.length_x, help=_("translate x value"))
    @self.console_argument("ty", type=self.length_y, help=_("translate y value"))
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
            for node in self.elems():
                name = str(node)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(
                    f"{i}: translate({node.matrix.value_trans_x():.1f}, {node.matrix.value_trans_y():.1f}) - {name}"
                )
                i += 1
            channel("----------")
            return
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        if tx is None:
            tx = 0
        if ty is None:
            ty = 0
        matrix = Matrix.translate(tx, ty)
        try:
            if not absolute:
                for node in data:
                    if (
                        hasattr(node, "lock")
                        and node.lock
                        and not self.lock_allows_move
                    ):
                        continue

                    node.matrix *= matrix
                    node.modified()
            else:
                for node in data:
                    if (
                        hasattr(node, "lock")
                        and node.lock
                        and not self.lock_allows_move
                    ):
                        continue
                    otx = node.matrix.value_trans_x()
                    oty = node.matrix.value_trans_y()
                    ntx = tx - otx
                    nty = ty - oty
                    matrix = Matrix.translate(ntx, nty)
                    node.matrix *= matrix
                    node.modified()
        except ValueError:
            raise CommandSyntaxError
        return "elements", data

    @self.console_argument("tx", type=self.length_x, help=_("New x value"))
    @self.console_argument("ty", type=self.length_y, help=_("New y value"))
    @self.console_command(
        "position",
        help=_("position <tx> <ty>"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_position(
        command, channel, _, tx, ty, absolute=False, data=None, **kwargs
    ):
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        if tx is None or ty is None:
            channel(_("You need to provide a new position."))
            return

        dbounds = Node.union_bounds(data)
        for node in data:
            if hasattr(node, "lock") and node.lock and not self.lock_allows_move:
                continue
            nbounds = node.bounds
            dx = tx - dbounds[0]
            dy = ty - dbounds[1]
            if dx != 0 or dy != 0:
                node.matrix.post_translate(dx, dy)
            node.modified()
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
            bounds = Node.union_bounds(data)
            otx = bounds[0]
            oty = bounds[1]
            ntx = tx - otx
            nty = ty - oty
            for node in data:
                if hasattr(node, "lock") and node.lock and not self.lock_allows_move:
                    continue
                node.matrix.post_translate(ntx, nty)
                node.modified()
        except ValueError:
            raise CommandSyntaxError
        return "elements", data

    @self.console_argument(
        "x_pos", type=self.length_x, help=_("x position for top left corner")
    )
    @self.console_argument(
        "y_pos", type=self.length_y, help=_("y position for top left corner")
    )
    @self.console_argument("width", type=self.length_x, help=_("new width of selected"))
    @self.console_argument(
        "height", type=self.length_y, help=_("new height of selected")
    )
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
            x, y, x1, y1 = area
            w, h = x1 - x, y1 - y
            if w == 0 or h == 0:  # dot
                channel(_("resize: cannot resize a dot"))
                return
            sx = width / w
            sy = height / h
            # Don't do anything if scale is 1
            if sx == 1.0 and sy == 1.0:
                scale_str = ""
            else:
                scale_str = f"scale({sx},{sy})"
            if x_pos == x and y_pos == y and scale_str == "":
                return
            #     trans1_str = ""
            #     trans2_str = ""
            # else:
            trans1_str = f"translate({round(x_pos, 7)},{round(y_pos, 7)})"
            trans2_str = f"translate({round(-x, 7)},{round(-y, 7)})"
            matrixstr = f"{trans1_str} {scale_str} {trans2_str}".strip()
            # channel(f"{matrixstr}")
            matrix = Matrix(matrixstr)
            if data is None:
                data = list(self.elems(emphasized=True))
            images = []
            for node in data:
                if hasattr(node, "lock") and node.lock:
                    channel(_("resize: cannot resize a locked element"))
                    continue
                node.matrix *= matrix
                node.modified()
                if hasattr(node, "update"):
                    images.append(node)
            for node in images:
                node.update(None)
            self.signal("refresh_scene", "Scene")
            return "elements", data
        except (ValueError, ZeroDivisionError, TypeError):
            raise CommandSyntaxError

    @self.console_argument("sx", type=float, help=_("scale_x value"))
    @self.console_argument("kx", type=float, help=_("skew_x value"))
    @self.console_argument("ky", type=float, help=_("skew_y value"))
    @self.console_argument("sy", type=float, help=_("scale_y value"))
    @self.console_argument("tx", type=self.length_x, help=_("translate_x value"))
    @self.console_argument("ty", type=self.length_y, help=_("translate_y value"))
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
            for node in self.elems():
                name = str(node)
                if len(name) > 50:
                    name = name[:50] + "…"
                channel(f"{i}: {str(node.matrix)} - {name}")
                i += 1
            channel("----------")
            return
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        images = []
        try:
            # SVG 7.15.3 defines the matrix form as:
            # [a c  e]
            # [b d  f]
            m = Matrix(
                sx,
                kx,
                ky,
                sy,
                tx,
                ty,
            )
            for node in data:
                if hasattr(node, "lock") and node.lock:
                    continue
                node.matrix = Matrix(m)
                node.modified()
                if hasattr(node, "update"):
                    images.append(node)
        except ValueError:
            raise CommandSyntaxError
        for node in images:
            node.update(None)
        self.signal("refresh_scene", "Scene")
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
        images = []
        for e in data:
            if hasattr(e, "lock") and e.lock:
                continue
            name = str(e)
            if len(name) > 50:
                name = name[:50] + "…"
            channel(_("reset - {name}").format(name=name))
            e.matrix.reset()
            e.modified()
            if hasattr(e, "update"):
                images.append(e)
        for e in images:
            e.update(None)
        self.signal("refresh_scene", "Scene")
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
            try:
                e.shape.reify()
            except AttributeError as err:
                try:
                    e.path.reify()
                except AttributeError:
                    channel(_("Couldn't reify - %s - %s") % (name, err))
                    return "elements", data
            e.altered()
            channel(_("reified - %s") % name)
        return "elements", data

    @self.console_command(
        "circle_arc_path",
        help=_("Convert paths to use circular arcs."),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_circ_arc_path(command, channel, _, data=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        for e in data:
            try:
                if e.lock:
                    continue
            except AttributeError:
                pass
            if e.type == "elem path":
                e.path.approximate_bezier_with_circular_arcs()
                e.altered()

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
            was_emphasized = True
            old_first = self.first_emphasized
        else:
            was_emphasized = False
            old_first = None
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        self.classify(data)
        if was_emphasized:
            for e in data:
                e.emphasized = True
            if len(data) == 1:
                data[0].focus()
            if old_first is not None and old_first in data:
                self.first_emphasized = old_first
            else:
                self.first_emphasized = None

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
            was_emphasized = True
            old_first = self.first_emphasized
        else:
            was_emphasized = False
            old_first = None
        if len(data) == 0:
            channel(_("No selected elements."))
            return
        self.remove_elements_from_operations(data)
        # restore emphasized flag as it is relevant for subsequent operations
        if was_emphasized:
            for e in data:
                e.emphasized = True
            if len(data) == 1:
                data[0].focus()
            if old_first is not None and old_first in data:
                self.first_emphasized = old_first
            else:
                self.first_emphasized = None
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
        self.signal("tree_changed")
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
        self.remove_nodes(todelete[entry])
        self.validate_selected_area()
        self.signal("tree_changed")
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
        self.remove_nodes(data)
        self.signal("tree_changed")
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
        self.signal("refresh_scene")
        self.signal("rebuild_tree")

    @self.console_command(
        "redo",
    )
    def undo_redo(command, channel, _, data=None, **kwgs):
        if not self.undo.redo():
            channel("No redo available.")
            return
        channel(f"Redo: {self.undo}")
        self.signal("refresh_scene")
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
            for optional in ("wxfont", "mktext", "mkfont", "mkfontsize"):
                if hasattr(e, optional):
                    setattr(copy_node, optional, getattr(e, optional))
            self._clipboard[destination].append(copy_node)
        return "elements", self._clipboard[destination]

    @self.console_option("dx", "x", help=_("paste offset x"), type=Length, default=0)
    @self.console_option("dy", "y", help=_("paste offset y"), type=Length, default=0)
    @self.console_command(
        "paste",
        help=_("clipboard paste"),
        input_type="clipboard",
        output_type="elements",
    )
    def clipboard_paste(command, channel, _, data=None, post=None, dx=None, dy=None, **kwargs):
        destination = self._clipboard_default
        try:
            pasted = [copy(e) for e in self._clipboard[destination]]
        except (TypeError, KeyError):
            channel(_("Error: Clipboard Empty"))
            return
        if dx != 0 or dy != 0:
            matrix = Matrix.translate(float(dx), float(dy))
            for node in pasted:
                node.matrix *= matrix
        group = self.elem_branch.add(type="group", label="Group", id="Copy")
        for p in pasted:
            group.add_node(copy(p))
        self.set_emphasis([group])
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

    # ==========
    # TRACE OPERATIONS
    # ==========

    # Function to return the euclidean distance
    # between two points
    def dist(a, b):
        return sqrt(pow(a[0] - b[0], 2) + pow(a[1] - b[1], 2))

    # Function to check whether a point lies inside
    # or on the boundaries of the circle
    def is_inside(center, radius, p):
        return dist(center, p) <= radius

    # The following two functions are used
    # To find the equation of the circle when
    # three points are given.

    # Helper method to get a circle defined by 3 points
    def get_circle_center(bx, by, cx, cy):
        B = bx * bx + by * by
        C = cx * cx + cy * cy
        D = bx * cy - by * cx
        return [(cy * B - by * C) / (2 * D), (bx * C - cx * B) / (2 * D)]

    # Function to return the smallest circle
    # that intersects 2 points
    def circle_from1(A, B):
        # Set the center to be the midpoint of A and B
        C = [(A[0] + B[0]) / 2.0, (A[1] + B[1]) / 2.0]

        # Set the radius to be half the distance AB
        return C, dist(A, B) / 2.0

    # Function to return a unique circle that
    # intersects three points
    def circle_from2(A, B, C):
        if A == B:
            I, radius = circle_from1(A, C)
            return I, radius
        elif A == C:
            I, radius = circle_from1(A, B)
            return I, radius
        elif B == C:
            I, radius = circle_from1(A, B)
            return I, radius
        else:
            I = get_circle_center(B[0] - A[0], B[1] - A[1], C[0] - A[0], C[1] - A[1])
            I[0] += A[0]
            I[1] += A[1]
            radius = dist(I, A)
            return I, radius

    # Function to check whether a circle
    # encloses the given points
    def is_valid_circle(center, radius, P):

        # Iterating through all the points
        # to check  whether the points
        # lie inside the circle or not
        for p in P:
            if not is_inside(center, radius, p):
                return False
        return True

    # Function to return the minimum enclosing
    # circle for N <= 3
    def min_circle_trivial(P):
        assert len(P) <= 3

        if not P:
            return [0, 0], 0

        elif len(P) == 1:
            return P[0], 0

        elif len(P) == 2:
            center, radius = circle_from1(P[0], P[1])
            return center, radius

        # To check if MEC can be determined
        # by 2 points only
        for i in range(3):
            for j in range(i + 1, 3):

                center, radius = circle_from1(P[i], P[j])
                if is_valid_circle(center, radius, P):
                    return center, radius

        center, radius = circle_from2(P[0], P[1], P[2])
        return center, radius

    # Returns the MEC using Welzl's algorithm
    # Takes a set of input points P and a set R
    # points on the circle boundary.
    # n represents the number of points in P
    # that are not yet processed.
    def welzl_helper(P, R, n):
        # Base case when all points processed or |R| = 3
        if n == 0 or len(R) == 3:
            center, radius = min_circle_trivial(R)
            return center, radius

        # Pick a random point randomly
        idx = randint(0, n - 1)
        p = P[idx]

        # Put the picked point at the end of P
        # since it's more efficient than
        # deleting from the middle of the vector
        P[idx], P[n - 1] = P[n - 1], P[idx]

        # Get the MEC circle d from the
        # set of points P - :p
        dcenter, dradius = welzl_helper(P, R.copy(), n - 1)

        # If d contains p, return d
        if is_inside(dcenter, dradius, p):
            return dcenter, dradius

        # Otherwise, must be on the boundary of the MEC
        R.append(p)

        # Return the MEC for P - :p and R U :p
        dcenter, dradius = welzl_helper(P, R.copy(), n - 1)
        return dcenter, dradius

    def welzl(P):
        P_copy = P.copy()
        shuffle(P_copy)
        center, radius = welzl_helper(P_copy, [], len(P_copy))
        return center, radius

    def generate_hull_shape(method, data, resolution=None):
        if resolution is None:
            DETAIL = 500  # How coarse / fine shall a subpath be split
        else:
            DETAIL = int(resolution)
        pts = []
        min_val = [float("inf"), float("inf")]
        max_val = [-float("inf"), -float("inf")]
        for node in data:
            if method in ("hull", "segment", "circle"):
                try:
                    path = node.as_path()
                except AttributeError:
                    path = None
                if path is not None:
                    p = path.first_point
                    pts += [(p.x, p.y)]
                    for segment in path:
                        p = segment.end
                        pts += [(p.x, p.y)]
                else:
                    bounds = node.bounds
                    pts += [
                        (bounds[0], bounds[1]),
                        (bounds[0], bounds[3]),
                        (bounds[2], bounds[1]),
                        (bounds[2], bounds[3]),
                    ]
            elif method == "complex":
                try:
                    path = node.as_path()
                except AttributeError:
                    path = None

                if path is not None:

                    from numpy import linspace

                    for subpath in path.as_subpaths():
                        psp = Path(subpath)
                        p = psp.first_point
                        pts += [(p.x, p.y)]
                        positions = linspace(0, 1, num=DETAIL, endpoint=True)
                        subj = psp.npoint(positions)
                        # Not sure why we need to do that, its already rows x 2
                        # subj.reshape((2, DETAIL))
                        s = list(map(Point, subj))
                        for p in s:
                            pts += [(p.x, p.y)]
                else:
                    bounds = node.bounds
                    pts += [
                        (bounds[0], bounds[1]),
                        (bounds[0], bounds[3]),
                        (bounds[2], bounds[1]),
                        (bounds[2], bounds[3]),
                    ]
            elif method == "quick":
                bounds = node.bounds
                min_val[0] = min(min_val[0], bounds[0])
                min_val[1] = min(min_val[1], bounds[1])
                max_val[0] = max(max_val[0], bounds[2])
                max_val[1] = max(max_val[1], bounds[3])
        if method == "quick":
            if (
                not isinf(min_val[0])
                and not isinf(min_val[1])
                and not isinf(max_val[0])
                and not isinf(max_val[0])
            ):
                pts += [
                    (min_val[0], min_val[1]),
                    (min_val[0], max_val[1]),
                    (max_val[0], min_val[1]),
                    (max_val[0], max_val[1]),
                ]
        if method == "segment":
            hull = [p for p in pts]
        elif method == "circle":
            mec_center, mec_radius = welzl(pts)
            # So now we have a circle with (mec[0], mec[1]), and mec_radius
            hull = []
            RES = 100
            for i in range(RES):
                hull += [
                    (
                        mec_center[0] + mec_radius * cos(i / RES * tau),
                        mec_center[1] + mec_radius * sin(i / RES * tau),
                    )
                ]
        else:
            hull = [p for p in Point.convex_hull(pts)]
        if len(hull) != 0:
            hull.append(hull[0])  # loop
        return hull

    @self.console_argument(
        "method",
        help=_("Method to use (one of quick, hull, complex, segment, circle)"),
    )
    @self.console_argument("resolution")
    @self.console_option("start", "s", type=int, help=_("0=immediate, 1=User interaction, 2=wait for 5 seconds"))
    @self.console_command(
        "trace",
        help=_("trace the given elements"),
        input_type=("elements", "shapes", None),
    )
    def trace_trace_spooler(
        command, channel, _, method=None, resolution=None, start=None, data=None, **kwargs
    ):
        if method is None:
            method = "quick"
        method = method.lower()
        if method not in ("segment", "quick", "hull", "complex", "circle"):
            channel(
                _(
                    "Invalid method, please use one of quick, hull, complex, segment, circle."
                )
            )
            return

        spooler = self.device.spooler
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No elements bounds to trace"))
            return
        hull = generate_hull_shape(method, data, resolution)
        if start is None:
            # Lets take system default
            start = self.trace_start_method
        if start < 0 or start > 2:
            start = 0
        if len(hull) == 0:
            channel(_("No elements bounds to trace."))
            return

        def run_shape(_spooler, startmethod, _hull):
            def trace_hull(startmethod=0):
                if startmethod == 0:
                    # Immediately
                    pass
                elif startmethod == 1:
                    # Dialog
                    yield ('console', 'interrupt "Trace is about to start"')
                elif startmethod == 2:
                    # Wait for some seconds
                    yield ('wait', 5000)

                yield "wait_finish"
                yield "rapid_mode"
                idx = 0
                for p in _hull:
                    idx += 1
                    yield (
                        "move_abs",
                        Length(amount=p[0]).length_mm,
                        Length(amount=p[1]).length_mm,
                    )

            _spooler.laserjob(
                list(trace_hull(startmethod)), label=f"Trace Job: {method}", helper=True
            )

        run_shape(spooler, start, hull)

    @self.console_argument(
        "method",
        help=_("Method to use (one of quick, hull, complex, segment, circle)"),
    )
    @self.console_argument(
        "resolution", help=_("Resolution for complex slicing, default=500")
    )
    @self.console_command(
        "tracegen",
        help=_("create the trace around the given elements"),
        input_type=("elements", "shapes", None),
        output_type="elements",
    )
    def trace_trace_generator(
        command, channel, _, method=None, resolution=None, data=None, post=None, **kwargs
    ):
        if method is None:
            method = "quick"
        method = method.lower()
        if not method in ("segment", "quick", "hull", "complex", "circle"):
            channel(
                _(
                    "Invalid method, please use one of quick, hull, complex, segment, circle."
                )
            )
            return

        if data is None:
            data = list(self.elems(emphasized=True))
        hull = generate_hull_shape(method, data, resolution=resolution)
        if len(hull) == 0:
            channel(_("No elements bounds to trace."))
            return
        shape = Polyline(hull)
        if shape.is_degenerate():
            channel(_("Shape is degenerate."))
            return "elements", data
        node = self.elem_branch.add(shape=shape, type="elem polyline")
        node.stroke = self.default_stroke
        node.fill = self.default_fill
        node.altered()
        self.set_emphasis([node])
        node.focus()
        data.append(node)
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "elements", data

    # --------------------------- END COMMANDS ------------------------------
