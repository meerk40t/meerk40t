from LaserProject import *


class ElementProperty(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: ElementProperty.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((292, 269))
        self.text_name = wx.TextCtrl(self, wx.ID_ANY, "")
        self.spin_speed_set = wx.SpinCtrlDouble(self, wx.ID_ANY, "20.0", min=0.0, max=240.0)
        self.checkbox_custom_d_ratio = wx.CheckBox(self, wx.ID_ANY, "Custom D-Ratio")
        self.spin_speed_dratio = wx.SpinCtrlDouble(self, wx.ID_ANY, "0.261", min=0.0, max=1.0)
        self.spin_passes = wx.SpinCtrl(self, wx.ID_ANY, "1", min=0, max=63)
        self.spin_step_size = wx.SpinCtrl(self, wx.ID_ANY, "1", min=0, max=63)
        self.combo_raster_direction = wx.ComboBox(self, wx.ID_ANY,
                                                  choices=["Top To Bottom", "Bottom To Top"],
                                                  style=wx.CB_DROPDOWN)
        self.button_F00 = wx.Button(self, wx.ID_ANY, "")
        self.button_0F0 = wx.Button(self, wx.ID_ANY, "")
        self.button_00F = wx.Button(self, wx.ID_ANY, "")
        self.button_F0F = wx.Button(self, wx.ID_ANY, "")
        self.button_0FF = wx.Button(self, wx.ID_ANY, "")
        self.button_FF0 = wx.Button(self, wx.ID_ANY, "")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_COMBOBOX, self.on_combobox_rasterdirection, self.combo_raster_direction)
        self.Bind(wx.EVT_TEXT, self.on_text_name_change, self.text_name)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_name_change, self.text_name)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_speed, self.spin_speed_set)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_speed, self.spin_speed_set)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_speed_dratio, self.spin_speed_dratio)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_speed_dratio, self.spin_speed_dratio)
        self.Bind(wx.EVT_SPINCTRL, self.on_spin_passes, self.spin_passes)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_passes, self.spin_passes)
        self.Bind(wx.EVT_SPINCTRL, self.on_spin_step, self.spin_step_size)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_step, self.spin_step_size)
        self.Bind(wx.EVT_BUTTON, self.on_button_f00, self.button_F00)
        self.Bind(wx.EVT_BUTTON, self.on_button_0f0, self.button_0F0)
        self.Bind(wx.EVT_BUTTON, self.on_button_00f, self.button_00F)
        self.Bind(wx.EVT_BUTTON, self.on_button_f0f, self.button_F0F)
        self.Bind(wx.EVT_BUTTON, self.on_button_0ff, self.button_0FF)
        self.Bind(wx.EVT_BUTTON, self.on_button_ff0, self.button_FF0)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_speed_dratio, self.checkbox_custom_d_ratio)
        # end wxGlade
        self.element = None

    def set_element(self, element):
        self.element = element
        self.text_name.SetValue(str(element))
        if isinstance(element, list):
            pass
        else:
            cut = element.cut
            if VARIABLE_NAME_SPEED in cut:
                self.spin_speed_set.SetValue(cut[VARIABLE_NAME_SPEED])
            if VARIABLE_NAME_DRATIO in cut:
                self.spin_speed_dratio.SetValue(cut[VARIABLE_NAME_DRATIO])
            if VARIABLE_NAME_PASSES in cut:
                self.spin_passes.SetValue(cut[VARIABLE_NAME_PASSES])
            if VARIABLE_NAME_RASTER_STEP in cut:
                self.spin_step_size.SetValue(cut[VARIABLE_NAME_RASTER_STEP])
            if VARIABLE_NAME_RASTER_DIRECTION in cut:
                self.combo_raster_direction.SetSelection(cut[VARIABLE_NAME_RASTER_DIRECTION])

    def __set_properties(self):
        # begin wxGlade: ElementProperty.__set_properties
        self.SetTitle("Element Properties")
        self.spin_speed_set.SetMinSize((100, 23))
        self.spin_speed_set.SetIncrement(1.0)
        self.spin_speed_dratio.SetMinSize((100, 23))
        self.spin_speed_dratio.SetIncrement(0.001)
        self.spin_speed_dratio.Enable(False)
        self.spin_passes.SetMinSize((100, 23))
        self.spin_step_size.SetMinSize((100, 23))
        self.combo_raster_direction.SetSelection(0)
        self.button_F00.SetBackgroundColour(wx.Colour(255, 0, 0))
        self.button_0F0.SetBackgroundColour(wx.Colour(0, 255, 0))
        self.button_00F.SetBackgroundColour(wx.Colour(0, 0, 255))
        self.button_F0F.SetBackgroundColour(wx.Colour(255, 0, 255))
        self.button_0FF.SetBackgroundColour(wx.Colour(0, 255, 255))
        self.button_FF0.SetBackgroundColour(wx.Colour(255, 255, 0))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ElementProperty.__do_layout
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_4 = wx.WrapSizer(wx.VERTICAL)
        grid_sizer_1 = wx.FlexGridSizer(5, 3, 10, 10)
        sizer_8.Add(self.text_name, 0, wx.EXPAND, 0)
        label_1 = wx.StaticText(self, wx.ID_ANY, "Speed")
        grid_sizer_1.Add(label_1, 0, 0, 0)
        grid_sizer_1.Add(self.spin_speed_set, 0, 0, 0)
        label_2 = wx.StaticText(self, wx.ID_ANY, "mm/s")
        grid_sizer_1.Add(label_2, 0, 0, 0)
        grid_sizer_1.Add(self.checkbox_custom_d_ratio, 0, 0, 0)
        grid_sizer_1.Add(self.spin_speed_dratio, 0, 0, 0)
        grid_sizer_1.Add((0, 0), 0, 0, 0)
        label_6 = wx.StaticText(self, wx.ID_ANY, "Passes")
        grid_sizer_1.Add(label_6, 0, 0, 0)
        grid_sizer_1.Add(self.spin_passes, 0, 0, 0)
        grid_sizer_1.Add((0, 0), 0, 0, 0)
        label_7 = wx.StaticText(self, wx.ID_ANY, "Raster Step")
        grid_sizer_1.Add(label_7, 0, 0, 0)
        grid_sizer_1.Add(self.spin_step_size, 0, 0, 0)
        label_4 = wx.StaticText(self, wx.ID_ANY, " mil")
        grid_sizer_1.Add(label_4, 0, 0, 0)
        label_5 = wx.StaticText(self, wx.ID_ANY, "Raster Direction")
        grid_sizer_1.Add(label_5, 0, 0, 0)
        grid_sizer_1.Add(self.combo_raster_direction, 0, 0, 0)
        grid_sizer_1.Add((0, 0), 0, 0, 0)
        sizer_8.Add(grid_sizer_1, 5, wx.EXPAND, 0)
        sizer_4.Add(self.button_F00, 0, wx.EXPAND, 0)
        sizer_4.Add(self.button_0F0, 0, wx.EXPAND, 0)
        sizer_4.Add(self.button_00F, 0, wx.EXPAND, 0)
        sizer_4.Add(self.button_F0F, 0, wx.EXPAND, 0)
        sizer_4.Add(self.button_0FF, 0, wx.EXPAND, 0)
        sizer_4.Add(self.button_FF0, 0, wx.EXPAND, 0)
        sizer_8.Add(sizer_4, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_8)
        self.Layout()
        self.Centre()
        # end wxGlade

    def flat_element(self, element):
        if not isinstance(element, list):
            yield element
        else:
            for e in element:
                for flat_e in self.flat_element(e):
                    yield flat_e

    def on_text_name_change(self, event):  # wxGlade: ElementProperty.<event_handler>
        for e in self.flat_element(self.element):
            e.cut[VARIABLE_NAME_NAME] = self.text_name.GetValue()

    def on_spin_speed(self, event):  # wxGlade: ElementProperty.<event_handler>
        for e in self.flat_element(self.element):
            e.cut[VARIABLE_NAME_SPEED] = self.spin_speed_set.GetValue()

    def on_check_speed_dratio(self, event):
        self.spin_speed_dratio.Enable(self.checkbox_custom_d_ratio.GetValue())

    def on_spin_speed_dratio(self, event):  # wxGlade: ElementProperty.<event_handler>
        for e in self.flat_element(self.element):
            e.cut[VARIABLE_NAME_DRATIO] = self.spin_speed_dratio.GetValue()

    def on_spin_passes(self, event):  # wxGlade: ElementProperty.<event_handler>
        for e in self.flat_element(self.element):
            e.cut[VARIABLE_NAME_PASSES] = self.spin_passes.GetValue()

    def on_spin_step(self, event):  # wxGlade: ElementProperty.<event_handler>
        for e in self.flat_element(self.element):
            e.cut[VARIABLE_NAME_RASTER_STEP] = self.spin_step_size.GetValue()

    def on_combobox_rasterdirection(self, event):  # wxGlade: Preferences.<event_handler>
        for e in self.flat_element(self.element):
            e.cut[VARIABLE_NAME_RASTER_DIRECTION] = self.combo_raster_direction.GetSelection()

    def on_button_f00(self, event):  # wxGlade: ElementProperty.<event_handler>
        for e in self.flat_element(self.element):
            e.cut[VARIABLE_NAME_COLOR] = 0xFF0000

    def on_button_0f0(self, event):  # wxGlade: ElementProperty.<event_handler>
        for e in self.flat_element(self.element):
            e.cut[VARIABLE_NAME_COLOR] = 0x00FF00

    def on_button_00f(self, event):  # wxGlade: ElementProperty.<event_handler>
        for e in self.flat_element(self.element):
            e.cut[VARIABLE_NAME_COLOR] = 0x0000FF

    def on_button_f0f(self, event):  # wxGlade: ElementProperty.<event_handler>
        for e in self.flat_element(self.element):
            e.cut[VARIABLE_NAME_COLOR] = 0xFF00FF

    def on_button_0ff(self, event):  # wxGlade: ElementProperty.<event_handler>
        for e in self.flat_element(self.element):
            e.cut[VARIABLE_NAME_COLOR] = 0x00FFFF

    def on_button_ff0(self, event):  # wxGlade: ElementProperty.<event_handler>
        for e in self.flat_element(self.element):
            e.cut[VARIABLE_NAME_COLOR] = 0xFFFF00

# end of class ElementProperty
