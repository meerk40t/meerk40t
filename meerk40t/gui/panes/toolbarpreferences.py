import wx
from wx import aui

from ..icons import (
    icons8_administrative_tools_50,
    icons8_computer_support_50,
    icons8_keyboard_50,
    icons8_manager_50,
    icons8_roll_50,
)

ID_CONFIGURATION = wx.NewId()
ID_DEVICES = wx.NewId()
ID_KEYMAP = wx.NewId()
ID_SETTING = wx.NewId()
ID_ROTARY = wx.NewId()

_ = wx.GetTranslation


def register_preferences_tools(context, gui):
    toolbar = aui.AuiToolBar()

    toolbar.AddTool(
        ID_DEVICES,
        _("Devices"),
        icons8_manager_50.GetBitmap(),
        kind=wx.ITEM_NORMAL,
        short_help_string=_("Opens Device Manager"),
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda v: context("window toggle DeviceManager\n"),
        id=ID_DEVICES,
    )

    toolbar.AddTool(
        ID_CONFIGURATION,
        _("Config"),
        icons8_computer_support_50.GetBitmap(),
        kind=wx.ITEM_NORMAL,
        short_help_string=_("Opens Configuration Window"),
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda v: context("window toggle Configuration\n"),
        id=ID_CONFIGURATION,
    )

    toolbar.AddTool(
        ID_SETTING,
        _("Preferences"),
        icons8_administrative_tools_50.GetBitmap(),
        kind=wx.ITEM_NORMAL,
        short_help_string=_("Opens Preferences Window"),
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda v: context("window toggle Preferences\n"),
        id=ID_SETTING,
    )

    toolbar.AddTool(
        ID_KEYMAP,
        _("Keymap"),
        icons8_keyboard_50.GetBitmap(),
        kind=wx.ITEM_NORMAL,
        short_help_string=_("Opens Keymap Window"),
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda v: context("window toggle Keymap\n"),
        id=ID_KEYMAP,
    )
    toolbar.AddTool(
        ID_ROTARY,
        _("Rotary"),
        icons8_roll_50.GetBitmap(),
        kind=wx.ITEM_NORMAL,
        short_help_string=_("Opens Rotary Window"),
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda v: context("window -p rotary/1 toggle Rotary\n"),
        id=ID_ROTARY,
    )

    toolbar.Create(gui)

    pane = (
        aui.AuiPaneInfo()
        .Name("preferences_toolbar")
        .Top()
        .ToolbarPane()
        .FloatingSize(290, 58)
        .Layer(1)
        .Caption(_("Configuration"))
        .CaptionVisible(not context.pane_lock)
        .Hide()
    )
    pane.dock_proportion = 290
    pane.control = toolbar
    pane.submenu = _("Toolbars")
    gui.on_pane_add(pane)
    gui.context.register("pane/preferences_toolbar", pane)

    return toolbar
