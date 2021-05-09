import wx

from ..svgelements import Color
from .icons import icons8_delete_50, icons8_laser_beam_52, icons8_plus_50
from .laserrender import swizzlecolor
from .mwindow import MWindow

_ = wx.GetTranslation

_simple_width = 350
_advanced_width = 612


class OperationProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(_simple_width, 500, *args, **kwds)
        # self.set_alt_size(_advanced_width, 500)

        self.main_panel = wx.Panel(self, wx.ID_ANY)
        self.button_add_layer = wx.BitmapButton(
            self.main_panel, wx.ID_ANY, icons8_plus_50.GetBitmap()
        )
        self.listbox_layer = wx.ListBox(
            self.main_panel, wx.ID_ANY, choices=[], style=wx.LB_ALWAYS_SB | wx.LB_SINGLE
        )
        self.button_remove_layer = wx.BitmapButton(
            self.main_panel, wx.ID_ANY, icons8_delete_50.GetBitmap()
        )
        self.button_layer_color = wx.Button(self.main_panel, wx.ID_ANY, "")
        self.combo_type = wx.ComboBox(
            self.main_panel,
            wx.ID_ANY,
            choices=[_("Engrave"), _("Cut"), _("Raster"), _("Image")],
            style=wx.CB_DROPDOWN,
        )
        self.checkbox_output = wx.CheckBox(self.main_panel, wx.ID_ANY, _("Enable"))
        self.checkbox_show = wx.CheckBox(self.main_panel, wx.ID_ANY, _("Show"))
        self.text_speed = wx.TextCtrl(self.main_panel, wx.ID_ANY, "20.0")
        self.text_power = wx.TextCtrl(self.main_panel, wx.ID_ANY, "1000.0")
        self.raster_panel = wx.Panel(self.main_panel, wx.ID_ANY)
        self.text_raster_step = wx.TextCtrl(self.raster_panel, wx.ID_ANY, "1")
        self.text_overscan = wx.TextCtrl(self.raster_panel, wx.ID_ANY, "20")
        self.combo_raster_direction = wx.ComboBox(
            self.raster_panel,
            wx.ID_ANY,
            choices=[
                _("Top To Bottom"),
                _("Bottom To Top"),
                _("Right To Left"),
                _("Left To Right"),
                _("Crosshatch"),
            ],
            style=wx.CB_DROPDOWN,
        )
        self.radio_directional_raster = wx.RadioBox(
            self.raster_panel,
            wx.ID_ANY,
            _("Directional Raster"),
            choices=[_("Bidirectional"), _("Unidirectional")],
            majorDimension=1,
            style=wx.RA_SPECIFY_ROWS,
        )
        self.slider_top = wx.Slider(self.raster_panel, wx.ID_ANY, 1, 0, 2)
        self.slider_left = wx.Slider(
            self.raster_panel, wx.ID_ANY, 1, 0, 2, style=wx.SL_VERTICAL
        )
        self.display_panel = wx.Panel(self.raster_panel, wx.ID_ANY)
        self.slider_right = wx.Slider(
            self.raster_panel, wx.ID_ANY, 1, 0, 2, style=wx.SL_VERTICAL
        )
        self.slider_bottom = wx.Slider(self.raster_panel, wx.ID_ANY, 1, 0, 2)
        self.checkbox_advanced = wx.CheckBox(self.main_panel, wx.ID_ANY, _("Advanced"))
        self.advanced_panel = wx.Panel(self.main_panel, wx.ID_ANY)
        self.check_dratio_custom = wx.CheckBox(
            self.advanced_panel, wx.ID_ANY, _("Custom D-Ratio")
        )
        self.text_dratio = wx.TextCtrl(self.advanced_panel, wx.ID_ANY, "0.261")
        self.checkbox_custom_accel = wx.CheckBox(
            self.advanced_panel, wx.ID_ANY, _("Acceleration")
        )
        self.slider_accel = wx.Slider(
            self.advanced_panel,
            wx.ID_ANY,
            1,
            1,
            4,
            style=wx.SL_AUTOTICKS | wx.SL_LABELS,
        )
        self.check_dot_length_custom = wx.CheckBox(
            self.advanced_panel, wx.ID_ANY, _("Dot Length (mils)")
        )
        self.text_dot_length = wx.TextCtrl(self.advanced_panel, wx.ID_ANY, "1")
        self.check_shift_enabled = wx.CheckBox(
            self.advanced_panel, wx.ID_ANY, _("Group Pulses")
        )
        self.check_passes = wx.CheckBox(self.advanced_panel, wx.ID_ANY, _("Passes"))
        self.text_passes = wx.TextCtrl(self.advanced_panel, wx.ID_ANY, "1")

        self.__set_properties()
        self.__do_layout()

        self.combo_type.SetFocus()
        self.operation = node

        self.raster_pen = wx.Pen()
        self.raster_pen.SetColour(wx.BLACK)
        self.raster_pen.SetWidth(2)

        self.travel_pen = wx.Pen()
        self.travel_pen.SetColour(wx.Colour(255, 127, 255, 64))
        self.travel_pen.SetWidth(1)

        self.raster_lines = None
        self.travel_lines = None

    def restore(self, *args, node=None, **kwds):
        self.operation = node
        self.set_widgets()
        self.on_size()

    def window_close(self):
        pass

    def window_open(self):
        self.set_widgets()
        self.Bind(wx.EVT_BUTTON, self.on_button_add, self.button_add_layer)
        self.Bind(wx.EVT_LISTBOX, self.on_list_layer_click, self.listbox_layer)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_list_layer_dclick, self.listbox_layer)
        self.Bind(wx.EVT_BUTTON, self.on_button_remove, self.button_remove_layer)
        self.Bind(wx.EVT_BUTTON, self.on_button_layer, self.button_layer_color)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_operation, self.combo_type)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_output, self.checkbox_output)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_show, self.checkbox_show)
        self.Bind(wx.EVT_TEXT, self.on_text_speed, self.text_speed)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_speed, self.text_speed)
        self.Bind(wx.EVT_TEXT, self.on_text_power, self.text_power)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_power, self.text_power)
        self.Bind(wx.EVT_TEXT, self.on_text_raster_step, self.text_raster_step)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_raster_step, self.text_raster_step)
        self.Bind(wx.EVT_TEXT, self.on_text_overscan, self.text_overscan)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_overscan, self.text_overscan)
        self.Bind(
            wx.EVT_COMBOBOX, self.on_combo_raster_direction, self.combo_raster_direction
        )
        self.Bind(
            wx.EVT_RADIOBOX, self.on_radio_directional, self.radio_directional_raster
        )
        self.Bind(wx.EVT_SLIDER, self.on_slider_top, self.slider_top)
        self.Bind(wx.EVT_SLIDER, self.on_slider_left, self.slider_left)
        self.Bind(wx.EVT_SLIDER, self.on_slider_right, self.slider_right)
        self.Bind(wx.EVT_SLIDER, self.on_slider_bottom, self.slider_bottom)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_advanced, self.checkbox_advanced)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_dratio, self.check_dratio_custom)
        self.Bind(wx.EVT_TEXT, self.on_text_dratio, self.text_dratio)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_dratio, self.text_dratio)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_acceleration, self.checkbox_custom_accel
        )
        self.Bind(wx.EVT_COMMAND_SCROLL, self.on_slider_accel, self.slider_accel)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_dot_length, self.check_dot_length_custom
        )
        self.Bind(wx.EVT_TEXT, self.on_text_dot_length, self.text_dot_length)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_dot_length, self.text_dot_length)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_group_pulses, self.check_shift_enabled)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_passes, self.check_passes)
        self.Bind(wx.EVT_TEXT, self.on_text_passes, self.text_passes)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_passes, self.text_passes)
        self.display_panel.Bind(wx.EVT_PAINT, self.on_display_paint)
        self.display_panel.Bind(wx.EVT_ERASE_BACKGROUND, self.on_display_erase)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.on_size()

    def set_widgets(self):
        if self.operation is not None:
            op = self.operation.operation
            if op == "Engrave":
                self.combo_type.SetSelection(0)
            elif op == "Cut":
                self.combo_type.SetSelection(1)
            elif op == "Raster":
                self.combo_type.SetSelection(2)
            elif op == "Image":
                self.combo_type.SetSelection(3)
            elif op == "Dots":
                for m in self.main_panel.Children:
                    if isinstance(m, wx.Window):
                        m.Hide()
                return
        self.button_layer_color.SetBackgroundColour(
            wx.Colour(swizzlecolor(self.operation.color))
        )
        if self.operation.settings.speed is not None:
            self.text_speed.SetValue(str(self.operation.settings.speed))
        if self.operation.settings.power is not None:
            self.text_power.SetValue(str(self.operation.settings.power))
        if self.operation.settings.dratio is not None:
            self.text_dratio.SetValue(str(self.operation.settings.dratio))
        if self.operation.settings.dratio_custom is not None:
            self.check_dratio_custom.SetValue(self.operation.settings.dratio_custom)
        if self.operation.settings.acceleration is not None:
            self.slider_accel.SetValue(self.operation.settings.acceleration)
        if self.operation.settings.acceleration_custom is not None:
            self.checkbox_custom_accel.SetValue(
                self.operation.settings.acceleration_custom
            )
            self.slider_accel.Enable(self.checkbox_custom_accel.GetValue())
        if self.operation.settings.raster_step is not None:
            self.text_raster_step.SetValue(str(self.operation.settings.raster_step))
        if self.operation.settings.overscan is not None:
            self.text_overscan.SetValue(str(self.operation.settings.overscan))
        if self.operation.settings.raster_direction is not None:
            self.combo_raster_direction.SetSelection(
                self.operation.settings.raster_direction
            )
        if self.operation.settings.raster_swing is not None:
            self.radio_directional_raster.SetSelection(
                self.operation.settings.raster_swing
            )
        if self.operation.settings.raster_preference_top is not None:
            self.slider_top.SetValue(self.operation.settings.raster_preference_top + 1)
        if self.operation.settings.raster_preference_left is not None:
            self.slider_left.SetValue(
                self.operation.settings.raster_preference_left + 1
            )
        if self.operation.settings.raster_preference_right is not None:
            self.slider_right.SetValue(
                self.operation.settings.raster_preference_right + 1
            )
        if self.operation.settings.raster_preference_bottom is not None:
            self.slider_bottom.SetValue(
                self.operation.settings.raster_preference_bottom + 1
            )
        if self.operation.settings.advanced is not None:
            self.checkbox_advanced.SetValue(self.operation.settings.advanced)
        if self.operation.settings.dot_length_custom is not None:
            self.check_dot_length_custom.SetValue(
                self.operation.settings.dot_length_custom
            )
        if self.operation.settings.dot_length is not None:
            self.text_dot_length.SetValue(str(self.operation.settings.dot_length))
        if self.operation.settings.shift_enabled is not None:
            self.check_shift_enabled.SetValue(self.operation.settings.shift_enabled)
        if self.operation.settings.passes_custom is not None:
            self.check_passes.SetValue(self.operation.settings.passes_custom)
        if self.operation.settings.passes is not None:
            self.text_passes.SetValue(str(self.operation.settings.passes))
        if self.operation.output is not None:
            self.checkbox_output.SetValue(self.operation.output)
        if self.operation.show is not None:
            self.checkbox_show.SetValue(self.operation.show)
        self.on_check_advanced()
        self.on_combo_operation()

    def __set_properties(self):
        # begin wxGlade: OperationProperty.__set_properties
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_laser_beam_52.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Operation Properties"))
        self.button_add_layer.SetSize(self.button_add_layer.GetBestSize())
        self.listbox_layer.SetMinSize((40, -1))
        self.button_remove_layer.SetSize(self.button_remove_layer.GetBestSize())
        self.button_layer_color.SetBackgroundColour(wx.Colour(0, 0, 0))
        self.button_layer_color.SetToolTip(_("Change/View color of this layer"))
        self.combo_type.SetToolTip(_("Default Operation Mode Type"))
        self.checkbox_output.SetToolTip(_("Enable output of this layer"))
        self.checkbox_output.SetValue(1)
        self.checkbox_show.SetToolTip(_("Show This Layer"))
        self.checkbox_show.SetValue(1)
        self.text_speed.SetToolTip(_("Speed at which to perform the action in mm/s."))
        self.text_power.SetToolTip(
            _(
                "1000 always on. 500 it's half power (fire every other step). This is software PPI control."
            )
        )
        self.text_raster_step.SetToolTip(
            _(
                "Scan gap / step size, is the distance between scanlines in a raster engrave. Distance here is in 1/1000th of an inch."
            )
        )
        self.text_overscan.SetToolTip(_("Overscan amount"))
        self.combo_raster_direction.SetToolTip(_("Direction to perform a raster"))
        self.combo_raster_direction.SetSelection(0)
        self.radio_directional_raster.SetToolTip(
            _("Rastering on forward and backswing or only forward swing?")
        )
        self.radio_directional_raster.SetSelection(0)
        self.checkbox_advanced.SetToolTip(_("Turn on advanced options?"))
        self.check_dratio_custom.SetToolTip(
            _("Enables the ability to modify the diagonal ratio.")
        )
        self.text_dratio.SetToolTip(
            _(
                "Diagonal ratio is the ratio of additional time needed to perform a diagonal step rather than an orthogonal step. (0.261 default)"
            )
        )
        self.checkbox_custom_accel.SetToolTip(
            _("Enables the ability to modify the acceleration factor.")
        )
        self.slider_accel.SetToolTip(_("Acceleration Factor Override"))
        self.check_dot_length_custom.SetToolTip(_("Enable Dot Length Feature"))
        self.text_dot_length.SetToolTip(
            _("PPI minimum on length for making dash patterns")
        )
        self.check_shift_enabled.SetToolTip(
            _("Attempts to adjust the pulse grouping for data efficiency.")
        )
        self.check_passes.SetToolTip(_("Enable Passes"))
        self.text_passes.SetToolTip(_("Run operation how many times?"))
        # end wxGlade

        # 0.6.1 freeze, drops.
        self.radio_directional_raster.Enable(False)
        self.slider_top.Enable(False)
        self.slider_right.Enable(False)
        self.slider_left.Enable(False)
        self.slider_bottom.Enable(False)
        self.button_add_layer.Show(False)
        self.button_remove_layer.Show(False)
        self.listbox_layer.Show(False)
        self.checkbox_show.Enable(False)

    def __do_layout(self):
        # begin wxGlade: OperationProperty.__do_layout
        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        extras_sizer = wx.BoxSizer(wx.VERTICAL)
        passes_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self.advanced_panel, wx.ID_ANY, _("Passes")), wx.VERTICAL
        )
        sizer_22 = wx.BoxSizer(wx.HORIZONTAL)
        advanced_ppi_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self.advanced_panel, wx.ID_ANY, _("PPI Advanced")),
            wx.HORIZONTAL,
        )
        sizer_19 = wx.BoxSizer(wx.VERTICAL)
        sizer_20 = wx.BoxSizer(wx.HORIZONTAL)
        advanced_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self.advanced_panel, wx.ID_ANY, _("Speedcode Advanced")),
            wx.VERTICAL,
        )
        sizer_12 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_11 = wx.BoxSizer(wx.HORIZONTAL)
        param_sizer = wx.BoxSizer(wx.VERTICAL)
        raster_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self.raster_panel, wx.ID_ANY, _("Raster")), wx.VERTICAL
        )
        sizer_2 = wx.StaticBoxSizer(
            wx.StaticBox(self.raster_panel, wx.ID_ANY, _("Start Preference")),
            wx.VERTICAL,
        )
        sizer_7 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_6 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        speed_power_sizer = wx.BoxSizer(wx.HORIZONTAL)
        power_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self.main_panel, wx.ID_ANY, _("Power (ppi)")), wx.HORIZONTAL
        )
        speed_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self.main_panel, wx.ID_ANY, _("Speed (mm/s)")), wx.HORIZONTAL
        )
        layer_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self.main_panel, wx.ID_ANY, _("Layer")), wx.HORIZONTAL
        )
        layers_sizer = wx.BoxSizer(wx.VERTICAL)
        layers_sizer.Add(self.button_add_layer, 0, 0, 0)
        layers_sizer.Add(self.listbox_layer, 1, wx.EXPAND, 0)
        layers_sizer.Add(self.button_remove_layer, 0, 0, 0)
        sizer_main.Add(layers_sizer, 0, wx.EXPAND, 0)
        layer_sizer.Add(self.button_layer_color, 0, 0, 0)
        layer_sizer.Add(self.combo_type, 1, 0, 0)
        layer_sizer.Add(self.checkbox_output, 1, 0, 0)
        layer_sizer.Add(self.checkbox_show, 1, 0, 0)
        param_sizer.Add(layer_sizer, 0, wx.EXPAND, 0)
        speed_sizer.Add(self.text_speed, 1, 0, 0)
        speed_power_sizer.Add(speed_sizer, 1, wx.EXPAND, 0)
        power_sizer.Add(self.text_power, 1, 0, 0)
        speed_power_sizer.Add(power_sizer, 1, wx.EXPAND, 0)
        param_sizer.Add(speed_power_sizer, 0, wx.EXPAND, 0)
        label_7 = wx.StaticText(self.raster_panel, wx.ID_ANY, _("Raster Step (mils)"))
        sizer_3.Add(label_7, 1, 0, 0)
        sizer_3.Add(self.text_raster_step, 1, 0, 0)
        raster_sizer.Add(sizer_3, 0, wx.EXPAND, 0)
        label_6 = wx.StaticText(self.raster_panel, wx.ID_ANY, _("Overscan (mils)"))
        sizer_6.Add(label_6, 1, 0, 0)
        sizer_6.Add(self.text_overscan, 1, 0, 0)
        raster_sizer.Add(sizer_6, 0, wx.EXPAND, 0)
        label_5 = wx.StaticText(self.raster_panel, wx.ID_ANY, _("Raster Direction"))
        sizer_4.Add(label_5, 1, 0, 0)
        sizer_4.Add(self.combo_raster_direction, 1, 0, 0)
        raster_sizer.Add(sizer_4, 0, wx.EXPAND, 0)
        raster_sizer.Add(self.radio_directional_raster, 0, wx.EXPAND, 0)
        sizer_2.Add(self.slider_top, 0, wx.EXPAND, 0)
        sizer_7.Add(self.slider_left, 0, wx.EXPAND, 0)
        sizer_7.Add(self.display_panel, 1, wx.EXPAND, 0)
        sizer_7.Add(self.slider_right, 0, 0, 0)
        sizer_2.Add(sizer_7, 0, wx.EXPAND, 0)
        sizer_2.Add(self.slider_bottom, 0, wx.EXPAND, 0)
        raster_sizer.Add(sizer_2, 1, wx.EXPAND, 0)
        self.raster_panel.SetSizer(raster_sizer)
        param_sizer.Add(self.raster_panel, 1, wx.EXPAND, 0)
        param_sizer.Add(self.checkbox_advanced, 0, 0, 0)
        sizer_main.Add(param_sizer, 0, wx.EXPAND, 0)
        sizer_11.Add(self.check_dratio_custom, 1, 0, 0)
        sizer_11.Add(self.text_dratio, 1, 0, 0)
        advanced_sizer.Add(sizer_11, 0, wx.EXPAND, 0)
        sizer_12.Add(self.checkbox_custom_accel, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_12.Add(self.slider_accel, 1, wx.EXPAND, 0)
        advanced_sizer.Add(sizer_12, 0, wx.EXPAND, 0)
        extras_sizer.Add(advanced_sizer, 0, wx.EXPAND, 0)
        sizer_20.Add(self.check_dot_length_custom, 1, 0, 0)
        sizer_20.Add(self.text_dot_length, 1, 0, 0)
        sizer_19.Add(sizer_20, 1, wx.EXPAND, 0)
        sizer_19.Add(self.check_shift_enabled, 0, 0, 0)
        advanced_ppi_sizer.Add(sizer_19, 1, wx.EXPAND, 0)
        extras_sizer.Add(advanced_ppi_sizer, 0, wx.EXPAND, 0)
        sizer_22.Add(self.check_passes, 1, 0, 0)
        sizer_22.Add(self.text_passes, 1, 0, 0)
        passes_sizer.Add(sizer_22, 0, wx.EXPAND, 0)
        extras_sizer.Add(passes_sizer, 0, wx.EXPAND, 0)
        self.advanced_panel.SetSizer(extras_sizer)
        sizer_main.Add(self.advanced_panel, 1, wx.EXPAND, 0)
        self.main_panel.SetSizer(sizer_main)
        sizer_1.Add(self.main_panel, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        self.Centre()
        # end wxGlade

    def on_display_paint(self, event):
        try:
            wx.BufferedPaintDC(self.display_panel, self._Buffer)
        except RuntimeError:
            pass

    def on_display_erase(self, event):
        pass

    def set_buffer(self):
        width, height = self.display_panel.ClientSize
        if width <= 0:
            width = 1
        if height <= 0:
            height = 1
        self._Buffer = wx.Bitmap(width, height)

    def on_size(self, event=None):
        self.Layout()
        self.set_buffer()
        self.refresh_display()

    def refresh_display(self):
        if not wx.IsMainThread():
            wx.CallAfter(self.refresh_in_ui)
        else:
            self.refresh_in_ui()

    def calculate_raster_lines(self):
        w, h = self._Buffer.Size
        pos = 20
        steps = 20
        try:
            steps /= self.operation.settings.raster_step
            steps = int(steps)
        except (ValueError, ZeroDivisionError):
            pass
        step = (h - 40) / steps
        right = True
        last = None
        r_start = list()
        r_end = list()
        t_start = list()
        t_end = list()
        for j in range(steps):
            r_start.append((20, pos))
            r_end.append((w - 40, pos))
            if right:
                if last is not None:
                    t_start.append((last[0], last[1]))
                    t_end.append((w - 40, pos))
                r_start.append((w - 40, pos))
                r_end.append((w - 42, pos - 2))
                last = (w - 40, pos)
            else:
                if last is not None:
                    t_start.append((last[0], last[1]))
                    t_end.append((20, pos))
                r_start.append((20, pos))
                r_end.append((22, pos - 2))
            right = not right
            pos += step
        self.raster_lines = r_start, r_end
        self.travel_lines = t_start, t_end

    def refresh_in_ui(self):
        """Performs the redraw of the data in the UI thread."""
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        if self.raster_lines is None:
            self.calculate_raster_lines()

        starts, ends = self.raster_lines
        gc.SetPen(self.raster_pen)
        gc.StrokeLineSegments(starts, ends)

        gc.SetPen(self.travel_pen)
        starts, ends = self.raster_lines
        gc.StrokeLineSegments(starts, ends)

        gc.Destroy()
        del dc
        self.display_panel.Refresh()
        self.display_panel.Update()

    def on_menu_clear(self, event):  # wxGlade: OperationProperty.<event_handler>
        self.context.elements.clear_operations()

    def on_menu_default0(self, event):  # wxGlade: OperationProperty.<event_handler>
        self.context.elements.load_default()

    def on_menu_default1(self, event):  # wxGlade: OperationProperty.<event_handler>
        self.context.elements.load_default2()

    def on_menu_save(self, event):  # wxGlade: OperationProperty.<event_handler>
        pass

    def on_menu_load(self, event):  # wxGlade: OperationProperty.<event_handler>
        pass

    def on_menu_import(self, event):  # wxGlade: OperationProperty.<event_handler>
        pass

    def on_button_add(self, event):  # wxGlade: OperationProperty.<event_handler>
        pass

    def on_list_layer_click(self, event):  # wxGlade: OperationProperty.<event_handler>
        pass

    def on_list_layer_dclick(self, event):  # wxGlade: OperationProperty.<event_handler>
        pass

    def on_button_remove(self, event):  # wxGlade: OperationProperty.<event_handler>
        pass

    def on_button_layer(self, event):  # wxGlade: OperationProperty.<event_handler>
        data = wx.ColourData()
        if self.operation.color is not None and self.operation.color != "none":
            data.SetColour(wx.Colour(swizzlecolor(self.operation.color)))
        dlg = wx.ColourDialog(self, data)
        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetColourData()
            color = data.GetColour()
            rgb = color.GetRGB()
            color = swizzlecolor(rgb)
            self.operation.color = Color(color, 1.0)
            self.button_layer_color.SetBackgroundColour(
                wx.Colour(swizzlecolor(self.operation.color))
            )
        self.context.signal("element_property_update", self.operation)

    def on_combo_operation(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>

        self.text_dot_length.Enable(self.check_dot_length_custom.GetValue())
        self.text_passes.Enable(self.check_passes.GetValue())
        select = self.combo_type.GetSelection()
        if select == 0:
            self.operation.operation = "Engrave"
            self.raster_panel.Show(False)
            self.check_dratio_custom.Enable(True)
            self.text_dratio.Enable(self.check_dratio_custom.GetValue())
            self.Layout()
        elif select == 1:
            self.operation.operation = "Cut"
            self.raster_panel.Show(False)
            self.check_dratio_custom.Enable(True)
            self.text_dratio.Enable(self.check_dratio_custom.GetValue())
            self.Layout()
        elif select == 2:
            self.operation.operation = "Raster"
            self.raster_panel.Show(True)
            self.text_raster_step.Enable(True)
            self.text_raster_step.SetValue(str(self.operation.settings.raster_step))
            self.check_dratio_custom.Enable(False)
            self.text_dratio.Enable(False)
            self.Layout()
        elif select == 3:
            self.operation.operation = "Image"
            self.raster_panel.Show(True)
            self.text_raster_step.Enable(False)
            self.text_raster_step.SetValue(_("Pass Through"))
            self.check_dratio_custom.Enable(False)
            self.text_dratio.Enable(False)
            self.Layout()
        self.context.signal("element_property_update", self.operation)

    def on_check_output(self, event):  # wxGlade: OperationProperty.<event_handler>
        self.operation.output = bool(self.checkbox_output.GetValue())
        self.context.signal("element_property_update", self.operation)

    def on_check_show(self, event):
        self.operation.show = bool(self.checkbox_show.GetValue())
        self.context.signal("element_property_update", self.operation)

    def on_text_speed(self, event):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.speed = float(self.text_speed.GetValue())
        except ValueError:
            return
        self.context.signal("element_property_update", self.operation)

    def on_text_power(self, event):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.power = float(self.text_power.GetValue())
        except ValueError:
            return
        self.context.signal("element_property_update", self.operation)

    def on_text_raster_step(self, event):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.raster_step = int(self.text_raster_step.GetValue())
        except ValueError:
            return
        self.context.signal("element_property_update", self.operation)
        self.raster_lines = None
        self.travel_lines = None
        self.refresh_display()

    def on_text_overscan(self, event):  # wxGlade: OperationProperty.<event_handler>
        overscan = self.text_overscan.GetValue()
        if not overscan.endswith("%"):
            try:
                overscan = int(overscan)
            except ValueError:
                return
        self.operation.settings.overscan = overscan
        self.context.signal("element_property_update", self.operation)

    def on_combo_raster_direction(self, event):  # wxGlade: Preferences.<event_handler>
        self.operation.settings.raster_direction = (
            self.combo_raster_direction.GetSelection()
        )
        self.context.raster_direction = self.operation.settings.raster_direction
        self.context.signal("element_property_update", self.operation)

    def on_radio_directional(self, event):  # wxGlade: RasterProperty.<event_handler>
        self.operation.settings.raster_swing = (
            self.radio_directional_raster.GetSelection()
        )
        self.context.signal("element_property_update", self.operation)

    def on_slider_top(self, event):  # wxGlade: OperationProperty.<event_handler>
        self.operation.settings.raster_preference_top = self.slider_top.GetValue() - 1
        self.context.signal("element_property_update", self.operation)

    def on_slider_left(self, event):  # wxGlade: OperationProperty.<event_handler>
        self.operation.settings.raster_preference_left = self.slider_left.GetValue() - 1
        self.context.signal("element_property_update", self.operation)

    def on_slider_right(self, event):  # wxGlade: OperationProperty.<event_handler>
        self.operation.settings.raster_preference_right = (
            self.slider_right.GetValue() - 1
        )
        self.context.signal("element_property_update", self.operation)

    def on_slider_bottom(self, event):  # wxGlade: OperationProperty.<event_handler>
        self.operation.settings.raster_preference_bottom = (
            self.slider_bottom.GetValue() - 1
        )
        self.context.signal("element_property_update", self.operation)

    def on_check_advanced(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        on = self.checkbox_advanced.GetValue()
        self.advanced_panel.Show(on)
        self.operation.settings.advanced = bool(on)
        if on:
            self.SetSize((_advanced_width, 500))
        else:
            self.SetSize((_simple_width, 500))

    def on_check_dratio(self, event):  # wxGlade: OperationProperty.<event_handler>
        on = self.check_dratio_custom.GetValue()
        self.text_dratio.Enable(on)
        self.operation.settings.dratio_custom = bool(on)
        self.context.signal("element_property_update", self.operation)

    def on_text_dratio(self, event):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.dratio = float(self.text_dratio.GetValue())
        except ValueError:
            return
        self.context.signal("element_property_update", self.operation)

    def on_check_acceleration(
        self, event
    ):  # wxGlade: OperationProperty.<event_handler>
        on = self.checkbox_custom_accel.GetValue()
        self.slider_accel.Enable(on)
        self.operation.settings.acceleration_custom = bool(on)
        self.context.signal("element_property_update", self.operation)

    def on_slider_accel(self, event):
        self.operation.settings.acceleration = self.slider_accel.GetValue()
        self.context.signal("element_property_update", self.operation)

    def on_check_dot_length(self, event):  # wxGlade: OperationProperty.<event_handler>
        on = self.check_dot_length_custom.GetValue()
        self.text_dot_length.Enable(on)
        self.operation.settings.dot_length_custom = bool(on)
        self.context.signal("element_property_update", self.operation)

    def on_text_dot_length(self, event):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.dot_length = int(self.text_dot_length.GetValue())
        except ValueError:
            return
        self.context.signal("element_property_update", self.operation)

    def on_check_group_pulses(
        self, event
    ):  # wxGlade: OperationProperty.<event_handler>
        self.operation.settings.shift_enabled = bool(
            self.check_shift_enabled.GetValue()
        )
        self.context.signal("element_property_update", self.operation)

    def on_check_passes(self, event):  # wxGlade: OperationProperty.<event_handler>
        on = self.check_passes.GetValue()
        self.text_passes.Enable(on)
        self.operation.settings.passes_custom = bool(on)
        self.context.signal("element_property_update", self.operation)

    def on_text_passes(self, event):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.passes = int(self.text_passes.GetValue())
        except ValueError:
            return
        self.context.signal("element_property_update", self.operation)

    def on_key_press(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            self.Close()
        event.Skip()
