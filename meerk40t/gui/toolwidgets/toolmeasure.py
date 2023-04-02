from math import atan, cos, sin, sqrt, tau

import wx

from meerk40t.core.units import Length
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_ABORT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget

_ = wx.GetTranslation


class MeasureTool(ToolWidget):
    """
    Measuring Tool.

    Works like polygon but displays lengths at each side
    and after 3 points the covered area as well
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.point_series = []
        self.length_series = []
        self.mouse_position = None
        self.scene = scene
        self.line_pen = wx.Pen()
        self.line_pen.SetColour(self.scene.colors.color_measure_line)
        self.line_pen.SetStyle(wx.PENSTYLE_DOT)
        self.line_pen.SetWidth(1000)

    def process_draw(self, gc):
        matrix = gc.GetTransform().Get()
        if self.point_series:
            try:
                self.font_size = 10.0 / matrix[0]
            except ZeroDivisionError:
                self.font_size = 5000
                return
            # print ("Fontsize=%.3f, " % self.font_size)
            if self.font_size < 1.0:
                self.font_size = 1.0  # Mac does not allow values lower than 1.
            try:
                font = wx.Font(
                    self.font_size,
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_BOLD,
                )
            except TypeError:
                font = wx.Font(
                    int(self.font_size),
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_BOLD,
                )
            gc.SetFont(font, self.scene.colors.color_measure_text)

            gc.SetPen(self.line_pen)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            points = list(self.point_series)
            if self.mouse_position is not None:
                points.append(self.mouse_position)
            all_cx = 0
            all_cy = 0
            area_x_y = 0
            area_y_x = 0
            # https://www.wikihow.com/Calculate-the-Area-of-a-Polygon
            idx = -1
            last_x = 0
            last_y = 0
            for pt in points:
                idx += 1
                # print("%d, %.1f, %.1f" % (idx, pt[0],pt[1]))
                all_cx += pt[0]
                all_cy += pt[1]
                if idx > 0:
                    area_x_y += last_x * pt[1]
                    area_y_x += last_y * pt[0]
                last_x = pt[0]
                last_y = pt[1]

            # Complete calculation of area by closing the loop
            area_x_y += last_x * points[0][1]
            area_y_x += last_y * points[0][0]
            area = 0.5 * abs(area_x_y - area_y_x)

            points.append(points[0])
            first_point = None

            context = self.scene.context
            units = context.units_name

            pt_count = 0
            perimeter = 0
            for pt in points:
                pt_count += 1
                if first_point is not None:
                    dx = pt[0] - first_point[0]
                    dy = pt[1] - first_point[1]
                    if dx == 0:
                        slope = 0
                        slope_angle = tau / 4
                    else:
                        slope = dy / dx
                        slope_angle = -1 * atan(slope)
                    dlen = sqrt(dx * dx + dy * dy)
                    cx = (pt[0] + first_point[0]) / 2
                    cy = (pt[1] + first_point[1]) / 2

                    perimeter += dlen

                    s_txt = str(Length(amount=dlen, digits=2, preferred_units=units))
                    (t_width, t_height) = gc.GetTextExtent(s_txt)

                    tcx = cx - cos(slope_angle) * t_width / 2
                    tcy = cy + sin(slope_angle) * t_width / 2
                    dx = tcx - cx
                    dy = tcy - dy
                    gc.DrawText(s_txt, tcx, tcy, slope_angle)
                first_point = pt

            if pt_count > 3:
                # remove last point, as this one coincides with the first...
                pt_count -= 1
                all_cx = all_cx / pt_count
                all_cy = all_cy / pt_count
                # area is in base units^2, so back to units

                base_square = float(Length(f"1{units}"))
                base_square *= base_square
                area = area / base_square
                s_area = _("Area")
                s_perim = _("Perimeter")
                s_txt = (
                    f"{s_area}={area:.1f}{units}²\n{s_perim}: "
                    f"{str(Length(amount=perimeter, digits=1, preferred_units=units))}"
                )
                t_width, t_height = gc.GetTextExtent(s_txt)
                gc.DrawText(
                    s_txt,
                    all_cx - 0.5 * t_width,
                    all_cy - 0.5 * t_height,
                )

            # Draw lines at last to make them more visible
            gc.DrawLines(points)

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
            if nearest_snap is None:
                self.point_series.append((space_pos[0], space_pos[1]))
            else:
                self.point_series.append((nearest_snap[0], nearest_snap[1]))
            self.scene.pane.tool_active = True
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
        elif event_type == "rightdown":
            self.scene.pane.tool_active = False
            self.point_series = []
            self.mouse_position = None
            self.scene.request_refresh()
            response = RESPONSE_ABORT
        elif event_type == "doubleclick":
            self.scene.pane.tool_active = False
            self.point_series = []
            self.mouse_position = None
            self.scene.request_refresh()
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
        return response
