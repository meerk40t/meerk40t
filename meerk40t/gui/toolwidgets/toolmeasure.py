from math import sqrt, atan, tau
import wx
from meerk40t.core.units import Length
from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget


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
        self.pen = wx.Pen()
        self.pen.SetColour(self.scene.colors.color_manipulation)
        self.pen.SetStyle(wx.PENSTYLE_DOT)

    def process_draw(self, gc: wx.GraphicsContext):
        matrix = self.scene.matrix
        print("Scale-Factors, matrix=%.4f" % matrix.value_scale_x())
        if self.point_series:
            try:
                self.font_size = 14.0 / matrix.value_scale_x()
            except ZeroDivisionError:
                matrix.reset()
                return
            try:
                font = wx.Font(self.font_size, wx.SWISS, wx.NORMAL, wx.BOLD)
            except TypeError:
                font = wx.Font(int(self.font_size), wx.SWISS, wx.NORMAL, wx.BOLD)
            gc.SetFont(font, self.scene.colors.color_manipulation)
            gc.SetPen(self.pen)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            points = list(self.point_series)
            if self.mouse_position is not None:
                points.append(self.mouse_position)
            points.append(points[0])
            gc.DrawLines(points)
            first_point = None
            # https://www.wikihow.com/Calculate-the-Area-of-a-Polygon
            area_xy = 0
            area_yx = 0

            context = self.scene.context
            units = context.units_name

            pt_count = 0
            perimeter = 0
            all_cx = 0
            all_cy = 0
            print(points)
            for pt in points:
                pt_count += 1
                print("Pt %d, (%.1f, %.1f)" % (pt_count, pt[0], pt[1]))
                all_cx += pt[0]
                all_cy += pt[1]
                if not first_point is None:
                    area_xy += first_point[0] * pt[1]
                    area_yx += first_point[1] * pt[0]
                    print(
                        "Area, x*y =%.1f, y*x=%.1f, a=%.1f "
                        % (area_xy, area_yx, 0.5 * abs(area_xy - area_yx))
                    )
                    dx = pt[0] - first_point[0]
                    dy = pt[1] - first_point[1]
                    if dy == 0:
                        slope_angle = tau / 4
                    else:
                        slope = dx / dy
                        slope_angle = atan(slope)
                    dlen = sqrt(dx * dx + dy * dy)
                    cx = (pt[0] + first_point[0]) / 2
                    cy = (pt[1] + first_point[1]) / 2
                    perimeter += dlen
                    s_txt = str(Length(amount=dlen, digits=2, preferred_units=units))
                    (t_width, t_height) = gc.GetTextExtent(s_txt)
                    print("Line %d: %s" % (pt_count, s_txt))
                    gc.DrawText(
                        s_txt,
                        cx + 0.5 * t_height,
                        cy + 0.5 * t_width,
                        slope_angle,
                    )
                first_point = pt

            if pt_count > 2:
                all_cx = all_cx / pt_count
                all_cy = all_cy / pt_count
                area = 0.5 + abs(area_xy - area_yx)
                # perimeter is in base units, so back to units
                print("Area before: %.2f" % area)
                base_square = float(Length("1{units}".format(units=units)))
                base_square *= base_square
                print("base square: %.2f" % base_square)
                area = area / base_square
                print("Area after: %.5f" % area)

                s_txt = (
                    "Area: "
                    + str(Length(amount=area, digits=3, preferred_units=units))
                    + "²\nTotal Length: "
                    + str(Length(amount=perimeter, digits=1, preferred_units=units))
                )
                (t_width, t_height) = gc.GetTextExtent(s_txt)
                gc.DrawText(
                    s_txt,
                    all_cx + 0.5 * t_height,
                    all_cy + 0.5 * t_width,
                )
                print("Total: %s" % (s_txt))

    def event(self, window_pos=None, space_pos=None, event_type=None):
        response = RESPONSE_CHAIN
        if event_type == "leftclick":
            self.point_series.append((space_pos[0], space_pos[1]))
            self.scene.tool_active = True
            response = RESPONSE_CONSUME
        elif event_type == "rightdown":
            self.scene.tool_active = False
            self.point_series = []
            self.mouse_position = None
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        elif event_type == "hover":
            self.mouse_position = space_pos[0], space_pos[1]
            if self.point_series:
                self.scene.request_refresh()
        elif event_type == "doubleclick":
            self.scene.tool_active = False
            self.point_series = []
            self.mouse_position = None
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        elif event_type == "lost":
            self.scene.tool_active = False
            self.point_series = []
            self.mouse_position = None
        return response
