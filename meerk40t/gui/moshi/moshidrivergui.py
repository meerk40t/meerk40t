# -*- coding: ISO-8859-1 -*-

import wx

from meerk40t.gui.icons import icons8_administrative_tools_50
from meerk40t.gui.mwindow import MWindow

_ = wx.GetTranslation


class MoshiConfigurationPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        self.checkbox_home_right = wx.CheckBox(self, wx.ID_ANY, _("Home Right"))
        self.checkbox_home_bottom = wx.CheckBox(self, wx.ID_ANY, _("Home Bottom"))
        self.spin_home_x = wx.SpinCtrlDouble(
            self, wx.ID_ANY, "0.0", min=-50000.0, max=50000.0
        )
        self.spin_home_y = wx.SpinCtrlDouble(
            self, wx.ID_ANY, "0.0", min=-50000.0, max=50000.0
        )
        self.button_home_by_current = wx.Button(self, wx.ID_ANY, _("Set Current"))
        self.checkbox_random_ppi = wx.CheckBox(self, wx.ID_ANY, _("Randomize PPI"))

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_home_right, self.checkbox_home_right)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_home_bottom, self.checkbox_home_bottom)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.spin_on_home_x, self.spin_home_x)
        self.Bind(wx.EVT_TEXT_ENTER, self.spin_on_home_x, self.spin_home_x)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.spin_on_home_y, self.spin_home_y)
        self.Bind(wx.EVT_TEXT_ENTER, self.spin_on_home_y, self.spin_home_y)
        self.Bind(
            wx.EVT_BUTTON, self.on_button_set_home_current, self.button_home_by_current
        )
        self.Bind(wx.EVT_CHECKBOX, self.on_check_random_ppi, self.checkbox_random_ppi)
        # end wxGlade

    def __set_properties(self):
        self.checkbox_home_right.SetToolTip(
            _("Indicates the device Home is on the right")
        )
        self.checkbox_home_bottom.SetToolTip(
            _("Indicates the device Home is on the bottom")
        )
        self.spin_home_x.SetMinSize((80, 23))
        self.spin_home_x.SetToolTip(_("Translate Home X"))
        self.spin_home_y.SetMinSize((80, 23))
        self.spin_home_y.SetToolTip(_("Translate Home Y"))
        self.button_home_by_current.SetToolTip(
            _("Set Home Position based on the current position")
        )
        self.checkbox_random_ppi.SetToolTip(
            _("Rather than orderly PPI, we perform PPI based on a randomized average")
        )
        self.checkbox_random_ppi.Enable(False)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MoshiDriverGui.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_6 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Pulse Planner")), wx.HORIZONTAL
        )
        sizer_home = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Shift Home Position")), wx.HORIZONTAL
        )
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_config = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Configuration")), wx.HORIZONTAL
        )
        sizer_config.Add(self.checkbox_home_right, 0, 0, 0)
        sizer_config.Add(self.checkbox_home_bottom, 0, 0, 0)
        sizer_main.Add(sizer_config, 1, wx.EXPAND, 0)
        label_9 = wx.StaticText(self, wx.ID_ANY, "X")
        sizer_4.Add(label_9, 0, 0, 0)
        sizer_4.Add(self.spin_home_x, 0, 0, 0)
        label_12 = wx.StaticText(self, wx.ID_ANY, _("mil"))
        sizer_4.Add(label_12, 0, 0, 0)
        sizer_home.Add(sizer_4, 2, wx.EXPAND, 0)
        label_10 = wx.StaticText(self, wx.ID_ANY, "Y")
        sizer_2.Add(label_10, 0, 0, 0)
        sizer_2.Add(self.spin_home_y, 0, 0, 0)
        label_11 = wx.StaticText(self, wx.ID_ANY, _("mil"))
        sizer_2.Add(label_11, 1, 0, 0)
        sizer_home.Add(sizer_2, 2, wx.EXPAND, 0)
        sizer_home.Add(self.button_home_by_current, 1, 0, 0)
        sizer_main.Add(sizer_home, 1, wx.EXPAND, 0)
        sizer_6.Add(self.checkbox_random_ppi, 0, 0, 0)
        sizer_main.Add(sizer_6, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        self.Layout()
        # end wxGlade

    def initialize(self):
        # self.context.listen("pipe;buffer", self.on_buffer_update)
        self.context.listen("active", self.on_active_change)

    def finalize(self):
        # self.context.unlisten("pipe;buffer", self.on_buffer_update)
        self.context.unlisten("active", self.on_active_change)

    def on_active_change(self, origin, active):
        # self.Close()
        pass

    def on_check_home_right(self, event):  # wxGlade: MoshiDriverGui.<event_handler>
        print("Event handler 'on_check_home_right' not implemented!")
        event.Skip()

    def on_check_home_bottom(self, event):  # wxGlade: MoshiDriverGui.<event_handler>
        print("Event handler 'on_check_home_bottom' not implemented!")
        event.Skip()

    def spin_on_home_x(self, event):  # wxGlade: MoshiDriverGui.<event_handler>
        print("Event handler 'spin_on_home_x' not implemented!")
        event.Skip()

    def spin_on_home_y(self, event):  # wxGlade: MoshiDriverGui.<event_handler>
        print("Event handler 'spin_on_home_y' not implemented!")
        event.Skip()

    def on_button_set_home_current(
        self, event
    ):  # wxGlade: MoshiDriverGui.<event_handler>
        print("Event handler 'on_button_set_home_current' not implemented!")
        event.Skip()

    def on_check_random_ppi(self, event):  # wxGlade: MoshiDriverGui.<event_handler>
        print("Event handler 'on_check_random_ppi' not implemented!")
        event.Skip()


class MoshiDriverGui(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(335, 170, *args, **kwds)

        self.panel = MoshiConfigurationPanel(self, wx.ID_ANY, context=self.context)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Moshiboard-Configuration"))

    def window_open(self):
        self.panel.initialize()

    def window_close(self):
        self.panel.finalize()
