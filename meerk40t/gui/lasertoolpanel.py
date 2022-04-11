import wx
from wx import aui

from meerk40t.core.units import ViewPort, Length
from meerk40t.gui.icons import instruction_circle, instruction_rectangle
from math import sqrt

_ = wx.GetTranslation

def register_panel_lasertool(window, context):
    panel = LaserToolPanel(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .MinSize(80, 165)
        .FloatingSize(120, 195)
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
        self.laserposition = None

        sizer_main = wx.BoxSizer(wx.VERTICAL)

        self.nbook_lasertools = wx.Notebook(self, wx.ID_ANY)
        sizer_main.Add(self.nbook_lasertools, 1, wx.EXPAND, 0)

        self.nb_circle = wx.Panel(self.nbook_lasertools, wx.ID_ANY)
        self.nbook_lasertools.AddPage(self.nb_circle, _("Find center"))

        sizer_circle = wx.BoxSizer(wx.VERTICAL)

        sizer_9 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_circle.Add(sizer_9, 0, wx.EXPAND, 0)

        sizer_10 = wx.BoxSizer(wx.VERTICAL)
        sizer_9.Add(sizer_10, 0, wx.EXPAND, 0)

        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10.Add(sizer_1, 1, wx.EXPAND, 0)

        label_1 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("A"))
        label_1.SetMinSize((20, 23))
        sizer_1.Add(label_1, 0, 0, 0)

        self.btnSet1 = wx.Button(self.nb_circle, wx.ID_ANY, _("Get"))
        self.btnSet1.SetToolTip(_("Place the laser over the desired point and press..."))
        sizer_1.Add(self.btnSet1, 0, 0, 0)

        self.lbl_pos_1 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("<empty>"))
        sizer_1.Add(self.lbl_pos_1, 0, 0, 0)

        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10.Add(sizer_2, 1, wx.EXPAND, 0)

        label_2 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("B"))
        label_2.SetMinSize((20, 23))
        sizer_2.Add(label_2, 0, 0, 0)

        self.btnSet2 = wx.Button(self.nb_circle, wx.ID_ANY, _("Get"))
        self.btnSet2.SetToolTip(_("Place the laser over the desired point and press..."))
        sizer_2.Add(self.btnSet2, 0, 0, 0)

        self.lbl_pos_2 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("<empty>"))
        sizer_2.Add(self.lbl_pos_2, 0, 0, 0)

        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10.Add(sizer_3, 1, wx.EXPAND, 0)

        label_3 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("C"))
        label_3.SetMinSize((20, 23))
        sizer_3.Add(label_3, 0, 0, 0)

        self.btnSet3 = wx.Button(self.nb_circle, wx.ID_ANY, _("Get"))
        self.btnSet3.SetToolTip(_("Place the laser over the desired point and press..."))
        sizer_3.Add(self.btnSet3, 0, 0, 0)

        self.lbl_pos_3 = wx.StaticText(self.nb_circle, wx.ID_ANY, _("<empty>"))
        sizer_3.Add(self.lbl_pos_3, 0, 0, 0)

        image1 = wx.StaticBitmap(self.nb_circle, wx.ID_ANY, instruction_circle.GetBitmap())
        instructions = _("Instruction: place the laser on three points on the circumference of the circle on the bed and confirm the position by clicking on the buttons below.\nMK will find the center for you and place the laser above it or will recreate the circle for futher processing.")
        image1.SetToolTip(instructions)
        sizer_9.Add(image1, 1, 0, 0)

        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_circle.Add(sizer_4, 0, wx.EXPAND, 0)

        self.btn_move_to_center = wx.Button(self.nb_circle, wx.ID_ANY, _("Move to center"))
        sizer_4.Add(self.btn_move_to_center, 0, 0, 0)

        self.btn_create_circle = wx.Button(self.nb_circle, wx.ID_ANY, _("Create circle"))
        sizer_4.Add(self.btn_create_circle, 0, 0, 0)

        self.check_reference_1 = wx.CheckBox(self.nb_circle, wx.ID_ANY, _("Make reference"))
        self.check_reference_1.SetMinSize((-1, 23))
        sizer_4.Add(self.check_reference_1, 0, 0, 0)

        self.nb_rectangle = wx.Panel(self.nbook_lasertools, wx.ID_ANY)
        self.nbook_lasertools.AddPage(self.nb_rectangle, _("Place rectangle"))

        sizer_rectangle = wx.BoxSizer(wx.VERTICAL)

        sizer_11 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_rectangle.Add(sizer_11, 0, wx.EXPAND, 0)

        sizer_12 = wx.BoxSizer(wx.VERTICAL)
        sizer_11.Add(sizer_12, 0, wx.EXPAND, 0)

        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_12.Add(sizer_5, 1, wx.EXPAND, 0)

        label_4 = wx.StaticText(self.nb_rectangle, wx.ID_ANY, _("Side A 1"))
        label_4.SetMinSize((45, 23))
        sizer_5.Add(label_4, 0, 0, 0)

        self.btnSet1_copy = wx.Button(self.nb_rectangle, wx.ID_ANY, _("Get"))
        self.btnSet1_copy.SetToolTip(_("Place the laser over the desired point and press..."))
        sizer_5.Add(self.btnSet1_copy, 0, 0, 0)

        self.lbl_pos_4 = wx.StaticText(self.nb_rectangle, wx.ID_ANY, _("<empty>"))
        sizer_5.Add(self.lbl_pos_4, 0, 0, 0)

        sizer_6 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_12.Add(sizer_6, 1, wx.EXPAND, 0)

        label_5 = wx.StaticText(self.nb_rectangle, wx.ID_ANY, _("Side A 2"))
        label_5.SetMinSize((45, 23))
        sizer_6.Add(label_5, 0, 0, 0)

        self.btnSet2_copy = wx.Button(self.nb_rectangle, wx.ID_ANY, _("Get"))
        self.btnSet2_copy.SetToolTip(_("Place the laser over the desired point and press..."))
        sizer_6.Add(self.btnSet2_copy, 0, 0, 0)

        self.lbl_pos_5 = wx.StaticText(self.nb_rectangle, wx.ID_ANY, _("<empty>"))
        sizer_6.Add(self.lbl_pos_5, 0, 0, 0)

        sizer_7 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_12.Add(sizer_7, 1, wx.EXPAND, 0)

        label_6 = wx.StaticText(self.nb_rectangle, wx.ID_ANY, _("Side B"))
        label_6.SetMinSize((45, 23))
        sizer_7.Add(label_6, 0, 0, 0)

        self.btnSet3_copy = wx.Button(self.nb_rectangle, wx.ID_ANY, _("Get"))
        self.btnSet3_copy.SetToolTip(_("Place the laser over the desired point and press..."))
        sizer_7.Add(self.btnSet3_copy, 0, 0, 0)

        self.lbl_pos_6 = wx.StaticText(self.nb_rectangle, wx.ID_ANY, _("<empty>"))
        sizer_7.Add(self.lbl_pos_6, 0, 0, 0)

        image2 = wx.StaticBitmap(self.nb_rectangle, wx.ID_ANY, instruction_rectangle.GetBitmap())
        instructions = _("Instruction: place the laser on two points of one side of a rectangle on the bed and confirm the position by clicking on the buttons below. Then choose one point on the other side of the corner.\nMK will create a rectangle for you for futher processing.")
        image2.SetToolTip(instructions)
        sizer_11.Add(image2, 1, 0, 0)

        sizer_8 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_rectangle.Add(sizer_8, 0, wx.EXPAND, 0)

        self.btn_create_rectangle = wx.Button(self.nb_rectangle, wx.ID_ANY, _("Create rectangle"))
        sizer_8.Add(self.btn_create_rectangle, 0, 0, 0)

        self.check_reference_2 = wx.CheckBox(self.nb_rectangle, wx.ID_ANY, _("Make reference"))
        self.check_reference_2.SetMinSize((-1, 23))
        sizer_8.Add(self.check_reference_2, 0, 0, 0)

        self.nb_rectangle.SetSizer(sizer_rectangle)

        self.nb_circle.SetSizer(sizer_circle)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        self.Layout()

        self.btnSet1.Bind(wx.EVT_BUTTON, self.on_click_get1)
        self.btnSet2.Bind(wx.EVT_BUTTON, self.on_click_get2)
        self.btnSet3.Bind(wx.EVT_BUTTON, self.on_click_get3)
        self.btn_move_to_center.Bind(wx.EVT_BUTTON, self.on_btn_move_center)
        self.btn_create_circle.Bind(wx.EVT_BUTTON, self.on_btn_create_circle)
        self.btnSet1_copy.Bind(wx.EVT_BUTTON, self.on_click_get1)
        self.btnSet2_copy.Bind(wx.EVT_BUTTON, self.on_click_get2)
        self.btnSet3_copy.Bind(wx.EVT_BUTTON, self.on_click_get3)
        self.btn_create_rectangle.Bind(wx.EVT_BUTTON, self.on_btn_create_rectangle)
        # end wxGlade

    def set_coord(self, idx=0, position=None):
        if position is None:
            label_string = _("<empty>")
        else:
            p = self.context
            units = p.units_name
            label_string = "({x}, {y})".format(
                x=str(Length(amount=position[0], digits=3, preferred_units=units)),
                y=str(Length(amount=position[1], digits=3, preferred_units=units)))
        if idx == 0:
            self.lbl_pos_1.Label = label_string
            self.lbl_pos_4.Label = label_string
            self.coord_a = position
            self.check_input()
        elif idx == 1:
            self.lbl_pos_2.Label = label_string
            self.lbl_pos_5.Label = label_string
            self.coord_b = position
            self.check_input()
        elif idx == 2:
            self.lbl_pos_3.Label = label_string
            self.lbl_pos_6.Label = label_string
            self.coord_c = position
            self.check_input()

    def check_input(self):
        if self.coord_a is None or self.coord_b is None or self.coord_c is None:
            value = False
        else:
            value = True
        self.btn_create_circle.Enable(value)
        self.btn_move_to_center.Enable(value)
        self.btn_create_rectangle.Enable(value)

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

    def calculate_center(self):
        '''
        Let's recall how the equation of a circle looks like in general form:
        x^2+y^2+2ax+2by+c=0

        Since all three points should belong to one circle, we can write a system of equations.

        x_1^2+y_1^2+2ax_1+2by_1+c=0\\x_2^2+y_2^2+2ax_2+2by_2+c=0\\x_3^2+y_3^2+2ax_3+2by_3+c=0

        The values (x_1, y_1), (x_2, y_2) and (x_3, y_3) are known. Let's rearrange with respect to unknowns a, b and c.

        2x_1a+2y_1b+c + x_1^2+y_1^2+=0\\2x_2a+2y_2b+c+x_2^2+y_2^2=0\\2x_3a+2y_3b+c+x_3^2+y_3^2=0
        '''
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

        f = (((sx13) * (x12) + (sy13) *
            (x12) + (sx21) * (x13) +
            (sy21) * (x13)) // (2 *
            ((y31) * (x12) - (y21) * (x13))))

        g = (((sx13) * (y12) + (sy13) * (y12) +
            (sx21) * (y13) + (sy21) * (y13)) //
            (2 * ((x31) * (y12) - (x21) * (y13))))

        c = (-pow(self.coord_a[0], 2) - pow(self.coord_a[1], 2) -
            2 * g * self.coord_a[0] - 2 * f * self.coord_a[1])

        # eqn of circle be x^2 + y^2 + 2*g*x + 2*f*y + c = 0
        # where centre is (h = -g, k = -f) and
        # radius r as r^2 = h^2 + k^2 - c
        h = -g
        k = -f
        sqr_of_r = h * h + k * k - c

        # r is the radius
        if sqr_of_r<0:
            result = False
        else:
            r = round(sqrt(sqr_of_r), 5)

        # print("Centre = (", h, ", ", k, ")")
        # print("Radius = ", r)
        center = (h, k)
        radius = r
        return result, center, radius

    def calculate_rectangle(self):
        result = False
        center = None
        angle = None
        return result, center, angle

    def on_btn_move_center(self, event):  # wxGlade: clsLasertools.<event_handler>
        result, center, radius = self.calculate_center()
        if result:
            p = self.context
            self.context("move_absolute {x} {y}\n".format(
                x=str(Length(amount=center[0], digits=5, preferred_units=p.units)),
                y=str(Length(amount=center[1], digits=5, preferred_units=p.units))
            ))
        event.Skip()

    def on_btn_create_circle(self, event):  # wxGlade: clsLasertools.<event_handler>
        result, center, radius = self.calculate_center()
        if result:
            p = self.context
            units = p.units_name
            self.context("move_absolute {x} {y}\n".format(
                x=str(Length(amount=center[0], digits=5, preferred_units=units)),
                y=str(Length(amount=center[1], digits=5, preferred_units=units))
            ))
            self.context("circle {x} {y} {r}\n".format(
                x=str(Length(amount=center[0], digits=5, preferred_units=units)),
                y=str(Length(amount=center[1], digits=5, preferred_units=units)),
                r=str(Length(amount=radius, digits=5, preferred_units=units))
            ))
            if self.check_reference_1.GetValue():
                pass # Not yet implemented
        event.Skip()

    def on_btn_create_rectangle(self, event):  # wxGlade: clsLasertools.<event_handler>
        result, center, angle = self.calculate_rectangle()
        if result:
            self.context("rect {x} {y} 5cm 5cm rotate {angle}\n".format(x=center[0], y=center[0], angle=angle))
            if self.check_reference_1.GetValue():
                pass # Not yet implemented
        event.Skip()

    def pane_show(self, *args):
        self.context.listen("driver;position", self.on_update_laser)
        self.context.listen("emulator;position", self.on_update_laser)

    def pane_hide(self, *args):
        self.context.unlisten("driver;position", self.on_update_laser)
        self.context.unlisten("emulator;position", self.on_update_laser)

    def on_update_laser(self, origin, pos):
        self.laserposition = (pos[2], pos[3])
