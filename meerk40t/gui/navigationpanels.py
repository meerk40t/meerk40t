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
    """
    This is a wrapper class around some buttons that
    allow a click, hold & repeat action
    Parameters: interval = time between repeats in seconds
    After instantiation you can add buttons via the
    add_button method.
        add_button(button, routine, parameters)
    this will call routine(parameters)

    Usage:

        def test1():
            print ("Clicked")

        def test2(p1, p2):
            print (f"Clicked with {p1} and {p2}")

        self.timer = TimerButton(self, interval=0.5)
        button1 = wxButton(self, wx.ID_ANY, "Click and hold me")
        button2 = wxButton(self, wx.ID_ANY, "Me too, please")
        self.timer.add_button(button1, test1, None)
        self.timer.add_button(button2, test2, ('First', 'Second'))
    """

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
    Z_SMALL = 1
    Z_MEDIUM = 10
    Z_LARGE = 100
    # define your “steps” once
    _BUTTON_SPECS = [
        ("up", Z_SMALL, icon_z_up),
        ("up", Z_MEDIUM, icon_z_up_double),
        ("up", Z_LARGE, icon_z_up_triple),
        ("home", None, icon_z_home),
        ("down", Z_SMALL, icon_z_down),
        ("down", Z_MEDIUM, icon_z_down_double),
        ("down", Z_LARGE, icon_z_down_triple),
    ]

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ZMovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("zmove")
        self.icon_size = 15
        self.resize_factor = 1
        self.resolution = 1
        self.buttons = {}
        self.listening = False

        for direction, step, icon in self._BUTTON_SPECS:
            if direction == "home":
                btnname = f"button_z_{direction}"
            else:
                btnname = f"button_z_{direction}_{step}"
            btn = wx.StaticBitmap(self, wx.ID_ANY)
            setattr(self, btnname, btn)
            self.buttons[btnname] = (btn, direction, step, icon)

        self.__set_properties()
        self.__do_layout()
        self.__do_logic()

    def __do_logic(self):
        self.timer = TimerButtons(self)
        for btn, direction, step, icon in self.buttons.values():
            if direction == "home":
                btn.Bind(wx.EVT_LEFT_DOWN, self.z_home)
                btn.Bind(wx.EVT_RIGHT_DOWN, self.z_focus)
            else:
                handler = (
                    self.z_move_up(step)
                    if direction == "up"
                    else self.z_move_down(step)
                )
                self.timer.add_button(btn, handler)
        self.set_timer_options()

    def __set_properties(self):
        for btn, direction, step, icon in self.buttons.values():
            if direction == "home":
                tip = _("Move the laser to the defined Z-Home-Position")
            else:
                mm = step * 0.1
                # _("Move the laserhead down by {mm} mm")
                # _("Move the laserhead up by {mm} mm")
                if direction == "up":
                    tip = _("Move the laser up by {mm}mm").format(mm=mm)
                else:
                    tip = _("Move the laser down by {mm}mm").format(mm=mm)
            btn.SetToolTip(tip)

    def __do_layout(self):
        # begin wxGlade: ZMovePanel.__do_layout
        self.navigation_sizer = wx.BoxSizer(wx.VERTICAL)
        for name in self.buttons:
            self.navigation_sizer.Add(self.buttons[name][0], 0, 0)
        self.SetSizer(self.navigation_sizer)
        self.navigation_sizer.Fit(self)
        self.set_icons(iconsize=10)
        self.Layout()

    def z_home(self, event=None):
        self.context("z_home\n")

    def z_focus(self, event=None):
        if self.context.kernel.has_command("z_focus"):
            self.context("z_focus\n")

    def z_move_down(self, distance):
        def handler():
            self.context(f"z_move -{distance*0.1:.2f}mm")

        return handler

    def z_move_up(self, distance):
        def handler():
            self.context(f"z_move {distance*0.1:.2f}mm")

        return handler

    def set_icons(self, iconsize=None, dimension=None):
        # orgsize = iconsize
        if iconsize is None and dimension is not None:
            dim_x = int(dimension[0] / 3) - 8
            dim_y = int(dimension[1] / 4) - 8
            iconsize = max(10, min(dim_x, dim_y))
        # This is a bug within wxPython! It seems to appear only here at very high scale factors under windows
        bmp = icon_z_home.GetBitmap(resize=self.icon_size, resolution=self.resolution)
        s = bmp.Size
        self.button_z_home.SetBitmap(bmp)
        t = self.button_z_home.GetBitmap().Size
        # print(f"Was asking for {best_size}x{best_size}, got {s[0]}x{s[1]}, button has {t[0]}x{t[1]}")
        scale_x = s[0] / t[0]
        scale_y = s[1] / t[1]
        self.resize_factor = (self.icon_size * scale_x, self.icon_size * scale_y)

        self.icon_size = iconsize
        # print(f"Icon-Size set to {self.icon_size}, requested was {orgsize}")
        for btn, direction, step, icon in self.buttons.values():
            bmp = icon.GetBitmap(resize=self.resize_factor, resolution=self.resolution)
            btn.SetBitmap(bmp)
        self.navigation_sizer.Layout()
        self.Layout()

    def on_update(self, origin, *args):
        has_home = self.context.kernel.has_command("z_home")
        # print (f"Has_home for {self.context.device.name}: {has_home}")
        self.button_z_home.Show(has_home)
        tip = _("Move the laser to the defined Z-Home-Position")
        if self.context.kernel.has_command("z_focus"):
            tip += "\n" + _("Right click: autofocus the Z-Axis")

        self.button_z_home.SetToolTip(tip)

        self.navigation_sizer.Show(self.button_z_home, has_home)
        self.navigation_sizer.Layout()

    def pane_show(self, *args):
        self.listening = True
        self.context.listen("button-repeat", self.on_button_repeat)
        self.context.listen("activate;device", self.on_update)
        self.on_update(None)

    def pane_hide(self, *args):
        if self.listening:
            self.context.unlisten("button-repeat", self.on_button_repeat)
            self.context.unlisten("activate;device", self.on_update)
            self.listening = False

    def set_timer_options(self):
        interval = self.context.button_repeat
        if interval is None:
            interval = 0.5
        interval = max(0, interval)
        accelerate = self.context.button_accelerate
        if accelerate is None:
            accelerate = True
        self.timer.interval = interval
        self.timer.accelerate = accelerate

    def on_button_repeat(self, origin, *args):
        self.set_timer_options()


