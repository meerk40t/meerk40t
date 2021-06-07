import wx
from wx import aui

from ..icons import (
    icons8_place_marker_50,
    icons8_oval_50,
    icons8_circle_50,
    icons8_polygon_50,
    icons8_polyline_50,
    icons8_rectangular_50,
    icons8_type_50,
)


ID_TOOL_POSITION = wx.NewId()
ID_TOOL_OVAL = wx.NewId()
ID_TOOL_CIRCLE = wx.NewId()
ID_TOOL_POLYGON = wx.NewId()
ID_TOOL_POLYLINE = wx.NewId()
ID_TOOL_RECT = wx.NewId()
ID_TOOL_TEXT = wx.NewId()

_ = wx.GetTranslation


def register_shapes_tools(context, gui):
    tool = aui.AuiToolBar()

    tool.AddTool(
        ID_TOOL_POSITION, _("Set Position"), icons8_place_marker_50.GetBitmap()
    )
    tool.AddTool(
        ID_TOOL_OVAL,
        _("Oval"),
        icons8_oval_50.GetBitmap(),
    )
    tool.AddTool(
        ID_TOOL_CIRCLE,
        _("Circle"),
        icons8_circle_50.GetBitmap(),
    )
    tool.AddTool(ID_TOOL_POLYGON, _("Polygon"), icons8_polygon_50.GetBitmap())
    tool.AddTool(ID_TOOL_POLYLINE, _("Polyline"), icons8_polyline_50.GetBitmap())
    tool.AddTool(ID_TOOL_RECT, _("Rectangle"), icons8_rectangular_50.GetBitmap())
    tool.AddTool(
        ID_TOOL_TEXT,
        _("Text"),
        icons8_type_50.GetBitmap(),
    )

    tool.Bind(
        wx.EVT_TOOL,
        lambda e: context("tool position\n"),
        id=ID_TOOL_POSITION,
    )
    tool.Bind(
        wx.EVT_TOOL,
        lambda e: context("tool oval\n"),
        id=ID_TOOL_OVAL,
    )
    tool.Bind(
        wx.EVT_TOOL,
        lambda e: context("tool circle\n"),
        id=ID_TOOL_CIRCLE,
    )
    tool.Bind(
        wx.EVT_TOOL,
        lambda e: context("tool polygon\n"),
        id=ID_TOOL_POLYGON,
    )
    tool.Bind(
        wx.EVT_TOOL,
        lambda e: context("tool polyline\n"),
        id=ID_TOOL_POLYLINE,
    )
    tool.Bind(
        wx.EVT_TOOL,
        lambda e: context("tool rect\n"),
        id=ID_TOOL_RECT,
    )
    tool.Bind(
        wx.EVT_TOOL,
        lambda e: context("tool text\n"),
        id=ID_TOOL_TEXT,
    )

    tool.Create(gui)

    pane = (
        aui.AuiPaneInfo()
        .Name("tool_toolbar")
        .Top()
        .ToolbarPane()
        .FloatingSize(430, 58)
        .Layer(1)
        .Caption(_("Tools"))
        .CaptionVisible(not context.pane_lock)
        .Hide()
    )
    pane.dock_proportion = 430
    pane.control = tool
    pane.submenu = _("Toolbars")
    gui.on_pane_add(pane)
    context.register("pane/tool_toolbar", pane)

    return tool
