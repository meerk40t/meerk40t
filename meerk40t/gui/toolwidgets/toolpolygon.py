import wx

from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Path, Polygon


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
            gc.SetPen(wx.BLUE_PEN)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            points = list(self.point_series)
            if self.mouse_position is not None:
                points.append(self.mouse_position)
            points.append(points[0])
            gc.DrawLines(points)

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if event_type == "leftclick":
            self.point_series.append((space_pos[0], space_pos[1]))
        elif event_type == "rightdown":
            self.point_series = []
            self.mouse_position = None
            self.scene.context.signal("refresh_scene", self.scene.name)
        elif event_type == "hover":
            self.mouse_position = space_pos[0], space_pos[1]
            if self.point_series:
                self.scene.context.signal("refresh_scene", self.scene.name)
        elif event_type == "doubleclick":
            polyline = Polygon(*self.point_series, stroke="blue")
            t = Path(polyline)
            if len(t) != 0:
                self.scene.context.elements.add_elem(t, classify=True)
            self.point_series = []
            self.mouse_position = None
