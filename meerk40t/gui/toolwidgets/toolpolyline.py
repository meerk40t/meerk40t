import wx

from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Polyline
from meerk40t.gui.laserrender import swizzlecolor


class PolylineTool(ToolWidget):
    """
    Polyline Drawing Tool.

    Adds polylines with clicks.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.point_series = []
        self.mouse_position = None

    def process_draw(self, gc: wx.GraphicsContext):
        if self.point_series:
            if self.scene.default_stroke is None:
                self.pen.SetColour(wx.BLUE)
            else:
                self.pen.SetColour(wx.Colour(swizzlecolor(self.scene.default_stroke)))
            gc.SetPen(self.pen)
            if self.scene.default_fill is None:
                gc.SetBrush(wx.TRANSPARENT_BRUSH)
            else:
                gc.SetBrush(wx.Brush(wx.Colour(swizzlecolor(self.scene.default_fill)), wx.BRUSHSTYLE_SOLID))
            points = list(self.point_series)
            if self.mouse_position is not None:
                points.append(self.mouse_position)
            gc.DrawLines(points)

    def event(self, window_pos=None, space_pos=None, event_type=None):
        response = RESPONSE_CHAIN
        if event_type == "leftclick":
            self.scene.tool_active = True
            self.point_series.append((space_pos[0], space_pos[1]))
            response = RESPONSE_CONSUME
        elif event_type == "rightdown":
            self.point_series = []
            self.mouse_position = None
            self.scene.tool_active = False
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        elif event_type == "hover":
            self.mouse_position = space_pos[0], space_pos[1]
            if self.point_series:
                self.scene.request_refresh()
            response = RESPONSE_CHAIN
        elif event_type == "doubleclick":
            polyline = Polyline(*self.point_series, stroke="blue", stroke_width=1000)
            elements = self.scene.context.elements
            node = elements.elem_branch.add(shape=polyline, type="elem polyline")
            if not self.scene.default_stroke is None:
                node.stroke = self.scene.default_stroke
            if not self.scene.default_fill is None:
                node.fill = self.scene.default_fill

            elements.classify([node])
            self.scene.tool_active = False
            self.point_series = []
            self.mouse_position = None
            self.notify_created()
            response = RESPONSE_CONSUME
        elif event_type == "lost":
            self.scene.tool_active = False
            self.point_series = []
            self.mouse_position = None
        return response
