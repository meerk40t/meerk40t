"""
This file contains routines to create some test patterns
to establish the correct kerf size of your laser
"""

import wx

from meerk40t.core.node.op_cut import CutOpNode
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.node.op_raster import RasterOpNode
from meerk40t.core.units import UNITS_PER_PIXEL, Length
from meerk40t.gui.icons import STD_ICON_SIZE, icons8_detective_50, icons8_hinges_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import StaticBoxSizer, TextCtrl
from meerk40t.svgelements import Color, Matrix, Polyline

_ = wx.GetTranslation


class KerfPanel(wx.Panel):
    """
    UI for KerfTest, allows setting of parameters
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        self.text_speed = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_speed.set_range(0, 1000)
        self.text_power = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_power.set_range(0, 1000)

        self.radio_pattern = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Pattern"),
            choices=(
                _("Rectangular (box joints)"),
                _("Circular (inlays)"),
                _("Slider"),
            ),
        )
        self.spin_count = wx.SpinCtrl(self, wx.ID_ANY, initial=5, min=1, max=100)
        self.text_min = TextCtrl(self, wx.ID_ANY, limited=True, check="length")
        self.text_max = TextCtrl(self, wx.ID_ANY, limited=True, check="length")
        self.text_dim = TextCtrl(self, wx.ID_ANY, limited=True, check="length")
        # self.text_dim.set_range(0, 50)
        self.text_delta = TextCtrl(self, wx.ID_ANY, limited=True, check="length")
        # self.text_delta.set_range(0, 50)

        self.button_create = wx.Button(self, wx.ID_ANY, _("Create Pattern"))
        self.button_create.SetBitmap(icons8_detective_50.GetBitmap(resize=25))

        self._set_layout()
        self._set_logic()
        self._set_defaults()
        # Check for appropriate values
        self.on_valid_values(None)
        self.Layout()

    def _set_defaults(self):
        self.radio_pattern.SetSelection(0)
        self.spin_count.SetValue(5)
        self.text_dim.SetValue("20mm")
        self.text_delta.SetValue("5mm")
        self.text_speed.SetValue("5")
        self.text_power.SetValue("1000")
        self.text_min.SetValue("0.05mm")
        self.text_max.SetValue("0.25mm")

    def _set_logic(self):
        self.button_create.Bind(wx.EVT_BUTTON, self.on_button_generate)
        self.spin_count.Bind(wx.EVT_SPINCTRL, self.on_valid_values)
        self.text_delta.Bind(wx.EVT_TEXT, self.on_valid_values)
        self.text_min.Bind(wx.EVT_TEXT, self.on_valid_values)
        self.text_max.Bind(wx.EVT_TEXT, self.on_valid_values)
        self.text_dim.Bind(wx.EVT_TEXT, self.on_valid_values)
        self.text_dim.Bind(wx.EVT_TEXT, self.on_valid_values)
        self.text_speed.Bind(wx.EVT_TEXT, self.on_valid_values)
        self.text_power.Bind(wx.EVT_TEXT, self.on_valid_values)

    def _set_layout(self):
        def size_it(ctrl, value):
            ctrl.SetMaxSize(wx.Size(int(value), -1))
            ctrl.SetMinSize(wx.Size(int(value * 0.75), -1))
            ctrl.SetSize(wx.Size(value, -1))

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_cutop = StaticBoxSizer(self, wx.ID_ANY, _("Cut-Operation"), wx.HORIZONTAL)
        sizer_speed = StaticBoxSizer(self, wx.ID_ANY, _("Speed"), wx.HORIZONTAL)
        sizer_power = StaticBoxSizer(self, wx.ID_ANY, _("Power"), wx.HORIZONTAL)
        sizer_speed.Add(self.text_speed, 1, wx.EXPAND, 0)
        sizer_power.Add(self.text_power, 1, wx.EXPAND, 0)
        sizer_cutop.Add(sizer_speed, 1, wx.EXPAND, 0)
        sizer_cutop.Add(sizer_power, 1, wx.EXPAND, 0)

        sizer_param = StaticBoxSizer(self, wx.ID_ANY, _("Parameters"), wx.VERTICAL)

        hline_type = wx.BoxSizer(wx.HORIZONTAL)
        hline_type.Add(self.radio_pattern, 0, wx.EXPAND, 0)
        hline_count = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Count:"))
        self.info_distance = wx.StaticText(self, wx.ID_ANY, "")
        size_it(mylbl, 85)
        hline_count.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_count.Add(self.spin_count, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_count.Add(self.info_distance, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_min = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Minimum:"))
        size_it(mylbl, 85)
        hline_min.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_min.Add(self.text_min, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_max = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Maximum:"))
        size_it(mylbl, 85)
        hline_max.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_max.Add(self.text_max, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_dim = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Size:"))
        size_it(mylbl, 85)
        hline_dim.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_dim.Add(self.text_dim, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_delta = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Delta:"))
        size_it(mylbl, 85)
        hline_delta.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_delta.Add(self.text_delta, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_param.Add(hline_type, 0, wx.EXPAND, 0)
        sizer_param.Add(hline_count, 0, wx.EXPAND, 0)
        sizer_param.Add(hline_min, 0, wx.EXPAND, 0)
        sizer_param.Add(hline_max, 0, wx.EXPAND, 0)
        sizer_param.Add(hline_dim, 0, wx.EXPAND, 0)
        sizer_param.Add(hline_delta, 0, wx.EXPAND, 0)

        sizer_info = StaticBoxSizer(self, wx.ID_ANY, _("How to use it"), wx.VERTICAL)
        infomsg = _(
            "If you want to produce cut out shapes with *exact* dimensions"
            + " after the burn, then you need to take half the width of the"
            + " laserbeam into consideration (aka Kerf compensation).\n"
            + "This routine will create a couple of testshapes for you to establish this value.\n"
            + "After you cut these shapes out you need to try to fit the shapes with the same"
            + " label together. Choose the pair that has a perfect fit and use the"
            + " label as your kerf-compensation value."
        )
        info_label = wx.TextCtrl(
            self, wx.ID_ANY, value=infomsg, style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        info_label.SetBackgroundColour(self.GetBackgroundColour())
        sizer_info.Add(info_label, 1, wx.EXPAND, 0)

        main_sizer.Add(sizer_cutop, 0, wx.EXPAND, 1)
        main_sizer.Add(sizer_param, 0, wx.EXPAND, 1)
        main_sizer.Add(self.button_create, 0, 0, 0)
        main_sizer.Add(sizer_info, 1, wx.EXPAND, 0)
        main_sizer.Layout()

        self.text_min.SetToolTip(_("Minimum value for Kerf"))
        self.text_max.SetToolTip(_("Maximum value for Kerf"))
        self.text_dim.SetToolTip(_("Dimension of the to be created pattern"))
        self.text_delta.SetToolTip(_("Horizontal gap between patterns"))

        self.button_create.SetToolTip(_("Create a test-pattern with your values"))

        self.SetSizer(main_sizer)

    def on_button_close(self, event):
        self.context("window close Kerftest\n")

    def on_valid_values(self, event):
        def valid_length(control):
            res = False
            d = control.GetValue()
            if d != "":
                try:
                    test = float(Length(d))
                    res = True
                except ValueError:
                    pass
            return res

        def valid_float(control, minv, maxv):
            res = False
            d = control.GetValue()
            if d != "":
                try:
                    test = float(d)
                    if minv <= test <= maxv:
                        res = True
                except ValueError:
                    pass
            return res

        is_valid = True
        count = self.spin_count.GetValue()
        if count < 1:
            is_valid = False
        if not valid_length(self.text_delta):
            is_valid = False
        if not valid_length(self.text_dim):
            is_valid = False
        if not valid_length(self.text_min):
            is_valid = False
        if not valid_length(self.text_max):
            is_valid = False
        if not valid_float(self.text_power, 0, 1000):
            is_valid = False
        if not valid_float(self.text_speed, 0, 1000):
            is_valid = False

        if is_valid:
            try:
                minv = float(Length(self.text_min.GetValue()))
                maxv = float(Length(self.text_max.GetValue()))
                if minv > maxv or minv < 0 or maxv < 0:
                    is_valid = False
            except ValueError:
                is_valid = False
        if is_valid:
            delta = maxv - minv
            if count > 1:
                delta /= count - 1
            self.info_distance.SetLabel(
                _("Every {dist}").format(dist=Length(delta, digits=3).length_mm)
            )
        else:
            self.info_distance.SetLabel("---")
        self.button_create.Enable(is_valid)

    def on_button_generate(self, event):
        def make_color(idx, maxidx, colidx):
            r = 0
            g = 0
            b = 0
            if maxidx < 8:
                colrange = 8
            if maxidx < 16:
                colrange = 16
            elif maxidx < 32:
                colrange = 32
            elif maxidx < 64:
                colrange = 64
            elif maxidx < 128:
                colrange = 128
            else:
                colrange = 255
            colfactor = 256 / colrange
            if colidx == "r":
                r = 255 - int(colfactor * colrange / maxidx * idx)
            elif colidx == "g":
                g = 255 - int(colfactor * colrange / maxidx * idx)
            elif colidx == "b":
                b = 255 - int(colfactor * colrange / maxidx * idx)
            mycolor = Color(r, g, b)
            return mycolor

        def clear_all():
            self.context.elements.clear_operations(fast=True)
            self.context.elements.clear_elements(fast=True)

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

        def create_operations():
            kerf = minv
            if count < 2:
                delta = maxv - minv
            else:
                delta = (maxv - minv) / (count - 1)
            operation_branch = self.context.elements.op_branch
            element_branch = self.context.elements.elem_branch
            text_op = RasterOpNode()
            text_op.color = Color("black")
            text_op.label = "Descriptions"
            operation_branch.add_node(text_op)
            x_offset = y_offset = float(Length("5mm"))
            xx = x_offset
            yy = y_offset
            textfactor = pattern_size / float(Length("20mm"))
            if textfactor > 2:
                textfactor = 2
            for idx in range(count):
                kerlen = Length(kerf)
                op_col_inner = make_color(idx, count, "g")
                op_col_outer = make_color(idx, count, "r")
                inner_op = CutOpNode(label=f"Inner {shortened(kerlen.mm, 3)}mm")
                inner_op.color = op_col_inner
                inner_op.speed = op_speed
                inner_op.power = op_power
                inner_op.kerf = -1 * kerf
                outer_op = CutOpNode(label=f"Outer {shortened(kerlen.mm, 3)}mm")
                outer_op.color = op_col_outer
                outer_op.speed = op_speed
                outer_op.power = op_power
                outer_op.kerf = kerf
                if rectangular:
                    operation_branch.add_node(outer_op)

                    shape1 = Polyline(
                        (
                            (xx + 0.0 * pattern_size, yy + 0.0 * pattern_size),
                            (xx + 1.0 * pattern_size, yy + 0.0 * pattern_size),
                            (xx + 1.0 * pattern_size, yy + 0.75 * pattern_size),
                            (xx + 0.75 * pattern_size, yy + 0.75 * pattern_size),
                            (xx + 0.75 * pattern_size, yy + 0.5 * pattern_size),
                            (xx + 0.25 * pattern_size, yy + 0.5 * pattern_size),
                            (xx + 0.25 * pattern_size, yy + 0.75 * pattern_size),
                            (xx + 0.0 * pattern_size, yy + 0.75 * pattern_size),
                            (xx + 0.0 * pattern_size, yy + 0.0 * pattern_size),
                        )
                    )
                    elem1 = "elem polyline"
                    node = element_branch.add(shape=shape1, type=elem1)
                    node.stroke = op_col_outer
                    node.stroke_width = 500
                    outer_op.add_reference(node, 0)

                    node = element_branch.add(
                        text=f"{shortened(kerlen.mm, 3)}mm",
                        matrix=Matrix(
                            f"translate({xx + 0.5 * pattern_size}, {yy + 0.25 * pattern_size})"
                            + f" scale({0.5 * textfactor * UNITS_PER_PIXEL})"
                        ),
                        anchor="middle",
                        fill=Color("black"),
                        type="elem text",
                    )
                    text_op.add_reference(node, 0)

                    shape2 = Polyline(
                        (
                            (xx + 0.0 * pattern_size, yy + (1.1 + 0.5) * pattern_size),
                            (xx + 0.25 * pattern_size, yy + (1.1 + 0.5) * pattern_size),
                            (
                                xx + 0.25 * pattern_size,
                                yy + (1.1 + 0.25) * pattern_size,
                            ),
                            (
                                xx + 0.75 * pattern_size,
                                yy + (1.1 + 0.25) * pattern_size,
                            ),
                            (xx + 0.75 * pattern_size, yy + (1.1 + 0.5) * pattern_size),
                            (xx + 1.0 * pattern_size, yy + (1.1 + 0.5) * pattern_size),
                            (xx + 1.0 * pattern_size, yy + (1.1 + 1.0) * pattern_size),
                            (xx + 0.0 * pattern_size, yy + (1.1 + 1.0) * pattern_size),
                            (xx + 0.0 * pattern_size, yy + (1.1 + 0.5) * pattern_size),
                        )
                    )
                    elem2 = "elem polyline"
                    node = element_branch.add(shape=shape2, type=elem2)
                    node.stroke = op_col_outer
                    node.stroke_width = 500
                    outer_op.add_reference(node, 0)

                    node = element_branch.add(
                        text=f"{shortened(kerlen.mm, 3)}mm",
                        matrix=Matrix(
                            f"translate({xx + 0.5 * pattern_size}, {yy + (1.1 + 0.7) * pattern_size})"
                            + f" scale({0.5 * textfactor * UNITS_PER_PIXEL})"
                        ),
                        anchor="middle",
                        fill=Color("black"),
                        type="elem text",
                    )
                    text_op.add_reference(node, 0)
                else:
                    operation_branch.add_node(outer_op)
                    operation_branch.add_node(inner_op)
                    node = element_branch.add(
                        x=xx,
                        y=yy,
                        width=pattern_size,
                        height=pattern_size,
                        stroke=op_col_outer,
                        stroke_width=500,
                        type="elem rect",
                    )
                    # Needs to be outer
                    outer_op.add_reference(node, 0)

                    node = element_branch.add(
                        cx=xx + 0.5 * pattern_size,
                        cy=yy + 0.5 * pattern_size,
                        rx=0.3 * pattern_size,
                        ry=0.3 * pattern_size,
                        stroke=op_col_inner,
                        stroke_width=500,
                        type="elem ellipse",
                    )
                    inner_op.add_reference(node, 0)

                    node = element_branch.add(
                        text=f"{shortened(kerlen.mm, 3)}mm",
                        matrix=Matrix(
                            f"translate({xx + 0.5 * pattern_size}, {yy + 0.8 * pattern_size})"
                            + f" scale({0.5 * textfactor * UNITS_PER_PIXEL})"
                        ),
                        anchor="middle",
                        fill=Color("black"),
                        type="elem text",
                    )
                    text_op.add_reference(node, 0)

                    node = element_branch.add(
                        cx=xx + 0.5 * pattern_size,
                        cy=yy + (1.1 + 0.5) * pattern_size,
                        rx=0.3 * pattern_size,
                        ry=0.3 * pattern_size,
                        stroke=op_col_outer,
                        stroke_width=500,
                        type="elem ellipse",
                    )
                    outer_op.add_reference(node, 0)

                    node = element_branch.add(
                        text=f"{shortened(kerlen.mm, 3)}mm",
                        matrix=Matrix(
                            f"translate({xx + 0.5 * pattern_size}, {yy + (1.1 + 0.4) * pattern_size})"
                            + f" scale({0.5 * textfactor * UNITS_PER_PIXEL})"
                        ),
                        anchor="middle",
                        fill=Color("black"),
                        type="elem text",
                    )
                    text_op.add_reference(node, 0)

                kerf += delta
                xx += pattern_size
                xx += gap_size
            node = element_branch.add(
                text=f"Kerf-Test (speed={op_speed}mm/s, power={op_power/10.0:.0f}%)",
                matrix=Matrix(
                    f"translate({0 + x_offset}, {2.2 * pattern_size + y_offset})"
                    + f" scale({UNITS_PER_PIXEL})"
                ),
                fill=Color("black"),
                type="elem text",
            )
            text_op.add_reference(node, 0)

        def create_slider():
            num_cuts = 20
            pat_size = 2
            pat_wid = 0.5
            border = 1.0
            pattern_size = float(Length(f"{pat_size}cm"))
            pattern_width = float(Length(f"{pat_wid}cm"))
            inner_border = float(Length(f"{border}cm"))

            operation_branch = self.context.elements.op_branch
            element_branch = self.context.elements.elem_branch

            cut_op = CutOpNode(label=f"Regular cut (no kerf)")
            cut_op.color = Color("red")
            cut_op.speed = op_speed
            cut_op.power = op_power
            cut_op.kerf = 0
            engrave_op = EngraveOpNode(label=f"Markings")
            engrave_op.color = Color("blue")
            cut_op.kerf = 0
            text_op = RasterOpNode()
            text_op.color = Color("black")
            text_op.label = "Descriptions"
            # instruction_op = RasterOpNode()
            # instruction_op.color = Color("cyan")
            # instruction_op.label = "Instructions"
            # instruction_op.output = False
            # operation_branch.add_node(instruction_op)
            operation_branch.add_node(text_op)
            operation_branch.add_node(cut_op)
            operation_branch.add_node(engrave_op)
            x_offset = float(Length("1cm"))
            y_offset = float(Length("1cm"))

            # First the engraves
            group_markers = element_branch.add(type="group", label="Markers")

            # The outer box
            wd = 2 * inner_border + (num_cuts - 1) * pattern_width
            ht = 2 * inner_border + pattern_size
            node = element_branch.add(
                x=x_offset,
                y=y_offset,
                width=wd,
                height=ht,
                stroke=engrave_op.color,
                stroke_width=500,
                type="elem rect",
                label="Outer box",
            )
            engrave_op.add_reference(node, 0)
            group_markers.append_child(node)

            # The scales
            # 0.1 mm will be num_cuts x 0.1 mm
            # The compensation is just half of it
            x_val = x_offset + inner_border + (num_cuts - 1) * pattern_width
            y_val = y_offset + inner_border + pattern_size
            kerfval = 0
            idx = 0
            ticklen = float(Length("4mm"))
            tickdist = float(Length("0.02mm"))
            xfactor = tickdist * num_cuts / 2.0
            textsize = UNITS_PER_PIXEL / 5.0
            group_upper = element_branch.add(type="group", label="Upper marks")
            group_lower = element_branch.add(type="group", label="Lower marks")

            group_markers.append_child(group_upper)
            group_markers.append_child(group_lower)

            for idx in range(51):
                if idx % 10 == 0:
                    yfactor = 1.0
                    zfactor = 0.6
                elif idx % 5 == 0:
                    yfactor = 0.6
                    zfactor = 1.0
                else:
                    yfactor = 0
                    zfactor = 0
                if yfactor != 0:
                    shape = Polyline(
                        (x_val - idx * xfactor, y_val),
                        (x_val - idx * xfactor, y_val + yfactor * ticklen),
                    )
                    node = element_branch.add(
                        shape=shape,
                        type="elem polyline",
                        label=f"Lower Tick {shortened(Length(kerfval).mm, 3)}mm",
                    )
                    node.stroke = engrave_op.color
                    node.stroke_width = 500
                    engrave_op.add_reference(node, 0)
                    group_lower.append_child(node)
                if zfactor != 0:
                    y = y_offset + inner_border
                    shape = Polyline(
                        (x_val - idx * xfactor, y),
                        (x_val - idx * xfactor, y - zfactor * ticklen),
                    )
                    node = element_branch.add(
                        shape=shape,
                        type="elem polyline",
                        label=f"Upper Tick {shortened(Length(kerfval).mm, 3)}mm",
                    )
                    node.stroke = engrave_op.color
                    node.stroke_width = 500
                    engrave_op.add_reference(node, 0)
                    group_upper.append_child(node)
                x = x_val - idx * xfactor
                if idx % 10 == 0:
                    y = y_val + 1.25 * ticklen
                    node = element_branch.add(
                        text=f"{shortened(Length(kerfval).mm, 3)}",
                        matrix=Matrix(f"translate({x}, {y}) scale({textsize})"),
                        anchor="middle",
                        fill=Color("black"),
                        type="elem text",
                    )
                    text_op.add_reference(node, 0)
                    group_lower.append_child(node)
                elif idx % 5 == 0:
                    y = y_offset + inner_border - 1.45 * ticklen
                    node = element_branch.add(
                        text=f"{shortened(Length(kerfval).mm, 3)}",
                        matrix=Matrix(f"translate({x}, {y}) scale({textsize})"),
                        anchor="middle",
                        fill=Color("black"),
                        type="elem text",
                    )
                    text_op.add_reference(node, 0)
                    group_upper.append_child(node)

                idx += 1
                kerfval += tickdist
            x = x_offset + inner_border + (num_cuts - 5) * pattern_width
            y = y_offset + 0.10 * inner_border
            node = element_branch.add(
                text="Kerf-Compensation [mm]",
                matrix=Matrix(f"translate({x}, {y})" + f" scale({1.5 * textsize})"),
                fill=Color("black"),
                type="elem text",
            )
            text_op.add_reference(node, 0)
            group_upper.append_child(node)

            x = x_offset + inner_border + (num_cuts - 5) * pattern_width
            y = y_offset + 1.75 * inner_border + pattern_size
            node = element_branch.add(
                text="Kerf-Compensation [mm]",
                matrix=Matrix(f"translate({x}, {y})" + f" scale({1.5 * textsize})"),
                fill=Color("black"),
                type="elem text",
            )
            text_op.add_reference(node, 0)
            group_lower.append_child(node)

            x = x_offset + inner_border + 0.5 * pattern_width
            y = x_offset + inner_border + 0.5 * pattern_size
            shape = Polyline(
                (x + 3 * pattern_width, y - 0.25 * pattern_size),
                (x, y),
                (x + 3 * pattern_width, y + 0.25 * pattern_size),
            )
            node = element_branch.add(
                shape=shape, type="elem polyline", label="arrow_head"
            )
            node.stroke = engrave_op.color
            node.stroke_width = 500
            engrave_op.add_reference(node, 0)
            group_markers.append_child(node)

            shape = Polyline(
                (x, y),
                (x + (num_cuts - 2) * pattern_width, y),
            )
            node = element_branch.add(
                shape=shape, type="elem polyline", label="arrow_body"
            )
            node.stroke = engrave_op.color
            node.stroke_width = 500
            engrave_op.add_reference(node, 0)
            group_markers.append_child(node)

            group_node = element_branch.add(type="group", label="Instructions")

            info = (
                "1) Burn this design, so that all shapes are cut out.",
                "2) Push all shapes firmly to the left.",
                "3) The right edge of the last shape will indicate the required kerf-compensation",
            )
            for i in range(3):
                x = x_offset + inner_border
                y = y_offset + inner_border * (1 + (i + 0.75) / 4) + pattern_size
                node = element_branch.add(
                    text=info[i],
                    matrix=Matrix(f"translate({x}, {y})" + f" scale({1.5 * textsize})"),
                    fill=Color("black"),
                    type="elem text",
                )
                text_op.add_reference(node, 0)
                group_node.append_child(node)

            # wd = 2 * inner_border + num_cuts * pattern_width
            # ht = 2 * inner_border + pattern_size
            # shape0 = Rect(x=x_offset, y=y_offset, width=wd, height=ht)
            # elem0 = "elem rect"
            # node = element_branch.add(shape=shape0, type=elem0)
            # node.stroke = engrave_op.color
            # node.stroke_width = 500
            # engrave_op.add_reference(node, 0)

            # Now the cuts
            # First all divider lines
            group_node = element_branch.add(type="group", label="Cut-out")
            for i in range(1, num_cuts - 1):
                shape = Polyline(
                    (
                        x_offset + inner_border + i * pattern_width,
                        y_offset + inner_border,
                    ),
                    (
                        x_offset + inner_border + i * pattern_width,
                        y_offset + inner_border + pattern_size,
                    ),
                )
                node = element_branch.add(
                    shape=shape, type="elem polyline", label=f"Divider #{i}"
                )
                node.stroke = cut_op.color
                node.stroke_width = 500
                cut_op.add_reference(node, 0)
                group_node.append_child(node)

            # The inner box as cut
            wd = (num_cuts - 1) * pattern_width
            ht = pattern_size
            node = element_branch.add(
                x=x_offset + inner_border,
                y=y_offset + inner_border,
                width=wd,
                height=ht,
                stroke=cut_op.color,
                stroke_width=500,
                type="elem rect",
                label="Inner box",
            )
            cut_op.add_reference(node, 0)
            group_node.append_child(node)

            # node = element_branch.add(
            #     text="Burn the displayed pattern on your laser and push the cut out shapes to the left,\n"
            #          "so that there are no more gaps. Look at the value of the scale at the right side\n"
            #          "of your last block and use this as your kerf compensation value.",
            #     matrix=Matrix(
            #         f"translate({xx + 0.5 * pattern_size}, {yy + (1.1 + 0.4) * pattern_size})"
            #         + f" scale({0.5 * textfactor * UNITS_PER_PIXEL})"
            #     ),
            #     anchor="middle",
            #     fill=instruction_op.color,
            #     type="elem text",
            # )
            # text_op.add_reference(node, 0)

        try:
            minv = float(Length(self.text_min.GetValue()))
            maxv = float(Length(self.text_max.GetValue()))
            op_speed = float(self.text_speed.GetValue())
            op_power = float(self.text_power.GetValue())
            gap_size = float(Length(self.text_delta.GetValue()))
            count = self.spin_count.GetValue()
            if count < 2:
                count = 1
                maxv = minv
            pattern_size = float(Length(self.text_dim.GetValue()))
            rectangular = bool(self.radio_pattern.GetSelection() == 0)
            slider = bool(self.radio_pattern.GetSelection() == 2)
        except ValueError:
            return

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
        if slider:
            create_slider()
        else:
            create_operations()

        self.context.signal("rebuild_tree")
        self.context.signal("refresh_scene", "Scene")

    def pane_show(self):
        return


class KerfTool(MWindow):
    """
    KerfTool is the wrapper class to setup the
    required calls to open the KerfPanel window
    """

    def __init__(self, *args, **kwds):
        super().__init__(570, 420, submenu="Laser-Tools", *args, **kwds)
        self.panel_template = KerfPanel(
            self,
            wx.ID_ANY,
            context=self.context,
        )
        self.add_module_delegate(self.panel_template)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_hinges_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Kerf-Test"))
        self.Layout()

    def window_open(self):
        self.panel_template.pane_show()

    def window_close(self):
        pass

    @staticmethod
    def submenu():
        return ("Laser-Tools", "Kerf-Test")
