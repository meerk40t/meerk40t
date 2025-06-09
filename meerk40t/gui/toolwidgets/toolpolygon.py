from math import cos, sin, tau

import wx

from meerk40t.core.units import Angle, Length
from meerk40t.gui.icons import (
    STD_ICON_SIZE,
    icon_crossing_star,
    icon_growing,
    icon_mk_polygon,
    icon_polygon,
    icon_regular_star,
)
from meerk40t.gui.toolwidgets.toolpointlistbuilder import PointListTool
from meerk40t.kernel.kernel import Job
from meerk40t.svgelements import Point, Polygon

_ = wx.GetTranslation


class PolygonTool(PointListTool):
    """
    Polygon Drawing Tool.

    Adds polygon with clicks.
    """

    def __init__(self, scene, mode=None):
        PointListTool.__init__(self, scene, mode=mode)

        # design_mode
        # 0 - freehand polygon
        # 1 - regular polygon
        # 2 - star polygon
        # 3 - crossing star polygon
        # 4 - growing polygon
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
        if mode < 0 or mode > 4:
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
                "help": "polygon",
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
                "help": "polygon",
                "action": lambda v: self.set_designmode(3),
                "size": icon_size,
                "group": "polygon",
                "identifier": "polygon4",
            },
        )

        self.scene.context.kernel.register(
            "button/secondarytool_polygon/tool_growingpoly",
            {
                "label": _("Grow"),
                "icon": icon_growing,
                "tip": _("Draw a growing polygon"),
                "help": "polygon",
                "action": lambda v: self.set_designmode(4),
                "size": icon_size,
                "group": "polygon",
                "identifier": "polygon5",
            },
        )

    def draw_points(self, gc, points):
        if len(points) > 2:
            points.append((points[0][0], points[0][1]))
        gc.StrokeLines(points)

    def point_added(self):
        tc = len(self.point_series)
        if tc >= 2 and self.design_mode == 1:
            self.end_tool()
        elif tc >= 2 and self.design_mode == 2:
            self.end_tool()
        elif tc >= 2 and self.design_mode == 3:
            self.end_tool()
        elif tc >= 2 and self.design_mode == 4:
            self.end_tool()

    def key_up(self, keycode, modifier):
        result = False
        if keycode == "f":
            # Freehand
            self.set_designmode(0)
            result = True
        elif keycode == "r":
            # Regular
            self.set_designmode(1)
            result = True
        elif keycode in ("1", "s"):
            # Star 1
            self.set_designmode(2)
            result = True
        elif keycode in ("2", "p"):
            # Star 2 / Pentagram
            self.set_designmode(3)
            result = True
        elif keycode == "g":
            # Growing polygon
            self.set_designmode(4)
            result = True
        return result

    def add_regular_node(self):
        # We have now enough information to create a regular polygon
        # The first point and the second point define an edge,
        # we just assume it's a regular triangle
        # and hand over to another tool to let the user refine it
        corners = 3
        pt1 = Point(self.point_series[0])
        pt2 = Point(self.point_series[1])
        # plus 60 degrees
        angle = pt2.angle_to(pt1)
        distance = pt1.distance_to(pt2)
        tangle = angle - tau / 6
        p3x = pt2.x + cos(tangle) * distance
        p3y = pt2.y + sin(tangle) * distance
        # points.append((p3x, p3y))
        pt3 = Point(p3x, p3y)
        cx = (pt1.x + pt2.x + pt3.x) / 3
        cy = (pt1.y + pt2.y + pt3.y) / 3
        center = Point(cx, cy)

        radius = center.distance_to(pt1)
        startangle = center.angle_to(pt1)
        command = f"shape {corners} {Length(center.x, digits=3).length_mm} {Length(center.y, digits=3).length_mm}"
        command += f" {Length(radius, digits=3).length_mm} -s {Angle(startangle, digits=2).angle_degrees}\n"
        self.scene.context(command)
        selected_node = self.scene.context.elements.first_element(emphasized=True)
        if selected_node is not None:
            return "tool parameter"

    def add_star_node(self, mode):
        # We have now enough information to create a regular polygon
        # The first point is the center, the second point defines
        # the start point, we just assume it's a regular triangle
        # and hand over to another tool to let the user refine it
        # We have now enough information to create a star shape
        # The first point is the center, the second point defines
        # the start point, we just provide a good-looking example
        # and hand over to another tool
        pt1 = Point(self.point_series[0])
        pt2 = Point(self.point_series[1])
        radius = pt1.distance_to(pt2)
        startangle = pt1.angle_to(pt2)
        if mode == 1:
            corners = 16
            inner = radius * 0.5
            command = (
                f"shape {corners} {Length(pt1.x).length_mm} {Length(pt1.y).length_mm}"
                + f" {Length(radius).length_mm} -s {Angle(startangle, digits=2).angle_degrees}"
                + f" -r {Length(inner).length_mm}\n"
            )
        else:
            corners = 8
            density = 5
            command = (
                f"shape {corners} {Length(pt1.x).length_mm} {Length(pt1.y).length_mm}"
                + f" {Length(radius).length_mm} -s {Angle(startangle, digits=2).angle_degrees}"
                + f" -d {density}\n"
            )
        self.scene.context(command)
        selected_node = self.scene.context.elements.first_element(emphasized=True)
        if selected_node is not None:
            return "tool parameter"

    def add_growing_node(self):
        # We have now enough information to create a regular polygon
        # The first point is the center, the second point defines
        # the start point, we just assume it's a regular triangle
        # and hand over to another tool to let the user refine it
        corners = 3
        iterations = 10
        gap = 4
        pt1 = Point(self.point_series[0])
        pt2 = Point(self.point_series[1])
        side = pt1.distance_to(pt2)
        angle = pt1.angle_to(pt2)
        command = f"growingshape {Length(pt1.x, digits=3).length_mm} {Length(pt1.y, digits=3).length_mm}"
        command += f" {corners} {iterations} {Length(side, digits=3).length_mm}"
        command += f" -a {Angle(angle, digits=2).angle_degrees}"
        command += f" -g {gap}\n"
        self.scene.context(command)
        selected_node = self.scene.context.elements.first_element(emphasized=True)
        if selected_node is not None:
            return "tool parameter"

    def add_freehand_node(self):
        lines = list(self.point_series)
        polyline = Polygon(*lines)
        elements = self.scene.context.elements
        # _("Create polyline")
        with elements.undoscope("Create polyline"):
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

    def create_node(self):
        if len(self.point_series) < 2:
            return None
        followup = None
        if self.design_mode == 0:
            followup = self.add_freehand_node()
        elif self.design_mode == 1:
            followup = self.add_regular_node()
        elif self.design_mode == 2:
            followup = self.add_star_node(1)
        elif self.design_mode == 3:
            followup = self.add_star_node(2)
        elif self.design_mode == 4:
            followup = self.add_growing_node()
        return followup
