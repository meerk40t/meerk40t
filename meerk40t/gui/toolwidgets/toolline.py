import math

import wx

from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_ABORT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.tools.geomstr import Geomstr

_ = wx.GetTranslation


class LineTool(ToolWidget):
    """
    Line Drawing Tool.

    Adds Line with click and drag.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.p1 = None
        self.p2 = None

    def process_draw(self, gc: wx.GraphicsContext):
        if self.p1 is not None and self.p2 is not None:
            matrix = gc.GetTransform().Get()
            # pixel = 1.0 / matrix[0]
            x0 = self.p1.real
            y0 = self.p1.imag
            x1 = self.p2.real
            y1 = self.p2.imag
            elements = self.scene.context.elements
            if elements.default_stroke is None:
                self.pen.SetColour(wx.BLUE)
            else:
                self.pen.SetColour(wx.Colour(swizzlecolor(elements.default_stroke)))
            gc.SetPen(self.pen)
            gc.StrokeLine(
                x0,
                y0,
                x1,
                y1,
            )
            s = f"Draw line from {x0}, {y0} to {x0}, {y0}"
            self.scene.context.signal("statusmsg", s)

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        keycode=None,
        **kwargs,
    ):
        response = RESPONSE_CHAIN
        update_required = False
        if event_type == "leftdown":
            self.scene.pane.tool_active = True
            if nearest_snap is None:
                sx, sy = self.scene.get_snap_point(
                    space_pos[0], space_pos[1], modifiers
                )
                self.p1 = complex(sx, sy)
            else:
                self.p1 = complex(nearest_snap[0], nearest_snap[1])
            response = RESPONSE_CONSUME
        elif event_type == "move":
            if self.p1 is not None:
                self.p2 = complex(space_pos[0], space_pos[1])
                if "shift" in modifiers:
                    r = abs(self.p1 - self.p2)
                    a = Geomstr.angle(None, self.p1, self.p2)
                    delta = math.tau / 32

                    for i in range(-4, 4):
                        s = i * math.tau / 8 - delta
                        e = i * math.tau / 8 + delta
                        if s <= a <= e:
                            self.p2 = Geomstr.polar(None, self.p1, i * math.tau / 8, r)
                else:
                    if nearest_snap is not None:
                        self.p2 = complex(nearest_snap[0], nearest_snap[1])
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
        elif event_type == "leftclick":
            # Dear user: that's too quick for my taste - take your time...
            self.p1 = None
            self.p2 = None
            self.scene.pane.tool_active = False
            self.scene.request_refresh()
            response = RESPONSE_ABORT
        elif event_type == "leftup":
            self.scene.pane.tool_active = False
            try:
                if self.p1 is None or self.p2 is None:
                    return RESPONSE_ABORT
                x1 = self.p1.real
                y1 = self.p1.imag
                x2 = self.p2.real
                y2 = self.p2.imag
                elements = self.scene.context.elements
                node = elements.elem_branch.add(
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    stroke_width=elements.default_strokewidth,
                    stroke=elements.default_stroke,
                    fill=elements.default_fill,
                    type="elem line",
                )
                if elements.classify_new:
                    elements.classify([node])
                self.notify_created(node)
                self.p1 = None
                self.p2 = None
            except IndexError:
                pass
            self.scene.request_refresh()
            self.scene.context.signal("statusmsg", "")
            response = RESPONSE_ABORT
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            if self.scene.pane.tool_active:
                self.scene.pane.tool_active = False
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
            self.p1 = None
            self.p2 = None
            self.scene.context.signal("statusmsg", "")
        elif update_required:
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        return response
