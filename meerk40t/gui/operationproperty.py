import wx

from ..kernel import signal_listener
from ..svgelements import Color
from .icons import icons8_laser_beam_52
from .laserrender import swizzlecolor
from .mwindow import MWindow

_ = wx.GetTranslation

COLOR_TOOLTIP = _(
    """Change/View color of this layer. When Meerk40t classifies elements to operations, this exact color is used to match elements to this operation."""
)

OPERATION_TYPE_TOOLTIP = _(
    """Operation Type

Cut & Engrave are vector operations, Raster and Image are raster operations.

Cut and Engrave operations are essentially the same except that for a Cut operation with Cut Outer Paths last, only closed Paths in Cut operations are considered as being Outer-most."""
)

OPERATION_DEFAULT_TOOLTIP = _(
    """When classifying elements, Default operations gain all appropriate elements not matched to an existing operation of the same colour, rather than a new operation of that color being created.

Raster operations created automatically."""
)

OPERATION_SPEED_TOOLTIP = _(
    """Speed at which the head moves in mm/s.
For Cut/Engrave vector operations, this is the speed of the head regardless of direction i.e. the separate x/y speeds vary according to the direction.

For Raster/Image operations, this is the speed of the head as it sweeps backwards and forwards."
    """
)

OPERATION_POWER_TOOLTIP = _(
    """Pulses Per Inch - This is software created laser power control.
1000 is always on, 500 is half power (fire every other step).
Values of 100 or have pulses > 1/10" and are generally used only for dotted or perforated lines."""
)

OPERATION_PASSES_TOOLTIP = _(
    """"How many times to repeat this operation?
    
Setting e.g. passes to 2 is essentially equivalent to Duplicating the operation, creating a second identical operation with the same settings and same elements.

The number of Operation Passes can be changed extremely easily, but you cannot change any of the other settings.

Duplicating the Operation gives more flexibility for changing settings, but is far more cumbersome to change the number of duplications because you need to add and delete the duplicates one by one."""
)

OPERATION_RASTERSTEP_TOOLTIP = _(
    """
In a raster engrave, the step size is the distance between raster lines in 1/1000" and also the number of raster dots that get combined together.

Because the laser dot is >> 1/1000" in diameter, at step 1 the raster lines overlap a lot, and consequently  you can raster with steps > 1 without leaving gaps between the lines.

The step size before you get gaps will depend on your focus and the size of your laser dot.

Step size > 1 reduces the laser energy delivered by the same factor, so you may need to increase power equivalently with a higher front-panel power, a higher PPI or by rastering at a slower speed.

Step size > 1 also turns the laser on and off fewer times, and combined with a slower speed this can prevent your laser from stuttering."""
)

OPERATION_RASTERDIRECTION_TOOLTIP = _(
    """Direction to perform a raster

Normally you would raster in an X-direction and select Top-to-Bottom (T2B) or Bottom-to-Top (B2T).

This is because rastering in the X-direction involve moving only the laser head which is relatively low mass.

Rastering in the Y-direction (Left-to-Right or Right-to-Left) involves moving not only the laser head but additionally the entire x-axis gantry assembly including the stepper motor, mirror and the gantry itself.\n\nThis total mass is much greater, acceleration therefore needs to be much slower, and allow for space at each end of the raster to reverse direction the speed has to be much slower."""
)

OPERATION_RASTERSWING_TOOLTIP = _(
    """"Raster on forward and backswing or only forward swing?
    
Rastering only on forward swings will double the time required to complete the raster.
    
It seems doubtful that there will be significant quality benefits from rastering in one direction."""
)

OPERATION_ACCEL_TOOLTIP = _(
    """The m2-nano controller has four acceleration settings, and automatically selects the appropriate setting for the Cut or Raster speed.
This setting allows you to override the automatic selection and specify your own."""
)

