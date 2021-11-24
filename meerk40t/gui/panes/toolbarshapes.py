import wx
from wx import aui

from ..icons import (
    icons8_circle_50,
    icons8_cursor_50,
    icons8_oval_50,
    icons8_pencil_drawing_50,
    icons8_place_marker_50,
    icons8_polygon_50,
    icons8_polyline_50,
    icons8_rectangular_50,
    icons8_type_50,
    icons8_vector_50,
)

ID_TOOL_MOUSE = wx.NewId()
ID_TOOL_POSITION = wx.NewId()
ID_TOOL_OVAL = wx.NewId()
ID_TOOL_CIRCLE = wx.NewId()
ID_TOOL_POLYGON = wx.NewId()
ID_TOOL_POLYLINE = wx.NewId()
ID_TOOL_RECT = wx.NewId()
ID_TOOL_VECTOR = wx.NewId()
ID_TOOL_TEXT = wx.NewId()

_ = wx.GetTranslation


def register_shapes_tools(context, gui):
    toolbar = aui.AuiToolBar()

    toolbar.AddTool(ID_TOOL_MOUSE, _("Regular Scene"), icons8_cursor_50.GetBitmap())
    toolbar.Bind(
        wx.EVT_TOOL,
        lambda e: context("tool none\n"),
        id=ID_TOOL_MOUSE,
    )
    if context.has_feature("tool/position"):
        toolbar.AddTool(
            ID_TOOL_POSITION, _("Set Position"), icons8_place_marker_50.GetBitmap()
        )
        toolbar.Bind(
            wx.EVT_TOOL,
            lambda e: context("tool position\n"),
            id=ID_TOOL_POSITION,
        )
    if context.has_feature("tool/draw"):
        toolbar.AddTool(
            ID_TOOL_POSITION, _("Draw"), icons8_pencil_drawing_50.GetBitmap()
        )
        toolbar.Bind(
            wx.EVT_TOOL,
            lambda e: context("tool draw\n"),
            id=ID_TOOL_POSITION,
        )
    if context.has_feature("tool/oval"):
        toolbar.AddTool(
            ID_TOOL_OVAL,
            _("Oval"),
            icons8_oval_50.GetBitmap(),
        )

        toolbar.Bind(
            wx.EVT_TOOL,
            lambda e: context("tool oval\n"),
            id=ID_TOOL_OVAL,
        )
    if context.has_feature("tool/circle"):
        toolbar.AddTool(
            ID_TOOL_CIRCLE,
            _("Circle"),
            icons8_circle_50.GetBitmap(),
        )

        toolbar.Bind(
            wx.EVT_TOOL,
            lambda e: context("tool circle\n"),
            id=ID_TOOL_CIRCLE,
        )
    if context.has_feature("tool/polygon"):
        toolbar.AddTool(ID_TOOL_POLYGON, _("Polygon"), icons8_polygon_50.GetBitmap())

        toolbar.Bind(
            wx.EVT_TOOL,
            lambda e: context("tool polygon\n"),
            id=ID_TOOL_POLYGON,
        )
    if context.has_feature("tool/polyline"):
        toolbar.AddTool(ID_TOOL_POLYLINE, _("Polyline"), icons8_polyline_50.GetBitmap())
        toolbar.Bind(
            wx.EVT_TOOL,
            lambda e: context("tool polyline\n"),
            id=ID_TOOL_POLYLINE,
        )
    if context.has_feature("tool/rect"):
        toolbar.AddTool(ID_TOOL_RECT, _("Rectangle"), icons8_rectangular_50.GetBitmap())

        toolbar.Bind(
            wx.EVT_TOOL,
            lambda e: context("tool rect\n"),
            id=ID_TOOL_RECT,
        )
    if context.has_feature("tool/vector"):
        toolbar.AddTool(ID_TOOL_VECTOR, _("Vector"), icons8_vector_50.GetBitmap())

        toolbar.Bind(
            wx.EVT_TOOL,
            lambda e: context("tool vector\n"),
            id=ID_TOOL_VECTOR,
        )
    if context.has_feature("tool/text"):
        toolbar.AddTool(
            ID_TOOL_TEXT,
            _("Text"),
            icons8_type_50.GetBitmap(),
        )
        toolbar.Bind(
            wx.EVT_TOOL,
            lambda e: context("tool text\n"),
            id=ID_TOOL_TEXT,
        )

    toolbar.Create(gui)

    width = toolbar.ToolCount * 58
    pane = (
        aui.AuiPaneInfo()
        .Name("tool_toolbar")
        .Top()
        .ToolbarPane()
        .FloatingSize(width, 58)
        .Layer(1)
        .Caption(_("Tools"))
        .CaptionVisible(not context.pane_lock)
        .Hide()
    )
    pane.dock_proportion = width
    pane.control = toolbar
    pane.submenu = _("Toolbars")
    gui.on_pane_add(pane)
    context.register("pane/tool_toolbar", pane)

    return toolbar
