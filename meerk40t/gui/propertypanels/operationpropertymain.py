import wx

from meerk40t.gui.wxutils import (
    ScrolledPanel,
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    set_ctrl_value,
    wxButton,
    wxCheckBox,
    wxComboBox,
    wxRadioBox,
    wxStaticBitmap,
    wxStaticText,
)
from meerk40t.constants import (
    RASTER_T2B,
    RASTER_B2T,
    RASTER_R2L,
    RASTER_L2R,
    RASTER_HATCH,
    RASTER_GREEDY_H,
    RASTER_GREEDY_V,
    RASTER_CROSSOVER,
    RASTER_SPIRAL,
)
from meerk40t.kernel import lookup_listener, signal_listener
from meerk40t.gui.icons import icon_letter_h
from ...core.units import UNITS_PER_MM, Length
from ...svgelements import Color
from ..laserrender import swizzlecolor
from .attributes import IdPanel

_ = wx.GetTranslation

# OPERATION_TYPE_TOOLTIP = _(
#     """Operation Type

# Cut & Engrave are vector operations, Raster and Image are raster operations.

# Cut and Engrave operations are essentially the same except that for a Cut operation with Cut Outer Paths last, only closed Paths in Cut operations are considered as being Outer-most."""
# )


def validate_raster_settings(node):
    # Make sure things are properly set...
    if node.raster_direction in (RASTER_T2B, ):
        node.raster_preference_top = True
    elif node.raster_direction in (RASTER_B2T, ):
        node.raster_preference_top = False
    elif node.raster_direction in (RASTER_R2L, ):
        node.raster_preference_left = True
    elif node.raster_direction in (RASTER_L2R, ):
        node.raster_preference_left = False
    elif node.raster_direction in (RASTER_HATCH, RASTER_CROSSOVER):
        node.raster_preference_top = True
        node.raster_preference_left = True
    if node.raster_direction in (RASTER_CROSSOVER, RASTER_GREEDY_H, RASTER_GREEDY_V, RASTER_SPIRAL):
        node.bidirectional = True

class LayerSettingPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.operation = node

        layer_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Layer:"), wx.HORIZONTAL)

        self.button_layer_color = wxButton(self, wx.ID_ANY, "")
        self.button_layer_color.SetBackgroundColour(wx.Colour(0, 0, 0))
        COLOR_TOOLTIP = _(
            "Change/View color of this layer. When Meerk40t classifies elements to operations,"
        ) + _("this exact color is used to match elements to this operation.")

        self.button_layer_color.SetToolTip(COLOR_TOOLTIP)
        layer_sizer.Add(self.button_layer_color, 0, wx.EXPAND, 0)
        h_classify_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Restrict classification"), wx.HORIZONTAL
        )
        h_property_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Properties"), wx.HORIZONTAL
        )
        rastertooltip = ""
        if self.operation.type == "op raster":
            rastertooltip = (
                "\n"
                + _("If neither stroke nor fill are checked, then the raster op")
                + "\n"
                + _("will classify all elements that have a fill")
                + "\n"
                + _("or stroke that are either black or white.")
            )
        try:
            self.has_stroke = self.operation.has_color_attribute("stroke")
            self.checkbox_stroke = wxCheckBox(self, wx.ID_ANY, _("Stroke"))
            self.checkbox_stroke.SetToolTip(
                _("Look at the stroke color to restrict classification.")
                + rastertooltip
            )
            self.checkbox_stroke.SetValue(1 if self.has_stroke else 0)
            h_classify_sizer.Add(self.checkbox_stroke, 1, 0, 0)
            self.Bind(wx.EVT_CHECKBOX, self.on_check_stroke, self.checkbox_stroke)
        except AttributeError:
            self.has_stroke = None

        try:
            self.has_fill = self.operation.has_color_attribute("fill")
            self.checkbox_fill = wxCheckBox(self, wx.ID_ANY, _("Fill"))
            self.checkbox_fill.SetToolTip(
                _("Look at the fill color to restrict classification.") + rastertooltip
            )
            self.checkbox_fill.SetValue(1 if self.has_fill else 0)
            h_classify_sizer.Add(self.checkbox_fill, 1, 0, 0)
            self.Bind(wx.EVT_CHECKBOX, self.on_check_fill, self.checkbox_fill)
        except AttributeError:
            self.has_fill = None

        self.checkbox_stop = wxCheckBox(self, wx.ID_ANY, _("Stop"))
        self.checkbox_stop.SetToolTip(
            _("If active, then this op will prevent further classification")
            + "\n"
            + _("from other ops if it could classify an element by itself.")
        )
        h_classify_sizer.Add(self.checkbox_stop, 1, 0, 0)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_stop, self.checkbox_stop)
        self.has_stop = hasattr(self.operation, "stopop")
        if not self.has_stop:
            self.checkbox_stop.SetValue(False)
            self.checkbox_stop.Enable(False)
        else:
            self.checkbox_stop.SetValue(self.operation.stopop)
            self.checkbox_stop.Enable(True)

        if (
            self.has_fill is not None
            or self.has_stroke is not None
            or self.has_stop is not None
        ):
            layer_sizer.Add(h_classify_sizer, 1, wx.EXPAND, 0)

        # self.combo_type = wxComboBox(
        #     self,
        #     wx.ID_ANY,
        #     choices=["Engrave", "Cut", "Raster", "Image", "Hatch", "Dots"],
        #     style=wx.CB_DROPDOWN,
        # )
        # self.combo_type.SetToolTip(OPERATION_TYPE_TOOLTIP)
        # self.combo_type.SetSelection(0)
        # layer_sizer.Add(self.combo_type, 1, 0, 0)

        self.checkbox_output = wxCheckBox(self, wx.ID_ANY, _("Enable"))
        self.checkbox_output.SetToolTip(
            _("Enable this operation for inclusion in Execute Job.")
        )
        self.checkbox_output.SetValue(1)
        h_property_sizer.Add(self.checkbox_output, 1, 0, 0)

        self.checkbox_visible = wxCheckBox(self, wx.ID_ANY, _("Visible"))
        self.checkbox_visible.SetToolTip(
            _("Hide all contained elements on scene if not set.")
        )
        self.checkbox_visible.SetValue(1)
        self.checkbox_visible.Enable(False)
        h_property_sizer.Add(self.checkbox_visible, 1, 0, 0)

        self.checkbox_default = wxCheckBox(self, wx.ID_ANY, _("Default"))
        OPERATION_DEFAULT_TOOLTIP = (
            _(
                "When classifying elements, Default operations gain all appropriate elements "
            )
            + _("not matched to an existing operation of the same colour, ")
            + _("rather than a new operation of that color being created.")
        )

        self.checkbox_default.SetToolTip(OPERATION_DEFAULT_TOOLTIP)
        self.checkbox_default.SetValue(1)
        h_property_sizer.Add(self.checkbox_default, 1, 0, 0)

        layer_sizer.Add(h_property_sizer, 1, wx.EXPAND, 0)

        self.SetSizer(layer_sizer)

        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_layer, self.button_layer_color)
        # self.Bind(wx.EVT_COMBOBOX, self.on_combo_operation, self.combo_type)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_output, self.checkbox_output)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_visible, self.checkbox_visible)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_default, self.checkbox_default)
        # end wxGlade

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def accepts(self, node):
        return node.type in (
            "op cut",
            "op engrave",
            "op raster",
            "op image",
            "op dots",
        )

    def set_widgets(self, node):
        self.operation = node
        if self.operation is None or not self.accepts(node):
            self.Hide()
            return
        self.button_layer_color.SetBackgroundColour(
            wx.Colour(swizzlecolor(self.operation.color))
        )
        if self.operation.output is not None:
            self.checkbox_output.SetValue(self.operation.output)
        flag_set = True
        flag_enabled = False
        if self.operation.output is not None:
            if not self.operation.output:
                flag_enabled = True
                flag_set = self.operation.is_visible
        self.checkbox_visible.SetValue(flag_set)
        self.checkbox_visible.Enable(flag_enabled)
        if self.operation.default is not None:
            self.checkbox_default.SetValue(self.operation.default)
        try:
            if self.has_fill:
                self.checkbox_fill.SetValue(
                    1 if self.operation.has_color_attribute("fill") else 0
                )
        except AttributeError:
            pass
        try:
            if self.has_stroke:
                self.checkbox_stroke.SetValue(
                    1 if self.operation.has_color_attribute("stroke") else 0
                )
        except AttributeError:
            pass
        self.has_stop = hasattr(self.operation, "stopop")
        if not self.has_stop:
            self.checkbox_stop.SetValue(False)
            self.checkbox_stop.Enable(False)
        else:
            self.checkbox_stop.SetValue(self.operation.stopop)
            self.checkbox_stop.Enable(True)

        self.Layout()
        self.Show()

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
            try:
                self.button_layer_color.SetBackgroundColour(
                    wx.Colour(swizzlecolor(self.operation.color))
                )
            except RuntimeError:
                return
            # Ask the user if she/he wants to assign the color of the contained objects
            try:
                candidate_stroke = bool(self.checkbox_stroke.GetValue())
            except AttributeError:
                candidate_stroke = False
            try:
                candidate_fill = bool(self.checkbox_fill.GetValue())
            except AttributeError:
                candidate_fill = False
            if (
                self.operation.type in ("op engrave", "op cut")
                and len(self.operation.children) > 0
                and (candidate_fill or candidate_stroke)
            ):
                changed = []
                for e in self.operation.children:
                    if e.type.startswith("effect "):
                        e.stroke = self.operation.color
                        changed.append(e)
                dlg = wx.MessageDialog(
                    None,
                    message=_(
                        "Do you want to change the color of the contained elements too?"
                    ),
                    caption=_("Update Colors?"),
                    style=wx.YES_NO | wx.ICON_QUESTION,
                )
                response = dlg.ShowModal()
                dlg.Destroy()
                if response == wx.ID_YES:
                    for refnode in self.operation.children:
                        if refnode in changed:
                            continue
                        if hasattr(refnode, "node"):
                            cnode = refnode.node
                        else:
                            cnode = refnode
                        add_to_change = False
                        if candidate_stroke and hasattr(cnode, "stroke"):
                            cnode.stroke = self.operation.color
                            add_to_change = True

                        if candidate_fill and hasattr(cnode, "fill"):
                            cnode.fill = self.operation.color
                            add_to_change = True

                        if add_to_change:
                            changed.append(cnode)
                if len(changed) > 0:
                    self.context.elements.signal("element_property_update", changed)
                    self.context.elements.signal("refresh_scene", "Scene")

        self.context.elements.signal(
            "element_property_reload", self.operation, "button_layer"
        )
        self.context.elements.signal("updateop_tree")

    def on_check_output(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        if self.operation.output != bool(self.checkbox_output.GetValue()):
            self.operation.output = bool(self.checkbox_output.GetValue())
            self.context.elements.signal(
                "element_property_reload", self.operation, "check_output"
            )
        self.context.elements.signal("updateop_tree")
        self.checkbox_visible.Enable(not bool(self.checkbox_output.GetValue()))

    def on_check_visible(self, event=None):
        if self.operation.is_visible != bool(self.checkbox_visible.GetValue()):
            self.operation.is_visible = bool(self.checkbox_visible.GetValue())
            self.context.elements.validate_selected_area()
            self.context.elements.signal("element_property_update", self.operation)
            self.context.elements.signal("refresh_scene", "Scene")

    def on_check_default(self, event=None):
        if self.operation.default != bool(self.checkbox_default.GetValue()):
            self.operation.default = bool(self.checkbox_default.GetValue())
            self.context.elements.signal(
                "element_property_reload", self.operation, "check_default"
            )

    def on_check_fill(self, event=None):
        if self.checkbox_fill.GetValue():
            self.operation.add_color_attribute("fill")
        else:
            self.operation.remove_color_attribute("fill")
        self.context.elements.signal(
            "element_property_reload", self.operation, "check_fill"
        )
        event.Skip()

    def on_check_stroke(self, event=None):
        if self.checkbox_stroke.GetValue():
            self.operation.add_color_attribute("stroke")
        else:
            self.operation.remove_color_attribute("stroke")
        self.context.elements.signal(
            "element_property_reload", self.operation, "check_stroke"
        )
        event.Skip()

    def on_check_stop(self, event=None):
        if self.checkbox_stop.GetValue():
            self.operation.stopop = True
        else:
            self.operation.stopop = False
        self.context.elements.signal(
            "element_property_reload", self.operation, "check_stopop"
        )
        event.Skip()


# end of class LayerSettingPanel


class SpeedPpiPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: SpeedPpiPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.operation = node

        self.context.device.setting(bool, "use_percent_for_power_display", False)
        self.use_percent = self.context.device.use_percent_for_power_display
        self.context.device.setting(bool, "use_mm_min_for_speed_display", False)
        self.use_mm_min = self.context.device.use_mm_min_for_speed_display

        speed_power_sizer = wx.BoxSizer(wx.HORIZONTAL)
        if self.use_mm_min:
            speed_fact = 60
        else:
            speed_fact = 1

        speed_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Speed"), wx.HORIZONTAL)
        speed_power_sizer.Add(speed_sizer, 1, wx.EXPAND, 0)

        self.text_speed = TextCtrl(
            self,
            wx.ID_ANY,
            f"{20 * speed_fact:.0f}",
            limited=True,
            check="float",
            style=wx.TE_PROCESS_ENTER,
            nonzero=True,
        )
        self.trailer_speed = wxStaticText(self, id=wx.ID_ANY)
        speed_sizer.Add(self.text_speed, 1, wx.EXPAND, 0)
        speed_sizer.Add(self.trailer_speed, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.power_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Power (ppi)"), wx.HORIZONTAL
        )
        speed_power_sizer.Add(self.power_sizer, 1, wx.EXPAND, 0)

        self.text_power = TextCtrl(
            self,
            wx.ID_ANY,
            "1000.0",
            limited=True,
            check="float",
            style=wx.TE_PROCESS_ENTER,
        )
        self.trailer_power = wxStaticText(self, id=wx.ID_ANY, label=_("/1000"))
        self.power_sizer.Add(self.text_power, 1, wx.EXPAND, 0)
        self.power_sizer.Add(self.trailer_power, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.update_power_speed_properties()

        freq = self.context.device.lookup("frequency")
        if freq:
            frequency_sizer = StaticBoxSizer(
                self, wx.ID_ANY, _("Frequency (kHz)"), wx.HORIZONTAL
            )
            speed_power_sizer.Add(frequency_sizer, 1, wx.EXPAND, 0)

            self.text_frequency = TextCtrl(
                self,
                wx.ID_ANY,
                "20.0",
                limited=True,
                check="float",
                style=wx.TE_PROCESS_ENTER,
            )
            OPERATION_FREQUENCY_TOOLTIP = (
                _("Laser frequency in kHz.")
                + "\n"
                + _("For lasers with frequencies that can be set.")
            )
            self.text_frequency.SetToolTip(OPERATION_FREQUENCY_TOOLTIP)
            self.text_frequency.set_warn_level(*freq)
            frequency_sizer.Add(self.text_frequency, 1, wx.EXPAND, 0)
        else:
            self.text_frequency = None

        self.SetSizer(speed_power_sizer)

        self.Layout()

        self.text_speed.SetActionRoutine(self.on_text_speed)
        self.text_power.SetActionRoutine(self.on_text_power)

        if self.text_frequency:
            self.text_frequency.SetActionRoutine(self.on_text_frequency)

        # end wxGlade

    def pane_hide(self):
        pass

    def pane_show(self):
        self.update_power_speed_properties()

    def on_device_update(self):
        try:
            self.update_power_speed_properties()
        except RuntimeError:
            # Pane was already destroyed
            return
        self.set_widgets(self.operation)

    def update_power_speed_properties(self):
        speed_min = None
        speed_max = None
        power_min = None
        power_max = None

        op = self.operation.type
        if op.startswith("op "):  # Should, shouldn't it?
            op = op[3:]
        else:
            op = ""
        if op != "":
            label = "dangerlevel_op_" + op
            warning = [False, 0, False, 0, False, 0, False, 0]
            if hasattr(self.context.device, label):
                dummy = getattr(self.context.device, label)
                if isinstance(dummy, (tuple, list)) and len(dummy) == len(warning):
                    warning = dummy
            if warning[0]:
                power_min = warning[1]
            if warning[2]:
                power_max = warning[3]
            if warning[4]:
                speed_min = warning[5]
            if warning[6]:
                speed_max = warning[7]
        self.use_mm_min = self.context.device.use_mm_min_for_speed_display
        if self.use_mm_min:
            if speed_min is not None:
                speed_min *= 60
            if speed_max is not None:
                speed_max *= 60
            speed_unit = "mm/min"
        else:
            speed_unit = "mm/s"
        self.trailer_speed.SetLabel(speed_unit)
        OPERATION_SPEED_TOOLTIP = (
            _("Speed at which the head moves in {unit}.").format(unit=speed_unit)
            + "\n"
            + _(
                "For Cut/Engrave vector operations, this is the speed of the head regardless of direction i.e. the separate x/y speeds vary according to the direction."
            )
            + "\n"
            + _(
                "For Raster/Image operations, this is the speed of the head as it sweeps backwards and forwards."
            )
        )
        self.text_speed.SetToolTip(OPERATION_SPEED_TOOLTIP)
        self.text_speed.set_error_level(0, None)
        self.text_speed.set_warn_level(speed_min, speed_max)

        self.use_percent = self.context.device.use_percent_for_power_display
        if self.use_percent:
            self.trailer_power.SetLabel("%")
            self.text_power._check = "percent"
            if power_min is not None:
                power_min /= 10
            if power_max is not None:
                power_max /= 10
            self.text_power.set_range(0, 100)
            self.text_power.set_warn_level(power_min, power_max)
            OPERATION_POWER_TOOLTIP = _(
                "% of maximum power - This is a percentage of the maximum power of the laser."
            )
            self.power_sizer.SetLabel(_("Power"))
        else:
            self.trailer_power.SetLabel(_("/1000"))
            self.text_power._check = "float"
            self.text_power.set_range(0, 1000)
            self.text_power.set_warn_level(power_min, power_max)
            OPERATION_POWER_TOOLTIP = _(
                _("Pulses Per Inch - This is software created laser power control.")
                + "\n"
                + _("1000 is always on, 500 is half power (fire every other step).")
                + "\n"
                + _(
                    'Values of 100 or have pulses > 1/10" and are generally used only for dotted or perforated lines.'
                )
            )
            self.power_sizer.SetLabel(_("Power (ppi)"))
        self.text_power.SetToolTip(OPERATION_POWER_TOOLTIP)

    def accepts(self, node):
        return node.type in (
            "op cut",
            "op engrave",
            "op raster",
            "op image",
            "op dots",
        )

    def set_widgets(self, node):
        self.operation = node
        if self.operation is None or not self.accepts(node):
            self.Hide()
            return
        if self.operation.speed is not None:
            if self.use_mm_min:
                set_ctrl_value(self.text_speed, str(self.operation.speed * 60))
            else:
                set_ctrl_value(self.text_speed, str(self.operation.speed))
        if self.operation.power is not None:
            if self.use_percent:
                set_ctrl_value(self.text_power, f"{self.operation.power / 10.0:.0f}")
            else:
                set_ctrl_value(self.text_power, f"{self.operation.power:.0f}")
            self.update_power_label()
        if self.operation.frequency is not None and self.text_frequency:
            set_ctrl_value(self.text_frequency, str(self.operation.frequency))
        self.Show()

    def on_text_speed(self):  # wxGlade: OperationProperty.<event_handler>
        try:
            value = float(self.text_speed.GetValue())
            if self.use_mm_min:
                value /= 60
            if self.operation.speed != value:
                self.operation.speed = value
                self.context.elements.signal(
                    "element_property_reload", self.operation, "text_speed"
                )
                self.context.elements.signal("updateop_tree")
        except ValueError:
            pass

    def on_text_frequency(self):
        try:
            value = float(self.text_frequency.GetValue())
            if self.operation.frequency != value:
                self.operation.frequency = value
                self.context.elements.signal(
                    "element_property_reload", self.operation, "text_frquency"
                )
        except ValueError:
            pass

    def update_power_label(self):
        # if self.operation.power <= 100:
        #     self.power_label.SetLabel(_("Power (ppi):") + "⚠️")
        # else:
        #     self.power_label.SetLabel(_("Power (ppi):"))
        if self.use_percent:
            return
        try:
            value = float(self.text_power.GetValue())
            self.power_sizer.SetLabel(_("Power (ppi)") + f" ({value/10:.1f}%)")
        except ValueError:
            return

    def on_text_power(self):
        try:
            value = float(self.text_power.GetValue())
            if self.use_percent:
                value *= 10
            if self.operation.power != value:
                self.operation.power = value
                self.update_power_label()
                self.context.elements.signal(
                    "element_property_reload", self.operation, "text_power"
                )
                self.context.elements.signal("updateop_tree")
        except ValueError:
            return


# end of class SpeedPpiPanel


class PassesPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: PassesPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.operation = node
        self.has_kerf = False

        sizer_main = wx.BoxSizer(wx.HORIZONTAL)

        self.sizer_kerf = StaticBoxSizer(
            self, wx.ID_ANY, _("Kerf compensation:"), wx.HORIZONTAL
        )
        self.text_kerf = TextCtrl(
            self,
            wx.ID_ANY,
            "0",
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_kerf.SetToolTip(
            _(
                "Enter half the width of your laserbeam (kerf)\n"
                + "if you want to have a shape with an exact size.\n"
                + "Use the negative value if you are using the cutout\n"
                + "as a placeholder for another part (eg inlays)."
            )
        )
        self.kerf_label = wxStaticText(self, wx.ID_ANY, "")
        self.sizer_kerf.Add(self.text_kerf, 1, wx.EXPAND, 0)
        self.sizer_kerf.Add(self.kerf_label, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.sizer_coolant = StaticBoxSizer(
            self, wx.ID_ANY, _("Coolant:"), wx.HORIZONTAL
        )
        cool_choices = [_("No changes"), _("Turn on"), _("Turn off")]
        self.combo_coolant = wxComboBox(
            self,
            wx.ID_ANY,
            choices=cool_choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_coolant.SetToolTip(
            _(
                "Define whether coolant support shall be explicitly turned on or off at the start of the operation, or whether it should be left at its current state."
            )
        )
        self.sizer_coolant.Add(self.combo_coolant, 1, wx.EXPAND, 0)

        sizer_passes = StaticBoxSizer(self, wx.ID_ANY, _("Passes:"), wx.HORIZONTAL)

        self.check_passes = wxCheckBox(self, wx.ID_ANY, _("Passes"))
        self.check_passes.SetToolTip(_("Enable Operation Passes"))
        sizer_passes.Add(self.check_passes, 0, wx.EXPAND, 0)

        self.text_passes = TextCtrl(
            self, wx.ID_ANY, "1", limited=True, check="int", style=wx.TE_PROCESS_ENTER
        )
        OPERATION_PASSES_TOOLTIP = (
            _("How many times to repeat this operation?")
            + "\n"
            + _(
                "Setting e.g. passes to 2 is essentially equivalent to Duplicating the operation, "
            )
            + _(
                "creating a second identical operation with the same settings and same elements."
            )
            + "\n"
            + _("The number of Operation Passes can be changed extremely easily, ")
            + _("but you cannot change any of the other settings.")
            + "\n"
            + _(
                "Duplicating the Operation gives more flexibility for changing settings, "
            )
            + _("but is far more cumbersome to change the number of duplications ")
            + _("because you need to add and delete the duplicates one by one.")
        )

        self.text_passes.SetToolTip(OPERATION_PASSES_TOOLTIP)
        sizer_passes.Add(self.text_passes, 1, wx.EXPAND, 0)

        sizer_main.Add(sizer_passes, 1, wx.EXPAND, 0)
        sizer_main.Add(self.sizer_kerf, 1, wx.EXPAND, 0)
        sizer_main.Add(self.sizer_coolant, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)

        self.Layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_passes, self.check_passes)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_coolant, self.combo_coolant)

        self.text_passes.SetActionRoutine(self.on_text_passes)
        self.text_kerf.SetActionRoutine(self.on_text_kerf)
        # end wxGlade

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def accepts(self, node):
        return node.type in (
            "op cut",
            "op engrave",
            "op raster",
            "op image",
            "op dots",
        )

    def set_widgets(self, node):
        self.operation = node
        if self.operation is None or not self.accepts(node):
            self.Hide()
            return
        self.has_kerf = bool(self.operation.type == "op cut")
        if self.has_kerf:
            s_label = ""
            s_kerf = "0"
            try:
                ll = Length(self.operation.kerf, digits=2, preferred_units="mm")
                kval = float(ll)
                s_kerf = ll.preferred_length
                if kval < 0:
                    s_label = " " + _("Inward")
                elif kval > 0:
                    s_label = " " + _("Outward")
                else:
                    s_kerf = "0"

            except ValueError:
                pass
            self.text_kerf.SetValue(s_kerf)
            self.kerf_label.SetLabel(s_label)
        if self.operation.passes_custom is not None:
            self.check_passes.SetValue(self.operation.passes_custom)
        if self.operation.passes is not None:
            set_ctrl_value(self.text_passes, str(self.operation.passes))
        on = self.check_passes.GetValue()
        self.text_passes.Enable(on)
        self.sizer_kerf.ShowItems(self.has_kerf)
        self.sizer_kerf.Show(self.has_kerf)
        if hasattr(self.operation, "coolant"):
            show_cool = True
            value = self.operation.coolant
            if value is None:
                value = 0
            self.combo_coolant.SetSelection(value)
        else:
            show_cool = False
        if hasattr(self.context.device, "device_coolant"):
            enable_cool = True
            if self.context.device.device_coolant is None:
                enable_cool = False
        else:
            enable_cool = False
        self.combo_coolant.Enable(enable_cool)
        self.sizer_coolant.ShowItems(show_cool)
        self.sizer_coolant.Show(show_cool)
        self.Layout()
        self.Show()

    def on_combo_coolant(self, event=None):
        value = self.combo_coolant.GetSelection()
        if value < 0:
            value = 0
        self.operation.coolant = value
        self.context.elements.signal(
            "element_property_reload", self.operation, "coolant"
        )
        event.Skip()

    def on_check_passes(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        on = self.check_passes.GetValue()
        self.text_passes.Enable(on)
        self.operation.passes_custom = bool(on)
        self.context.elements.signal(
            "element_property_reload", self.operation, "check_passes"
        )
        event.Skip()

    def on_text_passes(self):
        try:
            value = int(self.text_passes.GetValue())
            if self.operation.passes != value:
                self.operation.passes = value
                self.context.elements.signal(
                    "element_property_reload", self.operation, "text_Passes"
                )
        except ValueError:
            pass

    def on_text_kerf(self):
        try:
            value = float(Length(self.text_kerf.GetValue()))
            if self.operation.kerf != value:
                self.operation.kerf = value
                self.context.elements.signal(
                    "element_property_reload", self.operation, "text_kerf"
                )
        except ValueError:
            pass


# end of class PassesPanel


class InfoPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: PassesPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        sizer_info = StaticBoxSizer(self, wx.ID_ANY, _("Info:"), wx.HORIZONTAL)

        sizer_children = StaticBoxSizer(self, wx.ID_ANY, _("Children:"), wx.HORIZONTAL)
        sizer_time = StaticBoxSizer(
            self, wx.ID_ANY, _("Est. burn-time:"), wx.HORIZONTAL
        )

        self.text_children = TextCtrl(self, wx.ID_ANY, "0", style=wx.TE_READONLY)
        self.text_children.SetMinSize(dip_size(self, 25, -1))
        self.text_children.SetMaxSize(dip_size(self, 55, -1))
        self.text_time = TextCtrl(self, wx.ID_ANY, "---", style=wx.TE_READONLY)
        self.text_time.SetMinSize(dip_size(self, 55, -1))
        self.text_time.SetMaxSize(dip_size(self, 100, -1))
        self.text_children.SetToolTip(
            _("How many elements does this operation contain")
        )
        self.text_time.SetToolTip(_("Estimated time for execution (hh:mm:ss)"))
        self.btn_update = wxButton(self, wx.ID_ANY, _("Calculate"))
        self.btn_update.Bind(wx.EVT_BUTTON, self.on_button_calculate)

        self.btn_recalc = wxButton(self, wx.ID_ANY, _("Re-Classify"))
        self.btn_recalc.Bind(wx.EVT_BUTTON, self.on_button_refresh)

        sizer_children.Add(self.text_children, 1, wx.EXPAND, 0)
        sizer_time.Add(self.text_time, 1, wx.EXPAND, 0)
        sizer_time.Add(self.btn_update, 0, wx.EXPAND, 0)
        sizer_time.AddSpacer(20)
        sizer_time.Add(self.btn_recalc, 0, wx.EXPAND, 0)

        sizer_info.Add(sizer_children, 1, wx.EXPAND, 0)
        sizer_info.Add(sizer_time, 2, wx.EXPAND, 0)

        self.SetSizer(sizer_info)

        self.Layout()

        # end wxGlade

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def on_button_refresh(self, event):
        if not hasattr(self.operation, "classify"):
            return

        infotxt = (
            _("Do you really want to reassign elements to this operation?")
            + "\n"
            + _("Atttention: This will delete all existing assignments!")
        )
        dlg = wx.MessageDialog(
            None, infotxt, "Re-Classify", wx.YES_NO | wx.ICON_WARNING
        )
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_YES:
            with self.context.elements.undoscope("Re-Classify"):
                myop = self.operation
                myop.remove_all_children()
                data = list(self.context.elements.elems())
                reverse = self.context.elements.classify_reverse
                fuzzy = self.context.elements.classify_fuzzy
                fuzzydistance = self.context.elements.classify_fuzzydistance
                if reverse:
                    data = reversed(data)
                for node in data:
                    # result is a tuple containing classified, should_break, feedback
                    result = myop.classify(
                        node,
                        fuzzy=fuzzy,
                        fuzzydistance=fuzzydistance,
                        usedefault=False,
                    )
            # Probably moot as the next command will move the focus away...
            self.refresh_display()
            self.context.signal("tree_changed")
            self.context.signal("activate_single_node", myop)

    def on_button_calculate(self, event):
        self.text_time.SetValue(self.operation.time_estimate())

    def refresh_display(self):
        childs = len(self.operation.children)
        self.text_time.SetValue("---")
        self.text_children.SetValue(str(childs))

    def accepts(self, node):
        return node.type in (
            "op cut",
            "op engrave",
            "op raster",
            "op image",
            "op dots",
        )

    def set_widgets(self, node):
        self.operation = node
        if self.operation is None or not self.accepts(node):
            self.Hide()
            return
        self.refresh_display()
        self.Show()


# end of class InfoPanel


class PanelStartPreference(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: PanelStartPreference.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        sizer_main = StaticBoxSizer(self, wx.ID_ANY, _("Start Preference:"), wx.VERTICAL)

        self.slider_pref_left = wx.Slider(self, wx.ID_ANY, 1, 0, 1)
        sizer_main.Add(self.slider_pref_left, 0, wx.EXPAND, 0)

        sizer_top_display = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_top_display, 1, wx.EXPAND, 0)

        self.slider_pref_top = wx.Slider(self, wx.ID_ANY, 1, 0, 1, style=wx.SL_VERTICAL)
        sizer_top_display.Add(self.slider_pref_top, 0, wx.EXPAND, 0)

        self.display_panel = wx.Panel(self, wx.ID_ANY)
        sizer_top_display.Add(self.display_panel, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)

        self.Layout()

        self.Bind(wx.EVT_SLIDER, self.on_slider_pref_left, self.slider_pref_left)
        self.Bind(wx.EVT_SLIDER, self.on_slider_pref_top, self.slider_pref_top)
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

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    # @signal_listener("element_property_reload")
    def on_element_property_reload(self, *args):
        self.set_widgets(self.operation)
        self._reload_display()

    def accepts(self, node):
        return node.type in (
            "op raster",
            "op image",
        )

    def set_widgets(self, node):
        self.operation = node
        if self.operation is None or not self.accepts(node):
            self.Hide()
            return
        if self.operation.raster_direction in (
            RASTER_CROSSOVER, RASTER_SPIRAL,
        ): # Crossover
            self.Hide()
            return
        validate_raster_settings(self.operation)
        self._toggle_sliders()
        self.refresh_display()
        self.Show()

    def on_display_paint(self, event=None):
        try:
            wx.BufferedPaintDC(self.display_panel, self._Buffer)
        except RuntimeError:
            pass

    def on_display_erase(self, event=None):
        pass

    def set_buffer(self):
        width, height = self.display_panel.Size
        if width <= 0:
            width = 1
        if height <= 0:
            height = 1
        self._Buffer = wx.Bitmap(width, height)

    def on_size(self, event=None):
        self.Layout()
        self.set_buffer()
        self.raster_lines = None
        self.travel_lines = None
        self.direction_lines = None
        wx.CallAfter(self.refresh_in_ui)

    def refresh_display(self):
        if self._Buffer is None:
            self.set_buffer()

        if not wx.IsMainThread():
            wx.CallAfter(self.refresh_in_ui)
        else:
            self.refresh_in_ui()

    def calculate_raster_lines(self):
        w, h = self._Buffer.Size
        if w<10 or h<10: # Ini initialisation phase and too small anyway...
            return

        from_left = self.operation.raster_preference_left
        from_top = self.operation.raster_preference_top

        last = None
        direction = self.operation.raster_direction
        # Rasterline Indicator
        r_start = []
        r_end = []
        # Travel Indicator
        t_start = []
        t_end = []
        # Direction Indicator
        d_start = []
        d_end = []
        factor = 3
        bidirectional = self.operation.bidirectional
        dpi = max(1, self.operation.dpi)

        def dir_arrow_up_down(up: bool):
            d_start.append((w * 0.05, h * 0.05))
            d_end.append((w * 0.05, h * 0.95))
            # Direction Arrow
            d_start.append((w * 0.05, (h * 0.95) if up else (h * 0.05)))
            d_end.append((w * 0.05 + 4, (h * 0.95 - 4) if up else (h * 0.05 + 4)))
            d_start.append((w * 0.05, (h * 0.95) if up else (h * 0.05)))
            d_end.append((w * 0.05 - 4, (h * 0.95 - 4) if up else (h * 0.05 + 4)))

        def dir_arrow_left_right(left: bool):
            # Direction Line
            d_start.append((w * 0.05, h * 0.05))
            d_end.append((w * 0.95, h * 0.05))
            # Direction Arrow
            d_start.append(((w * 0.95) if left else (w * 0.05), h * 0.05))
            d_end.append(((w * 0.95 - 4) if left else (w * 0.05 + 4), h * 0.05 - 4))
            d_start.append(((w * 0.95) if left else (w * 0.05), h * 0.05))
            d_end.append(((w * 0.95 - 4) if left else (w * 0.05 + 4), h * 0.05 + 4))

        if direction in (RASTER_T2B, RASTER_B2T, RASTER_HATCH, RASTER_GREEDY_H, RASTER_CROSSOVER): # Horizontal mode, raster will be built from top to bottom (or vice versa)
            # Direction Line
            if direction in (RASTER_B2T, ):
                # Bottom to Top
                dir_arrow_up_down(False)
                start = int(h * 0.9)
                end = int(h * 0.1)
                step = -1000 / dpi * factor
            else:
                # Top to Bottom or Crosshatch
                dir_arrow_up_down(True)
                start = int(h * 0.1)
                end = int(h * 0.9)
                step = 1000 / dpi * factor
            if step == 0:
                step = abs(start-end) / 10
            while abs(step) > abs(start - end):
                step /= 2
            while abs(start - end) / abs(step) > 100:
                step *= 2

            pos = start
            while min(start, end) <= pos <= max(start, end):
                # Primary Line Horizontal Raster, no need to be fancy and be directional here...
                r_start.append((w * 0.1, pos))
                r_end.append((w * 0.9, pos))

                # Travel segment
                if last is not None:
                    # Travel Lines, from end of last line to next
                    t_start.append((last[0], last[1]))
                    t_end.append((w * 0.1 if from_left else w * 0.9, pos))

                # Arrow segment
                r_start.append((w * 0.9 if from_left else w * 0.1, pos))
                r_end.append((w * 0.9 - 2 if from_left else w * 0.1 + 2, pos - 2))
                last = r_start[-1]
                if bidirectional:
                    from_left = not from_left
                pos += step
        if direction in (RASTER_R2L, RASTER_L2R, RASTER_HATCH, RASTER_GREEDY_V, RASTER_CROSSOVER): # Vertical mode, raster will be built from left to right (or vice versa)
            if direction in (RASTER_R2L, ):
                # Right to Left
                dir_arrow_left_right(False)
                start = int(w * 0.9)
                end = int(w * 0.1)
                step = -1000 / dpi * factor
            else:
                # Left to Right or Crosshatch
                dir_arrow_left_right(True)
                start = int(w * 0.1)
                end = int(w * 0.9)
                step = 1000 / dpi * factor
            if step == 0:
                step = abs(start-end) / 10
            while abs(step) > abs(start - end):
                step /= 2
            while abs(start - end) / abs(step) > 100:
                step *= 2

            pos = start
            while min(start, end) <= pos <= max(start, end):
                # Primary Line Vertical Raster.
                r_start.append((pos, h * 0.1))
                r_end.append((pos, h * 0.9))

                # Travel Segment
                if last is not None:
                    # Travel Lines
                    t_start.append((last[0], last[1]))
                    t_end.append((pos, h * 0.1 if from_top else h * 0.9))

                # Arrow Segment
                r_start.append((pos, h * 0.9 if from_top else h * 0.1))
                r_end.append((pos - 2, (h * 0.9) - 2 if from_top else (h * 0.1) + 2))

                last = r_start[-1]
                if bidirectional:
                    from_top = not from_top
                pos += step
        self.raster_lines = r_start, r_end
        self.travel_lines = t_start, t_end
        self.direction_lines = d_start, d_end

    def refresh_in_ui(self):
        """Performs redrawing of the data in the UI thread."""
        try:
            visible = self.Shown
        except RuntimeError:
            # May have already been deleted....
            return
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        if visible:
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
        direction = self.operation.raster_direction
        prefer_min_y = self.operation.raster_preference_top
        prefer_min_x = self.operation.raster_preference_left

        self.slider_pref_left.Enable(direction in (RASTER_T2B, RASTER_B2T, RASTER_GREEDY_H, RASTER_GREEDY_V))
        self.slider_pref_top.Enable(direction in (RASTER_L2R, RASTER_R2L, RASTER_GREEDY_H, RASTER_GREEDY_V))
        self.slider_pref_left.SetValue(0 if prefer_min_x else 1)
        self.slider_pref_top.SetValue(0 if prefer_min_y else 1)


    def _reload_display(self):
        self.raster_lines = None
        self.travel_lines = None
        self.refresh_display()

    def on_slider_pref_left(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        value = self.slider_pref_left.GetValue() == 0
        if self.operation.raster_preference_left != value:
            self.operation.raster_preference_left = value
            self._reload_display()
            self.context.elements.signal(
                "element_property_update", self.operation, "slider_top"
            )

    def on_slider_pref_top(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        value = self.slider_pref_top.GetValue() == 0
        if self.operation.raster_preference_top != value:
            self.operation.raster_preference_top = value
            self._reload_display()
            self.context.elements.signal(
                "element_property_update", self.operation, "slider_left"
            )
# end of class PanelStartPreference


class RasterSettingsPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: RasterSettingsPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node
        iconsize = dip_size(self, 30, 20)
        bmpsize = min(iconsize[0], iconsize[1]) * self.context.root.bitmap_correction_scale

        raster_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Raster:"), wx.VERTICAL)
        param_sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer_dpi = StaticBoxSizer(self, wx.ID_ANY, _("DPI:"), wx.HORIZONTAL)
        param_sizer.Add(sizer_dpi, 1, wx.EXPAND, 0)
        self.check_overrule_dpi = wxCheckBox(self, wx.ID_ANY)
        self.check_overrule_dpi.SetToolTip(_("Overrules image dpi settings and uses this value instead"))
        self.text_dpi = TextCtrl(
            self,
            wx.ID_ANY,
            "500",
            limited=True,
            check="int",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_dpi.set_default_values(
            [
                (str(dpi), _("Set DPI to {value}").format(value=str(dpi)))
                for dpi in self.context.device.view.get_sensible_dpi_values()
            ]
        )
        self.text_dpi.set_error_level(1, 100000)
        OPERATION_DPI_TOOLTIP = (
            _('In a raster engrave, the step size is the distance between raster lines in 1/1000" ') +
            _("and also the number of raster dots that get combined together.") + "\n" +
            _('Because the laser dot is >> 1/1000" in diameter, at step 1 the raster lines overlap a lot, ') +
            _("and consequently you can raster with steps > 1 without leaving gaps between the lines.") + "\n" +
            _("The step size before you get gaps will depend on your focus and the size of your laser dot.") + "\n"+
            _("Step size > 1 reduces the laser energy delivered by the same factor, so you may need to increase ") +
            _("power equivalently with a higher front-panel power, a higher PPI or by rastering at a slower speed.") + "\n" +
            _("Step size > 1 also turns the laser on and off fewer times, and combined with a slower speed") +
            _("this can prevent your laser from stuttering.")
        )
        self.text_dpi.SetToolTip(OPERATION_DPI_TOOLTIP)
        sizer_dpi.Add(self.check_overrule_dpi, 0, wx.EXPAND, 0)
        sizer_dpi.Add(self.text_dpi, 1, wx.EXPAND, 0)

        sizer_optimize = StaticBoxSizer(self, wx.ID_ANY, _("Optimize movement:"), wx.HORIZONTAL)
        self.check_laserdot = wxCheckBox(self, wx.ID_ANY, _("Consider laserdot") )
        self.check_laserdot.SetToolTip(
            _("A laser dot has a certain diameter, so for high dpi values, lines will overlap a lot.") + "\n" +
            _("Active: don't burn pixels already overlapped") + "\n" +
            _("Inactive: burn all pixels regardless of a possible overlap.")
        )
        sizer_optimize.Add(self.check_laserdot, 1, wx.EXPAND, 0)
        param_sizer.Add(sizer_optimize, 1, wx.EXPAND, 0)

        self.sizer_grayscale = StaticBoxSizer(self, wx.ID_ANY, _("Override black/white image:"), wx.HORIZONTAL)
        param_sizer.Add(self.sizer_grayscale, 1, wx.EXPAND, 0)
        self.check_grayscale = wxCheckBox(self, wx.ID_ANY, _("Use grayscale instead") )
        self.check_grayscale.SetToolTip(
            _("Usually a raster will be created as a grayscale picture and the burn-power of a pixel will depend on its darkness.") + "\n" +
            _("If you uncheck this value then every non-white pixel (even very light ones) will become black and will be burned at full power.")
        )
        self.sizer_grayscale.Add(self.check_grayscale, 1, wx.EXPAND, 0)

        sizer_overscan = StaticBoxSizer(self, wx.ID_ANY, _("Overscan:"), wx.HORIZONTAL)
        param_sizer.Add(sizer_overscan, 1, wx.EXPAND, 0)
        self.text_overscan = TextCtrl(
            self,
            wx.ID_ANY,
            "0mm",
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_overscan.SetToolTip(_("Padding that will be added at the end of a scanline to allow the laser to slow down"))
        sizer_overscan.Add(self.text_overscan, 1, wx.EXPAND, 0)

        raster_sizer.Add(param_sizer, 0, wx.EXPAND, 0)

        sizer_4 = StaticBoxSizer(self, wx.ID_ANY, _("Direction:"), wx.HORIZONTAL)
        raster_sizer.Add(sizer_4, 0, wx.EXPAND, 0)
        self.raster_terms = [
            (RASTER_T2B, "Top To Bottom"),
            (RASTER_B2T, "Bottom To Top"),
            (RASTER_R2L, "Right To Left"),
            (RASTER_L2R, "Left To Right"),
            (RASTER_HATCH, "Crosshatch"),
            (RASTER_GREEDY_H, "Greedy horizontal"),
            (RASTER_GREEDY_V, "Greedy vertical"),
            (RASTER_CROSSOVER, "Crossover"),
            (RASTER_SPIRAL, "Spiral"),
        ]
        # Look for registered raster (image) preprocessors,
        # these are routines that take one image as parameter
        # and deliver a set of (result image, method (aka raster_direction) )
        # that will be dealt with independently
        # The registered datastructure is (rasterid, description, method)
        self.raster_terms.extend(
            (key, description)
            for key, description, method in self.context.kernel.lookup_all(
                "raster_preprocessor/.*"
            )
        )
        # Add a couple of testcases
        # test_methods = (
        #     (-1, "Test: Horizontal Rectangle"),
        #     (-2, "Test: Vertical Rectangle"),
        #     (-3, "Test: Horizontal Snake"),
        #     (-4, "Test: Vertical Snake"),
        #     (-5,  "Test: Spiral"),
        # )
        # self.raster_terms.extend(test_methods)

        self.raster_methods = [ key for key, info in self.raster_terms ]

        self.combo_raster_direction = wxComboBox(
            self,
            wx.ID_ANY,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        OPERATION_RASTERDIRECTION_TOOLTIP = (
            _("Direction to perform a raster")
            + "\n"
            + _(
                "Normally you would raster in an X-direction and select Top-to-Bottom (T2B) or Bottom-to-Top (B2T)."
            )
            + "\n"
            + _(
                "This is because rastering in the X-direction involve moving only the laser head which is relatively low mass."
            )
            + "\n"
            + _(
                "Rastering in the Y-direction (Left-to-Right or Right-to-Left) involves moving not only the laser head "
            )
            + _(
                "but additionally the entire x-axis gantry assembly including the stepper motor, mirror and the gantry itself."
            )
            + "\n"
            + _(
                "This total mass is much greater, acceleration therefore needs to be much slower, "
            )
            + _(
                "and allow for space at each end of the raster to reverse direction the speed has to be much slower."
            )
        )

        self.combo_raster_direction.SetToolTip(OPERATION_RASTERDIRECTION_TOOLTIP)
        # OSX needs an early population, as events might occur before pane_show has been called
        self.fill_raster_combo()
        self.combo_raster_direction.SetSelection(0)
        sizer_4.Add(self.combo_raster_direction, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.btn_instruction = wxStaticBitmap(self, wx.ID_ANY)
        self.btn_instruction.SetBitmap(icon_letter_h.GetBitmap(resize=bmpsize))
        self.btn_instruction.SetToolTip(_("Quick info about the available modes"))
        sizer_4.Add(self.btn_instruction, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.radio_raster_swing = wxRadioBox(
            self,
            wx.ID_ANY,
            _("Directional Raster:"),
            choices=[_("Unidirectional"), _("Bidirectional")],
            majorDimension=1,
            style=wx.RA_SPECIFY_ROWS,
        )
        OPERATION_RASTERSWING_TOOLTIP = (
            _("Raster on forward and backswing or only forward swing?")
            + "\n"
            + _(
                "Rastering only on forward swings will double the time required to complete the raster."
            )
            + "\n"
            + _(
                "It seems doubtful that there will be significant quality benefits from rastering in one direction."
            )
        )
        self.radio_raster_swing.SetToolTip(OPERATION_RASTERSWING_TOOLTIP)
        self.radio_raster_swing.SetSelection(0)
        raster_sizer.Add(self.radio_raster_swing, 0, wx.EXPAND, 0)

        self.panel_start = PanelStartPreference(
            self, wx.ID_ANY, context=context, node=node
        )
        raster_sizer.Add(self.panel_start, 1, wx.EXPAND, 0)

        self.SetSizer(raster_sizer)

        self.Layout()
        self.Bind(wx.EVT_CHECKBOX, self.on_overrule, self.check_overrule_dpi)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_grayscale, self.check_grayscale)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_laserdot, self.check_laserdot)
        self.text_dpi.SetActionRoutine(self.on_text_dpi)
        self.text_overscan.SetActionRoutine(self.on_text_overscan)

        self.Bind(
            wx.EVT_COMBOBOX, self.on_combo_raster_direction, self.combo_raster_direction
        )
        self.Bind(wx.EVT_RADIOBOX, self.on_radio_directional, self.radio_raster_swing)
        self.btn_instruction.Bind(wx.EVT_LEFT_DOWN, self.on_raster_help)

    def fill_raster_combo(self):
        unsupported = ()
        if hasattr(self.context.device, "get_raster_instructions"):
            instructions = self.context.device.get_raster_instructions()
            unsupported = instructions.get("unsupported_opt", ())
        # print (f"fill raster called: {unsupported}")
        self.raster_methods = [ key for key, info in self.raster_terms if key not in unsupported ]
        choices = [ info for key, info in self.raster_terms if key not in unsupported ]
        self.combo_raster_direction.Clear()
        self.combo_raster_direction.SetItems(choices)
        if self.operation is not None:
            self.set_raster_combo()

    @lookup_listener("service/device/active")
    def on_device_update(self, *args):
        if self.Shown():
            self.fill_raster_combo()

    def pane_hide(self):
        self.panel_start.pane_hide()

    def pane_show(self):
        self.fill_raster_combo()
        self.panel_start.pane_show()

    def accepts(self, node):
        return node.type in (
            "op raster",
            "op image",
        )

    def set_widgets(self, node):
        self.operation = node
        if self.operation is None or not self.accepts(node):
            self.Hide()
            return
        if self.operation.dpi is not None:
            dpi = int(self.operation.dpi)
            set_ctrl_value(self.text_dpi, str(dpi))
        if hasattr(self.operation, "use_grayscale"):
            self.sizer_grayscale.ShowItems(True)

            self.check_grayscale.SetValue(self.operation.use_grayscale)
        else:
            self.sizer_grayscale.ShowItems(False)
        if hasattr(self.operation, "overrule_dpi"):
            self.check_overrule_dpi.Show(True)
            overrule = self.operation.overrule_dpi
            if overrule is None:
                overrule = False
            self.check_overrule_dpi.SetValue(overrule)
            self.text_dpi.Enable(overrule)
        else:
            self.check_overrule_dpi.Show(False)
            self.text_dpi.Enable(True)
        if self.operation.overscan is not None:
            set_ctrl_value(self.text_overscan, str(self.operation.overscan))
        self.set_raster_combo()
        if self.operation.bidirectional is not None:
            self.radio_raster_swing.SetSelection(self.operation.bidirectional)
        self.check_laserdot.SetValue(self.operation.consider_laserspot)
        # Hide it for now...
        # self.check_laserdot.Show(False)
        self.allow_controls_according_to_optimization()
        self.Show()

    def allow_controls_according_to_optimization(self):
        direction = self.operation.raster_direction
        overscan_okay = direction not in (RASTER_GREEDY_H, RASTER_GREEDY_V)
        swing_okay = direction in (RASTER_B2T, RASTER_T2B, RASTER_R2L, RASTER_L2R, RASTER_HATCH)
        self.text_overscan.Enable(overscan_okay)
        self.radio_raster_swing.Enable(swing_okay)
        if not swing_okay:
            self.radio_raster_swing.SetSelection(True)

    def on_overrule(self, event):
        if self.operation is None or not hasattr(self.operation, "overrule_dpi"):
            return
        b = self.check_overrule_dpi.GetValue()
        self.text_dpi.Enable(b)
        if self.operation.overrule_dpi != b:
            self.operation.overrule_dpi = b
            self.context.signal(
                "element_property_reload", self.operation, "text_dpi"
            )
            self.context.signal("warn_state_update")

    def on_text_dpi(self):
        try:
            value = int(self.text_dpi.GetValue())
        except ValueError as e:
            # print (e)
            return
        if self.operation.dpi != value:
            self.operation.dpi = value
            self.context.signal(
                "element_property_reload", self.operation, "text_dpi"
            )
            self.context.signal("warn_state_update")

    def on_check_grayscale(self, event):
        value = self.check_grayscale.GetValue()
        if self.operation.use_grayscale != value:
            self.operation.use_grayscale = value
            self.context.elements.signal("element_property_reload", self.operation)

    def on_check_laserdot(self, event):
        value = self.check_laserdot.GetValue()
        if self.operation.consider_laserspot != value:
            self.operation.consider_laserspot = value
            self.context.elements.signal("element_property_reload", self.operation)

    def on_text_overscan(self):
        try:
            v = Length(
                self.text_overscan.GetValue(),
                unitless=UNITS_PER_MM,
                preferred_units="mm",
                digits=4,
            )
        except ValueError:
            return
        # print ("Start overscan=%s - target=%s" % (start_text, str(v.preferred_length)))
        value = v.preferred_length
        if v._amount < 1e-10:
            value = 0
        if self.operation.overscan != value:
            self.operation.overscan = value
            self.context.elements.signal(
                "element_property_reload", self.operation, "text_overscan"
            )

    def on_combo_raster_direction(self, event=None):
        idx = self.combo_raster_direction.GetSelection()
        if idx < 0:
            return
        value = self.raster_methods[idx]

        if (self.operation.raster_direction != value ):
            self.operation.raster_direction = value
            validate_raster_settings(self.operation)

            self.context.raster_direction = self.operation.raster_direction
            self.context.elements.signal(
                "element_property_reload", self.operation, "combo_raster"
            )
        event.Skip()

    def on_radio_directional(self, event=None):
        self.operation.bidirectional = bool(self.radio_raster_swing.GetSelection())
        self.context.elements.signal(
            "element_property_reload", self.operation, "radio_direct"
        )
        event.Skip()

    def set_raster_combo(self):
        idx = -1
        if self.operation is not None and self.operation.raster_direction is not None:
            try:
                idx = self.raster_methods.index(self.operation.raster_direction)
            except ValueError:
                idx = 0
        self.combo_raster_direction.SetSelection(idx)

    def on_raster_help(self, event):
        unsupported = ()
        if hasattr(self.context.device, "get_raster_instructions"):
            instructions = self.context.device.get_raster_instructions()
            unsupported = instructions.get("unsupported_opt", ())

        inform = {
            RASTER_T2B: _("- Top To Bottom: follows the picture line by line starting at the top"),
            RASTER_B2T: _("- Bottom To Top: follows the picture line by line starting at the bottom"),
            RASTER_R2L: _("- Right To Left: follows the picture column by column starting at the right side"),
            RASTER_L2R: _("- Left To Right: follows the picture column by column starting at the left side"),
            RASTER_HATCH: _("- Crosshatch: Makes two passes: one horizontally then another one vertically"),
            RASTER_GREEDY_H:
                _("- Greedy horizontal: Instead of following a complete line,") + "\n" +
                _("  this will choose the nearest to be drawn segment,") + "\n" +
                _("  lasering these segments with vertical lines.") + "\n" +
                _("  Usually much faster on an image with a lot of white pixels."),
            RASTER_GREEDY_V:
                _("- Greedy vertical: Instead of following a complete line,") + "\n" +
                _("  this will choose the nearest to be drawn segment,") + "\n" +
                _("  lasering these segments with vertical lines.") + "\n" +
                _("  Usually much faster on an image with a lot of white pixels."),
            RASTER_CROSSOVER:
                _("- Crossover: Sweeping over the image drawing first all lines") + "\n" +
                _("  with a majority of black pixels and then drawing the columns") + "\n" +
                _("  where we have a majority.") + "\n" +
                _("  Usually much faster on an image with a lot of white pixels."),
            RASTER_SPIRAL:
                _("- Spiral: Starting in the center spiralling outwards"),
        }
        lines = [_("You can choose from the following modes to laser an image:")]
        lines.extend( [info for key, info in inform.items() if key not in unsupported] )

        message = "\n".join(lines)
        wx.MessageBox(
            caption=_("Help"),
            message=message,
            style=wx.OK|wx.ICON_INFORMATION
        )

# end of class RasterSettingsPanel


class DwellSettingsPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: PassesPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        sizer_passes = StaticBoxSizer(
            self, wx.ID_ANY, _("Dwell Time: (ms)"), wx.HORIZONTAL
        )

        self.text_dwelltime = TextCtrl(
            self,
            wx.ID_ANY,
            "1.0",
            limited=True,
            style=wx.TE_PROCESS_ENTER,
            check="float",
        )
        self.text_dwelltime.SetToolTip(
            _("Dwell time (ms) at each location in the sequence")
        )
        sizer_passes.Add(self.text_dwelltime, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_passes)

        self.Layout()

        self.text_dwelltime.SetActionRoutine(self.on_text_dwelltime)
        # end wxGlade

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def accepts(self, node):
        return node.type in ("op dots",)

    def set_widgets(self, node):
        self.operation = node
        if self.operation is None or not self.accepts(node):
            self.Hide()
            return
        set_ctrl_value(self.text_dwelltime, str(self.operation.dwell_time))
        self.Show()

    def on_text_dwelltime(self):
        try:
            value = float(self.text_dwelltime.GetValue())
            if self.operation.dwell_time != value:
                self.operation.dwell_time = value
                self.context.elements.signal(
                    "element_property_reload", self.operation, "text_dwell"
                )
        except ValueError:
            pass


# end of class PassesPanel


class ParameterPanel(ScrolledPanel):
    name = _("Properties")
    priority = -1

    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: ParameterPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node
        self.panels = []
        self.SetHelpText("operationproperty")

        param_sizer = wx.BoxSizer(wx.VERTICAL)

        self.id_panel = IdPanel(
            self,
            wx.ID_ANY,
            context=context,
            node=node,
            showid=True,
        )
        param_sizer.Add(self.id_panel, 0, wx.EXPAND, 0)
        self.panels.append(self.id_panel)

        self.layer_panel = LayerSettingPanel(
            self, wx.ID_ANY, context=context, node=node
        )
        param_sizer.Add(self.layer_panel, 0, wx.EXPAND, 0)
        self.panels.append(self.layer_panel)

        self.speedppi_panel = SpeedPpiPanel(self, wx.ID_ANY, context=context, node=node)
        param_sizer.Add(self.speedppi_panel, 0, wx.EXPAND, 0)
        self.panels.append(self.speedppi_panel)

        self.passes_panel = PassesPanel(self, wx.ID_ANY, context=context, node=node)
        param_sizer.Add(self.passes_panel, 0, wx.EXPAND, 0)
        self.panels.append(self.passes_panel)

        self.raster_panel = RasterSettingsPanel(
            self, wx.ID_ANY, context=context, node=node
        )
        param_sizer.Add(self.raster_panel, 1, wx.EXPAND, 0)
        self.panels.append(self.raster_panel)

        self.dwell_panel = DwellSettingsPanel(
            self, wx.ID_ANY, context=context, node=node
        )
        param_sizer.Add(self.dwell_panel, 0, wx.EXPAND, 0)
        self.panels.append(self.dwell_panel)

        self.info_panel = InfoPanel(self, wx.ID_ANY, context=context, node=node)
        param_sizer.Add(self.info_panel, 0, wx.EXPAND, 0)
        self.panels.append(self.info_panel)

        self.SetSizer(param_sizer)

        self.Layout()
        # end wxGlade

    @signal_listener("power_percent")
    @signal_listener("speed_min")
    @lookup_listener("service/device/active")
    def on_device_update(self, *args):
        self.speedppi_panel.on_device_update()

    @signal_listener("element_property_reload")
    def on_element_property_reload(self, origin=None, *args):
        # Is this something I should care about?
        # element_property_reload provides a list of nodes that are affected
        # if self.operation isn't one of them, then we just let it slip
        for_me = False
        if len(args) > 0:
            element = args[0]
            if isinstance(element, (tuple, list)):
                for node in element:
                    if node == self.operation:
                        for_me = True
                        break
            elif self.operation == element:
                for_me = True
        if not for_me:
            return

        # if origin is None:
        #     print ("EPR called with no origin")
        # else:
        #     print ("EPR called from:", args)
        try:
            self.raster_panel.panel_start.on_element_property_reload(*args)
        except AttributeError:
            pass
        self.set_widgets(self.operation)
        self.Layout()

    def set_widgets(self, node):
        try:
            self.operation = node
            for panel in self.panels:
                panel.set_widgets(node)
        except RuntimeError:
            # Already deleted
            return

    def pane_hide(self):
        for panel in self.panels:
            panel.pane_hide()

    def pane_show(self):
        for panel in self.panels:
            panel.pane_show()


# end of class ParameterPanel
