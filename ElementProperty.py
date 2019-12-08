import wx

from LaserProject import *
from LaserRender import swizzlecolor


class ElementProperty(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: ElementProperty.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((290, 312))
        self.text_name = wx.TextCtrl(self, wx.ID_ANY, "")
        self.spin_speed_set = wx.SpinCtrlDouble(self, wx.ID_ANY, "20.0", min=0.0, max=240.0)
        self.spin_power_set = wx.SpinCtrlDouble(self, wx.ID_ANY, "1000.0", min=0.0, max=1000.0)
        self.checkbox_custom_d_ratio = wx.CheckBox(self, wx.ID_ANY, "Custom D-Ratio")
        self.spin_speed_dratio = wx.SpinCtrlDouble(self, wx.ID_ANY, "0.261", min=0.0, max=1.0)
        self.spin_passes = wx.SpinCtrl(self, wx.ID_ANY, "1", min=0, max=63)
        self.spin_step_size = wx.SpinCtrl(self, wx.ID_ANY, "1", min=0, max=63)
        self.combo_raster_direction = wx.ComboBox(self, wx.ID_ANY, choices=["Top To Bottom", "Bottom To Top"],
                                                  style=wx.CB_DROPDOWN)
        self.button_F00 = wx.Button(self, wx.ID_ANY, "")
        self.button_0F0 = wx.Button(self, wx.ID_ANY, "")
        self.button_00F = wx.Button(self, wx.ID_ANY, "")
        self.button_F0F = wx.Button(self, wx.ID_ANY, "")
        self.button_0FF = wx.Button(self, wx.ID_ANY, "")
        self.button_FF0 = wx.Button(self, wx.ID_ANY, "")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_power, self.spin_power_set)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_power, self.spin_power_set)
        self.Bind(wx.EVT_COMBOBOX, self.on_combobox_rasterdirection, self.combo_raster_direction)
        # self.Bind(wx.EVT_TEXT, self.on_text_name_change, self.text_name)
        # self.Bind(wx.EVT_TEXT_ENTER, self.on_text_name_change, self.text_name)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_speed, self.spin_speed_set)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_speed, self.spin_speed_set)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_speed_dratio, self.spin_speed_dratio)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_speed_dratio, self.spin_speed_dratio)
        self.Bind(wx.EVT_SPINCTRL, self.on_spin_passes, self.spin_passes)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_passes, self.spin_passes)
        self.Bind(wx.EVT_SPINCTRL, self.on_spin_step, self.spin_step_size)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_step, self.spin_step_size)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_F00)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_0F0)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_00F)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_F0F)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_0FF)
        self.Bind(wx.EVT_BUTTON, self.on_button_color, self.button_FF0)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_speed_dratio, self.checkbox_custom_d_ratio)
        # end wxGlade
        self.project = None
        self.element = None

    def set_project_element(self, project, element):
        self.project = project
        self.element = element
        self.text_name.SetValue(str(element))
        props = element.properties
        if VARIABLE_NAME_SPEED in props:
            self.spin_speed_set.SetValue(props[VARIABLE_NAME_SPEED])
        if VARIABLE_NAME_POWER in props:
            self.spin_power_set.SetValue(props[VARIABLE_NAME_POWER])
        if VARIABLE_NAME_DRATIO in props:
            self.spin_speed_dratio.SetValue(props[VARIABLE_NAME_DRATIO])
        if VARIABLE_NAME_PASSES in props:
            self.spin_passes.SetValue(props[VARIABLE_NAME_PASSES])
        if VARIABLE_NAME_RASTER_STEP in props:
            self.spin_step_size.SetValue(props[VARIABLE_NAME_RASTER_STEP])
        if VARIABLE_NAME_RASTER_DIRECTION in props:
            self.combo_raster_direction.SetSelection(props[VARIABLE_NAME_RASTER_DIRECTION])
        if VARIABLE_NAME_COLOR in props:
            color = wx.Colour(swizzlecolor(props[VARIABLE_NAME_COLOR]))
            self.text_name.SetBackgroundColour(color)

    def __set_properties(self):
        # begin wxGlade: ElementProperty.__set_properties
        self.SetTitle("Element Properties")
        self.spin_speed_set.SetMinSize((100, 23))
        self.spin_speed_set.SetToolTip("Speed at which to perform the action in mm/s.")
        self.spin_power_set.SetMinSize((100, 23))
        self.spin_power_set.SetToolTip(
            "1000 always on. 500 it's half power (fire every other step). This is software PPI control.")
        self.checkbox_custom_d_ratio.SetToolTip("Enables the ability to modify the diagonal ratio.")
        self.spin_speed_dratio.SetMinSize((100, 23))
        self.spin_speed_dratio.SetToolTip(
            "Diagonal ratio is the ratio of additional time needed to perform a diagonal step rather than an orthogonal step.")
        self.spin_speed_dratio.Enable(False)
        self.spin_speed_dratio.SetIncrement(0.01)
        self.spin_passes.SetMinSize((100, 23))
        self.spin_passes.SetToolTip("How many times should this action be performed?")
        self.spin_step_size.SetMinSize((100, 23))
        self.spin_step_size.SetToolTip(
            "Scan gap / step size, is the distance between scanlines in a raster engrave. Distance here is in 1/1000th of an inch.")
        self.combo_raster_direction.SetToolTip("Direction to perform a raster")
        self.combo_raster_direction.SetSelection(0)
        self.button_F00.SetBackgroundColour(wx.Colour(255, 0, 0))
        self.button_F00.SetToolTip("#FF0000 defined values.")
        self.button_0F0.SetBackgroundColour(wx.Colour(0, 255, 0))
        self.button_0F0.SetToolTip("#00FF00 defined values.")
        self.button_00F.SetBackgroundColour(wx.Colour(0, 0, 255))
        self.button_00F.SetToolTip("#00FF00 defined values.")
        self.button_F0F.SetBackgroundColour(wx.Colour(255, 0, 255))
        self.button_F0F.SetToolTip("#FF00FF defined values.")
        self.button_0FF.SetBackgroundColour(wx.Colour(0, 255, 255))
        self.button_0FF.SetToolTip("#00FFFF defined values.")
        self.button_FF0.SetBackgroundColour(wx.Colour(255, 255, 0))
        self.button_FF0.SetToolTip("#FFFF00 defined values.")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ElementProperty.__do_layout
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_4 = wx.WrapSizer(wx.VERTICAL)
        grid_sizer_1 = wx.FlexGridSizer(6, 3, 10, 10)
        sizer_8.Add(self.text_name, 0, wx.EXPAND, 0)
        label_1 = wx.StaticText(self, wx.ID_ANY, "Speed")
        grid_sizer_1.Add(label_1, 0, 0, 0)
        grid_sizer_1.Add(self.spin_speed_set, 0, 0, 0)
        label_2 = wx.StaticText(self, wx.ID_ANY, "mm/s")
        grid_sizer_1.Add(label_2, 0, 0, 0)
        label_3 = wx.StaticText(self, wx.ID_ANY, "Power")
        grid_sizer_1.Add(label_3, 0, 0, 0)
        grid_sizer_1.Add(self.spin_power_set, 0, 0, 0)
        label_8 = wx.StaticText(self, wx.ID_ANY, "ppi")
        grid_sizer_1.Add(label_8, 0, 0, 0)
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

    def on_text_name_change(self, event):  # wxGlade: ElementProperty.<event_handler>
        self.element.properties[VARIABLE_NAME_NAME] = self.text_name.GetValue()
        if self.project is not None:
            self.project("elements", 0)

    def on_spin_speed(self, event):  # wxGlade: ElementProperty.<event_handler>
        for e in self.element.flat_elements():
            e.properties[VARIABLE_NAME_SPEED] = self.spin_speed_set.GetValue()
        if self.project is not None:
            self.project("elements", 0)

    def on_spin_power(self, event):
        for e in self.element.flat_elements():
            e.properties[VARIABLE_NAME_POWER] = self.spin_power_set.GetValue()

    def on_check_speed_dratio(self, event):
        self.spin_speed_dratio.Enable(self.checkbox_custom_d_ratio.GetValue())

    def on_spin_speed_dratio(self, event):  # wxGlade: ElementProperty.<event_handler>
        for e in self.element.flat_elements():
            e.properties[VARIABLE_NAME_DRATIO] = self.spin_speed_dratio.GetValue()

    def on_spin_passes(self, event):  # wxGlade: ElementProperty.<event_handler>
        self.element.properties[VARIABLE_NAME_PASSES] = self.spin_passes.GetValue()
        if self.project is not None:
            self.project("elements", 0)

    def on_spin_step(self, event):  # wxGlade: ElementProperty.<event_handler>
        for e in self.element.flat_elements():
            e.properties[VARIABLE_NAME_RASTER_STEP] = self.spin_step_size.GetValue()
            self.project.validate_matrix(e)
        if self.project is not None:
            self.project("elements", 0)

    def on_combobox_rasterdirection(self, event):  # wxGlade: Preferences.<event_handler>
        for e in self.element.flat_elements():
            e.properties[VARIABLE_NAME_RASTER_DIRECTION] = self.combo_raster_direction.GetSelection()

    def on_button_color(self, event):  # wxGlade: ElementProperty.<event_handler>
        button = event.EventObject
        self.text_name.SetBackgroundColour(button.GetBackgroundColour())
        self.text_name.Refresh()
        color = swizzlecolor(button.GetBackgroundColour().GetRGB())

        for e in self.element.flat_elements():
            e.set_color(color)
        if self.project is not None:
            self.project("elements", 0)

# end of class ElementProperty
