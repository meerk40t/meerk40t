import wx

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
        step = context.device.length("10mm", as_float=True)
        starts = []
        ends = []
        if step == 0:
            self.grid = None
            return starts, ends
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

    def process_draw(self, gc):
        """
        Draw the grid on the scene.
        """
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
