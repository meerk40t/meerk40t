from math import sin, sqrt, tan, tau

import wx

from meerk40t.core.units import Length, Angle
from meerk40t.gui.icons import STD_ICON_SIZE, PyEmbeddedImage, icons8_polygon_50
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_ABORT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
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
        self.design_param = 0
        self.define_buttons()

    def set_designmode(self, mode):
        if mode < 0 or mode > 3:
            mode = 0
        # print(f"Designmode set to {mode}")
        if mode != self.design_mode:
            self.design_mode = mode
            self.design_param = 0
            self.scene.refresh_scene()
        else:
            self.design_param += 1

    def define_buttons(self):
        icon_size = STD_ICON_SIZE
        icon_regular_star = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwY"
            b"AAAD5klEQVR4nO2ZaahNaxjHf8c5uAfXlEPGpMzDByGzW265fCDXUPcDMuSTWfKB4pshlClj"
            b"XVxdRd2MR9dMXeEDkumQFNec46Acw3G2Hv1Xve32OXvtY6119opfrdq969nP87zvWut9hhd+"
            b"4IsawFngjH7Hll+BhK6hxJg9zkT+JqY0BkqBMl2lGosds/QkCoGj+j2TGHJFzo8Bxur3NWJG"
            b"bzn+AqgN1AKeaawXMWKznF7ljK3W2CZiQj7wSk53ccY7aawEqEMMmCSH/0tx77zuTSQGnJOz"
            b"U1Lcm6p7Fu2zmg5AOfAW+DnF/XrAG03GXrWsZbmc3FaJzHbJLCNLyQMey8m+lcj1k8xToCZZ"
            b"yCg5eMuH7A3JjiQLOSjn5vmQnS/ZA1RDbCgA2gE9gcHAcGAcMB1YAHwCPkguHQWS/aT/Tpeu"
            b"4dLdU7YKZNsXE4A/gX3AceACcB24DxQrc034vPZmsDh7M9BbJl/uy7cL8nWffLc58NyHolLl"
            b"TfeAy4oVhXJmK7AGWAI0z2AiLfSfNdJhugql+7JsvZDtdP7ZHPhNaUNCe/x4oBvQFmgE5FL9"
            b"5MqXtvJtvBOPSjSHr7QHbjoZ6y9kL/2BJ/L1blI+95X6zs5jH+EMso9p2iTMx3/1lCp8hF50"
            b"tmtLlgStvBR+2Vha/gDe6U/28TWl+mgMnJAv74HJmSqwvfyBFNzTRxY1HYHb8uFxmtQn7RZ5"
            b"UYosox1NdIxwdlPbjtt8q0KruXdIYbne1TC7hjnAQuCzbO4JuqKc7UR5C151CZ6fgL+cRVuq"
            b"iYX6uK3d0zpA3abLayGVyFaoWGVXJIOW5wSF9/oWRVk9rpdRy5WCwl4j07mOCPHSmQEB6hwo"
            b"nVZ0RUILJ8EMMupbpH4t3a2IsG91KATdh6Pse+2SsTkh6J4r3TuJgIcyFkbK0l26HxEynWXo"
            b"ic9A1UlnI0d9bqk5Tq1htkJjpoxY9E334S5MKlM/Kr2xI4bK2C35UOuh/TJSWSrdRwc6Xpqx"
            b"XVe5c9hjMhUxWXJmKxRyneOCVKlJvla8zEn97VTXY5CadwklhFvUC06mlZOm+CqeMsVrdVp9"
            b"kMwQ4I5TJq+tIKnMVwT3ylVr7wxLIVfko/VaZRZL+QZnrKFW1nttrurYLR09gEtJ/bAmzv2N"
            b"Gl8Uwjw4LeVecTXOORd8p5XOJNLnqTR4Kx0v1XE0ftfYqaAnUUf1sr3/XYF/nNU8p5K0qlhr"
            b"9Jij74ieWJlewUDrnmHOynuNsWKdSgVR+ORIV7GTx3nNj1TfUJVZmdSitDyrJcHTzEmBvGtF"
            b"kAZOSun/OgcJm1GylZDtwBiiXasB0dFANs3298MXw0hXuTS4jKMAAAAASUVORK5CYII="
        )
        icon_crossing_star = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAIAAACRXR/mAAAABnRSTlMA/wD/AP83WBt9AAAA"
            b"CXBIWXMAAA7EAAAOxAGVKw4bAAACbUlEQVRYhd2YO08CQRDHZw/LCw0tHb3PgoJeOv08+gV8"
            b"ND4a/QAajYaHET8CCT0JoaAlAZUooiWsxSXruXc7O8tsjLkJ1e3M3H/3tzO7h5BSwv+zwFsi"
            b"kQtEzls2X4n8WqZlKXy+OGZ6tQBgIecLOfeVzYMsDZwXjpmGqPD54siVlYqMzzG7EDVwXjiy"
            b"ZCGwmBwzCjEVGZ/j8rJywQrTAbHlZVnvj5wLJgtiuVw2DVUqFU5mIf7nrpdSCggEBCcnp5Js"
            b"UQjfJ25HR8cqBOIp6FkEBLs7u7hPdbvqlDAuANRAvd4gKqNPwClhrVb/eSJ/14vqzkjviXwo"
            b"zcnqaXqdvt/VMH56FAoFqyYAyOfzyCiyBCllqK6/gcj1ej1t9ObmFgBeXp8pst6nbwDQaj1p"
            b"z7vdrlrI1LXUIf6SnDYbOkGTP2mfIBlNQEulElETABSLxaRKXBMAgLE8EpVyd3c/HA6dWpEK"
            b"n0wmV1fXDiWMQEydpX2iPmKpJ89Czi8uL5zUaHZ2fuYwHzqLfr+verFTO41+g8GA/i4qRIjV"
            b"FHHbxt2c65foF7d4YxuPx0mH0WiEtyW7EVe13W4nwaUCNVEWEHQ6Hc8QTRQ0oNh54sJx+eu2"
            b"pobaJ2lG2luPjy3++5zCSRDx9Y9G9/f3pJQHB4dWT4o+lizkLEf8SRc1qwf+juQQcmPz2beQ"
            b"v4qaD03TV3Wj2cBjcbND1FbeqeKSzkSOJIha0jAMiTgWch6GYao+liyVbm11XU30YzalpI7s"
            b"YzZVvW1zY0tLazILRC2e07qcUlEr8fNrxm+nn18zorPzJwbfuJ8Y1uDlzFuX/3v7BikOKD82"
            b"lTxEAAAAAElFTkSuQmCC"
        )
        icon_polygon = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwY"
            b"AAACZUlEQVR4nO2aT0sVURjGf7qo0EVIEUUYiYFCFLRIsEViGXTzC1hgfYeSbFVt0o1pu3Kj"
            b"req61BbZoqCWldEHUFKvtJBKKPpH6Y0DT3AW/rn3zJxzz8j9wV3NnOd5z9yZOe/7noEqVaKh"
            b"G1gCZoGzKeoaLaNZAHIEwBgVPf8WQ0xkLsBEZn1PYjewbJmleWt1WRdpWV7eGJTRS48ez+Ux"
            b"4MvgIPAdWAPafZkAJ+XxEzjkw+ChrtQj/PNYXuNpCx8HVoHfQDP+OQz8kueJNIWf6QoNEY67"
            b"8pxOS7BTgl+APYSjAfgk73NJxWqBGYldJTzX5P1esThzRUIfgJ2EZ4fWKxPDZVeRXcCCRHqo"
            b"HBcVg8nv6lwEbkjgXdK/NSE1wGvF0u/yoH3W4DNUntOKZQXYW87Aexo4STxMKaaRUgc0aTH6"
            b"CxwlHlqAP1qUj5QyYEIzv098PFBs+a1ObFPC9g3YT3zsA74qxlObnfhCM75JvNxSjK/WO3hB"
            b"72lzwkegnnipV4zF9er7Quh6OSGFjeLN8kQW7AM562DWbq3zm9XL5oGKldul9A3s1+8B4n79"
            b"tm91cl4zNotPbIwqNlPTZzZFaS03RUGJWVGJWiw8UUzDrml8mt1EVzqsNL7svkF/RIXVG8Vy"
            b"3bXUnZeAKTcrxSVrzXAqdVHBH0vzoTeJkLml3krItGZC05dWO8hu0Dk9aAlosF44iRt0/5mW"
            b"oGljhmJYnk/TFD2mBTJUE7vJVxMbtfhLTg8SkpfXWJY3etrk8QNo9GUyEHDr7U6ozdC5LG+G"
            b"bpvt6W31wUBOk/H1CcfiRnV4lSqE5x+0Tyg887i34gAAAABJRU5ErkJggg=="
        )

        self.scene.context.kernel.register(
            "button/tool_polygon/tool_freehand",
            {
                "label": "Freehand",
                "icon": icons8_polygon_50,
                "tip": "Draw a freehand polygon (f)",
                "action": lambda v: self.set_designmode(0),
                "size": icon_size,
            },
        )

        self.scene.context.kernel.register(
            "button/tool_polygon/tool_polygon",
            {
                "label": "Regular",
                "icon": icon_polygon,
                "tip": "Draw a regular polygon (r)",
                "action": lambda v: self.set_designmode(1),
                "size": icon_size,
            },
        )

        self.scene.context.kernel.register(
            "button/tool_polygon/tool_star1",
            {
                "label": "Star 1",
                "icon": icon_regular_star,
                "tip": "Draw a regular star (1)",
                "action": lambda v: self.set_designmode(2),
                "size": icon_size,
            },
        )

        self.scene.context.kernel.register(
            "button/tool_polygon/tool_star2",
            {
                "label": "Star 2",
                "icon": icon_crossing_star,
                "tip": "Draw a crossing star (2)",
                "action": lambda v: self.set_designmode(3),
                "size": icon_size,
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
                pos = [space_pos[0], space_pos[1]]
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
