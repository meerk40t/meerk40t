import wx

from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Path, Point


class DrawTool(ToolWidget):
    """
    Draw Tool adds paths that are clicked and drawn within the scene.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.preferred_length = 50
        self.series = None
        self.last_position = None

    def process_draw(self, gc: wx.GraphicsContext):
        if self.series is not None and len(self.series) > 1:
            gc.SetPen(self.pen)
            gc.StrokeLines(self.series)

    def add_point(self, point):
        if len(self.series):
            last = self.series[-1]
            if Point.distance(last, point) < self.preferred_length:
                return
        self.series.append(point)

    def event(
        self, window_pos=None, space_pos=None, event_type=None, modifiers=None, **kwargs
    ):
        # We don't set tool_active here, as this can't be properly honored...
        # And we don't care about nearest_snap either...
        response = RESPONSE_CHAIN
        if self.series is None:
            self.series = []
        if event_type == "leftdown":
            self.pen = wx.Pen()
            elements = self.scene.context.elements
            self.pen.SetColour(wx.Colour(swizzlecolor(elements.default_stroke)))
            try:
                self.pen.SetWidth(elements.default_strokewidth)
            except TypeError:
                self.pen.SetWidth(int(elements.default_strokewidth))
            self.add_point(space_pos[:2])
            response = RESPONSE_CONSUME
        elif event_type == "move":
            if self.series is None:
                return RESPONSE_DROP
            self.add_point(space_pos[:2])
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            self.series = None
            if self.scene.pane.tool_active:
                self.scene.pane.tool_active = False
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
        elif event_type == "leftup":
            try:
                t = Path()
                t.move(self.series[0])
                for m in self.series:
                    t.line(m)
                elements = self.scene.context.elements
                node = elements.elem_branch.add(
                    path=t,
                    type="elem path",
                    stroke_width=elements.default_strokewidth,
                    stroke=elements.default_stroke,
                    fill=elements.default_fill,
                )
                if elements.classify_new:
                    elements.classify([node])
                self.notify_created(node)
            except IndexError:
                pass
            self.series = None
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        return response
