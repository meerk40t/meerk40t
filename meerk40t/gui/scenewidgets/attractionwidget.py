import wx

from meerk40t.core.units import Length
from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CHAIN
from meerk40t.gui.scene.widget import Widget


class AttractionWidget(Widget):
    """
    Interface Widget - computes and displays attraction points
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self.compute = True
        self.grid_line_pen = wx.Pen()
        self.grid_line_pen.SetColour(wx.Colour(0xA0, 0xA0, 0xA0, 128))
        self.grid_line_pen.SetWidth(1)
        self.my_x = 0
        self.my_y = 0
        self.caret_pen = wx.Pen(wx.Colour(0x00, 0xFF, 0x00, 0x40))
        self.midpoint_pen = wx.Pen(wx.Colour(0xFF, 0x00, 0x00, 0x40))
        self.center_pen = wx.Pen(wx.Colour(0x00, 0x00, 0xFF, 0x40))
        self.symbol_size = 10

    def hit(self):
        """
        Hit-Logic - by definition: yes, I want to be involved
        """
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        """
        Event-Logic - just note the current position
        """
        if not space_pos is None:
            self.my_x = space_pos[0]
            self.my_y = space_pos[1]
        return RESPONSE_CHAIN

    def draw_caret(self, gc, x, y):
        gc.SetPen(self.caret_pen)
        brush = wx.Brush(colour=self.caret_pen.GetColour(), style=wx.BRUSHSTYLE_SOLID)
        gc.SetBrush(brush)
        path = gc.CreatePath()
        path.MoveToPoint(x - self.symbol_size / 2, y)
        path.AddLineToPoint(x, y - self.symbol_size / 2)
        path.AddLineToPoint(x + self.symbol_size / 2, y)
        path.AddLineToPoint(x, y + self.symbol_size / 2)
        path.CloseSubpath()
        gc.DrawPath(path)

    def draw_center(self, gc, x, y):
        gc.SetPen(self.center_pen)
        brush = wx.Brush(colour=self.center_pen.GetColour(), style=wx.BRUSHSTYLE_SOLID)
        gc.SetBrush(brush)
        path = gc.CreatePath()
        path.MoveToPoint(x - self.symbol_size / 2, y - self.symbol_size / 2)
        path.AddLineToPoint(x, y)
        path.AddLineToPoint(x + self.symbol_size / 2, y - self.symbol_size / 2)
        path.AddLineToPoint(x + self.symbol_size / 2, y + self.symbol_size / 2)
        path.AddLineToPoint(x, y)
        path.AddLineToPoint(x - self.symbol_size / 2, y + self.symbol_size / 2)
        path.CloseSubpath()
        gc.DrawPath(path)

    def draw_midpoint(self, gc, x, y):
        gc.SetPen(self.midpoint_pen)
        brush = wx.Brush(
            colour=self.midpoint_pen.GetColour(), style=wx.BRUSHSTYLE_SOLID
        )
        gc.SetBrush(brush)
        path = gc.CreatePath()
        path.MoveToPoint(x - self.symbol_size / 2, y - self.symbol_size / 2)
        path.AddLineToPoint(x + self.symbol_size / 2, y - self.symbol_size / 2)
        path.AddLineToPoint(x, y)
        path.AddLineToPoint(x + self.symbol_size / 2, y + self.symbol_size / 2)
        path.AddLineToPoint(x - self.symbol_size / 2, y + self.symbol_size / 2)
        path.CloseSubpath()
        gc.DrawPath(path)

    def process_draw(self, gc):
        """
        Draw all attraction points on the scene.
        """
        type_point = 1
        type_middle = 2
        type_center = 3
        matrix = self.parent.matrix
        try:
            self.symbol_size = 8 / matrix.value_scale_x()
        except ZeroDivisionError:
            matrix.reset()
            return

        if self.scene.tick_distance > 0:
            s = "{amount}{units}".format(
                amount=self.scene.tick_distance, units=self.scene.context.units_name
            )
            len_tick = float(Length(s))
            # Attraction length is 1/3, 4/3, 9/3 of a grid-unit
            factor = 1 / 5 * self.scene.magnet_attraction * self.scene.magnet_attraction
            attraction_len = factor * len_tick
        self.display_points = []
        if self.compute and len(self.scene.attraction_points) > 0:
            for pts in self.scene.attraction_points:
                # Point in bbox?
                if not pts[3]:  # not emphasized
                    if (
                        abs(pts[0] - self.my_x) <= attraction_len
                        and abs(pts[1] - self.my_y) <= attraction_len
                    ):
                        if pts[2] == type_point:
                            self.draw_caret(gc, pts[0], pts[1])
                        elif pts[2] == type_middle:
                            self.draw_midpoint(gc, pts[0], pts[1])
                        elif pts[2] == type_center:
                            self.draw_center(gc, pts[0], pts[1])

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which draw the background and updates the grid when needed recalculate the lines
        """
        if signal == "attraction":
            if args[0]:
                self.compute = True
            else:
                self.compute = False
