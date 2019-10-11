import wx

import LaserRender
from LaserProject import *


class ColorDefine(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: ColorDefine.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((740, 281))
        self.list_colors = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.spin_speed_set = wx.SpinCtrlDouble(self, wx.ID_ANY, "20.0", min=0.0, max=240.0)
        self.spin_power_set = wx.SpinCtrlDouble(self, wx.ID_ANY, "1000.0", min=0.0, max=1000.0)
        self.checkbox_custom_d_ratio = wx.CheckBox(self, wx.ID_ANY, "Custom D-Ratio")
        self.spin_speed_dratio = wx.SpinCtrlDouble(self, wx.ID_ANY, "0.261", min=0.0, max=1.0)
        self.spin_passes = wx.SpinCtrl(self, wx.ID_ANY, "1", min=0, max=63)
        self.spin_step_size = wx.SpinCtrl(self, wx.ID_ANY, "1", min=0, max=63)
        self.combo_raster_direction = wx.ComboBox(self, wx.ID_ANY, choices=["Top To Bottom", "Bottom To Top"], style=wx.CB_DROPDOWN)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_list_color_selected, self.list_colors)
        self.Bind(wx.EVT_COMBOBOX, self.on_combobox_rasterdirection, self.combo_raster_direction)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_speed, self.spin_speed_set)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_speed, self.spin_speed_set)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_power, self.spin_power_set)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_power, self.spin_power_set)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_speed_dratio, self.checkbox_custom_d_ratio)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_speed_dratio, self.spin_speed_dratio)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_speed_dratio, self.spin_speed_dratio)
        self.Bind(wx.EVT_SPINCTRL, self.on_spin_passes, self.spin_passes)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_passes, self.spin_passes)
        self.Bind(wx.EVT_SPINCTRL, self.on_spin_step, self.spin_step_size)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_step, self.spin_step_size)
        # end wxGlade
        self.project = None
        self.index = None

    def set_project(self, project):
        self.project = project
        self.refresh_list()
        self.load_color_data("Vector")

    def __set_properties(self):
        # begin wxGlade: ColorDefine.__set_properties
        self.SetTitle("ColorDefine")
        self.list_colors.AppendColumn("Color", format=wx.LIST_FORMAT_LEFT, width=75)
        self.list_colors.AppendColumn("Speed", format=wx.LIST_FORMAT_LEFT, width=70)
        self.list_colors.AppendColumn("Power", format=wx.LIST_FORMAT_LEFT, width=63)
        self.list_colors.AppendColumn("D-Ratio", format=wx.LIST_FORMAT_LEFT, width=58)
        self.list_colors.AppendColumn("Passes", format=wx.LIST_FORMAT_LEFT, width=46)
        self.list_colors.AppendColumn("Step", format=wx.LIST_FORMAT_LEFT, width=39)
        self.list_colors.AppendColumn("Direction", format=wx.LIST_FORMAT_LEFT, width=87)
        self.spin_speed_set.SetMinSize((100, 23))
        self.spin_speed_set.SetToolTip("Speed at which to perform the action in mm/s.")
        self.spin_power_set.SetMinSize((100, 23))
        self.spin_power_set.SetToolTip("1000 always on. 500 it's half power (fire every other step). This is software PPI control.")
        self.checkbox_custom_d_ratio.SetToolTip("Enables the ability to modify the diagonal ratio.")
        self.spin_speed_dratio.SetMinSize((100, 23))
        self.spin_speed_dratio.SetToolTip("Diagonal ratio is the ratio of additional time needed to perform a diagonal step rather than an orthogonal step.")
        self.spin_speed_dratio.Enable(False)
        self.spin_speed_dratio.SetIncrement(0.01)
        self.spin_passes.SetMinSize((100, 23))
        self.spin_passes.SetToolTip("How many times should this action be performed?")
        self.spin_step_size.SetMinSize((100, 23))
        self.spin_step_size.SetToolTip("Scan gap / step size, is the distance between scanlines in a raster engrave. Distance here is in 1/1000th of an inch.")
        self.combo_raster_direction.SetToolTip("Direction to perform a raster")
        self.combo_raster_direction.SetSelection(0)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ColorDefine.__do_layout
        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        grid_sizer_1 = wx.FlexGridSizer(6, 3, 10, 10)
        sizer_1.Add(self.list_colors, 0, wx.EXPAND, 0)
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
        sizer_1.Add(grid_sizer_1, 5, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def refresh_list(self):
        self.list_colors.DeleteAllItems()
        i = 0
        for key in self.project.properties:
            action = self.project.properties[key]
            if isinstance(key, int):
                v = "#{:02x}{:02x}{:02x}".format((key >> 16) & 0xFF, (key >> 8) & 0xFF, key & 0xFF)
                m = self.list_colors.InsertItem(i, v)
                self.list_colors.SetItemBackgroundColour(i, wx.Colour(LaserRender.swizzlecolor(key)))
            elif isinstance(key, str):
                m = self.list_colors.InsertItem(i, key)
            elif key is None:
                m = self.list_colors.InsertItem(i, "Default")
            else:
                m = self.list_colors.InsertItem(i, "Error")
            i += 1
            if VARIABLE_NAME_SPEED in action:
                self.list_colors.SetItem(m, 1, str(action[VARIABLE_NAME_SPEED]))
            if VARIABLE_NAME_POWER in action:
                self.list_colors.SetItem(m, 2, str(action[VARIABLE_NAME_POWER]))
            if VARIABLE_NAME_DRATIO in action:
                self.list_colors.SetItem(m, 3, str(action[VARIABLE_NAME_DRATIO]))
            if VARIABLE_NAME_PASSES in action:
                self.list_colors.SetItem(m, 4, str(action[VARIABLE_NAME_PASSES]))
            if VARIABLE_NAME_RASTER_STEP in action:
                self.list_colors.SetItem(m, 5, str(action[VARIABLE_NAME_RASTER_STEP]))
            if VARIABLE_NAME_RASTER_DIRECTION in action:
                self.list_colors.SetItem(m, 6, str(action[VARIABLE_NAME_RASTER_DIRECTION]))

    def load_color_data(self, index):
        properties = self.project.properties
        if index in properties:
            props = properties[index]
            default_props = properties[None]
            if VARIABLE_NAME_SPEED in props:
                self.spin_speed_set.SetValue(props[VARIABLE_NAME_SPEED])
            else:
                self.spin_speed_set.SetValue(default_props[VARIABLE_NAME_SPEED])
            if VARIABLE_NAME_POWER in props:
                self.spin_power_set.SetValue(props[VARIABLE_NAME_POWER])
            else:
                self.spin_power_set.SetValue(default_props[VARIABLE_NAME_POWER])
            if VARIABLE_NAME_DRATIO in props:
                self.spin_speed_dratio.SetValue(props[VARIABLE_NAME_DRATIO])
            else:
                self.spin_speed_dratio.SetValue(default_props[VARIABLE_NAME_DRATIO])
            if VARIABLE_NAME_PASSES in props:
                self.spin_passes.SetValue(props[VARIABLE_NAME_PASSES])
            else:
                self.spin_passes.SetValue(default_props[VARIABLE_NAME_PASSES])
            if VARIABLE_NAME_RASTER_STEP in props:
                self.spin_step_size.SetValue(props[VARIABLE_NAME_RASTER_STEP])
            else:
                self.spin_step_size.SetValue(default_props[VARIABLE_NAME_RASTER_STEP])
            if VARIABLE_NAME_RASTER_DIRECTION in props:
                self.combo_raster_direction.SetSelection(props[VARIABLE_NAME_RASTER_DIRECTION])
            else:
                self.combo_raster_direction.SetSelection(default_props[VARIABLE_NAME_RASTER_DIRECTION])

    def on_list_color_selected(self, event):  # wxGlade: ColorDefine.<event_handler>
        index = event.Index
        m = self.list_colors.GetItemText(index, 0)
        if isinstance(m, str):
            if '#' in m:
                m = svg_parser.parse_svg_color(m)
            elif 'Default' == m:
                m = None
        self.index = m
        self.load_color_data(m)

    def on_spin_speed(self, event):  # wxGlade: ElementProperty.<event_handler>
        self.project.properties[self.index][VARIABLE_NAME_SPEED] = self.spin_speed_set.GetValue()
        self.refresh_list()

    def on_spin_power(self, event):
        self.project.properties[self.index][VARIABLE_NAME_POWER] = self.spin_power_set.GetValue()
        self.refresh_list()

    def on_check_speed_dratio(self, event):
        self.spin_speed_dratio.Enable(self.checkbox_custom_d_ratio.GetValue())

    def on_spin_speed_dratio(self, event):  # wxGlade: ElementProperty.<event_handler>
        self.project.properties[self.index][VARIABLE_NAME_DRATIO] = self.spin_speed_dratio.GetValue()
        self.refresh_list()

    def on_spin_passes(self, event):  # wxGlade: ElementProperty.<event_handler>
        self.project.properties[self.index][VARIABLE_NAME_PASSES] = self.spin_passes.GetValue()
        self.refresh_list()

    def on_spin_step(self, event):  # wxGlade: ElementProperty.<event_handler>
        self.project.properties[self.index][VARIABLE_NAME_RASTER_STEP] = self.spin_step_size.GetValue()
        self.refresh_list()

    def on_combobox_rasterdirection(self, event):  # wxGlade: Preferences.<event_handler>
        self.project.properties[self.index][VARIABLE_NAME_RASTER_DIRECTION] = self.combo_raster_direction.GetSelection()
        self.refresh_list()
