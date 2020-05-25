
import wx

from Kernel import Module

_ = wx.GetTranslation


class EngraveProperty(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: EngraveProperty.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((305, 216))
        self.spin_speed_set = wx.SpinCtrlDouble(self, wx.ID_ANY, "20.0", min=0.0, max=240.0)
        self.spin_power_set = wx.SpinCtrlDouble(self, wx.ID_ANY, "1000.0", min=0.0, max=1000.0)
        self.checkbox_custom_d_ratio = wx.CheckBox(self, wx.ID_ANY, _("Custom D-Ratio"))
        self.spin_speed_dratio = wx.SpinCtrlDouble(self, wx.ID_ANY, "0.261", min=0.0, max=1.0)
        self.checkbox_custom_accel = wx.CheckBox(self, wx.ID_ANY, _("Acceleration Override"))
        self.slider_accel = wx.Slider(self, wx.ID_ANY, 1, 1, 4, style=wx.SL_AUTOTICKS | wx.SL_LABELS)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_speed, self.spin_speed_set)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_speed, self.spin_speed_set)
        self.Bind(wx.EVT_TEXT, self.on_spin_speed, self.spin_speed_set)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_power, self.spin_power_set)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_power, self.spin_power_set)
        self.Bind(wx.EVT_TEXT, self.on_spin_power, self.spin_power_set)
        self.Bind(wx.EVT_CHECKBOX, lambda e: self.spin_speed_dratio.Enable(self.checkbox_custom_d_ratio.GetValue()), self.checkbox_custom_d_ratio)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_speed_dratio, self.spin_speed_dratio)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_speed_dratio, self.spin_speed_dratio)
        self.Bind(wx.EVT_TEXT, self.on_spin_speed_dratio, self.spin_speed_dratio)
        self.Bind(wx.EVT_CHECKBOX, lambda e: self.slider_accel.Enable(self.checkbox_custom_accel.GetValue()), self.checkbox_custom_accel)
        self.Bind(wx.EVT_COMMAND_SCROLL, self.on_slider_accel, self.slider_accel)
        self.operation = None
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def set_operation(self, operation):
        self.operation = operation
        try:
            if operation.speed is not None:
                self.spin_speed_set.SetValue(operation.speed)
        except AttributeError:
            self.spin_speed_set.Enable(False)
        try:
            if operation.parse_power is not None:
                self.spin_power_set.SetValue(operation.parse_power)
        except AttributeError:
            self.spin_power_set.Enable(False)

        try:
            if operation.dratio is not None:
                self.spin_speed_dratio.SetValue(operation.dratio)
        except AttributeError:
            self.spin_speed_dratio.Enable(False)
            self.checkbox_custom_d_ratio.Enable(False)

        try:
            if operation.accel is not None:
                self.slider_accel.SetValue(operation.accel)
        except AttributeError:
            self.slider_accel.Enable(False)
            self.checkbox_custom_accel.Enable(False)
        return self

    def initialize(self):
        self.device.close('window', self.name)
        self.Show()

    def shutdown(self,  channel):
        self.Close()

    def on_close(self, event):
        self.device.remove('window', self.name)
        event.Skip()  # Call destroy.

    def __set_properties(self):
        # begin wxGlade: EngraveProperty.__set_properties
        self.SetTitle(_("Engrave Properties"))
        self.spin_speed_set.SetMinSize((100, 23))
        self.spin_speed_set.SetToolTip(_("Speed at which to perform the action in mm/s."))
        self.spin_power_set.SetMinSize((100, 23))
        self.spin_power_set.SetToolTip(_("1000 always on. 500 it's half power (fire every other step). This is software PPI control."))
        self.checkbox_custom_d_ratio.SetToolTip(_("Enables the ability to modify the diagonal ratio."))
        self.spin_speed_dratio.SetMinSize((100, 23))
        self.spin_speed_dratio.SetToolTip(_("Diagonal ratio is the ratio of additional time needed to perform a diagonal step rather than an orthogonal step."))
        self.spin_speed_dratio.Enable(False)
        self.spin_speed_dratio.SetIncrement(0.01)
        self.checkbox_custom_accel.SetToolTip(_("Enables the ability to modify the acceleration factor."))
        self.slider_accel.SetToolTip(_("Acceleration Factor Override"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: EngraveProperty.__do_layout
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_11 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_9 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_7 = wx.BoxSizer(wx.HORIZONTAL)
        label_1 = wx.StaticText(self, wx.ID_ANY, _("Speed"))
        sizer_7.Add(label_1, 0, 0, 0)
        sizer_7.Add(self.spin_speed_set, 0, 0, 0)
        label_2 = wx.StaticText(self, wx.ID_ANY, _("mm/s"))
        sizer_7.Add(label_2, 0, 0, 0)
        sizer_8.Add(sizer_7, 1, wx.EXPAND, 0)
        label_3 = wx.StaticText(self, wx.ID_ANY, _("Power"))
        sizer_9.Add(label_3, 0, 0, 0)
        sizer_9.Add(self.spin_power_set, 0, 0, 0)
        label_8 = wx.StaticText(self, wx.ID_ANY, _("ppi"))
        sizer_9.Add(label_8, 0, 0, 0)
        sizer_8.Add(sizer_9, 1, wx.EXPAND, 0)
        sizer_10.Add(self.checkbox_custom_d_ratio, 1, 0, 0)
        sizer_10.Add(self.spin_speed_dratio, 1, 0, 0)
        sizer_8.Add(sizer_10, 1, wx.EXPAND, 0)
        sizer_11.Add(self.checkbox_custom_accel, 1, 0, 0)
        sizer_11.Add(self.slider_accel, 1, wx.EXPAND, 0)
        sizer_8.Add(sizer_11, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_8)
        self.Layout()
        self.Centre()
        # end wxGlade

    def on_spin_speed(self, event):  # wxGlade: ElementProperty.<event_handler>
        self.operation.speed = self.spin_speed_set.GetValue()
        self.device.device_root.engrave_speed = self.operation.speed
        self.device.signal("element_property_update", self.operation)

    def on_spin_power(self, event):
        self.operation.parse_power = self.spin_power_set.GetValue()
        self.device.device_root.engrave_power = self.operation.parse_power
        self.device.signal("element_property_update", self.operation)

    def on_spin_speed_dratio(self, event):  # wxGlade: ElementProperty.<event_handler>
        self.operation.dratio = self.spin_speed_dratio.GetValue()
        self.device.device_root.engrave_dratio = self.operation.dratio
        self.device.signal("element_property_update", self.operation)

    def on_slider_accel(self, event):  # wxGlade: EngraveProperty.<event_handler>
        self.operation.accel = self.slider_accel.GetValue()
        self.device.signal("element_property_update", self.operation)
