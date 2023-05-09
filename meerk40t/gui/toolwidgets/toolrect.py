import wx

from meerk40t.core.units import Length
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_ABORT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget

_ = wx.GetTranslation


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
        # 0 -> from corner, 1 from center
        self.creation_mode = 0

    def process_draw(self, gc: wx.GraphicsContext):
        if self.p1 is not None and self.p2 is not None:
            matrix = gc.GetTransform().Get()
            pixel = 1.0 / matrix[0]
            if self.creation_mode == 1:
                # From center (p1 center, p2 one corner)
                p_x = self.p1.real - (self.p2.real - self.p1.real)
                p_y = self.p1.imag - (self.p2.imag - self.p1.imag)
                x0 = min(p_x, self.p2.real)
                y0 = min(p_y, self.p2.imag)
                x1 = max(p_x, self.p2.real)
                y1 = max(p_y, self.p2.imag)
            else:
                # From corner (p1 corner, p2 corner)
                x0 = min(self.p1.real, self.p2.real)
                y0 = min(self.p1.imag, self.p2.imag)
                x1 = max(self.p1.real, self.p2.real)
                y1 = max(self.p1.imag, self.p2.imag)

            elements = self.scene.context.elements
            if elements.default_stroke is None:
                self.pen.SetColour(wx.BLUE)
            else:
                self.pen.SetColour(wx.Colour(swizzlecolor(elements.default_stroke)))
            gc.SetPen(self.pen)
            if elements.default_fill is None:
                gc.SetBrush(wx.TRANSPARENT_BRUSH)
            else:
                gc.SetBrush(
                    wx.Brush(
                        wx.Colour(swizzlecolor(elements.default_fill)),
                        wx.BRUSHSTYLE_SOLID,
                    )
                )
            gc.DrawRectangle(x0, y0, x1 - x0, y1 - y0)
            if abs(x1 - x0) > 10 * pixel and abs(y1 - y0) > 10 * pixel:
                ccx = (x0 + x1) / 2
                ccy = (y0 + y1) / 2
                gc.StrokeLine(
                    ccx - 4 * pixel,
                    ccy - 4 * pixel,
                    ccx + 4 * pixel,
                    ccy + 4 * pixel,
                )
                gc.StrokeLine(
                    ccx - 4 * pixel,
                    ccy + 4 * pixel,
                    ccx + 4 * pixel,
                    ccy - 4 * pixel,
                )
            units = self.scene.context.units_name
            s = "O=({cx}, {cy}), a={a}, b={b}".format(
                cx=Length(amount=x0, digits=2, preferred_units=units),
                cy=Length(amount=y0, digits=2, preferred_units=units),
                a=Length(amount=x1 - x0, digits=2, preferred_units=units),
                b=Length(amount=y1 - y0, digits=2, preferred_units=units),
            )
            s += _(" (Press Alt-Key to draw from center)")
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
        if (
            modifiers is None
            or (event_type == "key_up" and "alt" in modifiers)
            or ("alt" not in modifiers)
        ):
            if self.creation_mode != 0:
                self.creation_mode = 0
                update_required = True
        else:
            if self.creation_mode != 1:
                self.creation_mode = 1
                update_required = True
        if event_type == "leftdown":
            self.scene.pane.tool_active = True
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
            self.scene.pane.tool_active = False
            self.scene.request_refresh()
            response = RESPONSE_ABORT
        elif event_type == "leftup":
            self.scene.pane.tool_active = False
            try:
                if self.p1 is None:
                    return
                if nearest_snap is None:
                    self.p2 = complex(space_pos[0], space_pos[1])
                else:
                    self.p2 = complex(nearest_snap[0], nearest_snap[1])
                dx = self.p1.real - self.p2.real
                dy = self.p1.imag - self.p2.imag
                if abs(dx) < 1e-10 or abs(dy) < 1e-10:
                    # Degenerate? Ignore!
                    self.p1 = None
                    self.p2 = None
                    self.scene.request_refresh()
                    self.scene.context.signal("statusmsg", "")
                    response = RESPONSE_ABORT
                    return response
                if self.creation_mode == 1:
                    # From center (p1 center, p2 one corner)
                    p_x = self.p1.real - (self.p2.real - self.p1.real)
                    p_y = self.p1.imag - (self.p2.imag - self.p1.imag)
                    x0 = min(p_x, self.p2.real)
                    y0 = min(p_y, self.p2.imag)
                    x1 = max(p_x, self.p2.real)
                    y1 = max(p_y, self.p2.imag)
                else:
                    # From corner (p1 corner, p2 corner)
                    x0 = min(self.p1.real, self.p2.real)
                    y0 = min(self.p1.imag, self.p2.imag)
                    x1 = max(self.p1.real, self.p2.real)
                    y1 = max(self.p1.imag, self.p2.imag)
                elements = self.scene.context.elements
                node = elements.elem_branch.add(
                    x=x0,
                    y=y0,
                    x1=x1 - x0,
                    y1=y1 - y0,
                    type="elem rect",
                    stroke_width=elements.default_strokewidth,
                    stroke=elements.default_stroke,
                    fill=elements.default_fill,
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
