from math import sqrt, tau

import wx

from meerk40t.core.units import Length
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_ABORT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Point

class PointListTool(ToolWidget):
    """
    This tool is a basic widget just compiling a list of points.
    It aims to centralise the usual logic around adding points
    It even has a minimal display logic that draws the polyline
    of the given points. Any inherited class should just
    overload the draw routine.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.point_series = []
        self.mouse_position = None
        # angle_snap indicates whether a line should be angle snapping
        # False anything goes, True snaps to next 45° angle
        self.angle_snap = False

    def angled(self, pos):
        points = list(self.point_series)
        if self.angle_snap and len(points):
            # What is the angle between mouse_pos and the last_position?
            p1 = Point(points[-1][0], points[-1][1])
            p2 = Point(pos[0], pos[1])
            oldangle = p1.angle_to(p2)
            dist = p1.distance_to(p2)
            newangle = round(oldangle / tau * 8, 0) / 8 * tau
            p3 = p1.polar(p1, newangle, dist)
            pos = [p3.x, p3.y]
        return pos

    def process_draw(self, gc: wx.GraphicsContext):
        if self.point_series:
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
            points = list(self.point_series)
            if self.mouse_position is not None:
                pos = self.angled(self.mouse_position)
                points.append(pos)

            self.draw_points(gc, points)
            self.status_message(points)


    def draw_points(self, gc, points):
        # can be overloaded if needed
        gc.StrokeLines(points)

    def status_message(self, points):
        x0 = points[-2][0]
        y0 = points[-2][1]
        x1 = points[-1][0]
        y1 = points[-1][1]
        units = self.scene.context.units_name
        s = "Pts: {pts}, to last point: O=({cx}, {cy}), d={a}".format(
            pts=len(points),
            cx=Length(amount=x0, digits=2, preferred_units=units),
            cy=Length(amount=y0, digits=2, preferred_units=units),
            a=Length(
                amount=sqrt((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0)),
                digits=2,
                preferred_units=units,
            ),
        )
        self.scene.context.signal("statusmsg", s)

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
            if nearest_snap is None:
                sx, sy = self.scene.get_snap_point(
                    space_pos[0], space_pos[1], modifiers
                )
                pos = [sx, sy]
            else:
                pos = [nearest_snap[0], nearest_snap[1]]
            pos = self.angled(pos)
            self.point_series.append((pos[0], pos[1]))
            self.scene.context.signal("statusmsg", "")
            self.point_added()
            response = RESPONSE_CONSUME
            # Does this seem to close the path?
            if (
                len(self.point_series) > 2
                and abs(
                    complex(*self.point_series[0]) - complex(*self.point_series[-1])
                )
                < 5000
            ):
                self.end_tool()
                response = RESPONSE_ABORT
            # is the last point identical to the second-last?
            # Then we stop (and we discard the last point)
            if (
                len(self.point_series) > 2
                and abs(
                    complex(*self.point_series[-2]) - complex(*self.point_series[-1])
                )
                < 5000
            ):
                self.point_series.pop(-1)
                self.end_tool()
                response = RESPONSE_ABORT
        elif event_type == "rightdown":
            was_already_empty = len(self.point_series) == 0
            self.end_tool()
            if was_already_empty:
                self.scene.context("tool none\n")
            response = RESPONSE_CONSUME
        elif event_type == "leftdown":
            self.scene.pane.tool_active = True
            if nearest_snap is None:
                self.mouse_position = space_pos[0], space_pos[1]
            else:
                self.mouse_position = nearest_snap[0], nearest_snap[1]
            if self.point_series:
                self.scene.request_refresh()
            response = RESPONSE_CONSUME
        elif event_type in ("leftup", "move", "hover"):
            if nearest_snap is None:
                self.mouse_position = space_pos[0], space_pos[1]
            else:
                self.mouse_position = nearest_snap[0], nearest_snap[1]
            if self.point_series:
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
        elif event_type == "doubleclick":
            self.end_tool()
            response = RESPONSE_ABORT
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            if self.scene.pane.tool_active:
                self.scene.pane.tool_active = False
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
            self.point_series = []
            self.mouse_position = None
            self.scene.context.signal("statusmsg", "")
            self.aborted()
        elif update_required:
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        return response


    def aborted(self):
        # Can be overloaded
        return

    def point_added(self):
        # Can be overloaded
        # self.point_series does contain the list of valid points
        return

    def end_tool(self):
        self.create_node()
        self.scene.pane.tool_active = False
        self.point_series = []
        self.mouse_position = None
        self.scene.request_refresh()

    def create_node(self):
        print ("Needs to be overloaded!")
        # if len(self.point_series) > 1:
        #     polyline = Polyline(*self.point_series)
        #     elements = self.scene.context.elements
        #     node = elements.elem_branch.add(
        #         shape=polyline,
        #         type="elem polyline",
        #         stroke_width=elements.default_strokewidth,
        #         stroke=elements.default_stroke,
        #         fill=elements.default_fill,
        #     )
        #     if elements.classify_new:
        #         elements.classify([node])
        #     self.notify_created(node)
