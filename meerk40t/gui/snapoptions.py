import wx
from wx import aui

from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


def register_panel_snapoptions(window, context):
    panel = SnapOptionPanel(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .MinSize(80, 125)
        .FloatingSize(120, 145)
        .Hide()
        .Caption(_("Snap-Options"))
        .CaptionVisible(not context.pane_lock)
        .Name("snapoptions")
    )
    pane.dock_proportion = 150
    pane.control = panel
    pane.submenu = "_40_" + _("Editing")

    window.on_pane_create(pane)
    context.register("pane/snapoptions", pane)


class SnapOptionPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        # Main Sizer
        sizer_snap = wx.BoxSizer(wx.VERTICAL)
        maxpoints = 75

        self.slider_visibility = wx.Slider(
            self, wx.ID_ANY, 1, 1, maxpoints, style=wx.SL_HORIZONTAL
        )
        self.slider_visibility.SetToolTip(
            _("Defines until which distance snap points will be highlighted")
        )

        self.check_snap_points = wx.CheckBox(self, wx.ID_ANY, _("Snap to element"))
        self.check_snap_points.SetToolTip(
            _("Shall the cursor snap to the next element point?")
        )
        self.slider_distance_points = wx.Slider(
            self, wx.ID_ANY, 1, 1, maxpoints, style=wx.SL_HORIZONTAL
        )
        self.slider_distance_points.SetToolTip(
            _(
                "Set the distance inside which the cursor will snap to the next element point"
            )
        )

        self.check_snap_grid = wx.CheckBox(self, wx.ID_ANY, _("Snap to Grid"))
        self.check_snap_grid.SetToolTip(
            _("Shall the cursor snap to the next grid intersection?")
        )
        self.slider_distance_grid = wx.Slider(
            self, wx.ID_ANY, 1, 1, maxpoints, style=wx.SL_HORIZONTAL
        )
        self.slider_distance_grid.SetToolTip(
            _(
                "Set the distance inside which the cursor will snap to the next grid intersection"
            )
        )

        # Visibility
        sizer_snap_visibility = wx.BoxSizer(wx.VERTICAL)
        sizer_sub_visible = wx.BoxSizer(wx.HORIZONTAL)
        label_vis = wx.StaticText(self, wx.ID_ANY, _("Overall visibility"))

        label_vis_dist = wx.StaticText(self, wx.ID_ANY, _("Distance"))
        sizer_sub_visible.Add(label_vis_dist, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_sub_visible.Add(self.slider_visibility, 1, wx.EXPAND, 0)

        sizer_snap_visibility.Add(label_vis, 0, wx.EXPAND, 0)
        sizer_snap_visibility.Add(sizer_sub_visible, 0, wx.EXPAND, 0)

        sizer_points = wx.BoxSizer(wx.VERTICAL)

        sizer_sub_points = wx.BoxSizer(wx.HORIZONTAL)
        label_pts_dist = wx.StaticText(self, wx.ID_ANY, _("Distance"))
        sizer_sub_points.Add(label_pts_dist, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_sub_points.Add(self.slider_distance_points, 1, wx.EXPAND, 0)

        sizer_points.Add(self.check_snap_points, 0, wx.EXPAND, 0)
        sizer_points.Add(sizer_sub_points, 0, wx.EXPAND, 0)

        sizer_grid = wx.BoxSizer(wx.VERTICAL)

        sizer_sub_grid = wx.BoxSizer(wx.HORIZONTAL)

        label_grid_dist = wx.StaticText(self, wx.ID_ANY, _("Distance"))
        sizer_sub_grid.Add(label_grid_dist, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_sub_grid.Add(self.slider_distance_grid, 1, wx.EXPAND, 0)

        sizer_grid.Add(self.check_snap_grid, 0, wx.EXPAND, 0)
        sizer_grid.Add(sizer_sub_grid, 0, wx.EXPAND, 0)

        sizer_snap.Add(sizer_snap_visibility, 0, wx.ALL | wx.EXPAND, 0)
        sizer_snap.Add(sizer_points, 0, wx.ALL | wx.EXPAND, 0)
        sizer_snap.Add(sizer_grid, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_snap)
        sizer_snap.Fit(self)

        self.position_aspect_ratio = True
        self.position_x = 0.0
        self.position_y = 0.0
        self.position_h = 0.0
        self.position_w = 0.0
        # Additionally defined in wxmmain and attraction widget
        self.context.setting(bool, "snap_grid", True)
        self.context.setting(bool, "snap_points", False)
        self.context.setting(int, "show_attract_len", 45)
        self.context.setting(int, "action_attract_len", 20)
        self.context.setting(int, "grid_attract_len", 15)
        # Bindings
        self.Bind(wx.EVT_CHECKBOX, self.on_checkbox_grid, self.check_snap_grid)
        self.Bind(wx.EVT_CHECKBOX, self.on_checkbox_points, self.check_snap_points)
        self.Bind(wx.EVT_SLIDER, self.on_slider_grid, self.slider_distance_grid)
        self.Bind(wx.EVT_SLIDER, self.on_slider_points, self.slider_distance_points)
        self.Bind(wx.EVT_SLIDER, self.on_slider_visibility, self.slider_visibility)

    def on_checkbox_grid(self, event):
        state = self.check_snap_grid.GetValue()
        self.context.snap_grid = state
        self.context.signal("snap_grid", state)
        self.slider_distance_grid.Enable(state)

    def on_checkbox_points(self, event):
        state = self.check_snap_points.GetValue()
        self.context.snap_points = state
        self.context.signal("snap_points", state)
        self.slider_distance_points.Enable(state)

    def update_slider_tooltip(self, control):
        state = control.GetValue()
        ttip = control.GetToolTipText()
        lines = ttip.split("\n")
        if len(lines) > 1:
            lines = lines[:-1]
        lines.append(_("Current Value: {value} pixel").format(value=state))
        ttip = "\n".join(lines)
        control.SetToolTip(ttip)

    def on_slider_visibility(self, event):
        state = self.slider_visibility.GetValue()
        self.context.show_attract_len = state
        self.context.signal("show_attract_len", state)
        self.slider_visibility.Enable(state)
        self.update_slider_tooltip(self.slider_visibility)

    def on_slider_grid(self, event):
        state = self.slider_distance_grid.GetValue()
        self.context.grid_attract_len = state
        self.context.signal("grid_attract_len", state)
        self.update_slider_tooltip(self.slider_distance_grid)

    def on_slider_points(self, event):
        state = self.slider_distance_points.GetValue()
        self.context.action_attract_len = state
        self.context.signal("action_attract_len", state)
        self.update_slider_tooltip(self.slider_distance_points)

    def update_values(self):
        if self.check_snap_grid.GetValue != self.context.snap_grid:
            self.check_snap_grid.SetValue(self.context.snap_grid)
        if self.check_snap_points.GetValue() != self.context.snap_points:
            self.check_snap_points.SetValue(self.context.snap_points)
        if self.slider_distance_grid.GetValue() != self.context.grid_attract_len:
            self.slider_distance_grid.SetValue(self.context.grid_attract_len)
        if self.slider_distance_points.GetValue() != self.context.action_attract_len:
            self.slider_distance_points.SetValue(self.context.action_attract_len)
        if self.slider_visibility.GetValue() != self.context.show_attract_len:
            self.slider_visibility.SetValue(self.context.show_attract_len)
        self.update_slider_tooltip(self.slider_distance_grid)
        self.update_slider_tooltip(self.slider_distance_points)
        self.update_slider_tooltip(self.slider_visibility)
        self.slider_visibility.Enable(self.context.show_attract_len)
        self.slider_distance_points.Enable(self.context.snap_points)
        self.slider_distance_grid.Enable(self.context.snap_grid)

    @signal_listener("snap_points")
    @signal_listener("snap_grid")
    @signal_listener("grid_attract_len")
    @signal_listener("action_attract_len")
    @signal_listener("show_attract_len")
    def value_update(self, origin, *args):
        self.update_values()

    def pane_show(self, *args):
        self.update_values()

    def pane_hide(self, *args):
        pass
