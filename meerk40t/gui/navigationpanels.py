import platform
from math import isinf
from time import time

import wx
from wx import aui

from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_PIXEL, Angle, Length
from meerk40t.gui.icons import (
    EmptyIcon,
    get_default_icon_size,
    icon_circled_1,
    icon_corner1,
    icon_corner2,
    icon_corner3,
    icon_corner4,
    icon_fence_closed,
    icon_fence_open,
    icon_z_down,
    icon_z_down_double,
    icon_z_down_triple,
    icon_z_home,
    icon_z_up,
    icon_z_up_double,
    icon_z_up_triple,
    icons8_caret_down,
    icons8_caret_left,
    icons8_caret_right,
    icons8_caret_up,
    icons8_center_of_gravity,
    icons8_compress,
    icons8_delete,
    icons8_down,
    icons8_down_left,
    icons8_down_right,
    icons8_enlarge,
    icons8_home_filled,
    icons8_laser_beam,
    icons8_left,
    icons8_lock,
    icons8_move,
    icons8_pentagon,
    icons8_pentagon_squared,
    icons8_right,
    icons8_rotate_left,
    icons8_rotate_right,
    icons8_square_border,
    icons8_unlock,
    icons8_up,
    icons8_up_left,
    icons8_up_right,
)
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.position import PositionPanel
from meerk40t.gui.wxutils import (
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    wxBitmapButton,
    wxStaticBitmap,
    wxStaticText,
)
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


def register_panel_navigation(window, context):
    dragpanel = Drag(window, wx.ID_ANY, context=context)
    iconsize = get_default_icon_size(context)
    if platform.system() == "Windows":
        dx = 24
        dy = 30
    else:
        dx = 12
        dy = 12
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .MinSize(3 * iconsize + dx, 3 * iconsize + dy)
        .BestSize(3 * iconsize + dx, 3 * iconsize + dy)
        .FloatingSize(3 * iconsize + dx, 3 * iconsize + dy)
        .MaxSize(300, 300)
        .Caption(_("Drag"))
        .Name("drag")
        .CaptionVisible(not context.pane_lock)
        .Hide()
    )
    pane.dock_proportion = 3 * iconsize + dx
    pane.control = dragpanel

    def on_drag_resize(event):
        panelsize = event.GetSize()
        dragpanel.set_icons(dimension=panelsize)

    dragpanel.Bind(wx.EVT_SIZE, on_drag_resize)
    pane.submenu = "_20_" + _("Navigation")
    pane.helptext = _("Align and drag laserhead around to be burned elements")

    window.on_pane_create(pane)
    context.register("pane/drag", pane)
    jogpanel = Jog(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .MinSize(3 * iconsize + dx, 3 * iconsize + dy)
        .BestSize(3 * iconsize + dx, 3 * iconsize + dy)
        .FloatingSize(3 * iconsize + dx, 3 * iconsize + dy)
        .MaxSize(300, 300)
        .Caption(_("Jog"))
        .Name("jog")
        .Hide()
        .CaptionVisible(not context.pane_lock)
    )
    pane.dock_proportion = 3 * iconsize + dx
    pane.control = jogpanel

    def on_jog_resize(event):
        panelsize = event.GetSize()
        jogpanel.set_icons(dimension=panelsize)

    jogpanel.Bind(wx.EVT_SIZE, on_jog_resize)
    pane.submenu = "_20_" + _("Navigation")
    pane.helptext = _("Display laser jogging controls")

    window.on_pane_create(pane)
    context.register("pane/jog", pane)

    panel = MovePanel(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .MinSize(iconsize + 100, iconsize + 25)
        .BestSize(iconsize + 100, iconsize + 25)
        .FloatingSize(iconsize + 100, iconsize + 25)
        .MaxSize(200, 100)
        .Caption(_("Move"))
        .CaptionVisible(not context.pane_lock)
        .Name("move")
        .Hide()
    )
    pane.dock_proportion = iconsize + 100
    pane.control = panel
    pane.submenu = "_20_" + _("Navigation")
    pane.helptext = _("Display laser/element movement/dragging controls")

    window.on_pane_create(pane)
    context.register("pane/move", pane)

    panel = PulsePanel(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .MinSize(iconsize + 25, iconsize + 25)
        .FloatingSize(iconsize + 60, iconsize + 25)
        .Hide()
        .Caption(_("Pulse"))
        .CaptionVisible(not context.pane_lock)
        .Name("pulse")
    )
    pane.dock_proportion = iconsize + 60
    pane.control = panel
    pane.submenu = "_20_" + _("Navigation")
    pane.helptext = _("Display laser pulse panel")

    window.on_pane_create(pane)
    context.register("pane/pulse", pane)

    # panel = PositionPanel(window, wx.ID_ANY, context=context, small=False)
    # pane = (
    #     aui.AuiPaneInfo()
    #     .Right()
    #     .MinSize(75, 50)
    #     .FloatingSize(150, 75)
    #     .Hide()
    #     .Caption(_("Element-Size"))
    #     .CaptionVisible(not context.pane_lock)
    #     .Name("objsizer")
    # )
    # pane.dock_proportion = 150
    # pane.control = panel
    # pane.submenu = "_40_" + _("Editing")

    # window.on_pane_create(pane)
    # context.register("pane/objsizer", pane)

    if platform.system() == "Windows":
        dx = 24
        dy = 30
    else:
        dx = 12
        dy = 12
    panel = Transform(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .MinSize(max(3 * iconsize, 3 * 57), 3 * iconsize + dy)
        .FloatingSize(max(3 * iconsize, 3 * 57), 3 * iconsize + dy)
        .MaxSize(300, 300)
        .Caption(_("Transform"))
        .Name("transform")
        .CaptionVisible(not context.pane_lock)
        .Hide()
    )
    pane.dock_proportion = max(3 * iconsize, 3 * 57)
    pane.control = panel
    pane.submenu = "_40_" + _("Editing")
    pane.helptext = _("Display element transformation panel")

    window.on_pane_create(pane)
    context.register("pane/transform", pane)

    panel = JogDistancePanel(window, wx.ID_ANY, context=context, pane=True)
    pane = (
        aui.AuiPaneInfo()
        .Float()
        .MinSize(190, 110)
        .FloatingSize(190, 110)
        .Hide()
        .Caption(_("Distances"))
        .CaptionVisible(not context.pane_lock)
        .Name("jogdist")
    )
    pane.dock_proportion = 110
    pane.control = panel
    pane.submenu = "_20_" + _("Navigation")
    pane.helptext = _("Edit default jog distance")

    window.on_pane_create(pane)
    context.register("pane/jogdist", pane)


