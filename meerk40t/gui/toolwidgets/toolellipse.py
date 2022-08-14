import wx

from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_ABORT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Ellipse


class EllipseTool(ToolWidget):
    """
    Ellipse Drawing Tool.

    Adds Circle with click and drag.
    """

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
            if self.scene.context.elements.default_stroke is None:
                self.pen.SetColour(wx.BLUE)
            else:
                self.pen.SetColour(
                    wx.Colour(swizzlecolor(self.scene.context.elements.default_stroke))
                )
            gc.SetPen(self.pen)
            if self.scene.context.elements.default_fill is None:
                gc.SetBrush(wx.TRANSPARENT_BRUSH)
            else:
                gc.SetBrush(
                    wx.Brush(
                        wx.Colour(
                            swizzlecolor(self.scene.context.elements.default_fill)
                        ),
                        wx.BRUSHSTYLE_SOLID,
                    )
                )
            gc.DrawEllipse(x0, y0, x1 - x0, y1 - y0)

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        **kwargs,
    ):
        response = RESPONSE_CHAIN
        if event_type == "leftdown":
            self.scene.tool_active = True
            if nearest_snap is None:
                self.p1 = complex(space_pos[0], space_pos[1])
            else:
                self.p1 = complex(nearest_snap[0], nearest_snap[1])
            response = RESPONSE_CONSUME
        elif event_type == "move":
            if self.p1 is not None:
                if nearest_snap is None:
                    self.p2 = complex(space_pos[0], space_pos[1])
                else:
                    self.p2 = complex(nearest_snap[0], nearest_snap[1])
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
        elif event_type == "leftclick":
            # Dear user: that's too quick for my taste - take your time...
            self.p1 = None
            self.p2 = None
            self.scene.tool_active = False
            self.scene.request_refresh()
            response = RESPONSE_ABORT
        elif event_type == "leftup":
            self.scene.tool_active = False
            try:
                if self.p1 is None:
                    return
                if nearest_snap is None:
                    self.p2 = complex(space_pos[0], space_pos[1])
                else:
                    self.p2 = complex(nearest_snap[0], nearest_snap[1])
                x0 = min(self.p1.real, self.p2.real)
                y0 = min(self.p1.imag, self.p2.imag)
                x1 = max(self.p1.real, self.p2.real)
                y1 = max(self.p1.imag, self.p2.imag)
                ellipse = Ellipse(
                    (x1 + x0) / 2.0,
                    (y1 + y0) / 2.0,
                    abs(x0 - x1) / 2,
                    abs(y0 - y1) / 2,
                    stroke="blue",
                    stroke_width=1000,
                )
                if not ellipse.is_degenerate():
                    elements = self.scene.context.elements
                    node = elements.elem_branch.add(shape=ellipse, type="elem ellipse")
                    if self.scene.context.elements.default_stroke is not None:
                        node.stroke = self.scene.context.elements.default_stroke
                    if self.scene.context.elements.default_fill is not None:
                        node.fill = self.scene.context.elements.default_fill

                    if elements.classify_new:
                        elements.classify([node])
                    self.notify_created(node)
                self.p1 = None
                self.p2 = None
            except IndexError:
                pass
            self.scene.request_refresh()
            response = RESPONSE_ABORT
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            if self.scene.tool_active:
                self.scene.tool_active = False
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
            self.p1 = None
            self.p2 = None
        return response
