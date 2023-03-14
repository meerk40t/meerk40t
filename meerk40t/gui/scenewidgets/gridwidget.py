from math import atan2, cos, sin, sqrt, tau
from platform import system

import wx

from meerk40t.core.units import Length
from meerk40t.gui.laserrender import DRAW_MODE_GRID, DRAW_MODE_GUIDES
from meerk40t.gui.scene.widget import Widget


class GridWidget(Widget):
    """
    Interface Widget
    """

    def __init__(self, scene, name=None, suppress_labels=False):
        Widget.__init__(self, scene, all=True)
        if name is None:
            self.name = "Standard"
        else:
            self.name = name
        self.primary_grid_lines = None
        self.secondary_grid_lines = None
        self.background = None
        self.primary_grid_line_pen = wx.Pen()
        self.secondary_grid_line_pen = wx.Pen()
        self.circular_grid_line_pen = wx.Pen()
        self.last_ticksize = 0
        self.last_w = 0
        self.last_h = 0
        self.last_min_x = float("inf")
        self.last_min_y = float("inf")
        self.last_max_x = -float("inf")
        self.last_max_y = -float("inf")
        if suppress_labels is None:
            suppress_labels = False
        self.suppress_labels_in_all_cases = suppress_labels

        self.draw_grid = True
        self.primary_start_x = 0
        self.primary_start_y = 0
        self.secondary_start_x = 0
        self.secondary_start_y = 0
        self.circular_grid_center_x = 0
        self.circular_grid_center_y = 0
        # Min and max coords of the screen estate
        self.min_x = 0
        self.min_y = 0
        self.max_x = 0
        self.max_y = 0
        self.primary_tick_length_x = 0
        self.primary_tick_length_y = 0
        self.secondary_tick_length_x = 0
        self.secondary_tick_length_y = 0
        self.zero_x = 0
        self.zero_y = 0
        # Circular Grid
        self.min_radius = float("inf")
        self.max_radius = -float("inf")
        self.min_angle = 0
        self.max_angle = tau
        self.os = system()

        self.set_colors()

    @property
    def scene_scale(self):
        matrix = self.scene.widget_root.scene_widget.matrix
        try:
            return sqrt(abs(matrix.determinant))
        except (OverflowError, ValueError, ZeroDivisionError):
            matrix.reset()
        return 1.0

    ###########################
    # PEN SETUP
    ###########################

    def set_line_width(self, pen, line_width):
        # Sets the linewidth of a wx.pen
        # establish os-system
        if line_width < 1 and self.os == "Darwin":
            # Mac
            line_width = 1
        try:
            pen.SetWidth(line_width)
        except TypeError:
            pen.SetWidth(int(line_width))

    def _set_pen_width_from_matrix(self):
        line_width = 1.0 / self.scene_scale
        self.set_line_width(self.primary_grid_line_pen, line_width)
        self.set_line_width(self.secondary_grid_line_pen, line_width)
        self.set_line_width(self.circular_grid_line_pen, line_width)

    def set_colors(self):
        self.primary_grid_line_pen.SetColour(self.scene.colors.color_grid)
        self.secondary_grid_line_pen.SetColour(self.scene.colors.color_grid2)
        self.circular_grid_line_pen.SetColour(self.scene.colors.color_grid3)
        self.set_line_width(self.primary_grid_line_pen, 1)
        self.set_line_width(self.secondary_grid_line_pen, 1)
        self.set_line_width(self.circular_grid_line_pen, 1)

    ###########################
    # CALCULATE GRID LINES
    ###########################

    def _calc_primary_grid_lines(self):
        starts = []
        ends = []
        # Primary grid
        # We could be way too high
        start_x = self.zero_x
        while start_x - self.primary_tick_length_x > self.min_x:
            start_x -= self.primary_tick_length_x
        start_y = self.zero_y
        while start_y - self.primary_tick_length_y > self.min_y:
            start_y -= self.primary_tick_length_y
        # But we could be way too low, too
        while start_x < self.min_x:
            start_x += self.primary_tick_length_x
        while start_y < self.min_y:
            start_y += self.primary_tick_length_y

        x = start_x
        while x <= self.max_x:
            starts.append((x, self.min_y))
            ends.append((x, self.max_y))
            x += self.primary_tick_length_x

        y = start_y
        while y <= self.max_y:
            starts.append((self.min_x, y))
            ends.append((self.max_x, y))
            y += self.primary_tick_length_y
        self.primary_grid_lines = starts, ends

    def _calc_secondary_grid_lines(self):
        starts2 = []
        ends2 = []
        # Primary grid
        # Secondary grid
        # We could be way too high
        start_x = self.zero_x
        while start_x - self.secondary_tick_length_x > self.min_x:
            start_x -= self.secondary_tick_length_x
        start_y = self.zero_y
        while start_y - self.secondary_tick_length_y > self.min_y:
            start_y -= self.secondary_tick_length_y
        # But we could be way too low, too
        while start_x < self.min_x:
            start_x += self.secondary_tick_length_x
        while start_y < self.min_y:
            start_y += self.secondary_tick_length_y

        x = start_x
        while x <= self.max_x:
            starts2.append((x, self.min_y))
            ends2.append((x, self.max_y))
            x += self.secondary_tick_length_x

        y = start_y
        while y <= self.max_y:
            starts2.append((self.min_x, y))
            ends2.append((self.max_x, y))
            y += self.secondary_tick_length_y
        self.secondary_grid_lines = starts2, ends2

    def calculate_grid_lines(self):
        """
        Based on the current matrix calculate the grid within the bed-space.
        """
        d = self.scene.context.device
        self.zero_x = d.unit_width * d.show_origin_x
        self.zero_y = d.unit_height * d.show_origin_y
        self._calc_primary_grid_lines()
        self._calc_secondary_grid_lines()

    ###########################
    # CALCULATE PROPERTIES
    ###########################

    @property
    def scaled_conversion(self):
        return (
            self.scene.context.device.length(
                f"1{self.scene.context.units_name}",
                as_float=True,
            )
            * self.scene_scale
        )

    def calculate_tickdistance(self, w, h):
        # Establish the delta for about 15 ticks
        wpoints = w / 30.0
        hpoints = h / 20.0
        points = (wpoints + hpoints) / 2
        scaled_conversion = self.scaled_conversion
        if scaled_conversion == 0:
            return
        # tweak the scaled points into being useful.
        # points = scaled_conversion * round(points / scaled_conversion * 10.0) / 10.0
        delta = points / scaled_conversion
        # Let's establish a proper delta: we want to understand the log and x.yyy multiplikator
        x = delta
        factor = 1
        if x >= 1:
            while x >= 10:
                x *= 0.1
                factor *= 10
        else:
            while x < 1:
                x *= 10
                factor *= 0.1

        l_pref = delta / factor
        # Assign 'useful' scale
        if l_pref < 3:
            l_pref = 1
        # elif l_pref < 4:
        #    l_pref = 2.5
        else:
            l_pref = 5.0

        delta1 = l_pref * factor
        # print("New Delta={delta}".format(delta=delta))
        # points = self.scaled_conversion * float("{:.1g}".format(points / self.scaled_conversion))

        self.scene.pane.tick_distance = delta1

    def calculate_center_start(self):
        p = self.scene.context
        self.primary_start_x = p.device.unit_width * p.device.show_origin_x
        self.primary_start_y = p.device.unit_height * p.device.show_origin_y

        if self.scene.pane.grid_secondary_cx is None:
            self.secondary_start_x = self.primary_start_x
        else:
            self.secondary_start_x = self.scene.pane.grid_secondary_cx

        if self.scene.pane.grid_secondary_cy is None:
            self.secondary_start_y = self.primary_start_y
        else:
            self.secondary_start_y = self.scene.pane.grid_secondary_cy

        if self.scene.pane.grid_circular_cx is None:
            self.circular_grid_center_x = self.primary_start_x
        else:
            self.circular_grid_center_x = self.scene.pane.grid_circular_cx

        if self.scene.pane.grid_circular_cy is None:
            self.circular_grid_center_y = self.primary_start_y
        else:
            self.circular_grid_center_y = self.scene.pane.grid_circular_cy

    def calculate_gridsize(self, w, h):
        self.min_x = float("inf")
        self.max_x = -float("inf")
        self.min_y = float("inf")
        self.max_y = -float("inf")
        for xx in (0, w):
            for yy in (0, h):
                x, y = self.scene.convert_window_to_scene([xx, yy])
                self.min_x = min(self.min_x, x)
                self.min_y = min(self.min_y, y)
                self.max_x = max(self.max_x, x)
                self.max_y = max(self.max_y, y)

        # self.min_x, self.min_y = self.scene.convert_window_to_scene([0, 0])
        # self.max_x, self.max_y = self.scene.convert_window_to_scene([w, h])

        self.min_x = max(0, self.min_x)
        self.min_y = max(0, self.min_y)
        self.max_x = min(float(self.scene.context.device.unit_width), self.max_x)
        self.max_y = min(float(self.scene.context.device.unit_height), self.max_y)

    def calculate_tick_length(self):
        tick_length = float(
            Length(f"{self.scene.pane.tick_distance}{self.scene.context.units_name}")
        )
        if tick_length == 0:
            tick_length = float(Length("10mm"))
        self.primary_tick_length_x = tick_length
        self.primary_tick_length_y = tick_length
        # print (f"x={self.tlenx1} ({Length(amount=self.tlenx1, digits=3).length_mm})")
        # print (f"y={self.tleny1} ({Length(amount=self.tleny1, digits=3).length_mm})")
        self.secondary_tick_length_x = self.primary_tick_length_x * self.scene.pane.grid_secondary_scale_x
        self.secondary_tick_length_y = self.primary_tick_length_y * self.scene.pane.grid_secondary_scale_y

    def calculate_radii_angles(self):
        # let's establish which circles we really have to draw
        self.min_radius = float("inf")
        self.max_radius = -float("inf")
        test_points = (
            # all 4 corners
            (self.min_x, self.min_y),
            (self.min_x, self.max_y),
            (self.max_x, self.min_y),
            (self.max_x, self.max_y),
            # and the boundary points aligned with the center
            (self.circular_grid_center_x, self.max_y),
            (self.circular_grid_center_x, self.min_y),
            (self.min_x, self.circular_grid_center_y),
            (self.max_x, self.circular_grid_center_y),
        )
        for i, pt in enumerate(test_points):
            dx = pt[0] - self.circular_grid_center_x
            dy = pt[1] - self.circular_grid_center_y
            r = sqrt(dx * dx + dy * dy)
            if r < self.min_radius:
                self.min_radius = r
            if r > self.max_radius:
                self.max_radius = r

        # 1 | 2 | 3
        # --+---+--
        # 4 | 5 | 6
        # --+---+--
        # 7 | 8 | 9
        min_a = float("inf")
        max_a = -float("inf")
        if self.circular_grid_center_x <= self.min_x:
            # left
            if self.circular_grid_center_y <= self.min_y:
                # below
                pt1 = (self.min_x, self.max_y)
                pt2 = (self.max_x, self.min_y)
            elif self.circular_grid_center_y >= self.max_y:
                # above
                pt1 = (self.max_x, self.max_y)
                pt2 = (self.min_x, self.min_y)
            else:
                # between
                pt1 = (self.min_x, self.max_y)
                pt2 = (self.min_x, self.min_y)
        elif self.circular_grid_center_x >= self.max_x:
            # right
            if self.circular_grid_center_y <= self.min_y:
                # below
                pt1 = (self.min_x, self.min_y)
                pt2 = (self.max_x, self.max_y)
            elif self.circular_grid_center_y >= self.max_y:
                # above
                pt1 = (self.max_x, self.min_y)
                pt2 = (self.min_x, self.max_y)
            else:
                # between
                pt1 = (self.max_x, self.min_y)
                pt2 = (self.max_x, self.max_y)
        else:
            # between
            if self.circular_grid_center_y <= self.min_y:
                # below
                pt1 = (self.min_x, self.min_y)
                pt2 = (self.max_x, self.min_y)
            elif self.circular_grid_center_y >= self.max_y:
                # above
                pt1 = (self.max_x, self.max_y)
                pt2 = (self.min_x, self.max_y)
            else:
                # between
                pt1 = None
                pt2 = None
                min_a = 0
                max_a = tau
        if pt1 is not None:
            dx1 = pt1[0] - self.circular_grid_center_x
            dy1 = pt1[1] - self.circular_grid_center_y
            dx2 = pt2[0] - self.circular_grid_center_x
            dy2 = pt2[1] - self.circular_grid_center_y
            max_a = atan2(dy1, dx1)
            min_a = atan2(dy2, dx2)

        while max_a < min_a:
            max_a += tau
        while min_a < 0:
            min_a += tau
            max_a += tau
        self.min_angle = min_a
        self.max_angle = max_a
        if (
            self.min_x < self.circular_grid_center_x < self.max_x
            and self.min_y < self.circular_grid_center_y < self.max_y
        ):
            self.min_radius = 0

    ###########################
    # CALCULATE GRID POINTS
    ###########################

    def calculate_scene_grid_points(self):
        """
        Looks at all elements (all_points=True) or at non-selected elements (all_points=False)
        and identifies all attraction points (center, corners, sides)
        Notabene this calculation generates SCREEN coordinates
        """
        self.scene.grid_points = []  # Clear all

        # Let's add grid points - set just the visible part of the grid

        if self.scene.pane.draw_grid_primary:
            self._calculate_grid_points_primary()
        if self.scene.pane.draw_grid_secondary:
            self._calculate_grid_points_secondary()
        if self.scene.pane.draw_grid_circular:
            self._calculate_grid_points_circular()

    def _calculate_grid_points_primary(self):
        # That's easy just the rectangular stuff
        # We could be way too high
        start_x = self.zero_x
        while start_x - self.primary_tick_length_x > self.min_x:
            start_x -= self.primary_tick_length_x
        start_y = self.zero_y
        while start_y - self.primary_tick_length_y > self.min_y:
            start_y -= self.primary_tick_length_y
        # But we could be way too low, too
        while start_x < self.min_x:
            start_x += self.primary_tick_length_x
        while start_y < self.min_y:
            start_y += self.primary_tick_length_y
        x = start_x
        while x <= self.max_x:
            y = start_y
            while y <= self.max_y:
                # mx, my = self.scene.convert_scene_to_window([x, y])
                self.scene.grid_points.append([x, y])
                y += self.primary_tick_length_y
            x += self.primary_tick_length_x

    def _calculate_grid_points_secondary(self):
        if (
            self.scene.pane.draw_grid_primary
            and self.primary_start_x == 0
            and self.primary_start_y == 0
            and self.scene.pane.grid_secondary_scale_x == 1
            and self.scene.pane.grid_secondary_scale_y == 1
        ):
            return  # is it identical to the primary?
        # We could be way too high
        start_x = self.zero_x
        while start_x - self.secondary_tick_length_x > self.min_x:
            start_x -= self.secondary_tick_length_x
        start_y = self.zero_y
        while start_y - self.secondary_tick_length_y > self.min_y:
            start_y -= self.secondary_tick_length_y
        # But we could be way too low, too
        while start_x < self.min_x:
            start_x += self.secondary_tick_length_x
        while start_y < self.min_y:
            start_y += self.secondary_tick_length_y
        x = start_x
        while x <= self.max_x:
            y = start_y
            while y <= self.max_y:
                # mx, my = self.scene.convert_scene_to_window([x, y])
                self.scene.grid_points.append([x, y])
                y += self.secondary_tick_length_y
            x += self.secondary_tick_length_x

    def _calculate_grid_points_circular(self):
        p = self.scene.context
        # Okay, we are drawing on 48 segments line, even from center to outline, odd from 1/3rd to outline
        start_x = self.circular_grid_center_x
        start_y = self.circular_grid_center_y
        x = start_x
        y = start_y
        # mx, my = self.scene.convert_scene_to_window([x, y])
        self.scene.grid_points.append([x, y])
        max_r = abs(complex(p.device.unit_width, p.device.unit_height))  # hypot
        tick_length = (self.primary_tick_length_x + self.primary_tick_length_y) / 2
        r_fourth = max_r // (4 * tick_length) * tick_length
        segments = 48
        r_angle = 0
        i = 0
        while r_angle < self.min_angle:
            r_angle += tau / segments
            i += 1
        while r_angle < self.max_angle:
            c_angle = r_angle
            while c_angle > tau:
                c_angle -= tau
            if i % 2 == 0:
                r = 0
            else:
                r = r_fourth
            while r < self.min_radius:
                r += tick_length

            while r <= self.max_radius:
                r += tick_length
                x = start_x + r * cos(c_angle)
                y = start_y + r * sin(c_angle)

                if self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y:
                    # mx, my = self.scene.convert_scene_to_window([x, y])
                    self.scene.grid_points.append([x, y])

            i += 1
            r_angle += tau / segments

    ###########################
    # WIDGET DRAW AND PROCESS
    ###########################

    def process_draw(self, gc):
        """
        Draw the grid on the scene.
        """
        # print ("GridWidget %s draw" % self.name)

        # Get proper gridsize
        w, h = gc.Size
        if w < 50 or h < 50:
            # Algorithm is unstable for very low values of w or h.
            return
        if self.scene.pane.auto_tick:
            self.calculate_tickdistance(w, h)
        self.calculate_center_start()
        self.calculate_gridsize(w, h)
        self.calculate_tick_length()
        self.calculate_radii_angles()

        # When do we need to redraw?!
        if self.last_ticksize != self.scene.pane.tick_distance:
            self.last_ticksize = self.scene.pane.tick_distance
            self.primary_grid_lines = None
        # With the new zoom-algorithm we also need to redraw if the origin
        # or the size have changed...
        # That's a price I am willing to pay...
        if self.last_w != w or self.last_h != h:
            self.last_w = w
            self.last_h = h
            self.primary_grid_lines = None
        if self.min_x != self.last_min_x or self.min_y != self.last_min_y:
            self.last_min_x = self.min_x
            self.last_min_y = self.min_y
            self.primary_grid_lines = None
        if self.max_x != self.last_max_x or self.max_y != self.last_max_y:
            self.last_max_x = self.max_x
            self.last_max_y = self.max_y
            self.primary_grid_lines = None

        if self.scene.context.draw_mode & DRAW_MODE_GRID != 0:
            return  # Do not draw grid.

        if self.primary_grid_lines is None or self.secondary_grid_lines is None:
            self.calculate_grid_lines()
            self.calculate_scene_grid_points()

        self._set_pen_width_from_matrix()

        gc.SetPen(self.primary_grid_line_pen)
        brush = wx.Brush(
            colour=self.scene.colors.color_bed, style=wx.BRUSHSTYLE_TRANSPARENT
        )
        gc.SetBrush(brush)
        # There is a bug in wxPython v4.1.1 and below that will not allow to apply a LineWidth below a given level:
        # At a matrix scale value of about 17.2 and a corresponding line width of 0.058 everything looks good
        # but one step more with 18.9 and 0.053 the lines degenerate...
        # Interestingly, this does not apply to arcs in a path, they remain at 1 pixel.
        if self.scene.pane.draw_grid_circular:
            self._draw_grid_circular(gc)
        if self.scene.pane.draw_grid_secondary:
            self._draw_grid_secondary(gc)
        if self.scene.pane.draw_grid_primary:
            self._draw_grid_primary(gc)

    def _draw_grid_primary(self, gc):
        starts, ends = self.primary_grid_lines
        gc.SetPen(self.primary_grid_line_pen)
        grid_path = gc.CreatePath()
        if starts and ends:
            for i in range(len(starts)):
                sx = starts[i][0]
                sy = starts[i][1]
                grid_path.MoveToPoint(sx, sy)
                sx = ends[i][0]
                sy = ends[i][1]
                grid_path.AddLineToPoint(sx, sy)
            gc.StrokePath(grid_path)

    def _draw_grid_secondary(self, gc):
        starts2, ends2 = self.secondary_grid_lines
        gc.SetPen(self.secondary_grid_line_pen)
        grid_path = gc.CreatePath()
        if starts2 and ends2:
            for i in range(len(starts2)):
                sx = starts2[i][0]
                sy = starts2[i][1]
                grid_path.MoveToPoint(sx, sy)
                sx = ends2[i][0]
                sy = ends2[i][1]
                grid_path.AddLineToPoint(sx, sy)
            gc.StrokePath(grid_path)

            # gc.StrokeLineSegments(starts2, ends2)

    def _draw_grid_circular(self, gc):
        gc.SetPen(self.circular_grid_line_pen)
        u_width = float(self.scene.context.device.unit_width)
        u_height = float(self.scene.context.device.unit_height)
        gc.Clip(0, 0, u_width, u_height)
        siz = sqrt(u_width * u_width + u_height * u_height)
        sox = self.circular_grid_center_x / u_width
        soy = self.circular_grid_center_y / u_height
        step = self.primary_tick_length_x
        factor = max(2 * (1 - sox), 2 * (1 - soy))
        # Initially I drew a complete circle, which is a waste in most situations,
        # so let's create a path
        circle_path = gc.CreatePath()
        y = 0
        while y < 2 * self.min_radius:
            y += 2 * step
        while y < 2 * self.max_radius:
            y += 2 * step
            spoint_x = self.circular_grid_center_x + y / 2 * cos(self.min_angle)
            spoint_y = self.circular_grid_center_x + y / 2 * sin(self.min_angle)
            circle_path.MoveToPoint(spoint_x, spoint_y)
            # gc.DrawEllipse(self.cx - y / 2, self.cy - y / 2, y, y)
            circle_path.AddArc(
                self.circular_grid_center_x,
                self.circular_grid_center_y,
                y / 2,
                self.min_angle,
                self.max_angle,
                True,
            )
        gc.StrokePath(circle_path)
        # circle_path.AddArc(self.cx, self.cy, y, self.min_angle, self.max_angle)
        # (around one fourth of radius)
        mid_y = y // (4 * step) * step
        # print("Last Y=%.1f (%s), mid_y=%.1f (%s)" % (y, Length(amount=y).length_mm, mid_y, Length(amount=mid_y).length_mm))
        radials_start = []
        radials_end = []
        fsize = 10 / self.scene.widget_root.scene_widget.matrix.value_scale_x()
        if fsize < 1.0:
            fsize = 1.0  # Mac does not allow values lower than 1.
        try:
            font = wx.Font(
                fsize,
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD,
            )
        except TypeError:
            font = wx.Font(
                int(fsize),
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD,
            )
        # gc.SetFont(font, wx.BLACK)
        # debugstr = "Angle= %.1f - %.1f (%d)" % (self.min_angle/tau*360, self.max_angle/tau*360, self.sector)
        # gc.DrawText(debugstr, (self.min_x + self.max_x)/2, (self.min_y + self.max_y)/2)
        gc.SetFont(font, self.scene.colors.color_guide3)
        segments = 48
        r_angle = 0
        i = 0
        while r_angle < self.min_angle:
            r_angle += tau / segments
            i += 1

        # Draw radials...
        while r_angle < self.max_angle:
            c_angle = r_angle
            while c_angle > tau:
                c_angle -= tau
            if i % 2 == 0:
                degang = round(c_angle / tau * 360, 1)
                if degang == 360:
                    degang = 0
                a_text = f"{degang:.0f}°"
                (t_width, t_height) = gc.GetTextExtent(a_text)
                # Make sure text remains legible without breaking your neck... ;-)
                if tau * 1 / 4 < c_angle < tau * 3 / 4:
                    myangle = (-1.0 * c_angle) + tau / 2
                    dx = t_width
                else:
                    myangle = -1.0 * c_angle
                    dx = 0
                if (
                    self.scene.context.draw_mode & DRAW_MODE_GUIDES == 0
                    or self.suppress_labels_in_all_cases
                ):
                    gc.DrawText(
                        a_text,
                        self.circular_grid_center_x + cos(c_angle) * (mid_y + dx),
                        self.circular_grid_center_y + sin(c_angle) * (mid_y + dx),
                        myangle,
                    )
                s_factor = 0
            else:
                s_factor = 1
            radials_start.append(
                (
                    self.circular_grid_center_x + s_factor * 0.5 * mid_y * cos(c_angle),
                    self.circular_grid_center_y + s_factor * 0.5 * mid_y * sin(c_angle),
                )
            )
            radials_end.append(
                (
                    self.circular_grid_center_x + 0.5 * y * cos(c_angle),
                    self.circular_grid_center_y + 0.5 * y * sin(c_angle),
                )
            )
            r_angle += tau / segments
            i += 1
        if len(radials_start) > 0:
            gc.StrokeLineSegments(radials_start, radials_end)
        gc.ResetClip()

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which draw the background and updates the grid when needed to recalculate the lines
        """
        if signal == "grid":
            self.primary_grid_lines = None
        elif signal == "theme":
            self.set_colors()
