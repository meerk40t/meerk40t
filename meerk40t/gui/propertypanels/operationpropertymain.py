import wx

from meerk40t.gui.wxutils import ScrolledPanel, StaticBoxSizer
from meerk40t.kernel import signal_listener

from ...core.units import UNITS_PER_MM, Length
from ...svgelements import Angle, Color, Matrix
from ..laserrender import swizzlecolor
from ..wxutils import TextCtrl, set_ctrl_value
from .attributes import IdPanel

_ = wx.GetTranslation

# OPERATION_TYPE_TOOLTIP = _(
#     """Operation Type

# Cut & Engrave are vector operations, Raster and Image are raster operations.

# Cut and Engrave operations are essentially the same except that for a Cut operation with Cut Outer Paths last, only closed Paths in Cut operations are considered as being Outer-most."""
# )


class LayerSettingPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        layer_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Layer:"), wx.HORIZONTAL)

        self.button_layer_color = wx.Button(self, wx.ID_ANY, "")
        self.button_layer_color.SetBackgroundColour(wx.Colour(0, 0, 0))
        COLOR_TOOLTIP = _(
            "Change/View color of this layer. When Meerk40t classifies elements to operations,"
        ) + _("this exact color is used to match elements to this operation.")

        self.button_layer_color.SetToolTip(COLOR_TOOLTIP)
        layer_sizer.Add(self.button_layer_color, 0, wx.EXPAND, 0)
        h_classify_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Classification"), wx.HORIZONTAL
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
            self.checkbox_stroke = wx.CheckBox(self, wx.ID_ANY, _("Stroke"))
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
            self.checkbox_fill = wx.CheckBox(self, wx.ID_ANY, _("Fill"))
            self.checkbox_fill.SetToolTip(
                _("Look at the stroke color to restrict classification.")
                + rastertooltip
            )
            self.checkbox_fill.SetValue(1 if self.has_fill else 0)
            h_classify_sizer.Add(self.checkbox_fill, 1, 0, 0)
            self.Bind(wx.EVT_CHECKBOX, self.on_check_fill, self.checkbox_fill)
        except AttributeError:
            self.has_fill = None

        self.checkbox_stop = wx.CheckBox(self, wx.ID_ANY, _("Stop"))
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

        # self.combo_type = wx.ComboBox(
        #     self,
        #     wx.ID_ANY,
        #     choices=["Engrave", "Cut", "Raster", "Image", "Hatch", "Dots"],
        #     style=wx.CB_DROPDOWN,
        # )
        # self.combo_type.SetToolTip(OPERATION_TYPE_TOOLTIP)
        # self.combo_type.SetSelection(0)
        # layer_sizer.Add(self.combo_type, 1, 0, 0)

        self.checkbox_output = wx.CheckBox(self, wx.ID_ANY, _("Enable"))
        self.checkbox_output.SetToolTip(
            _("Enable this operation for inclusion in Execute Job.")
        )
        self.checkbox_output.SetValue(1)
        h_property_sizer.Add(self.checkbox_output, 1, 0, 0)

        self.checkbox_visible = wx.CheckBox(self, wx.ID_ANY, _("Visible"))
        self.checkbox_visible.SetToolTip(
            _("Hide all contained elements on scene if not set.")
        )
        self.checkbox_visible.SetValue(1)
        self.checkbox_visible.Enable(False)
        h_property_sizer.Add(self.checkbox_visible, 1, 0, 0)

        self.checkbox_default = wx.CheckBox(self, wx.ID_ANY, _("Default"))
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
            "op hatch",
        )

    def set_widgets(self, node):
        self.operation = node
        if self.operation is None or not self.accepts(node):
            self.Hide()
            return
        op = self.operation.type
        # if op == "op engrave":
        #     self.combo_type.SetSelection(0)
        # elif op == "op cut":
        #     self.combo_type.SetSelection(1)
        # elif op == "op raster":
        #     self.combo_type.SetSelection(2)
        # elif op == "op image":
        #     self.combo_type.SetSelection(3)
        # elif op == "op hatch":
        #     self.combo_type.SetSelection(4)
        # elif op == "op dots":
        #     self.combo_type.SetSelection(5)
        #     for m in self.GetParent().Children:
        #         if isinstance(m, wx.Window):
        #             m.Hide()
        #     return
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
                pass
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
                self.operation.type in ("op engrave", "op cut", "op hatch")
                and len(self.operation.children) > 0
                and (candidate_fill or candidate_stroke)
            ):
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
                    changed = []
                    for refnode in self.operation.children:
                        cnode = refnode.node
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

    # def on_combo_operation(
    #     self, event=None
    # ):  # wxGlade: OperationProperty.<event_handler>
    #
    #     select = self.combo_type.GetSelection()
    #     if select == 0:
    #         self.operation.replace_node(self.operation.settings, type="op engrave")
    #     elif select == 1:
    #         self.operation.replace_node(self.operation.settings, type="op cut")
    #     elif select == 2:
    #         self.operation.replace_node(self.operation.settings, type="op raster")
    #     elif select == 3:
    #         self.operation.replace_node(self.operation.settings, type="op image")
    #     elif select == 4:
    #         self.operation.replace_node(self.operation.settings, type="op hatch")
    #     elif select == 5:
    #         self.operation.replace_node(self.operation.settings, type="op dots")
    #     self.context.elements.signal("element_property_reload", self.operation)

    def on_check_output(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        if self.operation.output != bool(self.checkbox_output.GetValue()):
            self.operation.output = bool(self.checkbox_output.GetValue())
            self.context.elements.signal(
                "element_property_reload", self.operation, "check_output"
            )
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
        self.operation = node
        speed_min = None
        speed_max = None
        power_min = None
        power_max = None

        op = node.type
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
        # print (f"op='{op}', power={power_min}-{power_max}, speed={speed_min}-{speed_max}")
        speed_power_sizer = wx.BoxSizer(wx.HORIZONTAL)

        speed_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Speed (mm/s)"), wx.HORIZONTAL)
        speed_power_sizer.Add(speed_sizer, 1, wx.EXPAND, 0)

        self.text_speed = TextCtrl(
            self,
            wx.ID_ANY,
            "20.0",
            limited=True,
            check="float",
            style=wx.TE_PROCESS_ENTER,
            nonzero=True,
        )
        self.text_speed.set_error_level(0, None)
        self.text_speed.set_warn_level(speed_min, speed_max)
        OPERATION_SPEED_TOOLTIP = (
            _("Speed at which the head moves in mm/s.")
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
        speed_sizer.Add(self.text_speed, 1, wx.EXPAND, 0)

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
        self.text_power.SetToolTip(OPERATION_POWER_TOOLTIP)
        self.power_sizer.Add(self.text_power, 1, wx.EXPAND, 0)

        trailer_text = wx.StaticText(self, id=wx.ID_ANY, label=_("/1000"))
        self.power_sizer.Add(trailer_text, 0, wx.ALIGN_CENTER_VERTICAL, 0)

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
        pass

    def accepts(self, node):
        return node.type in (
            "op cut",
            "op engrave",
            "op raster",
            "op image",
            "op dots",
            "op hatch",
        )

    def set_widgets(self, node):
        self.operation = node
        if self.operation is None or not self.accepts(node):
            self.Hide()
            return
        if self.operation.speed is not None:
            set_ctrl_value(self.text_speed, str(self.operation.speed))
        if self.operation.power is not None:
            set_ctrl_value(self.text_power, str(self.operation.power))
            self.update_power_label()
        if self.operation.frequency is not None and self.text_frequency:
            set_ctrl_value(self.text_frequency, str(self.operation.frequency))
        self.Show()

    def on_text_speed(self):  # wxGlade: OperationProperty.<event_handler>
        try:
            value = float(self.text_speed.GetValue())
            if self.operation.speed != value:
                self.operation.speed = value
                self.context.elements.signal(
                    "element_property_reload", self.operation, "text_speed"
                )
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
        try:
            value = float(self.text_power.GetValue())
            self.power_sizer.SetLabel(_("Power (ppi)") + f" ({value/10:.1f}%)")
        except ValueError:
            return

    def on_text_power(self):
        try:
            value = float(self.text_power.GetValue())
            if self.operation.power != value:
                self.operation.power = value
                self.update_power_label()
                self.context.elements.signal(
                    "element_property_reload", self.operation, "text_power"
                )
        except ValueError:
            return


# end of class SpeedPpiPanel


class PassesPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: PassesPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
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
        self.kerf_label = wx.StaticText(self, wx.ID_ANY, "")
        self.sizer_kerf.Add(self.text_kerf, 1, wx.EXPAND, 0)
        self.sizer_kerf.Add(self.kerf_label, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_passes = StaticBoxSizer(self, wx.ID_ANY, _("Passes:"), wx.HORIZONTAL)

        self.check_passes = wx.CheckBox(self, wx.ID_ANY, _("Passes"))
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

        self.SetSizer(sizer_main)

        self.Layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_passes, self.check_passes)

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
            "op hatch",
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
        self.Layout()
        self.Show()

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

        self.text_children = wx.TextCtrl(self, wx.ID_ANY, "0", style=wx.TE_READONLY)
        self.text_children.SetMinSize((25, -1))
        self.text_children.SetMaxSize((55, -1))
        self.text_time = wx.TextCtrl(self, wx.ID_ANY, "---", style=wx.TE_READONLY)
        self.text_time.SetMinSize((55, -1))
        self.text_time.SetMaxSize((100, -1))
        self.text_children.SetToolTip(
            _("How many elements does this operation contain")
        )
        self.text_time.SetToolTip(_("Estimated time for execution (hh:mm:ss)"))
        self.btn_update = wx.Button(self, wx.ID_ANY, _("Calculate"))
        self.btn_update.Bind(wx.EVT_BUTTON, self.on_button_calculate)

        self.btn_recalc = wx.Button(self, wx.ID_ANY, _("Re-Classify"))
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
            "op hatch",
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

        sizer_2 = StaticBoxSizer(self, wx.ID_ANY, _("Start Preference:"), wx.VERTICAL)

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

    # @signal_listener("element_property_reload")
    def on_element_property_reload(self, *args):
        self._toggle_sliders()
        self.raster_lines = None
        self.travel_lines = None
        self.refresh_display()

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
        if self.operation.raster_preference_top is not None:
            self.slider_top.SetValue(self.operation.raster_preference_top + 1)
        if self.operation.raster_preference_left is not None:
            self.slider_left.SetValue(self.operation.raster_preference_left + 1)
        if self.operation.raster_preference_right is not None:
            self.slider_right.SetValue(self.operation.raster_preference_right + 1)
        if self.operation.raster_preference_bottom is not None:
            self.slider_bottom.SetValue(self.operation.raster_preference_bottom + 1)
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
        wx.CallAfter(self.refresh_in_ui)

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
        direction = self.operation.raster_direction
        r_start = list()
        r_end = list()
        t_start = list()
        t_end = list()
        d_start = list()
        d_end = list()
        factor = 3
        bidirectional = self.operation.bidirectional
        dpi = self.operation.dpi
        if dpi <= 1:
            dpi = 1

        if direction == 0 or direction == 1 or direction == 4:
            # Direction Line
            d_start.append((w * 0.05, h * 0.05))
            d_end.append((w * 0.05, h * 0.95))
            if direction == 1:
                # Bottom to Top
                if self.operation.raster_preference_bottom > 0:
                    # if bottom preference is left
                    right = False
                # Direction Arrow
                d_start.append((w * 0.05, h * 0.05))
                d_end.append((w * 0.05 + 4, h * 0.05 + 4))
                d_start.append((w * 0.05, h * 0.05))
                d_end.append((w * 0.05 - 4, h * 0.05 + 4))
                start = int(h * 0.9)
                end = int(h * 0.1)
                step = -1000 / dpi * factor
            else:
                # Top to Bottom or Crosshatch
                if self.operation.raster_preference_top > 0:
                    # if top preference is left
                    right = False
                d_start.append((w * 0.05, h * 0.95))
                d_end.append((w * 0.05 + 4, h * 0.95 - 4))
                d_start.append((w * 0.05, h * 0.95))
                d_end.append((w * 0.05 - 4, h * 0.95 - 4))
                start = int(h * 0.1)
                end = int(h * 0.9)
                step = 1000 / dpi * factor
            pos = start
            while min(start, end) <= pos <= max(start, end):
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
                if bidirectional:
                    right = not right
                pos += step
        if direction == 2 or direction == 3 or direction == 4:
            # Direction Line
            d_start.append((w * 0.05, h * 0.05))
            d_end.append((w * 0.95, h * 0.05))
            if direction == 2:
                # Right to Left
                if self.operation.raster_preference_right > 0:
                    # if right preference is bottom
                    top = False
                # Direction Arrow
                d_start.append((w * 0.05, h * 0.05))
                d_end.append((w * 0.05 + 4, h * 0.05 + 4))
                d_start.append((w * 0.05, h * 0.05))
                d_end.append((w * 0.05 + 4, h * 0.05 - 4))
                start = int(w * 0.9)
                end = int(w * 0.1)
                step = -1000 / dpi * factor
            else:
                # Left to Right or Crosshatch
                if self.operation.raster_preference_left > 0:
                    # if left preference is bottom
                    top = False
                d_start.append((w * 0.95, h * 0.05))
                d_end.append((w * 0.95 - 4, h * 0.05 + 4))
                d_start.append((w * 0.95, h * 0.05))
                d_end.append((w * 0.95 - 4, h * 0.05 - 4))
                start = int(w * 0.1)
                end = int(w * 0.9)
                step = 1000 / dpi * factor
            pos = start
            while min(start, end) <= pos <= max(start, end):
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
                if bidirectional:
                    top = not top
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
        if self.toggle_sliders:
            direction = self.operation.raster_direction
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
        if self.operation.raster_preference_top != self.slider_top.GetValue() - 1:
            self.operation.raster_preference_top = self.slider_top.GetValue() - 1
            self.context.elements.signal(
                "element_property_reload", self.operation, "slider_top"
            )

    def on_slider_left(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        if self.operation.raster_preference_left != self.slider_left.GetValue() - 1:
            self.operation.raster_preference_left = self.slider_left.GetValue() - 1
            self.context.elements.signal(
                "element_property_reload", self.operation, "slider_left"
            )

    def on_slider_right(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        if self.operation.raster_preference_right != self.slider_right.GetValue() - 1:
            self.operation.raster_preference_right = self.slider_right.GetValue() - 1
            self.context.elements.signal(
                "element_property_reload", self.operation, "slider_right"
            )

    def on_slider_bottom(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        if self.operation.raster_preference_bottom != self.slider_bottom.GetValue() - 1:
            self.operation.raster_preference_bottom = self.slider_bottom.GetValue() - 1
            self.context.elements.signal(
                "element_property_reload", self.operation, "slider_bottom"
            )


# end of class PanelStartPreference


class RasterSettingsPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: RasterSettingsPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        raster_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Raster:"), wx.VERTICAL)
        param_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = StaticBoxSizer(self, wx.ID_ANY, _("DPI:"), wx.HORIZONTAL)
        param_sizer.Add(sizer_3, 1, wx.EXPAND, 0)

        self.text_dpi = TextCtrl(
            self,
            wx.ID_ANY,
            "500",
            limited=True,
            check="float",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_dpi.set_error_level(1, 100000)
        OPERATION_DPI_TOOLTIP = (
            _(
                'In a raster engrave, the step size is the distance between raster lines in 1/1000" '
            )
            + _("and also the number of raster dots that get combined together.")
            + "\n"
            + _(
                'Because the laser dot is >> 1/1000" in diameter, at step 1 the raster lines overlap a lot, '
            )
            + _(
                "and consequently you can raster with steps > 1 without leaving gaps between the lines."
            )
            + "\n"
            + _(
                "The step size before you get gaps will depend on your focus and the size of your laser dot."
            )
            + "\n"
            + _(
                "Step size > 1 reduces the laser energy delivered by the same factor, so you may need to increase "
            )
            + _(
                "power equivalently with a higher front-panel power, a higher PPI or by rastering at a slower speed."
            )
            + "\n"
            + _(
                "Step size > 1 also turns the laser on and off fewer times, and combined with a slower speed"
            )
            + _("this can prevent your laser from stuttering.")
        )
        self.text_dpi.SetToolTip(OPERATION_DPI_TOOLTIP)
        sizer_3.Add(self.text_dpi, 1, wx.EXPAND, 0)

        sizer_6 = StaticBoxSizer(self, wx.ID_ANY, _("Overscan:"), wx.HORIZONTAL)
        param_sizer.Add(sizer_6, 1, wx.EXPAND, 0)

        raster_sizer.Add(param_sizer, 0, wx.EXPAND, 0)

        self.text_overscan = TextCtrl(
            self,
            wx.ID_ANY,
            "1mm",
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_overscan.SetToolTip(_("Overscan amount"))
        sizer_6.Add(self.text_overscan, 1, wx.EXPAND, 0)

        sizer_4 = StaticBoxSizer(self, wx.ID_ANY, _("Direction:"), wx.HORIZONTAL)
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
        self.combo_raster_direction.SetSelection(0)
        sizer_4.Add(self.combo_raster_direction, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.radio_raster_swing = wx.RadioBox(
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
        raster_sizer.Add(self.panel_start, 0, wx.EXPAND, 0)

        self.SetSizer(raster_sizer)

        self.Layout()

        self.text_dpi.SetActionRoutine(self.on_text_dpi)
        self.text_overscan.SetActionRoutine(self.on_text_overscan)

        self.Bind(
            wx.EVT_COMBOBOX, self.on_combo_raster_direction, self.combo_raster_direction
        )
        self.Bind(wx.EVT_RADIOBOX, self.on_radio_directional, self.radio_raster_swing)

    def pane_hide(self):
        self.panel_start.pane_hide()

    def pane_show(self):
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
            set_ctrl_value(self.text_dpi, str(self.operation.dpi))
        if self.operation.overscan is not None:
            set_ctrl_value(self.text_overscan, str(self.operation.overscan))
        if self.operation.raster_direction is not None:
            self.combo_raster_direction.SetSelection(self.operation.raster_direction)
        if self.operation.bidirectional is not None:
            self.radio_raster_swing.SetSelection(self.operation.bidirectional)
        self.Show()

    def on_text_dpi(self):
        try:
            value = int(self.text_dpi.GetValue())
            if self.operation.dpi != value:
                self.operation.dpi = value
                self.context.signal(
                    "element_property_reload", self.operation, "text_dpi"
                )
        except ValueError:
            pass

    def on_text_overscan(self):
        start_text = self.text_overscan.GetValue()
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
        if v._amount < 0.0000000001:
            value = 0
        if self.operation.overscan != value:
            self.operation.overscan = value
            self.context.elements.signal(
                "element_property_reload", self.operation, "text_overscan"
            )

    def on_combo_raster_direction(self, event=None):
        if (
            self.operation.raster_direction
            != self.combo_raster_direction.GetSelection()
        ):
            self.operation.raster_direction = self.combo_raster_direction.GetSelection()
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


# end of class RasterSettingsPanel


class HatchSettingsPanel(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: RasterSettingsPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node
        self._Buffer = None

        raster_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Hatch:"), wx.VERTICAL)

        sizer_distance = StaticBoxSizer(
            self, wx.ID_ANY, _("Hatch Distance:"), wx.HORIZONTAL
        )
        raster_sizer.Add(sizer_distance, 0, wx.EXPAND, 0)

        self.text_distance = TextCtrl(
            self,
            wx.ID_ANY,
            "1mm",
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        sizer_distance.Add(self.text_distance, 1, wx.EXPAND, 0)

        sizer_angle = StaticBoxSizer(self, wx.ID_ANY, _("Angle"), wx.HORIZONTAL)
        raster_sizer.Add(sizer_angle, 1, wx.EXPAND, 0)

        self.text_angle = TextCtrl(
            self,
            wx.ID_ANY,
            "0deg",
            limited=True,
            check="angle",
            style=wx.TE_PROCESS_ENTER,
        )
        sizer_angle.Add(self.text_angle, 1, wx.EXPAND, 0)

        self.slider_angle = wx.Slider(self, wx.ID_ANY, 0, 0, 360)
        sizer_angle.Add(self.slider_angle, 3, wx.EXPAND, 0)

        sizer_fill = StaticBoxSizer(self, wx.ID_ANY, _("Fill Style"), wx.VERTICAL)
        raster_sizer.Add(sizer_fill, 6, wx.EXPAND, 0)

        self.fills = list(self.context.match("hatch", suffix=True))
        self.combo_fill_style = wx.ComboBox(
            self, wx.ID_ANY, choices=self.fills, style=wx.CB_DROPDOWN
        )
        sizer_fill.Add(self.combo_fill_style, 0, wx.EXPAND, 0)

        self.display_panel = wx.Panel(self, wx.ID_ANY)
        sizer_fill.Add(self.display_panel, 6, wx.EXPAND, 0)

        self.SetSizer(raster_sizer)

        self.Layout()

        self.text_distance.SetActionRoutine(self.on_text_distance)
        self.text_angle.SetActionRoutine(self.on_text_angle)
        self.Bind(wx.EVT_COMMAND_SCROLL, self.on_slider_angle, self.slider_angle)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_fill, self.combo_fill_style)
        # end wxGlade
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.display_panel.Bind(wx.EVT_PAINT, self.on_display_paint)
        self.display_panel.Bind(wx.EVT_ERASE_BACKGROUND, self.on_display_erase)

        self.raster_pen = wx.Pen()
        self.raster_pen.SetColour(wx.Colour(0, 0, 0, 180))
        self.raster_pen.SetWidth(1)

        self.travel_pen = wx.Pen()
        self.travel_pen.SetColour(wx.Colour(255, 127, 255, 127))
        self.travel_pen.SetWidth(1)

        self.outline_pen = wx.Pen()
        self.outline_pen.SetColour(wx.Colour(0, 127, 255, 127))
        self.outline_pen.SetWidth(1)

        self.hatch_lines = None
        self.travel_lines = None
        self.outline_lines = None

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def accepts(self, node):
        return node.type in ("op hatch",)

    def set_widgets(self, node):
        self.operation = node
        if self.operation is None or not self.accepts(node):
            self.Hide()
            return
        i = 0
        for ht in self.fills:
            if ht == self.operation.hatch_type:
                break
            i += 1
        if i == len(self.fills):
            i = 0
        self.combo_fill_style.SetSelection(i)
        set_ctrl_value(self.text_angle, self.operation.hatch_angle)
        set_ctrl_value(self.text_distance, str(self.operation.hatch_distance))
        try:
            h_angle = float(Angle.parse(self.operation.hatch_angle).as_degrees)
            self.slider_angle.SetValue(int(h_angle))
        except ValueError:
            pass
        self.Show()

    def on_text_distance(self):
        try:
            self.operation.hatch_distance = Length(
                self.text_distance.GetValue()
            ).length_mm
            self.hatch_lines = None
            self.travel_lines = None
            self.refresh_display()
        except ValueError:
            pass

    def on_text_angle(self):
        try:
            angle = f"{Angle.parse(self.text_angle.GetValue()).as_degrees}deg"
            if angle == self.operation.hatch_angle:
                return
            self.operation.hatch_angle = angle
            self.hatch_lines = None
            self.travel_lines = None
            self.refresh_display()
        except ValueError:
            return
        try:
            h_angle = float(Angle.parse(self.operation.hatch_angle).as_degrees)
            while h_angle > self.slider_angle.GetMax():
                h_angle -= 360
            while h_angle < self.slider_angle.GetMin():
                h_angle += 360
            self.slider_angle.SetValue(int(h_angle))
        except ValueError:
            pass

    def on_slider_angle(self, event):  # wxGlade: HatchSettingsPanel.<event_handler>
        value = self.slider_angle.GetValue()
        self.text_angle.SetValue(f"{value}deg")
        self.on_text_angle()
        self.hatch_lines = None
        self.travel_lines = None
        self.refresh_display()

    def on_combo_fill(self, event):  # wxGlade: HatchSettingsPanel.<event_handler>
        hatch_type = self.fills[int(self.combo_fill_style.GetSelection())]
        self.operation.hatch_type = hatch_type
        self.hatch_lines = None
        self.travel_lines = None
        self.refresh_display()

    def on_display_paint(self, event=None):
        if self._Buffer is None:
            return
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
        self.hatch_lines = None
        self.travel_lines = None
        self.refresh_display()

    def refresh_display(self):
        if not wx.IsMainThread():
            wx.CallAfter(self.refresh_in_ui)
        else:
            self.refresh_in_ui()

    def calculate_hatch_lines(self):
        w, h = self._Buffer.Size
        hatch_type = self.operation.hatch_type
        hatch_algorithm = self.context.lookup(f"hatch/{hatch_type}")
        if hatch_algorithm is None:
            return
        paths = (
            complex(w * 0.05, h * 0.05),
            complex(w * 0.95, h * 0.05),
            complex(w * 0.95, h * 0.95),
            complex(w * 0.05, h * 0.95),
            complex(w * 0.05, h * 0.05),
            None,
            complex(w * 0.25, h * 0.25),
            complex(w * 0.75, h * 0.25),
            complex(w * 0.75, h * 0.75),
            complex(w * 0.25, h * 0.75),
            complex(w * 0.25, h * 0.25),
        )
        matrix = Matrix.scale(0.018)
        hatch = list(
            hatch_algorithm(
                settings=self.operation.settings,
                outlines=paths,
                matrix=matrix,
                limit=1000,
            )
        )
        o_start = []
        o_end = []
        last = None
        for c in paths:
            if last is not None and c is not None:
                o_start.append((c.real, c.imag))
                o_end.append((last.real, last.imag))
            last = c
        self.outline_lines = o_start, o_end
        h_start = []
        h_end = []
        t_start = []
        t_end = []
        last_x = None
        last_y = None
        travel = True
        for p in hatch:
            if p is None:
                travel = True
                continue
            x, y = p
            if last_x is None:
                last_x = x
                last_y = y
                travel = False
                continue
            if travel:
                t_start.append((last_x, last_y))
                t_end.append((x, y))
            else:
                h_start.append((last_x, last_y))
                h_end.append((x, y))
            travel = False
            last_x = x
            last_y = y
        self.hatch_lines = h_start, h_end
        self.travel_lines = t_start, t_end

    def refresh_in_ui(self):
        """Performs redrawing of the data in the UI thread."""
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        if self.Shown:
            if self.hatch_lines is None:
                self.calculate_hatch_lines()
            if self.hatch_lines is not None:
                starts, ends = self.hatch_lines
                if len(starts):
                    gc.SetPen(self.raster_pen)
                    gc.StrokeLineSegments(starts, ends)
                else:
                    font = wx.Font(
                        14, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD
                    )
                    gc.SetFont(font, wx.BLACK)
                    gc.DrawText(_("No hatch preview..."), 0, 0)
            if self.travel_lines is not None:
                starts, ends = self.travel_lines
                if len(starts):
                    gc.SetPen(self.travel_pen)
                    gc.StrokeLineSegments(starts, ends)
            if self.outline_lines is not None:
                starts, ends = self.outline_lines
                if len(starts):
                    gc.SetPen(self.outline_pen)
                    gc.StrokeLineSegments(starts, ends)
        gc.Destroy()
        dc.SelectObject(wx.NullBitmap)
        del dc
        self.display_panel.Refresh()
        self.display_panel.Update()


# end of class HatchSettingsPanel


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

        param_sizer = wx.BoxSizer(wx.VERTICAL)

        self.id_panel = IdPanel(
            self,
            wx.ID_ANY,
            context=context,
            node=node,
            showid=False,
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
        param_sizer.Add(self.raster_panel, 0, wx.EXPAND, 0)
        self.panels.append(self.raster_panel)

        self.hatch_panel = HatchSettingsPanel(
            self, wx.ID_ANY, context=context, node=node
        )
        param_sizer.Add(self.hatch_panel, 0, wx.EXPAND, 0)
        self.panels.append(self.hatch_panel)

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
        # if self.operation.type != "op hatch":
        #     if self.hatch_panel.Shown:
        #         self.hatch_panel.Hide()
        # else:
        #     if not self.hatch_panel.Shown:
        #         self.hatch_panel.Show()
        # if self.operation.type not in ("op raster", "op image"):
        #     if self.raster_panel.Shown:
        #         self.raster_panel.Hide()
        # else:
        #     if not self.raster_panel.Shown:
        #         self.raster_panel.Show()
        # if self.operation.type != "op dots":
        #     if self.dwell_panel.Shown:
        #         self.dwell_panel.Hide()
        # else:
        #     if not self.dwell_panel.Shown:
        #         self.dwell_panel.Show()
        self.set_widgets(self.operation)
        self.Layout()

    def set_widgets(self, node):
        self.operation = node
        for panel in self.panels:
            panel.set_widgets(node)

    def pane_hide(self):
        for panel in self.panels:
            panel.pane_hide()

    def pane_show(self):
        for panel in self.panels:
            panel.pane_show()


# end of class ParameterPanel
