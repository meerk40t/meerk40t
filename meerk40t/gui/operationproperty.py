import wx

from ..svgelements import Color
from .icons import icons8_laser_beam_52
from .laserrender import swizzlecolor
from .mwindow import MWindow

_ = wx.GetTranslation

_simple_width = 350
_advanced_width = 612


class OperationPropertyPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self._Buffer = None

        self.main_panel = wx.Panel(self, wx.ID_ANY)
        self.button_layer_color = wx.Button(self.main_panel, wx.ID_ANY, "")
        self.combo_type = wx.ComboBox(
            self.main_panel,
            wx.ID_ANY,
            choices=[_("Engrave"), _("Cut"), _("Raster"), _("Image")],
            style=wx.CB_DROPDOWN,
        )
        self.checkbox_output = wx.CheckBox(self.main_panel, wx.ID_ANY, _("Enable"))
        self.checkbox_default = wx.CheckBox(self.main_panel, wx.ID_ANY, _("Default"))
        self.text_speed = wx.TextCtrl(self.main_panel, wx.ID_ANY, "20.0")
        self.text_power = wx.TextCtrl(self.main_panel, wx.ID_ANY, "1000.0")
        self.speed_label = wx.StaticBox(
            self.main_panel,
            wx.ID_ANY,
            _("Speed (mm/s)"),
        )
        self.power_label = wx.StaticBox(
            self.main_panel,
            wx.ID_ANY,
            _("Power (ppi)"),
        )
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
            _("Directional Raster:"),
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
            self.advanced_panel, wx.ID_ANY, _("Pulse Grouping")
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
        self.travel_pen.SetColour(wx.Colour(255, 127, 255, 127))
        self.travel_pen.SetWidth(2)

        self.direction_pen = wx.Pen()
        self.direction_pen.SetColour(wx.Colour(127, 127, 255))
        self.direction_pen.SetWidth(2)

        self.raster_lines = None
        self.travel_lines = None
        self.direction_lines = None

        self.context.setting(bool, "developer_mode", False)
        if not self.context.developer_mode:
            # 0.6.1 freeze, drops.
            self.radio_directional_raster.Enable(False)
            self.slider_top.Enable(False)
            self.slider_right.Enable(False)
            self.slider_left.Enable(False)
            self.slider_bottom.Enable(False)
            self.toggle_sliders = False
        else:
            self.toggle_sliders = True
            self._toggle_sliders()
        if self.operation is None:
            for m in self.main_panel.Children:
                if isinstance(m, wx.Window):
                    m.Hide()

    def finalize(self):
        pass

    def initialize(self):
        self.set_widgets()
        # self.Bind(wx.EVT_BUTTON, self.on_button_add, self.button_add_layer)
        # self.Bind(wx.EVT_LISTBOX, self.on_list_layer_click, self.listbox_layer)
        # self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_list_layer_dclick, self.listbox_layer)
        # self.Bind(wx.EVT_BUTTON, self.on_button_remove, self.button_remove_layer)
        self.Bind(wx.EVT_BUTTON, self.on_button_layer, self.button_layer_color)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_operation, self.combo_type)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_output, self.checkbox_output)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_default, self.checkbox_default)
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
            self.update_speed_label()
            self.text_speed.SetValue(str(self.operation.settings.speed))
        if self.operation.settings.power is not None:
            self.update_power_label()
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
        if self.operation.default is not None:
            self.checkbox_default.SetValue(self.operation.default)
        self.on_check_advanced()
        self.on_combo_operation()

    def __set_properties(self):
        self.button_layer_color.SetBackgroundColour(wx.Colour(0, 0, 0))
        self.button_layer_color.SetToolTip(
            "\n".join(
                (
                    _(
                        "Change/View color of this layer. When Meerk40t classifies elements to operations, this exact color is used to match elements to this operation."
                    ),
                )
            )
        )
        self.combo_type.SetToolTip(
            "\n".join(
                (
                    _("Operation Type"),
                    "",
                    _(
                        "Cut & Engrave are vector operations, Raster and Image are raster operations."
                    ),
                    _(
                        "Cut and Engrave operations are essentially the same except that for a Cut operation with Cut Outer Paths last, only closed Paths in Cut operations are considered as being Outer-most."
                    ),
                )
            )
        )
        self.checkbox_output.SetToolTip(
            "\n".join((_("Enable this operation for inclusion in Execute Job."),))
        )
        self.checkbox_output.SetValue(1)
        self.checkbox_default.SetToolTip(
            "\n".join(
                (
                    _(
                        "When classifying elements, Default operations gain all appropriate elements not matched to an existing operation of the same colour, rather than a new operation of that color being created."
                    ),
                    _("Raster operations created automatically by Meerkat "),
                )
            )
        )
        self.checkbox_default.SetValue(0)
        self.text_speed.SetToolTip(
            "\n".join(
                (
                    _("Speed at which the head moves in mm/s."),
                    _(
                        "For Cut/Engrave vector operations, this is the speed of the head regardless of direction i.e. the separate x/y speeds vary according to the direction."
                    ),
                    _(
                        "For Raster/Image operations, this is the speed of the head as it sweeps backwards and forwards."
                    ),
                )
            )
        )
        self.text_power.SetToolTip(
            "\n".join(
                (
                    _(
                        "Pulses Per Inch - This is software created laser power control."
                    ),
                    _("1000 is always on, 500 is half power (fire every other step)."),
                    _(
                        'Values of 100 or have pulses > 1/10" and are generally used only for dotted or perforated lines.'
                    ),
                )
            )
        )
        self.text_raster_step.SetToolTip(
            "\n".join(
                (
                    _(
                        'In a raster engrave, the step size is the distance between raster lines in 1/1000" and also the number of raster dots that get combined together.'
                    ),
                    _(
                        'Because the laser dot is >> 1/1000" in diameter, at step 1 the raster lines overlap a lot, and consequently  you can raster with steps > 1 without leaving gaps between the lines.'
                    ),
                    _(
                        "The step size before you get gaps will depend on your focus and the size of your laser dot."
                    ),
                    _(
                        "Step size > 1 reduces the laser energy delivered by the same factor, so you may need to increase power equivalently with a higher front-panel power, a higher PPI or by rastering at a slower speed."
                    ),
                    _(
                        "Step size > 1 also turns the laser on and off fewer times, and combined with a slower speed this can prevent your laser from stuttering."
                    ),
                )
            )
        )
        self.text_overscan.SetToolTip(
            "\n".join((_("Overscan amount - BETTER EXPLANATION TO BE ADDED"),))
        )
        self.combo_raster_direction.SetToolTip(
            "\n".join(
                (
                    _("Direction to perform a raster"),
                    _(
                        "Normally you would raster in an X-direction and select Top-to-Bottom (T2B) or Bottom-to-Top (B2T)."
                    )
                    + " "
                    + _(
                        "This is because rastering in the X-direction involve moving only the laser head which is relatively low mass."
                    ),
                    _(
                        "Rastering in the Y-direction (Left-to-Right or Right-to-Left) involves moving not only the laser head but additionally the entire x-axis gantry assembly including the stepper motor, mirror and the gantry itself."
                    )
                    + " "
                    + _(
                        "This total mass is much greater, acceleration therefore needs to be much slower, and allow for space at each end of the raster to reverse direction the speed has to be much slower."
                    ),
                    _("Crosshatch - DESCRIPTION needed."),
                )
            )
        )
        self.combo_raster_direction.SetSelection(0)
        self.radio_directional_raster.SetToolTip(
            "\n".join(
                (
                    _("Raster on forward and backswing or only forward swing?"),
                    _(
                        "Rastering only on forward swings will double the time required to complete the raster."
                    ),
                    _(
                        "It seems doubtful that there will be significant quality benefits from rastering in one direction."
                    ),
                )
            )
        )
        self.radio_directional_raster.SetSelection(0)
        self.checkbox_advanced.SetToolTip("\n".join((_("Show advanced options?"),)))
        self.check_dratio_custom.SetToolTip(
            "\n".join((_("Enables the ability to modify the diagonal ratio."),))
        )
        self.text_dratio.SetToolTip(
            "\n".join(
                (
                    _(
                        "Diagonal ratio is the ratio of additional time needed to perform a diagonal step rather than an orthogonal step. (0.261 default)"
                    ),
                )
            )
        )
        self.checkbox_custom_accel.SetToolTip(
            "\n".join((_("Enables acceleration override"),))
        )
        self.slider_accel.SetToolTip(
            "\n".join(
                (
                    _(
                        "The m2-nano controller has four acceleration settings, and automatically selects the appropriate setting for the Cut or Raster speed."
                    ),
                    _(
                        "This setting allows you to override the automoatic selection and specify your own. The default settings are as follows:"
                    ),
                    "",
                    _("VECTOR"),
                    _("1: 0mm/s - 25.4mm/s"),
                    _("2: 25.4mm/s - 60mm/s"),
                    _("3: 60mm/s - 127mm/s"),
                    _("4: 127mm/s+"),
                    "",
                    _("RASTER"),
                    _("1: 0mm/s - 25.4mm/s"),
                    _("2: 25.4mm/s - 127mm/s"),
                    _("3: 127mm/s - 320mm/s"),
                    _("4: 320mm/s+"),
                    "",
                    _(
                        "This setting might be particularly useful if you want to raster L2R or R2L or possibly crosshatch to try to maximise speed whilst avoiding losing position."
                    ),
                )
            )
        )
        self.check_dot_length_custom.SetToolTip("\n".join((_("Enable Dot Length"),)))
        self.text_dot_length.SetToolTip(
            "\n".join(
                (
                    _(
                        "For Cut/Engrave operations, when using PPI, Dot Length sets the minimum length for the laser to be on in order to change a continuous lower power burn into a series of dashes."
                    ),
                    _(
                        "When this is set, the PPI effectively becomes the ratio of dashes to gaps. For example:"
                    ),
                    _(
                        'If you set Dot Length to 500 = 1/2", a PPI of 500 would result in 1/2" dashes and 1/2" gaps.'
                    ),
                    _(
                        'If you set Dot Length to 250 = 1/4", a PPI of 250 would result in 1/4" dashes and 3/4" gaps.'
                    ),
                )
            )
        )
        self.check_shift_enabled.SetToolTip(
            "\n".join(
                (
                    _(
                        "Pulse Grouping is an alternative means of reducing the incidence of stuttering, allowing you potentially to burn at higher speeds."
                    ),
                    _(
                        "This setting is an operation-by-operation equivalent to the Pulse Grouping option in Device Config."
                    ),
                    _(
                        "It works by swapping adjacent on or off bits to group on and off together and reduce the number of switches."
                    ),
                    _(
                        'As an example, instead of 1010 it will burn 1100 - because the laser beam is overlapping, and because a bit is only moved at most 1/1000", the difference should not be visible even under magnification.'
                    ),
                )
            )
        )
        self.check_passes.SetToolTip("\n".join((_("Enable Operation Passes"),)))
        self.text_passes.SetToolTip(
            "\n".join(
                (
                    _("How many times to repeat this operation?"),
                    _(
                        "Setting e.g. passes to 2 is essentially equivalent to Duplicating the operation, creating a second identical operation with the same settings and same elements."
                    ),
                    _(
                        "The number of Operation Passes can be changed extremely easily, but you cannot change any of the other settings."
                    ),
                    _(
                        "Duplicating the Operation gives more flexibility for changing settings, but is far more cumbersome to change the number of duplications because you need to add and delete the duplicates one by one."
                    ),
                )
            )
        )
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: OperationProperty.__do_layout
        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        extras_sizer = wx.BoxSizer(wx.VERTICAL)
        passes_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self.advanced_panel, wx.ID_ANY, _("Passes:")), wx.VERTICAL
        )
        sizer_22 = wx.BoxSizer(wx.HORIZONTAL)
        advanced_ppi_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self.advanced_panel, wx.ID_ANY, _("Advanced PPI:")),
            wx.HORIZONTAL,
        )
        sizer_19 = wx.BoxSizer(wx.VERTICAL)
        sizer_20 = wx.BoxSizer(wx.HORIZONTAL)
        advanced_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self.advanced_panel, wx.ID_ANY, _("Speedcode Advanced:")),
            wx.VERTICAL,
        )
        sizer_12 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_11 = wx.BoxSizer(wx.HORIZONTAL)
        param_sizer = wx.BoxSizer(wx.VERTICAL)
        raster_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self.raster_panel, wx.ID_ANY, _("Raster:")), wx.VERTICAL
        )
        sizer_2 = wx.StaticBoxSizer(
            wx.StaticBox(self.raster_panel, wx.ID_ANY, _("Start Preference:")),
            wx.VERTICAL,
        )
        sizer_7 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_6 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        speed_power_sizer = wx.BoxSizer(wx.HORIZONTAL)
        power_sizer = wx.StaticBoxSizer(self.power_label, wx.HORIZONTAL)
        speed_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self.main_panel, wx.ID_ANY, _("Speed (mm/s):")), wx.HORIZONTAL
        )
        layer_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self.main_panel, wx.ID_ANY, _("Layer:")), wx.HORIZONTAL
        )
        layers_sizer = wx.BoxSizer(wx.VERTICAL)
        # layers_sizer.Add(self.button_add_layer, 0, 0, 0)
        # layers_sizer.Add(self.listbox_layer, 1, wx.EXPAND, 0)
        # layers_sizer.Add(self.button_remove_layer, 0, 0, 0)
        sizer_main.Add(layers_sizer, 0, wx.EXPAND, 0)
        layer_sizer.Add(self.button_layer_color, 0, 0, 0)
        layer_sizer.Add(self.combo_type, 1, 0, 0)
        layer_sizer.Add(self.checkbox_output, 1, 0, 0)
        layer_sizer.Add(self.checkbox_default, 1, 0, 0)
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

    def on_display_paint(self, event=None):
        try:
            wx.BufferedPaintDC(self.display_panel, self._Buffer)
        except RuntimeError:
            pass

    def on_display_erase(self, event=None):
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
        right = True
        top = True

        last = None
        direction = self.operation.settings.raster_direction
        r_start = list()
        r_end = list()
        t_start = list()
        t_end = list()
        d_start = list()
        d_end = list()
        factor = 3
        unidirectional = self.operation.settings.raster_swing

        if direction == 0 or direction == 1 or direction == 4:
            # Direction Line
            d_start.append((w * 0.05, h * 0.05))
            d_end.append((w * 0.05, h * 0.95))
            if direction == 1:
                # Bottom to Top
                if self.operation.settings.raster_preference_bottom > 0:
                    # if bottom preference is left
                    right = False
                # Direction Arrow
                d_start.append((w * 0.05, h * 0.05))
                d_end.append((w * 0.05 + 4, h * 0.05 + 4))
                d_start.append((w * 0.05, h * 0.05))
                d_end.append((w * 0.05 - 4, h * 0.05 + 4))
                start = int(h * 0.9)
                end = int(h * 0.1)
                step = -self.operation.settings.raster_step * factor
            else:
                # Top to Bottom or Crosshatch
                if self.operation.settings.raster_preference_top > 0:
                    # if top preference is left
                    right = False
                d_start.append((w * 0.05, h * 0.95))
                d_end.append((w * 0.05 + 4, h * 0.95 - 4))
                d_start.append((w * 0.05, h * 0.95))
                d_end.append((w * 0.05 - 4, h * 0.95 - 4))
                start = int(h * 0.1)
                end = int(h * 0.9)
                step = self.operation.settings.raster_step * factor
            if step == 0:
                step = 1
            for pos in range(start, end, step):
                # Primary Line Horizontal Raster
                r_start.append((w * 0.1, pos))
                r_end.append((w * 0.9, pos))

                # Arrow Segment
                if last is not None:
                    # Travel Lines
                    t_start.append((last[0], last[1]))
                    t_end.append((w * 0.1 if right else w * 0.9, pos))

                r_start.append((w * 0.9 if right else w * 0.1, pos))
                r_end.append((w * 0.9 - 2 if right else w * 0.1 + 2, pos - 2))
                last = r_start[-1]
                if not unidirectional:
                    right = not right
        if direction == 2 or direction == 3 or direction == 4:
            # Direction Line
            d_start.append((w * 0.05, h * 0.05))
            d_end.append((w * 0.95, h * 0.05))
            if direction == 2:
                # Right to Left
                if self.operation.settings.raster_preference_right > 0:
                    # if right preference is bottom
                    top = False
                # Direction Arrow
                d_start.append((w * 0.05, h * 0.05))
                d_end.append((w * 0.05 + 4, h * 0.05 + 4))
                d_start.append((w * 0.05, h * 0.05))
                d_end.append((w * 0.05 + 4, h * 0.05 - 4))
                start = int(w * 0.9)
                end = int(w * 0.1)
                step = -self.operation.settings.raster_step * factor
            else:
                # Left to Right or Crosshatch
                if self.operation.settings.raster_preference_left > 0:
                    # if left preference is bottom
                    top = False
                d_start.append((w * 0.95, h * 0.05))
                d_end.append((w * 0.95 - 4, h * 0.05 + 4))
                d_start.append((w * 0.95, h * 0.05))
                d_end.append((w * 0.95 - 4, h * 0.05 - 4))
                start = int(w * 0.1)
                end = int(w * 0.9)
                step = self.operation.settings.raster_step * factor
            if step == 0:
                step = 1
            for pos in range(start, end, step):
                # Primary Line Vertical Raster.
                r_start.append((pos, h * 0.1))
                r_end.append((pos, h * 0.9))

                # Arrow Segment
                if last is not None:
                    # Travel Lines
                    t_start.append((last[0], last[1]))
                    t_end.append((pos, h * 0.1 if top else h * 0.9))
                r_start.append((pos, h * 0.9 if top else h * 0.1))
                r_end.append((pos - 2, (h * 0.9) - 2 if top else (h * 0.1) + 2))

                last = r_start[-1]
                if not unidirectional:
                    top = not top
        self.raster_lines = r_start, r_end
        self.travel_lines = t_start, t_end
        self.direction_lines = d_start, d_end

    def refresh_in_ui(self):
        """Performs the redraw of the data in the UI thread."""
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        if self.raster_panel.Shown:
            if self.raster_lines is None:
                self.calculate_raster_lines()
            if self.raster_lines is not None:
                starts, ends = self.raster_lines
                if len(starts):
                    gc.SetPen(self.raster_pen)
                    gc.StrokeLineSegments(starts, ends)
            if self.travel_lines is not None:
                starts, ends = self.travel_lines
                if len(starts):
                    gc.SetPen(self.travel_pen)
                    gc.StrokeLineSegments(starts, ends)
            if self.direction_lines is not None:
                starts, ends = self.direction_lines
                if len(starts):
                    gc.SetPen(self.direction_pen)
                    gc.StrokeLineSegments(starts, ends)
        gc.Destroy()
        del dc
        self.display_panel.Refresh()
        self.display_panel.Update()

    def on_button_layer(self, event=None):  # wxGlade: OperationProperty.<event_handler>
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
        self.context.signal("element_property_reload", self.operation)

    def on_combo_operation(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>

        self.text_dot_length.Enable(self.check_dot_length_custom.GetValue())
        self.text_passes.Enable(self.check_passes.GetValue())
        select = self.combo_type.GetSelection()
        self.raster_panel.Show(False)
        if select == 0:
            self.operation.operation = "Engrave"
            self.check_dratio_custom.Enable(True)
            self.text_dratio.Enable(self.check_dratio_custom.GetValue())
            self.Layout()
        elif select == 1:
            self.operation.operation = "Cut"
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
        elif select == 4:
            self.operation.operation = "Dots"
            self.check_dratio_custom.Enable(True)
            self.text_dratio.Enable(self.check_dratio_custom.GetValue())
            self.Layout()
        self.context.signal("element_property_reload", self.operation)

    def on_check_output(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        self.operation.output = bool(self.checkbox_output.GetValue())
        self.context.signal("element_property_reload", self.operation)

    def on_check_default(self, event=None):
        self.operation.default = bool(self.checkbox_default.GetValue())
        self.context.signal("element_property_reload", self.operation)

    def update_speed_label(self):
        if (
            self.operation._operation in ("Raster", "Image")
            and self.operation.settings.speed > 500
        ) or (
            self.operation._operation in ("Cut", "Engrave")
            and self.operation.settings.speed > 50
        ):
            self.speed_label.SetLabel(_("Speed (mm/s):") + "⚠️")
        else:
            self.speed_label.SetLabel(_("Speed (mm/s):"))

    def on_text_speed(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.speed = float(self.text_speed.GetValue())
        except ValueError:
            return
        self.update_speed_label()
        self.context.signal("element_property_reload", self.operation)

    def update_power_label(self):
        if self.operation.settings.power <= 100:
            self.power_label.SetLabel(_("Power (ppi):") + "⚠️")
        else:
            self.power_label.SetLabel(_("Power (ppi):"))

    def on_text_power(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.power = float(self.text_power.GetValue())
        except ValueError:
            return
        self.update_power_label()
        self.context.signal("element_property_reload", self.operation)

    def on_text_raster_step(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.raster_step = int(self.text_raster_step.GetValue())
        except ValueError:
            return
        self.context.signal("element_property_reload", self.operation)
        self.raster_lines = None
        self.travel_lines = None
        self.refresh_display()

    def on_text_overscan(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        overscan = self.text_overscan.GetValue()
        if not overscan.endswith("%"):
            try:
                overscan = int(overscan)
            except ValueError:
                return
        self.operation.settings.overscan = overscan
        self.context.signal("element_property_reload", self.operation)

    def _toggle_sliders(self):
        if self.toggle_sliders:
            direction = self.operation.settings.raster_direction
            self.slider_top.Enable(False)
            self.slider_right.Enable(False)
            self.slider_left.Enable(False)
            self.slider_bottom.Enable(False)
            if direction == 0:
                self.slider_top.Enable(True)
            elif direction == 1:
                self.slider_bottom.Enable(True)
            elif direction == 2:
                self.slider_right.Enable(True)
            elif direction == 3:
                self.slider_left.Enable(True)
            elif direction == 4:
                self.slider_top.Enable(True)
                self.slider_left.Enable(True)

    def on_combo_raster_direction(self, event=None):
        self.operation.settings.raster_direction = (
            self.combo_raster_direction.GetSelection()
        )
        self.context.raster_direction = self.operation.settings.raster_direction
        self._toggle_sliders()

        self.raster_lines = None
        self.travel_lines = None
        self.refresh_display()
        self.context.signal("element_property_reload", self.operation)

    def on_radio_directional(
        self, event=None
    ):  # wxGlade: RasterProperty.<event_handler>
        self.operation.settings.raster_swing = (
            self.radio_directional_raster.GetSelection()
        )
        self.raster_lines = None
        self.travel_lines = None
        self.refresh_display()
        self.context.signal("element_property_reload", self.operation)

    def on_slider_top(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        self.raster_lines = None
        self.travel_lines = None
        self.operation.settings.raster_preference_top = self.slider_top.GetValue() - 1
        self.refresh_display()
        self.context.signal("element_property_reload", self.operation)

    def on_slider_left(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        self.raster_lines = None
        self.travel_lines = None
        self.operation.settings.raster_preference_left = self.slider_left.GetValue() - 1
        self.refresh_display()
        self.context.signal("element_property_reload", self.operation)

    def on_slider_right(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        self.raster_lines = None
        self.travel_lines = None
        self.operation.settings.raster_preference_right = (
            self.slider_right.GetValue() - 1
        )
        self.refresh_display()
        self.context.signal("element_property_reload", self.operation)

    def on_slider_bottom(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        self.raster_lines = None
        self.travel_lines = None
        self.operation.settings.raster_preference_bottom = (
            self.slider_bottom.GetValue() - 1
        )
        self.refresh_display()
        self.context.signal("element_property_reload", self.operation)

    def on_check_advanced(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        on = self.checkbox_advanced.GetValue()
        self.advanced_panel.Show(on)
        self.operation.settings.advanced = bool(on)
        if on:
            self.GetParent().SetSize((_advanced_width, 500))
        else:
            self.GetParent().SetSize((_simple_width, 500))

    def on_check_dratio(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        on = self.check_dratio_custom.GetValue()
        self.text_dratio.Enable(on)
        self.operation.settings.dratio_custom = bool(on)
        self.context.signal("element_property_reload", self.operation)

    def on_text_dratio(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.dratio = float(self.text_dratio.GetValue())
        except ValueError:
            return
        self.context.signal("element_property_reload", self.operation)

    def on_check_acceleration(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        on = self.checkbox_custom_accel.GetValue()
        self.slider_accel.Enable(on)
        self.operation.settings.acceleration_custom = bool(on)
        self.context.signal("element_property_reload", self.operation)

    def on_slider_accel(self, event=None):
        self.operation.settings.acceleration = self.slider_accel.GetValue()
        self.context.signal("element_property_reload", self.operation)

    def on_check_dot_length(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        on = self.check_dot_length_custom.GetValue()
        self.text_dot_length.Enable(on)
        self.operation.settings.dot_length_custom = bool(on)
        self.context.signal("element_property_reload", self.operation)

    def on_text_dot_length(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.dot_length = int(self.text_dot_length.GetValue())
        except ValueError:
            return
        self.context.signal("element_property_reload", self.operation)

    def on_check_group_pulses(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        self.operation.settings.shift_enabled = bool(
            self.check_shift_enabled.GetValue()
        )
        self.context.signal("element_property_reload", self.operation)

    def on_check_passes(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        on = self.check_passes.GetValue()
        self.text_passes.Enable(on)
        self.operation.settings.passes_custom = bool(on)
        self.context.signal("element_property_reload", self.operation)

    def on_text_passes(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.passes = int(self.text_passes.GetValue())
        except ValueError:
            return
        self.context.signal("element_property_reload", self.operation)


class OperationProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(_simple_width, 500, *args, **kwds)

        self.panel = OperationPropertyPanel(
            self, wx.ID_ANY, context=self.context, node=node
        )
        # begin wxGlade: OperationProperty.__set_properties
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_laser_beam_52.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Operation Properties"))

    def restore(self, *args, node=None, **kwds):
        self.panel.operation = node
        self.panel.set_widgets()
        self.panel.on_size()
        self.Refresh()
        self.Update()

    def window_open(self):
        self.panel.initialize()

    def window_close(self):
        self.panel.finalize()

    def window_preserve(self):
        return False
