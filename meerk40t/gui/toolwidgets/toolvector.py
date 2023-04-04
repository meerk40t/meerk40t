from math import tau

import wx

from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Path, Point

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
        # angle_snap indicates whether a line should be angle snapping
        # False anything goes, True snaps to next 45° angle
        self.angle_snap = False

    def angled(self, pos):
        if self.angle_snap and self.path:
            # What is the angle between mouse_pos and the last_position?
            p1 = self.path.z_point
            p2 = Point(pos[0], pos[1])
            oldangle = p1.angle_to(p2)
            dist = p1.distance_to(p2)
            newangle = round(oldangle / tau * 8, 0) / 8 * tau
            p3 = p1.polar(p1, newangle, dist)
            pos = [p3.x, p3.y]
        return pos

    def process_draw(self, gc: wx.GraphicsContext):
        if self.path:
            gc.SetPen(self.pen)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            path = Path(self.path)
            if self.mouse_position is not None:
                if self.c0:
                    pos = self.mouse_position
                    path.smooth_cubic(self.c0, pos)
                else:
                    pos = self.angled(self.mouse_position)
                    path.line(pos)
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
        update_required = False
        if (
            modifiers is None
            or (event_type == "key_up" and "alt" in modifiers)
            or ("alt" not in modifiers)
        ):
            if self.angle_snap:
                self.angle_snap = False
                update_required = True
        else:
            if not self.angle_snap:
                self.angle_snap = True
                update_required = True

        if event_type == "leftclick":
            self.scene.pane.tool_active = True
            elements = self.scene.context.elements
            if self.path is None:
                self.pen = wx.Pen()
                self.pen.SetColour(wx.Colour(swizzlecolor(elements.default_stroke)))
                try:
                    self.pen.SetWidth(elements.default_strokewidth)
                except TypeError:
                    self.pen.SetWidth(int(elements.default_strokewidth))
                self.path = Path()
                if nearest_snap is None:
                    self.path.move((space_pos[0], space_pos[1]))
                else:
                    self.path.move((nearest_snap[0], nearest_snap[1]))
            else:
                if nearest_snap is None:
                    pos = [space_pos[0], space_pos[1]]
                else:
                    pos = [nearest_snap[0], nearest_snap[1]]
                pos = self.angled(pos)
                self.path.line((pos[0], pos[1]))
            self.c0 = None
            response = RESPONSE_CONSUME
        elif event_type == "rightdown":
            if self.path is None or len(self.path) == 0:
                was_already_empty = True
            else:
                was_already_empty = False
            self.end_tool()
            if was_already_empty:
                self.scene.context("tool none\n")
            response = RESPONSE_CONSUME
        elif event_type == "leftdown":
            self.scene.pane.tool_active = True
            if nearest_snap is None:
                pos = (space_pos[0], space_pos[1])
            else:
                pos = (nearest_snap[0], nearest_snap[1])
            pos = self.angled(pos)
            self.c0 = (pos[0], pos[1])
            response = RESPONSE_CONSUME
        elif event_type == "move":
            if nearest_snap is None:
                pos = (space_pos[0], space_pos[1])
            else:
                pos = (nearest_snap[0], nearest_snap[1])
            pos = self.angled(pos)
            self.c0 = (pos[0], pos[1])
            if self.path:
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
        elif event_type == "leftup":
            self.scene.pane.tool_active = False
            if self.c0 is not None and self.path:
                self.scene.pane.tool_active = True
                pos = self.mouse_position
                self.path.smooth_cubic(self.c0, pos)
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
            self.end_tool()
            response = RESPONSE_CONSUME
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            if self.scene.pane.tool_active:
                self.scene.pane.tool_active = False
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
            self.scene.context.signal("statusmsg", "")
            self.path = None
        elif update_required:
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        return response

    def end_tool(self):
        self.scene.pane.tool_active = False
        t = self.path
        if t is not None and len(t) > 1:
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
        self.scene.request_refresh()
