from copy import copy
from math import tau

import PIL
import wx
from wx import aui

from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.node.op_cut import CutOpNode
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.node.op_hatch import HatchOpNode
from meerk40t.core.node.op_image import ImageOpNode
from meerk40t.core.node.op_raster import RasterOpNode
from meerk40t.core.units import UNITS_PER_PIXEL, Angle, Length
from meerk40t.gui.icons import icons8_detective_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import StaticBoxSizer, TextCtrl
from meerk40t.kernel import signal_listener
from meerk40t.svgelements import Circle, Color, Matrix, Rect

_ = wx.GetTranslation


class TemplatePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.callback = None
        self.current_op = None
        opchoices = [_("Cut"), _("Engrave"), _("Raster"), _("Image"), _("Hatch")]
        # Setup 5 Op nodes - they aren't saved yet
        self.default_op = []
        # A tuple defining whether a free color-selection scheme is allowed, linked to default_op
        self.color_scheme_free = []
        self.default_op.append(CutOpNode())
        self.color_scheme_free.append(True)
        self.default_op.append(EngraveOpNode())
        self.color_scheme_free.append(True)
        self.default_op.append(RasterOpNode())
        self.color_scheme_free.append(False)
        self.default_op.append(ImageOpNode())
        self.color_scheme_free.append(True)
        self.default_op.append(HatchOpNode())
        self.color_scheme_free.append(True)

        self._freecolor = True

        self.parameters = []
        color_choices = [_("Red"), _("Green"), _("Blue")]

        self.combo_ops = wx.ComboBox(
            self, id=wx.ID_ANY, choices=opchoices, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )

        self.check_labels = wx.CheckBox(self, wx.ID_ANY, _("Labels"))
        self.check_values = wx.CheckBox(self, wx.ID_ANY, _("Values"))

        self.combo_param_1 = wx.ComboBox(
            self, id=wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.spin_count_1 = wx.SpinCtrl(self, wx.ID_ANY, initial=5, min=1, max=100)
        self.text_min_1 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_max_1 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_dim_1 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_dim_1.set_range(0, 50)
        self.text_delta_1 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_delta_1.set_range(0, 50)
        self.unit_param_1a = wx.StaticText(self, wx.ID_ANY, "")
        self.unit_param_1b = wx.StaticText(self, wx.ID_ANY, "")
        self.combo_color_1 = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=color_choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.check_color_direction_1 = wx.CheckBox(self, wx.ID_ANY, _("Growing"))

        self.combo_param_2 = wx.ComboBox(
            self, id=wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.spin_count_2 = wx.SpinCtrl(self, wx.ID_ANY, initial=5, min=1, max=100)
        self.text_min_2 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_max_2 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_dim_2 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_dim_2.set_range(0, 50)
        self.text_delta_2 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_delta_2.set_range(0, 50)
        self.unit_param_2a = wx.StaticText(self, wx.ID_ANY, "")
        self.unit_param_2b = wx.StaticText(self, wx.ID_ANY, "")
        self.combo_color_2 = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=color_choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.check_color_direction_2 = wx.CheckBox(self, wx.ID_ANY, _("Growing"))

        self.button_create = wx.Button(self, wx.ID_ANY, _("Create Pattern"))
        self.button_create.SetBitmap(icons8_detective_50.GetBitmap(resize=25))

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_param_optype = wx.BoxSizer(wx.HORIZONTAL)

        sizer_param_op = StaticBoxSizer(
            self, wx.ID_ANY, _("Operation to test"), wx.HORIZONTAL
        )
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Operation:"))
        sizer_param_op.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_param_op.Add(self.combo_ops, 1, wx.EXPAND, 0)

        sizer_param_check = StaticBoxSizer(
            self, wx.ID_ANY, _("Show Labels / Values"), wx.HORIZONTAL
        )
        sizer_param_check.Add(self.check_labels, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_param_check.Add(self.check_values, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_param_optype.Add(sizer_param_op, 1, wx.EXPAND, 0)
        sizer_param_optype.Add(sizer_param_check, 1, wx.EXPAND, 0)

        sizer_param_xy = wx.BoxSizer(wx.HORIZONTAL)
        sizer_param_x = StaticBoxSizer(
            self, wx.ID_ANY, _("First parameter (X-Axis)"), wx.VERTICAL
        )

        hline_param_1 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Parameter:"))
        hline_param_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_param_1.Add(self.combo_param_1, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_count_1 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Count:"))
        hline_count_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_count_1.Add(self.spin_count_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_min_1 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Minimum:"))
        hline_min_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_min_1.Add(self.text_min_1, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_min_1.Add(self.unit_param_1a, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_max_1 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Maximum:"))
        hline_max_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_max_1.Add(self.text_max_1, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_max_1.Add(self.unit_param_1b, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_dim_1 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Width:"))
        hline_dim_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_dim_1.Add(self.text_dim_1, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        mylbl = wx.StaticText(self, wx.ID_ANY, "mm")
        hline_dim_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_delta_1 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Delta:"))
        hline_delta_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_delta_1.Add(self.text_delta_1, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        mylbl = wx.StaticText(self, wx.ID_ANY, "mm")
        hline_delta_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_color_1 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Color:"))
        hline_color_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_color_1.Add(self.combo_color_1, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_color_1.Add(self.check_color_direction_1, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_param_x.Add(hline_param_1, 0, wx.EXPAND, 0)
        sizer_param_x.Add(hline_count_1, 0, wx.EXPAND, 0)
        sizer_param_x.Add(hline_min_1, 0, wx.EXPAND, 0)
        sizer_param_x.Add(hline_max_1, 0, wx.EXPAND, 0)
        sizer_param_x.Add(hline_dim_1, 0, wx.EXPAND, 0)
        sizer_param_x.Add(hline_delta_1, 0, wx.EXPAND, 0)
        sizer_param_x.Add(hline_color_1, 0, wx.EXPAND, 0)

        sizer_param_y = StaticBoxSizer(
            self, wx.ID_ANY, _("Second parameter (Y-Axis)"), wx.VERTICAL
        )

        hline_param_2 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Parameter:"))
        hline_param_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_param_2.Add(self.combo_param_2, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_count_2 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Count:"))
        hline_count_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_count_2.Add(self.spin_count_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_min_2 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Minimum:"))
        hline_min_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_min_2.Add(self.text_min_2, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_min_2.Add(self.unit_param_2a, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_max_2 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Maximum:"))
        hline_max_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_max_2.Add(self.text_max_2, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_max_2.Add(self.unit_param_2b, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_dim_2 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Height:"))
        hline_dim_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_dim_2.Add(self.text_dim_2, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        mylbl = wx.StaticText(self, wx.ID_ANY, "mm")
        hline_dim_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_delta_2 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Delta:"))
        hline_delta_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_delta_2.Add(self.text_delta_2, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        mylbl = wx.StaticText(self, wx.ID_ANY, "mm")
        hline_delta_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_color_2 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Color:"))
        hline_color_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_color_2.Add(self.combo_color_2, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_color_2.Add(self.check_color_direction_2, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_param_y.Add(hline_param_2, 0, wx.EXPAND, 0)
        sizer_param_y.Add(hline_count_2, 0, wx.EXPAND, 0)
        sizer_param_y.Add(hline_min_2, 0, wx.EXPAND, 0)
        sizer_param_y.Add(hline_max_2, 0, wx.EXPAND, 0)
        sizer_param_y.Add(hline_dim_2, 0, wx.EXPAND, 0)
        sizer_param_y.Add(hline_delta_2, 0, wx.EXPAND, 0)
        sizer_param_y.Add(hline_color_2, 0, wx.EXPAND, 0)

        sizer_param_xy.Add(sizer_param_x, 1, wx.EXPAND, 0)
        sizer_param_xy.Add(sizer_param_y, 1, wx.EXPAND, 0)

        sizer_main.Add(sizer_param_optype, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_param_xy, 0, wx.EXPAND, 0)
        sizer_main.Add(self.button_create, 0, wx.EXPAND, 0)

        sizer_info = StaticBoxSizer(self, wx.ID_ANY, _("How to use it"), wx.VERTICAL)
        infomsg = _("To provide the best burning results, the parameters of operations")
        infomsg += " " + _(
            "need to be adjusted according to *YOUR* laser and the specific material"
        )
        infomsg += " " + _(
            "you want to work with (e.g. one batch of poplar plywood from one supplier"
        )
        infomsg += " " + _(
            "may respond completely different to a batch of another supplier despite"
        )
        infomsg += " " + _("having the very same specifications on paper).")
        infomsg += "\n" + _(
            "E.g. for a regular CO2 laser you want to optimize the burn speed"
        )
        infomsg += " " + _(
            "for a given power to reduce burn marks or decrease execution time."
        )
        infomsg += "\n" + _(
            "Meerk40t simplifies this task to find out the optimal settings"
        )
        infomsg += " " + _(
            "by creating a testpattern that varies two different parameters."
        )

        info_label = wx.TextCtrl(
            self, wx.ID_ANY, value=infomsg, style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        info_label.SetBackgroundColour(self.GetBackgroundColour())
        sizer_info.Add(info_label, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_info, 1, wx.EXPAND, 0)

        self.button_create.SetToolTip(_("Create a grid with your values"))
        s = _("Operation type for which the testpattern will be generated")
        s += "\n" + _(
            "You can define the common parameters for this operation in the other tabs on top of this window"
        )
        self.combo_ops.SetToolTip(s)
        self.combo_param_1.SetToolTip(
            _("Choose the first parameter that you want to be tested")
        )
        self.combo_param_2.SetToolTip(
            _("Choose the second parameter that you want to be tested")
        )
        self.combo_color_1.SetToolTip(
            _(
                "Choose the color aspect for the second parameter. NB: the colors for both parameters will be combined"
            )
        )
        self.combo_color_2.SetToolTip(
            _(
                "Choose the color aspect for the second parameter. NB: the colors for both parameters will be combined"
            )
        )
        self.check_color_direction_1.SetToolTip(
            _(
                "If checked, then the color aspect will grow from min to max values, if not then shrink"
            )
        )
        self.check_color_direction_2.SetToolTip(
            _(
                "If checked, then the color aspect will grow from min to max values, if not then shrink"
            )
        )
        self.spin_count_1.SetToolTip(
            _(
                "Define how many values you want to test in the interval between min and max"
            )
        )
        self.spin_count_2.SetToolTip(
            _(
                "Define how many values you want to test in the interval between min and max"
            )
        )
        self.check_labels.SetToolTip(
            _("Will create a descriptive label at the sides of the grid")
        )
        self.check_values.SetToolTip(
            _("Will create the corresponding values as labels at the sides of the grid")
        )
        self.text_min_1.SetToolTip(_("Minimum value for 1st parameter"))
        self.text_max_1.SetToolTip(_("Maximum value for 1st parameter"))
        self.text_min_2.SetToolTip(_("Minimum value for 2nd parameter"))
        self.text_max_2.SetToolTip(_("Maximum value for 2nd parameter"))
        self.text_dim_1.SetToolTip(_("Width of the to be created pattern"))
        self.text_dim_2.SetToolTip(_("Height of the to be created pattern"))
        self.text_delta_1.SetToolTip(_("Horizontal gap between patterns"))
        self.text_delta_2.SetToolTip(_("Vertical gap between patterns"))

        self.button_create.Bind(wx.EVT_BUTTON, self.on_button_create_pattern)
        self.combo_ops.Bind(wx.EVT_COMBOBOX, self.set_param_according_to_op)
        self.text_min_1.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_max_1.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_min_2.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_max_2.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_dim_1.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_delta_1.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_dim_2.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_delta_2.Bind(wx.EVT_TEXT, self.validate_input)
        self.combo_param_1.Bind(wx.EVT_COMBOBOX, self.on_combo_1)
        self.combo_param_2.Bind(wx.EVT_COMBOBOX, self.on_combo_2)

        self.SetSizer(sizer_main)
        self.Layout()
        self.setup_settings()
        self.combo_ops.SetSelection(0)
        self.restore_settings()
        # Repopulate combos
        self.set_param_according_to_op(None)
        # And then setting it back to the defaults...
        self.combo_param_1.SetSelection(
            min(self.context.template_param1, self.combo_param_1.GetCount() - 1)
        )
        # Make sure units appear properly
        self.on_combo_1(None)
        self.combo_param_2.SetSelection(
            min(self.context.template_param2, self.combo_param_2.GetCount() - 1)
        )
        # Make sure units appear properly
        self.on_combo_2(None)

    def set_callback(self, routine):
        self.callback = routine
        idx = self.combo_ops.GetSelection()
        if self.callback is not None and idx >= 0:
            self.callback(self.default_op[idx])

    def set_param_according_to_op(self, event):
        def preset_passes(node=None):
            # Will be called ahead of the modification of the passes variable
            node.passes_custom = True

        def preset_balor_wobble(node=None):
            # Will be called ahead of the modification of a wobble variable
            # to copy the device defaults
            if node is None or "balor" not in self.context.device.path:
                return
            node.settings["wobble_enabled"] = True

        def preset_balor_rapid(node=None):
            # Will be called ahead of the modification of a rapid variable
            # to copy the device defaults
            if node is None or "balor" not in self.context.device.path:
                return
            node.settings["rapid_enabled"] = True

        def preset_balor_pulse(node=None):
            # Will be called ahead of the modification of a pulse variable
            # to copy the device defaults
            if node is None or "balor" not in self.context.device.path:
                return
            node.settings["pulse_width_enabled"] = True

        def preset_balor_timings(node=None):
            # Will be called ahead of the modification of a timing variable
            # to copy the device defaults
            if node is None or "balor" not in self.context.device.path:
                return
            if not node.settings["timing_enabled"]:
                node.settings["timing_enabled"] = True
                node.settings["delay_laser_on"] = self.context.device.delay_laser_on
                node.settings["delay_laser_off"] = self.context.device.delay_laser_off
                node.settings["delay_polygon"] = self.context.device.delay_polygon

        opidx = self.combo_ops.GetSelection()
        if self.current_op == opidx:
            return
        self.current_op = opidx

        if opidx < 0:
            opnode = None
            self._freecolor = True
        else:
            opnode = self.default_op[opidx]
            self._freecolor = self.color_scheme_free[opidx]
        if self.callback is not None:
            self.callback(opnode)
        self.combo_color_1.Enable(self._freecolor)
        self.combo_color_2.Enable(self._freecolor)
        self.check_color_direction_1.Enable(self._freecolor)
        self.check_color_direction_2.Enable(self._freecolor)

        # (internal_attribute, secondary_attribute, Label, unit, keep_unit, needs_to_be_positive)
        self.parameters = [
            ("speed", None, _("Speed"), "mm/s", False, True),
            ("power", None, _("Power"), "ppi", False, True),
            ("passes", preset_passes, _("Passes"), "x", False, True),
        ]

        if opidx == 0:
            # Cut
            # (internal_attribute, secondary_attribute, Label, unit, keep_unit, needs_to_be_positive)
            self.parameters = [
                ("speed", None, _("Speed"), "mm/s", False, True),
                ("power", None, _("Power"), "ppi", False, True),
                ("passes", preset_passes, _("Passes"), "x", False, True),
            ]
        elif opidx == 1:
            # Engrave
            self.parameters = [
                ("speed", None, _("Speed"), "mm/s", False, True),
                ("power", None, _("Power"), "ppi", False, True),
                ("passes", preset_passes, _("Passes"), "x", False, True),
            ]
        elif opidx == 2:
            # Raster
            self.parameters = [
                ("speed", None, _("Speed"), "mm/s", False, True),
                ("power", None, _("Power"), "ppi", False, True),
                ("passes", preset_passes, _("Passes"), "x", False, True),
                ("dpi", None, _("DPI"), "dpi", False, True),
                ("overscan", None, _("Overscan"), "mm", False, True),
            ]
        elif opidx == 3:
            # Image
            self.parameters = [
                ("speed", None, _("Speed"), "mm/s", False, True),
                ("power", None, _("Power"), "ppi", False, True),
                ("passes", preset_passes, _("Passes"), "x", False, True),
                ("dpi", None, _("DPI"), "dpi", False, True),
                ("overscan", None, _("Overscan"), "mm", False, True),
            ]
        elif opidx == 4:
            # Hatch
            self.parameters = [
                ("speed", None, _("Speed"), "mm/s", False, True),
                ("power", None, _("Power"), "ppi", False, True),
                ("passes", preset_passes, _("Passes"), "x", False, True),
                ("hatch_distance", None, _("Hatch Distance"), "mm", False, True),
                ("hatch_angle", None, _("Hatch Angle"), "deg", False, True),
            ]

        if "balor" in self.context.device.path:
            balor_choices = [
                ("frequency", None, _("Frequency"), "kHz", False, True),
                (
                    "rapid_speed",
                    preset_balor_rapid,
                    _("Rapid Speed"),
                    "mm/s",
                    False,
                    True,
                ),
                (
                    "delay_laser_on",
                    preset_balor_timings,
                    _("Laser On Delay"),
                    "µs",
                    False,
                    False,
                ),
                (
                    "delay_laser_off",
                    preset_balor_timings,
                    _("Laser Off Delay"),
                    "µs",
                    False,
                    False,
                ),
                (
                    "delay_polygon",
                    preset_balor_timings,
                    _("Polygon Delay"),
                    "µs",
                    False,
                    False,
                ),
                (
                    "wobble_radius",
                    preset_balor_wobble,
                    _("Wobble Radius"),
                    "mm",
                    True,
                    True,
                ),
                (
                    "wobble_interval",
                    preset_balor_wobble,
                    _("Wobble Interval"),
                    "mm",
                    True,
                    True,
                ),
                (
                    "wobble_speed",
                    preset_balor_wobble,
                    _("Wobble Speed Multiplier"),
                    "x",
                    False,
                    True,
                ),
            ]
            if self.context.device.pulse_width_enabled:
                balor_choices.append(
                    (
                        "pulse_width",
                        preset_balor_pulse,
                        _("Pulse Width"),
                        "ns",
                        False,
                        True,
                    )
                )

            for entry in balor_choices:
                self.parameters.append(entry)
        choices = []
        for entry in self.parameters:
            choices.append(entry[2])
        self.combo_param_1.Clear()
        self.combo_param_1.Set(choices)
        self.combo_param_2.Clear()
        self.combo_param_2.Set(choices)
        idx1 = -1
        idx2 = -1
        if len(self.parameters) > 0:
            idx1 = 0
            idx2 = 0
        if len(self.parameters) > 1:
            idx2 = 1
        self.combo_param_1.SetSelection(idx1)
        self.on_combo_1(None)
        self.combo_param_2.SetSelection(idx2)
        self.on_combo_2(None)

    def on_combo_1(self, input):
        s_unit = ""
        b_positive = True
        idx = self.combo_param_1.GetSelection()
        # 0 = internal_attribute, 1 = secondary_attribute,
        # 2 = Label, 3 = unit,
        # 4 = keep_unit, 5 = needs_to_be_positive)
        if idx >= 0 and idx < len(self.parameters):
            s_unit = self.parameters[idx][3]
            b_positive = self.parameters[idx][5]
        self.unit_param_1a.SetLabel(s_unit)
        self.unit_param_1b.SetLabel(s_unit)
        # And now enter validation...
        self.validate_input(None)

    def on_combo_2(self, input):
        s_unit = ""
        idx = self.combo_param_2.GetSelection()
        # 0 = internal_attribute, 1 = secondary_attribute,
        # 2 = Label, 3 = unit,
        # 4 = keep_unit, 5 = needs_to_be_positive)
        if idx >= 0 and idx < len(self.parameters):
            s_unit = self.parameters[idx][3]
        self.unit_param_2a.SetLabel(s_unit)
        self.unit_param_2b.SetLabel(s_unit)
        # And now enter validation...
        self.validate_input(None)

    def validate_input(self, event):
        def valid_float(ctrl):
            result = True
            if ctrl.GetValue() == "":
                result = False
            else:
                try:
                    value = float(ctrl.GetValue())
                except ValueError:
                    result = False
            return result

        active = True
        optype = self.combo_ops.GetSelection()
        if optype < 0:
            active = False
        idx1 = self.combo_param_1.GetSelection()
        if idx1 < 0:
            active = False
        idx2 = self.combo_param_2.GetSelection()
        if idx2 < 0:
            active = False
        if idx1 == idx2:
            active = False
        if not valid_float(self.text_min_1):
            active = False
        if not valid_float(self.text_max_1):
            active = False
        if not valid_float(self.text_min_2):
            active = False
        if not valid_float(self.text_max_2):
            active = False
        if not valid_float(self.text_dim_1):
            active = False
        if not valid_float(self.text_delta_1):
            active = False
        if not valid_float(self.text_dim_2):
            active = False
        if not valid_float(self.text_delta_2):
            active = False

        self.button_create.Enable(active)

    def on_button_create_pattern(self, event):
        def make_color(idx1, max1, idx2, max2, aspect1, growing1, aspect2, growing2):
            if self._freecolor:
                r = 0
                g = 0
                b = 0

                rel = max1 - 1
                if rel < 1:
                    rel = 1
                if growing1:
                    val1 = int(idx1 / rel * 255.0)
                else:
                    val1 = 255 - int(idx1 / rel * 255.0)

                rel = max2 - 1
                if rel < 1:
                    rel = 1
                if growing2:
                    val2 = int(idx2 / rel * 255.0)
                else:
                    val2 = 255 - int(idx2 / rel * 255.0)
                if aspect1 == 1:
                    g = val1
                elif aspect1 == 2:
                    b = val1
                else:
                    r = val1
                if aspect2 == 1:
                    g = val1
                elif aspect2 == 2:
                    b = val2
                else:
                    r = val2
            else:
                r = 0
                g = 0
                b = 0
            mycolor = Color(r, g, b)
            return mycolor

        def clear_all():
            self.context.elements.clear_operations()
            self.context.elements.clear_elements()

        def create_operations():
            def shortened(value, digits):
                result = str(round(value, digits))
                if "." in result:
                    while result.endswith("0"):
                        result = result[:-1]
                if result.endswith("."):
                    if result == ".":
                        result = "0"
                    else:
                        result = result[:-1]
                return result

            # opchoices = [_("Cut"), _("Engrave"), _("Raster"), _("Image"), _("Hatch")]
            display_labels = self.check_labels.GetValue()
            display_values = self.check_values.GetValue()
            color_aspect_1 = max(0, self.combo_color_1.GetSelection())
            color_aspect_2 = max(0, self.combo_color_2.GetSelection())
            color_growing_1 = self.check_color_direction_1.GetValue()
            color_growing_2 = self.check_color_direction_2.GetValue()

            if optype < 0 or optype > 4:
                return
            if optype == 3:
                shapetype = "image"
            else:
                shapetype = "rect"
            size_x = float(Length(f"{dimension_1}mm"))
            size_y = float(Length(f"{dimension_2}mm"))
            gap_x = float(Length(f"{gap_1}mm"))
            gap_y = float(Length(f"{gap_2}mm"))
            expected_width = count_1 * size_x + (count_1 - 1) * gap_x
            expected_height = count_2 * size_y + (count_2 - 1) * gap_y
            # Need to be adjusted to allow for centering
            start_x = (float(Length(self.context.device.width)) - expected_width) / 2
            start_y = (float(Length(self.context.device.height)) - expected_height) / 2
            operation_branch = self.context.elements._tree.get(type="branch ops")
            element_branch = self.context.elements._tree.get(type="branch elems")

            text_scale_x = min(1.0, size_y / float(Length("20mm")))
            text_scale_y = min(1.0, size_x / float(Length("20mm")))

            # Make one op for text
            if display_labels or display_values:
                text_op = RasterOpNode()
                text_op.color = Color("black")
                text_op.label = "Descriptions"
                operation_branch.add_node(text_op)
            if display_labels:
                text_x = start_x + expected_width / 2
                text_y = start_y - min(float(Length("10mm")), 3 * gap_y)
                node = self.context.elements.elem_branch.add(
                    text=f"{param_name_1} [{param_unit_1}]",
                    matrix=Matrix(
                        f"translate({text_x}, {text_y}) scale({2 * max(text_scale_x, text_scale_y) * UNITS_PER_PIXEL})"
                    ),
                    anchor="middle",
                    fill=Color("black"),
                    type="elem text",
                )
                text_op.add_reference(node, 0)

                text_x = start_x - min(float(Length("10mm")), 3 * gap_x)
                text_y = start_y + expected_height / 2
                node = self.context.elements.elem_branch.add(
                    text=f"{param_name_2} [{param_unit_2}]",
                    matrix=Matrix(
                        f"translate({text_x}, {text_y}) scale({2 * max(text_scale_x, text_scale_y) * UNITS_PER_PIXEL})"
                    ),
                    anchor="middle",
                    fill=Color("black"),
                    type="elem text",
                )
                node.matrix.post_rotate(tau * 3 / 4, text_x, text_y)
                node.modified()
                text_op.add_reference(node, 0)

            p_value_1 = min_value_1

            xx = start_x
            for idx1 in range(count_1):
                pval1 = shortened(p_value_1, 3)

                p_value_2 = min_value_2
                yy = start_y

                if display_values:
                    # Add a text above for each column
                    text_x = xx + 0.5 * size_x
                    text_y = yy - min(float(Length("5mm")), 1.5 * gap_y)
                    node = self.context.elements.elem_branch.add(
                        text=f"{pval1}",
                        matrix=Matrix(
                            f"translate({text_x}, {text_y}) scale({text_scale_x * UNITS_PER_PIXEL})"
                        ),
                        anchor="middle",
                        fill=Color("black"),
                        type="elem text",
                    )
                    # node.matrix.post_rotate(tau / 4, text_x, text_y)
                    node.modified()
                    text_op.add_reference(node, 0)

                for idx2 in range(count_2):
                    pval2 = shortened(p_value_2, 3)
                    s_lbl = f"{param_type_1}={pval1}{param_unit_1}"
                    s_lbl += f"- {param_type_2}={pval2}{param_unit_2}"
                    if display_values and idx1 == 0:  # first row, so add a text above
                        text_x = xx - min(float(Length("5mm")), 1.5 * gap_x)
                        text_y = yy + 0.5 * size_y
                        node = self.context.elements.elem_branch.add(
                            text=f"{pval2}",
                            matrix=Matrix(
                                f"translate({text_x}, {text_y}) scale({text_scale_y * UNITS_PER_PIXEL})"
                            ),
                            anchor="middle",
                            fill=Color("black"),
                            type="elem text",
                        )
                        node.matrix.post_rotate(tau * 3 / 4, text_x, text_y)
                        text_op.add_reference(node, 0)
                    if optype == 0:  # Cut
                        this_op = copy(self.default_op[optype])
                        usefill = False
                    elif optype == 1:  # Engrave
                        this_op = copy(self.default_op[optype])
                        usefill = False
                    elif optype == 2:  # Raster
                        this_op = copy(self.default_op[optype])
                        usefill = True
                    elif optype == 3:  # Image
                        this_op = copy(self.default_op[optype])
                        usefill = False
                    elif optype == 4:  # Hatch
                        this_op = copy(self.default_op[optype])
                        usefill = True
                    else:
                        return
                    this_op.label = s_lbl

                    # Do we need to prep the op?
                    if param_prepper_1 is not None:
                        param_prepper_1(this_op)

                    if param_keep_unit_1:
                        value = str(p_value_1) + param_unit_1
                    else:
                        value = p_value_1
                    if hasattr(this_op, param_type_1):
                        # quick and dirty
                        if param_type_1 == "passes":
                            value = int(value)
                        if param_type_1 == "hatch_distance":
                            value = f"{value}mm"
                        setattr(this_op, param_type_1, value)
                    else:  # Try setting
                        this_op.settings[param_type_1] = value

                    # Do we need to prep the op?
                    if param_prepper_2 is not None:
                        param_prepper_2(this_op)

                    if param_keep_unit_2:
                        value = str(p_value_2) + param_unit_2
                    else:
                        value = p_value_2
                    if hasattr(this_op, param_type_2):
                        if param_type_2 == "passes":
                            value = int(value)
                        if param_type_2 == "hatch_distance":
                            value = f"{value}mm"
                        setattr(this_op, param_type_2, value)
                    else:  # Try setting
                        this_op.settings[param_type_2] = value

                    set_color = make_color(
                        idx1,
                        count_1,
                        idx2,
                        count_2,
                        color_aspect_1,
                        color_growing_1,
                        color_aspect_2,
                        color_growing_2,
                    )
                    this_op.color = set_color
                    # Add op to tree.
                    operation_branch.add_node(this_op)
                    # Now add a rectangle to the scene and assign it to the newly created op
                    if usefill:
                        fill_color = set_color
                    else:
                        fill_color = None
                    if shapetype == "image":
                        imgsx = int(size_x / UNITS_PER_PIXEL)
                        imgsy = int(size_y / UNITS_PER_PIXEL)
                        # print (f"Image to create: {imgsx} x {imgsy} pixel, {size_x} x {size_y}")
                        image = PIL.Image.new(
                            "RGBA",
                            size=(imgsx, imgsy),
                            color=(set_color.red, set_color.green, set_color.blue, 255),
                        )

                        elemnode = ImageNode(image=image)
                        elemnode.matrix.post_translate(xx, yy)
                        elemnode.matrix.post_scale(
                            UNITS_PER_PIXEL, UNITS_PER_PIXEL, xx, yy
                        )
                        elemnode.modified()
                        self.context.elements.elem_branch.add_node(elemnode)
                    elif shapetype == "rect":
                        pattern = Rect(
                            x=xx,
                            y=yy,
                            width=size_x,
                            height=size_y,
                            stroke=set_color,
                            fill=fill_color,
                        )
                        elem_type = "elem rect"
                        elemnode = self.context.elements.elem_branch.add(
                            shape=pattern, type=elem_type
                        )
                    elif shapetype == "circle":
                        pattern = Circle(
                            cx=xx + size_x / 2,
                            cy=yy + size_y / 2,
                            rx=size_x / 2,
                            ry=size_y / 2,
                            stroke=set_color,
                            fill=fill_color,
                        )
                        elem_type = "elem ellipse"
                        elemnode = self.context.elements.elem_branch.add(
                            shape=pattern, type=elem_type
                        )
                    elemnode.label = s_lbl
                    this_op.add_reference(elemnode, 0)
                    p_value_2 += delta_2
                    yy = yy + gap_y + size_y
                p_value_1 += delta_1
                xx = xx + gap_x + size_x

        # Read the parameters and user input
        optype = self.combo_ops.GetSelection()
        if optype < 0:
            return
        idx = self.combo_param_1.GetSelection()
        if idx < 0:
            return
        # 0 = internal_attribute, 1 = secondary_attribute,
        # 2 = Label, 3 = unit,
        # 4 = keep_unit, 5 = needs_to_be_positive)
        param_name_1 = self.parameters[idx][2]
        param_type_1 = self.parameters[idx][0]
        param_prepper_1 = self.parameters[idx][1]
        if param_prepper_1 == "":
            param_prepper_1 = None
        param_unit_1 = self.parameters[idx][3]
        param_keep_unit_1 = self.parameters[idx][4]
        param_positive_1 = self.parameters[idx][5]

        idx = self.combo_param_2.GetSelection()
        if idx < 0:
            return
        param_name_2 = self.parameters[idx][2]
        param_type_2 = self.parameters[idx][0]
        param_prepper_2 = self.parameters[idx][1]
        if param_prepper_2 == "":
            param_prepper_2 = None
        param_unit_2 = self.parameters[idx][3]
        param_keep_unit_2 = self.parameters[idx][4]
        param_positive_2 = self.parameters[idx][5]
        if param_type_1 == param_type_2:
            return
        if self.text_min_1.GetValue() == "":
            return
        try:
            min_value_1 = float(self.text_min_1.GetValue())
        except ValueError:
            return
        if self.text_min_2.GetValue() == "":
            return
        try:
            min_value_2 = float(self.text_min_2.GetValue())
        except ValueError:
            return
        if self.text_max_1.GetValue() == "":
            return
        try:
            max_value_1 = float(self.text_max_1.GetValue())
        except ValueError:
            return
        if self.text_max_2.GetValue() == "":
            return
        try:
            max_value_2 = float(self.text_max_2.GetValue())
        except ValueError:
            return

        if param_unit_1 == "deg":
            min_value_1 = Angle(self.text_min_1.GetValue()).degrees
            max_value_1 = Angle(self.text_max_1.GetValue()).degrees
        elif param_unit_1 == "ppi":
            min_value_1 = max(min_value_1, 0)
            max_value_1 = min(max_value_1, 1000)
        else:
            # > 0
            if param_positive_1:
                min_value_1 = max(min_value_1, 0)
                max_value_1 = max(max_value_1, 0)

        if param_unit_2 == "deg":
            min_value_2 = Angle(self.text_min_2.GetValue()).degrees
            max_value_2 = Angle(self.text_max_2.GetValue()).degrees
        elif param_unit_2 == "ppi":
            min_value_2 = max(min_value_2, 0)
            max_value_2 = min(max_value_2, 1000)
        else:
            # > 0
            if param_positive_2:
                min_value_2 = max(min_value_2, 0)
                max_value_2 = max(max_value_2, 0)

        count_1 = int(self.spin_count_1.GetValue())
        count_2 = int(self.spin_count_2.GetValue())
        if count_1 > 1:
            delta_1 = (max_value_1 - min_value_1) / (count_1 - 1)
        else:
            delta_1 = 0
        if count_2 > 1:
            delta_2 = (max_value_2 - min_value_2) / (count_2 - 1)
        else:
            delta_2 = 0
        try:
            dimension_1 = float(self.text_dim_1.GetValue())
        except ValueError:
            dimension_1 = -1
        try:
            dimension_2 = float(self.text_dim_2.GetValue())
        except ValueError:
            dimension_2 = -1
        if dimension_1 <= 0:
            dimension_1 = 5
        if dimension_2 <= 0:
            dimension_2 = 5

        try:
            gap_1 = float(self.text_delta_1.GetValue())
        except ValueError:
            gap_1 = -1
        try:
            gap_2 = float(self.text_delta_2.GetValue())
        except ValueError:
            gap_2 = -1

        if gap_1 < 0:
            gap_1 = 0
        if gap_2 < 0:
            gap_2 = 5

        message = _("This will delete all existing operations and elements") + "\n"
        message += (
            _("and replace them by the test-pattern! Are you really sure?") + "\n"
        )
        message += _("(Yes=Empty and Create, No=Keep existing)")
        caption = _("Create Test-Pattern")
        dlg = wx.MessageDialog(
            self,
            message,
            caption,
            wx.YES_NO | wx.CANCEL | wx.ICON_WARNING,
        )
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_YES:
            clear_all()
        elif result == wx.ID_CANCEL:
            return

        create_operations()

        self.context.signal("rebuild_tree")
        self.context.signal("refresh_scene", "Scene")
        self.save_settings()

    def setup_settings(self):
        self.context.setting(int, "template_optype", 0)
        self.context.setting(int, "template_param1", 0)
        self.context.setting(int, "template_param2", 1)
        self.context.setting(str, "template_min1", "")
        self.context.setting(str, "template_max1", "")
        self.context.setting(str, "template_min2", "")
        self.context.setting(str, "template_max2", "")
        self.context.setting(int, "template_count1", 5)
        self.context.setting(int, "template_count2", 5)
        self.context.setting(str, "template_dim_1", "10")
        self.context.setting(str, "template_dim_2", "10")
        self.context.setting(str, "template_gap_1", "5")
        self.context.setting(str, "template_gap_2", "5")
        self.context.setting(bool, "template_show_labels", True)
        self.context.setting(bool, "template_show_values", True)
        self.context.setting(int, "template_color1", 0)
        self.context.setting(int, "template_color2", 2)
        self.context.setting(bool, "template_coldir1", False)
        self.context.setting(bool, "template_coldir2", False)

    def save_settings(self):
        self.context.template_show_values = self.check_values.GetValue()
        self.context.template_show_labels = self.check_labels.GetValue()
        self.context.template_optype = self.combo_ops.GetSelection()
        self.context.template_param1 = self.combo_param_1.GetSelection()
        self.context.template_param2 = self.combo_param_2.GetSelection()
        self.context.template_min1 = self.text_min_1.GetValue()
        self.context.template_max1 = self.text_max_1.GetValue()
        self.context.template_min2 = self.text_min_2.GetValue()
        self.context.template_max2 = self.text_max_2.GetValue()
        self.context.template_count1 = self.spin_count_1.GetValue()
        self.context.template_count2 = self.spin_count_2.GetValue()
        self.context.template_dim_1 = self.text_dim_1.GetValue()
        self.context.template_dim_2 = self.text_dim_2.GetValue()
        self.context.template_gap_1 = self.text_delta_1.GetValue()
        self.context.template_gap_2 = self.text_delta_2.GetValue()
        self.context.template_color1 = self.combo_color_1.GetSelection()
        self.context.template_color2 = self.combo_color_2.GetSelection()
        self.context.template_coldir1 = self.check_color_direction_1.GetValue()
        self.context.template_coldir2 = self.check_color_direction_2.GetValue()

    def restore_settings(self):
        try:
            self.check_color_direction_1.SetValue(self.context.template_coldir1)
            self.check_color_direction_2.SetValue(self.context.template_coldir2)
            self.combo_color_1.SetSelection(
                min(self.context.template_color1, self.combo_color_1.GetCount() - 1)
            )
            self.combo_color_2.SetSelection(
                min(self.context.template_color2, self.combo_color_2.GetCount() - 1)
            )
            self.check_values.SetValue(self.context.template_show_values)
            self.check_labels.SetValue(self.context.template_show_labels)
            self.combo_ops.SetSelection(
                min(self.context.template_optype, self.combo_ops.GetCount() - 1)
            )
            self.combo_param_1.SetSelection(
                min(self.context.template_param1, self.combo_param_1.GetCount() - 1)
            )
            self.combo_param_2.SetSelection(
                min(self.context.template_param2, self.combo_param_2.GetCount() - 1)
            )
            self.text_min_1.SetValue(self.context.template_min1)
            self.text_max_1.SetValue(self.context.template_max1)
            self.text_min_2.SetValue(self.context.template_min2)
            self.text_max_2.SetValue(self.context.template_max2)
            self.spin_count_1.SetValue(self.context.template_count1)
            self.spin_count_2.SetValue(self.context.template_count2)
            self.text_dim_1.SetValue(self.context.template_dim_1)
            self.text_dim_2.SetValue(self.context.template_dim_2)
            self.text_delta_1.SetValue(self.context.template_gap_1)
            self.text_delta_2.SetValue(self.context.template_gap_2)
        except (AttributeError, ValueError):
            pass

    @signal_listener("activate;device")
    def on_activate_device(self, origin, device):
        self.set_param_according_to_op(None)


class TemplateTool(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(720, 750, submenu="Laser-Tools", *args, **kwds)
        self.panel_instances = list()
        self.panel_template = TemplatePanel(
            self,
            wx.ID_ANY,
            context=self.context,
        )

        self.notebook_main = aui.AuiNotebook(
            self,
            -1,
            style=aui.AUI_NB_TAB_EXTERNAL_MOVE
            | aui.AUI_NB_SCROLL_BUTTONS
            | aui.AUI_NB_TAB_SPLIT
            | aui.AUI_NB_TAB_MOVE,
        )

        self.notebook_main.AddPage(self.panel_template, _("Generator"))

        self.panel_template.set_callback(self.set_node)

        self.add_module_delegate(self.panel_template)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_detective_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Parameter-Test"))

    def set_node(self, node):
        def sort_priority(prop):
            prop_sheet, node = prop
            return (
                getattr(prop_sheet, "priority")
                if hasattr(prop_sheet, "priority")
                else 0
            )

        if node is None:
            return
        self.Freeze()
        pages_to_instance = []
        pages_in_node = []
        found = False
        for property_sheet in self.context.lookup_all(
            f"property/{node.__class__.__name__}/.*"
        ):
            if not hasattr(property_sheet, "accepts") or property_sheet.accepts(node):
                pages_in_node.append((property_sheet, node))
                found = True
        # If we did not have any hits and the node is a reference
        # then we fall back to the master. So if in the future we
        # would have a property panel dealing with reference-nodes
        # then this would no longer apply.
        if node.type == "reference" and not found:
            snode = node.node
            found = False
            for property_sheet in self.context.lookup_all(
                f"property/{snode.__class__.__name__}/.*"
            ):
                if not hasattr(property_sheet, "accepts") or property_sheet.accepts(
                    snode
                ):
                    pages_in_node.append((property_sheet, snode))
                    found = True

        pages_in_node.sort(key=sort_priority)
        pages_to_instance.extend(pages_in_node)

        for p in self.panel_instances:
            try:
                p.pane_hide()
            except AttributeError:
                pass
            self.remove_module_delegate(p)

        # Delete all but the first page...
        while self.notebook_main.GetPageCount() > 1:
            self.notebook_main.DeletePage(1)
        for prop_sheet, instance in pages_to_instance:
            page_panel = prop_sheet(
                self.notebook_main, wx.ID_ANY, context=self.context, node=instance
            )
            try:
                name = prop_sheet.name
            except AttributeError:
                name = instance.__class__.__name__

            self.notebook_main.AddPage(page_panel, _(name))
            try:
                page_panel.set_widgets(instance)
            except AttributeError:
                pass
            self.add_module_delegate(page_panel)
            self.panel_instances.append(page_panel)
            try:
                page_panel.pane_show()
            except AttributeError:
                pass
            page_panel.Layout()
            try:
                page_panel.SetupScrolling()
            except AttributeError:
                pass

        self.Layout()
        self.Thaw()

    def window_open(self):
        pass

    def window_close(self):
        for p in self.panel_instances:
            try:
                p.pane_hide()
            except AttributeError:
                pass
        # We do not remove the delegates, they will detach with the closing of the module.
        self.panel_instances.clear()

    @staticmethod
    def submenu():
        return ("Laser-Tools", "Parameter-Test")
