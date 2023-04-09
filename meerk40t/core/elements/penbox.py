"""
This is a giant list of console commands that deal with and often implement the elements system in the program.
"""

import os.path
import re
from copy import copy
from math import cos, gcd, isinf, pi, sin, sqrt, tau
from random import randint, shuffle

from meerk40t.kernel import CommandSyntaxError, Service, Settings

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
    if lifecycle == "register":
        kernel.add_service("penbox", Penbox(kernel))


def index_range(index_string):
    """
    Parses index ranges in the form <idx>,<idx>-<idx>,<idx>
    @param index_string:
    @return:
    """
    indexes = list()
    for s in index_string.split(","):
        q = list(s.split("-"))
        if len(q) == 1:
            indexes.append(int(q[0]))
        else:
            start = int(q[0])
            end = int(q[1])
            if start > end:
                for q in range(end, start + 1):
                    indexes.append(q)
            else:
                for q in range(start, end + 1):
                    indexes.append(q)
    return indexes

class Penbox(Service):
    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "penbox")
        self.pen_data = Settings(self.kernel.name, "penbox.cfg")
        self.penbox = {}
        self.load_persistent_penbox()

        _ = kernel.translation

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

        @self.console_argument("index", help=_("Penbox index"), type=index_range)
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

        # --------------------------- END COMMANDS ------------------------------

    def load_persistent_penbox(self):
        settings = self.pen_data
        pens = settings.read_persistent_string_dict("pens", suffix=True)
        for pen in pens:
            length = int(pens[pen])
            box = list()
            for i in range(length):
                penbox = dict()
                settings.read_persistent_string_dict(f"{pen} {i}", penbox, suffix=True)
                box.append(penbox)
            self.penbox[pen] = box

    def save_persistent_penbox(self):
        sections = {}
        for section in self.penbox:
            sections[section] = len(self.penbox[section])
        self.pen_data.write_persistent_dict("pens", sections)
        for section in self.penbox:
            for i, p in enumerate(self.penbox[section]):
                self.pen_data.write_persistent_dict(f"{section} {i}", p)

    def shutdown(self, *args, **kwargs):
        self.save_persistent_penbox()
        self.pen_data.write_configuration()
