import wx

from meerk40t.gui.icons import icons8_laser_beam_52

MILS_IN_MM = 39.3701

_ = wx.GetTranslation


class PulsePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PulsePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.button_navigate_pulse = wx.BitmapButton(
            self, wx.ID_ANY, icons8_laser_beam_52.GetBitmap()
        )
        self.spin_pulse_duration = wx.SpinCtrl(self, wx.ID_ANY, "50", min=1, max=1000)
        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_pulse, self.button_navigate_pulse
        )
        self.Bind(
            wx.EVT_SPINCTRL, self.on_spin_pulse_duration, self.spin_pulse_duration
        )
        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_spin_pulse_duration, self.spin_pulse_duration
        )
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: PulsePanel.__set_properties
        self.button_navigate_pulse.SetToolTip(_("Fire a short laser pulse"))
        self.button_navigate_pulse.SetSize(self.button_navigate_pulse.GetBestSize())
        self.spin_pulse_duration.SetMinSize((80, 23))
        self.spin_pulse_duration.SetToolTip(_("Set the duration of the laser pulse"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: PulsePanel.__do_layout
        sizer_5 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Short Pulse")), wx.HORIZONTAL
        )
        sizer_5.Add(self.button_navigate_pulse, 0, 0, 0)
        sizer_5.Add(self.spin_pulse_duration, 0, 0, 0)
        label_4 = wx.StaticText(self, wx.ID_ANY, _(" ms"))
        sizer_5.Add(label_4, 0, 0, 0)
        self.SetSizer(sizer_5)
        sizer_5.Fit(self)
        self.Layout()
        # end wxGlade

    def on_button_navigate_pulse(
        self, event=None
    ):  # wxGlade: Navigation.<event_handler>
        value = self.spin_pulse_duration.GetValue()
        self.context("pulse %f\n" % value)

    def on_spin_pulse_duration(self, event=None):  # wxGlade: Navigation.<event_handler>
        self.context.navigate_pulse = float(self.spin_pulse_duration.GetValue())
