import platform

import wx
from wx import aui

from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_PIXEL, Length
from meerk40t.gui.icons import (
    get_default_icon_size,
    icon_corner1,
    icon_corner2,
    icon_corner3,
    icon_corner4,
    icons8_center_of_gravity_50,
    icons8_compress_50,
    icons8_constraint_50,
    icons8_delete_50,
    icons8_down,
    icons8_down_50,
    icons8_down_left_50,
    icons8_down_right_50,
    icons8_enlarge_50,
    icons8_expansion_50,
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
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import TextCtrl
from meerk40t.svgelements import Angle

_ = wx.GetTranslation


def register_panel_navigation(window, context):
    panel = Drag(window, wx.ID_ANY, context=context)
    iconsize = get_default_icon_size()
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
    pane.control = panel
    pane.submenu = "_20_" + _("Navigation")

    window.on_pane_create(pane)
    context.register("pane/drag", pane)
    panel = Jog(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .MinSize(3 * iconsize + dx, 3 * iconsize + dy)
        .BestSize(3 * iconsize + dx, 3 * iconsize + dy)
        .FloatingSize(3 * iconsize + dx, 3 * iconsize + dy)
        .MaxSize(300, 300)
        .Caption(_("Jog"))
        .Name("jog")
        .CaptionVisible(not context.pane_lock)
    )
    pane.dock_proportion = 3 * iconsize + dx
    pane.control = panel
    pane.submenu = "_20_" + _("Navigation")

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
    )
    pane.dock_proportion = iconsize + 100
    pane.control = panel
    pane.submenu = "_20_" + _("Navigation")

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

    window.on_pane_create(pane)
    context.register("pane/pulse", pane)

    panel = SizePanel(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .MinSize(75, 50)
        .FloatingSize(150, 75)
        .Hide()
        .Caption(_("Element-Size"))
        .CaptionVisible(not context.pane_lock)
        .Name("objsizer")
    )
    pane.dock_proportion = 150
    pane.control = panel
    pane.submenu = "_40_" + _("Editing")

    window.on_pane_create(pane)
    context.register("pane/objsizer", pane)

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

    window.on_pane_create(pane)
    context.register("pane/jogdist", pane)


_confined = True


