import wx


from meerk40t.gui.icons import (
    icon_corner1,
    icon_corner2,
    icon_corner3,
    icon_corner4,
    icons8_down,
    icons8_left,
    icons8_level_1_50,
    icons8_pentagon_50,
    icons8_pentagon_square_50,
    icons8_right,
    icons8_square_border_50,
    icons8up,
)

_ = wx.GetTranslation


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

        self.Bind(
            wx.EVT_BUTTON,
            self.on_button_align_corner_tl,
            self.button_align_corner_top_left,
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_align_drag_up, self.button_align_drag_up
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_button_align_corner_tr,
            self.button_align_corner_top_right,
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_align_drag_left, self.button_align_drag_left
        )
        self.Bind(wx.EVT_BUTTON, self.on_button_align_center, self.button_align_center)
        self.Bind(
            wx.EVT_BUTTON, self.on_button_align_drag_right, self.button_align_drag_right
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_button_align_corner_bl,
            self.button_align_corner_bottom_left,
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_align_drag_down, self.button_align_drag_down
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_button_align_corner_br,
            self.button_align_corner_bottom_right,
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_align_trace_hull, self.button_align_trace_hull
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_button_align_trace_quick,
            self.button_align_trace_quick,
        )
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
