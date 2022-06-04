from math import cos, sin, sqrt, tau

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

    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self.grid = None
        self.grid2 = None
        self.background = None
        self.grid_line_pen = wx.Pen()
        self.grid_line_pen2 = wx.Pen()
        self.grid_line_pen3 = wx.Pen()
        self.last_ticksize = 0
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

        self.set_colors()

    def set_colors(self):
        self.grid_line_pen.SetColour(self.scene.colors.color_grid)
        self.grid_line_pen.SetWidth(1)
        self.grid_line_pen2.SetColour(self.scene.colors.color_grid2)
        self.grid_line_pen2.SetWidth(1)
        self.grid_line_pen3.SetColour(self.scene.colors.color_grid3)
        self.grid_line_pen3.SetWidth(1)

    def hit(self):
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        """
        Capture and deal with the double click event.

        Doubleclick in the grid loads a menu to remove the background.
        """
        if event_type == "hover":
            return RESPONSE_CHAIN
        elif event_type == "doubleclick":
            menu = wx.Menu()
            _ = self.scene.context._
            if self.background is not None:
                item = menu.Append(wx.ID_ANY, _("Remove Background"), "")
                self.scene.gui.Bind(
                    wx.EVT_MENU,
                    lambda e: self.scene.gui.signal("background", None),
                    id=item.GetId(),
                )
                if menu.MenuItemCount != 0:
                    self.scene.gui.PopupMenu(menu)
                    menu.Destroy()
        self.grid = None
        return RESPONSE_CHAIN

    def calculate_grid(self):
        """
        Based on the current matrix calculate the grid within the bed-space.
        """
        from time import time

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
        # print ("Grid-Calc done, time=%.6f, grid1=%d, grid2=%d" % ( end_time - start_time, len(starts), len(starts2)))

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
        if tlen==0:
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
        #print ("Min= %.1f, %.1f" % (self.min_x, self.min_y))
        #print ("Max= %.1f, %.1f" % (self.max_x, self.max_y))

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
            r_angle = 0
            segments = 48
            i = 0
            max_r = sqrt(
                p.device.unit_width * p.device.unit_width
                + p.device.unit_height * p.device.unit_height
            )
            tlen = (self.tlenx1 + self.tleny1) / 2
            r_fourth = max_r // (4 * tlen) * tlen
            while r_angle < tau:
                if i % 2 == 0:
                    r = 0
                else:
                    r = r_fourth
                while r < max_r:
                    r += tlen
                    x = start_x + r * cos(r_angle)
                    y = start_y + r * sin(r_angle)

                    if self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y:
                        self.scene.grid_points.append([x, y])

                i += 1
                r_angle += tau / segments
            circ_ct = len(self.scene.grid_points) - prim_ct - second_ct

        end_time = time()
        #print("Ready, time needed: %.6f, grid points added=%d (primary=%d, %.6f, secondary=%d, %.6f circ=%d, %.6f)" %
        #    (end_time - start_time,
        #    len(self.scene.grid_points),
        #    prim_ct, s_time_2-start_time,
        #    second_ct, s_time_3-s_time_2,
        #    circ_ct, end_time-s_time_3))

    def process_draw(self, gc):
        """
        Draw the grid on the scene.
        """
        # print ("GridWidget draw")

        if self.scene.context.draw_mode & DRAW_MODE_BACKGROUND == 0:
            context = self.scene.context
            unit_width = context.device.unit_width
            unit_height = context.device.unit_height
            background = self.background
            if background is None:
                brush = wx.Brush(
                    colour=self.scene.colors.color_bed, style=wx.BRUSHSTYLE_SOLID
                )
                gc.SetBrush(brush)
                gc.DrawRectangle(0, 0, unit_width, unit_height)
            elif isinstance(background, int):
                gc.SetBrush(wx.Brush(wx.Colour(swizzlecolor(background))))
                gc.DrawRectangle(0, 0, unit_width, unit_height)
            else:
                gc.DrawBitmap(background, 0, 0, unit_width, unit_height)
        # Get proper gridsize
        w, h = gc.Size
        if self.scene.auto_tick:
            self.calculate_tickdistance(w, h)
        self.calculate_gridsize(w, h)

        if self.last_ticksize != self.scene.tick_distance:
            self.last_ticksize = self.scene.tick_distance
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

            if line_width < 1:
                line_width = 1
            try:
                self.grid_line_pen.SetWidth(line_width)
                self.grid_line_pen2.SetWidth(line_width)
                self.grid_line_pen3.SetWidth(line_width)
            except TypeError:
                self.grid_line_pen.SetWidth(int(line_width))
                self.grid_line_pen2.SetWidth(int(line_width))
                self.grid_line_pen3.SetWidth(int(line_width))

            gc.SetPen(self.grid_line_pen)
            brush = wx.Brush(
                colour=self.scene.colors.color_bed, style=wx.BRUSHSTYLE_TRANSPARENT
            )
            gc.SetBrush(brush)

            if self.scene.draw_grid_circular:
                gc.SetPen(self.grid_line_pen3)
                u_width = float(context.device.unit_width)
                u_height = float(context.device.unit_height)
                gc.Clip(0, 0, u_width, u_height)
                siz = sqrt(u_width * u_width + u_height * u_height)
                # print("Wid=%.1f, Ht=%.1f, siz=%.1f, step=%.1f, sx=%.1f, sy=%.1f" %(u_width, u_height, siz, step, self.sx, self.sy))
                # print("Wid=%s, Ht=%s, siz=%s, step=%s, sx=%s, sy=%s" %(Length(amount=u_width).length_mm, Length(amount=u_height).length_mm, Length(amount=siz).length_mm, Length(amount=step).length_mm, Length(amount=self.sx).length_mm, Length(amount=self.sy).length_mm))
                sox = self.cx / u_width
                soy = self.cy / u_height
                step = self.tlenx1
                factor = max(2 * (1 - sox), 2 * (1 - soy))

                y = 0

                while y < siz * factor:
                    y += 2 * step
                    gc.DrawEllipse(self.cx - y / 2, self.cy - y / 2, y, y)
                mid_y = (
                    y // (4 * step) * step
                )  # (around one fourth of radius)
                # print("Last Y=%.1f (%s), mid_y=%.1f (%s)" % (y, Length(amount=y).length_mm, mid_y, Length(amount=mid_y).length_mm))
                radials_start = []
                radials_end = []
                r_angle = 0
                i = 0
                fsize = 10 / self.scene.widget_root.scene_widget.matrix.value_scale_x()
                if fsize < 1.0:
                    fsize = 1.0  # Mac does not allow values lower than 1.
                try:
                    font = wx.Font(fsize, wx.SWISS, wx.NORMAL, wx.BOLD)
                except TypeError:
                    font = wx.Font(int(fsize), wx.SWISS, wx.NORMAL, wx.BOLD)
                gc.SetFont(font, self.scene.colors.color_guide3)
                segments = 48
                while r_angle < tau:
                    if i % 2 == 0:
                        degang = round(r_angle / tau * 360, 1)
                        if degang == 360:
                            degang = 0
                        a_text = "%.0f°" % degang
                        (t_width, t_height) = gc.GetTextExtent(a_text)
                        # Make sure text remains legible without breaking your neck... ;-)
                        if tau * 1 / 4 < r_angle < tau * 3 / 4:
                            myangle = (-1.0 * r_angle) + tau / 2
                            dx = t_width
                        else:
                            myangle = -1.0 * r_angle
                            dx = 0
                        if self.scene.context.draw_mode & DRAW_MODE_GUIDES == 0:
                            gc.DrawText(
                                a_text,
                                self.cx + cos(r_angle) * (mid_y + dx),
                                self.cy + sin(r_angle) * (mid_y + dx),
                                myangle,
                            )
                        s_factor = 0
                    else:
                        s_factor = 1
                    radials_start.append(
                        (
                            self.cx + s_factor * 0.5 * mid_y * cos(r_angle),
                            self.cy + s_factor * 0.5 * mid_y * sin(r_angle),
                        )
                    )
                    radials_end.append(
                        (
                            self.cx + 0.5 * y * cos(r_angle),
                            self.cy + 0.5 * y * sin(r_angle),
                        )
                    )
                    r_angle += tau / segments
                    i += 1
                gc.StrokeLineSegments(radials_start, radials_end)
                gc.ResetClip()
            if self.scene.draw_grid_secondary:
                gc.SetPen(self.grid_line_pen2)
                if starts2 and ends2:
                    gc.StrokeLineSegments(starts2, ends2)
            if self.scene.draw_grid_primary:
                gc.SetPen(self.grid_line_pen)
                if starts and ends:
                    gc.StrokeLineSegments(starts, ends)

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which draw the background and updates the grid when needed to recalculate the lines
        """
        if signal == "grid":
            self.grid = None
        elif signal == "background":
            self.background = args[0]
        elif signal == "theme":
            self.set_colors()
