import wx
from wx.lib.scrolledpanel import ScrolledPanel

from meerk40t.core.units import Angle, Length
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.wxutils import TextCtrl
from meerk40t.kernel import Context
from meerk40t.svgelements import Color

_ = wx.GetTranslation


class ChoicePropertyPanel(ScrolledPanel):
    """
    ChoicePropertyPanel is a generic panel that presents a list of properties to be viewed and edited.
    In most cases it can be initialized by passing a choices value which will read the registered choice values
    and display the given properties, automatically generating an appropriate changers for that property.

    In most cases the ChoicePropertyPanel should be used for properties of a dynamic nature. A lot of different
    relationships can be established and the class should be kept fairly easy to extend. With a set dictionary
    either registered in the Kernel as a choice or called directly on the ChoicePropertyPanel you can make dynamic
    controls to set various properties. This avoids needing to create a new static window when a panel is just
    providing options to change settings.
    """

    def __init__(
        self,
        *args,
        context: Context = None,
        choices=None,
        scrolling=True,
        constraint=None,
        **kwds,
    ):
        # constraints is either
        # - None (default) - all choices will be display
        # - a pair of integers (start, end), from where to where (index) to display
        #   use case: display the first 10 entries constraint=(0, 9)
        #   then the remaining: constraint=(10, -1)
        #   -1 defines the min / max boundaries
        # - a list of strings that describe
        #   the pages to show : constraint=("page1", "page2")
        #   the pages to omit : constraint=("-page1", "-page2")
        #   a leading hyphen establishes omission
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
        prechoices = sorted(
            sorted(choices, key=lambda d: d["section"]), key=lambda d: d["page"]
        )
        self.choices = list()
        dealt_with = False
        if constraint is not None:
            if isinstance(constraint, (tuple, list, str)):
                if isinstance(constraint, str):
                    # make it a tuple
                    constraint = (constraint,)
                if len(constraint) > 0:
                    if isinstance(constraint[0], str):
                        dealt_with = True
                        # Section list
                        positive = list()
                        negative = list()
                        for item in constraint:
                            if item.startswith("-"):
                                item = item[1:]
                                negative.append(item.lower())
                            else:
                                positive.append(item.lower())
                        for i, c in enumerate(prechoices):
                            try:
                                this_page = c["page"].lower()
                            except KeyError:
                                this_page = ""
                            if len(negative) > 0 and len(positive) > 0:
                                # Negative takes precedence:
                                if not this_page in negative and this_page in positive:
                                    self.choices.append(c)
                            elif len(negative) > 0:
                                # only negative....
                                if not this_page in negative:
                                    self.choices.append(c)
                            elif len(positive) > 0:
                                # only positive....
                                if this_page in positive:
                                    self.choices.append(c)
                    else:
                        dealt_with = True
                        # Section list
                        startfrom = 0
                        endat = len(prechoices)
                        if constraint[0] >= 0:
                            startfrom = constraint[0]
                        if len(constraint) > 1 and constraint[1] >= 0:
                            endat = constraint[1]
                        if startfrom < 0:
                            startfrom = 0
                        if endat > len(prechoices):
                            endat = len(prechoices)
                        if endat < startfrom:
                            endat = len(prechoices)
                        for i, c in enumerate(prechoices):
                            if i >= startfrom and i < endat:
                                self.choices.append(c)
        else:
            # Empty constraint
            pass
        if not dealt_with:
            # no valid constraints
            self.choices = prechoices
        if len(self.choices) == 0:
            return
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
            data_type = c.get("type", data_type)
            try:
                # Get label
                label = c["label"]
            except KeyError:
                # Undefined label is the attr
                label = attr
            if last_page != this_page:
                last_section = ""
                # We could do a notebook, but let's choose a simple StaticBoxSizer instead...
                last_box = wx.StaticBoxSizer(
                    wx.StaticBox(self, id=wx.ID_ANY, label=_(this_page)), wx.VERTICAL
                )
                sizer_main.Add(last_box, 0, wx.EXPAND, 0)
                current_main_sizer = last_box
                current_sizer = last_box

            if last_section != this_section:
                last_box = wx.StaticBoxSizer(
                    wx.StaticBox(self, id=wx.ID_ANY, label=_(this_section)), wx.VERTICAL
                )
                current_main_sizer.Add(last_box, 0, wx.EXPAND, 0)
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
                control_sizer.Add(control, 0, wx.EXPAND, 0)
                control.Bind(
                    wx.EVT_BUTTON,
                    on_button_filename(attr, control, obj, c.get("wildcard", "*")),
                )
                current_sizer.Add(control_sizer, 0, wx.EXPAND, 0)
            elif data_type in (int, float) and data_style == "slider":
                control_sizer = wx.StaticBoxSizer(
                    wx.StaticBox(self, wx.ID_ANY, label), wx.HORIZONTAL
                )
                minvalue = c.get("min", 0)
                maxvalue = c.get("max", 0)
                if data_type == float:
                    value = float(data)
                elif data_type == int:
                    value = int(data)
                else:
                    value = int(data)
                control = wx.Slider(
                    self,
                    wx.ID_ANY,
                    value=value,
                    minValue=minvalue,
                    maxValue=maxvalue,
                    style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
                )

                def on_slider(param, ctrl, obj, dtype):
                    def select(event=None):
                        v = dtype(ctrl.GetValue())
                        setattr(obj, param, v)
                        self.context.signal(param, v)

                    return select

                control_sizer.Add(control, 1, wx.EXPAND, 0)
                control.Bind(
                    wx.EVT_SLIDER,
                    on_slider(attr, control, obj, data_type),
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
                if data is not None:
                    if data_type == str:
                        control.SetValue(str(data))
                    else:
                        least = None
                        for entry in choice_list:
                            if least is None:
                                least = entry
                            else:
                                if abs(data_type(entry) - data) < abs(
                                    data_type(least) - data
                                ):
                                    least = entry
                        if least is not None:
                            control.SetValue(least)

                def on_combo_text(param, ctrl, obj, dtype):
                    def select(event=None):
                        v = dtype(ctrl.GetValue())
                        setattr(obj, param, v)
                        self.context.signal(param, v)

                    return select

                control_sizer.Add(control, 1, wx.EXPAND, 0)
                control.Bind(
                    wx.EVT_COMBOBOX,
                    on_combo_text(attr, control, obj, data_type),
                )
                current_sizer.Add(control_sizer, 0, wx.EXPAND, 0)
            elif data_type in (str, int, float) and data_style == "combosmall":
                control_sizer = wx.BoxSizer(wx.HORIZONTAL)

                choice_list = list(map(str, c.get("choices", [c.get("default")])))
                control = wx.ComboBox(
                    self,
                    wx.ID_ANY,
                    choices=choice_list,
                    style=wx.CB_DROPDOWN | wx.CB_READONLY,
                )
                # print ("Choices: %s" % choice_list)
                # print ("To set: %s" % str(data))
                if data is not None:
                    if data_type == str:
                        control.SetValue(str(data))
                    else:
                        least = None
                        for entry in choice_list:
                            if least is None:
                                least = entry
                            else:
                                if abs(data_type(entry) - data) < abs(
                                    data_type(least) - data
                                ):
                                    least = entry
                        if least is not None:
                            control.SetValue(least)

                def on_combosmall_text(param, ctrl, obj, dtype):
                    def select(event=None):
                        v = dtype(ctrl.GetValue())
                        setattr(obj, param, v)
                        self.context.signal(param, v)

                    return select

                if label != "":
                    # Try to center it vertically to the controls extent
                    wd, ht = control.GetSize()
                    label_text = wx.StaticText(self, id=wx.ID_ANY, label=label + " ")
                    # label_text.SetMinSize((-1, ht))
                    control_sizer.Add(label_text, 0, wx.ALIGN_CENTER_VERTICAL, 0)
                control_sizer.Add(control, 0, wx.ALIGN_CENTER_VERTICAL, 0)
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
                label_text = wx.StaticText(
                    self, wx.ID_ANY, "", style=wx.ALIGN_CENTRE_HORIZONTAL
                )
                bit_sizer.Add(label_text, 0, wx.EXPAND, 0)
                if mask is not None:
                    label_text = wx.StaticText(
                        self,
                        wx.ID_ANY,
                        _("mask") + " ",
                        style=wx.ALIGN_CENTRE_HORIZONTAL,
                    )
                    bit_sizer.Add(label_text, 0, wx.EXPAND, 0)
                label_text = wx.StaticText(
                    self, wx.ID_ANY, _("value") + " ", style=wx.ALIGN_CENTRE_HORIZONTAL
                )
                bit_sizer.Add(label_text, 0, wx.EXPAND, 0)
                control_sizer.Add(bit_sizer, 0, wx.EXPAND, 0)

                bits = c.get("bits", 8)
                for b in range(bits):
                    # Label
                    bit_sizer = wx.BoxSizer(wx.VERTICAL)
                    label_text = wx.StaticText(
                        self, wx.ID_ANY, str(b), style=wx.ALIGN_CENTRE_HORIZONTAL
                    )
                    bit_sizer.Add(label_text, 0, wx.EXPAND, 0)

                    # value bit
                    control = wx.CheckBox(self)
                    control.SetValue(bool((data >> b) & 1))
                    if mask:
                        control.Enable(bool((mask_bits >> b) & 1))
                    control.Bind(
                        wx.EVT_CHECKBOX, on_checkbox_check(attr, control, obj, b)
                    )

                    # mask bit
                    if mask:
                        mask_ctrl = wx.CheckBox(self)
                        mask_ctrl.SetValue(bool((mask_bits >> b) & 1))
                        mask_ctrl.Bind(
                            wx.EVT_CHECKBOX,
                            on_checkbox_check(
                                mask, mask_ctrl, obj, b, enable_ctrl=control
                            ),
                        )
                        bit_sizer.Add(mask_ctrl, 0, wx.EXPAND, 0)

                    bit_sizer.Add(control, 0, wx.EXPAND, 0)
                    control_sizer.Add(bit_sizer, 0, wx.EXPAND, 0)

                current_sizer.Add(control_sizer, 0, wx.EXPAND, 0)
            elif data_type in (str, int, float):
                # str, int, and float type objects get a TextCtrl setter.
                control_sizer = wx.StaticBoxSizer(
                    wx.StaticBox(self, wx.ID_ANY, label), wx.HORIZONTAL
                )
                if data_type == int:
                    check_flag = "int"
                elif data_type == float:
                    check_flag = "float"
                else:
                    check_flag = ""
                control = TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER, limited=True, check=check_flag)
                control.SetValue(str(data))
                control_sizer.Add(control, 1, wx.EXPAND, 0)

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
                    wx.EVT_KILL_FOCUS, on_textbox_text(attr, control, obj, data_type)
                )
                control.Bind(
                    wx.EVT_TEXT_ENTER, on_textbox_text(attr, control, obj, data_type)
                )
                current_sizer.Add(control_sizer, 0, wx.EXPAND, 0)
            elif data_type == Length:
                # Length type is a TextCtrl with special checks
                control_sizer = wx.StaticBoxSizer(
                    wx.StaticBox(self, wx.ID_ANY, label), wx.HORIZONTAL
                )
                control = TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER, limited=True, check="length")
                control.SetValue(str(data))
                control_sizer.Add(control, 1, wx.EXPAND, 0)

                def on_textbox_text(param, ctrl, obj, dtype):
                    def text(event=None):
                        try:
                            v = Length(ctrl.GetValue())
                            data_v = v.preferred_length
                            setattr(obj, param, data_v)
                            self.context.signal(param, data_v)
                        except ValueError:
                            # cannot cast to data_type, pass
                            pass

                    return text

                control.Bind(
                    wx.EVT_KILL_FOCUS, on_textbox_text(attr, control, obj, data_type)
                )
                control.Bind(
                    wx.EVT_TEXT_ENTER, on_textbox_text(attr, control, obj, data_type)
                )
                current_sizer.Add(control_sizer, 0, wx.EXPAND, 0)
            elif data_type == Angle:
                # Angle type is a TextCtrl with special checks
                control_sizer = wx.StaticBoxSizer(
                    wx.StaticBox(self, wx.ID_ANY, label), wx.HORIZONTAL
                )
                control = TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER, check="angle", limited=True)
                control.SetValue(str(data))
                control_sizer.Add(control, 1, wx.EXPAND, 0)

                def on_textbox_text(param, ctrl, obj, dtype):
                    def text(event=None):
                        try:
                            v = Angle(ctrl.GetValue(), digits=5)
                            data_v = str(v)
                            setattr(obj, param, data_v)
                            self.context.signal(param, data_v)
                        except ValueError:
                            # cannot cast to data_type, pass
                            pass

                    return text

                control.Bind(
                    wx.EVT_KILL_FOCUS, on_textbox_text(attr, control, obj, data_type)
                )
                control.Bind(
                    wx.EVT_TEXT_ENTER, on_textbox_text(attr, control, obj, data_type)
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
                control_sizer.Add(control, 0, wx.EXPAND, 0)

                control.Bind(wx.EVT_BUTTON, on_button_color(attr, control, obj))
                current_sizer.Add(control_sizer, 0, wx.EXPAND, 0)
            else:
                # Requires a registered data_type
                continue
            if trailer != "":
                # Try to center it vertically to the controls extent
                wd, ht = control.GetSize()
                trailerflag = wx.ALIGN_CENTER_VERTICAL
                trailer_text = wx.StaticText(self, id=wx.ID_ANY, label=" " + trailer)
                # trailer_text.SetMinSize((-1, ht))
                control_sizer.Add(trailer_text, 0, trailerflag, 0)

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
