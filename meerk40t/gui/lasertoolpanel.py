from math import atan, sqrt, tau

import wx

from meerk40t.core.units import Length
from meerk40t.gui.icons import (
    instruction_circle,
    instruction_frame,
    instruction_rectangle,
)
from meerk40t.gui.mwindow import MWindow
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


DEFAULT_LEN = "5cm"


class LaserToolPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.coord_a = None
        self.coord_b = None
        self.coord_c = None
        self.laserposition = None

        sizer_main = wx.BoxSizer(wx.VERTICAL)

        self.nbook_lasertools = wx.Notebook(self, wx.ID_ANY)
        sizer_main.Add(self.nbook_lasertools, 1, wx.EXPAND, 0)

        # ------------------------ Circle with 3 points

        self.nb_circle = wx.Panel(self.nbook_lasertools, wx.ID_ANY)
        self.nbook_lasertools.AddPage(self.nb_circle, _("Find center"))

        self.sizer_circle = wx.BoxSizer(wx.VERTICAL)

        sizer_9 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_circle.Add(sizer_9, 0, wx.EXPAND, 0)

        sizer_10 = wx.BoxSizer(wx.VERTICAL)
        sizer_9.Add(sizer_10, 0, wx.EXPAND, 0)

        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10.Add(sizer_1, 1, wx.EXPAND, 0)

        label_1 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("A"))
        sizer_1.Add(label_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_set_circle_1 = wx.Button(self.nb_circle, wx.ID_ANY, _("Use position"))
        self.btn_set_circle_1.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_1.Add(self.btn_set_circle_1, 0, wx.EXPAND, 0)

        self.lbl_pos_1 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("<empty>"))
        sizer_1.Add(self.lbl_pos_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10.Add(sizer_2, 1, wx.EXPAND, 0)

        label_2 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("B"))
        sizer_2.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_set_circle_2 = wx.Button(self.nb_circle, wx.ID_ANY, _("Use position"))
        self.btn_set_circle_2.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_2.Add(self.btn_set_circle_2, 0, wx.EXPAND, 0)

        self.lbl_pos_2 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("<empty>"))
        sizer_2.Add(self.lbl_pos_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10.Add(sizer_3, 1, wx.EXPAND, 0)

        label_3 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("C"))
        sizer_3.Add(label_3, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_set_circle_3 = wx.Button(self.nb_circle, wx.ID_ANY, _("Use position"))
        self.btn_set_circle_3.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_3.Add(self.btn_set_circle_3, 0, wx.EXPAND, 0)

        self.lbl_pos_3 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("<empty>"))
        sizer_3.Add(self.lbl_pos_3, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        img_instruction_1 = wx.StaticBitmap(
            self.nb_circle, wx.ID_ANY, instruction_circle.GetBitmap()
        )
        instructions = _(
            "Instruction: place the laser on three points on the circumference of the circle on the bed and confirm the position by clicking on the buttons below.\nMK will find the center for you and place the laser above it or will recreate the circle for further processing."
        )
        img_instruction_1.SetToolTip(instructions)
        sizer_9.Add(img_instruction_1, 1, 0, 0)

        sizer_chk = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_circle.Add(sizer_chk, 0, wx.EXPAND, 0)
        self.check_ref_circle = wx.CheckBox(
            self.nb_circle, wx.ID_ANY, _("Make reference")
        )
        sizer_chk.Add(self.check_ref_circle, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.check_circle = wx.CheckBox(self.nb_circle, wx.ID_ANY, _("Mark Center"))
        sizer_chk.Add(self.check_circle, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_circle.Add(sizer_4, 0, wx.EXPAND, 0)

        self.btn_move_to_center = wx.Button(
            self.nb_circle, wx.ID_ANY, _("Move to center")
        )
        sizer_4.Add(self.btn_move_to_center, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_create_circle = wx.Button(
            self.nb_circle, wx.ID_ANY, _("Create circle")
        )
        sizer_4.Add(self.btn_create_circle, 0, wx.EXPAND, 0)

        # ------------------------ Rectangle with 2 points

        self.nb_rectangle = wx.Panel(self.nbook_lasertools, wx.ID_ANY)
        self.nbook_lasertools.AddPage(self.nb_rectangle, _("Place frame"))

        self.sizer_rectangle = wx.BoxSizer(wx.VERTICAL)

        sizer_rect_hor = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_rectangle.Add(sizer_rect_hor, 0, wx.EXPAND, 0)

        sizer_rect_vert = wx.BoxSizer(wx.VERTICAL)
        sizer_rect_hor.Add(sizer_rect_vert, 0, wx.EXPAND, 0)

        sizer_5a = wx.BoxSizer(wx.HORIZONTAL)
        sizer_rect_vert.Add(sizer_5a, 1, wx.EXPAND, 0)

        label_corner_1 = wx.StaticText(self.nb_rectangle, wx.ID_ANY, _("Corner 1"))
        sizer_5a.Add(label_corner_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_set_rect_1 = wx.Button(self.nb_rectangle, wx.ID_ANY, _("Use position"))
        self.btn_set_rect_1.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_5a.Add(self.btn_set_rect_1, 0, wx.EXPAND, 0)

        self.lbl_pos_7 = wx.StaticText(self.nb_rectangle, wx.ID_ANY, _("<empty>"))
        sizer_5a.Add(self.lbl_pos_7, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_6a = wx.BoxSizer(wx.HORIZONTAL)
        sizer_rect_vert.Add(sizer_6a, 1, wx.EXPAND, 0)

        label_corner_2 = wx.StaticText(self.nb_rectangle, wx.ID_ANY, _("Corner 2"))
        sizer_6a.Add(label_corner_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_set_rect_2 = wx.Button(self.nb_rectangle, wx.ID_ANY, _("Use position"))
        self.btn_set_rect_2.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_6a.Add(self.btn_set_rect_2, 0, wx.EXPAND, 0)

        self.lbl_pos_8 = wx.StaticText(self.nb_rectangle, wx.ID_ANY, _("<empty>"))
        sizer_6a.Add(self.lbl_pos_8, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.img_instruction_2 = wx.StaticBitmap(
            self.nb_rectangle, wx.ID_ANY, instruction_frame.GetBitmap()
        )
        instructions = _(
            "Instruction: place the laser on one corner of the encompassing rectangle and confirm the position by clicking on the buttons below. Then choose the opposing corner.\nMK will create a rectangle for you for further processing."
        )
        self.img_instruction_2.SetToolTip(instructions)
        sizer_rect_hor.Add(self.img_instruction_2, 1, 0, 0)

        sizer_chk_rect = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_rectangle.Add(sizer_chk_rect, 0, wx.EXPAND, 0)
        self.check_ref_frame = wx.CheckBox(
            self.nb_rectangle, wx.ID_ANY, _("Make reference")
        )
        sizer_chk_rect.Add(self.check_ref_frame, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_8a = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_rectangle.Add(sizer_8a, 0, wx.EXPAND, 0)

        self.btn_create_frame = wx.Button(
            self.nb_rectangle, wx.ID_ANY, _("Create frame")
        )
        sizer_8a.Add(self.btn_create_frame, 0, wx.EXPAND, 0)

        # ------------------------ Square with 3 points

        self.nb_square = wx.Panel(self.nbook_lasertools, wx.ID_ANY)
        self.nbook_lasertools.AddPage(self.nb_square, _("Place square"))

        self.sizer_square = wx.BoxSizer(wx.VERTICAL)

        sizer_sqare_hor = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_square.Add(sizer_sqare_hor, 0, wx.EXPAND, 0)

        sizer_sqare_vert = wx.BoxSizer(wx.VERTICAL)
        sizer_sqare_hor.Add(sizer_sqare_vert, 0, wx.EXPAND, 0)

        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sqare_vert.Add(sizer_5, 1, wx.EXPAND, 0)

        label_4 = wx.StaticText(self.nb_square, wx.ID_ANY, _("Side A 1"))
        label_4.SetMinSize((45, -1))
        sizer_5.Add(label_4, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_set_square_1 = wx.Button(self.nb_square, wx.ID_ANY, _("Use position"))
        self.btn_set_square_1.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_5.Add(self.btn_set_square_1, 0, wx.EXPAND, 0)

        self.lbl_pos_4 = wx.StaticText(self.nb_square, wx.ID_ANY, _("<empty>"))
        sizer_5.Add(self.lbl_pos_4, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_6 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sqare_vert.Add(sizer_6, 1, wx.EXPAND, 0)

        label_5 = wx.StaticText(self.nb_square, wx.ID_ANY, _("Side A 2"))
        label_5.SetMinSize((45, -1))
        sizer_6.Add(label_5, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_set_square_2 = wx.Button(self.nb_square, wx.ID_ANY, _("Use position"))
        self.btn_set_square_2.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_6.Add(self.btn_set_square_2, 0, wx.EXPAND, 0)

        self.lbl_pos_5 = wx.StaticText(self.nb_square, wx.ID_ANY, _("<empty>"))
        sizer_6.Add(self.lbl_pos_5, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_7 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sqare_vert.Add(sizer_7, 1, wx.EXPAND, 0)

        label_6 = wx.StaticText(self.nb_square, wx.ID_ANY, _("Side B"))
        label_6.SetMinSize((45, -1))
        sizer_7.Add(label_6, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_set_square_3 = wx.Button(self.nb_square, wx.ID_ANY, _("Use position"))
        self.btn_set_square_3.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_7.Add(self.btn_set_square_3, 0, wx.EXPAND, 0)

        self.lbl_pos_6 = wx.StaticText(self.nb_square, wx.ID_ANY, _("<empty>"))
        sizer_7.Add(self.lbl_pos_6, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        size_width = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sqare_vert.Add(size_width, 1, wx.EXPAND, 0)

        label_wd = wx.StaticText(self.nb_square, wx.ID_ANY, _("Dimension"))
        size_width.Add(label_wd, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.txt_width = wx.TextCtrl(self.nb_square, wx.ID_ANY, DEFAULT_LEN)
        self.txt_width.SetToolTip(_("Extension of the square to create"))
        self.txt_width.SetMinSize((60, -1))
        size_width.Add(self.txt_width, 0, wx.EXPAND, 0)

        self.img_instruction_3 = wx.StaticBitmap(
            self.nb_square, wx.ID_ANY, instruction_rectangle.GetBitmap()
        )
        instructions = _(
            "Instruction: place the laser on two points of one side of a square on the bed and confirm the position by clicking on the buttons below. Then choose one point on the other side of the corner.\nMK will create a square for you for further processing."
        )
        self.img_instruction_3.SetToolTip(instructions)
        sizer_sqare_hor.Add(self.img_instruction_3, 1, 0, 0)

        sizer_chk_square = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_square.Add(sizer_chk_square, 0, wx.EXPAND, 0)
        self.check_ref_square = wx.CheckBox(
            self.nb_square, wx.ID_ANY, _("Make reference")
        )
        sizer_chk_square.Add(self.check_ref_square, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.check_square = wx.CheckBox(self.nb_square, wx.ID_ANY, _("Mark Corner"))
        sizer_chk_square.Add(self.check_square, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_8 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_square.Add(sizer_8, 0, wx.EXPAND, 0)

        self.btn_create_square = wx.Button(
            self.nb_square, wx.ID_ANY, _("Create square")
        )
        sizer_8.Add(self.btn_create_square, 0, wx.EXPAND, 0)

        self.nb_square.SetSizer(self.sizer_square)

        self.nb_circle.SetSizer(self.sizer_circle)

        self.nb_rectangle.SetSizer(self.sizer_rectangle)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        self.Layout()
        self.check_input()
        self.btn_set_circle_1.Bind(wx.EVT_BUTTON, self.on_click_get1)
        self.btn_set_circle_2.Bind(wx.EVT_BUTTON, self.on_click_get2)
        self.btn_set_circle_3.Bind(wx.EVT_BUTTON, self.on_click_get3)
        self.btn_move_to_center.Bind(wx.EVT_BUTTON, self.on_btn_move_center)
        self.btn_create_circle.Bind(wx.EVT_BUTTON, self.on_btn_create_circle)
        self.btn_set_rect_1.Bind(wx.EVT_BUTTON, self.on_click_get1)
        self.btn_set_rect_2.Bind(wx.EVT_BUTTON, self.on_click_get2)
        self.btn_create_frame.Bind(wx.EVT_BUTTON, self.on_btn_create_frame)

        self.btn_set_square_1.Bind(wx.EVT_BUTTON, self.on_click_get1)
        self.btn_set_square_2.Bind(wx.EVT_BUTTON, self.on_click_get2)
        self.btn_set_square_3.Bind(wx.EVT_BUTTON, self.on_click_get3)
        self.txt_width.Bind(wx.EVT_KILL_FOCUS, self.on_text_change)
        self.btn_create_square.Bind(wx.EVT_BUTTON, self.on_btn_create_square)
        # self.img_instruction_3.Bind(wx.EVT_LEFT_DCLICK, self.create_scenario)
        # end wxGlade

    # scenario = 8
    #
    # def create_scenario(self, event):
    #    event.Skip()
    #    self.scenario += 1
    #    l1 ="10cm"
    #    self.txt_width.SetValue(l1)
    #    if self.scenario in (1, 2, 3, 4):
    #        c1 = (20 * UNITS_PER_MM, 20 * UNITS_PER_MM)
    #        c2 = (50 * UNITS_PER_MM, 20 * UNITS_PER_MM)
    #    else:
    #        c1 = (20 * UNITS_PER_MM, 20 * UNITS_PER_MM)
    #        c2 = (20 * UNITS_PER_MM, 50 * UNITS_PER_MM)
    #    if self.scenario in (1, 5):
    #        c3 = (10 * UNITS_PER_MM, 70 * UNITS_PER_MM)
    #    elif self.scenario in (2, 6):
    #        c3 = (10 * UNITS_PER_MM, 0 * UNITS_PER_MM)
    #    elif self.scenario in (3, 7):
    #        c3 = (70 * UNITS_PER_MM, 70 * UNITS_PER_MM)
    #    elif self.scenario in (4, 8):
    #        c3 = (70 * UNITS_PER_MM, 0 * UNITS_PER_MM)

    #    if self.scenario == 9:
    #        c1 = (20 * UNITS_PER_MM, 20 * UNITS_PER_MM)
    #        c2 = (30 * UNITS_PER_MM, 50 * UNITS_PER_MM)
    #        c3 = (70 * UNITS_PER_MM, 10 * UNITS_PER_MM)
    #    self.set_coord(idx=0, position=c1)
    #    self.set_coord(idx=1, position=c2)
    #    self.set_coord(idx=2, position=c3)
    #    if self.scenario>=9:
    #        self.scenario = 0

    def set_coord(self, idx=0, position=None):
        if position is None:
            label_string = _("<empty>")
        else:
            p = self.context
            units = p.units_name
            label_string = (
                f"({str(Length(amount=position[0], digits=1, preferred_units=units))}, "
                f"{str(Length(amount=position[1], digits=1, preferred_units=units))})"
            )
        if idx == 0:
            self.lbl_pos_1.Label = label_string
            self.lbl_pos_4.Label = label_string
            self.lbl_pos_7.Label = label_string
            self.coord_a = position
            self.check_input()
        elif idx == 1:
            self.lbl_pos_2.Label = label_string
            self.lbl_pos_5.Label = label_string
            self.lbl_pos_8.Label = label_string
            self.coord_b = position
            self.check_input()
        elif idx == 2:
            self.lbl_pos_3.Label = label_string
            self.lbl_pos_6.Label = label_string
            self.coord_c = position
            self.check_input()
        self.sizer_circle.Layout()
        self.sizer_square.Layout()
        self.sizer_rectangle.Layout()

    def check_input(self):
        if self.coord_a is None or self.coord_b is None or self.coord_c is None:
            value = False
        else:
            value = True
        self.btn_create_circle.Enable(value)
        self.btn_move_to_center.Enable(value)
        self.btn_create_square.Enable(value)
        if self.coord_a is None or self.coord_b is None:
            value = False
        else:
            value = True
        self.btn_create_frame.Enable(value)

    def on_click_get1(self, event):
        # Current Laserposition
        self.set_coord(idx=0, position=self.laserposition)

    def on_click_get2(self, event):
        # Current Laserposition
        self.set_coord(idx=1, position=self.laserposition)
        event.Skip()

    def on_click_get3(self, event):
        # Current Laserposition
        self.set_coord(idx=2, position=self.laserposition)
        event.Skip()

    def on_text_change(self, event):
        event.Skip()
        try:
            l = Length(self.txt_width.GetValue())
        except (ValueError, AttributeError):
            self.txt_width.SetValue(DEFAULT_LEN)

    def calculate_center(self):
        """
        Let's recall how the equation of a circle looks like in general form:
        x^2+y^2+2ax+2by+c=0

        Since all three points should belong to one circle, we can write a system of equations.

        x_1^2+y_1^2+2ax_1+2by_1+c=0\\x_2^2+y_2^2+2ax_2+2by_2+c=0\\x_3^2+y_3^2+2ax_3+2by_3+c=0

        The values (x_1, y_1), (x_2, y_2) and (x_3, y_3) are known. Let's rearrange with respect to unknowns a, b and c.

        2x_1a+2y_1b+c + x_1^2+y_1^2+=0\\2x_2a+2y_2b+c+x_2^2+y_2^2=0\\2x_3a+2y_3b+c+x_3^2+y_3^2=0
        """
        result = True
        center = None
        radius = None
        x12 = self.coord_a[0] - self.coord_b[0]
        x13 = self.coord_a[0] - self.coord_c[0]

        y12 = self.coord_a[1] - self.coord_b[1]
        y13 = self.coord_a[1] - self.coord_c[1]

        y31 = self.coord_c[1] - self.coord_a[1]
        y21 = self.coord_b[1] - self.coord_a[1]

        x31 = self.coord_c[0] - self.coord_a[0]
        x21 = self.coord_b[0] - self.coord_a[0]

        # coord_a[0]^2 - coord_c[0]^2
        sx13 = pow(self.coord_a[0], 2) - pow(self.coord_c[0], 2)

        # self.coord_a[1]^2 - self.coord_c[1]^2
        sy13 = pow(self.coord_a[1], 2) - pow(self.coord_c[1], 2)

        sx21 = pow(self.coord_b[0], 2) - pow(self.coord_a[0], 2)
        sy21 = pow(self.coord_b[1], 2) - pow(self.coord_a[1], 2)
        try:
            f = (sx13 * x12 + sy13 * x12 + sx21 * x13 + sy21 * x13) // (
                2 * (y31 * x12 - y21 * x13)
            )

            g = (sx13 * y12 + sy13 * y12 + sx21 * y13 + sy21 * y13) // (
                2 * (x31 * y12 - x21 * y13)
            )
        except (ZeroDivisionError, ArithmeticError):
            return False, None, None

        c = (
            -pow(self.coord_a[0], 2)
            - pow(self.coord_a[1], 2)
            - 2 * g * self.coord_a[0]
            - 2 * f * self.coord_a[1]
        )

        # eqn of circle be x^2 + y^2 + 2*g*x + 2*f*y + c = 0
        # where centre is (h = -g, k = -f) and
        # radius r as r^2 = h^2 + k^2 - c
        h = -g
        k = -f
        sqr_of_r = h * h + k * k - c

        # r is the radius
        if sqr_of_r < 0:
            result = False
        else:
            r = round(sqrt(sqr_of_r), 5)

        # print("Centre = (", h, ", ", k, ")")
        # print("Radius = ", r)
        center = (h, k)
        radius = r
        return result, center, radius

    def calculate_square(self):
        result = True
        center = None
        angle = 0
        signx = 1
        signy = 1
        # equation for the first line through (x1, y1)-(x2, y2)
        # y = a1 * x + b1
        dx1 = self.coord_a[0] - self.coord_b[0]
        dy1 = self.coord_a[1] - self.coord_b[1]
        if dx1 == 0 and dy1 == 0:
            result = False
        if self.coord_a == self.coord_b:
            result = False
        if self.coord_a == self.coord_c:
            result = False
        if self.coord_b == self.coord_c:
            result = False

        if dx1 == 0:
            a1 = float("inf")
            b1 = 0
        else:
            a1 = dy1 / dx1
            b1 = self.coord_a[1] - self.coord_a[0] * a1

        if dx1 == 0:
            center = (self.coord_a[0], self.coord_c[1])
        elif dy1 == 0:
            center = (self.coord_c[0], self.coord_a[1])
        else:
            # regular line
            # line 1
            # y = a1 * x + b1
            # orthogonal line
            a2 = -1 / a1
            b2 = self.coord_c[1] - self.coord_c[0] * a2

            x0 = (b2 - b1) / (a1 - a2)
            y0 = a1 * x0 + b1
            center = (x0, y0)
            dx1 = 0
            dy1 = 0
            angle = atan(a1)

        mid_a_x = (self.coord_a[0] + self.coord_b[0]) / 2
        mid_a_y = (self.coord_a[1] + self.coord_b[1]) / 2
        if abs(dx1) < abs(dy1):  # A is a 'vertical' line
            if mid_a_y < center[1]:
                if self.coord_c[0] >= center[0]:
                    segment = 4
                else:
                    segment = 3
            else:
                if self.coord_c[0] >= center[0]:
                    segment = 1
                else:
                    segment = 2
        else:  # Horizontal line
            if mid_a_x < center[0]:
                if self.coord_c[1] >= center[1]:
                    segment = 2
                else:
                    segment = 3
            else:
                if self.coord_c[1] >= center[1]:
                    segment = 1
                else:
                    segment = 4
        if segment == 1:
            signx = +1
            signy = +1
        elif segment == 2:
            signx = -1
            signy = +1
        elif segment == 3:
            signx = -1
            signy = -1
        elif segment == 4:
            signx = +1
            signy = -1

        # print (center, angle / tau * 360)
        return result, center, angle, signx, signy

    def calculate_frame(self):
        result = False
        left_top = (0, 0)
        width = 0
        height = 0
        if self.coord_a is not None and self.coord_b is not None:
            x0 = self.coord_a[0]
            x1 = self.coord_b[0]
            y0 = self.coord_a[1]
            y1 = self.coord_b[1]
            width = abs(x0 - x1)
            height = abs(y0 - y1)
            xx = min(x0, x1)
            yy = min(y0, y1)
            if width != 0 and height != 0:
                left_top = (xx, yy)
                result = True
        return result, left_top, width, height

    def on_btn_move_center(self, event):  # wxGlade: clsLasertools.<event_handler>
        result, center, radius = self.calculate_center()
        if result:
            p = self.context
            units = p.units_name
            cx = float(Length(amount=center[0], digits=5, preferred_units=units))
            cy = float(Length(amount=center[1], digits=5, preferred_units=units))
            if self.context.elements.classify_new:
                option = " classify"
                postsignal = "tree_changed"
            else:
                option = ""
                postsignal = ""
            if self.check_circle.GetValue():
                self.context(
                    f"circle "
                    f"{str(Length(amount=center[0], digits=5, preferred_units=units))} "
                    f"{str(Length(amount=center[1], digits=5, preferred_units=units))} "
                    f"1mm stroke blue{option}\n"
                )
            if postsignal != "":
                self.context.signal(postsignal)
            if (
                cx < 0
                or cy < 0
                or cx > self.context.device.unit_width
                or cy > self.context.device.unit_height
            ):
                message = (
                    _("The circles center seems to lie outside the bed-dimensions!")
                    + "\n"
                )
                message += (
                    _("If you continue to move to the center, then the laserhead might")
                    + "\n"
                )
                message += _(
                    "slam into the walls and get damaged! Do you really want to proeed?"
                )
                caption = _("Dangerous coordinates")
                dlg = wx.MessageDialog(
                    self,
                    message,
                    caption,
                    wx.YES_NO | wx.ICON_WARNING,
                )
                dlgresult = dlg.ShowModal()
                dlg.Destroy()
                if dlgresult != wx.ID_YES:
                    return
            self.context(
                f"move_absolute "
                f"{str(Length(amount=center[0], digits=5, preferred_units=units))} "
                f"{str(Length(amount=center[1], digits=5, preferred_units=units))}\n"
            )

    def on_btn_create_circle(self, event):  # wxGlade: clsLasertools.<event_handler>
        result, center, radius = self.calculate_center()
        if result:
            p = self.context
            units = p.units_name
            if self.context.elements.classify_new:
                option = " classify"
                postsignal = "tree_changed"
            else:
                option = ""
                postsignal = ""
            if self.check_circle.GetValue():
                self.context(
                    f"circle "
                    f"{str(Length(amount=center[0], digits=5, preferred_units=units))} "
                    f"{str(Length(amount=center[1], digits=5, preferred_units=units))} "
                    f"1mm stroke blue{option}\n"
                )
            self.context(
                f"circle "
                f"{str(Length(amount=center[0], digits=5, preferred_units=units))} "
                f"{str(Length(amount=center[1], digits=5, preferred_units=units))} "
                f"{str(Length(amount=radius, digits=5, preferred_units=units))}{option}\n"
            )
            if self.check_ref_circle.GetValue():
                self.context("reference\n")
            if postsignal != "":
                self.context.signal(postsignal)
        event.Skip()

    def on_btn_create_frame(self, event):  # wxGlade: clsLasertools.<event_handler>
        result, left_top, width, height = self.calculate_frame()

        if result:
            p = self.context
            units = p.units_name
            if self.context.elements.classify_new:
                option = " classify"
                postsignal = "tree_changed"
            else:
                option = ""
                postsignal = ""

            self.context(
                f"rect "
                f"{str(Length(amount=left_top[0], digits=5, preferred_units=units))} "
                f"{str(Length(amount=left_top[1], digits=5, preferred_units=units))} "
                f"{str(Length(amount=width, digits=5, preferred_units=units))} "
                f"{str(Length(amount=height, digits=5, preferred_units=units))}"
                f"{option}\n"
            )
            if self.check_ref_frame.GetValue():
                self.context("reference\n")
            if postsignal != "":
                self.context.signal(postsignal)
        event.Skip()

    def on_btn_create_square(self, event):  # wxGlade: clsLasertools.<event_handler>
        try:
            dim_x = Length(self.txt_width.GetValue())
            dim_y = Length(self.txt_width.GetValue())
        except ValueError:
            dim_x = Length(DEFAULT_LEN)
            dim_y = Length(DEFAULT_LEN)
        result, center, angle, signx, signy = self.calculate_square()
        dim_x *= signx
        dim_y *= signy
        angle = angle * 360 / tau
        if result:
            p = self.context
            units = p.units_name

            #            self.context("circle {x}mm {y}mm 2mm stroke green".format(x=round(self.coord_a[0]/UNITS_PER_MM,2),y=round(self.coord_a[1]/UNITS_PER_MM,2)) )
            #            self.context("circle {x}mm {y}mm 2mm stroke green".format(x=round(self.coord_b[0]/UNITS_PER_MM,2),y=round(self.coord_b[1]/UNITS_PER_MM,2)) )
            #            self.context("circle {x}mm {y}mm 2mm stroke red".format(x=round(self.coord_c[0]/UNITS_PER_MM,2),y=round(self.coord_c[1]/UNITS_PER_MM,2)) )

            if self.check_square.GetValue():
                self.context(
                    f"circle "
                    f"{str(Length(amount=center[0], digits=5, preferred_units=units))} "
                    f"{str(Length(amount=center[1], digits=5, preferred_units=units))} "
                    f"1mm stroke black\n"
                )
            self.context(
                f"rect "
                f"{str(Length(amount=center[0], digits=5, preferred_units=units))} "
                f"{str(Length(amount=center[1], digits=5, preferred_units=units))} "
                f"{str(dim_x.length_mm)} "
                f"{str(dim_y.length_mm)} "
                f"rotate {angle}deg "
                f"-x {str(Length(amount=center[0], digits=5, preferred_units=units))} "
                f"-y {str(Length(amount=center[1], digits=5, preferred_units=units))}\n"
            )
            if self.check_ref_square.GetValue():
                self.context("reference\n")
        event.Skip()

    @signal_listener("driver;position")
    @signal_listener("emulator;position")
    def on_update_laser(self, origin, pos):
        self.laserposition = (pos[2], pos[3])


class LaserTool(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(551, 234, submenu="Operations", *args, **kwds)
        self.panel = LaserToolPanel(self, wx.ID_ANY, context=self.context)
        _icon = wx.NullIcon
        # _icon.CopyFromBitmap(icons8_computer_support_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Place Template"))

    def window_open(self):
        pass

    def window_close(self):
        pass

    def delegates(self):
        yield self.panel

    @staticmethod
    def submenu():
        return ("Laser-Tools", "Place Template")
