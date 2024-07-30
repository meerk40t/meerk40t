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
    overload the draw routine and fill the create_node routine.
    The following caller routines are available:
    point_added(self): just a note that another point was added (self.point_series)
    create_node(self): a call that should pick up the points and create an element
    aborted(self): a note that the creation was aborted, in case you need to tidy up something
    status_message(points): this routine should give back a string that will be displayed in the status bar

    """

    def __init__(self, scene, mode=None):
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
            msg = self.status_message(points)
            if msg is not None:
                self.scene.context.signal("statusmsg", msg)

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
        elif event_type == "key_up":
            if not self.scene.pane.tool_active:
                return RESPONSE_CHAIN
            if self.key_up(keycode, modifiers):
                response = RESPONSE_CONSUME
        elif update_required:
            self.scene.request_refresh()
            # Have we clicked already?
            if len(self.point_series) > 0:
                response = RESPONSE_CONSUME
        return response

    def end_tool(self):
        followup = self.create_node()
        self.scene.pane.tool_active = False
        self.point_series = []
        self.mouse_position = None
        self.scene.request_refresh()
        if followup:
            self.scene.context(f"{followup}\n")
        elif self.scene.context.just_a_single_element:
            self.scene.pane.tool_active = False
            self.scene.context.signal("statusmsg", "")
            self.scene.context("tool none\n")

    # Routines that can be overloaded -------------------

    def draw_points(self, gc, points):
        """
        Can be overloaded if needed.
        Draws the shape on a given GraphicContexts,
        points do contain the already gathered points,
        including the mouse_position as last point
        """
        gc.StrokeLines(points)

    def status_message(self, points):
        """
        Can be overloaded if needed.
        Returns the to be displayed
        string for the statusbar.
        """
        x0 = points[-2][0]
        y0 = points[-2][1]
        x1 = points[-1][0]
        y1 = points[-1][1]
        units = self.scene.context.units_name
        msg = "Pts: {pts}, to last point: O=({cx}, {cy}), d={a}".format(
            pts=len(points),
            cx=Length(amount=x0, digits=2, preferred_units=units),
            cy=Length(amount=y0, digits=2, preferred_units=units),
            a=Length(
                amount=sqrt((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0)),
                digits=2,
                preferred_units=units,
            ),
        )
        return msg

    def aborted(self):
        """
        Can be overloaded if needed.
        Will be called if the user aborts the creation.
        """
        return

    def key_up(self, keycode, modifiers):
        """
        Can be overloaded if needed.
        Contains keycode and modifiers of the Widget event
        in case you want to do something with that information.
        Needs to return True if you consumed the keystroke
        """
        return False

    def point_added(self):
        """
        Can be overloaded if needed.
        Called whenever a new point was added:
        self.point_series does contain the list of valid points.
        If e.g. you just need two points then the code should look
        like this:
            def point_added(self):
                if len(self.point_series) > 1: # two points (or more)
                    # That's enough for my purpose
                    self.end_tool()
        """
        return

    def create_node(self):
        """
        This routine needs to be overloaded - this is the only
        mandatory one. To make sure you really notice it we
        will raise an error!
        The routine should pick up the points in self.point_series
        and create a new element. If you want a followup action
        to be executed at the end (e.g. you immediately want to
        fall back to the selection tool), then provide a command
        string to be done as a function result.
        Example code:
            def create_node(self):
                if len(self.point_series) > 1:
                    polyline = Polyline(*self.point_series)
                    elements = self.scene.context.elements
                    node = elements.elem_branch.add(
                        shape=polyline,
                        type="elem polyline",
                        stroke_width=elements.default_strokewidth,
                        stroke=elements.default_stroke,
                        fill=elements.default_fill,
                    )
                    if elements.classify_new:
                        elements.classify([node])
                    self.notify_created(node)
                return "tool none"
        """
        raise NotImplementedError
