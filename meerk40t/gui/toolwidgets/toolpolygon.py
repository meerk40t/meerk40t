import wx

from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Path, Polygon
from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME


class PolygonTool(ToolWidget):
    """
    Polygon Drawing Tool.

    Adds polygon with clicks.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.point_series = []
        self.mouse_position = None

    def process_draw(self, gc: wx.GraphicsContext):
        if self.point_series:
            gc.SetPen(self.pen)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            points = list(self.point_series)
            if self.mouse_position is not None:
                points.append(self.mouse_position)
            points.append(points[0])
            gc.DrawLines(points)

    def event(self, window_pos=None, space_pos=None, event_type=None):
        response = RESPONSE_CHAIN
        if event_type == "leftclick":
            self.point_series.append((space_pos[0], space_pos[1]))
            self.scene.tool_active = True
            response = RESPONSE_CONSUME
        elif event_type == "rightdown":
            self.scene.tool_active = False
            self.point_series = []
            self.mouse_position = None
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        elif event_type == "hover":
            self.mouse_position = space_pos[0], space_pos[1]
            if self.point_series:
                self.scene.request_refresh()
        elif event_type == "doubleclick":
            polyline = Polygon(*self.point_series, stroke="blue", stroke_width=1000)
            self.scene.context.elements.add_elem(polyline, classify=True)
            self.scene.tool_active = False
            self.point_series = []
            self.mouse_position = None
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        elif event_type == "lost":
            self.scene.tool_active = False
            self.point_series = []
            self.mouse_position = None
        return response
