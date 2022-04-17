import wx

from meerk40t.core.units import Length
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.kernel import Context
from meerk40t.svgelements import Color

_ = wx.GetTranslation


class ChoicePropertyPanel(wx.Panel):
    """
    ChoicePropertyPanel is a generic panel that simply presents a simple list of properties to be viewed and edited.
    In most cases it can be initialized by passing a choices value which will read the registered choice values
    and display the given properties, automatically generating an appropriate changer for that property.
    """

    def __init__(self, *args, context: Context = None, choices=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.listeners = list()
        if choices is None:
            return
        if isinstance(choices, str):
            choices = self.context.lookup("choices", choices)
            if choices is None:
                return
        self.choices = choices
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        for i, c in enumerate(self.choices):
            if isinstance(c, tuple):
                # If c is tuple
                dict_c = dict()
                try:
                    dict_c["object"] = c[0]
                    dict_c["attr"] = c[1]
                    dict_c["default"] = c[2]
                    dict_c["label"] = c[3]
                    dict_c["tip"] = c[4]
                    dict_c["type"] = c[5]
                except IndexError:
                    pass
                c = dict_c
            try:
                attr = c["attr"]
                obj = c["object"]
            except KeyError:
                continue

            # get default value
            if hasattr(obj, attr):
                data = getattr(obj, attr)
            else:
                # if obj can lack attr, default must have been assigned.
                try:
                    data = c["default"]
                except KeyError:
                    continue
            data_type = type(data)
            data_type = c.get("type", data_type)
            data_style = c.get("style", None)
            try:
                # Get label
                label = c["label"]
            except KeyError:
                # Undefined label is the attr
                label = attr

            if data_type == bool:
                # Bool type objects get a checkbox.
                control = wx.CheckBox(self, label=label)
                control.SetValue(data)

                def on_checkbox_check(param, ctrl, obj):
                    def check(event=None):
                        v = ctrl.GetValue()
                        setattr(obj, param, bool(v))
                        self.context.signal(param, v)

                    return check

                control.Bind(wx.EVT_CHECKBOX, on_checkbox_check(attr, control, obj))
                sizer_main.Add(control, 0, wx.EXPAND, 0)
            elif data_type == str and data_style == "file":
                control_sizer = wx.StaticBoxSizer(
                    wx.StaticBox(self, wx.ID_ANY, label), wx.HORIZONTAL
                )
                control = wx.Button(self, -1)

                def set_file(filename: str):
                    if not filename:
                        filename = _("No File")
                    control.SetLabel(filename)

                def on_button_filename(param, ctrl, obj, wildcard):
                    def click(event=None):
                        with wx.FileDialog(
                            self,
                            label,
                            wildcard=wildcard if wildcard else "*",
                            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                        ) as fileDialog:
                            if fileDialog.ShowModal() == wx.ID_CANCEL:
                                return  # the user changed their mind
                            pathname = str(fileDialog.GetPath())
                            ctrl.SetLabel(pathname)
                            self.Layout()
                            try:
                                setattr(obj, param, pathname)
                            except ValueError:
                                # cannot cast to data_type, pass
                                pass

                    return click

                set_file(data)
                control_sizer.Add(control)
                control.Bind(
                    wx.EVT_BUTTON,
                    on_button_filename(attr, control, obj, c.get("wildcard", "*")),
                )
                sizer_main.Add(control_sizer, 0, wx.EXPAND, 0)
            elif data_type == str and data_style == "combo":
                control_sizer = wx.StaticBoxSizer(
                    wx.StaticBox(self, wx.ID_ANY, label), wx.HORIZONTAL
                )
                control = wx.ComboBox(
                    self,
                    wx.ID_ANY,
                    choices=c.get("choices", [c.get("default")]),
                    style=wx.CB_DROPDOWN | wx.CB_READONLY,
                )
                control.SetValue(data)

                def on_combo_text(param, ctrl, obj):
                    def select(event=None):
                        setattr(obj, param, ctrl.GetValue())

                    return select

                control_sizer.Add(control)
                control.Bind(
                    wx.EVT_COMBOBOX,
                    on_combo_text(attr, control, obj),
                )
                sizer_main.Add(control_sizer, 0, wx.EXPAND, 0)
            elif data_type in (str, int, float):
                # str, int, and float type objects get a TextCtrl setter.
                control_sizer = wx.StaticBoxSizer(
                    wx.StaticBox(self, wx.ID_ANY, label), wx.HORIZONTAL
                )
                control = wx.TextCtrl(self, -1)
                control.SetValue(str(data))
                control_sizer.Add(control)

                def on_textbox_text(param, ctrl, obj, dtype):
                    def text(event=None):
                        v = ctrl.GetValue()
                        try:
                            setattr(obj, param, dtype(v))
                        except ValueError:
                            # cannot cast to data_type, pass
                            pass

                    return text

                control.Bind(
                    wx.EVT_TEXT, on_textbox_text(attr, control, obj, data_type)
                )
                sizer_main.Add(control_sizer, 0, wx.EXPAND, 0)
            elif data_type == Length:
                # Length type is a TextCtrl with special checks
                control_sizer = wx.StaticBoxSizer(
                    wx.StaticBox(self, wx.ID_ANY, label), wx.HORIZONTAL
                )
                control = wx.TextCtrl(self, -1)
                control.SetValue(str(data))
                control_sizer.Add(control)

                def on_textbox_text(param, ctrl, obj, dtype):
                    def text(event=None):
                        try:
                            v = Length(ctrl.GetValue())
                            ctrl.SetBackgroundColour(None)
                            ctrl.Refresh()
                        except ValueError:
                            ctrl.SetBackgroundColour(wx.RED)
                            ctrl.Refresh()
                            return
                        try:
                            setattr(obj, param, v.preferred_length)
                        except ValueError:
                            # cannot cast to data_type, pass
                            pass

                    return text

                control.Bind(
                    wx.EVT_TEXT, on_textbox_text(attr, control, obj, data_type)
                )
                sizer_main.Add(control_sizer, 0, wx.EXPAND, 0)
            elif data_type == Color:
                # Color data_type objects are get a button with the background.
                control_sizer = wx.StaticBoxSizer(
                    wx.StaticBox(self, wx.ID_ANY, label), wx.HORIZONTAL
                )
                control = wx.Button(self, -1)

                def set_color(color: Color):
                    control.SetLabel(str(color.hex))
                    control.SetBackgroundColour(wx.Colour(swizzlecolor(color)))
                    control.color = color

                def on_button_color(param, ctrl, obj):
                    def click(event=None):
                        color_data = wx.ColourData()
                        color_data.SetColour(wx.Colour(swizzlecolor(ctrl.color)))
                        dlg = wx.ColourDialog(self, color_data)
                        if dlg.ShowModal() == wx.ID_OK:
                            color_data = dlg.GetColourData()
                            data = Color(
                                swizzlecolor(color_data.GetColour().GetRGB()), 1.0
                            )
                            set_color(data)
                            try:
                                setattr(obj, param, data_type(data))
                            except ValueError:
                                # cannot cast to data_type, pass
                                pass

                    return click

                set_color(data)
                control_sizer.Add(control)

                control.Bind(wx.EVT_BUTTON, on_button_color(attr, control, obj))
                sizer_main.Add(control_sizer, 0, wx.EXPAND, 0)
            else:
                # Requires a registered data_type
                continue

            # Get enabled value
            try:
                enabled = c["enabled"]
                control.Enable(enabled)
            except KeyError:
                try:
                    conditional = c["conditional"]
                    c_obj, c_attr = conditional
                    enabled = bool(getattr(c_obj, c_attr))
                    control.Enable(enabled)

                    def on_enable_listener(param, ctrl, obj):
                        def listen(origin, value):
                            enabled = bool(getattr(obj, param))
                            ctrl.Enable(enabled)

                        return listen

                    listener = on_enable_listener(c_attr, control, c_obj)
                    self.listeners.append((c_attr, listener))
                    context.listen(c_attr, listener)
                except KeyError:
                    pass

            try:
                # Set the tool tip if 'tip' is available
                control.SetToolTip(c["tip"])
            except KeyError:
                pass

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

    def pane_hide(self):
        for attr, listener in self.listeners:
            self.context.unlisten(attr, listener)

    def pane_show(self):
        pass
