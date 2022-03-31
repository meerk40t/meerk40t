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
        self.grid_line_pen.SetColour(wx.Colour(0xA0, 0xA0, 0xA0))
        self.grid_line_pen.SetWidth(1)

    def hit(self):
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        """
        Capture and deal with the doubleclick event.

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
            s = "{dist}{unit}".format(dist=self.scene.tick_distance, unit=context.units_name)
            step = float(Length(s))
            # The very first time we get absurd values, so let's do as if nothing had happened...
            divider = units_width / step
            if divider > 1000: # Too many lines to draw?!
                # print ("Something strange happened: %s" %s)
                step = 0
        if step==0:
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

        self.grid = starts, ends

    def calculate_gridsize(self, w, h):
       # Establish the delta for about 15 ticks
        wpoints = w / 15.0
        hpoints = h / 15.0
        points = min(wpoints, hpoints)
        scaled_conversion = (
            self.scene.context.device.length(str(1) + self.scene.context.units_name, as_float=True)
            * self.scene.widget_root.scene_widget.matrix.value_scale_x()
        )
        if scaled_conversion == 0:
            return
        # tweak the scaled points into being useful.
        # points = scaled_conversion * round(points / scaled_conversion * 10.0) / 10.0
        delta = points / scaled_conversion
        # Lets establish a proper delta: we want to understand the log and x.yyy multiplikator
        x = delta
        factor = 1
        if x >= 1:
            while (x>=10):
              x *= 0.1
              factor *= 10
        else:
            while x<1:
                x *= 10
                factor *= 0.1

        l_pref = delta / factor
        # Assign 'useful' scale
        if l_pref < 3:
            l_pref = 1
        #elif l_pref < 4:
        #    l_pref = 2.5
        else:
            l_pref = 5.0

        delta = l_pref * factor
        # print ("New Delta={delta}".format(delta=delta))
        # points = self.scaled_conversion * float("{:.1g}".format(points / self.scaled_conversion))

        self.scene.tick_distance = delta
        # print ("set scene_tick_distance to %f" % delta)

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
                gc.SetBrush(wx.WHITE_BRUSH)
                gc.DrawRectangle(0, 0, unit_width, unit_height)
            elif isinstance(background, int):
                gc.SetBrush(wx.Brush(wx.Colour(swizzlecolor(background))))
                gc.DrawRectangle(0, 0, unit_width, unit_height)
            else:
                gc.DrawBitmap(background, 0, 0, unit_width, unit_height)
        # Get proper gridsize
        w, h = gc.Size
        self.calculate_gridsize(w, h)

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
                if starts and ends:
                    gc.StrokeLineSegments(starts, ends)

            except (OverflowError, ValueError, ZeroDivisionError):
                matrix.reset()

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which draw the background and updates the grid when needed recalculate the lines
        """
        if signal == "grid":
            self.grid = None

        elif signal == "background":
            self.background = args[0]
