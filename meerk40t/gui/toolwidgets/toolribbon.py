import math

import wx

from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Path, Point


class RibbonTool(ToolWidget):
    """
    Ribbon Tool draws new segments by animating some click and press locations.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.preferred_length = 50
        self.last_position = None
        self.track_object = [0, 0]
        self.velocity = [0, 0]
        self.series = []
        self.stop = False
        self.pos = 0

    def process_draw(self, gc: wx.GraphicsContext):
        elements = self.scene.context.elements
        if elements.default_stroke is None:
            self.pen.SetColour(wx.BLUE)
        else:
            self.pen.SetColour(wx.Colour(swizzlecolor(elements.default_stroke)))
        gc.SetPen(self.pen)
        gc.SetBrush(wx.RED_BRUSH)
        gc.DrawEllipse(self.track_object[0], self.track_object[1], 5000, 5000)
        if self.last_position:
            gc.DrawEllipse(self.last_position[0], self.last_position[1], 5000, 5000)

        if self.series is not None and len(self.series) > 1:
            gc.SetPen(self.pen)
            gc.StrokeLines(self.series)

    def tick(self):
        if self.last_position is None:
            return
        friction = 0.05
        attraction = 500
        vx = self.velocity[0] * (1 - friction)
        vy = self.velocity[1] * (1 - friction)
        angle = Point.angle(self.last_position, self.track_object)
        vx -= attraction * math.cos(angle)
        vy -= attraction * math.sin(angle)

        self.velocity[0] = vx
        self.velocity[1] = vy
        self.track_object[0] += vx
        self.track_object[1] += vy
        self.pos += 1
        if self.pos & 2:
            self.series.append((self.last_position[0], self.last_position[1]))
        else:
            self.series.append((self.track_object[0], self.track_object[1]))
        self.scene.request_refresh()
        if self.stop:
            return False
        return (
            abs(self.last_position[0] - self.track_object[0]) > 1000
            or abs(self.last_position[1] - self.track_object[1]) > 1000
        )

    def event(
        self, window_pos=None, space_pos=None, event_type=None, modifiers=None, **kwargs
    ):
        # We don't set tool_active here, as this can't be properly honored...
        # And we don't care about nearest_snap either...
        response = RESPONSE_CHAIN
        if event_type == "leftdown":
            self.stop = False
            self.last_position = space_pos[:2]
            self.scene.animate(self)
            response = RESPONSE_CONSUME
        elif event_type == "move" or event_type == "hover":
            self.last_position = space_pos[:2]
            response = RESPONSE_CONSUME
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            self.stop = True
            self.series.clear()
            if self.scene.tool_active:
                self.scene.tool_active = False
                self.scene.request_refresh()
                return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        elif event_type == "leftup":
            self.stop = True
            if self.series:
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
                self.series.clear()
            response = RESPONSE_CONSUME
        return response
