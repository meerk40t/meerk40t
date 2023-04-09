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

    # --------------------------- END COMMANDS ------------------------------
