import wx
from wx import aui

from meerk40t.core.units import ViewPort, Length
from meerk40t.gui.icons import icons8_lock_50, icons8_padlock_50

_ = wx.GetTranslation


def register_panel_snapoptions(window, context):
    panel = SnapOptionPanel(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .MinSize(75, 50)
        .FloatingSize(150, 75)
        .Hide()
        .Caption(_("Snap-Options"))
        .CaptionVisible(not context.pane_lock)
        .Name("snapoptions")
    )
    pane.dock_proportion = 150
    pane.dock_proportion = 150
    pane.control = panel
    pane.submenu = _("Editing")

    window.on_pane_add(pane)
    context.register("pane/snapoptions", pane)


class SnapOptionPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        sizer_snap = wx.BoxSizer(wx.VERTICAL)

        sizer_snap_1 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Overall visibility")), wx.VERTICAL)
        sizer_snap.Add(sizer_snap_1, 0, wx.EXPAND, 0)

        label_5 = wx.StaticText(self, wx.ID_ANY, _("Overall visibility"))
        sizer_snap_1.Add(label_5, 0, 0, 0)

        self.slider_distance_points = wx.Slider(self, wx.ID_ANY, 1, 1, 50, style=wx.SL_HORIZONTAL | wx.SL_LABEL)
        self.slider_distance_points.SetToolTip(_("Set the distance inside which the cursor will snap to the next element point"))
        sizer_snap_1.Add(self.slider_distance_points, 1, wx.EXPAND, 0)

        sizer_snap_2 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Snap to element")), wx.VERTICAL)
        sizer_snap.Add(sizer_snap_2, 0, wx.EXPAND, 0)

        sizer_h1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_snap_2.Add(sizer_h1, 1, wx.EXPAND, 0)

        self.check_snap_points = wx.CheckBox(self, wx.ID_ANY, _("Snap to element"))
        self.check_snap_points.SetToolTip(_("Shall the cursor snap to the next element point?"))
        sizer_h1.Add(self.check_snap_points, 0, 0, 0)

        sizer_h2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_snap_2.Add(sizer_h2, 1, wx.EXPAND, 0)

        label_4 = wx.StaticText(self, wx.ID_ANY, _("Distance"))
        sizer_h2.Add(label_4, 0, 0, 0)

        self.slider_visibility = wx.Slider(self, wx.ID_ANY, 1, 1, 50, style=wx.SL_HORIZONTAL | wx.SL_LABEL)
        self.slider_visibility.SetToolTip(_("Defines until which distance snap points will be highlighted"))
        sizer_h2.Add(self.slider_visibility, 1, wx.EXPAND, 0)

        sizer_snap_3 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Snap to grid")), wx.VERTICAL)
        sizer_snap.Add(sizer_snap_3, 0, wx.EXPAND, 0)

        sizer_h3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_snap_3.Add(sizer_h3, 1, wx.EXPAND, 0)

        self.check_snap_grid = wx.CheckBox(self, wx.ID_ANY, _("Snap to Grid"))
        self.check_snap_grid.SetToolTip(_("Shall the cursor snap to the next grid intersection?"))
        sizer_h3.Add(self.check_snap_grid, 0, 0, 0)

        sizer_h4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_snap_3.Add(sizer_h4, 1, wx.EXPAND, 0)

        label_3 = wx.StaticText(self, wx.ID_ANY, _("Distance"))
        sizer_h4.Add(label_3, 0, 0, 0)

        self.slider_distance_grid = wx.Slider(self, wx.ID_ANY, 1, 1, 50, style=wx.SL_HORIZONTAL | wx.SL_LABEL)
        self.slider_distance_grid.SetToolTip(_("Set the distance inside which the cursor will snap to the next grid intersection"))
        sizer_h4.Add(self.slider_distance_grid, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_snap)
        sizer_snap.Fit(self)


        self.position_aspect_ratio = True
        self.position_x = 0.0
        self.position_y = 0.0
        self.position_h = 0.0
        self.position_w = 0.0
        self.context.setting(bool, "snap_grid", True)
        self.context.setting(bool, "snap_points", True)
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

    def on_checkbox_points(self, event):
        state = self.check_snap_points.GetValue()
        self.context.snap_points = state

    def on_slider_visibility(self, event):
        state = self.slider_visibility.GetValue()
        self.context.show_attract_len = state

    def on_slider_grid(self, event):
        state = self.slider_distance_grid.GetValue()
        self.context.grid_attract_len = state

    def on_slider_points(self, event):
        state = self.slider_distance_points.GetValue()
        self.context.action_attract_len = state

    def update_values(self):
        self.check_snap_grid.SetValue(self.context.snap_grid)
        self.check_snap_points.SetValue(self.context.snap_points)
        self.slider_distance_grid.SetValue(self.context.grid_attract_len)
        self.slider_distance_points.SetValue(self.context.action_attract_len)
        self.slider_visibility.SetValue(self.context.show_attract_len)

    def pane_show(self, *args):
        self.update_values()

    def pane_hide(self, *args):
        pass

