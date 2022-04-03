import wx

from meerk40t.core.units import Length
from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CHAIN, RESPONSE_CHGPOS
from meerk40t.gui.scene.widget import Widget
from math import sqrt


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
        self.display_points = []
        self.show_attract_len = 0
        self.action_attract_len = 0
        self.isShiftPressed = False
        self.isCtrlPressed = False
        self.isAltPressed = False

    def hit(self):
        """
        Hit-Logic - by definition: yes, I want to be involved
        """
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        """
        Event-Logic - just note the current position
        """
        response = RESPONSE_CHAIN
        if not space_pos is None:
            self.my_x = space_pos[0]
            self.my_y = space_pos[1]
        # print("Key-Down: %f - literal: %s" % (keycode, literal))
        if event_type == "kb_shift_press":
            if not self.isShiftPressed:  # ignore multiple calls
                self.isShiftPressed = True
        elif event_type == "kb_ctrl_press":
            if not self.isCtrlPressed:  # ignore multiple calls
                self.isCtrlPressed = True
        elif event_type == "kb_alt_press":
            if not self.isAltPressed:  # ignore multiple calls
                self.isAltPressed = True
        elif event_type == "kb_shift_release":
            if self.isShiftPressed:  # ignore multiple calls
                self.isShiftPressed = False
        elif event_type == "kb_ctrl_release":
            if self.isCtrlPressed:  # ignore multiple calls
                self.isCtrlPressed = False
        elif event_type == "kb_alt_release":
            if self.isAltPressed:  # ignore multiple calls
                self.isAltPressed = False
        elif event_type in (
            "leftdown",
            "leftup",
            "leftclick",
        ):  # Intentionally ignore middle
            print(
                "Left-MB-%s, checking for %d points:"
                % (event_type, len(self.display_points))
            )
            # Check whether shift key is pressed...
            if not self.isShiftPressed:
                # Loop through display points
                if len(self.display_points) > 0:
                    # Has to be lower than the action threshold
                    min_delta = float("inf")  # self.action_attract_len
                    new_x = self.my_x
                    new_y = self.my_y
                    for pt in self.display_points:
                        delta = sqrt(
                            (pt[0] - self.my_x) * (pt[0] - self.my_x)
                            + (pt[1] - self.my_y) * (pt[1] - self.my_y)
                        )
                        if delta < min_delta:
                            new_x = pt[0]
                            new_y = pt[1]
                            min_delta = delta
                    # print(
                    #    "Check complete: old x,y = %.1f, %.1f, new = %.1f,%.1f, delta=%.1f, threshold=%.1f"
                    #    % (
                    #        self.my_x,
                    #        self.my_y,
                    #        new_x,
                    #        new_y,
                    #        delta,
                    #        self.action_attract_len,
                    #    )
                    # )
                    if min_delta < self.action_attract_len:
                        # Is the distance small enough?
                        self.scene.new_x_space = new_x
                        self.scene.new_y_space = new_y
                        response = RESPONSE_CHGPOS

        return response

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

    def draw_gridpoint(self, gc, x, y):
        gc.SetPen(self.center_pen)
        gc.DrawLine(x, y - self.symbol_size / 2, x, y + self.symbol_size / 2)
        gc.DrawLine(x - self.symbol_size / 2, y, x + self.symbol_size / 2, y)

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
        path.AddLineToPoint(x, y)
        path.CloseSubpath()
        gc.DrawPath(path)

    def process_draw(self, gc):
        """
        Draw all attraction points on the scene.
        """
        type_point = 1
        type_middle = 2
        type_center = 3
        type_grid = 4
        matrix = self.parent.matrix
        try:
            # Intentionally big to clearly see shape
            self.symbol_size = 20 / matrix.value_scale_x()
        except ZeroDivisionError:
            matrix.reset()
            return
        # Anything within a 10 Pixel Radius will be attracted, anything within a 30 Pixel Radius will be diplayed
        self.show_attract_len = 45 / matrix.value_scale_x()
        self.action_attract_len = 15 / matrix.value_scale_x()

        self.display_points = []
        if self.compute and len(self.scene.attraction_points) > 0:
            for pts in self.scene.attraction_points:
                if not pts[3]:  # not emphasized
                    if (
                        abs(pts[0] - self.my_x) <= self.show_attract_len
                        and abs(pts[1] - self.my_y) <= self.show_attract_len
                    ):
                        self.display_points.append([pts[0], pts[1]])
                        if pts[2] == type_point:
                            self.draw_caret(gc, pts[0], pts[1])
                        elif pts[2] == type_middle:
                            self.draw_midpoint(gc, pts[0], pts[1])
                        elif pts[2] == type_center:
                            self.draw_center(gc, pts[0], pts[1])
                        elif pts[2] == type_grid:
                            self.draw_grid_point(gc, pts[0], pts[1])

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which draw the background and updates the grid when needed recalculate the lines
        """
        if signal == "attraction":
            if args[0]:
                self.compute = True
            else:
                self.compute = False
