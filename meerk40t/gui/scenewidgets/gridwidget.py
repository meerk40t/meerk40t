from math import sqrt, cos, sin, tau
import wx

from meerk40t.core.units import Length
from meerk40t.gui.laserrender import DRAW_MODE_BACKGROUND, DRAW_MODE_GRID, swizzlecolor
from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CHAIN
from meerk40t.gui.scene.widget import Widget

class GridWidget(Widget):
    """
    Interface Widget
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self.grid = None
        self.background = None
        self.grid_line_pen = wx.Pen()
        self.last_ticksize = 0
        self.draw_grid = True
        self.sx = 0
        self.sy = 0
        self.step = 0

        self.set_colors()

    def set_colors(self):
        self.grid_line_pen.SetColour(self.scene.colors.color_grid)
        self.grid_line_pen.SetWidth(1)

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
        context = self.scene.context
        units_width = float(context.device.unit_width)
        units_height = float(context.device.unit_height)
        step = 0
        if self.scene.tick_distance > 0:
            s = "{dist}{unit}".format(
                dist=self.scene.tick_distance, unit=context.units_name
            )
            # print ("Calculate grid with %s" %s)
            step = float(Length(s))
            # The very first time we get absurd values, so let's do as if nothing had happened...
            if units_width / step > 1000 or units_height / step > 1000:
                # print ("Something strange happened: %s" %s)
                step = 0
        if step == 0:
            # print ("Default kicked in")
            step = float(Length("10mm"))

        starts = []
        ends = []
        if step == 0:
            self.grid = None
            return

        x = 0.0
        while x < units_width:
            starts.append((x, 0.0))
            ends.append((x, units_height))
            x += step

        y = 0.0
        while y < units_height:
            starts.append((0.0, y))
            ends.append((units_width, y))
            y += step
        self.step = step
        self.grid = starts, ends

    def calculate_gridsize(self, w, h):
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

        delta = l_pref * factor
        # print("New Delta={delta}".format(delta=delta))
        # points = self.scaled_conversion * float("{:.1g}".format(points / self.scaled_conversion))

        self.scene.tick_distance = delta

        points = self.scene.tick_distance * scaled_conversion

        p = self.scene.context
        self.units = p.units_name

        self.sx = p.device.unit_width * p.device.show_origin_x
        self.sy = p.device.unit_height * p.device.show_origin_y

        if points == 0:
            return

        #print ("The intended scale is in {units} with a tick every {delta} {units}".format(delta=self.scene.tick_distance, units=self.units))
        #print("Start-location is at %.1f, %.1f" % (self.sx, self.sy))
        #print("device, w=%.1f, h=%.1f" % (p.device.unit_width, p.device.unit_height))
        #print("origin, x=%.1f, y=%.1f" % (p.device.show_origin_x, p.device.show_origin_y))

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
        if self.scene.auto_tick:
            w, h = gc.Size
            self.calculate_gridsize(w, h)

        if self.last_ticksize != self.scene.tick_distance:
            self.last_ticksize = self.scene.tick_distance
            self.grid = None

        if self.scene.context.draw_mode & DRAW_MODE_GRID == 0:
            if self.grid is None:
                self.calculate_grid()

            starts, ends = self.grid
            matrix = self.scene.widget_root.scene_widget.matrix
            try:
                scale_x = matrix.value_scale_x()
                line_width = 1.0 / scale_x
                if line_width < 1:
                    line_width = 1
                try:
                    self.grid_line_pen.SetWidth(line_width)
                except TypeError:
                    self.grid_line_pen.SetWidth(int(line_width))

                gc.SetPen(self.grid_line_pen)
                brush = wx.Brush(
                    colour=self.scene.colors.color_bed, style=wx.BRUSHSTYLE_TRANSPARENT
                )
                gc.SetBrush(brush)

                if self.scene.draw_grid_circular:
                    u_width = float(context.device.unit_width)
                    u_height = float(context.device.unit_height)
                    gc.Clip(0, 0, u_width, u_height)
                    siz = sqrt(u_width * u_width + u_height * u_height)
                    #print("Wid=%.1f, Ht=%.1f, siz=%.1f, step=%.1f, sx=%.1f, sy=%.1f" %(u_width, u_height, siz, self.step, self.sx, self.sy))
                    #print("Wid=%s, Ht=%s, siz=%s, step=%s, sx=%s, sy=%s" %(Length(amount=u_width).length_mm, Length(amount=u_height).length_mm, Length(amount=siz).length_mm, Length(amount=self.step).length_mm, Length(amount=self.sx).length_mm, Length(amount=self.sy).length_mm))

                    y = 0
                    factor = max( 2* (1-context.device.show_origin_x), 2* (1-context.device.show_origin_y))
                    # print ("Factor=%.2f" % factor)
                    while (y < siz * factor ):
                        y += 2 * self.step
                        gc.DrawEllipse(self.sx - y/2, self.sy - y/2, y, y)
                    mid_y = y // (3 * self.step) * self.step # (around one third of radius)
                    # print("Last Y=%.1f (%s), mid_y=%.1f (%s)" % (y, Length(amount=y).length_mm, mid_y, Length(amount=mid_y).length_mm))
                    radials_start = []
                    radials_end = []
                    r_angle = 0
                    i = 0
                    segments = 48
                    while r_angle<tau:
                        if i % 2 == 0:
                            s_factor = 0
                        else:
                            s_factor = 1
                        radials_start.append((self.sx + s_factor * 0.5 * mid_y * cos(r_angle), self.sy + s_factor * 0.5 * mid_y * sin(r_angle)))
                        radials_end.append((self.sx + 0.5 * y * cos(r_angle), self.sy + 0.5 * y * sin(r_angle)))
                        r_angle += tau / segments
                        i += 1
                    gc.StrokeLineSegments(radials_start, radials_end)
                    gc.ResetClip()
                if self.scene.draw_grid_rectangular:
                    if starts and ends:
                        gc.StrokeLineSegments(starts, ends)

            except (OverflowError, ValueError, ZeroDivisionError):
                matrix.reset()

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
