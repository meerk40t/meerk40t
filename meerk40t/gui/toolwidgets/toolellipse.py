import wx

from meerk40t.gui.scene.sceneconst import (
    RESPONSE_ABORT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Ellipse, Path


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
            gc.SetPen(self.pen)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            gc.DrawEllipse(x0, y0, x1 - x0, y1 - y0)

    def event(self, window_pos=None, space_pos=None, event_type=None):
        response = RESPONSE_CHAIN
        if event_type == "leftdown":
            self.scene.tool_active = True
            self.p1 = complex(space_pos[0], space_pos[1])
            response = RESPONSE_CONSUME
        elif event_type == "move":
            self.p2 = complex(space_pos[0], space_pos[1])
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        elif event_type == "leftup":
            self.scene.tool_active = False
            try:
                if self.p1 is None:
                    return
                self.p2 = complex(space_pos[0], space_pos[1])
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
                    elements.classify([node])
                self.p1 = None
                self.p2 = None
            except IndexError:
                pass
            self.scene.request_refresh()
            response = RESPONSE_ABORT
        elif event_type == "lost":
            self.scene.tool_active = False
        return response
