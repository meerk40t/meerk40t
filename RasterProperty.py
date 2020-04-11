import wx

from Kernel import Module

_ = wx.GetTranslation


class RasterProperty(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: RasterProperty.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((359, 355))
        self.spin_speed_set = wx.SpinCtrlDouble(self, wx.ID_ANY, "200.0", min=0.0, max=500.0)
        self.spin_power_set = wx.SpinCtrlDouble(self, wx.ID_ANY, "1000.0", min=0.0, max=1000.0)
        self.spin_step_size = wx.SpinCtrl(self, wx.ID_ANY, "1", min=0, max=63)
        self.combo_raster_direction = wx.ComboBox(self, wx.ID_ANY, choices=[_("Top To Bottom"), _("Bottom To Top"), _("Right To Left"), _("Left To Right")], style=wx.CB_DROPDOWN)
        self.spin_overscan_set = wx.SpinCtrlDouble(self, wx.ID_ANY, "20.0", min=0.0, max=1000.0)
        self.radio_directional_raster = wx.RadioBox(self, wx.ID_ANY, _("Directional Raster"), choices=[_("Bidirectional"), _("Unidirectional")], majorDimension=2, style=wx.RA_SPECIFY_ROWS)
        self.radio_corner = wx.RadioBox(self, wx.ID_ANY, _("Start Corner"), choices=[" ", " ", " ", " "], majorDimension=2, style=wx.RA_SPECIFY_ROWS)
        self.combo_second_pass = wx.ComboBox(self, wx.ID_ANY, choices=[_("None"), _("Crosshatch"), _("Backwards"), _("Repeat")], style=wx.CB_DROPDOWN)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_speed, self.spin_speed_set)
        self.Bind(wx.EVT_TEXT, self.on_spin_speed, self.spin_speed_set)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_speed, self.spin_speed_set)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_power, self.spin_power_set)
        self.Bind(wx.EVT_TEXT, self.on_spin_power, self.spin_power_set)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_power, self.spin_power_set)
        self.Bind(wx.EVT_SPINCTRL, self.on_spin_step, self.spin_step_size)
        self.Bind(wx.EVT_TEXT, self.on_spin_step, self.spin_step_size)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_step, self.spin_step_size)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_raster_direction, self.combo_raster_direction)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_overscan, self.spin_overscan_set)
        self.Bind(wx.EVT_TEXT, self.on_spin_overscan, self.spin_overscan_set)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_overscan, self.spin_overscan_set)
        self.Bind(wx.EVT_RADIOBOX, self.on_radio_directional, self.radio_directional_raster)
        self.Bind(wx.EVT_RADIOBOX, self.on_radio_corner, self.radio_corner)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_second_pass, self.combo_second_pass)
        # end wxGlade
        self.kernel = None
        self.operation = None
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def on_close(self, event):
        self.kernel.module_instance_remove(self.name)
        event.Skip()  # Call destroy.

    def set_operation(self, operation):
        self.operation = operation
        try:
            if operation.speed is not None:
                self.spin_speed_set.SetValue(operation.speed)
        except AttributeError:
            self.spin_speed_set.Enable(False)
        try:
            if operation.power is not None:
                self.spin_power_set.SetValue(operation.power)
        except AttributeError:
            self.spin_power_set.Enable(False)

        try:
            if operation.raster_step is not None:
                self.spin_step_size.SetValue(operation.raster_step)
        except AttributeError:
            self.spin_step_size.Enable(False)

        try:
            if operation.overscan is not None:
                self.spin_overscan_set.SetValue(operation.overscan)
        except AttributeError:
            self.spin_overscan_set.Enable(False)

        try:
            if operation.raster_direction is not None:
                self.combo_raster_direction.SetSelection(operation.raster_direction)
        except AttributeError:
            self.combo_raster_direction.Enable(False)

        try:
            if operation.bidirectional is not None:
                self.radio_directional_raster.SetSelection(operation.bidirectional)
        except AttributeError:
            self.radio_directional_raster.Enable(False)

        try:
            if operation.corner is not None:
                self.radio_corner.SetSelection(operation.corner)
        except AttributeError:
            self.radio_corner.Enable(False)

        try:
            if operation.second_pass is not None:
                self.combo_second_pass.SetSelection(operation.second_pass)
        except AttributeError:
            self.combo_second_pass.Enable(False)
        return self

    def initialize(self, kernel, name=None):
        kernel.module_instance_close(name)
        Module.initialize(kernel, name)
        self.kernel = kernel
        self.name = name
        self.Show()

    def shutdown(self, kernel):
        self.Close()
        Module.shutdown(self, kernel)
        self.kernel = None

    def __set_properties(self):
        # begin wxGlade: RasterProperty.__set_properties
        self.SetTitle(_("Raster Properties"))
        self.spin_speed_set.SetMinSize((100, 23))
        self.spin_speed_set.SetToolTip(_("Speed at which to perform the action in mm/s."))
        self.spin_power_set.SetMinSize((100, 23))
        self.spin_power_set.SetToolTip(_("1000 always on. 500 it's half power (fire every other step). This is software PPI control."))
        self.spin_step_size.SetMinSize((100, 23))
        self.spin_step_size.SetToolTip(_("Scan gap / step size, is the distance between scanlines in a raster engrave. Distance here is in 1/1000th of an inch."))
        self.combo_raster_direction.SetToolTip(_("Direction to perform a raster"))
        self.combo_raster_direction.SetSelection(0)
        self.spin_overscan_set.SetMinSize((100, 23))
        self.spin_overscan_set.SetToolTip(_("Overscan amount"))
        self.radio_directional_raster.SetToolTip(_("Rastering on forward and backswing or only forward swing?"))
        self.radio_directional_raster.Enable(False)
        self.radio_directional_raster.SetSelection(0)
        self.radio_corner.SetToolTip(_("Which corner should we start in?"))
        self.radio_corner.Enable(False)
        self.radio_corner.SetSelection(0)
        self.combo_second_pass.SetToolTip(_("Direction to perform a second pass rastering"))
        self.combo_second_pass.Enable(False)
        self.combo_second_pass.SetSelection(0)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: RasterProperty.__do_layout
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_7 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Second Pass")), wx.HORIZONTAL)
        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_6 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        label_1 = wx.StaticText(self, wx.ID_ANY, _("Speed"))
        sizer_1.Add(label_1, 1, 0, 0)
        sizer_1.Add(self.spin_speed_set, 1, 0, 0)
        label_2 = wx.StaticText(self, wx.ID_ANY, _("mm/s"))
        sizer_1.Add(label_2, 1, 0, 0)
        sizer_8.Add(sizer_1, 1, wx.EXPAND, 0)
        label_3 = wx.StaticText(self, wx.ID_ANY, _("Power"))
        sizer_2.Add(label_3, 1, 0, 0)
        sizer_2.Add(self.spin_power_set, 1, 0, 0)
        label_8 = wx.StaticText(self, wx.ID_ANY, _("ppi"))
        sizer_2.Add(label_8, 1, 0, 0)
        sizer_8.Add(sizer_2, 1, wx.EXPAND, 0)
        label_7 = wx.StaticText(self, wx.ID_ANY, _("Raster Step"))
        sizer_3.Add(label_7, 1, 0, 0)
        sizer_3.Add(self.spin_step_size, 1, 0, 0)
        label_4 = wx.StaticText(self, wx.ID_ANY, _(" mil"))
        sizer_3.Add(label_4, 1, 0, 0)
        sizer_8.Add(sizer_3, 1, wx.EXPAND, 0)
        label_5 = wx.StaticText(self, wx.ID_ANY, _("Raster Direction"))
        sizer_4.Add(label_5, 1, 0, 0)
        sizer_4.Add(self.combo_raster_direction, 1, 0, 0)
        label_10 = wx.StaticText(self, wx.ID_ANY, "")
        sizer_4.Add(label_10, 1, 0, 0)
        sizer_8.Add(sizer_4, 1, wx.EXPAND, 0)
        label_6 = wx.StaticText(self, wx.ID_ANY, _("Overscan"))
        sizer_6.Add(label_6, 1, 0, 0)
        sizer_6.Add(self.spin_overscan_set, 1, 0, 0)
        label_9 = wx.StaticText(self, wx.ID_ANY, _("mils"))
        sizer_6.Add(label_9, 1, 0, 0)
        sizer_8.Add(sizer_6, 1, wx.EXPAND, 0)
        sizer_5.Add(self.radio_directional_raster, 3, wx.EXPAND, 0)
        sizer_5.Add(self.radio_corner, 1, 0, 0)
        sizer_8.Add(sizer_5, 1, wx.EXPAND, 0)
        sizer_7.Add(self.combo_second_pass, 3, 0, 0)
        sizer_8.Add(sizer_7, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_8)
        self.Layout()
        self.Centre()
        # end wxGlade

    def on_spin_speed(self, event):  # wxGlade: ElementProperty.<event_handler>
        self.operation.speed = self.spin_speed_set.GetValue()
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.operation)

    def on_spin_power(self, event):
        self.operation.power = self.spin_power_set.GetValue()
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.operation)

    def on_spin_step(self, event):  # wxGlade: ElementProperty.<event_handler>
        self.operation.raster_step = self.spin_step_size.GetValue()
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.operation)

    def on_combo_raster_direction(self, event):  # wxGlade: Preferences.<event_handler>
        self.operation.raster_direction = self.combo_raster_direction.GetSelection()
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.operation)

    def on_combo_second_pass(self, event):  # wxGlade: RasterProperty.<event_handler>
        self.operation.second_pass = self.combo_second_pass.GetSelection()
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.operation)

    def on_spin_overscan(self, event):  # wxGlade: RasterProperty.<event_handler>
        self.operation.overscan = self.spin_overscan_set.GetValue()
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.operation)

    def on_radio_directional(self, event):  # wxGlade: RasterProperty.<event_handler>
        self.operation.bidirectional = self.radio_directional_raster.GetSelection()
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.operation)

    def on_radio_corner(self, event):  # wxGlade: RasterProperty.<event_handler>
        self.operation.corner = self.radio_corner.GetSelection()
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.operation)

