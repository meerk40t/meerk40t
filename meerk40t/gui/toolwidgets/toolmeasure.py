from math import atan2, cos, sin, sqrt, tau

import wx

from meerk40t.core.units import Length
from meerk40t.gui.wxutils import get_matrix_scale, get_gc_scale, dip_size

from .toolpointlistbuilder import PointListTool

_ = wx.GetTranslation


class MeasureTool(PointListTool):
    """
    Measuring Tool.

    Works like polygon but displays lengths at each side
    and after 3 points the covered area as well
    """

    def __init__(self, scene, mode=None):
        PointListTool.__init__(self, scene, mode=mode)
        self.line_pen = wx.Pen()
        self.line_pen.SetColour(self.scene.colors.color_measure_line)
        self.line_pen.SetStyle(wx.PENSTYLE_DOT)
        self.line_pen.SetWidth(1000)
        fact = dip_size(self.scene.pane, 100, 100)
        self.font_size_factor = (fact[0] + fact[1]) / 100 * 0.5

    def create_node(self):
        # No need to create anything
        return

    def point_added(self):
        # Nothing particular to do here
        return

    def draw_points(self, gc, points):
        if not self.point_series:
            return
        mat_fact = get_gc_scale(gc)
        try:
            font_size = 10.0 / mat_fact
        except ZeroDivisionError:
            font_size = 5000
        if font_size > 1e8:
            font_size = 5000
        font_size *= self.font_size_factor            
        # print ("Fontsize=%.3f, " % self.font_size)
        if font_size < 1.0:
            font_size = 1.0  # Mac does not allow values lower than 1.
        try:
            font = wx.Font(
                font_size,
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD,
            )
        except TypeError:
            font = wx.Font(
                int(font_size),
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD,
            )
        gc.SetFont(font, self.scene.colors.color_measure_text)

        # matrix = self.parent.matrix
        # linewidth = 2.0 / matrix_scale(matrix)
        try:
            linewidth = 2.0 / mat_fact
        except ZeroDivisionError:
            linewidth = 2000
        if linewidth < 1:
            linewidth = 1
        try:
            self.line_pen.SetWidth(linewidth)
        except TypeError:
            self.line_pen.SetWidth(int(linewidth))
        gc.SetPen(self.line_pen)
        gc.SetBrush(wx.TRANSPARENT_BRUSH)
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
                    slope_angle = tau / 4
                else:
                    slope_angle = -1 * atan2(dy, dx)
                dlen = sqrt(dx * dx + dy * dy)
                cx = (pt[0] + first_point[0]) / 2
                cy = (pt[1] + first_point[1]) / 2

                perimeter += dlen

                s_txt = str(Length(amount=dlen, digits=2, preferred_units=units))
                (t_width, t_height) = gc.GetTextExtent(s_txt)

                tcx = cx - cos(slope_angle) * t_width / 2
                tcy = cy + sin(slope_angle) * t_width / 2
                # dx = tcx - cx
                # dy = tcy - dy
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
