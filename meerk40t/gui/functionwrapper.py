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
    wxButton,
    wxCheckBox,
    wxStaticText,
)

_ = wx.GetTranslation


class ConsoleCommandUI(wx.Panel):
    def __init__(self, parent, id, *args, context=None, command_string: str, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, parent, id, *args, **kwds)
        self.active = False
        self.parent_window = parent
        self.context:Any = context
        self.cmd_string:str = ""
        self.var_set:list = []
        units = self.context.units_name
        if units in ("inch", "inches"):
            units = "in"
        self.units = units
        self._establish_base(command_string)
        self.TAG:str = f"FUNCTION_{self.cmd_string}"
        self.undo_index = None
        self._build_panel()

    def _build_panel(self):
        def get_tbox_param(entry):
            checker = ""
            small = False
            if entry["value"] is None:
                cval = "" 
            else:
                cval = str(entry["value"])
                if isinstance(entry["value"], (tuple, list)):
                    cval = cval[1:-1]
            if entry["type"] == Length:
                checker = "length"
                small = True
                if entry["value"] is not None:
                    cval = Length(entry["value"], preferred_units=self.units).preferred_length
            if entry["type"] == Angle:
                checker = "angle"
                small = True
                if entry["value"] is not None:
                    cval = Angle(entry["value"]).angle_degrees
            elif entry["type"] == int:
                if entry["nargs"] == 1:
                    checker = "int"
                    small = True
            elif entry["type"] == float:
                checker = "float"
                small = True
            return checker, small, cval

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
            varname = "" if varname is None else varname.replace("_", " ").capitalize()
            control_line = wx.BoxSizer(wx.HORIZONTAL)
            label = wxStaticText(self, wx.ID_ANY, _(varname))
            label.SetMinSize(dip_size(self, 75, -1))
            control_line.Add(label, 0, wx.EXPAND, 0)
            if e["type"] == bool:
                control = wxCheckBox(self, wx.ID_ANY)
                control.SetValue(bool(e["value"]))
                control.Bind(wx.EVT_CHECKBOX, self.on_check_boxes(e))
            else:
                checker, small, cval = get_tbox_param(e)
                control = TextCtrl(
                    self,
                    wx.ID_ANY,
                    value=cval,
                    check=checker,
                    limited=small,
                    nonzero=True,
                )
                control.Bind(wx.EVT_TEXT, self.on_text_boxes(e))
            control.SetToolTip(e["help"])
            control_line.Add(control, 1, wx.EXPAND, 0)
            if e["optional"]:
                o_sizer.Add(control_line, 0, wx.EXPAND, 0)
                has_options = True
            else:
                p_sizer.Add(control_line, 0, wx.EXPAND, 0)
                has_params = True
        if has_params:
            main_sizer.Add(p_sizer, 0, wx.EXPAND, 0)
        if has_options:
            main_sizer.Add(o_sizer, 0, wx.EXPAND, 0)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_okay = wxButton(self, wx.ID_OK, _("Apply"))
        self.btn_cancel = wxButton(self, wx.ID_CANCEL, _("Cancel"))
        self.btn_okay.Bind(wx.EVT_BUTTON, self.accept_it)
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.cancel_it)
        button_sizer.Add(self.btn_okay)
        button_sizer.Add(self.btn_cancel)
        # button_sizer.Add(self.check_preview)
        main_sizer.Add(button_sizer, 0, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.Layout()
        # print(self.cmd_string, self.var_set)

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
                    "nargs": a.get("nargs", 1),
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
                    "nargs": b.get("nargs", 1),
                }
                self.var_set.append(var_info)
            break

    def command_string(self) -> str:
        var_string: str = ""
        for entry in self.var_set:
            if entry["value"] is None:
                continue
            if entry["type"] == Length:
                var_repr = Length(entry["value"]).length_mm
            elif entry["type"] == bool:
                if not entry["value"]:
                    continue
            elif entry["type"] == Angle:
                var_repr = Angle(entry["value"]).degrees
            else:
                if isinstance(entry["value"], (tuple, list)):
                    var_repr = ""
                    for idx, num in enumerate(entry["value"]):
                        if idx > 0:
                            var_repr = f"{var_repr},{num}"
                        else:
                            var_repr = f"{num}"
                else:
                    var_repr = str(entry["type"](entry["value"]))
            if entry["optional"]:
                var_string = f"{var_string} -{entry['short']} {var_repr}"
            else:
                var_string = f"{var_string} {var_repr}"
        print (f"{self.cmd_string}{var_string}")
        return f"{self.cmd_string}{var_string}\n"


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
                if var_dict["nargs"] > 1:
                    value = obj.GetValue()
                else:
                    value = var_dict["type"](obj.GetValue())
                var_dict["value"] = value
                self.updated()
            except ValueError:
                return

        return handler


    def show_stuff(self, has_emph):
        for ctrl in self.GetChildren():
            ctrl.Enable(has_emph)

    def updated(self):
        if not self.active:
            return
        if self.undo_index is None:
            self.context.elements.undo.mark(self.TAG)
            self.undo_index = self.context.elements.undo.find(self.TAG)

        idx = self.context.elements.undo.find(self.TAG)
        if idx >= 0:
            self.context.elements.undo.undo(index=idx)
        cmd = self.command_string()
        self.context(cmd)
        self.context.signal("refresh_scene", "Scene")
        self.context.signal("rebuild_tree")

    def cancel_it(self, event):
        idx = self.context.elements.undo.find(self.TAG)
        if idx >= 0:
            self.context.elements.undo.undo(index=idx)
            self.context.elements.undo.remove(index=idx)
        self.context.signal("refresh_scene", "Scene")
        self.context.signal("rebuild_tree")
        if hasattr(self.parent_window, "done"):
            self.parent_window.done()

    def accept_it(self, event):
        cmd = self.command_string()
        with self.context.elements.undoscope(_(self.cmd_string)):
            self.context(cmd)

        idx = self.context.elements.undo.find(self.TAG)
        if idx >= 0:
            self.context.elements.undo.remove(idx)
        if hasattr(self.parent_window, "done"):
            self.parent_window.done()

    def pane_show(self):
        # print (f"Active {self.cmd_string}")
        self.active = True
        self.updated()

    def pane_hide(self):
        self.active = False
        idx = self.context.elements.undo.find(self.TAG)
        if idx >= 0:
            self.context.elements.undo.remove(idx)
        self.undo_index = None

        # print (f"Inactive {self.cmd_string}")
