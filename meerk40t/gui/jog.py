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


class Transform(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: Transform.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.button_scale_down = wx.BitmapButton(
            self, wx.ID_ANY, icons8_compress_50.GetBitmap()
        )
        self.button_translate_up = wx.BitmapButton(
            self, wx.ID_ANY, icons8_up_50.GetBitmap()
        )
        self.button_scale_up = wx.BitmapButton(
            self, wx.ID_ANY, icons8_enlarge_50.GetBitmap()
        )
        self.button_translate_left = wx.BitmapButton(
            self, wx.ID_ANY, icons8_left_50.GetBitmap()
        )
        self.button_reset = wx.BitmapButton(
            self, wx.ID_ANY, icons8_delete_50.GetBitmap()
        )
        self.button_translate_right = wx.BitmapButton(
            self, wx.ID_ANY, icons8_right_50.GetBitmap()
        )
        self.button_rotate_ccw = wx.BitmapButton(
            self, wx.ID_ANY, icons8_rotate_left_50.GetBitmap()
        )
        self.button_translate_down = wx.BitmapButton(
            self, wx.ID_ANY, icons8_down_50.GetBitmap()
        )
        self.button_rotate_cw = wx.BitmapButton(
            self, wx.ID_ANY, icons8_rotate_right_50.GetBitmap()
        )
        self.text_a = wx.TextCtrl(self, wx.ID_ANY, "1.000000")
        self.text_c = wx.TextCtrl(self, wx.ID_ANY, "0.000000")
        self.text_d = wx.TextCtrl(self, wx.ID_ANY, "1.000000")
        self.text_b = wx.TextCtrl(self, wx.ID_ANY, "0.000000")
        self.text_e = wx.TextCtrl(self, wx.ID_ANY, "0.000000")
        self.text_f = wx.TextCtrl(self, wx.ID_ANY, "0.000000")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_scale_down, self.button_scale_down)
        self.Bind(wx.EVT_BUTTON, self.on_translate_up, self.button_translate_up)
        self.Bind(wx.EVT_BUTTON, self.on_scale_up, self.button_scale_up)
        self.Bind(wx.EVT_BUTTON, self.on_translate_left, self.button_translate_left)
        self.Bind(wx.EVT_BUTTON, self.on_reset, self.button_reset)
        self.Bind(wx.EVT_BUTTON, self.on_translate_right, self.button_translate_right)
        self.Bind(wx.EVT_BUTTON, self.on_rotate_ccw, self.button_rotate_ccw)
        self.Bind(wx.EVT_BUTTON, self.on_translate_down, self.button_translate_down)
        self.Bind(wx.EVT_BUTTON, self.on_rotate_cw, self.button_rotate_cw)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_a)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_c)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_e)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_b)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_d)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_f)
        # end wxGlade
        self.select_ready(False)

    def __set_properties(self):
        # begin wxGlade: Transform.__set_properties
        self.button_scale_down.SetSize(self.button_scale_down.GetBestSize())
        self.button_translate_up.SetSize(self.button_translate_up.GetBestSize())
        self.button_scale_up.SetSize(self.button_scale_up.GetBestSize())
        self.button_translate_left.SetSize(self.button_translate_left.GetBestSize())
        self.button_reset.SetSize(self.button_reset.GetBestSize())
        self.button_translate_right.SetSize(self.button_translate_right.GetBestSize())
        self.button_rotate_ccw.SetSize(self.button_rotate_ccw.GetBestSize())
        self.button_translate_down.SetSize(self.button_translate_down.GetBestSize())
        self.button_rotate_cw.SetSize(self.button_rotate_cw.GetBestSize())

        self.button_scale_down.SetToolTip(_("Scale Down"))
        self.button_translate_up.SetToolTip(_("Translate Top"))
        self.button_scale_up.SetToolTip(_("Scale Up"))
        self.button_translate_left.SetToolTip(_("Translate Left"))
        self.button_reset.SetToolTip(_("Reset Matrix"))
        self.button_translate_right.SetToolTip(_("Translate Right"))
        self.button_rotate_ccw.SetToolTip(_("Rotate Counterclockwise"))
        self.button_translate_down.SetToolTip(_("Translate Bottom"))
        self.button_rotate_cw.SetToolTip(_("Rotate Clockwise"))
        self.text_a.SetMinSize((60, 23))
        self.text_a.SetToolTip("Transform: Scale X")
        self.text_c.SetMinSize((60, 23))
        self.text_c.SetToolTip("Transform: Skew Y")
        self.text_e.SetMinSize((60, 23))
        self.text_e.SetToolTip("Transform: Translate X")
        self.text_b.SetMinSize((60, 23))
        self.text_b.SetToolTip("Transform: Skew X")
        self.text_d.SetMinSize((60, 23))
        self.text_d.SetToolTip("Transform: Scale Y")
        self.text_f.SetMinSize((60, 23))
        self.text_f.SetToolTip("Transform: Translate Y")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Transform.__do_layout
        matrix_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_17 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        grid_sizer_2 = wx.FlexGridSizer(3, 3, 0, 0)
        grid_sizer_2.Add(self.button_scale_down, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_up, 0, 0, 0)
        grid_sizer_2.Add(self.button_scale_up, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_left, 0, 0, 0)
        grid_sizer_2.Add(self.button_reset, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_right, 0, 0, 0)
        grid_sizer_2.Add(self.button_rotate_ccw, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_down, 0, 0, 0)
        grid_sizer_2.Add(self.button_rotate_cw, 0, 0, 0)
        matrix_sizer.Add(grid_sizer_2, 0, wx.EXPAND, 0)
        sizer_2.Add(self.text_a, 0, 0, 0)
        sizer_2.Add(self.text_c, 0, 0, 0)
        sizer_17.Add(sizer_2, 1, wx.EXPAND, 0)
        sizer_3.Add(self.text_e, 0, 0, 0)
        sizer_3.Add(self.text_b, 0, 0, 0)
        sizer_17.Add(sizer_3, 1, wx.EXPAND, 0)
        sizer_4.Add(self.text_d, 0, 0, 0)
        sizer_4.Add(self.text_f, 0, 0, 0)
        sizer_17.Add(sizer_4, 1, wx.EXPAND, 0)
        matrix_sizer.Add(sizer_17, 1, wx.EXPAND, 0)
        self.SetSizer(matrix_sizer)
        matrix_sizer.Fit(self)
        self.Layout()
        # end wxGlade

    def initialize(self, *args):
        self.context.listen("emphasized", self.on_emphasized_elements_changed)
        self.update_matrix_text()

    def finalize(self, *args):
        self.context.unlisten("emphasized", self.on_emphasized_elements_changed)

    def on_emphasized_elements_changed(self, origin, elements):
        self.select_ready(self.context.elements.has_emphasis())
        self.update_matrix_text()

    def update_matrix_text(self):
        f = self.context.elements.first_element(emphasized=True)
        v = f is not None
        self.text_a.Enable(v)
        self.text_b.Enable(v)
        self.text_c.Enable(v)
        self.text_d.Enable(v)
        self.text_e.Enable(v)
        self.text_f.Enable(v)
        if v:
            matrix = f.transform
            self.text_a.SetValue(str(matrix.a))
            self.text_b.SetValue(str(matrix.b))
            self.text_c.SetValue(str(matrix.c))
            self.text_d.SetValue(str(matrix.d))
            self.text_e.SetValue(str(matrix.e))
            self.text_f.SetValue(str(matrix.f))

    def select_ready(self, v):
        """
        Enables the relevant buttons when there is a selection in the elements.
        :param v: whether selection is currently drag ready.
        :return:
        """
        self.button_scale_down.Enable(v)
        self.button_scale_up.Enable(v)
        self.button_rotate_ccw.Enable(v)
        self.button_rotate_cw.Enable(v)
        self.button_translate_down.Enable(v)
        self.button_translate_up.Enable(v)
        self.button_translate_left.Enable(v)
        self.button_translate_right.Enable(v)
        self.button_reset.Enable(v)

    def matrix_updated(self):
        self.context.signal("refresh_scene")
        self.update_matrix_text()

    def on_scale_down(self, event):  # wxGlade: Navigation.<event_handler>
        scale = 19.0 / 20.0
        spooler, input_driver, output = self.context.registered[
            "device/%s" % self.context.root.active
        ]
        self.context(
            "scale %f %f %f %f\n"
            % (
                scale,
                scale,
                input_driver.current_x,
                input_driver.current_y,
            )
        )
        self.matrix_updated()

    def on_scale_up(self, event):  # wxGlade: Navigation.<event_handler>
        scale = 20.0 / 19.0
        spooler, input_driver, output = self.context.registered[
            "device/%s" % self.context.root.active
        ]
        self.context(
            "scale %f %f %f %f\n"
            % (
                scale,
                scale,
                input_driver.current_x,
                input_driver.current_y,
            )
        )
        self.matrix_updated()

    def on_translate_up(self, event):  # wxGlade: Navigation.<event_handler>
        dx = 0
        dy = -self.context.navigate_jog
        self.context("translate %f %f\n" % (dx, dy))
        self.matrix_updated()

    def on_translate_left(self, event):  # wxGlade: Navigation.<event_handler>
        dx = -self.context.navigate_jog
        dy = 0
        self.context("translate %f %f\n" % (dx, dy))
        self.matrix_updated()

    def on_translate_right(self, event):  # wxGlade: Navigation.<event_handler>
        dx = self.context.navigate_jog
        dy = 0
        self.context("translate %f %f\n" % (dx, dy))
        self.matrix_updated()

    def on_translate_down(self, event):  # wxGlade: Navigation.<event_handler>
        dx = 0
        dy = self.context.navigate_jog
        self.context("translate %f %f\n" % (dx, dy))
        self.matrix_updated()

    def on_reset(self, event):  # wxGlade: Navigation.<event_handler>
        self.context("reset\n")
        self.matrix_updated()

    def on_rotate_ccw(self, event):  # wxGlade: Navigation.<event_handler>
        spooler, input_driver, output = self.context.registered[
            "device/%s" % self.context.root.active
        ]
        self.context(
            "rotate %fdeg %f %f\n"
            % (-5, input_driver.current_x, input_driver.current_y)
        )
        self.matrix_updated()

    def on_rotate_cw(self, event):  # wxGlade: Navigation.<event_handler>
        spooler, input_driver, output = self.context.registered[
            "device/%s" % self.context.root.active
        ]
        self.context(
            "rotate %fdeg %f %f\n" % (5, input_driver.current_x, input_driver.current_y)
        )
        self.matrix_updated()

    def on_text_matrix(self, event):  # wxGlade: Navigation.<event_handler>
        try:
            self.context(
                "matrix %f %f %f %f %s %s\n"
                % (
                    float(self.text_a.GetValue()),
                    float(self.text_b.GetValue()),
                    float(self.text_c.GetValue()),
                    float(self.text_d.GetValue()),
                    self.text_e.GetValue(),
                    self.text_f.GetValue(),
                )
            )
        except ValueError:
            self.update_matrix_text()
        self.context.signal("refresh_scene")


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


class JogDistancePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: JogDistancePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.spin_jog_mils = wx.SpinCtrlDouble(self, wx.ID_ANY, "100.0", min=0.0, max=10000.0)
        self.spin_jog_mm = wx.SpinCtrlDouble(self, wx.ID_ANY, "10.0", min=0.0, max=254.0)
        self.spin_jog_cm = wx.SpinCtrlDouble(self, wx.ID_ANY, "1.0", min=0.0, max=25.4)
        self.spin_jog_inch = wx.SpinCtrlDouble(self, wx.ID_ANY, "0.394", min=0.0, max=10.0)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_jog_distance, self.spin_jog_mils)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_jog_distance, self.spin_jog_mils)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_jog_distance, self.spin_jog_mm)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_jog_distance, self.spin_jog_mm)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_jog_distance, self.spin_jog_cm)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_jog_distance, self.spin_jog_cm)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_jog_distance, self.spin_jog_inch)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_jog_distance, self.spin_jog_inch)
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: JogDistancePanel.__set_properties
        self.spin_jog_mils.SetMinSize((80, 23))
        self.spin_jog_mils.SetToolTip(
            _("Set Jog Distance in mils (1/1000th of an inch)")
        )
        self.spin_jog_mm.SetMinSize((80, 23))
        self.spin_jog_mm.SetToolTip(_("Set Jog Distance in mm"))
        self.spin_jog_cm.SetMinSize((80, 23))
        self.spin_jog_cm.SetToolTip(_("Set Jog Distance in cm"))
        self.spin_jog_inch.SetMinSize((80, 23))
        self.spin_jog_inch.SetToolTip(_("Set Jog Distance in inch"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: JogDistancePanel.__do_layout
        sizer_6 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Jog Distance")), wx.HORIZONTAL
        )
        sizer_10 = wx.BoxSizer(wx.VERTICAL)
        sizer_9 = wx.BoxSizer(wx.VERTICAL)
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_7 = wx.BoxSizer(wx.VERTICAL)
        sizer_7.Add(self.spin_jog_mils, 0, 0, 0)
        label_5 = wx.StaticText(self, wx.ID_ANY, _("mils"))
        sizer_7.Add(label_5, 0, 0, 0)
        sizer_6.Add(sizer_7, 0, wx.EXPAND, 0)
        sizer_8.Add(self.spin_jog_mm, 0, 0, 0)
        label_6 = wx.StaticText(self, wx.ID_ANY, _(" mm"))
        sizer_8.Add(label_6, 0, 0, 0)
        sizer_6.Add(sizer_8, 0, wx.EXPAND, 0)
        sizer_9.Add(self.spin_jog_cm, 0, 0, 0)
        label_7 = wx.StaticText(self, wx.ID_ANY, _("cm"))
        sizer_9.Add(label_7, 0, 0, 0)
        sizer_6.Add(sizer_9, 0, wx.EXPAND, 0)
        sizer_10.Add(self.spin_jog_inch, 0, 0, 0)
        label_8 = wx.StaticText(self, wx.ID_ANY, _("inch"))
        sizer_10.Add(label_8, 0, 0, 0)
        sizer_6.Add(sizer_10, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_6)
        sizer_6.Fit(self)
        self.Layout()
        # end wxGlade

    def initialize(self, *args):
        self.set_jog_distances(self.context.navigate_jog)

    def set_jog_distances(self, jog_mils):
        self.spin_jog_mils.SetValue(jog_mils)
        self.spin_jog_mm.SetValue(jog_mils / MILS_IN_MM)
        self.spin_jog_cm.SetValue(jog_mils / (MILS_IN_MM * 10.0))
        self.spin_jog_inch.SetValue(jog_mils / 1000.0)

    def on_spin_jog_distance(self, event):  # wxGlade: Navigation.<event_handler>
        if event.Id == self.spin_jog_mils.Id:
            self.context.navigate_jog = float(self.spin_jog_mils.GetValue())
        elif event.Id == self.spin_jog_mm.Id:
            self.context.navigate_jog = float(self.spin_jog_mm.GetValue() * MILS_IN_MM)
        elif event.Id == self.spin_jog_cm.Id:
            self.context.navigate_jog = float(
                self.spin_jog_cm.GetValue() * MILS_IN_MM * 10.0
            )
        else:
            self.context.navigate_jog = float(self.spin_jog_inch.GetValue() * 1000.0)
        self.set_jog_distances(int(self.context.navigate_jog))


class PulsePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PulsePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.button_navigate_pulse = wx.BitmapButton(
            self, wx.ID_ANY, icons8_laser_beam_52.GetBitmap()
        )
        self.spin_pulse_duration = wx.SpinCtrl(self, wx.ID_ANY, "50", min=1, max=1000)
        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_pulse, self.button_navigate_pulse
        )
        self.Bind(
            wx.EVT_SPINCTRL, self.on_spin_pulse_duration, self.spin_pulse_duration
        )
        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_spin_pulse_duration, self.spin_pulse_duration
        )
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: PulsePanel.__set_properties
        self.button_navigate_pulse.SetToolTip("Fire a short laser pulse")
        self.button_navigate_pulse.SetSize(self.button_navigate_pulse.GetBestSize())
        self.spin_pulse_duration.SetMinSize((80, 23))
        self.spin_pulse_duration.SetToolTip("Set the duration of the laser pulse")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: PulsePanel.__do_layout
        sizer_5 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Short Pulse"), wx.HORIZONTAL)
        sizer_5.Add(self.button_navigate_pulse, 0, 0, 0)
        sizer_5.Add(self.spin_pulse_duration, 0, 0, 0)
        label_4 = wx.StaticText(self, wx.ID_ANY, " ms")
        sizer_5.Add(label_4, 0, 0, 0)
        self.SetSizer(sizer_5)
        sizer_5.Fit(self)
        self.Layout()
        # end wxGlade

    def on_button_navigate_pulse(self, event):  # wxGlade: Navigation.<event_handler>
        value = self.spin_pulse_duration.GetValue()
        self.context("pulse %f\n" % value)

    def on_spin_pulse_duration(self, event):  # wxGlade: Navigation.<event_handler>
        self.context.navigate_pulse = float(self.spin_pulse_duration.GetValue())


class NotePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: NotePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.check_auto_open_notes = wx.CheckBox(
            self, wx.ID_ANY, _("Automatically Open Notes")
        )
        self.text_notes = wx.TextCtrl(
            self,
            wx.ID_ANY,
            "",
            style=wx.TE_BESTWRAP | wx.TE_MULTILINE | wx.TE_WORDWRAP | wx.TE_RICH,
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_auto_note_open, self.check_auto_open_notes
        )
        self.Bind(wx.EVT_TEXT, self.on_text_notes, self.text_notes)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_notes, self.text_notes)
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: NotePanel.__set_properties
        self.check_auto_open_notes.SetToolTip(
            _("Automatically open notes if they exist when file is opened.")
        )
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: NotePanel.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(self.check_auto_open_notes, 0, 0, 0)
        sizer_1.Add(self.text_notes, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()
        # end wxGlade

    def initialize(self, *args):
        self.context.setting(bool, "auto_note", True)
        self.check_auto_open_notes.SetValue(self.context.auto_note)
        if self.context.elements.note is not None:
            self.text_notes.SetValue(self.context.elements.note)

    def on_check_auto_note_open(self, event):  # wxGlade: Notes.<event_handler>
        self.context.auto_note = self.check_auto_open_notes.GetValue()

    def on_text_notes(self, event):  # wxGlade: Notes.<event_handler>
        if len(self.text_notes.GetValue()) == 0:
            self.context.elements.note = None
        else:
            self.context.elements.note = self.text_notes.GetValue()


class SpoolerPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: SpoolerPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.available_devices = [
            self.context.registered[i] for i in self.context.match("device")
        ]
        selected_spooler = self.context.root.active
        spools = [str(i) for i in self.context.match("device", suffix=True)]
        index = spools.index(selected_spooler)
        self.connected_name = spools[index]
        self.connected_spooler, self.connected_driver, self.connected_output = (
            None,
            None,
            None,
        )
        try:
            (
                self.connected_spooler,
                self.connected_driver,
                self.connected_output,
            ) = self.available_devices[index]
        except IndexError:
            for m in self.Children:
                if isinstance(m, wx.Window):
                    m.Disable()
        spools = [" -> ".join(map(repr, ad)) for ad in self.available_devices]
        self.combo_device = wx.ComboBox(
            self, wx.ID_ANY, choices=spools, style=wx.CB_DROPDOWN
        )
        self.combo_device.SetSelection(index)

        self.list_job_spool = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_COMBOBOX, self.on_combo_device, self.combo_device)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.on_list_drag, self.list_job_spool)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_rightclick, self.list_job_spool)
        # end wxGlade
        self.dirty = False
        self.update_buffer_size = False
        self.update_spooler_state = False
        self.update_spooler = True

        self.elements_progress = 0
        self.elements_progress_total = 0
        self.command_index = 0
        self.listener_list = None
        self.list_lookup = {}

    def __set_properties(self):
        # begin wxGlade: SpoolerPanel.__set_properties
        self.combo_device.SetToolTip("Select the device")
        self.list_job_spool.SetToolTip("List and modify the queued operations")
        self.list_job_spool.AppendColumn("#", format=wx.LIST_FORMAT_LEFT, width=78)
        self.list_job_spool.AppendColumn("Name", format=wx.LIST_FORMAT_LEFT, width=143)
        self.list_job_spool.AppendColumn("Status", format=wx.LIST_FORMAT_LEFT, width=73)
        self.list_job_spool.AppendColumn("Type", format=wx.LIST_FORMAT_LEFT, width=53)
        self.list_job_spool.AppendColumn("Speed", format=wx.LIST_FORMAT_LEFT, width=83)
        self.list_job_spool.AppendColumn("Settings", format=wx.LIST_FORMAT_LEFT, width=223)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: SpoolerPanel.__do_layout
        sizer_frame = wx.BoxSizer(wx.VERTICAL)
        sizer_frame.Add(self.combo_device, 0, wx.EXPAND, 0)
        sizer_frame.Add(self.list_job_spool, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_frame)
        sizer_frame.Fit(self)
        self.Layout()
        # end wxGlade

    def on_combo_device(self, event):  # wxGlade: Spooler.<event_handler>
        self.available_devices = [
            self.context.registered[i] for i in self.context.match("device")
        ]
        index = self.combo_device.GetSelection()
        (
            self.connected_spooler,
            self.connected_driver,
            self.connected_output,
        ) = self.available_devices[index]
        self.update_spooler = True
        self.refresh_spooler_list()

    def on_list_drag(self, event):  # wxGlade: JobSpooler.<event_handler>
        event.Skip()

    def on_item_rightclick(self, event):  # wxGlade: JobSpooler.<event_handler>
        index = event.Index
        spooler = self.connected_spooler
        try:
            element = spooler._queue[index]
        except IndexError:
            return
        menu = wx.Menu()
        convert = menu.Append(
            wx.ID_ANY, _("Remove %s") % str(element)[:16], "", wx.ITEM_NORMAL
        )
        self.Bind(wx.EVT_MENU, self.on_tree_popup_delete(element), convert)
        convert = menu.Append(wx.ID_ANY, _("Clear All"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_tree_popup_clear(element), convert)
        self.PopupMenu(menu)
        menu.Destroy()

    def initialize(self, *args):
        self.context.listen("spooler;queue", self.on_spooler_update)
        self.refresh_spooler_list()

    def finalize(self, *args):
        self.context.unlisten("spooler;queue", self.on_spooler_update)

    def refresh_spooler_list(self):
        if not self.update_spooler:
            return
        if not self.connected_spooler:
            return

        def name_str(e):
            try:
                return e.__name__
            except AttributeError:
                return str(e)

        try:
            self.list_job_spool.DeleteAllItems()
        except RuntimeError:
            return

        spooler = self.connected_spooler
        if len(spooler._queue) > 0:
            # This should actually process and update the queue items.
            for i, e in enumerate(spooler._queue):
                m = self.list_job_spool.InsertItem(i, "#%d" % i)
                if m != -1:
                    self.list_job_spool.SetItem(m, 1, name_str(e))
                    try:
                        self.list_job_spool.SetItem(m, 2, e._status_value)
                    except AttributeError:
                        pass
                    try:
                        self.list_job_spool.SetItem(m, 3, e.operation)
                    except AttributeError:
                        pass
                    try:
                        self.list_job_spool.SetItem(m, 4, _("%.1fmm/s") % (e.speed))
                    except AttributeError:
                        pass
                    settings = list()
                    try:
                        settings.append(_("power=%g") % (e.power))
                    except AttributeError:
                        pass
                    try:
                        settings.append(_("step=%d") % (e.raster_step))
                    except AttributeError:
                        pass
                    try:
                        settings.append(_("overscan=%d") % (e.overscan))
                    except AttributeError:
                        pass
                    self.list_job_spool.SetItem(m, 5, " ".join(settings))

    def on_tree_popup_clear(self, element):
        def delete(event):
            spooler = self.connected_spooler
            spooler.clear_queue()
            self.refresh_spooler_list()

        return delete

    def on_tree_popup_delete(self, element):
        def delete(event):
            spooler = self.connected_spooler
            spooler.remove(element)
            self.refresh_spooler_list()

        return delete

    def on_spooler_update(self, origin, value, *args, **kwargs):
        self.update_spooler = True
        self.refresh_spooler_list()


class ConsolePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConsolePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.text_main = wx.TextCtrl(
            self,
            wx.ID_ANY,
            "",
            style=wx.TE_BESTWRAP
                  | wx.TE_MULTILINE
                  | wx.TE_READONLY
                  | wx.TE_RICH2
                  | wx.TE_AUTO_URL,
        )
        self.text_main.SetFont(
            wx.Font(
                10, wx.FONTFAMILY_TELETYPE, wx.NORMAL, wx.NORMAL, faceName="Monospace"
            )
        )
        self.text_entry = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER | wx.TE_PROCESS_TAB
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down, self.text_entry)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_entry, self.text_entry)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down_main, self.text_main)
        self.Bind(wx.EVT_TEXT_URL, self.on_text_uri)
        # end wxGlade
        self.command_log = []
        self.command_position = 0

    def __set_properties(self):
        # begin wxGlade: ConsolePanel.__set_properties
        self.text_entry.SetFocus()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ConsolePanel.__do_layout
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.text_main, 20, wx.EXPAND, 0)
        sizer_2.Add(self.text_entry, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_2)
        sizer_2.Fit(self)
        self.Layout()
        # end wxGlade

    def initialize(self, *args):
        self.context.channel("console").watch(self.update_text)

    def finalize(self, *args):
        self.context.channel("console").unwatch(self.update_text)

    def update_text(self, text):
        if not wx.IsMainThread():
            wx.CallAfter(self.update_text_gui, str(text) + "\n")
        else:
            self.update_text_gui(str(text) + "\n")

    def update_text_gui(self, text):
        try:
            self.text_main.AppendText(text)
        except RuntimeError:
            pass

    def on_text_uri(self, event):
        mouseEvent = event.GetMouseEvent()
        if mouseEvent.LeftDClick():
            urlStart = event.GetURLStart()
            urlEnd = event.GetURLEnd()
            url = self.text_main.GetRange(urlStart, urlEnd)
            import webbrowser

            webbrowser.open_new_tab(url)

    def on_key_down_main(self, event):
        key = event.GetKeyCode()
        if key != wx.WXK_CONTROL and (key != ord("C") or not event.ControlDown()):
            if self.FindFocus() is not self.text_entry:
                self.text_entry.SetFocus()
                self.text_entry.AppendText(str(chr(key)).lower())
        event.Skip()

    def on_key_down(self, event):
        key = event.GetKeyCode()
        try:
            if key == wx.WXK_DOWN:
                self.text_entry.SetValue(self.command_log[self.command_position + 1])
                if not wx.IsMainThread():
                    wx.CallAfter(self.text_entry.SetInsertionPointEnd)
                else:
                    self.text_entry.SetInsertionPointEnd()
                self.command_position += 1
            elif key == wx.WXK_UP:
                self.text_entry.SetValue(self.command_log[self.command_position - 1])
                if not wx.IsMainThread():
                    wx.CallAfter(self.text_entry.SetInsertionPointEnd)
                else:
                    self.text_entry.SetInsertionPointEnd()
                self.command_position -= 1
            else:
                event.Skip()
        except IndexError:
            pass

    def on_entry(self, event):  # wxGlade: Terminal.<event_handler>
        command = self.text_entry.GetValue()
        self.context(command + "\n")
        self.text_entry.SetValue("")
        self.command_log.append(command)
        self.command_position = 0
        event.Skip(False)


class DevicesPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: DevicesPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.devices_list = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.on_list_drag, self.devices_list)
        self.Bind(
            wx.EVT_LIST_ITEM_ACTIVATED, self.on_list_item_activated, self.devices_list
        )
        self.Bind(
            wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_list_right_click, self.devices_list
        )
        self.Bind(
            wx.EVT_LIST_ITEM_SELECTED, self.on_list_item_selected, self.devices_list
        )
        self.Bind(
            wx.EVT_LIST_ITEM_DESELECTED, self.on_list_item_selected, self.devices_list
        )
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: DevicesPanel.__set_properties
        self.devices_list.SetFont(
            wx.Font(
                13,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        self.devices_list.AppendColumn("Index", format=wx.LIST_FORMAT_LEFT, width=56)
        self.devices_list.AppendColumn("Spooler", format=wx.LIST_FORMAT_LEFT, width=74)
        self.devices_list.AppendColumn(
            "Driver/Input", format=wx.LIST_FORMAT_LEFT, width=170
        )
        self.devices_list.AppendColumn("Output", format=wx.LIST_FORMAT_LEFT, width=170)
        self.devices_list.AppendColumn(
            "Registered", format=wx.LIST_FORMAT_LEFT, width=93
        )
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: DevicesPanel.__do_layout
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.Add(self.devices_list, 0, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()
        # end wxGlade

    def initialize(self, *args):
        self.refresh_device_list()

    def finalize(self, *args):
        item = self.devices_list.GetFirstSelected()
        if item != -1:
            uid = self.devices_list.GetItem(item).Text
            self.context.device_primary = uid

    def refresh_device_list(self):
        self.devices_list.DeleteAllItems()
        for i, dev in enumerate(self.context.match("device")):
            device = self.context.registered[dev]
            spooler, input_driver, output = device
            device_context = self.context.get_context("devices")
            dev_string = "device_%d" % i
            if hasattr(device_context, dev_string):
                line = getattr(device_context, dev_string)
                registered = len(line) > 0
            else:
                registered = False
            m = self.devices_list.InsertItem(i, str(i))
            if self.context.active == str(m):
                self.devices_list.SetItemBackgroundColour(m, wx.LIGHT_GREY)

            if m != -1:
                spooler_name = spooler.name if spooler is not None else "None"
                self.devices_list.SetItem(m, 1, str(spooler_name))
                self.devices_list.SetItem(m, 2, str(input_driver))
                self.devices_list.SetItem(m, 3, str(output))
                self.devices_list.SetItem(m, 4, str(registered))

    def on_list_drag(self, event):  # wxGlade: DeviceManager.<event_handler>
        pass

    def on_list_right_click(self, event):  # wxGlade: DeviceManager.<event_handler>
        uid = event.GetLabel()
        self.refresh_device_list()

    def on_list_item_selected(self, event=None):
        item = self.devices_list.GetFirstSelected()

    def on_list_item_activated(
        self, event=None
    ):  # wxGlade: DeviceManager.<event_handler>
        item = self.devices_list.GetFirstSelected()
        if item == -1:
            return
        uid = self.devices_list.GetItem(item).Text
        self.context("device activate %s\n" % uid)
        self.refresh_device_list()