def get_movement(context, dx, dy):
    device = context.device
    _confined = context.confined

    try:
        current_x, current_y = device.current
    except AttributeError:
        return dx, dy

    if not _confined:
        return dx, dy

    newx = float(Length(dx))
    newy = float(Length(dy))
    min_x = 0
    max_x = float(Length(device.view.width))
    min_y = 0
    max_y = float(Length(device.view.height))
    # print ("Delta:", newx, newy)
    # print ("Current:", current_x, current_y)
    if newx + current_x > max_x:
        tmp = max_x - current_x
        if newx != 0:
            newy = newy * tmp / newx
        newx = tmp
    elif newx + current_x < min_x:
        tmp = -1 * current_x
        if newx != 0:
            newy = newy * tmp / newx
        newx = tmp
    if newy + current_y > max_y:
        tmp = max_y - current_y
        if newy != 0:
            newx = newx * tmp / newy
        newy = tmp
    elif newy + current_y < min_y:
        tmp = -1 * current_y
        if newy != 0:
            newx = newx * tmp / newy
        newy = tmp
    sx = Length(newx)
    sy = Length(newy)
    nx = f"{sx.mm:.4f}mm"
    ny = f"{sy.mm:.4f}mm"
    return nx, ny


class TimerButtons:
    """TimerButtons - User interface panel for laser cutting operations"""

    def __init__(self, *args, interval=0.5, accelerate=True, **kwds):
        self.parent = args[0]
        self.timer = wx.Timer(self.parent, wx.ID_ANY)
        self.timer_buttons = dict()
        self._interval = 0
        self.interval = interval
        self.accelerate = accelerate
        self.timer_execution = None
        self.timer_delta = 1.0
        self.timer_looped = 0
        self.active_button = None
        self.parent.Bind(wx.EVT_TIMER, self.timer_event, self.timer)

    @property
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, value):
        self._interval = value

    def add_button(self, button, routine):
        _id = button.GetId()
        self.timer_buttons[_id] = (button, routine)
        button.Bind(wx.EVT_LEFT_DOWN, self.on_button_down)
        button.Bind(wx.EVT_LEFT_UP, self.on_button_up)
        button.Bind(wx.EVT_LEAVE_WINDOW, self.on_button_lost)
        button.Bind(wx.EVT_BUTTON, self.on_button_click)

    def execute(self, button):
        if button is None:
            return
        _id = button.GetId()
        if _id not in self.timer_buttons:
            return
        action = self.timer_buttons[_id][1]
        if action is None:
            return
        action()

    def timer_event(self, event):
        if self.active_button is None:
            return
        self.execute(self.active_button)
        self.timer_execution = time()
        self.timer_looped += 1
        if self.timer_looped == 5 and self.accelerate:
            self.timer.Stop()
            if self.interval > 0:
                self.timer.Start(int(self.interval * 500))
        elif self.timer_looped == 10 and self.accelerate:
            self.timer.Stop()
            if self.interval > 0:
                self.timer.Start(int(self.interval * 250))

    def stop_timer(self, action):
        self.timer.Stop()
        t = time()
        if self.active_button is not None and (
            self.timer_execution is None
            or t - self.timer_execution > self.interval * 500
        ):
            self.execute(self.active_button)
        # self.timer_execution = None
        self.timer_looped = 0
        self.active_button = None

    def start_timer(self, button=None):
        self.stop_timer(action=False)
        self.active_button = button
        self.timer_execution = None
        if self.active_button is not None:
            if self.interval > 0:
                self.timer.Start(int(self.interval * 1000))

    def on_button_lost(self, event=None):
        self.stop_timer(action=False)
        event.Skip()

    def on_button_down(self, event=None):
        self.stop_timer(action=False)
        if event is None:
            return
        button = event.GetEventObject()
        self.start_timer(button=button)

    def on_button_up(self, event=None):
        # That consumes the event and a wx.EVT_BUTTON will not be raised
        self.stop_timer(action=True)

    def on_button_click(self, event=None):
        # That could still happen due to a keypress
        # (i.e. return, space) while the button has focus
        if event is None:
            return
        button = event.GetEventObject()
        self.active_button = button
        self.stop_timer(action=True)


