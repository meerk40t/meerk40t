from math import atan, cos, sin, sqrt, tau
from time import time

import wx

from meerk40t.core.units import Length
from meerk40t.gui.laserrender import (
    DRAW_MODE_BACKGROUND,
    DRAW_MODE_GRID,
    DRAW_MODE_GUIDES,
    swizzlecolor,
)
from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CHAIN
from meerk40t.gui.scene.widget import Widget


class GridWidget(Widget):
    """
    Interface Widget
    """

    def __init__(self, scene, name=None):
        Widget.__init__(self, scene, all=True)
        if name is None:
            self.name = "Standard"
        else:
            self.name = name
        self.grid = None
        self.grid2 = None
        self.background = None
        self.grid_line_pen = wx.Pen()
        self.grid_line_pen2 = wx.Pen()
        self.grid_line_pen3 = wx.Pen()
        self.last_ticksize = 0
        self.last_w = 0
        self.last_h = 0
        self.last_min_x = float("inf")
        self.last_min_y = float("inf")
        self.last_max_x = -float("inf")
        self.last_max_y = -float("inf")

        self.draw_grid = True
        self.sx = 0
        self.sy = 0
        self.sx2 = 0
        self.sy2 = 0
        self.cx = 0
        self.cy = 0
        # Min and max coords of the screen estate
        self.min_x = 0
        self.min_y = 0
        self.max_x = 0
        self.max_y = 0
        self.tlenx1 = 0
        self.tleny1 = 0
        self.tlenx2 = 0
        self.tleny2 = 0
        self.sxx1 = 0
        self.syy1 = 0
        self.sxx2 = 0
        self.syy2 = 0
        # Circular Grid
        self.min_radius = float("inf")
        self.max_radius = -float("inf")
        self.min_angle = 0
        self.max_angle = tau
        self.osv = -1
        self.sector = 0

        self.set_colors()

    def set_line_width(self, pen, line_width):
        # Sets the linewidth of a wx.pen
        # establish os-system
        if self.osv < 0:
            from platform import system

            sysname = system()
            if sysname == "Windows":
                # Windows
                self.osv = 0
            elif sysname == "Darwin":
                # Mac
                self.osv = 1
            else:
                # Linux
                self.osv = 2
        if self.osv == 0:
            # Windows
            pass  # no changes
        elif self.osv == 1:
            # Mac
            if line_width < 1:
                line_width = 1
        else:
            # Linux
            pass  # no changes
        try:
            pen.SetWidth(line_width)
        except TypeError:
            pen.SetWidth(int(line_width))

    def set_colors(self):
        self.grid_line_pen.SetColour(self.scene.colors.color_grid)
        self.grid_line_pen2.SetColour(self.scene.colors.color_grid2)
        self.grid_line_pen3.SetColour(self.scene.colors.color_grid3)
        self.set_line_width(self.grid_line_pen, 1)
        self.set_line_width(self.grid_line_pen2, 1)
        self.set_line_width(self.grid_line_pen3, 1)

    def hit(self):
        return HITCHAIN_HIT

    def event(
        self, window_pos=None, space_pos=None, event_type=None, nearest_snap=None
    ):
        """
        Capture and deal with events.
        """
        return RESPONSE_CHAIN

    def calculate_grid(self):
        """
        Based on the current matrix calculate the grid within the bed-space.
        """
        start_time = time()
        context = self.scene.context
        units_width = float(context.device.unit_width)
        units_height = float(context.device.unit_height)
        starts = []
        ends = []
        starts2 = []
        ends2 = []
        # Primary grid
        x = self.sxx1
        while x <= self.max_x:
            starts.append((x, 0.0))
            ends.append((x, units_height))
            x += self.tlenx1

        y = self.syy1
        while y <= self.max_y:
            starts.append((0.0, y))
            ends.append((units_width, y))
            y += self.tleny1

        # Secondary grid

        x = self.sxx2
        while x <= self.max_x:
            starts2.append((x, 0.0))
            ends2.append((x, units_height))
            x += self.tlenx2
        y = self.syy2
        while y <= self.max_y:
            starts2.append((0.0, y))
            ends2.append((units_width, y))
            y += self.tleny2

        self.grid = starts, ends
        self.grid2 = starts2, ends2
        end_time = time()
        # print ("Grid-Calc %s done, time=%.6f, grid1=%d, grid2=%d" % (self.name, end_time - start_time, len(starts), len(starts2)))

    def calculate_tickdistance(self, w, h):
        # Establish the delta for about 15 ticks
        wpoints = w / 30.0
        hpoints = h / 20.0
        points = (wpoints + hpoints) / 2
        scaled_conversion = (
            self.scene.context.device.length(
                str(1) + self.scene.context.units_name, as_float=True
            )
            * self.scene.widget_root.scene_widget.matrix.value_scale_x()
        )
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

        self.scene.tick_distance = delta1

    @staticmethod
    def calc_atan(dx, dy):
        if dx == 0:
            if dy < 0:
                c_angle = -1 / 4 * tau
                quadrant = 4
            elif dy == 0:
                c_angle = 0
                quadrant = 0
            else:
                c_angle = 1 / 4 * tau
                quadrant = 1
        elif dx > 0 and dy >= 0:
            # Quadrant 1: angle between 0 und 90 (0 - tau / 4)
            c_angle = atan(dy / dx)
            quadrant = 1
        elif dx < 0 and dy >= 0:
            # Quadrant 2: angle between 90 und 180 (1/4 tau - 2/4 tau)
            c_angle = atan(dy / dx) + tau / 2
            quadrant = 2
        elif dx < 0 and dy < 0:
            # Quadrant 3: angle between 180 und 270 (2/4 tau - 3/4 tau)
            c_angle = atan(dy / dx) + tau / 2
            quadrant = 3
        elif dx > 0 and dy < 0:
            # Quadrant 4: angle between 270 und 360 (2/4 tau - 3/4 tau)
            c_angle = atan(dy / dx)
            quadrant = 4
        # print ("Quadrant %d, angle=%.2f (%.2f)" % ( quadrant, c_angle, c_angle / tau * 360.0))
        return c_angle

    def calculate_gridsize(self, w, h):
        scaled_conversion = (
            self.scene.context.device.length(
                str(1) + self.scene.context.units_name, as_float=True
            )
            * self.scene.widget_root.scene_widget.matrix.value_scale_x()
        )
        points = self.scene.tick_distance * scaled_conversion

        p = self.scene.context

        self.sx = p.device.unit_width * p.device.show_origin_x
        self.sy = p.device.unit_height * p.device.show_origin_y

        if self.scene.grid_secondary_cx is None:
            self.sx2 = self.sx
        else:
            self.sx2 = self.scene.grid_secondary_cx
        if self.scene.grid_secondary_cy is None:
            self.sy2 = self.sy
        else:
            self.sy2 = self.scene.grid_secondary_cy

        if self.scene.grid_circular_cx is None:
            self.cx = self.sx
        else:
            self.cx = self.scene.grid_circular_cx
        if self.scene.grid_circular_cy is None:
            self.cy = self.sy
        else:
            self.cy = self.scene.grid_circular_cy

        self.min_x, self.min_y = self.scene.convert_window_to_scene([0, 0])
        self.min_x = max(0, self.min_x)
        self.min_y = max(0, self.min_y)
        self.max_x, self.max_y = self.scene.convert_window_to_scene([w, h])
        self.max_x = min(float(self.scene.context.device.unit_width), self.max_x)
        self.max_y = min(float(self.scene.context.device.unit_height), self.max_y)
        tlen = float(
            Length(
                "{value}{units}".format(
                    value=self.scene.tick_distance, units=self.scene.context.units_name
                )
            )
        )
        if tlen == 0:
            tlen = float(Length("10mm"))
        self.tlenx1 = tlen
        self.tleny1 = tlen
        self.sxx1 = round(self.min_x / self.tlenx1, 0) * (self.tlenx1 + 1)
        while self.sxx1 > self.min_x:
            self.sxx1 -= self.tlenx1
        if self.sxx1 < self.min_x:
            self.sxx1 += self.tlenx1
        self.syy1 = round(self.min_y / self.tleny1, 0) * (self.tleny1 + 1)
        while self.syy1 > self.min_y:
            self.syy1 -= self.tleny1
        if self.syy1 < self.min_y:
            self.syy1 += self.tleny1

        self.tlenx2 = tlen * self.scene.grid_secondary_scale_x
        self.tleny2 = tlen * self.scene.grid_secondary_scale_y
        self.sxx2 = round(self.min_x / self.tlenx2, 0) * (self.tlenx2 + 1)
        while self.sxx2 > self.min_x:
            self.sxx2 -= self.tlenx2
        if self.sxx2 < self.min_x:
            self.sxx2 += self.tlenx2
        self.syy2 = round(self.min_y / self.tleny2, 0) * (self.tleny2 + 1)
        while self.syy2 > self.min_y:
            self.syy2 -= self.tleny2
        if self.syy2 < self.min_y:
            self.syy2 += self.tleny2

        # lets establish which circles we really have to draw
        self.min_radius = float("inf")
        self.max_radius = -float("inf")
        test_points = (
            # all 4 corners
            (self.min_x, self.min_y),
            (self.min_x, self.max_y),
            (self.max_x, self.min_y),
            (self.max_x, self.max_y),
            # and the boundary points aligned with the center
            (self.cx, self.max_y),
            (self.cx, self.min_y),
            (self.min_x, self.cy),
            (self.max_x, self.cy),
        )
        for i, pt in enumerate(test_points):
            dx = pt[0] - self.cx
            dy = pt[1] - self.cy
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
        if self.cx <= self.min_x:
            # left
            if self.cy <= self.min_y:
                # below
                quadrant = 7
                pt1 = (self.min_x, self.max_y)
                pt2 = (self.max_x, self.min_y)
            elif self.cy >= self.max_y:
                # above
                quadrant = 1
                pt1 = (self.max_x, self.max_y)
                pt2 = (self.min_x, self.min_y)
            else:
                # between
                quadrant = 4
                pt1 = (self.min_x, self.max_y)
                pt2 = (self.min_x, self.min_y)
        elif self.cx >= self.max_x:
            # right
            if self.cy <= self.min_y:
                # below
                quadrant = 9
                pt1 = (self.min_x, self.min_y)
                pt2 = (self.max_x, self.max_y)
            elif self.cy >= self.max_y:
                # above
                quadrant = 3
                pt1 = (self.max_x, self.min_y)
                pt2 = (self.min_x, self.max_y)
            else:
                # between
                quadrant = 6
                pt1 = (self.max_x, self.min_y)
                pt2 = (self.max_x, self.max_y)
        else:
            # between
            if self.cy <= self.min_y:
                # below
                quadrant = 8
                pt1 = (self.min_x, self.min_y)
                pt2 = (self.max_x, self.min_y)
            elif self.cy >= self.max_y:
                # above
                quadrant = 2
                pt1 = (self.max_x, self.max_y)
                pt2 = (self.min_x, self.max_y)
            else:
                # between
                quadrant = 5
                pt1 = None
                pt2 = None
                min_a = 0
                max_a = tau
        self.sector = quadrant
        if not pt1 is None:
            dx1 = pt1[0] - self.cx
            dy1 = pt1[1] - self.cy
            dx2 = pt2[0] - self.cx
            dy2 = pt2[1] - self.cy
            max_a = self.calc_atan(dx1, dy1)
            min_a = self.calc_atan(dx2, dy2)

        while max_a < min_a:
            max_a += tau
        while min_a < 0:
            min_a += tau
            max_a += tau
        self.min_angle = min_a
        self.max_angle = max_a
        if self.min_x < self.cx < self.max_x and self.min_y < self.cy < self.max_y:
            self.min_radius = 0
        # print(
        #    "Min-Radius: %.1f, Max-Radius=%.1f, min-angle = %.2f (%.1f), max-angle=%.2f (%.1f)"
        #    % (
        #        self.min_radius,
        #        self.max_radius,
        #        self.min_angle,
        #        self.min_angle / tau * 360,
        #        self.max_angle,
        #        self.max_angle / tau * 360,
        #    )
        # )
        # print ("calculate_gridsize %s, tlen=%.1f" % (self.name, tlen))
        # print ("Min= %.1f, %.1f" % (self.min_x, self.min_y))
        # print ("Max= %.1f, %.1f" % (self.max_x, self.max_y))

    def calculate_grid_points(self):
        """
        Looks at all elements (all_points=True) or at non-selected elements (all_points=False) and identifies all
        attraction points (center, corners, sides)
        """
        from time import time

        start_time = time()
        prim_ct = 0
        second_ct = 0
        circ_ct = 0
        self.scene.grid_points = []  # Clear all

        # Let's add grid points - set the full grid
        p = self.scene.context
        if self.scene.draw_grid_primary:
            # That's easy just the rectangular stuff
            x = self.sxx1
            while x <= self.max_x:
                y = self.syy1
                while y <= self.max_y:
                    self.scene.grid_points.append([x, y])
                    y += self.tleny1
                x += self.tlenx1
        prim_ct = len(self.scene.grid_points)

        s_time_2 = time()
        if self.scene.draw_grid_secondary:
            # is it identical to the primary?
            if (
                not self.scene.draw_grid_primary
                or self.sx != 0
                or self.sy != 0
                or self.scene.grid_secondary_scale_x != 1
                or self.scene.grid_secondary_scale_y != 1
            ):
                x = self.sxx2
                while x <= self.max_x:
                    y = self.syy2
                    while y <= self.max_y:
                        self.scene.grid_points.append([x, y])
                        y += self.tleny2
                    x += self.tlenx2

        second_ct = len(self.scene.grid_points) - prim_ct

        s_time_3 = time()
        if self.scene.draw_grid_circular:
            # Okay, we are drawing on 48 segments line, even from center to outline, odd from 1/3rd to outline
            start_x = self.cx
            start_y = self.cy
            x = start_x
            y = start_y
            self.scene.grid_points.append([x, y])
            max_r = sqrt(
                p.device.unit_width * p.device.unit_width
                + p.device.unit_height * p.device.unit_height
            )
            tlen = (self.tlenx1 + self.tleny1) / 2
            r_fourth = max_r // (4 * tlen) * tlen
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
                    r += tlen

                while r <= self.max_radius:
                    r += tlen
                    x = start_x + r * cos(c_angle)
                    y = start_y + r * sin(c_angle)

                    if self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y:
                        self.scene.grid_points.append([x, y])

                i += 1
                r_angle += tau / segments
            circ_ct = len(self.scene.grid_points) - prim_ct - second_ct

        end_time = time()
        # print("Ready, time needed: %.6f, grid points added=%d (primary=%d, %.6f, secondary=%d, %.6f circ=%d, %.6f)" %
        #    (end_time - start_time,
        #    len(self.scene.grid_points),
        #    prim_ct, s_time_2-start_time,
        #    second_ct, s_time_3-s_time_2,
        #    circ_ct, end_time-s_time_3))

    def process_draw(self, gc):
        """
        Draw the grid on the scene.
        """
        # print ("GridWidget %s draw" % self.name)

        # Get proper gridsize
        w, h = gc.Size
        if self.scene.auto_tick:
            self.calculate_tickdistance(w, h)
        self.calculate_gridsize(w, h)

        # When do we need to redraw?!
        if self.last_ticksize != self.scene.tick_distance:
            self.last_ticksize = self.scene.tick_distance
            self.grid = None
        # With the new zoom-algorithm we also need to redraw if the origin
        # or the size have changed...
        # That's a price I am willing to pay...
        if self.last_w != w or self.last_h != h:
            self.last_w = w
            self.last_h = h
            self.grid = None
        if self.min_x != self.last_min_x or self.min_y != self.last_min_y:
            self.last_min_x = self.min_x
            self.last_min_y = self.min_y
            self.grid = None
        if self.max_x != self.last_max_x or self.max_y != self.last_max_y:
            self.last_max_x = self.max_x
            self.last_max_y = self.max_y
            self.grid = None

        if self.scene.context.draw_mode & DRAW_MODE_GRID == 0:
            if self.grid is None:
                self.calculate_grid()
                self.calculate_grid_points()

            starts, ends = self.grid
            starts2, ends2 = self.grid2

            matrix = self.scene.widget_root.scene_widget.matrix
            try:
                scale_x = matrix.value_scale_x()
                line_width = 1.0 / scale_x
            except (OverflowError, ValueError, ZeroDivisionError):
                matrix.reset()
                return
            self.set_line_width(self.grid_line_pen, line_width)
            self.set_line_width(self.grid_line_pen2, line_width)
            self.set_line_width(self.grid_line_pen3, line_width)

            gc.SetPen(self.grid_line_pen)
            brush = wx.Brush(
                colour=self.scene.colors.color_bed, style=wx.BRUSHSTYLE_TRANSPARENT
            )
            gc.SetBrush(brush)
            # While there is a bug in wxPython v4.1.1 and below that will not allow to apply a LineWidth bleow a given level:
            # At a matrix.value_scale_x value of about 17.2 and a corresponding line width of 0.058 everything looks good
            # but one step more with 18.9 and 0.053 the lines degenerate...
            # Interestingly this does not apply to arcs in a path, they remain at 1 pixel
            time1 = time()
            time_c = 0
            if self.scene.draw_grid_circular:
                gc.SetPen(self.grid_line_pen3)
                u_width = float(self.scene.context.device.unit_width)
                u_height = float(self.scene.context.device.unit_height)
                gc.Clip(0, 0, u_width, u_height)
                siz = sqrt(u_width * u_width + u_height * u_height)
                # print("Wid=%.1f, Ht=%.1f, siz=%.1f, step=%.1f, sx=%.1f, sy=%.1f" %(u_width, u_height, siz, step, self.sx, self.sy))
                # print("Wid=%s, Ht=%s, siz=%s, step=%s, sx=%s, sy=%s" %(Length(amount=u_width).length_mm, Length(amount=u_height).length_mm, Length(amount=siz).length_mm, Length(amount=step).length_mm, Length(amount=self.sx).length_mm, Length(amount=self.sy).length_mm))
                sox = self.cx / u_width
                soy = self.cy / u_height
                step = self.tlenx1
                factor = max(2 * (1 - sox), 2 * (1 - soy))
                # Initially I drew a complete circle, which is a waste in most situations,
                # so lets create a path
                circle_path = gc.CreatePath()
                y = 0
                while y < 2 * self.min_radius:
                    y += 2 * step
                time_c_s = time()
                while y < 2 * self.max_radius:
                    y += 2 * step
                    spoint_x = self.cx + y / 2 * cos(self.min_angle)
                    spoint_y = self.cx + y / 2 * sin(self.min_angle)
                    circle_path.MoveToPoint(spoint_x, spoint_y)
                    # gc.DrawEllipse(self.cx - y / 2, self.cy - y / 2, y, y)
                    circle_path.AddArc(
                        self.cx, self.cy, y / 2, self.min_angle, self.max_angle, True
                    )
                gc.StrokePath(circle_path)
                time_c += time() - time_c_s
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
                    font = wx.Font(fsize, wx.SWISS, wx.NORMAL, wx.BOLD)
                except TypeError:
                    font = wx.Font(int(fsize), wx.SWISS, wx.NORMAL, wx.BOLD)
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
                time_c_s = time()
                # Draw radials...
                while r_angle < self.max_angle:
                    c_angle = r_angle
                    while c_angle > tau:
                        c_angle -= tau
                    if i % 2 == 0:
                        degang = round(c_angle / tau * 360, 1)
                        if degang == 360:
                            degang = 0
                        a_text = "%.0f°" % degang
                        (t_width, t_height) = gc.GetTextExtent(a_text)
                        # Make sure text remains legible without breaking your neck... ;-)
                        if tau * 1 / 4 < c_angle < tau * 3 / 4:
                            myangle = (-1.0 * c_angle) + tau / 2
                            dx = t_width
                        else:
                            myangle = -1.0 * c_angle
                            dx = 0
                        if self.scene.context.draw_mode & DRAW_MODE_GUIDES == 0:
                            gc.DrawText(
                                a_text,
                                self.cx + cos(c_angle) * (mid_y + dx),
                                self.cy + sin(c_angle) * (mid_y + dx),
                                myangle,
                            )
                        s_factor = 0
                    else:
                        s_factor = 1
                    radials_start.append(
                        (
                            self.cx + s_factor * 0.5 * mid_y * cos(c_angle),
                            self.cy + s_factor * 0.5 * mid_y * sin(c_angle),
                        )
                    )
                    radials_end.append(
                        (
                            self.cx + 0.5 * y * cos(c_angle),
                            self.cy + 0.5 * y * sin(c_angle),
                        )
                    )
                    r_angle += tau / segments
                    i += 1
                if len(radials_start) > 0:
                    gc.StrokeLineSegments(radials_start, radials_end)
                time_c += time() - time_c_s
                gc.ResetClip()
            time2 = time()
            if self.scene.draw_grid_secondary:
                gc.SetPen(self.grid_line_pen2)
                grid_path = gc.CreatePath()
                if starts2 and ends2:
                    for i in range(len(starts2)):
                        grid_path.MoveToPoint(starts2[i][0], starts2[i][1])
                        grid_path.AddLineToPoint(ends2[i][0], ends2[i][1])
                    gc.StrokePath(grid_path)

                    # gc.StrokeLineSegments(starts2, ends2)
            time3 = time()
            if self.scene.draw_grid_primary:
                gc.SetPen(self.grid_line_pen)
                if starts and ends:
                    gc.StrokeLineSegments(starts, ends)
            time4 = time()
            scale_factor = self.scene.widget_root.scene_widget.matrix.value_scale_x()
            # print ("Draw done, ScaleFactor: %.5f, lwidth=%.5f, time needed: primary=%.5f, secondary=%.5f, circular=%.5f (%.5f)" % (scale_factor, 1.0/scale_factor, time4 - time3, time3 - time2, time2 - time1, time_c))

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which draw the background and updates the grid when needed to recalculate the lines
        """
        if signal == "grid":
            self.grid = None
        elif signal == "theme":
            self.set_colors()
