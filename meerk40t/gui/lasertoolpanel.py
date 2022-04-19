from math import atan, sqrt, tau

import wx
from wx import aui

from meerk40t.core.units import UNITS_PER_MM, Length
from meerk40t.gui.icons import (
    instruction_circle,
    instruction_frame,
    instruction_rectangle,
)

_ = wx.GetTranslation


DEFAULT_LEN = "5cm"


def register_panel_lasertool(window, context):
    panel = LaserToolPanel(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .MinSize(220, 165)
        .FloatingSize(240, 195)
        .Hide()
        .Caption(_("Lasertools"))
        .CaptionVisible(not context.pane_lock)
        .Name("lasertool")
    )
    pane.dock_proportion = 150
    pane.control = panel
    pane.submenu = _("Tools")

    window.on_pane_add(pane)
    context.register("pane/lasertool", pane)


class LaserToolPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.coord_a = None
        self.coord_b = None
        self.coord_c = None
        self.additional_coords = None
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
        label_1.SetMinSize((20, 23))
        sizer_1.Add(label_1, 0, 0, 0)

        self.btn_set_circle_1 = wx.Button(self.nb_circle, wx.ID_ANY, _("Use position"))
        self.btn_set_circle_1.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_1.Add(self.btn_set_circle_1, 0, 0, 0)

        self.lbl_pos_1 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("<empty>"))
        sizer_1.Add(self.lbl_pos_1, 0, 0, 0)

        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10.Add(sizer_2, 1, wx.EXPAND, 0)

        label_2 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("B"))
        label_2.SetMinSize((20, 23))
        sizer_2.Add(label_2, 0, 0, 0)

        self.btn_set_circle_2 = wx.Button(self.nb_circle, wx.ID_ANY, _("Use position"))
        self.btn_set_circle_2.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_2.Add(self.btn_set_circle_2, 0, 0, 0)

        self.lbl_pos_2 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("<empty>"))
        sizer_2.Add(self.lbl_pos_2, 0, 0, 0)

        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10.Add(sizer_3, 1, wx.EXPAND, 0)

        label_3 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("C"))
        label_3.SetMinSize((20, 23))
        sizer_3.Add(label_3, 0, 0, 0)

        self.btn_set_circle_3 = wx.Button(self.nb_circle, wx.ID_ANY, _("Use position"))
        self.btn_set_circle_3.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_3.Add(self.btn_set_circle_3, 0, 0, 0)

        self.lbl_pos_3 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("<empty>"))
        sizer_3.Add(self.lbl_pos_3, 0, 0, 0)

        img_instruction_1 = wx.StaticBitmap(
            self.nb_circle, wx.ID_ANY, instruction_circle.GetBitmap()
        )
        instructions = _(
            "Instruction: place the laser on three points on the circumference of the circle on the bed and confirm the position by clicking on the buttons below.\nMK will find the center for you and place the laser above it or will recreate the circle for futher processing."
        )
        img_instruction_1.SetToolTip(instructions)
        sizer_9.Add(img_instruction_1, 1, 0, 0)

        sizer_chk = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_circle.Add(sizer_chk, 0, wx.EXPAND, 0)
        self.check_ref_circle = wx.CheckBox(
            self.nb_circle, wx.ID_ANY, _("Make reference")
        )
        self.check_ref_circle.SetMinSize((-1, 23))
        sizer_chk.Add(self.check_ref_circle, 0, 0, 0)
        self.check_circle = wx.CheckBox(self.nb_circle, wx.ID_ANY, _("Mark Center"))
        self.check_circle.SetMinSize((-1, 23))
        sizer_chk.Add(self.check_circle, 0, 0, 0)

        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_circle.Add(sizer_4, 0, wx.EXPAND, 0)

        self.btn_move_to_center = wx.Button(
            self.nb_circle, wx.ID_ANY, _("Move to center")
        )
        sizer_4.Add(self.btn_move_to_center, 0, 0, 0)

        self.btn_create_circle = wx.Button(
            self.nb_circle, wx.ID_ANY, _("Create circle")
        )
        sizer_4.Add(self.btn_create_circle, 0, 0, 0)

        # ------------------------ Rectangle with 2 (or more) points

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
        label_corner_1.SetMinSize((-1, 23))
        sizer_5a.Add(label_corner_1, 0, 0, 0)

        self.btn_set_rect_1 = wx.Button(self.nb_rectangle, wx.ID_ANY, _("Use position"))
        self.btn_set_rect_1.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_5a.Add(self.btn_set_rect_1, 0, 0, 0)

        self.lbl_pos_7 = wx.StaticText(self.nb_rectangle, wx.ID_ANY, _("<empty>"))
        sizer_5a.Add(self.lbl_pos_7, 0, 0, 0)

        sizer_6a = wx.BoxSizer(wx.HORIZONTAL)
        sizer_rect_vert.Add(sizer_6a, 1, wx.EXPAND, 0)

        label_corner_2 = wx.StaticText(self.nb_rectangle, wx.ID_ANY, _("Corner 2"))
        label_corner_2.SetMinSize((-1, 23))
        sizer_6a.Add(label_corner_2, 0, 0, 0)

        self.btn_set_rect_2 = wx.Button(self.nb_rectangle, wx.ID_ANY, _("Use position"))
        self.btn_set_rect_2.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_6a.Add(self.btn_set_rect_2, 0, 0, 0)

        self.lbl_pos_8 = wx.StaticText(self.nb_rectangle, wx.ID_ANY, _("<empty>"))
        sizer_6a.Add(self.lbl_pos_8, 0, 0, 0)

        sizer_6b = wx.BoxSizer(wx.HORIZONTAL)
        sizer_rect_vert.Add(sizer_6b, 1, wx.EXPAND, 0)

        self.btn_set_rect_3 = wx.Button(self.nb_rectangle, wx.ID_ANY, _("Add. point"))
        self.btn_set_rect_3.SetToolTip(_("If the shape is more complex then you can add additional corner points"))
        sizer_6b.Add(self.btn_set_rect_3, 0, 0, 0)
        self.btn_set_rect_4 = wx.Button(self.nb_rectangle, wx.ID_ANY, _("Clear"))
        self.btn_set_rect_4.SetToolTip(_("Clear additional points"))
        sizer_6b.Add(self.btn_set_rect_4, 0, 0, 0)

        self.lbl_pos_9 = wx.StaticText(self.nb_rectangle, wx.ID_ANY, _("<empty>"))
        sizer_6b.Add(self.lbl_pos_9, 0, 0, 0)

        self.img_instruction_2 = wx.StaticBitmap(self.nb_rectangle, wx.ID_ANY, instruction_frame.GetBitmap())
        instructions = _("Instruction: place the laser on one corner of the encompassing rectangle and confirm the position by clicking on the buttons below. Then choose the opposing corner.\nMK will create a rectangle for you for futher processing.")
        self.img_instruction_2.SetToolTip(instructions)
        sizer_rect_hor.Add(self.img_instruction_2, 1, 0, 0)

        sizer_chk_rect = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_rectangle.Add(sizer_chk_rect, 0, wx.EXPAND, 0)
        self.check_ref_frame = wx.CheckBox(
            self.nb_rectangle, wx.ID_ANY, _("Make reference")
        )
        self.check_ref_frame.SetMinSize((-1, 23))
        sizer_chk_rect.Add(self.check_ref_frame, 0, 0, 0)

        sizer_8a = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_rectangle.Add(sizer_8a, 0, wx.EXPAND, 0)

        self.btn_create_frame = wx.Button(
            self.nb_rectangle, wx.ID_ANY, _("Create frame")
        )
        sizer_8a.Add(self.btn_create_frame, 0, 0, 0)

        # ------------------------ Square with 3 points

        self.nb_square = wx.Panel(self.nbook_lasertools, wx.ID_ANY)
        self.nbook_lasertools.AddPage(self.nb_square, _("Place rectangle"))

        self.sizer_square = wx.BoxSizer(wx.VERTICAL)

        sizer_sqare_hor = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_square.Add(sizer_sqare_hor, 0, wx.EXPAND, 0)

        sizer_sqare_vert = wx.BoxSizer(wx.VERTICAL)
        sizer_sqare_hor.Add(sizer_sqare_vert, 0, wx.EXPAND, 0)

        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sqare_vert.Add(sizer_5, 1, wx.EXPAND, 0)

        label_4 = wx.StaticText(self.nb_square, wx.ID_ANY, _("Corner A"))
        label_4.SetMinSize((45, 23))
        sizer_5.Add(label_4, 0, 0, 0)

        self.btn_set_square_1 = wx.Button(self.nb_square, wx.ID_ANY, _("Use position"))
        self.btn_set_square_1.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_5.Add(self.btn_set_square_1, 0, 0, 0)

        self.lbl_pos_4 = wx.StaticText(self.nb_square, wx.ID_ANY, _("<empty>"))
        sizer_5.Add(self.lbl_pos_4, 0, 0, 0)

        sizer_6 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sqare_vert.Add(sizer_6, 1, wx.EXPAND, 0)

        label_5 = wx.StaticText(self.nb_square, wx.ID_ANY, _("Corner B"))
        label_5.SetMinSize((45, 23))
        sizer_6.Add(label_5, 0, 0, 0)

        self.btn_set_square_2 = wx.Button(self.nb_square, wx.ID_ANY, _("Use position"))
        self.btn_set_square_2.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_6.Add(self.btn_set_square_2, 0, 0, 0)

        self.lbl_pos_5 = wx.StaticText(self.nb_square, wx.ID_ANY, _("<empty>"))
        sizer_6.Add(self.lbl_pos_5, 0, 0, 0)

        sizer_7 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sqare_vert.Add(sizer_7, 1, wx.EXPAND, 0)

        label_6 = wx.StaticText(self.nb_square, wx.ID_ANY, _("Corner C"))
        label_6.SetMinSize((45, 23))
        sizer_7.Add(label_6, 0, 0, 0)

        self.btn_set_square_3 = wx.Button(self.nb_square, wx.ID_ANY, _("Use position"))
        self.btn_set_square_3.SetToolTip(
            _("Place the laser over the desired point and click...")
        )
        sizer_7.Add(self.btn_set_square_3, 0, 0, 0)

        self.lbl_pos_6 = wx.StaticText(self.nb_square, wx.ID_ANY, _("<empty>"))
        sizer_7.Add(self.lbl_pos_6, 0, 0, 0)

        self.img_instruction_3 = wx.StaticBitmap(self.nb_square, wx.ID_ANY, instruction_rectangle.GetBitmap())
        instructions = _("Instruction: place the laser on three corners of rectangle on the bed and confirm the position by clicking on the buttons below.\nMK will create a rectangle for you for futher processing.")
        self.img_instruction_3.SetToolTip(instructions)
        sizer_sqare_hor.Add(self.img_instruction_3, 1, 0, 0)

        sizer_chk_square = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_square.Add(sizer_chk_square, 0, wx.EXPAND, 0)
        self.check_ref_square = wx.CheckBox(
            self.nb_square, wx.ID_ANY, _("Make reference")
        )
        self.check_ref_square.SetMinSize((-1, 23))
        sizer_chk_square.Add(self.check_ref_square, 0, 0, 0)
        self.check_square = wx.CheckBox(self.nb_square, wx.ID_ANY, _("Mark Center"))
        self.check_square.SetMinSize((-1, 23))
        sizer_chk_square.Add(self.check_square, 0, 0, 0)

        sizer_8 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_square.Add(sizer_8, 0, wx.EXPAND, 0)

        self.btn_create_square = wx.Button(
            self.nb_square, wx.ID_ANY, _("Create square")
        )
        sizer_8.Add(self.btn_create_square, 0, 0, 0)

        self.nb_square.SetSizer(self.sizer_square)

        self.nb_circle.SetSizer(self.sizer_circle)

        self.nb_rectangle.SetSizer(self.sizer_rectangle)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        self.Layout()

        self.btn_set_circle_1.Bind(wx.EVT_BUTTON, self.on_click_get1)
        self.btn_set_circle_2.Bind(wx.EVT_BUTTON, self.on_click_get2)
        self.btn_set_circle_3.Bind(wx.EVT_BUTTON, self.on_click_get3)
        self.btn_move_to_center.Bind(wx.EVT_BUTTON, self.on_btn_move_center)
        self.btn_create_circle.Bind(wx.EVT_BUTTON, self.on_btn_create_circle)
        self.btn_set_rect_1.Bind(wx.EVT_BUTTON, self.on_click_get1)
        self.btn_set_rect_2.Bind(wx.EVT_BUTTON, self.on_click_get2)
        self.btn_set_rect_3.Bind(wx.EVT_BUTTON, self.on_click_get_additional)
        self.btn_set_rect_4.Bind(wx.EVT_BUTTON, self.on_click_clear_additional)
        self.btn_create_frame.Bind(wx.EVT_BUTTON, self.on_btn_create_frame)

        self.btn_set_square_1.Bind(wx.EVT_BUTTON, self.on_click_get1)
        self.btn_set_square_2.Bind(wx.EVT_BUTTON, self.on_click_get2)
        self.btn_set_square_3.Bind(wx.EVT_BUTTON, self.on_click_get3)
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

    def on_click_clear_additional(self, event):
        self.additional_coords = None
        self.lbl_pos_9.Label= _("<empty>")
        self.sizer_rectangle.Layout()
        event.Skip()


    def on_click_get_additional(self, event):
        if self.additional_coords is None:
            self.additional_coords = [self.laserposition]
        else:
            self.additional_coords.append(self.laserposition)
        self.lbl_pos_9.Label = _("%d points") % len(self.additional_coords)
        self.sizer_rectangle.Layout()
        event.Skip()

    def set_coord(self, idx=0, position=None):
        if position is None:
            label_string = _("<empty>")
        else:
            p = self.context
            units = p.units_name
            label_string = "({x}, {y})".format(
                x=str(Length(amount=position[0], digits=1, preferred_units=units)),
                y=str(Length(amount=position[1], digits=1, preferred_units=units)),
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
        event.Skip()

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
            f = ((sx13) * (x12) + (sy13) * (x12) + (sx21) * (x13) + (sy21) * (x13)) // (
                2 * ((y31) * (x12) - (y21) * (x13))
            )

            g = ((sx13) * (y12) + (sy13) * (y12) + (sx21) * (y13) + (sy21) * (y13)) // (
                2 * ((x31) * (y12) - (x21) * (y13))
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
        # We have three corners, they should represent a rectangle.
        # We will check whether this is the case. If the delta is smaller than 5 degrees
        # then we will correct the shape, if its bigger then we will create a rhombus...
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
        if not self.coord_a is None and not self.coord_b is None:
            x0 = self.coord_a[0]
            x1 = self.coord_b[0]
            y0 = self.coord_a[1]
            y1 = self.coord_b[1]
            xmin = min(x0, x1)
            xmax = max(x0, x1)
            ymin = min(y0, y1)
            ymax = max(y0, y1)
            if not self.additional_coords is None:
                for pt in self.additional_coords:
                    xmin = min(xmin, pt[0])
                    xmax = max(xmax, pt[0])
                    ymin = min(ymin, pt[1])
                    ymax = max(ymax, pt[1])

            width = xmax - xmin
            height = ymax - ymin
            if width != 0 and height != 0:
                left_top = (xmin, ymin)
                result = True
        return result, left_top, width, height

    def on_btn_move_center(self, event):  # wxGlade: clsLasertools.<event_handler>
        result, center, radius = self.calculate_center()
        if result:
            p = self.context
            units = p.units_name
            if self.check_circle.GetValue():
                self.context(
                    "circle {x} {y} 1mm stroke black\n".format(
                        x=str(
                            Length(amount=center[0], digits=5, preferred_units=units)
                        ),
                        y=str(
                            Length(amount=center[1], digits=5, preferred_units=units)
                        ),
                    )
                )

            self.context(
                "move_absolute {x} {y}\n".format(
                    x=str(Length(amount=center[0], digits=5, preferred_units=units)),
                    y=str(Length(amount=center[1], digits=5, preferred_units=units)),
                )
            )
        event.Skip()

    def on_btn_create_circle(self, event):  # wxGlade: clsLasertools.<event_handler>
        result, center, radius = self.calculate_center()
        if result:
            p = self.context
            units = p.units_name
            if self.check_circle.GetValue():
                self.context(
                    "circle {x} {y} 1mm stroke black\n".format(
                        x=str(
                            Length(amount=center[0], digits=5, preferred_units=units)
                        ),
                        y=str(
                            Length(amount=center[1], digits=5, preferred_units=units)
                        ),
                    )
                )
            self.context(
                "circle {x} {y} {r}\n".format(
                    x=str(Length(amount=center[0], digits=5, preferred_units=units)),
                    y=str(Length(amount=center[1], digits=5, preferred_units=units)),
                    r=str(Length(amount=radius, digits=5, preferred_units=units)),
                )
            )
            if self.check_ref_circle.GetValue():
                self.context("reference\n")
        event.Skip()

    def on_btn_create_frame(self, event):  # wxGlade: clsLasertools.<event_handler>
        result, left_top, width, height = self.calculate_frame()

        if result:
            p = self.context
            units = p.units_name

            self.context(
                "rect {x} {y} {wd} {ht}\n".format(
                    x=str(Length(amount=left_top[0], digits=5, preferred_units=units)),
                    y=str(Length(amount=left_top[1], digits=5, preferred_units=units)),
                    wd=str(Length(amount=width, digits=5, preferred_units=units)),
                    ht=str(Length(amount=height, digits=5, preferred_units=units)),
                )
            )
            if self.check_ref_frame.GetValue():
                self.context("reference\n")
        event.Skip()

    def on_btn_create_square(self, event):  # wxGlade: clsLasertools.<event_handler>
        try:
            dim_x = Length(self.txt_width.GetValue())
            dim_y = Length(self.txt_width.GetValue())
        except ValueError:
            dim_x = Length(DEFAULT_LEN)
            dim_y = Length(DEFAULT_LEN)
        result, center, angle, dim_x, dim_y = self.calculate_square()
        angle = angle * 360 / tau
        if result:
            p = self.context
            units = p.units_name

            #            self.context("circle {x}mm {y}mm 2mm stroke green".format(x=round(self.coord_a[0]/UNITS_PER_MM,2),y=round(self.coord_a[1]/UNITS_PER_MM,2)) )
            #            self.context("circle {x}mm {y}mm 2mm stroke green".format(x=round(self.coord_b[0]/UNITS_PER_MM,2),y=round(self.coord_b[1]/UNITS_PER_MM,2)) )
            #            self.context("circle {x}mm {y}mm 2mm stroke red".format(x=round(self.coord_c[0]/UNITS_PER_MM,2),y=round(self.coord_c[1]/UNITS_PER_MM,2)) )

            if self.check_square.GetValue():
                self.context(
                    "circle {x} {y} 1mm stroke black\n".format(
                        x=str(
                            Length(amount=center[0], digits=5, preferred_units=units)
                        ),
                        y=str(
                            Length(amount=center[1], digits=5, preferred_units=units)
                        ),
                    )
                )
            self.context(
                "rect {x} {y} {wd} {ht} rotate {angle}deg -x {x} -y {y}\n".format(
                    x=str(Length(amount=center[0], digits=5, preferred_units=units)),
                    y=str(Length(amount=center[1], digits=5, preferred_units=units)),
                    wd=str(dim_x.length_mm),
                    ht=str(dim_y.length_mm),
                    angle=angle,
                )
            )
            if self.check_ref_square.GetValue():
                self.context("reference\n")
        event.Skip()

    def pane_show(self, *args):
        self.context.listen("driver;position", self.on_update_laser)
        self.context.listen("emulator;position", self.on_update_laser)

    def pane_hide(self, *args):
        self.context.unlisten("driver;position", self.on_update_laser)
        self.context.unlisten("emulator;position", self.on_update_laser)

    def on_update_laser(self, origin, pos):
        self.laserposition = (pos[2], pos[3])