class ZMovePanel(wx.Panel):
    """
    ZMovePanel - Laser positioning and alignment control interface.

    Provides a 3x4 grid of control buttons for precise laser head positioning and element
    alignment. Supports corner alignment, directional movement, center positioning, and
    trace operations. Includes lock mode functionality to maintain relative positioning
    between laser head and selected elements during manual movement.

    **Technical Details:**
    - 9-position alignment grid (4 corners + center + directional controls)
    - Lock mode system for maintaining laser-element relationships
    - Trace operations: convex hull, quick trace, and circular trace
    - Confined movement within bed boundaries
    - Timer-based continuous movement for directional controls
    - Real-time position synchronization with device drivers

    **Signal Listeners:**
    - None (uses direct context listening for position updates)

    **User Experience:**
    - Visual alignment controls with corner/center positioning
    - Lock mode indicators (green highlighting) for active alignments
    - Directional jog controls with acceleration
    - Trace operations for element boundary following
    - First position alignment for multi-element operations
    - Right-click lock mode toggles on alignment buttons
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: Drag.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.context.setting(bool, "confined", True)
        self.SetHelpText("drag")
        self.icon_size = None
        self.resize_factor = None
        self.resolution = 5
        self.button_align_corner_top_left = wxBitmapButton(self, wx.ID_ANY)
        self.button_align_drag_up = wxBitmapButton(self, wx.ID_ANY)
        self.button_align_corner_top_right = wxBitmapButton(self, wx.ID_ANY)
        self.button_align_drag_left = wxBitmapButton(self, wx.ID_ANY)
        self.button_align_center = wxBitmapButton(self, wx.ID_ANY)
        self.button_align_drag_right = wxBitmapButton(self, wx.ID_ANY)
        self.button_align_corner_bottom_left = wxBitmapButton(self, wx.ID_ANY)
        self.button_align_drag_down = wxBitmapButton(self, wx.ID_ANY)
        self.button_align_corner_bottom_right = wxBitmapButton(self, wx.ID_ANY)
        self.button_align_first_position = wxBitmapButton(self, wx.ID_ANY)
        self.button_align_trace_hull = wxBitmapButton(self, wx.ID_ANY)
        self.button_align_trace_quick = wxBitmapButton(self, wx.ID_ANY)
        self.bg_color = self.button_align_corner_top_left.BackgroundColour
        self.__set_properties()
        self.__do_layout()
        # self.set_icons(iconsize=25)

        self.timer = TimerButtons(self)
        self.timer.add_button(self.button_align_drag_left, self.drag_left)
        self.timer.add_button(self.button_align_drag_right, self.drag_right)
        self.timer.add_button(self.button_align_drag_up, self.drag_up)
        self.timer.add_button(self.button_align_drag_down, self.drag_down)
        self.set_timer_options()

        self.Bind(
            wx.EVT_BUTTON,
            self.on_button_align_corner_tl,
            self.button_align_corner_top_left,
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_button_align_corner_tr,
            self.button_align_corner_top_right,
        )
        self.Bind(wx.EVT_BUTTON, self.on_button_align_center, self.button_align_center)
        self.Bind(
            wx.EVT_BUTTON,
            self.on_button_align_corner_bl,
            self.button_align_corner_bottom_left,
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
        self.button_align_trace_quick.Bind(
            wx.EVT_RIGHT_DOWN, self.on_button_align_trace_circle
        )
        # Right Button Events
        self.button_align_corner_top_left.Bind(
            wx.EVT_RIGHT_DOWN, self.on_button_lock_tl
        )
        self.button_align_corner_top_right.Bind(
            wx.EVT_RIGHT_DOWN, self.on_button_lock_tr
        )
        self.button_align_corner_bottom_left.Bind(
            wx.EVT_RIGHT_DOWN, self.on_button_lock_bl
        )
        self.button_align_corner_bottom_right.Bind(
            wx.EVT_RIGHT_DOWN, self.on_button_lock_br
        )
        self.button_align_center.Bind(wx.EVT_RIGHT_DOWN, self.on_button_lock_center)
        self.button_align_first_position.Bind(
            wx.EVT_BUTTON, self.on_button_align_first_position
        )

        # end wxGlade
        self.elements = None
        self.console = None
        self.design_locked = False
        self.drag_ready(False)
        self._current_lockmode = 0

    def __set_properties(self):
        # begin wxGlade: Drag.__set_properties
        lockmsg = "\n" + _(
            "(Right Mouseclick to lock/unlock the selection to the laserhead)"
        )
        self.button_align_corner_top_left.SetToolTip(
            _("Align laser with the upper left corner of the selection") + lockmsg
        )
        self.button_align_corner_top_left.SetSize(
            self.button_align_corner_top_left.GetBestSize()
        )
        self.button_align_drag_up.SetToolTip(
            _("Move the selection and laser position upwards")
        )
        self.button_align_drag_up.SetSize(self.button_align_drag_up.GetBestSize())
        self.button_align_corner_top_right.SetToolTip(
            _("Align laser with the upper right corner of the selection") + lockmsg
        )
        self.button_align_corner_top_right.SetSize(
            self.button_align_corner_top_right.GetBestSize()
        )
        self.button_align_drag_left.SetToolTip(
            _("Move the selection and laser position leftwards")
        )
        self.button_align_drag_left.SetSize(self.button_align_drag_left.GetBestSize())
        self.button_align_center.SetToolTip(
            _("Align laser with the center of the selection") + lockmsg
        )
        self.button_align_center.SetSize(self.button_align_center.GetBestSize())
        self.button_align_drag_right.SetToolTip(
            _("Move the selection and laser position rightwards")
        )
        self.button_align_drag_right.SetSize(self.button_align_drag_right.GetBestSize())
        self.button_align_corner_bottom_left.SetToolTip(
            _("Align laser with the lower left corner of the selection") + lockmsg
        )
        self.button_align_corner_bottom_left.SetSize(
            self.button_align_corner_bottom_left.GetBestSize()
        )
        self.button_align_drag_down.SetToolTip(
            _("Move the selection and laser position downwards")
        )
        self.button_align_drag_down.SetSize(self.button_align_drag_down.GetBestSize())
        self.button_align_corner_bottom_right.SetToolTip(
            _("Align laser with the lower right corner of the selection") + lockmsg
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
            _("Perform a simple trace of the selection (Right=Circle around)")
        )
        self.button_align_trace_quick.SetSize(
            self.button_align_trace_quick.GetBestSize()
        )
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Drag.__do_layout
        self.navigation_sizer = wx.BoxSizer(wx.VERTICAL)
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
        self.navigation_sizer.Add(align_sizer, 1, wx.ALIGN_CENTER_HORIZONTAL, 0)
        self.SetSizer(self.navigation_sizer)
        self.navigation_sizer.Fit(self)
        self.Layout()
        # end wxGlade

    def set_icons(self, iconsize=None, dimension=None):
        if iconsize is None and dimension is not None:
            dim_x = int(dimension[0] / 3) - 8
            dim_y = int(dimension[1] / 4) - 8
            iconsize = max(15, min(dim_x, dim_y))
        self.icon_size = iconsize
        # This is a bug within wxPython! It seems to appear only here at very high scale factors under windows
        bmp = icon_corner1.GetBitmap(resize=self.icon_size, resolution=self.resolution)
        s = bmp.Size
        self.button_align_corner_top_left.SetBitmap(bmp)
        t = self.button_align_corner_top_left.GetBitmap().Size
        # print(f"Was asking for {best_size}x{best_size}, got {s[0]}x{s[1]}, button has {t[0]}x{t[1]}")
        scale_x = s[0] / t[0]
        scale_y = s[1] / t[1]
        self.resize_factor = (self.icon_size * scale_x, self.icon_size * scale_y)
        self.button_align_corner_top_left.SetBitmap(
            icon_corner1.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_align_drag_up.SetBitmap(
            icons8_caret_up.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_align_corner_top_right.SetBitmap(
            icon_corner2.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_align_drag_left.SetBitmap(
            icons8_caret_left.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_align_center.SetBitmap(
            icons8_square_border.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_align_drag_right.SetBitmap(
            icons8_caret_right.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_align_corner_bottom_left.SetBitmap(
            icon_corner4.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_align_drag_down.SetBitmap(
            icons8_caret_down.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_align_corner_bottom_right.SetBitmap(
            icon_corner3.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_align_first_position.SetBitmap(
            icon_circled_1.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_align_trace_hull.SetBitmap(
            icons8_pentagon.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_align_trace_quick.SetBitmap(
            icons8_pentagon_squared.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.navigation_sizer.Layout()
        self.Layout()

    @property
    def lockmode(self):
        return self._current_lockmode

    @lockmode.setter
    def lockmode(self, value):
        coldefault = self.bg_color
        collocked = wx.GREEN
        bval = [coldefault, coldefault, coldefault, coldefault, coldefault]
        self._current_lockmode = value
        if 1 <= value <= 5:
            self.align_per_pos(value)
            bval[value - 1] = collocked
        self.button_align_corner_top_left.BackgroundColour = bval[0]
        self.button_align_corner_top_right.BackgroundColour = bval[1]
        self.button_align_corner_bottom_left.BackgroundColour = bval[2]
        self.button_align_corner_bottom_right.BackgroundColour = bval[3]
        self.button_align_center.BackgroundColour = bval[4]

    def lock_mode_toggle(self, button):
        if button == self.lockmode:
            self.lockmode = 0
        else:
            self.lockmode = button

    def drag_left(self):
        p1 = f"-{self.context.jog_amount}"
        p2 = "0"
        self.drag_relative(p1, p2)

    def drag_right(self):
        p1 = f"{self.context.jog_amount}"
        p2 = "0"
        self.drag_relative(p1, p2)

    def drag_down(self):
        p1 = "0"
        p2 = f"{self.context.jog_amount}"
        self.drag_relative(p1, p2)

    def drag_up(self):
        p1 = "0"
        p2 = f"-{self.context.jog_amount}"
        self.drag_relative(p1, p2)

    def on_button_lock_tl(self, event=None):
        self.lock_mode_toggle(1)

    def on_button_lock_tr(self, event=None):
        self.lock_mode_toggle(2)

    def on_button_lock_bl(self, event=None):
        self.lock_mode_toggle(3)

    def on_button_lock_br(self, event=None):
        self.lock_mode_toggle(4)

    def on_button_lock_center(self, event=None):
        self.lock_mode_toggle(5)

    def drag_ready(self, v):
        self.design_locked = v
        self.button_align_drag_down.Enable(v)
        self.button_align_drag_up.Enable(v)
        self.button_align_drag_right.Enable(v)
        self.button_align_drag_left.Enable(v)

    def get_bbox(self):
        elements = self.context.elements
        if elements.has_emphasis():
            elements.validate_selected_area()
            bbox = elements.selected_area()
        else:
            bbox = Node.union_bounds(elements.elems())
        return bbox

    def align_per_pos(self, value):
        bbox = self.get_bbox()
        if bbox is None:
            return
        if value == 1:
            x = bbox[0]
            y = bbox[1]
            if isinf(x) or isinf(y):
                return
        elif value == 2:
            x = bbox[2]
            y = bbox[1]
            if isinf(x) or isinf(y):
                return
        elif value == 3:
            x = bbox[0]
            y = bbox[3]
            if isinf(x) or isinf(y):
                return
        elif value == 4:
            x = bbox[2]
            y = bbox[3]
            if isinf(x) or isinf(y):
                return
        elif value == 5:
            x = (bbox[0] + bbox[2]) / 2.0
            y = (bbox[3] + bbox[1]) / 2.0
            if isinf(x) or isinf(y):
                return
        else:
            return
        if self.context.confined:
            min_x = 0
            max_x = float(Length(self.context.device.view.width))
            min_y = 0
            max_y = float(Length(self.context.device.view.height))
            if x < min_x or x > max_x or y < min_y or y > max_y:
                dlg = wx.MessageDialog(
                    None,
                    _("Cannot move outside bed dimensions"),
                    _("Error"),
                    wx.ICON_WARNING,
                )
                dlg.ShowModal()
                dlg.Destroy()
                return
        self.context(
            f"move_absolute {Length(amount=x).length_mm} {Length(amount=y).length_mm}\n"
        )
        self.drag_ready(True)

    def on_button_align_center(self, event=None):  # wxGlade: Navigation.<event_handler>
        self.lockmode = 0  # Reset
        self.align_per_pos(5)

    def on_button_align_corner_tl(self, event=None):
        self.lockmode = 0  # Reset
        self.align_per_pos(1)

    def on_button_align_corner_tr(self, event=None):
        self.lockmode = 0  # Reset
        self.align_per_pos(2)

    def on_button_align_corner_bl(self, event=None):
        self.lockmode = 0  # Reset
        self.align_per_pos(3)

    def on_button_align_corner_br(self, event=None):
        self.lockmode = 0  # Reset
        self.align_per_pos(4)

    def drag_relative(self, dx, dy):
        nx, ny = get_movement(self.context, dx, dy)
        self.context(f"move_relative {nx} {ny}\ntranslate {nx} {ny}\n")

    def on_button_align_first_position(self, event=None):
        first_node = None
        elements = self.context.elements
        e = list(elements.elems(emphasized=True))
        if len(e) == 0:
            for n in elements.elems():
                first_node = n
                break
        else:
            first_node = e[0]
        if first_node is None:
            return
        if hasattr(first_node, "as_geometry"):
            g = first_node.as_geometry()
            pt = g.first_point
            pos = (pt.real, pt.imag)
            # try:
            #     g = first_node.as_geometry()
            #     pos = g.first_point
            # except (IndexError, AttributeError):
            #     return
        elif first_node.type == "elem image":
            pos = (
                first_node.matrix.value_trans_x(),
                first_node.matrix.value_trans_y(),
            )
            # try:
            #     pos = (
            #         first_node.matrix.value_trans_x(),
            #         first_node.matrix.value_trans_y(),
            #     )
            # except (IndexError, AttributeError):
            #     return
        else:
            return
        self.context(
            f"move_absolute {Length(amount=pos[0]).length_mm} {Length(amount=pos[1]).length_mm}\n"
        )
        self.drag_ready(True)

    def on_button_align_trace_hull(self, event=None):
        self.context("element* trace hull\n")

    def on_button_align_trace_circle(self, event=None):
        self.context("element* trace circle\n")

    def on_button_align_trace_quick(self, event=None):
        self.context("element* trace quick\n")
        self.drag_ready(True)

    def on_modified(self, *args):
        # The selection was dragged around by the user, so let's realign the laserposition
        if self.lockmode != 0:
            self.align_per_pos(self.lockmode)

    def pane_show(self, *args):
        self.context.listen("driver;position", self.on_update)
        self.context.listen("emulator;position", self.on_update)
        self.context.listen("button-repeat", self.on_button_repeat)
        self.context.listen("modified_by_tool", self.on_modified)

    # Not sure whether this is the right thing to do, if it's still locked and then
    # the pane gets hidden?! Let's call it a feature for now...
    def pane_hide(self, *args):
        self.context.unlisten("driver;position", self.on_update)
        self.context.unlisten("emulator;position", self.on_update)
        self.context.unlisten("button-repeat", self.on_button_repeat)
        self.context.unlisten("modified_by_tool", self.on_modified)

    def set_timer_options(self):
        interval = self.context.button_repeat
        if interval is None:
            interval = 0.5
        if interval < 0:
            interval = 0
        accelerate = self.context.button_accelerate
        if accelerate is None:
            accelerate = True
        self.timer.interval = interval
        self.timer.accelerate = accelerate

    def on_button_repeat(self, origin, *args):
        self.set_timer_options()

    def on_update(self, origin, pos):
        # bb = self.get_bbox()
        elements = self.context.elements
        bb = elements._emphasized_bounds

        if bb is None or self.lockmode == 0:
            return
        if self.lockmode == 1:  # tl
            orgx = bb[0]
            orgy = bb[1]
        elif self.lockmode == 2:  # tr
            orgx = bb[2]
            orgy = bb[1]
        elif self.lockmode == 3:  # bl
            orgx = bb[0]
            orgy = bb[3]
        elif self.lockmode == 4:  # br
            orgx = bb[2]
            orgy = bb[3]
        elif self.lockmode == 5:  # center
            orgx = (bb[0] + bb[2]) / 2
            orgy = (bb[1] + bb[3]) / 2
        else:
            raise ValueError("Invalid Lockmode.")
        dx = pos[2] - orgx
        dy = pos[3] - orgy

        self.context(
            f"translate {Length(amount=dx).length_mm} {Length(amount=dy).length_mm}\n"
        )
        self.drag_ready(True)


class Jog(wx.Panel):
    """
    Jog - Manual laser positioning and element transformation controls.

    Provides directional movement controls for both laser head positioning and element
    manipulation. Supports jogging in 8 directions with configurable distances, scaling,
    rotation, and matrix transformations. Includes both fine control (5%/50%) and coarse
    control (10x distance) movement options.

    **Technical Details:**
    - 8-directional jog controls with timer-based continuous movement
    - Element transformation: scale (5%/50%), rotate (5°/90°), translate
    - Matrix editing with direct SVG transformation matrix input
    - Distance-based movement with configurable jog amounts
    - Acceleration support for long-press continuous movement
    - Real-time scene updates and element modification signaling

    **Signal Listeners:**
    - None (uses direct context listening for button repeat settings)

    **User Experience:**
    - Directional arrow controls for precise positioning
    - Scale controls with percentage-based adjustments
    - Rotation controls with degree-based increments
    - Matrix input for advanced transformation control
    - Reset function to restore original element state
    - Visual feedback with scene refresh on all operations
    """

    def drag_ready(self, v):
        self.context.elements.signal("refresh_scene", "Scene")
        self.update_matrix_text()

    def _scale(self, scale):
        self.context(f"scale {scale} {scale} \n")
        self.context.elements.signal("ext-modified")
        self.matrix_updated()

    def _rotate(self, angle):
        self.context(f"rotate {angle}deg \n")
        self.context.elements.signal("ext-modified")
        self.matrix_updated()

    def _translate(self, dx, dy, scale):
        dx = Length(
            dx,
            relative_length=self.context.space.display.width,
            unitless=UNITS_PER_PIXEL,
            preferred_units=self.context.units_name,
        )
        dx *= scale

        dy = Length(
            dy,
            relative_length=self.context.space.display.height,
            unitless=UNITS_PER_PIXEL,
            preferred_units=self.context.units_name,
        )
        dy *= scale

        self.context(f"translate {dx} {dy}\n")
        self.context.elements.signal("ext-modified")
        self.matrix_updated()

    def on_scale_down_50(self, event=None):  # wxGlade: Navigation.<event_handler>
        scale = 2.0 / 3.0  # 66.6% - inverse of 150%
        self._scale(scale)

    def on_scale_up_50(self, event=None):  # wxGlade: Navigation.<event_handler>
        scale = 3.0 / 2.0  # 150%
        self._scale(scale)

    def on_scale_down_5(self, event=None):  # wxGlade: Navigation.<event_handler>
        scale = 19.0 / 20.0
        self._scale(scale)

    def on_scale_up_5(self, event=None):  # wxGlade: Navigation.<event_handler>
        scale = 20.0 / 19.0
        self._scale(scale)

    def trans_down(self):
        dx = 0
        dy = self.context.jog_amount
        self._translate(dx, dy, 1)

    def trans_up(self):
        dx = 0
        dy = self.context.jog_amount
        self._translate(dx, dy, -1)

    def trans_left(self):
        dx = self.context.jog_amount
        dy = 0
        self._translate(dx, dy, -1)

    def trans_right(self):
        dx = self.context.jog_amount
        dy = 0
        self._translate(dx, dy, 1)

    def on_translate_up_10(self, event=None):  # wxGlade: Navigation.<event_handler>
        dx = 0
        dy = self.context.jog_amount * 10
        self._translate(dx, dy, -10)

    def on_translate_left_10(self, event=None):  # wxGlade: Navigation.<event_handler>
        dx = self.context.jog_amount
        dy = 0
        self._translate(dx, dy, -10)

    def on_translate_right_10(self, event=None):  # wxGlade: Navigation.<event_handler>
        dx = self.context.jog_amount
        dy = 0
        self._translate(dx, dy, 10)

    def on_translate_down_10(self, event=None):  # wxGlade: Navigation.<event_handler>
        dx = 0
        dy = self.context.jog_amount
        self._translate(dx, dy, 10)

    def on_reset(self, event=None):  # wxGlade: Navigation.<event_handler>
        self.context("reset\n")
        self.matrix_updated()

    def on_rotate_ccw_5(self, event=None):  # wxGlade: Navigation.<event_handler>
        angle = -5.0
        self._rotate(angle)

    def on_rotate_cw_5(self, event=None):  # wxGlade: Navigation.<event_handler>
        angle = 5.0
        self._rotate(angle)

    def on_rotate_ccw_90(self, event=None):  # wxGlade: Navigation.<event_handler>
        angle = -90.0
        self._rotate(angle)

    def on_rotate_cw_90(self, event=None):  # wxGlade: Navigation.<event_handler>
        angle = 90.0
        self._rotate(angle)

    @staticmethod
    def skewed_value(stxt):
        return Angle(stxt).radians

    @staticmethod
    def scaled_value(stxt):
        if stxt.endswith("%"):
            value = float(stxt[:-1]) / 100.0
        else:
            value = float(stxt)
        return value

    def on_text_matrix(self):
        try:
            scale_x = self.scaled_value(self.text_a.GetValue())
            skew_x = self.skewed_value(self.text_c.GetValue())
            scale_y = self.scaled_value(self.text_d.GetValue())
            skew_y = self.skewed_value(self.text_b.GetValue())
            translate_x = float(Length(self.text_e.GetValue()))
            translate_y = float(Length(self.text_f.GetValue()))
            f = self.context.elements.first_element(emphasized=True)
            if f is None:
                return
            matrix = f.matrix
            if (
                scale_x == matrix.a
                and skew_y == matrix.b
                and skew_x == matrix.c
                and scale_y == matrix.d
                and translate_x == matrix.e
                and translate_y == matrix.f
            ):
                return
            # SVG defines the transformation Matrix as  - Matrix parameters are
            #  Scale X  - Skew X  - Translate X            1 - 3 - 5
            #  Skew Y   - Scale Y - Translate Y            2 - 4 - 6
            self.context(
                f"matrix {scale_x} {skew_y} {skew_x} {scale_y} {translate_x} {translate_y}\n"
            )
            self.context.signal("refresh_scene", "Scene")
        except ValueError:
            pass

        self.update_matrix_text()


class JogDistancePanel(wx.Panel):
    """
    JogDistancePanel - Configurable jog distance settings for laser movement.

    Provides a simple input control for setting the default distance used by jog
    operations in navigation panels. Supports various length units and validates
    input to ensure proper distance values for laser positioning.

    **Technical Details:**
    - Length input validation with unit conversion
    - Persistent settings storage and retrieval
    - Real-time updates to jog movement distances
    - Integration with unit system preferences
    - Signal emission for distance changes

    **Signal Listeners:**
    - None

    **User Experience:**
    - Simple text input with length validation
    - Automatic unit conversion and display
    - Focus management for quick distance changes
    - Immediate application of distance settings
    """

    def __init__(self, *args, context=None, pane=False, **kwds):
        # begin wxGlade: JogDistancePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)

        self.SetHelpText("jog")
        self.text_jog_amount = TextCtrl(
            self,
            wx.ID_ANY,
            style=wx.TE_PROCESS_ENTER,
            value="10mm",
            check="length",
        )
        main_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Jog Distance:"), wx.VERTICAL)
        main_sizer.Add(self.text_jog_amount, 0, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()

        self.text_jog_amount.SetActionRoutine(self.on_text_jog_amount)

    def pane_show(self, *args):
        try:
            joglen = Length(
                self.context.jog_amount,
                digits=2,
                preferred_units=self.context.units_name,
            )
        except:
            joglen = Length("10mm", digits=2, preferred_units=self.context.units_name)

        self.text_jog_amount.SetValue(joglen.preferred_length)
        self.Children[0].SetFocus()

    def on_text_jog_amount(self):  # wxGlade: Navigation.<event_handler>
        try:
            jog = Length(
                self.text_jog_amount.GetValue(),
                unitless=UNITS_PER_PIXEL,
                preferred_units=self.context.units_name,
            ).preferred_length
        except ValueError:
            return
        self.context.jog_amount = str(jog)
        self.context.signal("jog_amount", str(jog))


class NavigationPanel(wx.Panel):
    """Navigation Panel - Control laser movement and positioning"""

    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        pulse_and_move_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_panels_sizer = wx.BoxSizer(wx.HORIZONTAL)

        jogdistancepanel = JogDistancePanel(self, wx.ID_ANY, context=self.context)
        main_sizer.Add(jogdistancepanel, 0, wx.EXPAND, 0)

        jogpanel = Jog(self, wx.ID_ANY, context=self.context)
        main_panels_sizer.Add(jogpanel, 1, wx.EXPAND, 0)

        dragpanel = Drag(self, wx.ID_ANY, context=self.context)
        main_panels_sizer.Add(dragpanel, 1, wx.EXPAND, 0)

        transformpanel = Transform(self, wx.ID_ANY, context=self.context)

        main_panels_sizer.Add(transformpanel, 1, wx.EXPAND, 0)
        main_sizer.Add(main_panels_sizer, 0, wx.EXPAND, 0)

        short_pulse = PulsePanel(self, wx.ID_ANY, context=self.context)
        pulse_and_move_sizer.Add(short_pulse, 1, wx.EXPAND, 0)

        move_panel = MovePanel(self, wx.ID_ANY, context=self.context)
        pulse_and_move_sizer.Add(move_panel, 1, wx.EXPAND, 0)

        size_panel = PositionPanel(self, wx.ID_ANY, context=self.context, small=True)
        pulse_and_move_sizer.Add(size_panel, 1, wx.EXPAND, 0)

        main_sizer.Add(pulse_and_move_sizer, 0, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()
        self.panels = [
            jogdistancepanel,
            jogpanel,
            dragpanel,
            transformpanel,
            short_pulse,
            move_panel,
            size_panel,
        ]
        self.Bind(wx.EVT_SIZE, self.on_resize)

    def on_resize(self, event):
        wb_size = event.GetSize()
        if platform.system() == "Linux":
            # They don't resize well
            panel_size = (max(20, wb_size[0] / 3 - 60), wb_size[1])
        else:
            panel_size = (wb_size[0] / 3, wb_size[1])
        for panel in self.panels:
            if hasattr(panel, "set_icons"):
                panel.set_icons(dimension=panel_size)
        self.Layout()

    def pane_show(self):
        for p in self.panels:
            try:
                p.pane_show()
            except AttributeError:
                pass

    def pane_hide(self):
        for p in self.panels:
            try:
                p.pane_hide()
            except AttributeError:
                pass


class Navigation(MWindow):
    """Navigation Panel - Control laser movement and positioning"""

    def __init__(self, *args, **kwds):
        super().__init__(650, 450, *args, **kwds)

        self.panel = NavigationPanel(self, wx.ID_ANY, context=self.context)
        self.sizer.Add(self.panel, 1, wx.EXPAND, 0)
        self.add_module_delegate(self.panel)
        iconsize = int(0.75 * get_default_icon_size(self.context))
        minw = (3 + 3 + 3) * iconsize + 150
        minh = (4 + 1) * iconsize + 170
        super().SetSizeHints(minW=minw, minH=minh)

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_move.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: Navigation.__set_properties
        self.SetTitle(_("Navigation"))
        self.restore_aspect(honor_initial_values=True)

    @staticmethod
    def sub_register(kernel):
        kernel.register("wxpane/Navigation", register_panel_navigation)
        kernel.register(
            "button/preparation/Navigation",
            {
                "label": _("Navigation"),
                "icon": icons8_move,
                "tip": _("Opens Navigation Window"),
                "action": lambda v: kernel.console("window toggle Navigation\n"),
                "priority": 1,
            },
        )

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    @staticmethod
    def submenu():
        # Hint for Translation: _("Editing"), _("Jog, Move and Transform")
        return "Editing", "Jog, Move and Transform"

    @staticmethod
    def helptext():
        return _("Open a control window to move the laser around")
