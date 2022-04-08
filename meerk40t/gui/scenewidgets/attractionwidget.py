import wx

from meerk40t.core.units import Length
from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CHAIN, RESPONSE_CHGPOS
from meerk40t.gui.scene.widget import Widget
from math import sqrt

TYPE_BOUND = 0
TYPE_POINT = 1
TYPE_MIDDLE = 2
TYPE_CENTER = 3
TYPE_GRID = 4

class AttractionWidget(Widget):
    """
    Interface Widget - computes and displays attraction points
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        # Respond to Snap is not necessary, but for the sake of completeness...

        self.attraction_points = None # Clear all
        self.grid_points = None # Clear all
        self.my_x = None
        self.my_y = None
        self.visible_pen = wx.Pen(wx.Colour(0xA0, 0xA0, 0xA0, 0x40))
        self.visible_pen.SetWidth(1)
        self.closeup_pen = wx.Pen(wx.Colour(0x00, 0xFF, 0x00, 0xA0))
        self.closeup_pen.SetWidth(1)
        self.symbol_size = 1  # Will be replaced anyway
        self.display_points = []
        self.show_attract_len = 0
        self.action_attract_len = 0
        self.isShiftPressed = False
        self.isCtrlPressed = False
        self.isAltPressed = False
        self.showme = False
        self.scene.context.setting(bool, "snap_grid", True)
        self.scene.context.setting(bool, "snap_points", True)
        self.scene.context.setting(int, "show_attract_len", 45)
        self.scene.context.setting(int, "action_attract_len", 20)
        self.scene.context.setting(int, "grid_attract_len", 15)

        self.snap_grid = self.scene.context.snap_grid
        self.snap_points = self.scene.context.snap_points

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
            self.calculate_display_points()
            if event_type in ("leftdown", "move", "hover", "hover_start") and self.scene.tool_active:
                self.showme = True
            else:
                self.showme = False
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
        ):
            # Check whether shift key is pressed...
            if not self.isShiftPressed:
                # Loop through display points
                if len(self.display_points) > 0 and not self.my_x is None:
                    # Has to be lower than the action threshold
                    min_delta = float("inf")  # self.action_attract_len
                    new_x = None
                    new_y = None
                    for pt in self.display_points:
                        delta = sqrt(
                            (pt[0] - self.my_x) * (pt[0] - self.my_x)
                            + (pt[1] - self.my_y) * (pt[1] - self.my_y)
                        )
                        if delta < min_delta:
                            new_x = pt[0]
                            new_y = pt[1]
                            min_delta = delta
                    # fmt:off
                    #print("Check complete: old x,y = %.1f, %.1f, new = %s,%s, delta=%.1f, threshold=%.1f"
                    #   % ( self.my_x, self.my_y, new_x, new_y, delta, self.action_attract_len, ))
                    # fmt:on
                    if not new_x is None:
                        if (
                            abs(new_x - self.my_x) <= self.action_attract_len
                            and abs(new_y - self.my_y) <= self.action_attract_len
                        ):
                            # Is the distance small enough?
                            self.scene.new_x_space = new_x
                            self.scene.new_y_space = new_y
                            response = RESPONSE_CHGPOS
            #print ("response: %d" % response)

        return response

    def draw_caret(self, gc, x, y, closeup):
        if closeup:
            pen = self.closeup_pen
            sym_size = self.symbol_size
        else:
            pen = self.visible_pen
            sym_size = 0.5 * self.symbol_size
        gc.SetPen(pen)
        brush = wx.Brush(colour=pen.GetColour(), style=wx.BRUSHSTYLE_SOLID)
        gc.SetBrush(brush)
        path = gc.CreatePath()
        path.MoveToPoint(x - sym_size / 2, y)
        path.AddLineToPoint(x, y - sym_size / 2)
        path.AddLineToPoint(x + sym_size / 2, y)
        path.AddLineToPoint(x, y + sym_size / 2)
        path.CloseSubpath()
        gc.DrawPath(path)

    def draw_center(self, gc, x, y, closeup):
        if closeup:
            pen = self.closeup_pen
            sym_size = self.symbol_size
        else:
            pen = self.visible_pen
            sym_size = 0.5 * self.symbol_size
        gc.SetPen(pen)
        brush = wx.Brush(colour=pen.GetColour(), style=wx.BRUSHSTYLE_SOLID)
        gc.SetBrush(brush)
        path = gc.CreatePath()
        path.MoveToPoint(x - sym_size / 2, y - sym_size / 2)
        path.AddLineToPoint(x, y)
        path.AddLineToPoint(x + sym_size / 2, y - sym_size / 2)
        path.AddLineToPoint(x + sym_size / 2, y + sym_size / 2)
        path.AddLineToPoint(x, y)
        path.AddLineToPoint(x - sym_size / 2, y + sym_size / 2)
        path.CloseSubpath()
        gc.DrawPath(path)

    def draw_gridpoint(self, gc, x, y, closeup):
        if closeup:
            pen = self.closeup_pen
            sym_size = self.symbol_size
        else:
            pen = self.visible_pen
            sym_size = 0.5 * self.symbol_size
        gc.SetPen(pen)
        gc.SetPen(pen)
        brush = wx.Brush(colour=pen.GetColour(), style=wx.BRUSHSTYLE_SOLID)
        gc.SetBrush(brush)
        path = gc.CreatePath()
        dsize = 1 / 8 * sym_size
        path.MoveToPoint(x - sym_size / 2, y + dsize)
        path.AddLineToPoint(x - dsize, y + dsize)
        path.AddLineToPoint(x - dsize, y - sym_size / 2)
        path.AddLineToPoint(x + dsize, y - sym_size / 2)
        path.AddLineToPoint(x + dsize, y + dsize)
        path.AddLineToPoint(x + sym_size / 2, y + dsize)
        path.AddLineToPoint(x + sym_size / 2, y - dsize)
        path.AddLineToPoint(x + dsize, y + dsize)
        path.AddLineToPoint(x + dsize, y + sym_size / 2)
        path.AddLineToPoint(x - dsize, y + sym_size / 2)
        path.AddLineToPoint(x - dsize, y + dsize)
        path.AddLineToPoint(x - sym_size / 2, y + dsize)
        path.CloseSubpath()
        gc.DrawPath(path)

    def draw_midpoint(self, gc, x, y, closeup):
        if closeup:
            pen = self.closeup_pen
            sym_size = self.symbol_size
        else:
            pen = self.visible_pen
            sym_size = 0.5 * self.symbol_size
        gc.SetPen(pen)
        brush = wx.Brush(colour=pen.GetColour(), style=wx.BRUSHSTYLE_SOLID)
        gc.SetBrush(brush)
        path = gc.CreatePath()
        path.MoveToPoint(x - sym_size / 2, y - sym_size / 2)
        path.AddLineToPoint(x + sym_size / 2, y - sym_size / 2)
        path.AddLineToPoint(x, y)
        path.AddLineToPoint(x + sym_size / 2, y + sym_size / 2)
        path.AddLineToPoint(x - sym_size / 2, y + sym_size / 2)
        path.AddLineToPoint(x, y)
        path.CloseSubpath()
        gc.DrawPath(path)

    def process_draw(self, gc):
        """
        Draw all attraction points on the scene.
        """
        if self.showme:
            matrix = self.parent.matrix
            try:
                # Intentionally big to clearly see shape
                self.symbol_size = 12 / matrix.value_scale_x()
            except ZeroDivisionError:
                matrix.reset()
                return
            # Anything within a 15 Pixel Radius will be attracted, anything within a 45 Pixel Radius will be diplayed
            pixel1 = self.scene.context.show_attract_len
            pixel2 = self.scene.context.action_attract_len
            pixel3 = self.scene.context.grid_attract_len
            # print ("Current values are: show=%d, points=%d, grid=%d" % ( pixel1, pixel2, pixel3))
            self.show_attract_len = pixel1 / matrix.value_scale_x()
            self.action_attract_len = pixel2 / matrix.value_scale_x()
            self.grid_attract_len = pixel3 / matrix.value_scale_x()


            for pts in self.display_points:
                if (
                    abs(pts[0] - self.my_x) <= self.show_attract_len
                    and abs(pts[1] - self.my_y) <= self.show_attract_len
                ):
                    if pts[2] == TYPE_GRID:
                        closeup = (
                            abs(pts[0] - self.my_x) <= self.grid_attract_len
                            and abs(pts[1] - self.my_y) <= self.grid_attract_len
                        )
                    else:
                        closeup = (
                            abs(pts[0] - self.my_x) <= self.action_attract_len
                            and abs(pts[1] - self.my_y) <= self.action_attract_len
                        )

                    if pts[2]in (TYPE_POINT, TYPE_BOUND):
                        self.draw_caret(gc, pts[0], pts[1], closeup)
                    elif pts[2] == TYPE_MIDDLE:
                        self.draw_midpoint(gc, pts[0], pts[1], closeup)
                    elif pts[2] == TYPE_CENTER:
                        self.draw_center(gc, pts[0], pts[1], closeup)
                    elif pts[2] == TYPE_GRID:
                        self.draw_gridpoint(gc, pts[0], pts[1], closeup)

    def calculate_attraction_points(self):
        """
        Looks at all elements (all_points=True) or at non-selected elements (all_points=False) and identifies all
        attraction points (center, corners, sides)
        """
        from time import time
        start_time = time()
        self.attraction_points = []  # Clear all
        translation_table = {
            "bounds top_left" : TYPE_BOUND,
            "bounds top_right" : TYPE_BOUND,
            "bounds bottom_left" : TYPE_BOUND,
            "bounds bottom_right": TYPE_BOUND,
            "bounds center_center": TYPE_CENTER,
            "bounds top_center": TYPE_MIDDLE,
            "bounds bottom_center": TYPE_MIDDLE,
            "bounds center_left": TYPE_MIDDLE,
            "bounds center_right": TYPE_MIDDLE,
            "endpoint": TYPE_POINT,
        }

        for e in self.scene.context.elements.flat(types=("elem",)):
            emph = e.emphasized
            if hasattr(e, "points"):
                for pt in e.points:
                    try:
                        pt_type = translation_table[pt[2]]
                    except:
                        print ("Unknown type: %s" % pt[2])
                        pt_type = TYPE_POINT
                    self.attraction_points.append([pt[0], pt[1], pt_type, emph])

        end_time = time()
        print(
            "Ready, time needed: %.6f, attraction points added=%d"
            % (end_time - start_time, len(self.attraction_points))
        )

    def calculate_grid_points(self):
        """
        Looks at all elements (all_points=True) or at non-selected elements (all_points=False) and identifies all
        attraction points (center, corners, sides)
        """
        from time import time
        start_time = time()
        self.grid_points = []  # Clear all

        # Let's add grid points - set the full grid
        p = self.scene.context
        tlen = float(
            Length(
                "{value}{units}".format(value=self.scene.tick_distance, units=p.units_name)
            )
        )
        if tlen >= 1000:
            x = 0
            while x <= p.device.unit_width:
                y = 0
                while y <= p.device.unit_height:
                    self.grid_points.append([x, y])
                    y += tlen
                x += tlen

        end_time = time()
        print(
            "Ready, time needed: %.6f, grid points added=%d"
            % (end_time - start_time, len(self.grid_points))
        )

    def calculate_display_points(self):
        from time import time
        start_time = time()
        self.display_points = []
        if self.attraction_points is None:
            self.calculate_attraction_points()
        if self.grid_points is None:
            self.calculate_grid_points()

        self.snap_grid = self.scene.context.snap_grid
        self.snap_points = self.scene.context.snap_points
        if self.snap_points and len(self.attraction_points) > 0 and not self.my_x is None:
            for pts in self.attraction_points:
                if not pts[3]:  # not emphasized
                    if (
                        abs(pts[0] - self.my_x) <= self.show_attract_len
                        and abs(pts[1] - self.my_y) <= self.show_attract_len
                    ):
                        closeup = (
                            abs(pts[0] - self.my_x) <= self.action_attract_len
                            and abs(pts[1] - self.my_y) <= self.action_attract_len
                        )

                        self.display_points.append([pts[0], pts[1], pts[2]])

        if self.snap_grid and len(self.grid_points) > 0 and not self.my_x is None:
            for pts in self.grid_points:
                if (
                    abs(pts[0] - self.my_x) <= self.show_attract_len
                    and abs(pts[1] - self.my_y) <= self.show_attract_len
                ):
                    closeup = (
                        abs(pts[0] - self.my_x) <= self.action_attract_len
                        and abs(pts[1] - self.my_y) <= self.action_attract_len
                    )

                    self.display_points.append([pts[0], pts[1], TYPE_GRID])

        end_time = time()
        #print(
        #    "Ready, time needed: %.6f, points added=%d"
        #    % (end_time - start_time, len(self.display_points))
        #)

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which draw the background and updates the grid when needed recalculate the lines
        """
        # print ("AttractionWidget receives signal: %s" % signal)
        consumed = False
        if signal == "attraction":
            consumed = True
            pass
        if signal in ("modified", "emphasized", "element_added"):
            consumed = True
            self.attraction_points = None
        if signal in ("grid", "guide"):
            consumed = True
            self.grid_points = None
        if not consumed:
            print ("Dont know what to do with signal %s" % signal)
