import wx

from icons import *

_ = wx.GetTranslation


class Adjustments(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: Adjustments.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((424, 417))
        self.check_speed_override = wx.CheckBox(self, wx.ID_ANY, "")
        self.slider_speed_override = wx.Slider(self, wx.ID_ANY, 100, 0, 500,
                                               style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.check_power_override = wx.CheckBox(self, wx.ID_ANY, "")
        self.slider_power_override = wx.Slider(self, wx.ID_ANY, 1000, 0, 1000,
                                               style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.check_overscan_override = wx.CheckBox(self, wx.ID_ANY, "")
        self.slider_overscan_override = wx.Slider(self, wx.ID_ANY, 0, 0, 2000,
                                                  style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.check_speed_ratio = wx.CheckBox(self, wx.ID_ANY, "")
        self.slider_speed_ratio = wx.Slider(self, wx.ID_ANY, 100, 0, 500,
                                            style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.check_power_ratio = wx.CheckBox(self, wx.ID_ANY, "")
        self.slider_power_ratio = wx.Slider(self, wx.ID_ANY, 100, 0, 200,
                                            style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.checkbox_pattern_group = wx.CheckBox(self, wx.ID_ANY, _("Group Pulses"))
        self.button_up = wx.BitmapButton(self, wx.ID_ANY, icons8up.GetBitmap())
        self.button_left = wx.BitmapButton(self, wx.ID_ANY, icons8_left.GetBitmap())
        self.button_origin = wx.BitmapButton(self, wx.ID_ANY, icons8_center_of_gravity_50.GetBitmap())
        self.button_right = wx.BitmapButton(self, wx.ID_ANY, icons8_right.GetBitmap())
        self.button_down = wx.BitmapButton(self, wx.ID_ANY, icons8_down.GetBitmap())
        self.bitmap_flush_buffer = wx.BitmapButton(self, wx.ID_ANY, icons8_goal_50.GetBitmap())
        self.bitmap_cancel = wx.BitmapButton(self, wx.ID_ANY, icons8_delete_50.GetBitmap())
        self.bitmap_stop = wx.BitmapButton(self, wx.ID_ANY, icons8_stop_sign_50.GetBitmap())
        self.text_status_information = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_MULTILINE)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CHECKBOX, lambda e: self.slider_speed_override.Enable(self.check_speed_override.GetValue()),
                  self.check_speed_override)
        self.Bind(wx.EVT_SLIDER, self.on_slider_speed_override, self.slider_speed_override)
        self.Bind(wx.EVT_CHECKBOX, lambda e: self.slider_power_override.Enable(self.check_power_override.GetValue()),
                  self.check_power_override)
        self.Bind(wx.EVT_SLIDER, self.on_slider_power_override, self.slider_power_override)
        self.Bind(wx.EVT_CHECKBOX,
                  lambda e: self.slider_overscan_override.Enable(self.check_overscan_override.GetValue()),
                  self.check_overscan_override)
        self.Bind(wx.EVT_SLIDER, self.on_slider_overscan_override, self.slider_overscan_override)
        self.Bind(wx.EVT_CHECKBOX, lambda e: self.slider_speed_ratio.Enable(self.check_speed_ratio.GetValue()),
                  self.check_speed_ratio)
        self.Bind(wx.EVT_SLIDER, self.on_slider_speed_ratio, self.slider_speed_ratio)
        self.Bind(wx.EVT_CHECKBOX, lambda e: self.slider_power_ratio.Enable(self.check_power_ratio.GetValue()),
                  self.check_power_ratio)
        self.Bind(wx.EVT_SLIDER, self.on_slider_power_ratio, self.slider_power_ratio)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_pattern_group, self.checkbox_pattern_group)
        self.Bind(wx.EVT_BUTTON, self.on_button_adjust_top, self.button_up)
        self.Bind(wx.EVT_BUTTON, self.on_button_adjust_left, self.button_left)
        self.Bind(wx.EVT_BUTTON, self.on_button_adjust_origin, self.button_origin)
        self.Bind(wx.EVT_BUTTON, self.on_button_adjust_right, self.button_right)
        self.Bind(wx.EVT_BUTTON, self.on_button_adjust_bottom, self.button_down)
        self.Bind(wx.EVT_BUTTON, self.on_button_flush_buffer, self.bitmap_flush_buffer)
        self.Bind(wx.EVT_BUTTON, self.on_button_safe_quit, self.bitmap_cancel)
        self.Bind(wx.EVT_BUTTON, self.on_button_emergency_exit, self.bitmap_stop)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_press)
        self.SetFocus()
        # end wxGlade
        self.kernel = None
        self.device = None

    def __set_properties(self):
        # begin wxGlade: Adjustments.__set_properties
        self.SetTitle(_("Adjustments"))
        self.slider_speed_override.SetToolTip(_("Override the Speed setting. Use this instead."))
        self.slider_speed_override.Enable(False)
        self.slider_power_override.SetToolTip(_("Override the Power setting. Use this instead."))
        self.slider_power_override.Enable(False)
        self.slider_overscan_override.SetToolTip(_("Override the Overscan setting. Use this instead."))
        self.slider_overscan_override.Enable(False)
        self.slider_speed_ratio.SetToolTip(_("Scale the desired speed settings by this percent."))
        self.slider_speed_ratio.Enable(False)
        self.slider_power_ratio.SetToolTip(_("Scale the Power settings by this Percent. (Crimps to [0,1000])"))
        self.slider_power_ratio.Enable(False)
        self.checkbox_pattern_group.SetToolTip(_("Attempts to adjust the pulse grouping for data efficiency."))
        self.button_up.SetMinSize((58, 58))
        self.button_up.SetToolTip(_("Move writer position towards top."))
        self.button_left.SetMinSize((58, 58))
        self.button_left.SetToolTip(_("Move writer position towards left."))
        self.button_origin.SetToolTip(_("Set writer position as origin (0,0)"))
        self.button_origin.SetSize(self.button_origin.GetBestSize())
        self.button_right.SetMinSize((58, 58))
        self.button_right.SetToolTip(_("Move writer position towards right."))
        self.button_down.SetMinSize((58, 58))
        self.button_down.SetToolTip(_("Move writer position towards bottom."))
        self.bitmap_flush_buffer.SetMinSize((58, 58))
        self.bitmap_flush_buffer.SetToolTip(_("Flush buffers to empty."))
        self.bitmap_cancel.SetToolTip(_("Safely exit current job, purge the spooler."))
        self.bitmap_cancel.SetSize(self.bitmap_cancel.GetBestSize())
        self.bitmap_stop.SetMinSize((58, 58))
        self.bitmap_stop.SetToolTip(_("Emergency Stop. Kill all buffers stop at this location."))
        self.text_status_information.SetToolTip(_("Status Information"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Adjustments.__do_layout
        sizer_7 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        grid_sizer_1 = wx.FlexGridSizer(4, 3, 0, 0)
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_6 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Power Ratio")), wx.HORIZONTAL)
        sizer_5 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Speed Ratio")), wx.HORIZONTAL)
        sizer_4 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Overscan Override")), wx.HORIZONTAL)
        sizer_3 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Power Override")), wx.HORIZONTAL)
        sizer_2 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Speed Override")), wx.HORIZONTAL)
        sizer_2.Add(self.check_speed_override, 0, 0, 0)
        sizer_2.Add(self.slider_speed_override, 1, wx.EXPAND, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        sizer_3.Add(self.check_power_override, 0, 0, 0)
        sizer_3.Add(self.slider_power_override, 1, wx.EXPAND, 0)
        sizer_1.Add(sizer_3, 1, wx.EXPAND, 0)
        sizer_4.Add(self.check_overscan_override, 0, 0, 0)
        sizer_4.Add(self.slider_overscan_override, 1, wx.EXPAND, 0)
        sizer_1.Add(sizer_4, 1, wx.EXPAND, 0)
        sizer_5.Add(self.check_speed_ratio, 0, 0, 0)
        sizer_5.Add(self.slider_speed_ratio, 1, wx.EXPAND, 0)
        sizer_1.Add(sizer_5, 1, wx.EXPAND, 0)
        sizer_6.Add(self.check_power_ratio, 0, 0, 0)
        sizer_6.Add(self.slider_power_ratio, 1, wx.EXPAND, 0)
        sizer_1.Add(sizer_6, 1, wx.EXPAND, 0)
        sizer_1.Add(self.checkbox_pattern_group, 0, 0, 0)
        sizer_7.Add(sizer_1, 1, 0, 0)
        grid_sizer_1.Add((58, 58), 0, 0, 0)
        grid_sizer_1.Add(self.button_up, 0, 0, 0)
        grid_sizer_1.Add((58, 58), 0, 0, 0)
        grid_sizer_1.Add(self.button_left, 0, 0, 0)
        grid_sizer_1.Add(self.button_origin, 0, 0, 0)
        grid_sizer_1.Add(self.button_right, 0, 0, 0)
        grid_sizer_1.Add((58, 58), 0, 0, 0)
        grid_sizer_1.Add(self.button_down, 0, 0, 0)
        grid_sizer_1.Add((58, 58), 0, 0, 0)
        grid_sizer_1.Add(self.bitmap_flush_buffer, 0, 0, 0)
        grid_sizer_1.Add(self.bitmap_cancel, 0, 0, 0)
        grid_sizer_1.Add(self.bitmap_stop, 0, 0, 0)
        sizer_8.Add(grid_sizer_1, 0, wx.EXPAND, 0)
        sizer_8.Add(self.text_status_information, 1, wx.EXPAND, 0)
        sizer_7.Add(sizer_8, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_7)
        self.Layout()
        # end wxGlade
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def on_close(self, event):
        self.kernel.mark_window_closed("Adjustments")
        event.Skip()  # Call destroy as regular.
        if self.device is not None:
            self.device.execute("Realtime Resume")

    def set_kernel(self, kernel):
        self.kernel = kernel
        self.device = kernel.device
        if self.device is None:
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    value.Enable(False)
            dlg = wx.MessageDialog(None, _("You do not have a selected device."),
                                   _("No Device Selected."), wx.OK | wx.ICON_WARNING)
            result = dlg.ShowModal()
            dlg.Destroy()
            return
        self.device.execute("Realtime Pause")

    def on_slider_speed_override(self, event):  # wxGlade: Adjustments.<event_handler>
        print("Event handler 'on_slider_speed_override' not implemented!")
        event.Skip()

    def on_slider_power_override(self, event):  # wxGlade: Adjustments.<event_handler>
        print("Event handler 'on_slider_power_override' not implemented!")
        event.Skip()

    def on_slider_overscan_override(self, event):  # wxGlade: Adjustments.<event_handler>
        print("Event handler 'on_slider_overscan_override' not implemented!")
        event.Skip()

    def on_slider_speed_ratio(self, event):  # wxGlade: Adjustments.<event_handler>
        print("Event handler 'on_slider_speed_ratio' not implemented!")
        event.Skip()

    def on_slider_power_ratio(self, event):  # wxGlade: Adjustments.<event_handler>
        print("Event handler 'on_slider_power_ratio' not implemented!")
        event.Skip()

    def on_check_pattern_group(self, event):  # wxGlade: Adjustments.<event_handler>
        print("Event handler 'on_check_pattern_group' not implemented!")
        event.Skip()

    def on_button_adjust_top(self, event):  # wxGlade: Adjustments.<event_handler>
        print("Event handler 'on_button_adjust_top' not implemented!")
        event.Skip()

    def on_button_adjust_left(self, event):  # wxGlade: Adjustments.<event_handler>
        print("Event handler 'on_button_adjust_left' not implemented!")
        event.Skip()

    def on_button_adjust_origin(self, event):  # wxGlade: Adjustments.<event_handler>
        print("Event handler 'on_button_adjust_origin' not implemented!")
        event.Skip()

    def on_button_adjust_right(self, event):  # wxGlade: Adjustments.<event_handler>
        print("Event handler 'on_button_adjust_right' not implemented!")
        event.Skip()

    def on_button_adjust_bottom(self, event):  # wxGlade: Adjustments.<event_handler>
        print("Event handler 'on_button_adjust_bottom' not implemented!")
        event.Skip()

    def on_button_flush_buffer(self, event):  # wxGlade: Adjustments.<event_handler>
        print("Event handler 'on_button_flush_buffer' not implemented!")
        event.Skip()

    def on_button_safe_quit(self, event):  # wxGlade: Adjustments.<event_handler>
        print("Event handler 'on_button_safe_quit' not implemented!")
        event.Skip()

    def on_button_emergency_exit(self, event):  # wxGlade: Adjustments.<event_handler>
        print("Event handler 'on_button_emergency_exit' not implemented!")
        event.Skip()

    def on_key_press(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            self.Close()
        event.Skip()