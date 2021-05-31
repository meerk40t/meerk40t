import wx

from ..svgelements import Length

_ = wx.GetTranslation


from .icons import (
    icon_corner1,
    icon_corner2,
    icon_corner3,
    icon_corner4,
    icons8_center_of_gravity_50,
    icons8_compress_50,
    icons8_delete_50,
    icons8_down,
    icons8_down_50,
    icons8_down_left_50,
    icons8_down_right_50,
    icons8_enlarge_50,
    icons8_home_filled_50,
    icons8_laser_beam_52,
    icons8_left,
    icons8_left_50,
    icons8_level_1_50,
    icons8_lock_50,
    icons8_move_50,
    icons8_padlock_50,
    icons8_pentagon_50,
    icons8_pentagon_square_50,
    icons8_right,
    icons8_right_50,
    icons8_rotate_left_50,
    icons8_rotate_right_50,
    icons8_square_border_50,
    icons8_up_50,
    icons8_up_left_50,
    icons8_up_right_50,
    icons8up,
)

MILS_IN_MM = 39.3701


class Jog(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: Jog.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL

        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        context.setting(float, "navigate_jog", 394.0)
        self.button_navigate_up_left = wx.BitmapButton(
            self, wx.ID_ANY, icons8_up_left_50.GetBitmap()
        )
        self.button_navigate_up = wx.BitmapButton(
            self, wx.ID_ANY, icons8_up_50.GetBitmap()
        )
        self.button_navigate_up_right = wx.BitmapButton(
            self, wx.ID_ANY, icons8_up_right_50.GetBitmap()
        )
        self.button_navigate_left = wx.BitmapButton(
            self, wx.ID_ANY, icons8_left_50.GetBitmap()
        )
        self.button_navigate_home = wx.BitmapButton(
            self, wx.ID_ANY, icons8_home_filled_50.GetBitmap()
        )
        self.button_navigate_right = wx.BitmapButton(
            self, wx.ID_ANY, icons8_right_50.GetBitmap()
        )
        self.button_navigate_down_left = wx.BitmapButton(
            self, wx.ID_ANY, icons8_down_left_50.GetBitmap()
        )
        self.button_navigate_down = wx.BitmapButton(
            self, wx.ID_ANY, icons8_down_50.GetBitmap()
        )
        self.button_navigate_down_right = wx.BitmapButton(
            self, wx.ID_ANY, icons8_down_right_50.GetBitmap()
        )
        self.button_navigate_unlock = wx.BitmapButton(
            self, wx.ID_ANY, icons8_padlock_50.GetBitmap()
        )
        self.button_navigate_lock = wx.BitmapButton(
            self, wx.ID_ANY, icons8_lock_50.GetBitmap()
        )
        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_ul, self.button_navigate_up_left
        )
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_u, self.button_navigate_up)
        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_ur, self.button_navigate_up_right
        )
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_l, self.button_navigate_left)
        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_home, self.button_navigate_home
        )
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_r, self.button_navigate_right)
        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_dl, self.button_navigate_down_left
        )
        self.Bind(wx.EVT_BUTTON, self.on_button_navigate_d, self.button_navigate_down)
        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_dr, self.button_navigate_down_right
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_unlock, self.button_navigate_unlock
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_lock, self.button_navigate_lock
        )
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: Jog.__set_properties
        self.button_navigate_up_left.SetToolTip(
            _("Move laser diagonally in the up and left direction")
        )
        self.button_navigate_up_left.SetSize(self.button_navigate_up_left.GetBestSize())
        self.button_navigate_up.SetToolTip(_("Move laser in the up direction"))
        self.button_navigate_up.SetSize(self.button_navigate_up.GetBestSize())
        self.button_navigate_up_right.SetToolTip(
            _("Move laser diagonally in the up and right direction")
        )
        self.button_navigate_up_right.SetSize(
            self.button_navigate_up_right.GetBestSize()
        )
        self.button_navigate_left.SetToolTip(_("Move laser in the left direction"))
        self.button_navigate_left.SetSize(self.button_navigate_left.GetBestSize())
        self.button_navigate_home.SetSize(self.button_navigate_home.GetBestSize())
        self.button_navigate_right.SetToolTip(_("Move laser in the right direction"))
        self.button_navigate_right.SetSize(self.button_navigate_right.GetBestSize())
        self.button_navigate_down_left.SetToolTip(
            _("Move laser diagonally in the down and left direction")
        )
        self.button_navigate_down_left.SetSize(
            self.button_navigate_down_left.GetBestSize()
        )
        self.button_navigate_down.SetToolTip(_("Move laser in the down direction"))
        self.button_navigate_down.SetSize(self.button_navigate_down.GetBestSize())
        self.button_navigate_down_right.SetToolTip(
            _("Move laser diagonally in the down and right direction")
        )
        self.button_navigate_down_right.SetSize(
            self.button_navigate_down_right.GetBestSize()
        )
        self.button_navigate_unlock.SetToolTip(_("Unlock the laser rail"))
        self.button_navigate_unlock.SetSize(self.button_navigate_unlock.GetBestSize())
        self.button_navigate_lock.SetToolTip(_("Lock the laser rail"))
        self.button_navigate_lock.SetSize(self.button_navigate_lock.GetBestSize())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Jog.__do_layout
        navigation_sizer = wx.FlexGridSizer(4, 3, 0, 0)
        navigation_sizer.Add(self.button_navigate_up_left, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_up, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_up_right, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_left, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_home, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_right, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_down_left, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_down, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_down_right, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_unlock, 0, 0, 0)
        navigation_sizer.Add((0, 0), 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_lock, 0, 0, 0)
        self.SetSizer(navigation_sizer)
        navigation_sizer.Fit(self)
        self.Layout()
        # end wxGlade

    def on_button_navigate_home(self, event):  # wxGlade: Navigation.<event_handler>
        self.context("home\n")

    def on_button_navigate_ul(self, event):  # wxGlade: Navigation.<event_handler>
        dx = -self.context.navigate_jog
        dy = -self.context.navigate_jog
        self.context("move_relative %d %d\n" % (dx, dy))

    def on_button_navigate_u(self, event):  # wxGlade: Navigation.<event_handler>
        dx = 0
        dy = -self.context.navigate_jog
        self.context("move_relative %d %d\n" % (dx, dy))

    def on_button_navigate_ur(self, event):  # wxGlade: Navigation.<event_handler>
        dx = self.context.navigate_jog
        dy = -self.context.navigate_jog
        self.context("move_relative %d %d\n" % (dx, dy))

    def on_button_navigate_l(self, event):  # wxGlade: Navigation.<event_handler>
        dx = -self.context.navigate_jog
        dy = 0
        self.context("move_relative %d %d\n" % (dx, dy))

    def on_button_navigate_r(self, event):  # wxGlade: Navigation.<event_handler>
        dx = self.context.navigate_jog
        dy = 0
        self.context("move_relative %d %d\n" % (dx, dy))

    def on_button_navigate_dl(self, event):  # wxGlade: Navigation.<event_handler>
        dx = -self.context.navigate_jog
        dy = self.context.navigate_jog
        self.context("move_relative %d %d\n" % (dx, dy))

    def on_button_navigate_d(self, event):  # wxGlade: Navigation.<event_handler>
        dx = 0
        dy = self.context.navigate_jog
        self.context("move_relative %d %d\n" % (dx, dy))

    def on_button_navigate_dr(self, event):  # wxGlade: Navigation.<event_handler>
        dx = self.context.navigate_jog
        dy = self.context.navigate_jog
        self.context("move_relative %d %d\n" % (dx, dy))

    def on_button_navigate_unlock(self, event):  # wxGlade: Navigation.<event_handler>
        self.context("unlock\n")

    def on_button_navigate_lock(self, event):  # wxGlade: Navigation.<event_handler>
        self.context("lock\n")


