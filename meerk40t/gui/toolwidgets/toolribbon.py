import math

import wx

from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.tools.geomstr import Geomstr


class GravityNode:
    def __init__(self, ribbon, attract_node=0):
        self.ribbon = ribbon
        self.friction = 0.05
        self.distance = 50
        self.attraction = 1000
        self.position = None
        self.velocity = [0, 0]
        self.brush = wx.Brush(wx.RED)
        self.pen = wx.Pen(wx.BLUE)
        self.diameter = 5000
        self.attract_node = attract_node

    def tick(self):
        towards_pos = self.ribbon.nodes[self.attract_node].position
        if self.position is None:
            self.position = list(self.ribbon.position)
        vx = self.velocity[0] * (1 - self.friction)
        vy = self.velocity[1] * (1 - self.friction)
        angle = Geomstr.angle(
            None, complex(*towards_pos), complex(*self.position)
        )
        vx -= self.attraction * math.cos(angle)
        vy -= self.attraction * math.sin(angle)

        self.velocity[0] = vx
        self.velocity[1] = vy
        self.position[0] += vx
        self.position[1] += vy

    def process_draw(self, gc: wx.GraphicsContext):
        if not self.position:
            return
        gc.PushState()
        gc.SetPen(self.pen)
        gc.SetBrush(self.brush)
        gc.DrawEllipse(self.position[0], self.position[1], self.diameter, self.diameter)
        gc.PopState()


class PositionNode:
    def __init__(self, ribbon):
        self.ribbon = ribbon
        self.brush = wx.Brush(wx.RED)
        self.pen = wx.Pen(wx.BLUE)

    @property
    def position(self):
        return self.ribbon.position

    def tick(self):
        pass

    def process_draw(self, gc: wx.GraphicsContext):
        if not self.position:
            return
        gc.SetPen(self.pen)
        gc.SetBrush(self.brush)
        gc.DrawEllipse(self.position[0], self.position[1], 5000, 5000)


class DrawSequence:
    def __init__(self, ribbon, sequences):
        self.series = {}
        self.tick_index = 0
        self.ribbon = ribbon
        self.pen = wx.Pen(wx.BLUE)
        self.sequences = sequences

    @classmethod
    def zig(cls, ribbon):
        return cls(ribbon, sequences=[[[0], [0], [1], [1]]])

    @classmethod
    def bounce(cls, ribbon, *args):
        return cls(ribbon, sequences=[[list(args)]])

    def tick(self):
        self.tick_index += 1
        for s, sequence in enumerate(self.sequences):
            series = self.series.get(s)
            if series is None:
                # Add series if not init
                series = []
                self.series[s] = series

            q = self.tick_index % len(sequence)
            seq = sequence[q]
            for i in seq:
                x, y = self.ribbon.nodes[i].position
                series.append((x, y))

    def process_draw(self, gc: wx.GraphicsContext):
        gc.SetPen(self.pen)
        for q in self.series:
            series = self.series[q]
            gc.StrokeLines(series)

    def get_path(self):
        g = Geomstr()
        for q in self.series:
            series = self.series[q]
            g.polyline(points=[complex(x, y) for x, y in series])
        return g


class Ribbon:
    def __init__(self):
        self.nodes = []
        self.sequence = DrawSequence.zig(self)
        self.position = None

    @classmethod
    def gravity_tool(cls):
        obj = cls()
        obj.nodes.append(PositionNode(obj))
        obj.nodes.append(GravityNode(obj, 0))
        obj.sequence = DrawSequence.zig(obj)
        return obj

    @classmethod
    def bezier_gravity_tool(cls):
        obj = cls()
        obj.nodes.append(PositionNode(obj))
        obj.nodes.append(GravityNode(obj, 0))
        obj.nodes.append(GravityNode(obj, 1))
        obj.sequence = DrawSequence.bounce(obj, 1, 2)
        return obj

    def tick(self):
        for node in self.nodes:
            node.tick()
        self.sequence.tick()

    def process_draw(self, gc: wx.GraphicsContext):
        for node in self.nodes:
            node.process_draw(gc)
        self.sequence.process_draw(gc)

    def get_path(self):
        return self.sequence.get_path()

    def clear(self):
        self.sequence.series.clear()


class RibbonTool(ToolWidget):
    """
    Ribbon Tool draws new segments by animating some click and press locations.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.stop = False
        self.ribbon = Ribbon.gravity_tool()

    def process_draw(self, gc: wx.GraphicsContext):
        self.ribbon.process_draw(gc)

    def tick(self):
        self.ribbon.tick()
        self.scene.request_refresh()
        if self.stop:
            return False
        return True

    def event(
        self, window_pos=None, space_pos=None, event_type=None, modifiers=None, **kwargs
    ):
        # We don't set tool_active here, as this can't be properly honored...
        # And we don't care about nearest_snap either...
        response = RESPONSE_CHAIN
        if event_type == "leftdown":
            self.stop = False
            self.ribbon.position = space_pos[:2]
            self.scene.animate(self)
            response = RESPONSE_CONSUME
        elif event_type == "move" or event_type == "hover":
            self.ribbon.position = space_pos[:2]
            response = RESPONSE_CONSUME
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            self.stop = True
            self.ribbon.clear()
            if self.scene.pane.tool_active:
                self.scene.pane.tool_active = False
                self.scene.request_refresh()
                return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        elif event_type == "leftup":
            self.stop = True
            t = self.ribbon.get_path()
            if t:
                elements = self.scene.context.elements
                node = elements.elem_branch.add(
                    geometry=t,
                    type="elem path",
                    stroke_width=elements.default_strokewidth,
                    stroke=elements.default_stroke,
                    fill=elements.default_fill,
                )
                if elements.classify_new:
                    elements.classify([node])
                self.ribbon.clear()
            response = RESPONSE_CONSUME
        return response
