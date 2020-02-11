import wx

from LaserRender import swizzlecolor
from svgelements import *

_ = wx.GetTranslation


class ElementProperty(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: ElementProperty.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((330, 312))
        self.text_name = wx.TextCtrl(self, wx.ID_ANY, "")
        self.spin_speed_set = wx.SpinCtrlDouble(self, wx.ID_ANY, "20.0", min=0.0, max=500.0)
        self.spin_power_set = wx.SpinCtrlDouble(self, wx.ID_ANY, "1000.0", min=0.0, max=1000.0)
        self.checkbox_custom_d_ratio = wx.CheckBox(self, wx.ID_ANY, _("Custom D-Ratio"))
        self.spin_speed_dratio = wx.SpinCtrlDouble(self, wx.ID_ANY, "0.261", min=0.0, max=1.0)
        self.spin_passes = wx.SpinCtrl(self, wx.ID_ANY, "1", min=0, max=63)
        self.spin_step_size = wx.SpinCtrl(self, wx.ID_ANY, "1", min=0, max=63)
        self.combo_raster_direction = wx.ComboBox(self, wx.ID_ANY, choices=[_("Top To Bottom"), _("Bottom To Top")],
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
        self.Bind(wx.EVT_CHECKBOX, lambda e: self.spin_speed_dratio.Enable(self.checkbox_custom_d_ratio.GetValue()),
                  self.checkbox_custom_d_ratio)
        # end wxGlade
        self.kernel = None
        self.element = None
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def on_close(self, event):
        self.kernel.mark_window_closed("ElementProperty")
        event.Skip()  # Call destroy.

    def set_elements(self, operation):
        self.element = operation
        self.text_name.SetValue(str(operation))
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
            if operation.dratio is not None:
                self.spin_speed_dratio.SetValue(operation.dratio)
        except AttributeError:
            self.spin_speed_dratio.Enable(False)
            self.checkbox_custom_d_ratio.Enable(False)

        try:
            if operation.passes is not None:
                self.spin_passes.SetValue(operation.passes)
        except AttributeError:
            self.spin_passes.Enable(False)

        try:
            if operation.raster_step is not None:
                self.spin_step_size.SetValue(operation.raster_step)
        except AttributeError:
            self.spin_step_size.Enable(False)

        try:
            if operation.raster_direction is not None:
                self.combo_raster_direction.SetSelection(operation.raster_direction)
        except AttributeError:
            self.combo_raster_direction.Enable(False)

        try:
            if operation.stroke is not None and operation.stroke != "none":
                color = wx.Colour(swizzlecolor(operation.stroke))
                self.text_name.SetBackgroundColour(color)
        except AttributeError:
            pass

    def set_kernel(self, kernel):
        self.kernel = kernel

    def __set_properties(self):
        # begin wxGlade: ElementProperty.__set_properties
        self.SetTitle(_("Element Properties"))
        self.spin_speed_set.SetMinSize((100, 23))
        self.spin_speed_set.SetToolTip(_("Speed at which to perform the action in mm/s."))
        self.spin_power_set.SetMinSize((100, 23))
        self.spin_power_set.SetToolTip(
            _("1000 always on. 500 it's half power (fire every other step). This is software PPI control."))
        self.checkbox_custom_d_ratio.SetToolTip(_("Enables the ability to modify the diagonal ratio."))
        self.spin_speed_dratio.SetMinSize((100, 23))
        self.spin_speed_dratio.SetToolTip(
            _(
                "Diagonal ratio is the ratio of additional time needed to perform a diagonal step rather than an orthogonal step."))
        self.spin_speed_dratio.Enable(False)
        self.spin_speed_dratio.SetIncrement(0.01)
        self.spin_passes.SetMinSize((100, 23))
        self.spin_passes.SetToolTip(_("How many times should this action be performed?"))
        self.spin_step_size.SetMinSize((100, 23))
        self.spin_step_size.SetToolTip(
            _(
                "Scan gap / step size, is the distance between scanlines in a raster engrave. Distance here is in 1/1000th of an inch."))
        self.combo_raster_direction.SetToolTip(_("Direction to perform a raster"))
        self.combo_raster_direction.SetSelection(0)
        self.button_F00.SetBackgroundColour(wx.Colour(255, 0, 0))
        self.button_F00.SetToolTip(_("#FF0000 defined values."))
        self.button_0F0.SetBackgroundColour(wx.Colour(0, 255, 0))
        self.button_0F0.SetToolTip(_("#00FF00 defined values."))
        self.button_00F.SetBackgroundColour(wx.Colour(0, 0, 255))
        self.button_00F.SetToolTip(_("#00FF00 defined values."))
        self.button_F0F.SetBackgroundColour(wx.Colour(255, 0, 255))
        self.button_F0F.SetToolTip(_("#FF00FF defined values."))
        self.button_0FF.SetBackgroundColour(wx.Colour(0, 255, 255))
        self.button_0FF.SetToolTip(_("#00FFFF defined values."))
        self.button_FF0.SetBackgroundColour(wx.Colour(255, 255, 0))
        self.button_FF0.SetToolTip(_("#FFFF00 defined values."))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ElementProperty.__do_layout
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_4 = wx.WrapSizer(wx.VERTICAL)
        grid_sizer_1 = wx.FlexGridSizer(6, 3, 10, 10)
        sizer_8.Add(self.text_name, 0, wx.EXPAND, 0)
        label_1 = wx.StaticText(self, wx.ID_ANY, _("Speed"))
        grid_sizer_1.Add(label_1, 0, 0, 0)
        grid_sizer_1.Add(self.spin_speed_set, 0, 0, 0)
        label_2 = wx.StaticText(self, wx.ID_ANY, _("mm/s"))
        grid_sizer_1.Add(label_2, 0, 0, 0)
        label_3 = wx.StaticText(self, wx.ID_ANY, _("Power"))
        grid_sizer_1.Add(label_3, 0, 0, 0)
        grid_sizer_1.Add(self.spin_power_set, 0, 0, 0)
        label_8 = wx.StaticText(self, wx.ID_ANY, _("ppi"))
        grid_sizer_1.Add(label_8, 0, 0, 0)
        grid_sizer_1.Add(self.checkbox_custom_d_ratio, 0, 0, 0)
        grid_sizer_1.Add(self.spin_speed_dratio, 0, 0, 0)
        grid_sizer_1.Add((0, 0), 0, 0, 0)
        label_6 = wx.StaticText(self, wx.ID_ANY, _("Passes"))
        grid_sizer_1.Add(label_6, 0, 0, 0)
        grid_sizer_1.Add(self.spin_passes, 0, 0, 0)
        grid_sizer_1.Add((0, 0), 0, 0, 0)
        label_7 = wx.StaticText(self, wx.ID_ANY, _("Raster Step"))
        grid_sizer_1.Add(label_7, 0, 0, 0)
        grid_sizer_1.Add(self.spin_step_size, 0, 0, 0)
        label_4 = wx.StaticText(self, wx.ID_ANY, _(" mil"))
        grid_sizer_1.Add(label_4, 0, 0, 0)
        label_5 = wx.StaticText(self, wx.ID_ANY, _("Raster Direction"))
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
        try:
            self.element.name = self.text_name.GetValue()
            if self.kernel is not None:
                self.kernel.signal("element_property_update", self.element)
        except AttributeError:
            pass

    def on_spin_speed(self, event):  # wxGlade: ElementProperty.<event_handler>
        self.element.speed = self.spin_speed_set.GetValue()
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.element)

    def on_spin_power(self, event):
        self.element.power = self.spin_power_set.GetValue()
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.element)

    def on_spin_speed_dratio(self, event):  # wxGlade: ElementProperty.<event_handler>
        self.element.dratio = self.spin_speed_dratio.GetValue()
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.element)

    def on_spin_passes(self, event):  # wxGlade: ElementProperty.<event_handler>
        self.element.passes = self.spin_passes.GetValue()
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.element)

    def on_spin_step(self, event):  # wxGlade: ElementProperty.<event_handler>
        self.element.raster_step = self.spin_step_size.GetValue()
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.element)

    def on_combobox_rasterdirection(self, event):  # wxGlade: Preferences.<event_handler>
        self.element.raster_direction = self.combo_raster_direction.GetSelection()
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.element)

    def on_button_color(self, event):  # wxGlade: ElementProperty.<event_handler>
        button = event.EventObject
        self.text_name.SetBackgroundColour(button.GetBackgroundColour())
        self.text_name.Refresh()
        color = swizzlecolor(button.GetBackgroundColour().GetRGB())
        self.element.stroke = Color(color)
        self.element.values[SVG_ATTR_STROKE] = Color(color).hex
        if self.kernel is not None:
            self.kernel.signal("element_property_update", self.element)
