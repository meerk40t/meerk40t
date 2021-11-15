import wx
from wx import aui

from ..icons import (
    icons8_comments_50,
    icons8_console_50,
    icons8_fantasy_50,
    icons8_laser_beam_52,
    icons8_laser_beam_hazard2_50,
    icons8_opened_folder_50,
    icons8_save_50,
)

ID_ADD_FILE = wx.NewId()
ID_OPEN = wx.NewId()
ID_SAVE = wx.NewId()
ID_JOB = wx.NewId()
ID_SIM = wx.NewId()
ID_NOTES = wx.NewId()
ID_CONSOLE = wx.NewId()
ID_RASTER = wx.NewId()

_ = wx.GetTranslation


def register_project_tools(context, gui):
    toolbar = aui.AuiToolBar()
    toolbar.AddTool(
        ID_OPEN,
        _("Open"),
        icons8_opened_folder_50.GetBitmap(),
        kind=wx.ITEM_NORMAL,
        short_help_string=_("Opens new project"),
    )
    toolbar.AddTool(
        ID_SAVE,
        _("Save"),
        icons8_save_50.GetBitmap(),
        kind=wx.ITEM_NORMAL,
        short_help_string=_("Saves a project to disk"),
    )
    toolbar.AddSeparator()
    toolbar.Bind(wx.EVT_TOOL, lambda v: context("dialog_load\n"), id=ID_OPEN)
    toolbar.Bind(wx.EVT_TOOL, lambda v: context("dialog_save\n"), id=ID_SAVE)

    if context.has_feature("window/ExecuteJob"):
        toolbar.AddTool(
            ID_JOB,
            _("Execute Job"),
            icons8_laser_beam_52.GetBitmap(),
            kind=wx.ITEM_NORMAL,
            short_help_string=_("Execute the current laser project"),
        )
        toolbar.Bind(
            wx.EVT_TOOL,
            lambda v: context("window toggle ExecuteJob 0\n"),
            id=ID_JOB,
        )
    if context.has_feature("window/Simulation"):
        toolbar.AddTool(
            ID_SIM,
            _("Simulate"),
            icons8_laser_beam_hazard2_50.GetBitmap(),
            kind=wx.ITEM_NORMAL,
            short_help_string=_("Simulate the current laser job"),
        )

        def open_simulator(v=None):
            with wx.BusyInfo(_("Preparing simulation...")):
                context(
                    "plan0 copy preprocess validate blob preopt optimize\nwindow toggle Simulation 0\n"
                ),

        toolbar.Bind(
            wx.EVT_TOOL,
            open_simulator,
            id=ID_SIM,
        )
    if context.has_feature("window/RasterWizard"):
        toolbar.AddTool(
            ID_RASTER,
            _("RasterWizard"),
            icons8_fantasy_50.GetBitmap(),
            kind=wx.ITEM_NORMAL,
            short_help_string=_("Run RasterWizard"),
        )
        toolbar.Bind(
            wx.EVT_TOOL,
            lambda v: context("window toggle RasterWizard\n"),
            id=ID_RASTER,
        )
    toolbar.AddSeparator()
    if context.has_feature("window/Notes"):
        toolbar.AddTool(
            ID_NOTES,
            _("Notes"),
            icons8_comments_50.GetBitmap(),
            kind=wx.ITEM_NORMAL,
            short_help_string=_("Open Notes Window"),
        )
        toolbar.Bind(
            wx.EVT_TOOL,
            lambda v: context("window toggle Notes\n"),
            id=ID_NOTES,
        )
    if context.has_feature("window/Console"):
        toolbar.AddTool(
            ID_CONSOLE,
            _("Console"),
            icons8_console_50.GetBitmap(),
            kind=wx.ITEM_NORMAL,
            short_help_string=_("Open Console Window"),
        )
        toolbar.Bind(
            wx.EVT_TOOL,
            lambda v: context("window toggle Console\n"),
            id=ID_CONSOLE,
        )
    toolbar.Create(gui)

    width = toolbar.ToolCount * 58
    pane = (
        aui.AuiPaneInfo()
        .Name("project_toolbar")
        .Top()
        .ToolbarPane()
        .FloatingSize(width, 58)
        .Layer(1)
        .Caption(_("Project"))
        .CaptionVisible(not context.pane_lock)
        .Hide()
    )
    pane.dock_proportion = width
    pane.control = toolbar
    pane.submenu = _("Toolbars")
    gui.on_pane_add(pane)
    context.register("pane/project_toolbar", pane)

    return toolbar
