import wx
from wx import aui

from ..icons import icons8_flip_horizontal_50, icons8_flip_vertical_50

ID_FLIP_HORIZONTAL = wx.NewId()
ID_FLIP_VERTICAL = wx.NewId()

_ = wx.GetTranslation


def register_modify_tools(context, gui):
    toolbar = aui.AuiToolBar()

    toolbar.AddTool(
        ID_FLIP_HORIZONTAL,
        _("Mirror Horizontal"),
        icons8_flip_horizontal_50.GetBitmap(),
        kind=wx.ITEM_NORMAL,
        short_help_string=_("Mirror Selected Horizontally"),
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda v: context("scale 1 -1\n"),
        id=ID_FLIP_HORIZONTAL,
    )

    toolbar.AddTool(
        ID_FLIP_VERTICAL,
        _("Flip Vertical"),
        icons8_flip_vertical_50.GetBitmap(),
        kind=wx.ITEM_NORMAL,
        short_help_string=_("Flip Selected Vertically"),
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda v: context("scale -1 1\n"),
        id=ID_FLIP_VERTICAL,
    )

    toolbar.Create(gui)

    pane = (
        aui.AuiPaneInfo()
        .Name("modify_toolbar")
        .Top()
        .ToolbarPane()
        .FloatingSize(145, 58)
        .Layer(1)
        .Caption(_("Modification"))
        .CaptionVisible(not context.pane_lock)
        .Hide()
    )
    pane.dock_proportion = 145
    pane.control = toolbar
    pane.submenu = _("Toolbars")
    gui.on_pane_add(pane)
    gui.context.register("pane/modify_toolbar", pane)

    return toolbar