class Drag(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: Drag.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.button_align_corner_top_left = wx.BitmapButton(
            self, wx.ID_ANY, icon_corner1.GetBitmap()
        )
        self.button_align_drag_up = wx.BitmapButton(
            self, wx.ID_ANY, icons8up.GetBitmap()
        )
        self.button_align_corner_top_right = wx.BitmapButton(
            self, wx.ID_ANY, icon_corner2.GetBitmap()
        )
        self.button_align_drag_left = wx.BitmapButton(
            self, wx.ID_ANY, icons8_left.GetBitmap()
        )
        self.button_align_center = wx.BitmapButton(
            self, wx.ID_ANY, icons8_square_border_50.GetBitmap()
        )
        self.button_align_drag_right = wx.BitmapButton(
            self, wx.ID_ANY, icons8_right.GetBitmap()
        )
        self.button_align_corner_bottom_left = wx.BitmapButton(
            self, wx.ID_ANY, icon_corner4.GetBitmap()
        )
        self.button_align_drag_down = wx.BitmapButton(
            self, wx.ID_ANY, icons8_down.GetBitmap()
        )
        self.button_align_corner_bottom_right = wx.BitmapButton(
            self, wx.ID_ANY, icon_corner3.GetBitmap()
        )
        self.button_align_first_position = wx.BitmapButton(
            self, wx.ID_ANY, icons8_level_1_50.GetBitmap()
        )
        self.button_align_trace_hull = wx.BitmapButton(
            self, wx.ID_ANY, icons8_pentagon_50.GetBitmap()
        )
        self.button_align_trace_quick = wx.BitmapButton(
            self, wx.ID_ANY, icons8_pentagon_square_50.GetBitmap()
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_align_corner_tl, self.button_align_corner_top_left)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_drag_up, self.button_align_drag_up)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_corner_tr, self.button_align_corner_top_right)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_drag_left, self.button_align_drag_left)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_center, self.button_align_center)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_drag_right, self.button_align_drag_right)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_corner_bl, self.button_align_corner_bottom_left)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_drag_down, self.button_align_drag_down)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_corner_br, self.button_align_corner_bottom_right)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_trace_hull, self.button_align_trace_hull)
        self.Bind(wx.EVT_BUTTON, self.on_button_align_trace_quick, self.button_align_trace_quick)
        # end wxGlade
        self.elements = None
        self.console = None
        self.design_locked = False
        self.drag_ready(False)

    def __set_properties(self):
        # begin wxGlade: Drag.__set_properties
        self.button_align_corner_top_left.SetToolTip(
            _("Align laser with the upper left corner of the selection")
        )
        self.button_align_corner_top_left.SetSize(
            self.button_align_corner_top_left.GetBestSize()
        )
        self.button_align_drag_up.SetSize(self.button_align_drag_up.GetBestSize())
        self.button_align_corner_top_right.SetToolTip(
            _("Align laser with the upper right corner of the selection")
        )
        self.button_align_corner_top_right.SetSize(
            self.button_align_corner_top_right.GetBestSize()
        )
        self.button_align_drag_left.SetSize(self.button_align_drag_left.GetBestSize())
        self.button_align_center.SetToolTip(
            _("Align laser with the center of the selection")
        )
        self.button_align_center.SetSize(self.button_align_center.GetBestSize())
        self.button_align_drag_right.SetSize(self.button_align_drag_right.GetBestSize())
        self.button_align_corner_bottom_left.SetToolTip(
            _("Align laser with the lower left corner of the selection")
        )
        self.button_align_corner_bottom_left.SetSize(
            self.button_align_corner_bottom_left.GetBestSize()
        )
        self.button_align_drag_down.SetSize(self.button_align_drag_down.GetBestSize())
        self.button_align_corner_bottom_right.SetToolTip(
            _("Align laser with the lower right corner of the selection")
        )
        self.button_align_corner_bottom_right.SetSize(
            self.button_align_corner_bottom_right.GetBestSize()
        )
        self.button_align_first_position.SetToolTip(
            _("Align laser with the first position")
        )
        self.button_align_first_position.SetSize(
            self.button_align_first_position.GetBestSize()
        )
        self.button_align_trace_hull.SetToolTip(
            _("Perform a convex hull trace of the selection")
        )
        self.button_align_trace_hull.SetSize(self.button_align_trace_hull.GetBestSize())
        self.button_align_trace_quick.SetToolTip(
            _("Perform a simple trace of the selection")
        )
        self.button_align_trace_quick.SetSize(
            self.button_align_trace_quick.GetBestSize()
        )
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Drag.__do_layout
        align_sizer = wx.FlexGridSizer(4, 3, 0, 0)
        align_sizer.Add(self.button_align_corner_top_left, 0, 0, 0)
        align_sizer.Add(self.button_align_drag_up, 0, 0, 0)
        align_sizer.Add(self.button_align_corner_top_right, 0, 0, 0)
        align_sizer.Add(self.button_align_drag_left, 0, 0, 0)
        align_sizer.Add(self.button_align_center, 0, 0, 0)
        align_sizer.Add(self.button_align_drag_right, 0, 0, 0)
        align_sizer.Add(self.button_align_corner_bottom_left, 0, 0, 0)
        align_sizer.Add(self.button_align_drag_down, 0, 0, 0)
        align_sizer.Add(self.button_align_corner_bottom_right, 0, 0, 0)
        align_sizer.Add(self.button_align_first_position, 0, 0, 0)
        align_sizer.Add(self.button_align_trace_hull, 0, 0, 0)
        align_sizer.Add(self.button_align_trace_quick, 0, 0, 0)
        self.SetSizer(align_sizer)
        align_sizer.Fit(self)
        self.Layout()
        # end wxGlade

    def drag_ready(self, v):
        self.design_locked = v
        self.button_align_drag_down.Enable(v)
        self.button_align_drag_up.Enable(v)
        self.button_align_drag_right.Enable(v)
        self.button_align_drag_left.Enable(v)

    def on_button_align_center(self, event):  # wxGlade: Navigation.<event_handler>
        elements = self.context.elements
        elements.validate_selected_area()
        bbox = elements.selected_area()
        if bbox is None:
            return
        px = (bbox[0] + bbox[2]) / 2.0
        py = (bbox[3] + bbox[1]) / 2.0
        self.context("move_absolute %f %f\n" % (px, py))
        self.drag_ready(True)

    def on_button_align_corner_tl(self, event):  # wxGlade: Navigation.<event_handler>
        elements = self.context.elements
        elements.validate_selected_area()
        bbox = elements.selected_area()
        if bbox is None:
            return
        self.context("move_absolute %f %f\n" % (bbox[0], bbox[1]))
        self.drag_ready(True)

    def on_button_align_corner_tr(self, event):  # wxGlade: Navigation.<event_handler>
        elements = self.context.elements
        elements.validate_selected_area()
        bbox = elements.selected_area()
        if bbox is None:
            return
        self.context("move_absolute %f %f\n" % (bbox[2], bbox[1]))
        self.drag_ready(True)

    def on_button_align_corner_bl(self, event):  # wxGlade: Navigation.<event_handler>
        elements = self.context.elements
        elements.validate_selected_area()
        bbox = elements.selected_area()
        if bbox is None:
            return
        self.context("move_absolute %f %f\n" % (bbox[0], bbox[3]))
        self.drag_ready(True)

    def on_button_align_corner_br(self, event):  # wxGlade: Navigation.<event_handler>
        elements = self.context.elements
        elements.validate_selected_area()
        bbox = elements.selected_area()
        if bbox is None:
            return
        self.context("move_absolute %f %f\n" % (bbox[2], bbox[3]))
        self.drag_ready(True)

    def drag_relative(self, dx, dy):
        self.context("move_relative %d %d\ntranslate %d %d\n" % (dx, dy, dx, dy))

    def on_button_align_drag_down(self, event):  # wxGlade: Navigation.<event_handler>
        self.drag_relative(0, self.context.navigate_jog)

    def on_button_align_drag_right(self, event):  # wxGlade: Navigation.<event_handler>
        self.drag_relative(self.context.navigate_jog, 0)

    def on_button_align_drag_up(self, event):  # wxGlade: Navigation.<event_handler>
        self.drag_relative(0, -self.context.navigate_jog)

    def on_button_align_drag_left(self, event):  # wxGlade: Navigation.<event_handler>
        self.drag_relative(-self.context.navigate_jog, 0)

    def on_button_align_first_position(self, event):
        elements = self.context.elements
        e = list(elements.elems(emphasized=True))
        try:
            pos = e[0].first_point * e[0].transform
        except (IndexError, AttributeError):
            return
        if pos is None:
            return
        self.context("move_absolute %f %f\n" % (pos[0], pos[1]))
        self.drag_ready(True)

    def on_button_align_trace_hull(self, event):  # wxGlade: Navigation.<event_handler>
        self.context("trace_hull\n")

    def on_button_align_trace_quick(self, event):  # wxGlade: Navigation.<event_handler>
        self.context("trace_quick\n")
        self.drag_ready(True)


class MovePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.button_navigate_move_to = wx.BitmapButton(
            self, wx.ID_ANY, icons8_center_of_gravity_50.GetBitmap()
        )
        self.text_position_x = wx.TextCtrl(self, wx.ID_ANY, "0in")
        self.text_position_y = wx.TextCtrl(self, wx.ID_ANY, "0in")

        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_move_to, self.button_navigate_move_to
        )
        # end wxGlade
        self.bed_dim = context.root
        self.bed_dim.setting(int, "bed_width", 310)  # Default Value
        self.bed_dim.setting(int, "bed_height", 210)  # Default Value

    def __set_properties(self):
        # begin wxGlade: MovePanel.__set_properties
        self.button_navigate_move_to.SetToolTip("Move to the set position")
        self.button_navigate_move_to.SetSize(self.button_navigate_move_to.GetBestSize())
        self.text_position_x.SetToolTip("Set X value for the Move To")
        self.text_position_y.SetToolTip("Set Y value for the Move To")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MovePanel.__do_layout
        sizer_12 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Move To"), wx.HORIZONTAL
        )
        sizer_13 = wx.BoxSizer(wx.VERTICAL)
        sizer_15 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_14 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_12.Add(self.button_navigate_move_to, 0, 0, 0)
        label_9 = wx.StaticText(self, wx.ID_ANY, "X:")
        sizer_14.Add(label_9, 0, 0, 0)
        sizer_14.Add(self.text_position_x, 0, 0, 0)
        sizer_13.Add(sizer_14, 0, wx.EXPAND, 0)
        label_10 = wx.StaticText(self, wx.ID_ANY, "Y:")
        sizer_15.Add(label_10, 0, 0, 0)
        sizer_15.Add(self.text_position_y, 0, 0, 0)
        sizer_13.Add(sizer_15, 0, wx.EXPAND, 0)
        sizer_12.Add(sizer_13, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_12)
        sizer_12.Fit(self)
        self.Layout()
        # end wxGlade

    def on_button_navigate_move_to(self, event):  # wxGlade: Navigation.<event_handler>
        try:
            width = self.bed_dim.bed_width * MILS_IN_MM
            height = self.bed_dim.bed_height * MILS_IN_MM
            x = Length(self.text_position_x.GetValue()).value(
                ppi=1000.0, relative_length=width
            )
            y = Length(self.text_position_y.GetValue()).value(
                ppi=1000.0, relative_length=height
            )
            if x > width or y > height or x < 0 or y < 0:
                dlg = wx.MessageDialog(
                    None,
                    _("Cannot Move Outside Bed Dimensions"),
                    _("Error"),
                    wx.ICON_WARNING,
                )
                dlg.ShowModal()
                dlg.Destroy()
                return
            self.context("move %d %d\n" % (x, y))
        except ValueError:
            return
