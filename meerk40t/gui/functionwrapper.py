"""
This module provides generic routines to allow the input of function parameters and preview the results
"""
from typing import Any, Callable

import wx

from meerk40t.core.units import Angle, Length
from meerk40t.gui.wxutils import (
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    wxCheckBox,
    wxStaticText,
)

_ = wx.GetTranslation


class ConsoleCommandUI(wx.Panel):
    def __init__(self, *args, context=None, command_string: str, preview_routine: Callable=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context:Any = context
        self.cmd_string:str = ""
        self.var_set:list = []
        self.preview_routine = preview_routine
        self._establish_base(command_string)
        self.TAG:str = f"FUNCTION_{self.cmd_string}"
        self._build_panel()
        self.context.elements.undo.mark(self.TAG)

    def _build_panel(self):
        def get_tbox_param(entry):
            if entry["type"] == Length:
                checker = "length"
                small = True
            if entry["type"] == Angle:
                checker = "angle"
                small = True
            elif entry["type"] == int:
                checker = "int"
                small = True
            elif entry["type"] == float:
                checker = "float"
                small = True
            else:
                checker = ""
                small = False
            return checker, small

        main_sizer:wx.BoxSizer = wx.BoxSizer(wx.VERTICAL)
        has_params:bool = False
        has_options:bool = False
        p_sizer = StaticBoxSizer(
            self, wx.ID_ANY, label=_("Parameters"), orientation=wx.VERTICAL
        )
        o_sizer = StaticBoxSizer(
            self, wx.ID_ANY, label=_("Options"), orientation=wx.VERTICAL
        )
        for e in self.var_set:
            varname = e["name"]
            varname = "" if varname is None else varname.replace("_", " ")
            if e["type"] == bool:
                control = wxCheckBox(self, wx.ID_ANY, _(varname))
                control.SetValue(bool(e["value"]))
                control.Bind(wx.EVT_CHECKBOX, self.on_check_boxes(e))
                control.SetToolTip(e["help"])
            else:
                checker, small = get_tbox_param(e)
                control = wx.BoxSizer(wx.HORIZONTAL)
                label = wxStaticText(self, wx.ID_ANY, _(varname))
                label.SetMinSize(dip_size(self, 75, -1))
                text_box = TextCtrl(
                    self,
                    wx.ID_ANY,
                    value=e["value"],
                    check=checker,
                    limited=small,
                    nonzero=True,
                )
                text_box.SetToolTip(e["help"])
                control.Add(label, 0, wx.EXPAND, 0)
                control.Add(text_box, 1, wx.EXPAND, 0)
                text_box.Bind(wx.EVT_TEXT, self.on_text_boxes(e))
            if e["optional"]:
                o_sizer.Add(control, 0, wx.EXPAND, 0)
                has_options = True
            else:
                p_sizer.Add(control, 0, wx.EXPAND, 0)
                has_params = True
        if self.preview_routine is None:
            target = main_sizer
            self.preview_control = None
        else:
            preview_sizer = wx.BoxSizer(wx.HORIZONTAL)
            left_side = wx.BoxSizer(wx.VERTICAL)
            right_side = wx.BoxSizer(wx.VERTICAL)
            preview_sizer.Add(left_side, 0, wx.EXPAND, 0)
            preview_sizer.Add(right_side, 1, wx.EXPAND, 0)
            main_sizer.Add(preview_sizer, 1, wx.EXPAND, 0)

            self.preview_control = wx.StaticBitmap(self, wx.ID_ANY, style = wx.SB_FLAT)
            target = left_side
            right_side.Add(self.preview_control)
        if has_params:
            target.Add(p_sizer, 1, wx.EXPAND, 0)
        if has_options:
            target.Add(o_sizer, 1, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.Layout()

    def _establish_base(self, command_string:str):
        # Look inside the register commands...
        self.var_set.clear()
        self.cmd_string = ""
        for func, command_name, sname in self.context.kernel.find(
            "command", ".*", command_string
        ):
            parts = command_name.split("/")
            input_type = parts[1]
            command_item = parts[2]
            self.cmd_string = (
                command_item if input_type == "None" else f"{input_type} {command_item}"
            )
            func = self.context.kernel.lookup(command_name)
            for a in func.arguments:
                var_info:dict = {
                    "name": a.get("name", ""),
                    "type": a.get("type", type(None)),
                    "help": a.get("help", ""),
                    "short": "",
                    "optional": False,
                    "default": a.get("default", None),
                    "value": a.get("default", None),
                }
                self.var_set.append(var_info)
            for b in func.options:
                var_info = {
                    "name": b.get("name", ""),
                    "type": b.get("type", type(None)),
                    "help": b.get("help", ""),
                    "short": b.get("short", ""),
                    "optional": True,
                    "default": b.get("default", None),
                    "value": b.get("default", None),
                }
                self.var_set.append(var_info)
            break

    def command_string(self) -> str:
        var_string: str = ""
        for entry in self.var_set:
            if entry["type"] == Length:
                var_repr = Length(entry["value"]).length_mm
            elif entry["type"] == Angle:
                var_repr = Angle(entry["value"]).degrees
            else:
                var_repr = str(entry["type"](entry["value"]))
            if entry["optional"] == "optional":
                var_string = f" {var_string}-{entry['short']} {var_repr}"
            else:
                var_string = f" {var_string}{var_repr}"

        return f"{self.cmd_string}{var_string}\n"

    def variable_set(self) -> dict:
        return {entry.name: entry.value for entry in self.var_set}


    def on_check_boxes(self, var_dict):
        def handler(event: wx.CommandEvent):
            obj = event.GetEventObject()
            var_dict["value"] = obj.GetValue()
            self.updated()

        return handler

    def on_text_boxes(self, var_dict):
        def handler(event: wx.CommandEvent):
            obj = event.GetEventObject()
            try:
                value = var_dict["type"](obj.GetValue())
                var_dict["value"] = value
                self.updated()
            except ValueError:
                return

        return handler

    def updated(self):
        if self.preview_routine:
            bmp = self.preview_routine(self.variable_set())
            if bmp:
                self.preview_control.SetBitmap(bmp)
            else:
                self.preview_control.SetBitmap(wx.NullBitmap)

    def cancel_it(self, event):
        idx = self.context.elements.undo.find(self.TAG)
        if idx <= 0:
            return
        self.context.elements.undo.undo(index=idx)

    def accept_it(self, event):
        idx = self.context.elements.undo.find(self.TAG)
        if idx <= 0:
            return
        self.context.elements.undo.rename(index=idx, message=_(self.cmd_string))
