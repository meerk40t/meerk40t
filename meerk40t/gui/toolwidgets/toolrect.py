import wx

from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Rect
from meerk40t.gui.laserrender import swizzlecolor


class RectTool(ToolWidget):
    """
    Rectangle Drawing Tool.

    Adds Rectangles with click and drag.
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
            if self.scene.default_stroke is None:
                self.pen.SetColour(wx.BLUE)
            else:
                self.pen.SetColour(wx.Colour(swizzlecolor(self.scene.default_stroke)))
            gc.SetPen(self.pen)
            if self.scene.default_fill is None:
                gc.SetBrush(wx.TRANSPARENT_BRUSH)
            else:
                gc.SetBrush(wx.Brush(wx.Colour(swizzlecolor(self.scene.default_fill)), wx.BRUSHSTYLE_SOLID))
            gc.DrawRectangle(x0, y0, x1 - x0, y1 - y0)

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
                rect = Rect(x0, y0, x1 - x0, y1 - y0, stroke="blue", stroke_width=1000)
                if not rect.is_degenerate():
                    elements = self.scene.context.elements
                    node = elements.elem_branch.add(shape=rect, type="elem rect")
                    if not self.scene.default_stroke is None:
                        node.stroke = self.scene.default_stroke
                    if not self.scene.default_fill is None:
                        node.fill = self.scene.default_fill

                    elements.classify([node])
                    self.notify_created()
                self.p1 = None
                self.p2 = None
            except IndexError:
                pass
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        elif event_type == "lost":
            self.scene.tool_active = False
        return response
