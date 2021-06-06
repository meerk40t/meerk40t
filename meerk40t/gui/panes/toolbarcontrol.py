import wx
from wx import aui

ID_MAIN_TOOLBAR = wx.NewId()
ID_ADD_FILE = wx.NewId()
ID_OPEN = wx.NewId()

ID_SAVE = wx.NewId()
ID_NAV = wx.NewId()
ID_USB = wx.NewId()
ID_CONTROLLER = wx.NewId()
ID_CONFIGURATION = wx.NewId()
ID_DEVICES = wx.NewId()
ID_CAMERA = wx.NewId()
ID_CAMERA1 = wx.NewId()
ID_CAMERA2 = wx.NewId()
ID_CAMERA3 = wx.NewId()
ID_CAMERA4 = wx.NewId()
ID_CAMERA5 = wx.NewId()
ID_JOB = wx.NewId()
ID_SIM = wx.NewId()
ID_PAUSE = wx.NewId()
ID_STOP = wx.NewId()

ID_SPOOLER = wx.NewId()
ID_KEYMAP = wx.NewId()
ID_SETTING = wx.NewId()
ID_NOTES = wx.NewId()
ID_OPERATIONS = wx.NewId()
ID_CONSOLE = wx.NewId()
ID_ROTARY = wx.NewId()
ID_RASTER = wx.NewId()

from ..icons import (
    icons8_camera_50,
    icons8_connected_50,
    icons8_move_50,
    icons8_route_50,
)

_ = wx.GetTranslation


def register_control_tools(context, gui):
    toolbar = aui.AuiToolBar()

    toolbar.AddTool(
        ID_NAV,
        _("Navigation"),
        icons8_move_50.GetBitmap(),
        kind=wx.ITEM_NORMAL,
        short_help_string=_("Opens new project"),
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda v: context("window toggle Navigation\n"),
        id=ID_NAV,
    )
    if context.has_feature("modifier/Camera"):
        toolbar.AddTool(
            ID_CAMERA,
            _("Camera"),
            icons8_camera_50.GetBitmap(),
            kind=wx.ITEM_NORMAL,
            short_help_string=_("Opens Camera Window"),
        )
        toolbar.Bind(wx.EVT_TOOL, gui.on_camera_click, id=ID_CAMERA)
        # self.Bind(
        #     RB.EVT_RIBBONBUTTONBAR_DROPDOWN_CLICKED,
        #     self.on_camera_dropdown,
        #     id=ID_CAMERA,
        # )
        # self.Bind(wx.EVT_MENU, self.on_camera_click, id=ID_CAMERA1)
        # self.Bind(wx.EVT_MENU, self.on_camera_click, id=ID_CAMERA2)
        # self.Bind(wx.EVT_MENU, self.on_camera_click, id=ID_CAMERA3)
        # self.Bind(wx.EVT_MENU, self.on_camera_click, id=ID_CAMERA4)
        # self.Bind(wx.EVT_MENU, self.on_camera_click, id=ID_CAMERA5)

    toolbar.AddTool(
        ID_SPOOLER,
        _("Spooler"),
        icons8_route_50.GetBitmap(),
        kind=wx.ITEM_NORMAL,
        short_help_string=_("Opens Spooler Window"),
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda v: context("window toggle JobSpooler\n"),
        id=ID_SPOOLER,
    )
    toolbar.AddTool(
        ID_CONTROLLER,
        _("Controller"),
        icons8_connected_50.GetBitmap(),
        kind=wx.ITEM_NORMAL,
        short_help_string=_("Opens Controller Window"),
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda v: context("window toggle -o Controller\n"),
        id=ID_CONTROLLER,
    )

    toolbar.Create(gui)

    pane = (
        aui.AuiPaneInfo()
            .Name("control_toolbar")
            .Top()
            .ToolbarPane()
            .FloatingSize(230, 58)
            .Layer(1)
            .Caption(_("Control"))
            .CaptionVisible(not context.pane_lock)
            .Hide()
    )
    pane.dock_proportion = 40
    pane.control = toolbar
    pane.submenu = _("Toolbars")
    gui.on_pane_add(pane)
    context.register("pane/control_toolbar", pane)

    return toolbar

