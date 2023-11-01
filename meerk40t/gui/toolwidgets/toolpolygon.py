from math import sin, sqrt, tan, tau

import wx

from meerk40t.core.units import Angle, Length
from meerk40t.gui.icons import (
    STD_ICON_SIZE,
    icon_crossing_star,
    icon_mk_polygon,
    icon_polygon,
    icon_regular_star,
)
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_ABORT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.kernel.kernel import Job
from meerk40t.svgelements import Point, Polygon

_ = wx.GetTranslation


class PolygonTool(ToolWidget):
    """
    Polygon Drawing Tool.

    Adds polygon with clicks.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.point_series = []
        self.mouse_position = None
        # angle_snap indicates whether a line should be angle snapping
        # False anything goes, True snaps to next 45° angle
        self.angle_snap = False
        # design_mode
        # 0 - freehand polygon
        # 1 - regular polygon
        # 2 - star polygon
        # 3 - crossing star polygon
        self.design_mode = 0
        self.define_buttons()
        # We need to wait a bit until all things have
        # been processed by the ribbonbar
        self._signal_job = Job(
            process=self.signal_button_once,
            job_name="polygon-helper",
            interval=0.5,
            times=1,
            run_main=True,
        )
        self.scene.context.schedule(self._signal_job)

    def signal_button_once(self):
        self.set_designmode(self.design_mode)

    def set_designmode(self, mode):
        if mode < 0 or mode > 3:
            mode = 0
        if mode != self.design_mode:
            self.design_mode = mode
            self.scene.refresh_scene()
        message = ("polygon", f"polygon{self.design_mode + 1}")
        self.scene.context.signal("tool_changed", message)

    def define_buttons(self):
        icon_size = STD_ICON_SIZE

        self.scene.context.kernel.register(
            "button/secondarytool_polygon/tool_freehand",
            {
                "label": _("Freehand"),
                "icon": icon_mk_polygon,
                "tip": _("Draw a freehand polygon (f)"),
                "action": lambda v: self.set_designmode(0),
                "size": icon_size,
                "group": "polygon",
                "identifier": "polygon1",
            },
        )

        self.scene.context.kernel.register(
            "button/secondarytool_polygon/tool_polygon",
            {
                "label": _("Regular"),
                "icon": icon_polygon,
                "tip": _("Draw a regular polygon (r)"),
                "action": lambda v: self.set_designmode(1),
                "size": icon_size,
                "group": "polygon",
                "identifier": "polygon2",
            },
        )

        self.scene.context.kernel.register(
            "button/secondarytool_polygon/tool_star1",
            {
                "label": _("Star 1"),
                "icon": icon_regular_star,
                "tip": _("Draw a regular star (1)"),
                "action": lambda v: self.set_designmode(2),
                "size": icon_size,
                "group": "polygon",
                "identifier": "polygon3",
            },
        )

        self.scene.context.kernel.register(
            "button/secondarytool_polygon/tool_star2",
            {
                "label": _("Star 2"),
                "icon": icon_crossing_star,
                "tip": _("Draw a crossing star (2)"),
                "action": lambda v: self.set_designmode(3),
                "size": icon_size,
                "group": "polygon",
                "identifier": "polygon4",
            },
        )

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
            s = ""
            points = self.calculated_points(True)
            gc.StrokeLines(points)
            if self.design_mode == 0:
                total_len = 0
                for idx in range(1, len(points)):
                    x0 = points[idx][0]
                    y0 = points[idx][1]
                    x1 = points[idx - 1][0]
                    y1 = points[idx - 1][1]
                    total_len += sqrt((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0))
                    units = self.scene.context.units_name
                    s = "Pts: {pts}, Len={a}".format(
                        pts=len(points) - 1,
                        a=Length(amount=total_len, digits=2, preferred_units=units),
                    )
            else:
                s = _("Click on the first corner")

            self.scene.context.signal("statusmsg", s)

    def calculated_points(self, closeit):
        points = list(self.point_series)
        if self.mouse_position is not None:
            pos = self.angled(self.mouse_position)
            points.append(pos)
        tc = len(points)
        if self.design_mode == 0:
            pass
        elif self.design_mode == 1:
            number_points = tc
            if number_points > 2:
                # We have now enough information to create a regular polygon
                # The first point is the center, the second point defines
                # the start point, we just assume it's a regular triangle
                # and hand over to another tool to let the user refine it
                pt1 = Point(points[0])
                pt2 = Point(points[1])
                # print(
                #     f"p1=({Length(pt1.x).length_mm}, {Length(pt1.y).length_mm}), p2=({Length(pt2.x).length_mm}, {Length(pt2.y).length_mm})"
                # )
                radius = pt1.distance_to(pt2)
                startangle = pt1.angle_to(pt2)
                corners = 3
                command = f"shape {corners} {Length(pt1.x).length_mm} {Length(pt1.y).length_mm}"
                command += f" {Length(radius).length_mm} -s {Angle(startangle, digits=2).angle_degrees}\n"
                # print(command)
                self.scene.context(command)
                selected_node = self.scene.context.elements.first_element(
                    emphasized=True
                )
                if selected_node is not None:
                    self.end_tool()
                    self.scene.context("tool parameter\n")
        elif self.design_mode == 2:
            number_points = tc
            if number_points > 2:
                # We have now enough information to create a star shape
                # The first point is the center, the second point defines
                # the start point, we just provide a good looking example
                # and hand over to another tool
                pt1 = Point(points[0])
                pt2 = Point(points[1])
                radius = pt1.distance_to(pt2)
                startangle = pt1.angle_to(pt2)
                corners = 16
                inner = radius * 0.5
                command = (
                    f"shape {corners} {Length(pt1.x).length_mm} {Length(pt1.y).length_mm}"
                    + f" {Length(radius).length_mm} -s {Angle(startangle, digits=2).angle_degrees}"
                    + f" -r {Length(inner).length_mm}\n"
                )
                self.scene.context(command)
                selected_node = self.scene.context.elements.first_element(
                    emphasized=True
                )
                if selected_node is not None:
                    self.end_tool()
                    self.scene.context("tool parameter\n")
        elif self.design_mode == 3:
            number_points = tc
            if number_points > 2:
                # We have now enough information to create a star shape
                # The first point is the center, the second point defines
                # the start point, we just provide a good looking example
                # and hand over to another tool
                pt1 = Point(points[0])
                pt2 = Point(points[1])
                radius = pt1.distance_to(pt2)
                startangle = pt1.angle_to(pt2)
                corners = 8
                density = 5
                command = (
                    f"shape {corners} {Length(pt1.x).length_mm} {Length(pt1.y).length_mm}"
                    + f" {Length(radius).length_mm} -s {Angle(startangle, digits=2).angle_degrees}"
                    + f" -d {density}\n"
                )
                self.scene.context(command)
                selected_node = self.scene.context.elements.first_element(
                    emphasized=True
                )
                if selected_node is not None:
                    self.end_tool()
                    self.scene.context("tool parameter\n")
        # Close the polygon
        if closeit:
            points.append(points[0])
        return points

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
            if nearest_snap is None:
                sx, sy = self.scene.get_snap_point(
                    space_pos[0], space_pos[1], modifiers
                )
                pos = [sx, sy]
            else:
                pos = [nearest_snap[0], nearest_snap[1]]
            pos = self.angled(pos)
            self.point_series.append((pos[0], pos[1]))
            response = RESPONSE_CONSUME
            if (
                len(self.point_series) > 2
                and abs(
                    complex(*self.point_series[0]) - complex(*self.point_series[-1])
                )
                < 5000
            ):
                self.end_tool()
                response = RESPONSE_ABORT
            if (
                len(self.point_series) > 2
                and abs(
                    complex(*self.point_series[-2]) - complex(*self.point_series[-1])
                )
                < 5000
                and self.design_mode == 0
            ):
                self.end_tool()
                response = RESPONSE_ABORT
            self.scene.pane.tool_active = True
            response = RESPONSE_CONSUME
        elif event_type == "rightdown":
            was_already_empty = len(self.point_series) == 0
            self.end_tool()
            if was_already_empty:
                self.scene.context("tool none\n")
            response = RESPONSE_ABORT
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
        elif event_type == "key_up" and modifiers == "return":
            self.end_tool()
            response = RESPONSE_ABORT
        elif event_type == "key_up":
            if not self.scene.pane.tool_active:
                return RESPONSE_CHAIN
            # print(
            #     f"key-up: {event_type}, modifiers: '{modifiers}', keycode: '{keycode}'"
            # )
            if keycode == "f":
                # Freehand
                self.set_designmode(0)
            elif keycode == "r":
                # Regular
                self.set_designmode(1)
            elif keycode in ("1", "s"):
                # Star 1
                self.set_designmode(2)
            elif keycode in ("2", "p"):
                # Star 2 / Pentagram
                self.set_designmode(3)

            return RESPONSE_CONSUME
        elif update_required:
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        return response

    def end_tool(self):
        if len(self.point_series) > 2:
            lines = self.calculated_points(False)
            polyline = Polygon(*lines)
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
        self.scene.pane.tool_active = False
        self.point_series = []
        self.mouse_position = None

        self.scene.request_refresh()
