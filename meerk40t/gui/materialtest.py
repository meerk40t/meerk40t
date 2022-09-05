from copy import copy
from math import tau
import PIL
import wx

from meerk40t.core.node.op_cut import CutOpNode
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.node.op_hatch import HatchOpNode
from meerk40t.core.node.op_image import ImageOpNode
from meerk40t.core.node.op_raster import RasterOpNode
from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.units import UNITS_PER_PIXEL, UNITS_PER_INCH, Angle, Length
from meerk40t.gui.icons import icons8_detective_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import TextCtrl
from meerk40t.svgelements import Color, Matrix, Rect, Circle

_ = wx.GetTranslation


class TemplatePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        opchoices = [_("Cut"), _("Engrave"), _("Raster"), _("Image"), _("Hatch")]
        self.parameters = []
        self.combo_ops = wx.ComboBox(
            self, id=wx.ID_ANY, choices=opchoices, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )

        self.combo_param_1 = wx.ComboBox(
            self, id=wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.combo_param_2 = wx.ComboBox(
            self, id=wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.unit_param_1a = wx.StaticText(self, wx.ID_ANY, "")
        self.unit_param_1b = wx.StaticText(self, wx.ID_ANY, "")
        self.unit_param_2a = wx.StaticText(self, wx.ID_ANY, "")
        self.unit_param_2b = wx.StaticText(self, wx.ID_ANY, "")

        self.button_create = wx.Button(self, wx.ID_ANY, _("Create Pattern"))
        self.spin_count_1 = wx.SpinCtrl(self, wx.ID_ANY, initial=5, min=1, max=25)
        self.spin_count_2 = wx.SpinCtrl(self, wx.ID_ANY, initial=5, min=1, max=25)
        self.text_min_1 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_max_1 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_min_2 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_max_2 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.spin_dim_1 = wx.SpinCtrlDouble(
            self, wx.ID_ANY, min=0.1, max=50.0, initial=10.0
        )
        self.spin_dim_2 = wx.SpinCtrlDouble(
            self, wx.ID_ANY, min=0.1, max=50.0, initial=10.0
        )
        self.spin_delta_1 = wx.SpinCtrlDouble(
            self, wx.ID_ANY, min=0.0, max=50.0, initial=5.0
        )
        self.spin_delta_2 = wx.SpinCtrlDouble(
            self, wx.ID_ANY, min=0.0, max=50.0, initial=5.0
        )

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_param_optype = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Operation to test")), wx.HORIZONTAL
        )
        mylbl = wx.StaticText(self, wx.ID_ANY, _("Operation:"))
        sizer_param_optype.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_param_optype.Add(self.combo_ops, 0, wx.EXPAND, 0)
        sizer_param_xy = wx.BoxSizer(wx.HORIZONTAL)
        sizer_param_x = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("First parameter (X-Axis)")), wx.VERTICAL
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
        hline_dim_1.Add(self.spin_dim_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        mylbl = wx.StaticText(self, wx.ID_ANY, "mm, " + _("Delta:"))
        hline_dim_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_dim_1.Add(self.spin_delta_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        mylbl = wx.StaticText(self, wx.ID_ANY, "mm")
        hline_dim_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_param_x.Add(hline_param_1, 0, wx.EXPAND, 1)
        sizer_param_x.Add(hline_count_1, 0, wx.EXPAND, 1)
        sizer_param_x.Add(hline_min_1, 0, wx.EXPAND, 1)
        sizer_param_x.Add(hline_max_1, 0, wx.EXPAND, 1)
        sizer_param_x.Add(hline_dim_1, 0, wx.EXPAND, 1)

        sizer_param_y = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Second parameter (Y-Axis)")), wx.VERTICAL
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
        hline_dim_2.Add(self.spin_dim_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        mylbl = wx.StaticText(self, wx.ID_ANY, "mm, " + _("Delta:"))
        hline_dim_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_dim_2.Add(self.spin_delta_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        mylbl = wx.StaticText(self, wx.ID_ANY, "mm")
        hline_dim_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_param_y.Add(hline_param_2, 0, wx.EXPAND, 1)
        sizer_param_y.Add(hline_count_2, 0, wx.EXPAND, 1)
        sizer_param_y.Add(hline_min_2, 0, wx.EXPAND, 1)
        sizer_param_y.Add(hline_max_2, 0, wx.EXPAND, 1)
        sizer_param_y.Add(hline_dim_2, 0, wx.EXPAND, 1)

        sizer_param_xy.Add(sizer_param_x, 1, wx.EXPAND, 0)
        sizer_param_xy.Add(sizer_param_y, 1, wx.EXPAND, 0)

        sizer_main.Add(sizer_param_optype, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_param_xy, 0, wx.EXPAND, 0)
        sizer_main.Add(self.button_create, 0, wx.EXPAND, 0)

        self.button_create.Bind(wx.EVT_BUTTON, self.on_button_create_pattern)
        self.combo_ops.Bind(wx.EVT_COMBOBOX, self.set_param_according_to_op)
        self.text_min_1.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_max_1.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_min_2.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_max_2.Bind(wx.EVT_TEXT, self.validate_input)
        self.combo_param_1.Bind(wx.EVT_COMBOBOX, self.on_combo_1)
        self.combo_param_2.Bind(wx.EVT_COMBOBOX, self.on_combo_2)

        self.SetSizer(sizer_main)
        self.Layout()
        self.setup_settings()
        self.combo_ops.SetSelection(0)
        self.restore_settings()
        self.set_param_according_to_op(None)

    def set_param_according_to_op(self, event):
        opidx = self.combo_ops.GetSelection()
        # (internal_attribute, secondary_attribute, Label, unit, keep_unit, needs_to_be_positive)
        self.parameters = [
            ("speed", None, _("Speed"), "mm/s", False, True),
            ("ppi", None, _("Power"), "ppi", False, True),
        ]

        if opidx == 0:
            # Cut
            # (internal_attribute, secondary_attribute, Label, unit, keep_unit, needs_to_be_positive)
            self.parameters = [
                ("speed", None, _("Speed"), "mm/s", False, True),
                ("ppi", None, _("Power"), "ppi", False, True),
            ]
        elif opidx == 1:
            # Engrave
            self.parameters = [
                ("speed", None, _("Speed"), "mm/s", False, True),
                ("ppi", None, _("Power"), "ppi", False, True),
            ]
        elif opidx == 2:
            # Raster
            self.parameters = [
                ("speed", None, _("Speed"), "mm/s", False, True),
                ("ppi", None, _("Power"), "ppi", False, True),
                ("dpi", None, _("DPI"), "dpi", False, True),
                ("overscan", None, _("Overscan"), "mm", False, True),
            ]
        elif opidx == 3:
            # Image
            self.parameters = [
                ("speed", None, _("Speed"), "mm/s", False, True),
                ("ppi", None, _("Power"), "ppi", False, True),
                ("dpi", None, _("DPI"), "dpi", False, True),
                ("overscan", None, _("Overscan"), "mm", False, True),
            ]
        elif opidx == 4:
            # Hatch
            self.parameters = [
                ("speed", None, _("Speed"), "mm/s", False, True),
                ("ppi", None, _("Power"), "ppi", False, True),
                ("hatch_distance", None, _("Hatch Distance"), "mm", False, True),
                ("hatch_angle", None, _("Hatch Angle"), "deg", False, True),
            ]

        if "balor" in self.context.device._path:
            allow_balor = True
        else:
            allow_balor = False
        if allow_balor:
            balor_choices = [
                ("frequency", None, _("Frequency"), "kHz", False, True),
                ("rapid_speed", "rapid_enabled", _("Rapid Speed"), "mm/s", False, True),
                ("pulse_width", "pulse_width _enabled", _("Pulse Width"), "µs", False, True),
                ("delay_laser_on", "timing_enabled", _("Laser On Delay"), "µs", False, False),
                ("delay_laser_off", "timing_enabled",  _("Laser Off Delay"), "µs", False, False),
                ("delay_polygon", "timing_enabled", _("Polygon Delay"), "ns", False, False),
                ("wobble_radius", "wobble_enabled", _("Wobble Radius"), "mm", True, True),
                ("wobble_interval", "wobble_enabled", _("Wobble Interval"), "mm", True, True),
                ("wobble_speed", "wobble_enabled", _("Wobble Speed Multiplier"), "x", False, True),
            ]
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
        idx = self.combo_param_1.GetSelection()
        # 0 = internal_attribute, 1 = secondary_attribute,
        # 2 = Label, 3 = unit,
        # 4 = keep_unit, 5 = needs_to_be_positive)
        if idx >= 0 and idx < len(self.parameters):
            s_unit = self.parameters[idx][3]
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
        active = True
        self.button_create.Enable(active)

    def on_button_create_pattern(self, event):
        def make_color(idx1, max1, idx2, max2):
            r = 255 - int(idx1 / max1 * 255.0)
            g = 0
            b = 255 - int(idx2 / max2 * 255.0)
            mycolor = Color(r, g, b)
            return mycolor

        def clear_all():
            self.context("operation* delete\n")
            self.context("element* delete\n")

        def create_operations():
            # opchoices = [_("Cut"), _("Engrave"), _("Raster"), _("Image"), _("Hatch")]

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
            # Make one op for text
            text_op = RasterOpNode()
            text_op.color = Color("black")
            text_op.label = "Descriptions"
            operation_branch.add_node(text_op)
            text_x = start_x + expected_width / 2
            text_y = start_y - float(Length("3cm"))
            node = self.context.elements.elem_branch.add(
                text=f"{param_name_1}",
                matrix=Matrix(
                    f"translate({text_x}, {text_y}) scale({UNITS_PER_PIXEL})"
                ),
                anchor="middle",
                fill=Color("black"),
                type="elem text",
            )
            text_op.add_reference(node, 0)
            text_x = start_x - float(Length("3cm"))
            text_y = start_y + expected_height / 2
            node = self.context.elements.elem_branch.add(
                text=f"{param_name_2}",
                matrix=Matrix(
                    f"translate({text_x}, {text_y}) scale({UNITS_PER_PIXEL})"
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
            text_scale_x = min(1.0, size_y / float(Length("10mm")))
            text_scale_y = min(1.0, size_x / float(Length("10mm")))
            for idx1 in range(count_1):
                p_value_2 = min_value_2
                yy = start_y

                # Add a text above for each column
                text_x = xx + 0.5 * size_x
                text_y = yy - float(Length("5mm"))
                node = self.context.elements.elem_branch.add(
                    text=f"{p_value_1:.3f}",
                    matrix=Matrix(
                        f"translate({text_x}, {text_y}) scale({text_scale_x * UNITS_PER_PIXEL})"
                    ),
                    anchor="end",
                    fill=Color("black"),
                    type="elem text",
                )
                node.matrix.post_rotate(tau / 4, text_x, text_y)
                node.modified()
                text_op.add_reference(node, 0)

                for idx2 in range(count_2):
                    s_lbl = f"{param_type_1}={p_value_1:.3f}{param_unit_1}"
                    s_lbl += f"- {param_type_2}={p_value_2:.3f}{param_unit_2}"
                    if idx1 == 0:  # first row, so add a text above
                        text_x = xx - float(Length("5mm"))
                        text_y = yy + 0.5 * size_y
                        node = self.context.elements.elem_branch.add(
                            text=f"{p_value_2:.3f}",
                            matrix=Matrix(
                                f"translate({text_x}, {text_y}) scale({text_scale_y * UNITS_PER_PIXEL})"
                            ),
                            anchor="end",
                            fill=Color("black"),
                            type="elem text",
                        )
                        text_op.add_reference(node, 0)
                    if optype == 0:  # Cut
                        this_op = CutOpNode()
                        usefill = False
                    elif optype == 1:  # Engrave
                        this_op = EngraveOpNode()
                        usefill = False
                    elif optype == 2:  # Raster
                        this_op = RasterOpNode()
                        usefill = True
                    elif optype == 3:  # Image
                        this_op = ImageOpNode()
                        usefill = False
                    elif optype == 4:  # Hatch
                        this_op = HatchOpNode()
                        usefill = True
                    else:
                        return
                    this_op.label = s_lbl
                    if param_keep_unit_1:
                        value = str(p_value_1) + param_unit_1
                    else:
                        value = p_value_1
                    if hasattr(this_op, param_type_1):
                        setattr(this_op, param_type_1, value)
                    else: # Try setting
                        this_op.settings[param_type_1] = value
                    # Is there a corresponding xxx_enabled property available?
                    if param_override_1 is not None:
                        if hasattr(this_op, param_override_1):
                            setattr(this_op, param_override_1, True)
                        else: # Try setting
                            this_op.settings[param_override_1] = True

                    if param_keep_unit_2:
                        value = str(p_value_2) + param_unit_2
                    else:
                        value = p_value_2
                    if hasattr(this_op, param_type_2):
                        setattr(this_op, param_type_2, value)
                    else: # Try setting
                        this_op.settings[param_type_2] = value
                    # Is there a corresponding xxx_enabled property available?
                    if param_override_2 is not None:
                        if hasattr(this_op, param_override_2):
                            setattr(this_op, param_override_2, True)
                        else: # Try setting
                            this_op.settings[param_override_2] = True

                    set_color = make_color(idx1, count_1, idx2, count_2)
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
                        elem_type = "elem rect"
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
        param_override_1 = self.parameters[idx][1]
        if param_override_1 == "":
            param_override_1 = None
        param_unit_1 = self.parameters[idx][3]
        param_keep_unit_1 = self.parameters[idx][4]
        param_positive_1 = self.parameters[idx][5]

        idx = self.combo_param_2.GetSelection()
        if idx < 0:
            return
        param_name_2 = self.parameters[idx][2]
        param_type_2 = self.parameters[idx][0]
        param_override_2 = self.parameters[idx][1]
        if param_override_2 == "":
            param_override_2 = None
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
            min_value_1 = f"{Angle.parse(self.text_min_1.GetValue()).as_degrees}deg"
            max_value_1 = f"{Angle.parse(self.text_max_1.GetValue()).as_degrees}deg"
        elif param_unit_1 == "ppi":
            min_value_1 = max(min_value_1, 0)
            max_value_1 = min(max_value_1, 1000)
        else:
            # > 0
            if param_positive_1:
                min_value_1 = max(min_value_1, 0)
                max_value_1 = max(max_value_1, 0)

        if param_unit_2 == "deg":
            min_value_2 = f"{Angle.parse(self.text_min_2.GetValue()).as_degrees}deg"
            max_value_2 = f"{Angle.parse(self.text_max_2.GetValue()).as_degrees}deg"
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
        dimension_1 = self.spin_dim_1.GetValue()
        if dimension_1 <= 0:
            dimension_1 = 5
        dimension_2 = self.spin_dim_2.GetValue()
        if dimension_2 <= 0:
            dimension_2 = 5
        gap_1 = self.spin_delta_1.GetValue()
        if gap_1 < 0:
            gap_1 = 0
        gap_2 = self.spin_delta_2.GetValue()
        if gap_2 < 0:
            gap_2 = 5
        message = _("This will delete all existing operations and elements") + "\n"
        message += _("and replace them by the test-pattern! Are you really sure?")
        caption = _("Create Test-Pattern")
        dlg = wx.MessageDialog(
            self,
            message,
            caption,
            wx.YES_NO | wx.ICON_WARNING,
        )
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_NO:
            return

        clear_all()
        create_operations()

        self.context.signal("rebuild_tree")
        self.context.signal("refresh_scene")
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
        self.context.setting(float, "template_dim1", 10)
        self.context.setting(float, "template_dim2", 10)
        self.context.setting(float, "template_gap1", 5)
        self.context.setting(float, "template_gap2", 5)

    def save_settings(self):
        self.context.template_optype = self.combo_ops.GetSelection()
        self.context.template_param1 = self.combo_param_1.GetSelection()
        self.context.template_param2 = self.combo_param_2.GetSelection()
        self.context.template_min1 = self.text_min_1.GetValue()
        self.context.template_max1 = self.text_max_1.GetValue()
        self.context.template_min2 = self.text_min_2.GetValue()
        self.context.template_max2 = self.text_max_2.GetValue()
        self.context.template_count1 = self.spin_count_1.GetValue()
        self.context.template_count2 = self.spin_count_2.GetValue()
        self.context.template_dim1 = self.spin_dim_1.GetValue()
        self.context.template_dim2 = self.spin_dim_2.GetValue()
        self.context.template_gap1 = self.spin_delta_1.GetValue()
        self.context.template_gap2 = self.spin_delta_2.GetValue()

    def restore_settings(self):
        try:
            self.combo_ops.SetSelection(min(self.context.template_optype, self.combo_ops.GetCount() -1))
            self.combo_param_1.SetSelection(min(self.context.template_param1, self.combo_param_1.GetCount() -1))
            self.combo_param_2.SetSelection(min(self.context.template_param2, self.combo_param_2.GetCount() -1))
            self.text_min_1.SetValue(self.context.template_min1)
            self.text_max_1.SetValue(self.context.template_max1)
            self.text_min_2.SetValue(self.context.template_min2)
            self.text_max_2.SetValue(self.context.template_max1)
            self.spin_count_1.SetValue(self.context.template_count1)
            self.spin_count_2.SetValue(self.context.template_count2)
            self.spin_dim_1.SetValue(self.context.template_dim1)
            self.spin_dim_2.SetValue(self.context.template_dim2)
            self.spin_delta_1.SetValue(self.context.template_gap1)
            self.spin_delta_2.SetValue(self.context.template_gap2)
        except (AttributeError, ValueError):
            return


class TemplateTool(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(490, 280, submenu="Laser-Tools", *args, **kwds)
        self.panel = TemplatePanel(self, wx.ID_ANY, context=self.context)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_detective_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Parameter-Test"))

    def window_open(self):
        pass

    def window_close(self):
        pass

    def delegates(self):
        yield self.panel

    @staticmethod
    def submenu():
        return ("Laser-Tools", "Parameter-Test")