OPERATION_DRATIO_TOOLTIP = _(
    """Diagonal ratio is the ratio of additional time needed to perform a diagonal step rather than an orthogonal step. (0.261 default)"""
)

OPERATION_SHIFT_TOOLTIP = _(
    """Pulse Grouping is an alternative means of reducing the incidence of stuttering, allowing you potentially to burn at higher speeds.

This setting is an operation-by-operation equivalent to the Pulse Grouping option in Device Config.

It works by swapping adjacent on or off bits to group on and off together and reduce the number of switches.

As an example, instead of 1010 it will burn 1100 - because the laser beam is overlapping, and because a bit is only moved at most 1/1000", the difference should not be visible even under magnification."""
)

OPERATION_DOTLENGTH_TOOLTIP = _(
    """For Cut/Engrave operations, when using PPI, Dot Length sets the minimum length for the laser to be on in order to change a continuous lower power burn into a series of dashes.
    
When this is set, the PPI effectively becomes the ratio of dashes to gaps. For example:

If you set Dot Length to 500 = 1/2", a PPI of 500 would result in 1/2" dashes and 1/2" gaps.

If you set Dot Length to 250 = 1/4", a PPI of 250 would result in 1/4" dashes and 3/4" gaps.
"""
)


class LayerSettingPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        layer_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Layer:"), wx.HORIZONTAL
        )

        self.button_layer_color = wx.Button(self, wx.ID_ANY, "")
        self.button_layer_color.SetBackgroundColour(wx.Colour(0, 0, 0))
        self.button_layer_color.SetToolTip(COLOR_TOOLTIP)
        layer_sizer.Add(self.button_layer_color, 0, 0, 0)

        self.combo_type = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["Engrave", "Cut", "Raster", "Image"],
            style=wx.CB_DROPDOWN,
        )
        self.combo_type.SetToolTip(OPERATION_TYPE_TOOLTIP)
        self.combo_type.SetSelection(0)
        layer_sizer.Add(self.combo_type, 1, 0, 0)

        self.checkbox_output = wx.CheckBox(self, wx.ID_ANY, "Enable")
        self.checkbox_output.SetToolTip(
            "Enable this operation for inclusion in Execute Job."
        )
        self.checkbox_output.SetValue(1)
        layer_sizer.Add(self.checkbox_output, 1, 0, 0)

        self.checkbox_default = wx.CheckBox(self, wx.ID_ANY, "Default")
        self.checkbox_default.SetToolTip(OPERATION_DEFAULT_TOOLTIP)
        self.checkbox_default.SetValue(1)
        layer_sizer.Add(self.checkbox_default, 1, 0, 0)

        self.SetSizer(layer_sizer)

        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_layer, self.button_layer_color)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_operation, self.combo_type)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_output, self.checkbox_output)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_default, self.checkbox_default)
        # end wxGlade

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

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
                for m in self.GetParent().Children:
                    if isinstance(m, wx.Window):
                        m.Hide()
                return
        self.button_layer_color.SetBackgroundColour(
            wx.Colour(swizzlecolor(self.operation.color))
        )
        if self.operation.output is not None:
            self.checkbox_output.SetValue(self.operation.output)
        if self.operation.default is not None:
            self.checkbox_default.SetValue(self.operation.default)

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
        self.context.elements.signal("element_property_reload", self.operation)

    def on_combo_operation(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>

        select = self.combo_type.GetSelection()
        if select == 0:
            self.operation.operation = "Engrave"
        elif select == 1:
            self.operation.operation = "Cut"
        elif select == 2:
            self.operation.operation = "Raster"
        elif select == 3:
            self.operation.operation = "Image"
        elif select == 4:
            self.operation.operation = "Dots"
        self.context.elements.signal("element_property_reload", self.operation)

    def on_check_output(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        self.operation.output = bool(self.checkbox_output.GetValue())
        self.context.elements.signal("element_property_reload", self.operation)

    def on_check_default(self, event=None):
        self.operation.default = bool(self.checkbox_default.GetValue())
        self.context.elements.signal("element_property_reload", self.operation)


# end of class LayerSettingPanel


class SpeedPpiPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: SpeedPpiPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        speed_power_sizer = wx.BoxSizer(wx.HORIZONTAL)

        speed_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Speed (mm/s)"), wx.HORIZONTAL
        )
        speed_power_sizer.Add(speed_sizer, 1, wx.EXPAND, 0)

        self.text_speed = wx.TextCtrl(self, wx.ID_ANY, "20.0")
        self.text_speed.SetToolTip(OPERATION_SPEED_TOOLTIP)
        speed_sizer.Add(self.text_speed, 1, 0, 0)

        power_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Power (ppi)"), wx.HORIZONTAL
        )
        speed_power_sizer.Add(power_sizer, 1, wx.EXPAND, 0)

        self.text_power = wx.TextCtrl(self, wx.ID_ANY, "1000.0")
        self.text_power.SetToolTip(OPERATION_POWER_TOOLTIP)
        power_sizer.Add(self.text_power, 1, 0, 0)

        self.SetSizer(speed_power_sizer)

        self.Layout()

        self.Bind(wx.EVT_TEXT, self.on_text_speed, self.text_speed)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_speed, self.text_speed)
        self.Bind(wx.EVT_TEXT, self.on_text_power, self.text_power)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_power, self.text_power)
        # end wxGlade

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def set_widgets(self):
        if self.operation.settings.speed is not None:
            self.text_speed.SetValue(str(self.operation.settings.speed))
        if self.operation.settings.power is not None:
            self.update_power_label()
            self.text_power.SetValue(str(self.operation.settings.power))

    def on_text_speed(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.speed = float(self.text_speed.GetValue())
        except ValueError:
            return
        self.context.elements.signal("element_property_reload", self.operation)

    def update_power_label(self):
        # if self.operation.settings.power <= 100:
        #     self.power_label.SetLabel(_("Power (ppi):") + "⚠️")
        # else:
        #     self.power_label.SetLabel(_("Power (ppi):"))
        pass

    def on_text_power(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.power = float(self.text_power.GetValue())
        except ValueError:
            return
        self.update_power_label()
        self.context.elements.signal("element_property_reload", self.operation)


# end of class SpeedPpiPanel


class PassesPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: PassesPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        sizer_passes = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Passes:"), wx.HORIZONTAL
        )

        self.check_passes = wx.CheckBox(self, wx.ID_ANY, "Passes")
        self.check_passes.SetToolTip("Enable Operation Passes")
        sizer_passes.Add(self.check_passes, 1, 0, 0)

        self.text_passes = wx.TextCtrl(self, wx.ID_ANY, "1")
        self.text_passes.SetToolTip(OPERATION_PASSES_TOOLTIP)
        sizer_passes.Add(self.text_passes, 1, 0, 0)

        self.SetSizer(sizer_passes)

        self.Layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_passes, self.check_passes)
        self.Bind(wx.EVT_TEXT, self.on_text_passes, self.text_passes)
        # end wxGlade

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def set_widgets(self):
        if self.operation.settings.passes_custom is not None:
            self.check_passes.SetValue(self.operation.settings.passes_custom)
        if self.operation.settings.passes is not None:
            self.text_passes.SetValue(str(self.operation.settings.passes))

    def on_check_passes(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        on = self.check_passes.GetValue()
        self.text_passes.Enable(on)
        self.operation.settings.passes_custom = bool(on)
        self.context.elements.signal("element_property_reload", self.operation)

    def on_text_passes(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.passes = int(self.text_passes.GetValue())
        except ValueError:
            return
        self.context.elements.signal("element_property_reload", self.operation)


# end of class PassesPanel


class PanelStartPreference(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: PanelStartPreference.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        sizer_2 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Start Preference:"), wx.VERTICAL
        )

        self.slider_top = wx.Slider(self, wx.ID_ANY, 1, 0, 2)
        sizer_2.Add(self.slider_top, 0, wx.EXPAND, 0)

        sizer_7 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(sizer_7, 0, wx.EXPAND, 0)

        self.slider_left = wx.Slider(self, wx.ID_ANY, 1, 0, 2, style=wx.SL_VERTICAL)
        sizer_7.Add(self.slider_left, 0, wx.EXPAND, 0)

        self.display_panel = wx.Panel(self, wx.ID_ANY)
        sizer_7.Add(self.display_panel, 1, wx.EXPAND, 0)

        self.slider_right = wx.Slider(self, wx.ID_ANY, 1, 0, 2, style=wx.SL_VERTICAL)
        sizer_7.Add(self.slider_right, 0, 0, 0)

        self.slider_bottom = wx.Slider(self, wx.ID_ANY, 1, 0, 2)
        sizer_2.Add(self.slider_bottom, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_2)

        self.Layout()

        self.Bind(wx.EVT_SLIDER, self.on_slider_top, self.slider_top)
        self.Bind(wx.EVT_SLIDER, self.on_slider_left, self.slider_left)
        self.Bind(wx.EVT_SLIDER, self.on_slider_right, self.slider_right)
        self.Bind(wx.EVT_SLIDER, self.on_slider_bottom, self.slider_bottom)
        # end wxGlade
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.display_panel.Bind(wx.EVT_PAINT, self.on_display_paint)
        self.display_panel.Bind(wx.EVT_ERASE_BACKGROUND, self.on_display_erase)

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

        self._Buffer = None

        self.context.setting(bool, "developer_mode", False)
        if not self.context.developer_mode:
            # 0.6.1 freeze, drops.
            self.slider_top.Enable(False)
            self.slider_right.Enable(False)
            self.slider_left.Enable(False)
            self.slider_bottom.Enable(False)
            self.toggle_sliders = False
        else:
            self.toggle_sliders = True
            self._toggle_sliders()

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    @signal_listener("element_property_reload")
    def on_element_property_reload(self, origin=None, *args):
        self._toggle_sliders()
        self.raster_lines = None
        self.travel_lines = None
        self.refresh_display()

    def set_widgets(self):
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
        if self.Shown:
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
        dc.SelectObject(wx.NullBitmap)
        del dc
        self.display_panel.Refresh()
        self.display_panel.Update()

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

    def on_slider_top(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        self.operation.settings.raster_preference_top = self.slider_top.GetValue() - 1
        self.context.elements.signal("element_property_reload", self.operation)

    def on_slider_left(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        self.operation.settings.raster_preference_left = self.slider_left.GetValue() - 1
        self.context.elements.signal("element_property_reload", self.operation)

    def on_slider_right(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        self.operation.settings.raster_preference_right = (
            self.slider_right.GetValue() - 1
        )
        self.context.elements.signal("element_property_reload", self.operation)

    def on_slider_bottom(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        self.operation.settings.raster_preference_bottom = (
            self.slider_bottom.GetValue() - 1
        )
        self.context.elements.signal("element_property_reload", self.operation)


# end of class PanelStartPreference


class RasterSettingsPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: RasterSettingsPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        raster_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Raster:"), wx.VERTICAL
        )

        sizer_3 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Raster Step:"), wx.HORIZONTAL
        )
        raster_sizer.Add(sizer_3, 0, wx.EXPAND, 0)

        self.text_raster_step = wx.TextCtrl(self, wx.ID_ANY, "1")
        self.text_raster_step.SetToolTip(OPERATION_RASTERSTEP_TOOLTIP)
        sizer_3.Add(self.text_raster_step, 0, 0, 0)

        sizer_6 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Overscan:"), wx.HORIZONTAL
        )
        raster_sizer.Add(sizer_6, 0, wx.EXPAND, 0)

        self.text_overscan = wx.TextCtrl(self, wx.ID_ANY, "20")
        self.text_overscan.SetToolTip("Overscan amount")
        sizer_6.Add(self.text_overscan, 1, 0, 0)

        self.combo_overscan_units = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["steps", "mm", "cm", "inch", "mil", "%"],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_overscan_units.SetSelection(0)
        sizer_6.Add(self.combo_overscan_units, 0, 0, 0)

        sizer_4 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Direction:"), wx.HORIZONTAL
        )
        raster_sizer.Add(sizer_4, 0, wx.EXPAND, 0)

        self.combo_raster_direction = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=[
                "Top To Bottom",
                "Bottom To Top",
                "Right To Left",
                "Left To Right",
                "Crosshatch",
            ],
            style=wx.CB_DROPDOWN,
        )
        self.combo_raster_direction.SetToolTip(OPERATION_RASTERDIRECTION_TOOLTIP)
        self.combo_raster_direction.SetSelection(0)
        sizer_4.Add(self.combo_raster_direction, 1, 0, 0)

        self.radio_directional_raster = wx.RadioBox(
            self,
            wx.ID_ANY,
            "Directional Raster:",
            choices=["Bidirectional", "Unidirectional"],
            majorDimension=1,
            style=wx.RA_SPECIFY_ROWS,
        )
        self.radio_directional_raster.SetToolTip(OPERATION_RASTERSWING_TOOLTIP)
        self.radio_directional_raster.SetSelection(0)
        raster_sizer.Add(self.radio_directional_raster, 0, wx.EXPAND, 0)

        self.panel_start = PanelStartPreference(
            self, wx.ID_ANY, context=context, node=node
        )
        raster_sizer.Add(self.panel_start, 0, wx.EXPAND, 0)

        self.SetSizer(raster_sizer)

        self.Layout()

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
        # end wxGlade

        self.context.setting(bool, "developer_mode", False)
        if not self.context.developer_mode:
            self.radio_directional_raster.Enable(False)

    def pane_hide(self):
        self.panel_start.pane_hide()

    def pane_show(self):
        self.panel_start.pane_show()

    def set_widgets(self):
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

    def on_text_raster_step(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.raster_step = int(self.text_raster_step.GetValue())
        except ValueError:
            return
        self.context.signal("element_property_reload", self.operation)

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
        self.context.elements.signal("element_property_reload", self.operation)

    def on_combo_raster_direction(self, event=None):
        self.operation.settings.raster_direction = (
            self.combo_raster_direction.GetSelection()
        )
        self.context.raster_direction = self.operation.settings.raster_direction
        self.context.elements.signal("element_property_reload", self.operation)

    def on_radio_directional(
        self, event=None
    ):  # wxGlade: RasterProperty.<event_handler>
        self.operation.settings.raster_swing = (
            self.radio_directional_raster.GetSelection()
        )
        self.context.elements.signal("element_property_reload", self.operation)


# end of class RasterSettingsPanel


class ParameterPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: ParameterPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        param_sizer = wx.BoxSizer(wx.VERTICAL)

        self.layer_panel = LayerSettingPanel(
            self, wx.ID_ANY, context=context, node=node
        )
        param_sizer.Add(self.layer_panel, 0, wx.EXPAND, 0)

        self.speedppi_panel = SpeedPpiPanel(self, wx.ID_ANY, context=context, node=node)
        param_sizer.Add(self.speedppi_panel, 0, wx.EXPAND, 0)

        self.passes_panel = PassesPanel(self, wx.ID_ANY, context=context, node=node)
        param_sizer.Add(self.passes_panel, 0, wx.EXPAND, 0)

        self.raster_panel = RasterSettingsPanel(
            self, wx.ID_ANY, context=context, node=node
        )
        param_sizer.Add(self.raster_panel, 0, wx.EXPAND, 0)

        self.SetSizer(param_sizer)

        self.Layout()
        # end wxGlade

    @signal_listener("element_property_reload")
    def on_element_property_reload(self, origin=None, *args):
        if self.operation.operation not in ("Raster", "Image"):
            if self.raster_panel.Shown:
                self.raster_panel.Hide()
        else:
            if not self.raster_panel.Shown:
                self.raster_panel.Show()

    def set_widgets(self):
        self.layer_panel.set_widgets()
        self.speedppi_panel.set_widgets()
        self.passes_panel.set_widgets()
        self.raster_panel.set_widgets()

    def pane_hide(self):
        self.layer_panel.pane_hide()
        self.speedppi_panel.pane_hide()
        self.passes_panel.pane_hide()
        self.raster_panel.pane_hide()

    def pane_show(self):
        self.layer_panel.pane_show()
        self.speedppi_panel.pane_show()
        self.passes_panel.pane_show()
        self.raster_panel.pane_show()


# end of class ParameterPanel


class LhyAdvancedPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LhyAdvancedPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        extras_sizer = wx.BoxSizer(wx.VERTICAL)

        advanced_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Speed Code Features:"), wx.VERTICAL
        )
        extras_sizer.Add(advanced_sizer, 0, wx.EXPAND, 0)

        sizer_11 = wx.BoxSizer(wx.HORIZONTAL)
        advanced_sizer.Add(sizer_11, 0, wx.EXPAND, 0)

        self.check_dratio_custom = wx.CheckBox(self, wx.ID_ANY, "Custom D-Ratio")
        self.check_dratio_custom.SetToolTip(
            "Enables the ability to modify the diagonal ratio."
        )
        sizer_11.Add(self.check_dratio_custom, 1, 0, 0)

        self.text_dratio = wx.TextCtrl(self, wx.ID_ANY, "0.261")
        self.text_dratio.SetToolTip(OPERATION_DRATIO_TOOLTIP)
        sizer_11.Add(self.text_dratio, 1, 0, 0)

        sizer_12 = wx.BoxSizer(wx.HORIZONTAL)
        advanced_sizer.Add(sizer_12, 0, wx.EXPAND, 0)

        self.checkbox_custom_accel = wx.CheckBox(self, wx.ID_ANY, "Acceleration")
        self.checkbox_custom_accel.SetToolTip("Enables acceleration override")
        sizer_12.Add(self.checkbox_custom_accel, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_accel = wx.Slider(
            self, wx.ID_ANY, 1, 1, 4, style=wx.SL_AUTOTICKS | wx.SL_LABELS
        )
        self.slider_accel.SetToolTip(OPERATION_ACCEL_TOOLTIP)
        sizer_12.Add(self.slider_accel, 1, wx.EXPAND, 0)

        advanced_ppi_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Plot Planner"), wx.HORIZONTAL
        )
        extras_sizer.Add(advanced_ppi_sizer, 0, wx.EXPAND, 0)

        sizer_19 = wx.BoxSizer(wx.VERTICAL)
        advanced_ppi_sizer.Add(sizer_19, 1, wx.EXPAND, 0)

        sizer_20 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_19.Add(sizer_20, 1, wx.EXPAND, 0)

        self.check_dot_length_custom = wx.CheckBox(self, wx.ID_ANY, "Dot Length")
        self.check_dot_length_custom.SetToolTip("Enable Dot Length")
        sizer_20.Add(self.check_dot_length_custom, 1, 0, 0)
        self.text_dot_length = wx.TextCtrl(self, wx.ID_ANY, "1")
        self.text_dot_length.SetToolTip(OPERATION_DOTLENGTH_TOOLTIP)
        sizer_20.Add(self.text_dot_length, 1, 0, 0)

        self.combo_dot_length_units = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["steps", "mm", "cm", "inch", "mil", "%"],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_dot_length_units.SetSelection(0)
        sizer_20.Add(self.combo_dot_length_units, 0, 0, 0)

        self.check_shift_enabled = wx.CheckBox(self, wx.ID_ANY, "Group Pulses")
        self.check_shift_enabled.SetToolTip(OPERATION_SHIFT_TOOLTIP)
        sizer_19.Add(self.check_shift_enabled, 0, 0, 0)

        self.SetSizer(extras_sizer)

        self.Layout()

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
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_shift_enabled, self.check_shift_enabled
        )
        # end wxGlade

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def set_widgets(self):
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
        if self.operation.settings.dot_length_custom is not None:
            self.check_dot_length_custom.SetValue(
                self.operation.settings.dot_length_custom
            )
        if self.operation.settings.dot_length is not None:
            self.text_dot_length.SetValue(str(self.operation.settings.dot_length))
        if self.operation.settings.shift_enabled is not None:
            self.check_shift_enabled.SetValue(self.operation.settings.shift_enabled)

    def on_check_dratio(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        on = self.check_dratio_custom.GetValue()
        self.text_dratio.Enable(on)
        self.operation.settings.dratio_custom = bool(on)
        self.context.elements.signal("element_property_reload", self.operation)

    def on_text_dratio(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.dratio = float(self.text_dratio.GetValue())
        except ValueError:
            return
        self.context.elements.signal("element_property_reload", self.operation)

    def on_check_acceleration(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        on = self.checkbox_custom_accel.GetValue()
        self.slider_accel.Enable(on)
        self.operation.settings.acceleration_custom = bool(on)
        self.context.elements.signal("element_property_reload", self.operation)

    def on_slider_accel(self, event=None):
        self.operation.settings.acceleration = self.slider_accel.GetValue()
        self.context.elements.signal("element_property_reload", self.operation)

    def on_check_dot_length(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        on = self.check_dot_length_custom.GetValue()
        self.text_dot_length.Enable(on)
        self.operation.settings.dot_length_custom = bool(on)
        self.context.elements.signal("element_property_reload", self.operation)

    def on_text_dot_length(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        try:
            self.operation.settings.dot_length = int(self.text_dot_length.GetValue())
        except ValueError:
            return
        self.context.elements.signal("element_property_reload", self.operation)

    def on_check_shift_enabled(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        self.operation.settings.shift_enabled = bool(
            self.check_shift_enabled.GetValue()
        )
        self.context.elements.signal("element_property_reload", self.operation)


class OperationProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(350, 582, *args, **kwds)

        self.notebook_main = wx.Notebook(self, wx.ID_ANY)

        self.param_panel = ParameterPanel(
            self.notebook_main, wx.ID_ANY, context=self.context, node=node
        )
        self.notebook_main.AddPage(self.param_panel, "Properties")

        self.advanced_panel = LhyAdvancedPanel(
            self.notebook_main, wx.ID_ANY, context=self.context, node=node
        )
        self.notebook_main.AddPage(self.advanced_panel, "Advanced")

        self.add_module_delegate(self.param_panel.raster_panel.panel_start)
        self.add_module_delegate(self.param_panel)
        # begin wxGlade: OperationProperty.__set_properties
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_laser_beam_52.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Operation Properties"))
        self.param_panel.set_widgets()
        self.advanced_panel.set_widgets()

    def restore(self, *args, node=None, **kwds):
        self.param_panel.operation = node
        self.param_panel.set_widgets()
        self.param_panel.on_size()

        self.advanced_panel.operation = node
        self.advanced_panel.set_widgets()
        self.advanced_panel.on_size()
        self.Refresh()
        self.Update()

    def window_open(self):
        self.param_panel.pane_show()
        self.advanced_panel.pane_show()

    def window_close(self):
        self.param_panel.pane_hide()
        self.advanced_panel.pane_hide()

    def window_preserve(self):
        return False
