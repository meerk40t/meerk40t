import wx
from wx import aui

from ..icons import (
    icons8_align_left_50,
    icons8_align_right_50,
    icons8_align_top_50,
    icons8_align_bottom_50,
    icons_centerize,
    icons_evenspace_vert,
    icons_evenspace_horiz,
)


ID_ALIGN_LEFT = wx.NewId()
ID_ALIGN_RIGHT = wx.NewId()
ID_ALIGN_TOP = wx.NewId()
ID_ALIGN_BOTTOM = wx.NewId()
ID_ALIGN_CENTER = wx.NewId()

ID_ALIGN_SPACE_V = wx.NewId()
ID_ALIGN_SPACE_H = wx.NewId()

_ = wx.GetTranslation


def register_align_tools(context, gui):
    toolbar = aui.AuiToolBar()

    toolbar.AddTool(ID_ALIGN_LEFT, _("Align Left"), icons8_align_left_50.GetBitmap())
    toolbar.AddTool(ID_ALIGN_RIGHT, _("Align Right"), icons8_align_right_50.GetBitmap())
    toolbar.AddTool(ID_ALIGN_TOP, _("Align Top"), icons8_align_top_50.GetBitmap())
    toolbar.AddTool(
        ID_ALIGN_BOTTOM, _("Align Bottom"), icons8_align_bottom_50.GetBitmap()
    )
    toolbar.AddTool(ID_ALIGN_CENTER, _("Align Center"), icons_centerize.GetBitmap())
    toolbar.AddTool(
        ID_ALIGN_SPACE_V, _("Space Vertical"), icons_evenspace_vert.GetBitmap()
    )
    toolbar.AddTool(
        ID_ALIGN_SPACE_H,
        _("Space Horizontal"),
        icons_evenspace_horiz.GetBitmap(),
    )

    toolbar.Bind(
        wx.EVT_TOOL,
        lambda e: context("align left\n"),
        id=ID_ALIGN_LEFT,
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda e: context("align right\n"),
        id=ID_ALIGN_RIGHT,
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda e: context("align top\n"),
        id=ID_ALIGN_TOP,
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda e: context("align bottom\n"),
        id=ID_ALIGN_BOTTOM,
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda e: context("align center\n"),
        id=ID_ALIGN_CENTER,
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda e: context("align spacev\n"),
        id=ID_ALIGN_SPACE_V,
    )
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda e: context("align spaceh\n"),
        id=ID_ALIGN_SPACE_H,
    )

    toolbar.Create(gui)

    pane = (
        aui.AuiPaneInfo()
        .Name("align_toolbar")
        .Top()
        .ToolbarPane()
        .FloatingSize(430, 58)
        .Layer(1)
        .Caption(_("Alignment"))
        .CaptionVisible(not context.pane_lock)
        .Hide()
    )
    pane.dock_proportion = 430
    pane.control = toolbar
    pane.submenu = _("Toolbars")
    gui.on_pane_add(pane)
    context.register("pane/align_toolbar", pane)

    return toolbar
