import wx

from meerk40t.gui.wxutils import TextCtrl

_ = wx.GetTranslation


class LhyAdvancedPanel(wx.Panel):
    name = "Advanced"

    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LhyAdvancedPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        extras_sizer = wx.BoxSizer(wx.VERTICAL)

        advanced_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Speed Code Features:")), wx.VERTICAL
        )
        extras_sizer.Add(advanced_sizer, 0, wx.EXPAND, 0)

        sizer_11 = wx.BoxSizer(wx.HORIZONTAL)
        advanced_sizer.Add(sizer_11, 0, wx.EXPAND, 0)

        self.check_dratio_custom = wx.CheckBox(self, wx.ID_ANY, _("Custom D-Ratio"))
        self.check_dratio_custom.SetToolTip(
            _("Enables the ability to modify the diagonal ratio.")
        )
        sizer_11.Add(self.check_dratio_custom, 1, 0, 0)

        self.text_dratio = TextCtrl(
            self,
            wx.ID_ANY,
            "0.261",
            limited=True,
            check="float",
            style=wx.TE_PROCESS_ENTER,
        )
        OPERATION_DRATIO_TOOLTIP = _(
            "Diagonal ratio is the ratio of additional time needed to perform a diagonal step "
            + "rather than an orthogonal step. (0.261 default)"
        )

        self.text_dratio.SetToolTip(OPERATION_DRATIO_TOOLTIP)
        sizer_11.Add(self.text_dratio, 1, 0, 0)

        sizer_12 = wx.BoxSizer(wx.HORIZONTAL)
        advanced_sizer.Add(sizer_12, 0, wx.EXPAND, 0)

        self.checkbox_custom_accel = wx.CheckBox(self, wx.ID_ANY, _("Acceleration"))
        self.checkbox_custom_accel.SetToolTip(_("Enables acceleration override"))
        sizer_12.Add(self.checkbox_custom_accel, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_accel = wx.Slider(
            self, wx.ID_ANY, 1, 1, 4, style=wx.SL_AUTOTICKS | wx.SL_LABELS
        )
        OPERATION_ACCEL_TOOLTIP = (
            _(
                "The m2-nano controller has four acceleration settings, and automatically "
                + "selects the appropriate setting for the Cut or Raster speed."
            )
            + "\n"
            + _(
                "This setting allows you to override the automatic selection and specify your own."
            )
        )
        self.slider_accel.SetToolTip(OPERATION_ACCEL_TOOLTIP)
        sizer_12.Add(self.slider_accel, 1, wx.EXPAND, 0)

        advanced_ppi_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Plot Planner")), wx.HORIZONTAL
        )
        extras_sizer.Add(advanced_ppi_sizer, 0, wx.EXPAND, 0)

        sizer_19 = wx.BoxSizer(wx.VERTICAL)
        advanced_ppi_sizer.Add(sizer_19, 1, wx.EXPAND, 0)

        sizer_20 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_19.Add(sizer_20, 1, wx.EXPAND, 0)

        self.check_dot_length_custom = wx.CheckBox(self, wx.ID_ANY, _("Dot Length"))
        self.check_dot_length_custom.SetToolTip(_("Enable Dot Length"))
        sizer_20.Add(self.check_dot_length_custom, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.text_dot_length = TextCtrl(
            self, wx.ID_ANY, "1", limited=True, check="int", style=wx.TE_PROCESS_ENTER
        )
        OPERATION_DOTLENGTH_TOOLTIP = _(
            _(
                "For Cut/Engrave operations, when using PPI, Dot Length sets the minimum "
                + "length for the laser to be on in order to change a continuous lower "
                + "power burn into a series of dashes."
            )
            + "\n"
            + _(
                "When this is set, the PPI effectively becomes the ratio of "
                + "dashes to gaps. For example:"
            )
            + "\n"
            + _(
                'If you set Dot Length to 500 = 1/2", a PPI of 500 would result in '
                + '1/2" dashes and 1/2" gaps.'
            )
            + "\n"
            + _(
                'If you set Dot Length to 250 = 1/4", a PPI of 250 would result in 1/4" dashes and 3/4" gaps.'
            )
        )

        self.text_dot_length.SetToolTip(OPERATION_DOTLENGTH_TOOLTIP)
        sizer_20.Add(self.text_dot_length, 1, wx.EXPAND, 0)

        self.combo_dot_length_units = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["steps", "mm", "cm", "inch", "mil", "%"],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_dot_length_units.SetSelection(0)
        sizer_20.Add(self.combo_dot_length_units, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.check_shift_enabled = wx.CheckBox(self, wx.ID_ANY, _("Pulse Grouping"))
        OPERATION_SHIFT_TOOLTIP = (
            _(
                "Pulse Grouping is an alternative means of reducing the incidence of "
                "stuttering, allowing you potentially to burn at higher speeds."
            )
            + "\n"
            + _(
                "It works by swapping adjacent on or off bits to group on and off together"
                " and reduce the number of switches."
            )
            + "\n"
            + _(
                "As an example, instead of X_X_ it will burn XX__ - because the laser beam"
                ' is overlapping, and because a bit is only moved at most 1/1000", the '
                "difference should not be visible even under magnification."
            )
        )

        self.check_shift_enabled.SetToolTip(OPERATION_SHIFT_TOOLTIP)
        sizer_19.Add(self.check_shift_enabled, 0, 0, 0)

        self.SetSizer(extras_sizer)

        self.Layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_dratio, self.check_dratio_custom)
        self.text_dratio.SetActionRoutine(self.on_text_dratio)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_acceleration, self.checkbox_custom_accel
        )
        self.Bind(wx.EVT_COMMAND_SCROLL, self.on_slider_accel, self.slider_accel)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_dot_length, self.check_dot_length_custom
        )
        self.text_dot_length.SetActionRoutine(self.on_text_dot_length)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_shift_enabled, self.check_shift_enabled
        )
        # end wxGlade

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def set_widgets(self, node):
        self.operation = node
        if self.operation.dratio is not None:
            self.text_dratio.SetValue(str(self.operation.dratio))
        if self.operation.dratio_custom is not None:
            self.check_dratio_custom.SetValue(self.operation.dratio_custom)
        if self.operation.acceleration is not None:
            self.slider_accel.SetValue(self.operation.acceleration)
        if self.operation.acceleration_custom is not None:
            self.checkbox_custom_accel.SetValue(self.operation.acceleration_custom)
            self.slider_accel.Enable(self.checkbox_custom_accel.GetValue())
        if self.operation.dot_length_custom is not None:
            self.check_dot_length_custom.SetValue(self.operation.dot_length_custom)
        if self.operation.dot_length is not None:
            self.text_dot_length.SetValue(str(self.operation.dot_length))
        if self.operation.shift_enabled is not None:
            self.check_shift_enabled.SetValue(self.operation.shift_enabled)
        on = self.check_dratio_custom.GetValue()
        self.text_dratio.Enable(on)
        on = self.check_dot_length_custom.GetValue()
        self.text_dot_length.Enable(on)

    def on_check_dratio(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        on = self.check_dratio_custom.GetValue()
        self.text_dratio.Enable(on)
        self.operation.dratio_custom = bool(on)
        self.context.elements.signal("element_property_reload", self.operation)

    def on_text_dratio(self):
        try:
            self.operation.dratio = float(self.text_dratio.GetValue())
        except ValueError:
            return
        self.context.elements.signal("element_property_reload", self.operation)

    def on_check_acceleration(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        on = self.checkbox_custom_accel.GetValue()
        self.slider_accel.Enable(on)
        self.operation.acceleration_custom = bool(on)
        self.context.elements.signal("element_property_reload", self.operation)

    def on_slider_accel(self, event=None):
        self.operation.acceleration = self.slider_accel.GetValue()
        self.context.elements.signal("element_property_reload", self.operation)

    def on_check_dot_length(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        on = self.check_dot_length_custom.GetValue()
        self.text_dot_length.Enable(on)
        self.operation.dot_length_custom = bool(on)
        self.context.elements.signal("element_property_reload", self.operation)

    def on_text_dot_length(self):
        try:
            self.operation.dot_length = int(self.text_dot_length.GetValue())
        except ValueError:
            return
        self.context.elements.signal("element_property_reload", self.operation)

    def on_check_shift_enabled(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        self.operation.shift_enabled = bool(self.check_shift_enabled.GetValue())
        self.context.elements.signal("element_property_reload", self.operation)
