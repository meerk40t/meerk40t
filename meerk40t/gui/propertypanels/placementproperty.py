"""
Display and Editing of the properties of 'place current', 'place point'
"""

import math

import wx

from meerk40t.core.units import Angle, Length
from meerk40t.gui.propertypanels.attributes import IdPanel
from meerk40t.gui.wxutils import (
    ScrolledPanel,
    StaticBoxSizer,
    TextCtrl,
    set_ctrl_value,
    wxButton,
    wxCheckBox,
    wxComboBox,
    wxStaticText,
)
from meerk40t.kernel import signal_listener
from meerk40t.svgelements import Color
from meerk40t.tools.geomstr import Geomstr

_ = wx.GetTranslation


class PlacementPanel(wx.Panel):
    """
    Display and Editing of the properties of 'place current', 'place point'
    """

    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.operation = node
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetHelpText("placement")

        prop_sizer = wx.BoxSizer(wx.HORIZONTAL)
        first_sizer = StaticBoxSizer(self, wx.ID_ANY, "", wx.HORIZONTAL)
        self.checkbox_output = wxCheckBox(self, wx.ID_ANY, _("Enable"))
        self.checkbox_output.SetToolTip(
            _("Enable this operation for inclusion in Execute Job.")
        )
        self.checkbox_output.SetValue(1)
        first_sizer.Add(self.checkbox_output, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        info_loops = wxStaticText(self, wx.ID_ANY, _("Loops:"))
        self.text_loops = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="int",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_loops.lower_limit = 1
        self.loop_sizer = StaticBoxSizer(self, wx.ID_ANY, "", wx.HORIZONTAL)
        self.loop_sizer.Add(info_loops, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.loop_sizer.Add(self.text_loops, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.text_loops.SetToolTip(_("Define how often this placement will be used"))

        prop_sizer.Add(first_sizer, 1, wx.EXPAND, 0)
        # prop_sizer.Add(self.loop_sizer, 1, wx.EXPAND, 0)
        main_sizer.Add(prop_sizer, 0, 0, 0)

        # X and Y
        self.pos_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Placement:"), wx.HORIZONTAL)
        info_x = wxStaticText(self, wx.ID_ANY, _("X:"))
        self.text_x = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_x.SetToolTip(_("X-Coordinate of placement"))
        info_y = wxStaticText(self, wx.ID_ANY, _("Y:"))
        self.text_y = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_y.SetToolTip(_("Y-Coordinate of placement"))
        self.pos_sizer.Add(info_x, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.pos_sizer.Add(self.text_x, 1, wx.EXPAND, 0)
        self.pos_sizer.Add(info_y, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.pos_sizer.Add(self.text_y, 1, wx.EXPAND, 0)

        # Rotation
        self.rot_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Rotation:"), wx.HORIZONTAL)
        self.text_rot = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="angle",
            style=wx.TE_PROCESS_ENTER,
        )
        self.rot_sizer.Add(self.text_rot, 1, wx.EXPAND, 0)
        self.slider_angle = wx.Slider(self, wx.ID_ANY, 0, 0, 360)
        self.rot_sizer.Add(self.slider_angle, 3, wx.EXPAND, 0)
        ttip = _(
            "The to be plotted elements can be rotated around the defined coordinate"
        )
        self.text_rot.SetToolTip(ttip)
        self.slider_angle.SetToolTip(ttip)

        pos_rot_sizer = wx.BoxSizer(wx.HORIZONTAL)
        pos_rot_sizer.Add(self.pos_sizer, 1, wx.EXPAND, 0)
        pos_rot_sizer.Add(self.rot_sizer, 1, wx.EXPAND, 0)
        main_sizer.Add(pos_rot_sizer, 0, wx.EXPAND, 0)

        self.grid_sizer_1 = StaticBoxSizer(
            self, wx.ID_ANY, _("Repetitions in X-direction"), wx.HORIZONTAL
        )
        info_x1 = wxStaticText(self, wx.ID_ANY, _("Repeats:"))
        self.text_repeats_x = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="int",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_repeats_x.lower_limit = 0
        info_x2 = wxStaticText(self, wx.ID_ANY, _("Gap:"))
        self.text_gap_x = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_gap_x.SetToolTip(_("Gap in X-direction"))
        self.grid_sizer_1.Add(info_x1, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.grid_sizer_1.Add(self.text_repeats_x, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.grid_sizer_1.Add(info_x2, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.grid_sizer_1.Add(self.text_gap_x, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.grid_sizer_2 = StaticBoxSizer(
            self, wx.ID_ANY, _("Repetitions in Y-direction"), wx.HORIZONTAL
        )
        info_y1 = wxStaticText(self, wx.ID_ANY, _("Repeats:"))
        self.text_repeats_y = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="int",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_repeats_y.lower_limit = 0
        info_y2 = wxStaticText(self, wx.ID_ANY, _("Gap:"))
        self.text_gap_y = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_repeats_x.SetToolTip(
            _("How many repetitions in X-direction?\n0 = As many as possible")
        )
        self.text_repeats_y.SetToolTip(
            _("How many repetitions in Y-direction?\n0 = As many as possible")
        )
        self.text_gap_x.SetToolTip(_("Gap between placements in X-direction"))
        self.text_gap_y.SetToolTip(_("Gap between placements in Y-direction"))
        self.grid_sizer_2.Add(info_y1, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.grid_sizer_2.Add(self.text_repeats_y, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.grid_sizer_2.Add(info_y2, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.grid_sizer_2.Add(self.text_gap_y, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.grid_sizer_3 = StaticBoxSizer(
            self, wx.ID_ANY, _("Selection"), wx.HORIZONTAL
        )
        info_y1 = wxStaticText(self, wx.ID_ANY, _("Start-Index:"))
        self.text_start_idx = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="int",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_start_idx.lower_limit = 0
        info_y2 = wxStaticText(self, wx.ID_ANY, _("Count:"))
        self.text_repetitions = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="int",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_start_idx.lower_limit = 0
        self.text_start_idx.SetToolTip(_("First repetition to use"))
        self.text_repetitions.SetToolTip(_("Repetitions to use (0=all)"))
        self.grid_sizer_3.Add(info_y1, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.grid_sizer_3.Add(self.text_start_idx, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.grid_sizer_3.Add(info_y2, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.grid_sizer_3.Add(self.text_repetitions, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        grid_sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        grid_sizer_1.Add(self.grid_sizer_1, 1, wx.EXPAND, 0)
        grid_sizer_1.Add(self.grid_sizer_2, 1, wx.EXPAND, 0)
        main_sizer.Add(grid_sizer_1, 0, wx.EXPAND, 0)
        grid_sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        grid_sizer_2.Add(self.loop_sizer, 1, wx.EXPAND, 0)
        grid_sizer_2.Add(self.grid_sizer_3, 1, wx.EXPAND, 0)
        main_sizer.Add(grid_sizer_2, 0, wx.EXPAND, 0)
        self.text_alternating_x = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="percent",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_alternating_y = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="percent",
            style=wx.TE_PROCESS_ENTER,
        )
        self.slider_alternating_x = wx.Slider(self, wx.ID_ANY, 0, -200, 200)
        self.slider_alternating_y = wx.Slider(self, wx.ID_ANY, 0, -200, 200)
        ttip = _(
            "Every other {area} can be displaced by a percentage of the gap in {direction}-direction\n"
            + "Useful for honeycomb- or other irregular patterns that need to overlap"
        ).format(area=_("column"), direction="X")
        self.text_alternating_x.SetToolTip(ttip)
        self.slider_alternating_x.SetToolTip(ttip)
        self.check_alt_x = wxCheckBox(self, wx.ID_ANY)
        ttip = _(
            "Rotate elements every other {area}\n" + "Useful for triangular patterns."
        ).format(area=_("column"))
        self.check_alt_x.SetToolTip(ttip)
        ttip = _(
            "Every other {area} can be displaced by a percentage of the gap in {direction}-direction\n"
            + "Useful for honeycomb- or other irregular patterns that need to overlap"
        ).format(area=_("row"), direction="Y")
        self.text_alternating_y.SetToolTip(ttip)
        self.slider_alternating_y.SetToolTip(ttip)
        self.check_alt_y = wxCheckBox(self, wx.ID_ANY)
        ttip = _(
            "Rotate elements every other {area}\n" + "Useful for triangular patterns."
        ).format(area=_("row"))
        self.check_alt_y.SetToolTip(ttip)

        self.alt_x_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("X-Displacement:"), wx.HORIZONTAL
        )
        self.alt_x_sizer.Add(self.text_alternating_x, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.alt_x_sizer.Add(self.slider_alternating_x, 3, wx.ALIGN_CENTER_VERTICAL, 0)
        self.alt_x_sizer.Add(self.check_alt_x, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.alt_y_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Y-Displacement:"), wx.HORIZONTAL
        )
        self.alt_y_sizer.Add(self.text_alternating_y, 1, wx.EXPAND, 0)
        self.alt_y_sizer.Add(self.slider_alternating_y, 3, wx.EXPAND, 0)
        self.alt_y_sizer.Add(self.check_alt_y, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        alt_sizer = wx.BoxSizer(wx.HORIZONTAL)
        alt_sizer.Add(self.alt_x_sizer, 1, wx.EXPAND, 0)
        alt_sizer.Add(self.alt_y_sizer, 1, wx.EXPAND, 0)
        main_sizer.Add(alt_sizer, 0, wx.EXPAND, 0)
        # Corner

        self.corner_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Orientation:"), wx.HORIZONTAL
        )
        info_corner = wxStaticText(self, wx.ID_ANY, _("Corner:"))
        self.combo_corner = wxComboBox(
            self,
            wx.ID_ANY,
            choices=[
                _("Top-Left"),
                _("Top-Right"),
                _("Bottom-Right"),
                _("Bottom-Left"),
                _("Center"),
            ],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_corner.SetToolTip(
            _(
                "The corner type establishes the placement of the bounding box\n"
                + "of to be plotted elements against the defined coordinate"
            )
        )
        self.corner_sizer.Add(info_corner, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.corner_sizer.Add(self.combo_corner, 1, wx.EXPAND, 0)
        info_orientation = wxStaticText(self, wx.ID_ANY, _("Orientation:"))
        self.combo_orientation = wxComboBox(
            self,
            wx.ID_ANY,
            choices=[
                _("L2R (unidirectional)"),
                _("L2R (bidirectional)"),
                _("T2B (bidirectional)"),
            ],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_orientation.SetToolTip(
            _("Orientation defines the sequence of placement points")
            + "\n"
            + _("Left to right (unidirectional)")
            + "\n"
            + _("Left to right (bidirectional)")
            + "\n"
            + _("Top to bottom (bidirectional)")
        )

        self.corner_sizer.Add(info_orientation, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.corner_sizer.Add(self.combo_orientation, 1, wx.EXPAND, 0)
        main_sizer.Add(self.corner_sizer, 0, wx.EXPAND, 0)

        main_sizer.AddSpacer(25)
        self.helper_sizer = StaticBoxSizer(
            self, wx.ID_ANY, _("Grid Helper (Tiling):"), wx.HORIZONTAL
        )

        info1 = wxStaticText(self, wx.ID_ANY, _("Shape"))
        self.shape_information = (
            (_("Quadratic"), _("Side"), self.generate_quadratic),
            (_("Hexagon"), _("Side"), self.generate_hexagon),
            (_("Circular"), _("Diameter"), self.generate_circular),
            (_("Triangular"), _("Side"), self.generate_triangular),
        )
        choices = [e[0] for e in self.shape_information]

        self.combo_shape = wxComboBox(
            self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        ttip = _("Please provide some data about the intended tiling")
        self.combo_shape.SetToolTip(ttip)

        self.dimension_info = wxStaticText(self, wx.ID_ANY, _("Dimension"))
        self.text_dimension = TextCtrl(self, wx.ID_ANY, limited=True, check="length")
        self.text_dimension.SetToolTip(ttip)

        self.btn_generate = wxButton(self, wx.ID_ANY, _("Define"))
        self.btn_generate.SetToolTip(
            _("Establishes the parameter for the selected grid-type")
        )
        self.check_generate = wxCheckBox(self, wx.ID_ANY)
        self.check_generate.SetToolTip(
            _("If set then Define will create a matching pattern too")
        )
        self.helper_sizer.Add(info1, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.helper_sizer.Add(self.combo_shape, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.helper_sizer.Add(self.dimension_info, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.helper_sizer.Add(self.text_dimension, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.helper_sizer.Add(self.btn_generate, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.helper_sizer.Add(self.check_generate, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        main_sizer.Add(self.helper_sizer, 0, wx.EXPAND, 0)

        self.info_label = wxStaticText(self, wx.ID_ANY)
        self.info_label.SetFont(
            wx.Font(
                8, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
            )
        )
        main_sizer.Add(self.info_label, 1, wx.EXPAND, 0)

        self.combo_shape.SetSelection(0)
        self.on_combo_shape(None)
        self.SetSizer(main_sizer)
        self.Layout()

        self.Bind(wx.EVT_COMBOBOX, self.on_combo_corner, self.combo_corner)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_orientation, self.combo_orientation)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_shape, self.combo_shape)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_output, self.checkbox_output)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_alternate_x, self.check_alt_x)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_alternate_y, self.check_alt_y)
        self.text_rot.SetActionRoutine(self.on_text_rot)
        self.text_alternating_x.SetActionRoutine(self.on_text_alternating_x)
        self.text_alternating_y.SetActionRoutine(self.on_text_alternating_y)
        self.text_repeats_x.SetActionRoutine(self.on_text_nx)
        self.text_repeats_y.SetActionRoutine(self.on_text_ny)
        self.text_x.SetActionRoutine(self.on_text_x)
        self.text_y.SetActionRoutine(self.on_text_y)
        self.text_gap_x.SetActionRoutine(self.on_text_dx)
        self.text_gap_y.SetActionRoutine(self.on_text_dy)
        self.text_loops.SetActionRoutine(self.on_text_loops)
        self.text_dimension.SetActionRoutine(self.on_dimension)
        self.text_start_idx.SetActionRoutine(self.on_text_start_index)
        self.text_repetitions.SetActionRoutine(self.on_text_repetitions)
        self.btn_generate.Bind(wx.EVT_BUTTON, self.on_btn_generate)
        self.Bind(wx.EVT_COMMAND_SCROLL, self.on_slider_angle, self.slider_angle)
        self.Bind(
            wx.EVT_COMMAND_SCROLL,
            self.on_slider_alternating_x,
            self.slider_alternating_x,
        )
        self.Bind(
            wx.EVT_COMMAND_SCROLL,
            self.on_slider_alternating_y,
            self.slider_alternating_y,
        )

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def accepts(self, node):
        return node.type in (
            "place current",
            "place point",
        )

    def set_info_label(self):
        if not self.operation:
            self.info_label.SetLabel("")
            return
        if self.operation.start_index is None:
            self.operation.start_index = 0
        if self.operation.repetitions is None:
            self.operation.repetitions = 0
        label = ""
        scene_width = self.context.device.view.unit_width
        scene_height = self.context.device.view.unit_height
        xloop = self.operation.nx
        if xloop == 0:  # as much as we can fit
            if abs(self.operation.dx) < 1e-6:
                xloop = 1
            else:
                x = self.operation.x
                while x + self.operation.dx < scene_width:
                    x += self.operation.dx
                    xloop += 1
        yloop = self.operation.ny
        if yloop == 0:  # as much as we can fit
            if abs(self.operation.dy) < 1e-6:
                yloop = 1
            else:
                y = self.operation.y
                while y + self.operation.dy < scene_height:
                    y += self.operation.dy
                    yloop += 1
        result = []
        sorted_result = []
        idx = 0
        for ycount in range(yloop):
            for xcount in range(xloop):
                result.append(idx)
                idx += 1

        def idx_horizontal(row, col):
            return row * xloop + col

        def idx_vertical(col, row):
            return row * xloop + col

        if self.operation.orientation == 2:
            max_outer = xloop
            max_inner = yloop
            func = idx_vertical
            hither = True
        elif self.operation.orientation == 1:
            max_outer = yloop
            max_inner = xloop
            func = idx_horizontal
            hither = True
        else:
            max_outer = yloop
            max_inner = xloop
            func = idx_horizontal
            hither = False
        p_idx = 0
        p_count = 0
        s_index = self.operation.start_index
        if s_index is None:
            s_index = 0
        if s_index > max_outer * max_inner - 1:
            s_index = max_outer * max_inner - 1
        s_count = self.operation.repetitions
        if s_count is None or s_count < 0:
            s_count = 0
        if s_count == 0:
            s_count = max_inner * max_outer

        for idx_outer in range(max_outer):
            for idx_inner in range(max_inner):
                if hither and idx_outer % 2 == 1:
                    sorted_idx = func(idx_outer, max_inner - 1 - idx_inner)
                else:
                    sorted_idx = func(idx_outer, idx_inner)
                # print (f"p_idx={p_idx}, p_count={p_count}, s_index={s_index}, s_count={s_count}")
                if p_idx >= s_index and p_count < s_count:
                    sorted_result.append(result[sorted_idx])
                    p_count += 1

                p_idx += 1
        # print (result)
        # print (sorted_result)

        idx = 0
        for ycount in range(yloop):
            lbl = ""
            for xcount in range(xloop):
                if idx in sorted_result:
                    lbl += "X "
                else:
                    lbl += "- "

                idx += 1
            label += lbl + "\n"

        self.info_label.SetLabel(label)

    def set_widgets(self, node):
        def show_hide(sizer, flag):
            sizer.ShowItems(flag)
            sizer.Show(flag)

        self.operation = node
        if self.operation is None or not self.accepts(node):
            self.Hide()
            return
        if hasattr(self.operation, "validate"):
            self.operation.validate()
        op = self.operation.type
        is_current = bool(op == "place current")
        if self.operation.output is not None:
            self.checkbox_output.SetValue(self.operation.output)
        if self.operation.output:
            flag_enabled = True
        else:
            flag_enabled = False
        self.text_rot.Enable(flag_enabled)
        self.text_x.Enable(flag_enabled)
        self.text_y.Enable(flag_enabled)
        self.text_loops.Enable(flag_enabled)
        self.slider_angle.Enable(flag_enabled)
        self.slider_alternating_x.Enable(flag_enabled)
        self.slider_alternating_y.Enable(flag_enabled)
        self.slider_alternating_x.Enable(flag_enabled)
        self.slider_alternating_y.Enable(flag_enabled)
        self.check_alt_x.Enable(flag_enabled)
        self.check_alt_y.Enable(flag_enabled)
        self.text_gap_x.Enable(flag_enabled)
        self.text_gap_y.Enable(flag_enabled)
        self.text_repeats_x.Enable(flag_enabled)
        self.text_repeats_y.Enable(flag_enabled)

        show_hide(self.pos_sizer, not is_current)
        show_hide(self.grid_sizer_1, not is_current)
        show_hide(self.grid_sizer_2, not is_current)
        show_hide(self.grid_sizer_3, not is_current)
        show_hide(self.rot_sizer, not is_current)
        show_hide(self.alt_x_sizer, not is_current)
        show_hide(self.alt_y_sizer, not is_current)
        show_hide(self.corner_sizer, not is_current)
        show_hide(self.loop_sizer, not is_current)
        show_hide(self.helper_sizer, not is_current)
        if not is_current:
            units = self.context.units_name
            if units in ("inch", "inches"):
                units = "in"

            x = self.operation.x
            if isinstance(x, str):
                x = float(Length(x))
            if x is None:
                x = 0
            y = self.operation.y
            if isinstance(y, str):
                y = float(Length(y))
            if y is None:
                y = 0
            dx = self.operation.dx
            if isinstance(dx, str):
                dx = float(Length(dx))
            if dx is None:
                dx = 0
            dy = self.operation.dy
            if isinstance(dy, str):
                dy = float(Length(dy))
            if dy is None:
                dy = 0
            ang = self.operation.rotation
            myang = Angle(ang, digits=2)
            if ang is None:
                ang = 0
            loops = self.operation.loops
            if loops is None:
                loops = 1
            fx = self.operation.alternate_rot_x
            if isinstance(fx, str):
                fx = bool(fx)
            if fx is None:
                fx = False
            fy = self.operation.alternate_rot_y
            if isinstance(fy, str):
                fy = bool(fy)
            if fy is None:
                fy = False
            self.check_alt_x.SetValue(fx)
            self.check_alt_y.SetValue(fy)
            set_ctrl_value(self.text_loops, str(loops))
            reps = self.operation.repetitions
            if reps is None:
                reps = 0
            set_ctrl_value(self.text_repetitions, str(reps))
            s_idx = self.operation.start_index
            if s_idx is None:
                s_idx = 0
            set_ctrl_value(self.text_start_idx, str(s_idx))

            set_ctrl_value(self.text_loops, str(loops))
            set_ctrl_value(self.text_repeats_x, str(self.operation.nx))
            set_ctrl_value(self.text_repeats_y, str(self.operation.ny))
            set_ctrl_value(
                self.text_x,
                f"{Length(amount=x, preferred_units=units, digits=4).preferred_length}",
            )
            set_ctrl_value(
                self.text_y,
                f"{Length(amount=y, preferred_units=units, digits=4).preferred_length}",
            )
            set_ctrl_value(
                self.text_gap_x,
                f"{Length(amount=dx, preferred_units=units, digits=4).preferred_length}",
            )
            set_ctrl_value(
                self.text_gap_y,
                f"{Length(amount=dy, preferred_units=units, digits=4).preferred_length}",
            )
            set_ctrl_value(self.text_rot, f"{myang.angle_degrees}")
            try:
                h_angle = myang.degrees
                while h_angle > self.slider_angle.GetMax():
                    h_angle -= 360
                while h_angle < self.slider_angle.GetMin():
                    h_angle += 360
                self.slider_angle.SetValue(int(h_angle))
            except ValueError:
                pass
            # print (self.operation.alternating_dx, type(self.operation.alternating_dx).__name__)
            value = int(100.0 * self.operation.alternating_dx)
            if value > 200:
                value = 200
            if value < -200:
                value = -200
            self.slider_alternating_x.SetValue(value)
            self.text_alternating_x.SetValue(f"{value}%")
            value = int(100.0 * self.operation.alternating_dy)
            if value > 200:
                value = 200
            if value < -200:
                value = -200
            self.slider_alternating_y.SetValue(value)
            self.text_alternating_y.SetValue(f"{value}%")

            corner = max(min(self.operation.corner, 4), 0)  # between 0 and 4
            self.combo_corner.SetSelection(corner)

            orientation = max(min(self.operation.orientation, 2), 0)  # between 0 and 2
            self.combo_orientation.SetSelection(orientation)
            self.set_info_label()

        self.Layout()
        self.Show()

    def on_text_rot(self):
        if self.operation is None or not hasattr(self.operation, "rotation"):
            return
        try:
            self.operation.rotation = Angle(self.text_rot.GetValue()).angle
            self.updated()
        except ValueError:
            return
        myang = Angle(self.operation.rotation)
        try:
            h_angle = myang.degrees
            while h_angle > self.slider_angle.GetMax():
                h_angle -= 360
            while h_angle < self.slider_angle.GetMin():
                h_angle += 360
            self.slider_angle.SetValue(int(h_angle))
        except ValueError:
            pass

    def on_slider_angle(self, event):  # wxGlade: HatchSettingsPanel.<event_handler>
        if self.operation is None or not hasattr(self.operation, "rotation"):
            return
        value = self.slider_angle.GetValue()
        self.text_rot.SetValue(f"{value}deg")
        self.on_text_rot()

    def on_text_alternating_x(self):
        if self.operation is None or not hasattr(self.operation, "alternating_dx"):
            return
        txt = self.text_alternating_x.GetValue().strip()
        if not txt:
            return
        if txt.endswith("%"):
            txt = txt[:-1]
        try:
            factor = float(txt) / 100.0
            self.operation.alternating_dx = factor
            self.updated()
        except ValueError:
            return
        myval = self.operation.alternating_dx
        if myval is None:
            myval = 0
        myval *= 100.0
        self.slider_alternating_x.SetValue(int(myval))

    def on_slider_alternating_x(self, event):
        if self.operation is None or not hasattr(self.operation, "alternating_dx"):
            return
        value = self.slider_alternating_x.GetValue()
        self.text_alternating_x.SetValue(f"{value}%")
        self.on_text_alternating_x()

    def on_text_alternating_y(self):
        if self.operation is None or not hasattr(self.operation, "alternating_dy"):
            return
        txt = self.text_alternating_y.GetValue().strip()
        if not txt:
            return
        if txt.endswith("%"):
            txt = txt[:-1]
        try:
            factor = float(txt) / 100.0
            self.operation.alternating_dy = factor
            self.updated()
        except ValueError:
            return
        myval = self.operation.alternating_dy
        if myval is None:
            myval = 0
        myval *= 100.0
        self.slider_alternating_y.SetValue(int(myval))

    def on_slider_alternating_y(self, event):
        if self.operation is None or not hasattr(self.operation, "alternating_dy"):
            return
        value = self.slider_alternating_y.GetValue()
        self.text_alternating_y.SetValue(f"{value}%")
        self.on_text_alternating_y()

    def on_check_alternate_x(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        f = bool(self.check_alt_x.GetValue())
        if self.operation.alternate_rot_x != f:
            self.operation.alternate_rot_x = f
            self.context.elements.signal("element_property_update", self.operation)

    def on_check_alternate_y(
        self, event=None
    ):  # wxGlade: OperationProperty.<event_handler>
        f = bool(self.check_alt_y.GetValue())
        if self.operation.alternate_rot_y != f:
            self.operation.alternate_rot_y = f
            self.context.elements.signal("element_property_update", self.operation)

    def on_check_output(self, event=None):  # wxGlade: OperationProperty.<event_handler>
        if self.operation.output != bool(self.checkbox_output.GetValue()):
            self.operation.output = bool(self.checkbox_output.GetValue())
            self.context.elements.signal("element_property_update", self.operation)
        flag = self.operation.output
        self.text_x.Enable(flag)
        self.text_y.Enable(flag)
        self.text_rot.Enable(flag)
        self.slider_angle.Enable(flag)
        self.combo_corner.Enable(flag)
        self.combo_orientation.Enable(flag)

    def on_combo_corner(self, event):
        if self.operation is None or not hasattr(self.operation, "corner"):
            return
        corner = self.combo_corner.GetSelection()
        if corner < 0:
            return
        if self.operation.corner != corner:
            self.operation.corner = corner
            self.updated()

    def on_combo_orientation(self, event):
        if self.operation is None or not hasattr(self.operation, "orientation"):
            return
        orientation = self.combo_orientation.GetSelection()
        if orientation < 0:
            return
        if self.operation.orientation != orientation:
            self.operation.orientation = orientation
            self.updated()

    def on_text_x(self):
        if self.operation is None or not hasattr(self.operation, "x"):
            return
        try:
            x = float(Length(self.text_x.GetValue()))
        except ValueError:
            return
        if self.operation.x != x:
            self.operation.x = x
            self.updated()

    def on_text_dx(self):
        if self.operation is None or not hasattr(self.operation, "dx"):
            return
        try:
            x = float(Length(self.text_gap_x.GetValue()))
        except ValueError:
            return
        if self.operation.dx != x:
            self.operation.dx = x
            self.updated()

    def on_text_y(self):
        if self.operation is None or not hasattr(self.operation, "y"):
            return
        try:
            y = float(Length(self.text_y.GetValue()))
        except ValueError:
            return
        if self.operation.y != y:
            self.operation.y = y
            self.updated()

    def on_text_dy(self):
        if self.operation is None or not hasattr(self.operation, "dy"):
            return
        try:
            y = float(Length(self.text_gap_y.GetValue()))
        except ValueError:
            return
        if self.operation.dy != y:
            self.operation.dy = y
            self.updated()

    def on_text_loops(self):
        if self.operation is None or not hasattr(self.operation, "loops"):
            return
        try:
            loops = int(self.text_loops.GetValue())
            if loops < 1:
                loops = 1
        except ValueError:
            return
        if self.operation.loops != loops:
            self.operation.loops = loops
            self.updated()

    def on_text_nx(self):
        if self.operation is None or not hasattr(self.operation, "nx"):
            return
        try:
            nx = int(self.text_repeats_x.GetValue())
            if nx < 0:
                nx = 0
        except ValueError:
            return
        if self.operation.nx != nx:
            self.operation.nx = nx
            self.set_info_label()
            self.updated()

    def on_text_ny(self):
        if self.operation is None or not hasattr(self.operation, "ny"):
            return
        try:
            ny = int(self.text_repeats_y.GetValue())
            if ny < 0:
                ny = 0
        except ValueError:
            return
        if self.operation.ny != ny:
            self.operation.ny = ny
            self.set_info_label()
            self.updated()

    def on_text_start_index(self):
        if self.operation is None or not hasattr(self.operation, "start_index"):
            return
        try:
            start = int(self.text_start_idx.GetValue())
        except ValueError:
            return
        if self.operation.start_index != start:
            self.operation.start_index = start
            self.set_info_label()
            self.updated()

    def on_text_repetitions(self):
        if self.operation is None or not hasattr(self.operation, "repetitions"):
            return
        try:
            start = int(self.text_repetitions.GetValue())
        except ValueError:
            return
        if self.operation.repetitions != start:
            self.operation.repetitions = start
            self.set_info_label()
            self.updated()

    def generate_quadratic(self, dimension, sx, sy):
        scene_width = self.context.device.view.width
        scene_height = self.context.device.view.height
        x = sx
        y = sy
        nx = 0
        ny = 0
        dx = dimension
        dy = dimension
        alt_x = 0
        alt_y = 0
        flag_x = False
        flag_y = False
        geom = Geomstr.rect(sx, sy, dimension, dimension)
        # points = (
        #     sx + 1j * sy,
        #     sx + dimension + 1j * sy,
        #     sx + dimension + 1j * (sy + dimension),
        #     sx + 1j * (sy + dimension),
        #     sx + 1j * sy,
        # )
        # geom.polyline(points)
        # geom.end()
        while x + dimension <= scene_width:
            x += dimension
            nx += 1
        while y + dimension <= scene_height:
            y += dimension
            ny += 1
        if nx == 0:
            nx = 1
        if ny == 0:
            ny = 1
        return nx, ny, dx, dy, alt_x, alt_y, flag_x, flag_y, geom

    def generate_triangular(self, dimension, sx, sy):
        scene_width = self.context.device.view.width
        scene_height = self.context.device.view.height
        x = sx
        y = sy
        nx = 0
        ny = 0
        dx = 0.5 * dimension
        dy = 0.5 * math.sqrt(3) * dimension
        alt_x = 0
        alt_y = 0
        flag_x = True
        flag_y = False

        geom = Geomstr()
        points = (
            sx + 1j * (sy + dy),
            sx + dimension + 1j * (sy + dy),
            sx + 0.5 * dimension + 1j * sy,
            sx + 1j * (sy + dy),
        )
        geom.polyline(points)
        geom.end()

        while x + dimension <= scene_width:
            x += dx
            nx += 1
        while y + dimension <= scene_height:
            y += dy
            ny += 1
        if nx == 0:
            nx = 1
        if ny == 0:
            ny = 1
        return nx, ny, dx, dy, alt_x, alt_y, flag_x, flag_y, geom

    def generate_circular(self, dimension, sx, sy):
        scene_width = self.context.device.view.width
        scene_height = self.context.device.view.height
        x = sx
        y = sy
        nx = 0
        ny = 0
        radius = dimension / 2.0
        # cos(30°) * d
        dx = math.cos(math.tau / 12) * dimension
        dy = dimension
        alt_x = 0
        alt_y = 0.5
        flag_x = False
        flag_y = False

        geom = Geomstr.circle(radius, sx + radius, sy + radius, slices=4)
        while x + dimension <= scene_width:
            x += dx
            nx += 1

        while y + dimension + radius <= scene_height:
            y += dy
            ny += 1

        if nx == 0:
            nx = 1
        if ny == 0:
            ny = 1
        return nx, ny, dx, dy, alt_x, alt_y, flag_x, flag_y, geom

    def generate_hexagon(self, dimension, sx, sy):
        scene_width = self.context.device.view.width
        scene_height = self.context.device.view.height
        dim_x = 2 * dimension
        dim_y = math.sqrt(3) * dimension
        x = sx
        y = sy
        nx = 0
        ny = 0
        flag_x = False
        flag_y = False

        geom = Geomstr()
        points = (
            sx + 0.5 * dimension + 1j * sy,
            sx + 1.5 * dimension + 1j * sy,
            sx + 2 * dimension + 1j * (sy + 0.5 * dim_y),
            sx + 1.5 * dimension + 1j * (sy + dim_y),
            sx + 0.5 * dimension + 1j * (sy + dim_y),
            sx + 1j * (sy + 0.5 * dim_y),
            sx + 0.5 * dimension + 1j * sy,
        )
        geom.polyline(points)
        geom.end()

        dx = 1.5 * dimension
        dy = math.sqrt(3.0) * dimension
        alt_x = 0
        alt_y = 0.5
        while x + dim_x <= scene_width:
            x += dx
            nx += 1
        while y + dim_y <= scene_height:
            y += dy
            ny += 1
        if nx == 0:
            nx = 1
        if ny == 0:
            ny = 1

        return nx, ny, dx, dy, alt_x, alt_y, flag_x, flag_y, geom

    def validate_tesselation(self):
        flag = True
        idx = self.combo_shape.GetSelection()
        if idx < 0:
            flag = False
        s = self.text_dimension.GetValue()
        if s:
            # try:
            #     val = float(Length(s))
            # except ValueError:
            #     val = 0
            if flag <= 0:
                flag = False
        else:
            flag = False
        self.btn_generate.Enable(flag)

    def on_combo_shape(self, event):
        idx = self.combo_shape.GetSelection()
        if idx < 0:
            s = _("Dimension")
        else:
            s = self.shape_information[idx][1]
        self.dimension_info.SetLabel(s)
        self.Layout()
        self.validate_tesselation()

    def on_dimension(self, *args):
        self.validate_tesselation()

    def on_btn_generate(self, event):
        if self.operation is None or not hasattr(self.operation, "x"):
            return
        shape = self.combo_shape.GetSelection()
        if shape < 0:
            return
        s_dimen = self.text_dimension.GetValue()
        if s_dimen == "":
            return
        try:
            dimens = float(Length(s_dimen))
            if dimens == 0:
                return
        except ValueError:
            return
        try:
            sx = float(Length(self.text_x.GetValue()))
            sy = float(Length(self.text_y.GetValue()))
        except ValueError:
            return
        function = self.shape_information[shape][2]
        nx, ny, dx, dy, alt_x, alt_y, flag_x, flag_y, geom = function(dimens, sx, sy)
        self.operation.x = sx
        self.operation.y = sy
        self.operation.nx = nx
        self.operation.ny = ny
        self.operation.dx = dx
        self.operation.dy = dy
        self.operation.alternating_dx = alt_x
        self.operation.alternating_dy = alt_y
        self.operation.alternate_rot_x = flag_x
        self.operation.alternate_rot_y = flag_y
        self.operation.corner = 0
        self.operation.rotation = 0
        self.updated()
        if self.check_generate.GetValue() and geom is not None:
            # _("Create template")
            with self.context.elements.undoscope("Create template"):
                node = self.context.elements.elem_branch.add(
                    type="elem path",
                    geometry=geom,
                    stroke=Color("blue"),
                    stroke_width=1000,
                    label="Template",
                )
                data = [node]
                if self.context.elements.classify_new:
                    self.context.elements.classify(data)
            self.context.root.signal("refresh_scene", "Scene")

    def updated(self):
        self.context.elements.signal("element_property_reload", self.operation)
        self.context.elements.signal("refresh_scene", "Scene")


class PlacementParameterPanel(ScrolledPanel):
    name = _("Properties")
    priority = -1

    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: ParameterPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
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

        self.place_panel = PlacementPanel(self, wx.ID_ANY, context=context, node=node)
        param_sizer.Add(self.place_panel, 0, wx.EXPAND, 0)
        self.panels.append(self.place_panel)

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