class Drag(wx.Panel):
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

    def pane_show(self, *args):
        self.context.listen("driver;position", self.on_update)
        self.context.listen("emulator;position", self.on_update)
        self.context.listen("button-repeat", self.on_button_repeat)

    # Not sure whether this is the right thing to do, if it's still locked and then
    # the pane gets hidden?! Let's call it a feature for now...
    def pane_hide(self, *args):
        self.context.unlisten("driver;position", self.on_update)
        self.context.unlisten("emulator;position", self.on_update)
        self.context.unlisten("button-repeat", self.on_button_repeat)

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
    def __init__(self, *args, context=None, suppress_z_controls=False, **kwds):
        # begin wxGlade: Jog.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL

        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("jog")
        context.setting(float, "button_repeat", 0.5)
        context.setting(bool, "button_accelerate", True)
        context.setting(str, "jog_amount", "10mm")
        context.setting(bool, "confined", True)
        self.icon_size = None
        self.resize_factor = None
        self.resolution = 5
        self.suppress_z_controls = suppress_z_controls
        self.button_navigate_up_left = wxBitmapButton(self, wx.ID_ANY)
        self.button_navigate_up = wxBitmapButton(self, wx.ID_ANY)
        self.button_navigate_up_right = wxBitmapButton(self, wx.ID_ANY)
        self.button_navigate_left = wxBitmapButton(self, wx.ID_ANY)
        self.button_navigate_home = wxBitmapButton(self, wx.ID_ANY)
        self.button_navigate_right = wxBitmapButton(self, wx.ID_ANY)
        self.button_navigate_down_left = wxBitmapButton(self, wx.ID_ANY)
        self.button_navigate_down = wxBitmapButton(self, wx.ID_ANY)
        self.button_navigate_down_right = wxBitmapButton(self, wx.ID_ANY)
        self.button_navigate_unlock = wxBitmapButton(self, wx.ID_ANY)
        self.button_navigate_lock = wxBitmapButton(self, wx.ID_ANY)
        self.button_confine = wxBitmapButton(self, wx.ID_ANY)
        self.z_axis = ZMovePanel(self, wx.ID_ANY, context=context)
        zshow = (
            getattr(self.context.device, "supports_z_axis", False)
            and not self.suppress_z_controls
        )
        self.z_axis.Show(zshow)
        self.__set_properties()
        self.__do_layout()
        self.timer = TimerButtons(self)
        self.timer.add_button(self.button_navigate_down, self.jog_down)
        self.timer.add_button(self.button_navigate_left, self.jog_left)
        self.timer.add_button(self.button_navigate_right, self.jog_right)
        self.timer.add_button(self.button_navigate_up, self.jog_up)

        self.timer.add_button(self.button_navigate_up_left, self.jog_up_left)
        self.timer.add_button(self.button_navigate_up_right, self.jog_up_right)
        self.timer.add_button(self.button_navigate_down_left, self.jog_down_left)
        self.timer.add_button(self.button_navigate_down_right, self.jog_down_right)
        self.set_timer_options()

        # self.Bind(wx.EVT_BUTTON, self.on_button_navigate_l, self.button_navigate_left)
        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_home, self.button_navigate_home
        )
        self.button_navigate_home.Bind(
            wx.EVT_MIDDLE_DOWN, self.on_button_navigate_jobstart
        )

        self.button_navigate_home.Bind(
            wx.EVT_RIGHT_DOWN, self.on_button_navigate_physical_home
        )

        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_unlock, self.button_navigate_unlock
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_lock, self.button_navigate_lock
        )
        self.Bind(wx.EVT_BUTTON, self.on_button_confinement, self.button_confine)
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
        self.button_navigate_home.SetToolTip(
            _("Send laser to home position (right click: to physical home)")
        )
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
        self.button_confine.SetToolTip(_("Limit laser movement to bed size"))
        self.button_confine.SetSize(self.button_confine.GetBestSize())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Jog.__do_layout
        self.main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.navigation_sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = wx.FlexGridSizer(4, 3, 0, 0)
        button_sizer.Add(self.button_navigate_up_left, 0, 0, 0)
        button_sizer.Add(self.button_navigate_up, 0, 0, 0)
        button_sizer.Add(self.button_navigate_up_right, 0, 0, 0)
        button_sizer.Add(self.button_navigate_left, 0, 0, 0)
        button_sizer.Add(self.button_navigate_home, 0, 0, 0)
        button_sizer.Add(self.button_navigate_right, 0, 0, 0)
        button_sizer.Add(self.button_navigate_down_left, 0, 0, 0)
        button_sizer.Add(self.button_navigate_down, 0, 0, 0)
        button_sizer.Add(self.button_navigate_down_right, 0, 0, 0)
        button_sizer.Add(self.button_navigate_unlock, 0, 0, 0)
        button_sizer.Add(self.button_confine, 0, 0, 0)
        button_sizer.Add(self.button_navigate_lock, 0, 0, 0)
        self.navigation_sizer.Add(button_sizer, 1, wx.ALIGN_CENTER_HORIZONTAL, 0)
        self.main_sizer.Add(self.navigation_sizer, 0, wx.EXPAND)
        self.main_sizer.Add(self.z_axis, 0, wx.EXPAND)
        self.SetSizer(self.main_sizer)
        self.main_sizer.Fit(self)
        self.Layout()

    def set_icons(self, iconsize=None, dimension=None):
        cols = 4 if self.z_axis.IsShown() else 3
        if iconsize is None and dimension is not None:
            dim_x = int(dimension[0] / cols) - 8
            dim_y = int(dimension[1] / 4) - 8
            iconsize = max(15, min(dim_x, dim_y))
            dimension = None
        self.icon_size = iconsize
        # This is a bug within wxPython! It seems to appear only here at very high scale factors under windows
        bmp = icons8_up_left.GetBitmap(
            resize=self.icon_size, resolution=self.resolution
        )
        s = bmp.Size
        self.button_navigate_up_left.SetBitmap(bmp)
        t = self.button_navigate_up_left.GetBitmap().Size
        # print(f"Was asking for {best_size}x{best_size}, got {s[0]}x{s[1]}, button has {t[0]}x{t[1]}")
        scale_x = s[0] / t[0]
        scale_y = s[1] / t[1]
        self.resize_factor = (self.icon_size * scale_x, self.icon_size * scale_y)
        self.button_navigate_up_left.SetBitmap(
            icons8_up_left.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_navigate_up.SetBitmap(
            icons8_up.GetBitmap(resize=self.resize_factor, resolution=self.resolution)
        )
        self.button_navigate_up_right.SetBitmap(
            icons8_up_right.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_navigate_left.SetBitmap(
            icons8_left.GetBitmap(resize=self.resize_factor, resolution=self.resolution)
        )
        self.button_navigate_home.SetBitmap(
            icons8_home_filled.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_navigate_right.SetBitmap(
            icons8_right.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_navigate_down_left.SetBitmap(
            icons8_down_left.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_navigate_down.SetBitmap(
            icons8_down.GetBitmap(resize=self.resize_factor, resolution=self.resolution)
        )
        self.button_navigate_down_right.SetBitmap(
            icons8_down_right.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_navigate_unlock.SetBitmap(
            icons8_unlock.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_navigate_lock.SetBitmap(
            icons8_lock.GetBitmap(resize=self.resize_factor, resolution=self.resolution)
        )
        if self.context.confined:
            btn_icon = icon_fence_closed
        else:
            btn_icon = icon_fence_open
        self.button_confine.SetBitmap(
            btn_icon.GetBitmap(resize=self.resize_factor, resolution=self.resolution)
        )
        if self.z_axis.IsShown():
            # Has 7 Buttons for our 4
            self.z_axis.set_icons(
                iconsize=int(round(4 / 7 * self.icon_size, 0)), dimension=dimension
            )
        self.navigation_sizer.Layout()
        self.Layout()

    def jog_left(self):
        p1 = f"-{self.context.jog_amount}"
        p2 = "0"
        self.move_rel(p1, p2)

    def jog_up_left(self):
        p1 = f"-{self.context.jog_amount}"
        p2 = f"-{self.context.jog_amount}"
        self.move_rel(p1, p2)

    def jog_down_left(self):
        p1 = f"-{self.context.jog_amount}"
        p2 = f"{self.context.jog_amount}"
        self.move_rel(p1, p2)

    def jog_right(self):
        p1 = f"{self.context.jog_amount}"
        p2 = "0"
        self.move_rel(p1, p2)

    def jog_up_right(self):
        p1 = f"{self.context.jog_amount}"
        p2 = f"-{self.context.jog_amount}"
        self.move_rel(p1, p2)

    def jog_down_right(self):
        p1 = f"{self.context.jog_amount}"
        p2 = f"{self.context.jog_amount}"
        self.move_rel(p1, p2)

    def jog_up(self):
        p1 = "0"
        p2 = f"-{self.context.jog_amount}"
        self.move_rel(p1, p2)

    def jog_down(self):
        p1 = "0"
        p2 = f"{self.context.jog_amount}"
        self.move_rel(p1, p2)

    @property
    def is_confined(self):
        return self.context.confined

    @is_confined.setter
    def is_confined(self, value):
        # Let's see whether the device has a current option...
        try:
            dummy_x, dummy_y = self.context.device.current
        except AttributeError:
            value = False

        self.context.confined = value
        if value == 0:
            self.button_confine.SetBitmap(
                icon_fence_open.GetBitmap(
                    resize=self.resize_factor, resolution=self.resolution
                )
            )
            self.button_confine.SetToolTip(
                _("Caution: allow laser movement outside bed size")
            )
            # self.context("confine 0")
        else:
            self.button_confine.SetBitmap(
                icon_fence_closed.GetBitmap(
                    resize=self.resize_factor, resolution=self.resolution
                )
            )
            self.button_confine.SetToolTip(_("Limit laser movement to bed size"))
            # self.context("confine 1")

    def on_button_confinement(self, event=None):  # wxGlade: Navigation.<event_handler>
        self.is_confined = not self.is_confined
        try:
            current_x, current_y = self.context.device.current
        except AttributeError:
            self.is_confined = False
            return
        if not self.is_confined:
            return
        min_x = 0
        max_x = float(Length(self.context.device.view.width))
        min_y = 0
        max_y = float(Length(self.context.device.view.height))
        # Are we outside? Then let's move back to the edge...
        new_x = min(max_x, max(min_x, current_x))
        new_y = min(max_y, max(min_y, current_y))
        if new_x != current_x or new_y != current_y:
            self.context(
                f".move_absolute {Length(amount=new_x).mm:.3f}mm {Length(amount=new_y).mm:.3f}mm\n"
            )

    def move_rel(self, dx, dy):
        nx, ny = get_movement(self.context, dx, dy)
        self.context(f".move_relative {nx} {ny}\n")

    def on_button_navigate_jobstart(self, event):
        ops = self.context.elements.op_branch
        for op in ops.children:
            if op.type == "place point" and op.output:
                self.context(f"move_absolute {op.x}, {op.y}\n")
                break

    def on_button_navigate_home(
        self, event=None
    ):  # wxGlade: Navigation.<event_handler>
        self.context(".home\n")

    def on_button_navigate_physical_home(self, event=None):
        physical = False
        if hasattr(self.context.device, "has_endstops"):
            if self.context.device.has_endstops:
                physical = True
        if physical:
            self.context("physical_home\n")
        else:
            self.context("home\n")

    def on_button_navigate_unlock(
        self, event=None
    ):  # wxGlade: Navigation.<event_handler>
        self.context("unlock\n")

    def on_button_navigate_lock(
        self, event=None
    ):  # wxGlade: Navigation.<event_handler>
        self.context("lock\n")

    def set_home_logic(self):
        tip = _("Send laser to home position")
        if getattr(self.context.device, "has_endstops", False):
            tip = _("Send laser to home position (right click: to physical home)")
        ops = self.context.elements.op_branch
        for op in ops.children:
            if op.type == "place point" and op.output:
                tip += "\n" + _("(Middle Button: jump to first jobstart)")
                break
        self.button_navigate_home.SetToolTip(tip)

    def on_update(self, origin, *args):
        self.set_home_logic()
        self.set_z_support()

    def set_z_support(self):
        show_z = (
            getattr(self.context.device, "supports_z_axis", False)
            and not self.suppress_z_controls
        )
        self.z_axis.Show(show_z)
        if show_z:
            self.z_axis.pane_show()
        else:
            self.z_axis.pane_hide()
        self.set_icons(iconsize=None, dimension=self.GetClientSize())
        self.main_sizer.Show(self.z_axis, show_z)
        self.main_sizer.Layout()

    def pane_show(self):
        self.context.listen("activate;device", self.on_update)
        self.context.listen("button-repeat", self.on_button_repeat)
        self.set_home_logic()
        self.set_z_support()

    def pane_hide(self):
        self.context.unlisten("activate;device", self.on_update)
        self.context.unlisten("button-repeat", self.on_button_repeat)
        self.z_axis.pane_hide()

    def set_timer_options(self):
        interval = self.context.button_repeat
        if interval is None:
            interval = 0.5
        interval = max(0, interval)
        accelerate = self.context.button_accelerate
        if accelerate is None:
            accelerate = True
        self.timer.interval = interval
        self.timer.accelerate = accelerate

    def on_button_repeat(self, origin, *args):
        self.set_timer_options()


class MovePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)

        self.SetHelpText("move")
        iconsize = 0.5 * get_default_icon_size(self.context)
        self.button_navigate_move_to = wxBitmapButton(
            self, wx.ID_ANY, icons8_center_of_gravity.GetBitmap(resize=iconsize)
        )
        units = self.context.units_name
        if units in ("inch", "inches"):
            units = "in"
        default_pos = f"0{units}"
        self.text_position_x = TextCtrl(
            self,
            wx.ID_ANY,
            default_pos,
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_position_y = TextCtrl(
            self,
            wx.ID_ANY,
            default_pos,
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        self.small_buttons = []
        def_dim = int(2 / 3 * self.text_position_x.Size[1])
        def_pt = self.text_position_x.GetFont().GetPointSize()
        def_size = wx.Size(def_dim + 5, def_dim + 5)
        for idx in range(9):
            btn = wxStaticBitmap(self, wx.ID_ANY, size=def_size)
            icon = EmptyIcon(
                size=def_dim, msg=str(idx + 1), ptsize=def_pt, color=wx.LIGHT_GREY
            )
            btn.SetBitmap(icon.GetBitmap(resize=def_dim))
            self.small_buttons.append(btn)
            btn.Bind(wx.EVT_RIGHT_DOWN, self.on_right(idx))
            btn.Bind(wx.EVT_LEFT_DOWN, self.on_left(idx))
            if idx in (2, 5, 8):
                x = Length(self.context.elements.length_x("100%"))
            elif idx in (1, 4, 7):
                x = Length(self.context.elements.length_x("50%"))
            else:
                x = Length(self.context.elements.length_x("0%"))
            if idx in (6, 7, 8):
                y = Length(self.context.elements.length_y("100%"))
            elif idx in (3, 4, 5):
                y = Length(self.context.elements.length_y("50%"))
            else:
                y = Length(self.context.elements.length_y("0%"))
            gotostr = self.context.root.setting(
                str, f"movepos{idx}", f"{x.length_mm}|{y.length_mm}"
            )
            if gotostr:
                substr = gotostr.split("|")
                if len(substr) < 2:
                    return
                try:
                    x = Length(substr[0])
                    y = Length(substr[1])
                except ValueError:
                    pass
            label = _(
                "Left click to go to saved position\nRight click to save coordinates"
            )
            label += "\n" + _("Current: ") + f"{x.length_mm}, {y.length_mm}"
            btn.SetToolTip(label)

        self.label_pos = wxStaticText(self, wx.ID_ANY, "---")
        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_move_to, self.button_navigate_move_to
        )
        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_button_navigate_move_to, self.text_position_x
        )
        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_button_navigate_move_to, self.text_position_y
        )
        self.label_pos.Bind(wx.EVT_LEFT_DCLICK, self.on_label_dclick)
        self.button_navigate_move_to.Bind(
            wx.EVT_RIGHT_DOWN, self.on_button_navigate_move_to_right
        )
        self.Bind(wx.EVT_SIZE, self.on_size, self)

    def __set_properties(self):
        # begin wxGlade: MovePanel.__set_properties
        label = _("Move to the set position")
        label += "\n" + _("Right click to activate mouse-click mode to set position")
        self.button_navigate_move_to.SetToolTip(label)
        self.button_navigate_move_to.SetSize(self.button_navigate_move_to.GetBestSize())
        self.text_position_x.SetToolTip(_("Set X value for the Move To"))
        self.text_position_y.SetToolTip(_("Set Y value for the Move To"))
        self.label_pos.SetToolTip(_("Current laserhead position. Double-click to use."))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MovePanel.__do_layout
        main_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Move Laser to:"), wx.HORIZONTAL)
        v_main_sizer = wx.BoxSizer(wx.VERTICAL)
        h_x_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_y_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_info_sizer = wx.BoxSizer(wx.VERTICAL)
        smallfont = wx.Font(
            6, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )
        self.label_pos.SetFont(smallfont)
        button_info_sizer.Add(
            self.button_navigate_move_to, 0, wx.ALIGN_CENTER_HORIZONTAL, 0
        )
        button_info_sizer.Add(self.label_pos, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
        main_sizer.Add(button_info_sizer, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        label_9 = wxStaticText(self, wx.ID_ANY, "X:")
        self.text_position_x.SetMinSize(dip_size(self, 45, -1))
        self.text_position_y.SetMinSize(dip_size(self, 45, -1))
        h_x_sizer.Add(label_9, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        h_x_sizer.Add(self.text_position_x, 1, wx.EXPAND, 0)
        v_main_sizer.Add(h_x_sizer, 0, wx.EXPAND, 0)
        label_10 = wxStaticText(self, wx.ID_ANY, "Y:")
        h_y_sizer.Add(label_10, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        h_y_sizer.Add(self.text_position_y, 1, wx.EXPAND, 0)
        v_main_sizer.Add(h_y_sizer, 0, wx.EXPAND, 0)
        main_sizer.Add(v_main_sizer, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        # self.btn_sizer = wx.GridSizer(3, 3, 2, 2)
        # for idx in range(9):
        #     self.btn_sizer.Add(self.small_buttons[idx], 0, 0, 0)
        self.btn_sizer = wx.BoxSizer(wx.VERTICAL)
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        row3 = wx.BoxSizer(wx.HORIZONTAL)
        for idx in range(3):
            row1.Add(self.small_buttons[idx])
            row2.Add(self.small_buttons[idx + 3])
            row3.Add(self.small_buttons[idx + 6])
        self.btn_sizer.Add(row1, 0, 0, 0)
        self.btn_sizer.Add(row2, 0, 0, 0)
        self.btn_sizer.Add(row3, 0, 0, 0)
        main_sizer.Add(self.btn_sizer, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()
        # end wxGlade

    def on_size(self, event):
        # Resize event - only display numpad buttons if enough horizontal space
        winsize = self.GetSize()
        display_it = bool(winsize[0] > 175)
        self.btn_sizer.Show(display_it)
        self.btn_sizer.ShowItems(display_it)
        self.Layout()

    def on_label_dclick(self, event):
        p = self.context
        pos = p.device.current
        units = p.units_name
        xpos = Length(amount=pos[0], preferred_units=units)
        ypos = Length(amount=pos[1], preferred_units=units)
        self.text_position_x.SetValue(f"{round(xpos.preferred, 6):.1f}{units}")
        self.text_position_y.SetValue(f"{round(ypos.preferred, 6):.1f}{units}")

    def on_left(self, index):
        def handler(event):
            gotostr = getattr(self.context.root, f"movepos{index}", "")
            if gotostr:
                substr = gotostr.split("|")
                if len(substr) < 2:
                    return
                try:
                    x = Length(substr[0])
                    y = Length(substr[1])
                except ValueError:
                    return
                self.text_position_x.SetValue(substr[0])
                self.text_position_y.SetValue(substr[1])
                self.on_button_navigate_move_to(None)

        return handler

    def on_right(self, index):
        def handler(event):
            btn = event.GetEventObject()
            try:
                xlen = Length(self.text_position_x.GetValue())
                ylen = Length(self.text_position_y.GetValue())
                setattr(
                    self.context.root,
                    f"movepos{index}",
                    f"{xlen.length_mm}|{ylen.length_mm}",
                )
                label = _(
                    "Left click to go to saved position\nRight click to save coordinates"
                )
                label += "\n" + _("Current: ") + f"{xlen.length_mm}, {ylen.length_mm}"
                btn.SetToolTip(label)
            except ValueError:
                pass

        return handler

    def on_button_navigate_move_to_right(self, event=None):
        self.context("tool relocate\n")

    def on_button_navigate_move_to(
        self, event=None
    ):  # wxGlade: Navigation.<event_handler>
        try:
            x = self.text_position_x.GetValue()
            y = self.text_position_y.GetValue()
            pos_x = Length(
                x,
                relative_length=self.context.space.display.width,
                unitless=UNITS_PER_PIXEL,
                preferred_units=self.context.units_name,
            )
            pos_y = Length(
                y,
                relative_length=self.context.space.display.height,
                unitless=UNITS_PER_PIXEL,
                preferred_units=self.context.units_name,
            )
            if not self.context.device.view.source_contains(float(pos_x), float(pos_y)):
                dlg = wx.MessageDialog(
                    None,
                    _("Cannot move outside bed dimensions"),
                    _("Error"),
                    wx.ICON_WARNING,
                )
                dlg.ShowModal()
                dlg.Destroy()
                return
            self.context(f"move {pos_x} {pos_y}\n")
        except ValueError:
            return

    def update_position_info(self, origin, pos):
        # origin, pos

        if pos is None:
            return
        service = self.context.device
        # Might not come from the right device...
        if origin not in (service.path, "lhystudios"):
            # wrong device...
            return
        # New position...
        try:
            p = self.context
            units = p.units_name
            xpos = Length(amount=pos[2], preferred_units=units)
            ypos = Length(amount=pos[3], preferred_units=units)
            self.label_pos.SetLabel(
                f"{round(xpos.preferred, 6):.1f}{units}\n{round(ypos.preferred, 6):.1f}{units}"
            )
        except (ValueError, RuntimeError):
            # Already destroyed or invalid
            return
        self.label_pos.Refresh()
        # button_info_sizer.Layout()
        # self.GetSizer().Layout()
        self.Layout()
        self.Refresh()

    def pane_show(self, *args):
        self.context.listen("driver;position", self.update_position_info)
        self.context.listen("emulator;position", self.update_position_info)

    # Not sure whether this is the right thing to do, if it's still locked and then
    # the pane gets hidden?! Let's call it a feature for now...
    def pane_hide(self, *args):
        self.context.unlisten("driver;position", self.update_position_info)
        self.context.unlisten("emulator;position", self.update_position_info)


class PulsePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PulsePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)

        self.SetHelpText("pulse")
        iconsize = 0.5 * get_default_icon_size(self.context)
        self.button_navigate_pulse = wxBitmapButton(
            self, wx.ID_ANY, icons8_laser_beam.GetBitmap(resize=iconsize)
        )
        self.spin_pulse_duration = wx.SpinCtrl(
            self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER, value="50", min=1, max=1000
        )
        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_pulse, self.button_navigate_pulse
        )
        self.Bind(
            wx.EVT_SPINCTRL, self.on_spin_pulse_duration, self.spin_pulse_duration
        )
        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_button_navigate_pulse, self.spin_pulse_duration
        )
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: PulsePanel.__set_properties
        self.button_navigate_pulse.SetToolTip(_("Fire a short laser pulse"))
        self.button_navigate_pulse.SetSize(self.button_navigate_pulse.GetBestSize())
        self.spin_pulse_duration.SetMinSize(dip_size(self, 40, -1))
        self.spin_pulse_duration.SetToolTip(_("Set the duration of the laser pulse"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: PulsePanel.__do_layout
        sizer_5 = StaticBoxSizer(self, wx.ID_ANY, _("Short Pulse:"), wx.HORIZONTAL)
        sizer_5.Add(self.button_navigate_pulse, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_5.Add(self.spin_pulse_duration, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        label_4 = wxStaticText(self, wx.ID_ANY, _(" ms"))
        sizer_5.Add(label_4, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.SetSizer(sizer_5)
        sizer_5.Fit(self)
        self.Layout()
        # end wxGlade

    def on_button_navigate_pulse(
        self, event=None
    ):  # wxGlade: Navigation.<event_handler>
        value = self.spin_pulse_duration.GetValue()
        self.context(f"pulse {value}\n")

    def on_spin_pulse_duration(self, event=None):  # wxGlade: Navigation.<event_handler>
        self.context.navigate_pulse = float(self.spin_pulse_duration.GetValue())


# class SizePanel(wx.Panel):
#     object_ratio = None
#     object_x = None
#     object_y = None
#     object_width = None
#     object_height = None

#     def __init__(self, *args, context=None, **kwds):
#         # begin wxGlade: SizePanel.__init__
#         kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
#         wx.Panel.__init__(self, *args, **kwds)
#         self.context = context

#         self.mainsizer = StaticBoxSizer(
#             self, wx.ID_ANY, _("Object Dimensions"), wx.HORIZONTAL
#         )
#         self.button_navigate_resize = wxBitmapButton(
#             self, wx.ID_ANY, icons8_compress.GetBitmap(resize=32)
#         )
#         self.label_9 = wxStaticText(self, wx.ID_ANY, _("Width:"))
#         self.label_10 = wxStaticText(self, wx.ID_ANY, _("Height:"))

#         self.text_width = TextCtrl(
#             self,
#             wx.ID_ANY,
#             style=wx.TE_PROCESS_ENTER,
#             value="0",
#             check="length",
#             nonzero=True,
#         )
#         self.text_height = TextCtrl(
#             self,
#             wx.ID_ANY,
#             style=wx.TE_PROCESS_ENTER,
#             value="0",
#             check="length",
#             nonzero=True,
#         )
#         self.btn_lock_ratio = wxToggleButton(self, wx.ID_ANY, "")
#         self.bitmap_locked = icons8_lock.GetBitmap(resize=STD_ICON_SIZE/2, use_theme=False)
#         self.bitmap_unlocked = icons8_unlock.GetBitmap(resize=STD_ICON_SIZE/2, use_theme=False)

#         # No change of fields during input
#         # self.text_height.execute_action_on_change = False
#         # self.text_width.execute_action_on_change = False
#         self._updating = False
#         self.__set_properties()
#         self.__do_layout()

#         self.Bind(
#             wx.EVT_BUTTON, self.on_button_navigate_resize, self.button_navigate_resize
#         )
#         self.btn_lock_ratio.Bind(wx.EVT_TOGGLEBUTTON, self.on_toggle_ratio)
#         self.text_width.SetActionRoutine(self.on_textenter_width)
#         self.text_height.SetActionRoutine(self.on_textenter_height)

#     def __set_properties(self):
#         # begin wxGlade: SizePanel.__set_properties
#         self.button_navigate_resize.SetToolTip(_("Resize the object"))
#         self.button_navigate_resize.SetSize(self.button_navigate_resize.GetBestSize())
#         self.text_width.SetToolTip(_("Define width of selected object"))
#         self.text_height.SetToolTip(_("Define height of selected object"))
#         self.btn_lock_ratio.SetMinSize(dip_size(self, 32, 32))
#         self.btn_lock_ratio.SetToolTip(
#             _("Lock the ratio of width / height to the original values")
#         )
#         # Set toggle bitmap
#         self.on_toggle_ratio(None)
#         self.text_height.Enable(False)
#         self.text_width.Enable(False)
#         self.button_navigate_resize.Enable(False)

#         # end wxGlade

#     def __do_layout(self):
#         # begin wxGlade: SizePanel.__do_layout
#         self.mainsizer.Add(self.button_navigate_resize, 0, wx.ALIGN_CENTER_VERTICAL, 0)
#         sizer_label = wx.BoxSizer(wx.VERTICAL)
#         fieldsizer1 = wx.BoxSizer(wx.HORIZONTAL)
#         fieldsizer2 = wx.BoxSizer(wx.HORIZONTAL)
#         self.label_9.SetMinSize(dip_size(self, 45, -1))
#         self.label_10.SetMinSize(dip_size(self, 45, -1))
#         fieldsizer1.Add(self.label_9, 0, wx.ALIGN_CENTER_VERTICAL, 0)
#         fieldsizer1.Add(self.text_width, 1, wx.EXPAND, 0)

#         fieldsizer2.Add(self.label_10, 0, wx.ALIGN_CENTER_VERTICAL, 0)
#         fieldsizer2.Add(self.text_height, 1, wx.EXPAND, 0)

#         sizer_label.Add(fieldsizer1, 0, wx.EXPAND, 0)
#         sizer_label.Add(fieldsizer2, 0, wx.EXPAND, 0)

#         self.mainsizer.Add(sizer_label, 1, wx.ALIGN_CENTER_VERTICAL, 0)
#         self.mainsizer.Add(self.btn_lock_ratio, 0, wx.ALIGN_CENTER_VERTICAL, 0)

#         self.SetSizer(self.mainsizer)
#         self.mainsizer.Fit(self)

#         self.Layout()
#         # end wxGlade

#     def pane_show(self, *args):
#         self.context.listen("emphasized", self.on_emphasized_elements_changed)
#         self.context.listen("modified", self.on_modified_element)
#         self.update_sizes()

#     def pane_hide(self, *args):
#         self.context.unlisten("emphasized", self.on_emphasized_elements_changed)
#         self.context.unlisten("modified", self.on_modified_element)

#     def on_modified_element(self, origin, *args):
#         self.update_sizes()

#     def on_emphasized_elements_changed(self, origin, elements):
#         self.update_sizes()

#     def on_toggle_ratio(self, event):
#         if self.btn_lock_ratio.GetValue():
#             self.btn_lock_ratio.SetBitmap(self.bitmap_locked)
#         else:
#             self.btn_lock_ratio.SetBitmap(self.bitmap_unlocked)

#     def update_sizes(self):
#         self.object_x = None
#         self.object_y = None
#         self.object_width = None
#         self.object_height = None
#         self.object_ratio = None
#         bbox = self.context.elements.selected_area()
#         if bbox is not None:
#             p = self.context
#             units = p.units_name
#             try:
#                 self.object_x = bbox[0]
#                 self.object_y = bbox[1]
#                 self.object_width = bbox[2] - bbox[0]
#                 self.object_height = bbox[3] - bbox[1]
#                 try:
#                     self.object_ratio = self.object_width / self.object_height
#                 except ZeroDivisionError:
#                     self.object_ratio = 0
#             except (ValueError, AttributeError, TypeError):
#                 pass

#         if self.object_width is not None:
#             self.text_width.SetValue(
#                 Length(
#                     self.object_width, preferred_units=units, digits=3
#                 ).preferred_length
#             )
#             self.text_width.Enable(True)
#         else:
#             self.text_width.SetValue("---")
#             self.text_width.Enable(False)
#         if self.object_height is not None:
#             self.text_height.SetValue(
#                 Length(
#                     self.object_height, preferred_units=units, digits=3
#                 ).preferred_length
#             )
#             self.text_height.Enable(True)

#         else:
#             self.text_height.SetValue("---")
#             self.text_height.Enable(False)
#         if self.object_ratio is not None:
#             self.button_navigate_resize.Enable(True)
#         else:
#             self.button_navigate_resize.Enable(False)

#     def on_button_navigate_resize(self, event):
#         new_width = Length(
#             self.text_width.GetValue(), relative_length=self.object_width
#         )
#         new_w = float(new_width)
#         new_height = Length(
#             self.text_height.GetValue(), relative_length=self.object_height
#         )
#         new_h = float(new_height)
#         if (
#             abs(new_h - self.object_height) < 1.0e-6
#             and abs(new_w - self.object_width) < 1.0e-6
#         ):
#             # No change
#             return
#         if new_w == 0 or new_h == 0:
#             return
#         self.context(f"resize {self.object_x} {self.object_y} {new_width} {new_height}")
#         self.update_sizes()

#     def on_textenter_width(self):
#         if self._updating:
#             return
#         needsupdate = False
#         try:
#             p = self.context
#             units = p.units_name
#             new_width = Length(
#                 self.text_width.GetValue(),
#                 relative_length=self.object_width,
#                 preferred_units=units,
#                 digits=3,
#             )
#             new_w = float(new_width)
#             if new_w != self.object_width:
#                 needsupdate = True
#         except ValueError:
#             pass
#         if not needsupdate:
#             return
#         self._updating = True
#         if self.btn_lock_ratio.GetValue():
#             new_h = new_w * (1.0 / self.object_ratio)
#             new_height = Length(new_h, preferred_units=units, digits=3)
#             self.text_height.SetValue(new_height.preferred_length)
#         self._updating = False
#         self.on_button_navigate_resize(None)

#     def on_textenter_height(self):
#         if self._updating:
#             return
#         needsupdate = False
#         try:
#             p = self.context
#             units = p.units_name
#             new_height = Length(
#                 self.text_height.GetValue(),
#                 relative_length=self.object_height,
#                 preferred_units=units,
#                 digits=3,
#             )
#             new_h = float(new_height)
#             if new_h != self.object_height:
#                 needsupdate = True
#         except ValueError:
#             pass
#         if not needsupdate:
#             return
#         self._updating = True
#         if self.btn_lock_ratio.GetValue():
#             new_w = new_h * (1.0 / self.object_ratio)
#             new_width = Length(new_w, preferred_units=units, digits=3)
#             self.text_width.SetValue(new_width.preferred_length)
#         self._updating = False
#         self.on_button_navigate_resize(None)


class Transform(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: Transform.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)

        self.SetHelpText("transform")
        self.icon_size = None
        self.resize_factor = None
        self.resolution = 5
        self.button_scale_down = wxBitmapButton(self, wx.ID_ANY)
        self.button_translate_up = wxBitmapButton(self, wx.ID_ANY)
        self.button_scale_up = wxBitmapButton(self, wx.ID_ANY)
        self.button_translate_left = wxBitmapButton(self, wx.ID_ANY)
        self.button_reset = wxBitmapButton(self, wx.ID_ANY)
        self.button_translate_right = wxBitmapButton(self, wx.ID_ANY)
        self.button_rotate_ccw = wxBitmapButton(self, wx.ID_ANY)
        self.button_translate_down = wxBitmapButton(self, wx.ID_ANY)
        self.button_rotate_cw = wxBitmapButton(self, wx.ID_ANY)
        self.text_a = TextCtrl(
            self,
            wx.ID_ANY,
            style=wx.TE_PROCESS_ENTER,
            value="1.000000",
            check="percent",
            limited=True,
        )
        self.text_d = TextCtrl(
            self,
            wx.ID_ANY,
            style=wx.TE_PROCESS_ENTER,
            value="1.000000",
            check="percent",
            limited=True,
        )
        self.text_c = TextCtrl(
            self,
            wx.ID_ANY,
            style=wx.TE_PROCESS_ENTER,
            value="0.000000",
            check="angle",
            limited=True,
        )
        self.text_b = TextCtrl(
            self,
            wx.ID_ANY,
            style=wx.TE_PROCESS_ENTER,
            value="0.000000",
            check="angle",
            limited=True,
        )
        self.text_e = TextCtrl(
            self,
            wx.ID_ANY,
            style=wx.TE_PROCESS_ENTER,
            value="0.0",
            check="length",
            limited=True,
        )
        self.text_f = TextCtrl(
            self,
            wx.ID_ANY,
            style=wx.TE_PROCESS_ENTER,
            value="0.0",
            check="length",
            limited=True,
        )

        self.timer = TimerButtons(self)
        self.timer.add_button(self.button_translate_left, self.trans_left)
        self.timer.add_button(self.button_translate_right, self.trans_right)
        self.timer.add_button(self.button_translate_up, self.trans_up)
        self.timer.add_button(self.button_translate_down, self.trans_down)
        self.set_timer_options()
        self.__set_properties()
        self.__do_layout()

        self.button_scale_down.Bind(wx.EVT_BUTTON, self.on_scale_down_5)
        self.button_scale_up.Bind(wx.EVT_BUTTON, self.on_scale_up_5)
        self.button_reset.Bind(wx.EVT_BUTTON, self.on_reset)
        self.button_rotate_ccw.Bind(wx.EVT_BUTTON, self.on_rotate_ccw_5)
        self.button_rotate_cw.Bind(wx.EVT_BUTTON, self.on_rotate_cw_5)
        self.text_a.SetActionRoutine(self.on_text_matrix)
        self.text_b.SetActionRoutine(self.on_text_matrix)
        self.text_c.SetActionRoutine(self.on_text_matrix)
        self.text_d.SetActionRoutine(self.on_text_matrix)
        self.text_e.SetActionRoutine(self.on_text_matrix)
        self.text_f.SetActionRoutine(self.on_text_matrix)

        self.button_translate_up.Bind(wx.EVT_RIGHT_DOWN, self.on_translate_up_10)
        self.button_translate_down.Bind(wx.EVT_RIGHT_DOWN, self.on_translate_down_10)
        self.button_translate_left.Bind(wx.EVT_RIGHT_DOWN, self.on_translate_left_10)
        self.button_translate_right.Bind(wx.EVT_RIGHT_DOWN, self.on_translate_right_10)

        self.button_rotate_ccw.Bind(wx.EVT_RIGHT_DOWN, self.on_rotate_ccw_90)
        self.button_rotate_cw.Bind(wx.EVT_RIGHT_DOWN, self.on_rotate_cw_90)
        self.button_scale_down.Bind(wx.EVT_RIGHT_DOWN, self.on_scale_down_50)
        self.button_scale_up.Bind(wx.EVT_RIGHT_DOWN, self.on_scale_up_50)
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

        self.button_scale_down.SetToolTip(
            _("Scale Down by 5% / 50% on left / right click")
        )
        self.button_translate_up.SetToolTip(
            _("Translate Up by 1x / 10x Jog-Distance on left / right click")
        )
        self.button_scale_up.SetToolTip(_("Scale Up by 5% / 50% on left / right click"))
        self.button_translate_left.SetToolTip(
            _("Translate Left by 1x / 10x Jog-Distance on left / right click")
        )
        self.button_reset.SetToolTip(_("Reset Matrix"))
        self.button_translate_right.SetToolTip(
            _("Translate Right by 1x / 10x Jog-Distance on left / right click")
        )
        self.button_rotate_ccw.SetToolTip(
            _("Rotate Counterclockwise by 5° / by 90° on left / right click")
        )
        self.button_translate_down.SetToolTip(
            _("Translate Down by 1x / 10x Jog-Distance on left / right click")
        )
        self.button_rotate_cw.SetToolTip(
            _("Rotate Clockwise by 5° / by 90° on left / right click")
        )
        self.text_a.SetMinSize(dip_size(self, 55, -1))
        self.text_a.SetToolTip(
            _(
                "Scale X - scales the element by this factor in the X-Direction, i.e. 2.0 means 200% of the original scale. "
                "You may enter either this factor directly or state the scale as a %-value, so 0.5 or 50% will both cut the scale in half."
            )
        )
        self.text_d.SetMinSize(dip_size(self, 55, -1))
        self.text_d.SetToolTip(
            _(
                "Scale Y - scales the element by this factor in the Y-Direction, i.e. 2.0 means 200% of the original scale. "
                "You may enter either this factor directly or state the scale as a %-value, so 0.5 or 50% will both cut the scale in half."
            )
        )
        self.text_c.SetMinSize(dip_size(self, 55, -1))
        self.text_c.SetToolTip(
            _(
                "Skew X - to skew the element in X-direction by alpha° you need either \n"
                "- to provide tan(alpha), i.e. 15° = 0.2679, 30° = 0.5774, 45° = 1.0 and so on...\n"
                "- or provide the angle as 15deg, 0.25turn, (like all other angles)\n"
                "In any case this value will then be represented as tan(alpha)"
            )
        )
        self.text_b.SetMinSize(dip_size(self, 55, -1))
        self.text_b.SetToolTip(
            _(
                "Skew Y - to skew the element in Y-direction by alpha° you need either \n"
                "- to provide tan(alpha), i.e. 15° = 0.2679, 30° = 0.5774, 45° = 1.0 and so on...\n"
                "- or provide the angle as 15deg, 0.25turn, (like all other angles)\n"
                "In any case this value will then be represented as tan(alpha)"
            )
        )
        self.text_e.SetMinSize(dip_size(self, 40, -1))
        self.text_e.SetToolTip(
            _(
                "Translate X - moves the element by this amount of mils in the X-direction; "
                "you may use 'real' distances when modifying this factor, i.e. 2in, 3cm, 50mm"
            )
        )
        self.text_f.SetMinSize(dip_size(self, 40, -1))
        self.text_f.SetToolTip(
            _(
                "Translate Y - moves the element by this amount of mils in the Y-direction; "
                "you may use 'real' distances when modifying this factor, i.e. 2in, 3cm, 50mm"
            )
        )
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Transform.__do_layout
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        icon_sizer = wx.FlexGridSizer(3, 3, 0, 0)
        icon_sizer.Add(self.button_scale_down, 0, 0, 0)
        icon_sizer.Add(self.button_translate_up, 0, 0, 0)
        icon_sizer.Add(self.button_scale_up, 0, 0, 0)
        icon_sizer.Add(self.button_translate_left, 0, 0, 0)
        icon_sizer.Add(self.button_reset, 0, 0, 0)
        icon_sizer.Add(self.button_translate_right, 0, 0, 0)
        icon_sizer.Add(self.button_rotate_ccw, 0, 0, 0)
        icon_sizer.Add(self.button_translate_down, 0, 0, 0)
        icon_sizer.Add(self.button_rotate_cw, 0, 0, 0)

        matrix_sizer = wx.BoxSizer(wx.HORIZONTAL)
        col_sizer_1 = wx.BoxSizer(wx.VERTICAL)
        col_sizer_1.Add(wxStaticText(self, wx.ID_ANY, ""), wx.HORIZONTAL)
        col_sizer_1.Add(wxStaticText(self, wx.ID_ANY, _("X:")), wx.HORIZONTAL)
        col_sizer_1.Add(wxStaticText(self, wx.ID_ANY, _("Y:")), wx.HORIZONTAL)

        # Add some labels to make textboxes clearer to understand
        col_sizer_2 = wx.BoxSizer(wx.VERTICAL)
        col_sizer_2.Add(wxStaticText(self, wx.ID_ANY, _("Scale")), wx.HORIZONTAL)
        col_sizer_2.Add(self.text_a, 0, wx.EXPAND, 0)  # Scale X
        col_sizer_2.Add(self.text_d, 0, wx.EXPAND, 0)  # Scale Y

        col_sizer_3 = wx.BoxSizer(wx.VERTICAL)
        col_sizer_3.Add(wxStaticText(self, wx.ID_ANY, _("Skew")), wx.HORIZONTAL)
        col_sizer_3.Add(self.text_c, 0, wx.EXPAND, 0)  # Skew X
        col_sizer_3.Add(self.text_b, 0, wx.EXPAND, 0)  # Skew Y

        col_sizer_4 = wx.BoxSizer(wx.VERTICAL)
        col_sizer_4.Add(wxStaticText(self, wx.ID_ANY, _("Translate")), wx.HORIZONTAL)
        col_sizer_4.Add(self.text_e, 0, wx.EXPAND, 0)  # Translate X
        col_sizer_4.Add(self.text_f, 0, wx.EXPAND, 0)  # Translate Y

        matrix_sizer.Add(col_sizer_1, 0, wx.EXPAND, 0)  # fixed width
        matrix_sizer.Add(col_sizer_2, 1, wx.EXPAND, 0)  # grow
        matrix_sizer.Add(col_sizer_3, 1, wx.EXPAND, 0)  # grow
        matrix_sizer.Add(col_sizer_4, 1, wx.EXPAND, 0)  # grow

        main_sizer.Add(icon_sizer, 0, wx.EXPAND, 0)
        main_sizer.Add(matrix_sizer, 0, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()
        # end wxGlade

    def set_icons(self, iconsize=None, dimension=None):
        if iconsize is None and dimension is not None:
            dim_x = int(dimension[0] / 3) - 8
            dim_y = int(dimension[1] / 4) - 8
            iconsize = max(15, min(dim_x, dim_y))
        self.icon_size = iconsize
        # This is a bug within wxPython! It seems to appear only here at very high scale factors under windows
        bmp = icons8_compress.GetBitmap(
            resize=self.icon_size, resolution=self.resolution
        )
        s = bmp.Size
        self.button_scale_down.SetBitmap(bmp)
        t = self.button_scale_down.GetBitmap().Size
        # print(f"Was asking for {best_size}x{best_size}, got {s[0]}x{s[1]}, button has {t[0]}x{t[1]}")
        scale_x = s[0] / t[0]
        scale_y = s[1] / t[1]
        self.resize_factor = (self.icon_size * scale_x, self.icon_size * scale_y)

        self.button_scale_down.SetBitmap(
            icons8_compress.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_translate_up.SetBitmap(
            icons8_up.GetBitmap(resize=self.resize_factor, resolution=self.resolution)
        )
        self.button_scale_up.SetBitmap(
            icons8_enlarge.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_translate_left.SetBitmap(
            icons8_left.GetBitmap(resize=self.resize_factor, resolution=self.resolution)
        )
        self.button_reset.SetBitmap(
            icons8_delete.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_translate_right.SetBitmap(
            icons8_right.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_rotate_ccw.SetBitmap(
            icons8_rotate_left.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.button_translate_down.SetBitmap(
            icons8_down.GetBitmap(resize=self.resize_factor, resolution=self.resolution)
        )
        self.button_rotate_cw.SetBitmap(
            icons8_rotate_right.GetBitmap(
                resize=self.resize_factor, resolution=self.resolution
            )
        )
        self.Layout()

    def pane_show(self, *args):
        self.context.listen("emphasized", self.on_emphasized_elements_changed)
        self.context.listen("modified", self.on_modified_element)
        self.context.listen("button-repeat", self.on_button_repeat)
        self.update_matrix_text()

    def pane_hide(self, *args):
        self.context.unlisten("emphasized", self.on_emphasized_elements_changed)
        self.context.unlisten("modified", self.on_modified_element)
        self.context.unlisten("button-repeat", self.on_button_repeat)

    # To get updates about translation / scaling of selected elements
    # we need to attach to some signals...
    @signal_listener("refresh_scene")
    def on_refresh_scene(self, origin, scene_name=None, *args):
        if scene_name == "Scene":
            self.update_matrix_text()

    @signal_listener("modified_by_tool")
    def on_modified(self, *args):
        self.update_matrix_text()

    def set_timer_options(self):
        interval = self.context.button_repeat
        if interval is None:
            interval = 0.5
        interval = max(0, interval)
        accelerate = self.context.button_accelerate
        if accelerate is None:
            accelerate = True
        self.timer.interval = interval
        self.timer.accelerate = accelerate

    def on_button_repeat(self, origin, *args):
        self.set_timer_options()

    def on_modified_element(self, origin, *args):
        self.update_matrix_text()

    def on_emphasized_elements_changed(self, origin, *args):
        self.context.elements.set_start_time("Emphasis Transform")
        self.select_ready(self.context.elements.has_emphasis())
        self.update_matrix_text()
        self.context.elements.set_end_time("Emphasis Transform")

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
            matrix = f.matrix
            # You will get sometimes slightly different numbers than you would expect due to arithmetic operations
            # we will therefore 'adjust' those figures slightly to avoid confusion by rounding them to the sixth decimal (arbitrary)
            # that should be good enough...
            self.text_a.SetValue(f"{matrix.a:.5f}")  # Scale X
            self.text_b.SetValue(f"{matrix.b:.5f}")  # Skew Y
            self.text_c.SetValue(f"{matrix.c:.5f}")  # Skew X
            self.text_d.SetValue(f"{matrix.d:.5f}")  # Scale Y
            # Translate X & are in mils, so about 0.025 mm, so 1 digit should be more than enough...
            # self.text_e.SetValue(f"{matrix.e:.1f}")  # Translate X
            # self.text_f.SetValue(f"{matrix.f:.1f}")  # Translate Y
            l1 = Length(
                amount=matrix.e, digits=2, preferred_units=self.context.units_name
            )
            l2 = Length(
                amount=matrix.f, digits=2, preferred_units=self.context.units_name
            )
            self.text_e.SetValue(l1.preferred_length)
            self.text_f.SetValue(l2.preferred_length)
            m_e = matrix.e
            m_f = matrix.f
            ttip1 = _(
                "Translate X - moves the element by this amount of mils in the X-direction; "
                "you may use 'real' distances when modifying this factor, i.e. 2in, 3cm, 50mm"
            )
            ttip1 = ttip1 + "\n" + _("Current internal value: ") + f"{m_e:.1f}"
            ttip2 = _(
                "Translate Y - moves the element by this amount of mils in the Y-direction; "
                "you may use 'real' distances when modifying this factor, i.e. 2in, 3cm, 50mm"
            )
            ttip2 = ttip2 + "\n" + _("Current internal value: ") + f"{m_f:.1f}"

            self.text_e.SetToolTip(ttip1)
            self.text_f.SetToolTip(ttip2)

    def select_ready(self, v):
        """
        Enables the relevant buttons when there is a selection in the elements.
        @param v: whether selection is currently drag ready.
        @return:
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
        return "Editing", "Jog, Move and Transform"

    @staticmethod
    def helptext():
        return _("Open a control window to move the laser around")
