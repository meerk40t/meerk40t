import threading
import time

from meerk40t.gui.scene.scene import Scene
from meerk40t.gui.scene.widget import Widget

try:
    from math import tau
except ImportError:
    from math import pi

    tau = 2 * pi

import wx

from meerk40t.kernel import Job, Module
from meerk40t.svgelements import Matrix, Path, Point, Rect, Color
from meerk40t.gui.laserrender import (
    DRAW_MODE_ANIMATE,
    DRAW_MODE_BACKGROUND,
    DRAW_MODE_FLIPXY,
    DRAW_MODE_GRID,
    DRAW_MODE_GUIDES,
    DRAW_MODE_INVERT,
    DRAW_MODE_LASERPATH,
    DRAW_MODE_REFRESH,
    DRAW_MODE_RETICLE,
    DRAW_MODE_SELECTION,
    swizzlecolor,
)
from meerk40t.gui.zmatrix import ZMatrix

MILS_IN_MM = 39.3701

HITCHAIN_HIT = 0
HITCHAIN_DELEGATE = 1
HITCHAIN_HIT_AND_DELEGATE = 2
HITCHAIN_DELEGATE_AND_HIT = 3

RESPONSE_CONSUME = 0
RESPONSE_ABORT = 1
RESPONSE_CHAIN = 2
RESPONSE_DROP = 3

ORIENTATION_MODE_MASK = 0b00001111110000
ORIENTATION_DIM_MASK = 0b00000000001111
ORIENTATION_MASK = ORIENTATION_MODE_MASK | ORIENTATION_DIM_MASK
ORIENTATION_RELATIVE = 0b00000000000000
ORIENTATION_ABSOLUTE = 0b00000000010000
ORIENTATION_CENTERED = 0b00000000100000
ORIENTATION_HORIZONTAL = 0b00000001000000
ORIENTATION_VERTICAL = 0b00000010000000
ORIENTATION_GRID = 0b00000100000000
ORIENTATION_NO_BUFFER = 0b00001000000000
BUFFER = 10.0


class ToolContainer(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)

    def signal(self, signal, *args, **kwargs):
        if signal == "tool":
            tool = args[0]
            self.set_tool(tool)

    def set_tool(self, tool):
        self.remove_all_widgets()
        if tool is None:
            return
        new_tool = self.scene.context.registered["tool/%s" % tool]
        self.add_widget(0, new_tool(self.scene))


class CircleBrush:
    def __init__(self):
        self.tool_size = 100
        self.pos = 0 + 0j
        self.scale = 1.0
        self.range = self.tool_size * self.scale
        self.brush_fill = wx.Brush(wx.Colour(alpha=64, red=0, green=255, blue=0))
        self.using = False

    def set_location(self, x: float, y: float):
        self.pos = complex(x, y)

    def contains(self, x: float, y: float) -> bool:
        c = complex(x, y)
        return abs(self.pos - c) < self.range

    def draw(self, gc: wx.GraphicsContext):
        if self.using:
            self.drawBrush(gc)

    def drawBrush(self, gc: wx.GraphicsContext):
        gc.SetBrush(self.brush_fill)
        gc.DrawEllipse(
            self.pos.real - self.tool_size / 2.0,
            self.pos.imag - self.tool_size / 2.0,
            self.tool_size,
            self.tool_size,
        )


class ToolWidget(Widget):
    def __init__(self, scene: Scene):
        Widget.__init__(self, scene, all=True)
        self.brush = CircleBrush()

    def hit(self):
        return HITCHAIN_HIT

    def process_draw(self, gc):
        self.brush.draw(gc)


class DrawTool(ToolWidget):
    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.preferred_length = 50
        self.series = None
        self.last_position = None

    def process_draw(self, gc: wx.GraphicsContext):
        if self.series is not None and len(self.series) > 1:
            gc.StrokeLines(self.series)

    def add_point(self, point):
        if len(self.series):
            last = self.series[-1]
            if Point.distance(last, point) < self.preferred_length:
                return
            self.scene.gui.Update()
        self.series.append(point)

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if self.series is None:
            self.series = []
        if event_type == "leftdown":
            self.add_point(space_pos[:2])
        elif event_type == "move":
            if self.series is None:
                return RESPONSE_DROP
            self.add_point(space_pos[:2])
        elif event_type == "leftup":
            try:
                t = Path(stroke="blue")
                t.move(self.series[0])
                for m in self.series:
                    t.line(m)
                self.scene.context.root.elements.add_elem(t, classify=True)
            except IndexError:
                pass
            self.series = None


class RectTool(ToolWidget):
    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.p1 = None
        self.p2 = None

    def process_draw(self, gc: wx.GraphicsContext):
        if self.p1 is not None and self.p2 is not None:
            x0 = min(self.p1.real, self.p2.real)
            y0 = min(self.p1.imag, self.p2.imag)
            x1 = max(self.p1.real, self.p2.real)
            y1 = max(self.p1.imag, self.p2.imag)
            gc.SetPen(wx.BLUE_PEN)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            gc.DrawRectangle(x0, y0, x0 - x1, y0 - y1)

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if event_type == "leftdown":
            self.p1 = complex(space_pos[0], space_pos[1])
        elif event_type == "move":
            self.p2 = complex(space_pos[0], space_pos[1])
            self.scene.gui.signal("refresh_scene")
        elif event_type == "leftup":
            try:
                if self.p1 is None:
                    return
                self.p2 = complex(space_pos[0], space_pos[1])
                x0 = min(self.p1.real, self.p2.real)
                y0 = min(self.p1.imag, self.p2.imag)
                x1 = max(self.p1.real, self.p2.real)
                y1 = max(self.p1.imag, self.p2.imag)
                rect = Rect(x0, y0, x1 - x0, y1 - y0, stroke="blue")
                t = Path(rect)
                if len(t) != 0:
                    self.scene.context.root.elements.add_elem(t, classify=True)
                self.p1 = None
                self.p2 = None
            except IndexError:
                pass
