import wx
from wx.lib.scrolledpanel import ScrolledPanel

from meerk40t.core.units import Angle, Length
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.kernel import Context
from meerk40t.svgelements import Color

_ = wx.GetTranslation


class ChoicePropertyPanel(ScrolledPanel):
    """
    ChoicePropertyPanel is a generic panel that simply presents a simple list of properties to be viewed and edited.
    In most cases it can be initialized by passing a choices value which will read the registered choice values
    and display the given properties, automatically generating an appropriate changer for that property.
    """

    def __init__(self, *args, context: Context = None, choices=None, scrolling = True, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.listeners = list()
        if choices is None:
            return
        if isinstance(choices, str):
            choices = self.context.lookup("choices", choices)
            if choices is None:
                return
        # Let's see whether we have a section and a page property...
        for c in choices:
            try:
                dummy = c["section"]
            except KeyError:
                c["section"] = ""
            try:
                dummy = c["page"]
            except KeyError:
                c["page"] = ""
        # print ("Choices: " , choices)
        self.choices = sorted(sorted(choices, key=lambda d: d["section"]), key=lambda d: d["page"])
        # print ("Sorted choices: " , self.choices)


        sizer_main = wx.BoxSizer(wx.VERTICAL)
        last_page = ""
        last_section = ""
        last_box = None
        current_main_sizer = sizer_main
        current_sizer = sizer_main
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
            try:
                this_section = c["section"]
            except KeyError:
                this_section = ""
            try:
                this_page = c["page"]
            except KeyError:
                this_page = ""
            try:
                trailer = c["trailer"]
            except KeyError:
                trailer = ""

            # get default value
            if hasattr(obj, attr):
                data = getattr(obj, attr)
            else:
                # if obj can lack attr, default must have been assigned.
                try:
                    data = c["default"]
                except KeyError:
                    continue
            data_style = c.get("style", None)
            data_type = type(data)
            if data_style in ("combo", "combosmall"):
                print ("initial data_type=", data_type.__name__)
            data_type = c.get("type", data_type)
            if data_style in ("combo", "combosmall"):
                print ("after data_type=", data_type.__name__)
            try:
                # Get label
                label = c["label"]
            except KeyError:
                # Undefined label is the attr
                label = attr
            if last_page != this_page:
                # We could do a notebook, but let's choose a simple StaticBoxSizer instead...
                last_box = wx.StaticBoxSizer(wx.StaticBox(self, id=wx.ID_ANY, label=_(this_page)), wx.VERTICAL)
                sizer_main.Add(last_box, 0, wx.EXPAND, 0 )
                current_main_sizer = last_box

            if last_section != this_section:
                last_box = wx.StaticBoxSizer(wx.StaticBox(self, id=wx.ID_ANY, label=_(this_section)), wx.VERTICAL)
                current_main_sizer.Add(last_box, 0, wx.EXPAND, 0 )
                current_sizer = last_box

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
                current_sizer.Add(control, 0, wx.EXPAND, 0)
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
                                self.context.signal(param, pathname)
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
                current_sizer.Add(control_sizer, 0, wx.EXPAND, 0)
            elif data_type in (str, int, float) and data_style == "combo":
                control_sizer = wx.StaticBoxSizer(
                    wx.StaticBox(self, wx.ID_ANY, label), wx.HORIZONTAL
                )
                choice_list = list(map(str, c.get("choices", [c.get("default")])))
                control = wx.ComboBox(
                    self,
                    wx.ID_ANY,
                    choices=choice_list,
                    style=wx.CB_DROPDOWN | wx.CB_READONLY,
                )
                control.SetValue(str(data))

                def on_combo_text(param, ctrl, obj, dtype):
                    def select(event=None):
                        v = dtype(ctrl.GetValue())
                        setattr(obj, param, v)
                        self.context.signal(param, v)

                    return select

                control_sizer.Add(control)
                control.Bind(
                    wx.EVT_COMBOBOX,
                    on_combo_text(attr, control, obj, data_type),
                )
                current_sizer.Add(control_sizer, 0, wx.EXPAND, 0)
            elif data_type in (str, int, float) and data_style == "combosmall":
                control_sizer = wx.BoxSizer(wx.HORIZONTAL)
                if label != "":
                    label_text = wx.StaticText(self, wx.ID_ANY, " " + label)
                    control_sizer.Add(label_text)

                choice_list = list(map(str, c.get("choices", [c.get("default")])))
                control = wx.ComboBox(
                    self,
                    wx.ID_ANY,
                    choices=choice_list,
                    style=wx.CB_DROPDOWN | wx.CB_READONLY,
                )
                control.SetValue(str(data))

                def on_combosmall_text(param, ctrl, obj, dtype):
                    def select(event=None):
                        v = dtype(ctrl.GetValue())
                        setattr(obj, param, v)
                        self.context.signal(param, v)

                    return select

                control_sizer.Add(control)
                control.Bind(
                    wx.EVT_COMBOBOX,
                    on_combosmall_text(attr, control, obj, data_type),
                )
                current_sizer.Add(control_sizer, 0, wx.EXPAND, 0)
            elif data_type == int and data_style == "binary":
                mask = c.get("mask")

                # get default value
                mask_bits = 0
                if mask is not None and hasattr(obj, mask):
                    mask_bits = getattr(obj, mask)

                control_sizer = wx.StaticBoxSizer(
                    wx.StaticBox(self, wx.ID_ANY, label), wx.HORIZONTAL
                )

                def on_checkbox_check(param, ctrl, obj, bit, enable_ctrl=None):
                    def check(event=None):
                        v = ctrl.GetValue()
                        if enable_ctrl is not None:
                            enable_ctrl.Enable(v)
                        current = getattr(obj, param)
                        if v:
                            current |= 1 << bit
                        else:
                            current = ~((~current) | (1 << bit))
                        setattr(obj, param, current)
                        self.context.signal(f"{param}", v)

                    return check

                bit_sizer = wx.BoxSizer(wx.VERTICAL)
                label_text = wx.StaticText(self, wx.ID_ANY, "", style=wx.ALIGN_CENTRE_HORIZONTAL)
                bit_sizer.Add(label_text, 0, wx.EXPAND, 0)
                if mask is not None:
                    label_text = wx.StaticText(self, wx.ID_ANY, _("mask") + " ", style=wx.ALIGN_CENTRE_HORIZONTAL)
                    bit_sizer.Add(label_text, 0, wx.EXPAND, 0)
                label_text = wx.StaticText(self, wx.ID_ANY, _("value") + " ", style=wx.ALIGN_CENTRE_HORIZONTAL)
                bit_sizer.Add(label_text, 0, wx.EXPAND, 0)
                control_sizer.Add(bit_sizer, 0, wx.EXPAND, 0)

                bits = c.get("bits", 8)
                for b in range(bits):
                    # Label
                    bit_sizer = wx.BoxSizer(wx.VERTICAL)
                    label_text = wx.StaticText(self, wx.ID_ANY, str(b), style=wx.ALIGN_CENTRE_HORIZONTAL)
                    bit_sizer.Add(label_text, 0, wx.EXPAND, 0)

                    # value bit
                    control = wx.CheckBox(self)
                    control.SetValue(bool((data >> b) & 1))
                    if mask:
                        control.Enable(bool((mask_bits >> b) & 1))
                    control.Bind(wx.EVT_CHECKBOX, on_checkbox_check(attr, control, obj, b))

                    # mask bit
                    if mask:
                        mask_ctrl = wx.CheckBox(self)
                        mask_ctrl.SetValue(bool((mask_bits >> b) & 1))
                        mask_ctrl.Bind(wx.EVT_CHECKBOX, on_checkbox_check(mask, mask_ctrl, obj, b, enable_ctrl=control))
                        bit_sizer.Add(mask_ctrl, 0, wx.EXPAND, 0)

                    bit_sizer.Add(control, 0, wx.EXPAND, 0)
                    control_sizer.Add(bit_sizer, 0, wx.EXPAND, 0)

                current_sizer.Add(control_sizer, 0, wx.EXPAND, 0)
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
                            dtype_v = dtype(v)
                            setattr(obj, param, dtype_v)
                            self.context.signal(param, dtype_v)
                        except ValueError:
                            # cannot cast to data_type, pass
                            pass

                    return text

                control.Bind(
                    wx.EVT_TEXT, on_textbox_text(attr, control, obj, data_type)
                )
                current_sizer.Add(control_sizer, 0, wx.EXPAND, 0)
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
                            data_v = v.preferred_length
                            setattr(obj, param, data_v)
                            self.context.signal(param, data_v)
                        except ValueError:
                            # cannot cast to data_type, pass
                            pass

                    return text

                control.Bind(
                    wx.EVT_TEXT, on_textbox_text(attr, control, obj, data_type)
                )
                current_sizer.Add(control_sizer, 0, wx.EXPAND, 0)
            elif data_type == Angle:
                # Angle type is a TextCtrl with special checks
                control_sizer = wx.StaticBoxSizer(
                    wx.StaticBox(self, wx.ID_ANY, label), wx.HORIZONTAL
                )
                control = wx.TextCtrl(self, -1)
                control.SetValue(str(data))
                control_sizer.Add(control)

                def on_textbox_text(param, ctrl, obj, dtype):
                    def text(event=None):
                        try:
                            v = Angle(ctrl.GetValue(), digits=5)
                            ctrl.SetBackgroundColour(None)
                            ctrl.Refresh()
                        except ValueError:
                            ctrl.SetBackgroundColour(wx.RED)
                            ctrl.Refresh()
                            return
                        try:
                            data_v = str(v)
                            setattr(obj, param, data_v)
                            self.context.signal(param, data_v)
                        except ValueError:
                            # cannot cast to data_type, pass
                            pass

                    return text

                control.Bind(
                    wx.EVT_TEXT, on_textbox_text(attr, control, obj, data_type)
                )
                current_sizer.Add(control_sizer, 0, wx.EXPAND, 0)
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
                                data_v = data_type(data)
                                setattr(obj, param, data_v)
                                self.context.signal(param, data_v)
                            except ValueError:
                                # cannot cast to data_type, pass
                                pass

                    return click

                set_color(data)
                control_sizer.Add(control)

                control.Bind(wx.EVT_BUTTON, on_button_color(attr, control, obj))
                current_sizer.Add(control_sizer, 0, wx.EXPAND, 0)
            else:
                # Requires a registered data_type
                continue
            if trailer != "":
                trailer_text = wx.StaticText(self, wx.ID_ANY, " " + trailer)
                control_sizer.Add(trailer_text)

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
                            try:
                                ctrl.Enable(enabled)
                            except RuntimeError:
                                pass

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
            last_page = this_page
            last_section = this_section

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        # Make sure stuff gets scrolled if necessary by default
        if scrolling:
            self.SetupScrolling()

    def pane_hide(self):
        for attr, listener in self.listeners:
            self.context.unlisten(attr, listener)

    def pane_show(self):
        pass
