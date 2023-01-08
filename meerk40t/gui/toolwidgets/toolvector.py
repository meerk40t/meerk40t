import wx

from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Path

from ..laserrender import LaserRender, swizzlecolor


class VectorTool(ToolWidget):
    """
    Path Drawing Tool.

    Adds Path with click and drag.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.path = None
        self.mouse_position = None
        self.render = LaserRender(scene.context)
        self.c0 = None

    def process_draw(self, gc: wx.GraphicsContext):
        if self.path:
            gc.SetPen(self.pen)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            path = Path(self.path)
            if self.mouse_position is not None:
                if self.c0:
                    path.smooth_cubic(self.c0, self.mouse_position)
                else:
                    path.line(self.mouse_position)
            gpath = self.render.make_path(gc, path)
            gc.DrawPath(gpath)
            del gpath
            # x0 = points[-2][0]
            # y0 = points[-2][1]
            # x1 = points[-1][0]
            # y1 = points[-1][1]
            # s = "Pts: {pts}, to last point: O=({cx}, {cy}), d={a}".format(
            #     pts = len(points),
            #     cx = Length(amount=x0, digits=2).length_mm,
            #     cy = Length(amount=y0, digits=2).length_mm,
            #     a = Length(amount=sqrt((x1-x0)*(x1-x0) + (y1-y0)*(y1-y0)), digits=2).length_mm,
            # )
            # self.scene.context.signal("statusmsg", s)

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

        if event_type == "leftclick":
            self.scene.tool_active = True
            elements = self.scene.context.elements
            if self.path is None:
                self.pen = wx.Pen()
                self.pen.SetColour(wx.Colour(swizzlecolor(elements.default_stroke)))
                self.pen.SetWidth(elements.default_strokewidth)
                self.path = Path()
                if nearest_snap is None:
                    self.path.move((space_pos[0], space_pos[1]))
                else:
                    self.path.move((nearest_snap[0], nearest_snap[1]))
            else:
                if nearest_snap is None:
                    self.path.line((space_pos[0], space_pos[1]))
                else:
                    self.path.line((nearest_snap[0], nearest_snap[1]))
            self.c0 = None
            response = RESPONSE_CONSUME
        elif event_type == "rightdown":
            if self.path is None or len(self.path) == 0:
                was_already_empty = True
            else:
                was_already_empty = False
            self.scene.tool_active = False
            self.path = None
            self.mouse_position = None
            self.scene.request_refresh()
            self.scene.context.signal("statusmsg", "")
            if was_already_empty:
                self.scene.context("tool none\n")
            response = RESPONSE_CONSUME
        elif event_type == "leftdown":
            self.scene.tool_active = True
            if nearest_snap is None:
                self.c0 = (space_pos[0], space_pos[1])
            else:
                self.c0 = (nearest_snap[0], nearest_snap[1])
            response = RESPONSE_CONSUME
        elif event_type == "move":
            if nearest_snap is None:
                self.c0 = (space_pos[0], space_pos[1])
            else:
                self.c0 = (nearest_snap[0], nearest_snap[1])
            if self.path:
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
        elif event_type == "leftup":
            self.scene.tool_active = False
            if self.c0 is not None and self.path:
                self.scene.tool_active = True
                self.path.smooth_cubic(self.c0, self.mouse_position)
                self.scene.request_refresh()
            self.c0 = None
            self.mouse_position = None
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        elif event_type == "hover":
            if nearest_snap is None:
                self.mouse_position = space_pos[0], space_pos[1]
            else:
                self.mouse_position = nearest_snap[0], nearest_snap[1]
            if self.path:
                self.scene.request_refresh()
        elif event_type == "doubleclick":
            self.scene.tool_active = False
            t = self.path
            if len(t) != 0:
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
            self.path = None
            self.scene.context.signal("statusmsg", "")
            self.mouse_position = None
            response = RESPONSE_CONSUME
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            if self.scene.tool_active:
                self.scene.tool_active = False
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
            self.scene.context.signal("statusmsg", "")
            self.path = None
        return response