def get_movement(device, dx, dy):
    try:
        current_x, current_y = device.current
    except AttributeError:
        return dx, dy

    if not _confined:
        return dx, dy

    newx = float(Length(dx))
    newy = float(Length(dy))
    min_x = 0
    max_x = float(Length(device.width))
    min_y = 0
    max_y = float(Length(device.height))
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
        self.bg_color = self.button_align_corner_top_left.BackgroundColour
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
        self.button_align_trace_hull.Bind(
            wx.EVT_RIGHT_DOWN, self.on_button_align_trace_complex
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
            _(
                "Perform a convex hull trace of the selection (Right different algorithm)"
            )
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
        elif value == 2:
            x = bbox[2]
            y = bbox[1]
        elif value == 3:
            x = bbox[0]
            y = bbox[3]
        elif value == 4:
            x = bbox[2]
            y = bbox[3]
        elif value == 5:
            x = (bbox[0] + bbox[2]) / 2.0
            y = (bbox[3] + bbox[1]) / 2.0
        else:
            return
        if _confined:
            min_x = 0
            max_x = float(Length(self.context.device.width))
            min_y = 0
            max_y = float(Length(self.context.device.height))
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
        nx, ny = get_movement(self.context.device, dx, dy)
        self.context(f"move_relative {nx} {ny}\ntranslate {nx} {ny}\n")

    def on_button_align_drag_down(
        self, event=None
    ):  # wxGlade: Navigation.<event_handler>
        self.drag_relative(0, self.context.jog_amount)

    def on_button_align_drag_right(
        self, event=None
    ):  # wxGlade: Navigation.<event_handler>
        self.drag_relative(self.context.jog_amount, 0)

    def on_button_align_drag_up(
        self, event=None
    ):  # wxGlade: Navigation.<event_handler>
        self.drag_relative(0, str(-Length(self.context.jog_amount)))

    def on_button_align_drag_left(
        self, event=None
    ):  # wxGlade: Navigation.<event_handler>
        self.drag_relative(str(-Length(self.context.jog_amount)), 0)

    def on_button_align_first_position(self, event=None):
        elements = self.context.elements
        e = list(elements.elems(emphasized=True))
        first_node = e[0]
        if first_node.type == "elem path":
            try:
                pos = first_node.path.first_point * first_node.matrix
            except (IndexError, AttributeError):
                return
        elif first_node.type == "elem image":
            try:
                pos = (
                    first_node.matrix.value_trans_x(),
                    first_node.matrix.value_trans_y(),
                )
            except (IndexError, AttributeError):
                return
        else:
            return
        self.context(
            f"move_absolute {Length(amount=pos[0]).length_mm} {Length(amount=pos[1]).length_mm}\n"
        )
        self.drag_ready(True)

    def on_button_align_trace_hull(self, event=None):
        self.context("trace hull\n")

    def on_button_align_trace_complex(self, event=None):
        self.context("trace complex\n")

    def on_button_align_trace_circle(self, event=None):
        self.context("trace circle\n")

    def on_button_align_trace_quick(self, event=None):
        self.context("trace quick\n")
        self.drag_ready(True)

    def pane_show(self, *args):
        self.context.listen("driver;position", self.on_update)
        self.context.listen("emulator;position", self.on_update)

    # Not sure whether this is the right thing to do, if it's still locked and then
    # the pane gets hidden?! Let's call it a feature for now...
    def pane_hide(self, *args):
        self.context.unlisten("driver;position", self.on_update)
        self.context.unlisten("emulator;position", self.on_update)

    def on_update(self, origin, pos):
        # bb = self.get_bbox()
        elements = self.context.elements
        bb = elements._emphasized_bounds

        if bb is None or self.lockmode == 0:
            return
        dx = 0
        dy = 0
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
        dx = pos[2] - orgx
        dy = pos[3] - orgy

        self.context(
            f"translate {Length(amount=dx).length_mm} {Length(amount=dy).length_mm}\n"
        )
        self.drag_ready(True)


class Jog(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: Jog.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL

        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        context.setting(str, "jog_amount", "10mm")
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
        self.button_confine = wx.BitmapButton(
            self, wx.ID_ANY, icons8_constraint_50.GetBitmap()
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
        navigation_sizer.Add(self.button_confine, 0, 0, 0)
        navigation_sizer.Add(self.button_navigate_lock, 0, 0, 0)
        self.SetSizer(navigation_sizer)
        navigation_sizer.Fit(self)
        self.Layout()
        # end wxGlade

    @property
    def confined(self):
        global _confined
        return _confined

    @confined.setter
    def confined(self, value):
        global _confined
        # Let's see whether the device has a current option...
        try:
            dummyx, dummy = self.context.device.current
        except AttributeError:
            value = False

        _confined = value
        if value == 0:
            self.button_confine.SetBitmap(icons8_expansion_50.GetBitmap())
            self.button_confine.SetToolTip(
                _("Caution: allow laser movement outside bed size")
            )
            # self.context("confine 0")
        else:
            self.button_confine.SetBitmap(icons8_constraint_50.GetBitmap())
            self.button_confine.SetToolTip(_("Limit laser movement to bed size"))
            # self.context("confine 1")

    def on_button_confinement(self, event=None):  # wxGlade: Navigation.<event_handler>
        self.confined = not self.confined
        try:
            current_x, current_y = self.context.device.current
        except AttributeError:
            self.confined = False
        if self.confined:
            min_x = 0
            max_x = float(Length(self.context.device.width))
            min_y = 0
            max_y = float(Length(self.context.device.height))
            # Are we outside? Then lets move back to the edge...
            new_x = min(max_x, max(min_x, current_x))
            new_y = min(max_y, max(min_y, current_y))
            if new_x != current_x or new_y != current_y:
                self.context(
                    f"move_absolute {Length(amount=new_x).mm:.3f}mm {Length(amount=new_y).mm:.3f}mm\n"
                )

    def move_rel(self, dx, dy):
        nx, ny = get_movement(self.context.device, dx, dy)
        self.context(f"move_relative {nx} {ny}\n")

    def on_button_navigate_home(
        self, event=None
    ):  # wxGlade: Navigation.<event_handler>
        self.context("home\n")

    def on_button_navigate_ul(self, event=None):  # wxGlade: Navigation.<event_handler>
        self.move_rel(
            f"-{self.context.jog_amount}",
            f"-{self.context.jog_amount}",
        )

    def on_button_navigate_u(self, event=None):  # wxGlade: Navigation.<event_handler>
        self.move_rel("0", f"-{self.context.jog_amount}")

    def on_button_navigate_ur(self, event=None):  # wxGlade: Navigation.<event_handler>
        self.move_rel(
            f"{self.context.jog_amount}",
            f"-{self.context.jog_amount}",
        )

    def on_button_navigate_l(self, event=None):  # wxGlade: Navigation.<event_handler>
        self.move_rel(f"-{self.context.jog_amount}", "0")

    def on_button_navigate_r(self, event=None):  # wxGlade: Navigation.<event_handler>
        self.move_rel(f"{self.context.jog_amount}", "0")

    def on_button_navigate_dl(self, event=None):  # wxGlade: Navigation.<event_handler>
        self.move_rel(
            f"-{self.context.jog_amount}",
            f"{self.context.jog_amount}",
        )

    def on_button_navigate_d(self, event=None):  # wxGlade: Navigation.<event_handler>
        self.move_rel("0", f"{self.context.jog_amount}")

    def on_button_navigate_dr(self, event=None):  # wxGlade: Navigation.<event_handler>
        self.move_rel(
            f"{self.context.jog_amount}",
            f"{self.context.jog_amount}",
        )

    def on_button_navigate_unlock(
        self, event=None
    ):  # wxGlade: Navigation.<event_handler>
        self.context("unlock\n")

    def on_button_navigate_lock(
        self, event=None
    ):  # wxGlade: Navigation.<event_handler>
        self.context("lock\n")


class MovePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.button_navigate_move_to = wx.BitmapButton(
            self, wx.ID_ANY, icons8_center_of_gravity_50.GetBitmap(resize=32)
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

    def __set_properties(self):
        # begin wxGlade: MovePanel.__set_properties
        self.button_navigate_move_to.SetToolTip(_("Move to the set position"))
        self.button_navigate_move_to.SetSize(self.button_navigate_move_to.GetBestSize())
        self.text_position_x.SetToolTip(_("Set X value for the Move To"))
        self.text_position_y.SetToolTip(_("Set Y value for the Move To"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MovePanel.__do_layout
        main_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Move Laser to:")), wx.HORIZONTAL
        )
        v_main_sizer = wx.BoxSizer(wx.VERTICAL)
        h_x_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_y_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.Add(self.button_navigate_move_to, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        label_9 = wx.StaticText(self, wx.ID_ANY, "X:")
        self.text_position_x.SetMinSize((45, 23))
        self.text_position_y.SetMinSize((45, 23))
        h_x_sizer.Add(label_9, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        h_x_sizer.Add(self.text_position_x, 1, wx.EXPAND, 0)
        v_main_sizer.Add(h_x_sizer, 0, wx.EXPAND, 0)
        label_10 = wx.StaticText(self, wx.ID_ANY, "Y:")
        h_y_sizer.Add(label_10, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        h_y_sizer.Add(self.text_position_y, 1, wx.EXPAND, 0)
        v_main_sizer.Add(h_y_sizer, 0, wx.EXPAND, 0)
        main_sizer.Add(v_main_sizer, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()
        # end wxGlade

    def on_button_navigate_move_to(
        self, event=None
    ):  # wxGlade: Navigation.<event_handler>
        try:
            x = self.text_position_x.GetValue()
            y = self.text_position_y.GetValue()
            if not self.context.device.contains(x, y):
                dlg = wx.MessageDialog(
                    None,
                    _("Cannot move outside bed dimensions"),
                    _("Error"),
                    wx.ICON_WARNING,
                )
                dlg.ShowModal()
                dlg.Destroy()
                return
            pos_x = self.context.device.length(
                self.text_position_x.GetValue(),
                axis=0,
                new_units=self.context.units_name,
                unitless=UNITS_PER_PIXEL,
            )
            pos_y = self.context.device.length(
                self.text_position_y.GetValue(),
                axis=1,
                new_units=self.context.units_name,
                unitless=UNITS_PER_PIXEL,
            )
            self.context(f"move {pos_x} {pos_y}\n")
        except ValueError:
            return


class PulsePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PulsePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.button_navigate_pulse = wx.BitmapButton(
            self, wx.ID_ANY, icons8_laser_beam_52.GetBitmap(resize=32)
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
        self.spin_pulse_duration.SetMinSize((40, 23))
        self.spin_pulse_duration.SetToolTip(_("Set the duration of the laser pulse"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: PulsePanel.__do_layout
        sizer_5 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Short Pulse:")), wx.HORIZONTAL
        )
        sizer_5.Add(self.button_navigate_pulse, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_5.Add(self.spin_pulse_duration, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        label_4 = wx.StaticText(self, wx.ID_ANY, _(" ms"))
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


class SizePanel(wx.Panel):
    object_ratio = None
    object_x = None
    object_y = None
    object_width = None
    object_height = None

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: SizePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        self.mainsizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Object Dimensions")), wx.HORIZONTAL
        )
        self.button_navigate_resize = wx.BitmapButton(
            self, wx.ID_ANY, icons8_compress_50.GetBitmap(resize=32)
        )
        self.label_9 = wx.StaticText(self, wx.ID_ANY, _("Width:"))
        self.label_10 = wx.StaticText(self, wx.ID_ANY, _("Height:"))

        self.text_width = TextCtrl(
            self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER, value="0", check="length"
        )
        self.text_height = TextCtrl(
            self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER, value="0", check="length"
        )
        self.btn_lock_ratio = wx.ToggleButton(self, wx.ID_ANY, "")
        # No change of fields during input
        # self.text_height.execute_action_on_change = False
        # self.text_width.execute_action_on_change = False
        self._updating = False
        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_BUTTON, self.on_button_navigate_resize, self.button_navigate_resize
        )
        self.text_width.SetActionRoutine(self.on_textenter_width)
        self.text_height.SetActionRoutine(self.on_textenter_height)

    def __set_properties(self):
        # begin wxGlade: SizePanel.__set_properties
        self.button_navigate_resize.SetToolTip(_("Resize the object"))
        self.button_navigate_resize.SetSize(self.button_navigate_resize.GetBestSize())
        self.text_width.SetToolTip(_("Define width of selected object"))
        self.text_height.SetToolTip(_("Define height of selected object"))
        self.btn_lock_ratio.SetMinSize((32, 32))
        self.btn_lock_ratio.SetBitmap(
            icons8_lock_50.GetBitmap(resize=25, use_theme=False)
        )
        self.btn_lock_ratio.SetToolTip(
            _("Lock the ratio of width / height to the original values")
        )
        self.text_height.Enable(False)
        self.text_width.Enable(False)
        self.button_navigate_resize.Enable(False)

        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: SizePanel.__do_layout
        self.mainsizer.Add(self.button_navigate_resize, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_label = wx.BoxSizer(wx.VERTICAL)
        fieldsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        fieldsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.label_9.SetMinSize(wx.Size(45, -1))
        self.label_10.SetMinSize(wx.Size(45, -1))
        fieldsizer1.Add(self.label_9, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        fieldsizer1.Add(self.text_width, 1, wx.EXPAND, 0)

        fieldsizer2.Add(self.label_10, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        fieldsizer2.Add(self.text_height, 1, wx.EXPAND, 0)

        sizer_label.Add(fieldsizer1, 0, wx.EXPAND, 0)
        sizer_label.Add(fieldsizer2, 0, wx.EXPAND, 0)

        self.mainsizer.Add(sizer_label, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.mainsizer.Add(self.btn_lock_ratio, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.SetSizer(self.mainsizer)
        self.mainsizer.Fit(self)

        self.Layout()
        # end wxGlade

    def pane_show(self, *args):
        self.context.listen("emphasized", self.on_emphasized_elements_changed)
        self.context.listen("modified", self.on_modified_element)
        self.update_sizes()

    def pane_hide(self, *args):
        self.context.unlisten("emphasized", self.on_emphasized_elements_changed)
        self.context.unlisten("modified", self.on_modified_element)

    def on_modified_element(self, origin, *args):
        self.update_sizes()

    def on_emphasized_elements_changed(self, origin, elements):
        self.update_sizes()

    def update_sizes(self):
        self.object_x = None
        self.object_y = None
        self.object_width = None
        self.object_height = None
        self.object_ratio = None
        bbox = self.context.elements.selected_area()
        if bbox is not None:
            p = self.context
            units = p.units_name
            try:
                self.object_x = bbox[0]
                self.object_y = bbox[1]
                self.object_width = bbox[2] - bbox[0]
                self.object_height = bbox[3] - bbox[1]
                try:
                    self.object_ratio = self.object_width / self.object_height
                except ZeroDivisionError:
                    self.object_ratio = 0
            except (ValueError, AttributeError, TypeError):
                pass

        if self.object_width is not None:
            self.text_width.SetValue(Length(self.object_width, preferred_units=units, digits=3).preferred_length)
            self.text_width.Enable(True)
        else:
            self.text_width.SetValue("---")
            self.text_width.Enable(False)
        if self.object_height is not None:
            self.text_height.SetValue(Length(self.object_height, preferred_units=units, digits=3).preferred_length)
            self.text_height.Enable(True)

        else:
            self.text_height.SetValue("---")
            self.text_height.Enable(False)
        if self.object_ratio is not None:
            self.button_navigate_resize.Enable(True)
        else:
            self.button_navigate_resize.Enable(False)

    def on_button_navigate_resize(self, event):
        new_width = Length(
            self.text_width.GetValue(), relative_length=self.object_width
        )
        new_w = float(new_width)
        new_height = Length(
            self.text_height.GetValue(), relative_length=self.object_height
        )
        new_h = float(new_height)
        if abs(new_h - self.object_height) < 1.0E-6 and abs(new_w - self.object_width) < 1.0E-6:
            # No change
            return
        if new_w == 0 or new_h == 0:
            return
        self.context(f"resize {self.object_x} {self.object_y} {new_width} {new_height}")
        self.update_sizes()

    def on_textenter_width(self):
        if self._updating:
            return
        needsupdate = False
        try:
            p = self.context
            units = p.units_name
            new_width = Length(
                self.text_width.GetValue(),
                relative_length=self.object_width,
                preferred_units=units,
                digits=3,
            )
            new_w = float(new_width)
            if new_w != self.object_width:
                needsupdate = True
        except ValueError:
            pass
        if not needsupdate:
            return
        self._updating = True
        if self.btn_lock_ratio.GetValue():
            new_h = new_w * (1.0 / self.object_ratio)
            new_height = Length(new_h, preferred_units=units, digits=3)
            self.text_height.SetValue(new_height.preferred_length)
        self._updating = False
        self.on_button_navigate_resize(None)

    def on_textenter_height(self):
        if self._updating:
            return
        needsupdate = False
        try:
            p = self.context
            units = p.units_name
            new_height = Length(
                self.text_height.GetValue(),
                relative_length=self.object_height,
                preferred_units=units,
                digits=3,
            )
            new_h = float(new_height)
            if new_h != self.object_height:
                needsupdate = True
        except ValueError:
            pass
        if not needsupdate:
            return
        self._updating = True
        if self.btn_lock_ratio.GetValue():
            new_w = new_h * (1.0 / self.object_ratio)
            new_width = Length(new_w, preferred_units=units, digits=3)
            self.text_width.SetValue(new_width.preferred_length)
        self._updating = False
        self.on_button_navigate_resize(None)


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

        self.__set_properties()
        self.__do_layout()

        self.button_scale_down.Bind(wx.EVT_BUTTON, self.on_scale_down_5)
        self.button_translate_up.Bind(wx.EVT_BUTTON, self.on_translate_up_1)
        self.button_scale_up.Bind(wx.EVT_BUTTON, self.on_scale_up_5)
        self.button_translate_left.Bind(wx.EVT_BUTTON, self.on_translate_left_1)
        self.button_reset.Bind(wx.EVT_BUTTON, self.on_reset)
        self.button_rotate_ccw.Bind(wx.EVT_BUTTON, self.on_rotate_ccw_5)
        self.button_translate_right.Bind(wx.EVT_BUTTON, self.on_translate_right_1)
        self.button_rotate_cw.Bind(wx.EVT_BUTTON, self.on_rotate_cw_5)
        self.button_translate_down.Bind(wx.EVT_BUTTON, self.on_translate_down_1)
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
        self.text_a.SetMinSize((55, -1))
        self.text_a.SetToolTip(
            _(
                "Scale X - scales the element by this factor in the X-Direction, i.e. 2.0 means 200% of the original scale. "
                "You may enter either this factor directly or state the scale as a %-value, so 0.5 or 50% will both cut the scale in half."
            )
        )
        self.text_d.SetMinSize((55, -1))
        self.text_d.SetToolTip(
            _(
                "Scale Y - scales the element by this factor in the Y-Direction, i.e. 2.0 means 200% of the original scale. "
                "You may enter either this factor directly or state the scale as a %-value, so 0.5 or 50% will both cut the scale in half."
            )
        )
        self.text_c.SetMinSize((55, -1))
        self.text_c.SetToolTip(
            _(
                "Skew X - to skew the element in X-direction by alpha° you need either \n"
                "- to provide tan(alpha), i.e. 15° = 0.2679, 30° = 0.5774, 45° = 1.0 and so on...\n"
                "- or provide the angle as 15deg, 0.25turn, (like all other angles)\n"
                "In any case this value will then be represented as tan(alpha)"
            )
        )
        self.text_b.SetMinSize((55, -1))
        self.text_b.SetToolTip(
            _(
                "Skew Y - to skew the element in Y-direction by alpha° you need either \n"
                "- to provide tan(alpha), i.e. 15° = 0.2679, 30° = 0.5774, 45° = 1.0 and so on...\n"
                "- or provide the angle as 15deg, 0.25turn, (like all other angles)\n"
                "In any case this value will then be represented as tan(alpha)"
            )
        )
        self.text_e.SetMinSize((40, -1))
        self.text_e.SetToolTip(
            _(
                "Translate X - moves the element by this amount of mils in the X-direction; "
                "you may use 'real' distances when modifying this factor, i.e. 2in, 3cm, 50mm"
            )
        )
        self.text_f.SetMinSize((40, -1))
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
        col_sizer_1.Add(wx.StaticText(self, wx.ID_ANY, ""), wx.HORIZONTAL)
        col_sizer_1.Add(wx.StaticText(self, wx.ID_ANY, _("X:")), wx.HORIZONTAL)
        col_sizer_1.Add(wx.StaticText(self, wx.ID_ANY, _("Y:")), wx.HORIZONTAL)

        # Add some labels to make textboxes clearer to understand
        col_sizer_2 = wx.BoxSizer(wx.VERTICAL)
        col_sizer_2.Add(wx.StaticText(self, wx.ID_ANY, _("Scale")), wx.HORIZONTAL)
        col_sizer_2.Add(self.text_a, 0, wx.EXPAND, 0)  # Scale X
        col_sizer_2.Add(self.text_d, 0, wx.EXPAND, 0)  # Scale Y

        col_sizer_3 = wx.BoxSizer(wx.VERTICAL)
        col_sizer_3.Add(wx.StaticText(self, wx.ID_ANY, _("Skew")), wx.HORIZONTAL)
        col_sizer_3.Add(self.text_c, 0, wx.EXPAND, 0)  # Skew X
        col_sizer_3.Add(self.text_b, 0, wx.EXPAND, 0)  # Skew Y

        col_sizer_4 = wx.BoxSizer(wx.VERTICAL)
        col_sizer_4.Add(wx.StaticText(self, wx.ID_ANY, _("Translate")), wx.HORIZONTAL)
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

    def pane_show(self, *args):
        self.context.listen("emphasized", self.on_emphasized_elements_changed)
        self.context.listen("modified", self.on_modified_element)
        self.update_matrix_text()

    def pane_hide(self, *args):
        self.context.unlisten("emphasized", self.on_emphasized_elements_changed)
        self.context.unlisten("modified", self.on_modified_element)

    def on_modified_element(self, origin, *args):
        self.update_matrix_text()

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
        dx = self.context.device.length(
            dx,
            0,
            scale=scale,
            new_units=self.context.units_name,
            unitless=UNITS_PER_PIXEL,
        )
        dy = self.context.device.length(
            dy,
            1,
            scale=scale,
            new_units=self.context.units_name,
            unitless=UNITS_PER_PIXEL,
        )
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

    def on_translate_up_1(self, event=None):  # wxGlade: Navigation.<event_handler>
        dx = 0
        dy = self.context.jog_amount
        self._translate(dx, dy, -1)

    def on_translate_up_10(self, event=None):  # wxGlade: Navigation.<event_handler>
        dx = 0
        dy = self.context.jog_amount * 10
        self._translate(dx, dy, -10)

    def on_translate_left_1(self, event=None):  # wxGlade: Navigation.<event_handler>
        dx = self.context.jog_amount
        dy = 0
        self._translate(dx, dy, -1)

    def on_translate_left_10(self, event=None):  # wxGlade: Navigation.<event_handler>
        dx = self.context.jog_amount
        dy = 0
        self._translate(dx, dy, -10)

    def on_translate_right_1(self, event=None):  # wxGlade: Navigation.<event_handler>
        dx = self.context.jog_amount
        dy = 0
        self._translate(dx, dy, 1)

    def on_translate_right_10(self, event=None):  # wxGlade: Navigation.<event_handler>
        dx = self.context.jog_amount
        dy = 0
        self._translate(dx, dy, 10)

    def on_translate_down_1(self, event=None):  # wxGlade: Navigation.<event_handler>
        dx = 0
        dy = self.context.jog_amount
        self._translate(dx, dy, 1)

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
        return Angle.parse(stxt).as_radians

    @staticmethod
    def scaled_value(stxt):
        if stxt.endswith("%"):
            valu = float(stxt[:-1]) / 100.0
        else:
            valu = float(stxt)
        return valu

    def on_text_matrix(self):
        try:
            scale_x = self.scaled_value(self.text_a.GetValue())
            skew_x = self.skewed_value(self.text_c.GetValue())
            scale_y = self.scaled_value(self.text_d.GetValue())
            skew_y = self.skewed_value(self.text_b.GetValue())
            translate_x = float(Length(self.text_e.GetValue()))
            translate_y = float(Length(self.text_f.GetValue()))
            f = self.context.elements.first_element(emphasized=True)
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
            self.context.signal("refresh_scene")
        except ValueError:
            pass

        self.update_matrix_text()


class JogDistancePanel(wx.Panel):
    def __init__(self, *args, context=None, pane=False, **kwds):
        # begin wxGlade: JogDistancePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.text_jog_amount = TextCtrl(
            self,
            wx.ID_ANY,
            style=wx.TE_PROCESS_ENTER,
            value="10mm",
            check="length",
        )
        main_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Jog Distance:")), wx.VERTICAL
        )
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
            jog = self.context.device.length(
                self.text_jog_amount.GetValue(),
                new_units=self.context.units_name,
                unitless=UNITS_PER_PIXEL,
            )
        except ValueError:
            return
        self.context.jog_amount = str(jog)
        self.context.signal("jog_amount", str(jog))


class NavigationPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        pulse_and_move_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_panels_sizer = wx.BoxSizer(wx.HORIZONTAL)

        jogdistancepanel = JogDistancePanel(self, wx.ID_ANY, context=self.context)
        main_sizer.Add(jogdistancepanel, 0, wx.EXPAND, 0)

        navigationpanel = Jog(self, wx.ID_ANY, context=self.context)
        main_panels_sizer.Add(navigationpanel, 1, wx.EXPAND, 0)

        alignpanel = Drag(self, wx.ID_ANY, context=self.context)
        main_panels_sizer.Add(alignpanel, 1, wx.EXPAND, 0)

        transformpanel = Transform(self, wx.ID_ANY, context=self.context)

        main_panels_sizer.Add(transformpanel, 0, 0, 0)
        main_sizer.Add(main_panels_sizer, 0, wx.EXPAND, 0)

        short_pulse = PulsePanel(self, wx.ID_ANY, context=self.context)
        pulse_and_move_sizer.Add(short_pulse, 1, wx.EXPAND, 0)

        move_panel = MovePanel(self, wx.ID_ANY, context=self.context)
        pulse_and_move_sizer.Add(move_panel, 1, wx.EXPAND, 0)

        size_panel = SizePanel(self, wx.ID_ANY, context=self.context)
        pulse_and_move_sizer.Add(size_panel, 1, wx.EXPAND, 0)

        main_sizer.Add(pulse_and_move_sizer, 0, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.Layout()
        self.panels = [
            jogdistancepanel,
            navigationpanel,
            alignpanel,
            transformpanel,
            short_pulse,
            move_panel,
            size_panel,
        ]
        # end wxGlade

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
        super().__init__(598, 429, *args, **kwds)

        self.panel = NavigationPanel(self, wx.ID_ANY, context=self.context)
        self.add_module_delegate(self.panel)
        iconsize = get_default_icon_size()
        minw = (3 + 3 + 3) * iconsize + 150
        minh = (4 + 1) * iconsize + 170
        super().SetSizeHints(minW=minw, minH=minh)

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_move_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: Navigation.__set_properties
        self.SetTitle(_("Navigation"))

    @staticmethod
    def sub_register(kernel):

        kernel.register("wxpane/Navigation", register_panel_navigation)
        kernel.register(
            "button/control/Navigation",
            {
                "label": _("Navigation"),
                "icon": icons8_move_50,
                "tip": _("Opens Navigation Window"),
                "action": lambda v: kernel.console("window toggle Navigation\n"),
            },
        )

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    @staticmethod
    def submenu():
        return ("Editing", "Jog, Move and Transform")
