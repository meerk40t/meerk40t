from math import sqrt

import wx

from meerk40t.core.element_types import elem_nodes
from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_DELEGATE,
    HITCHAIN_HIT,
    RESPONSE_CHAIN,
)
from meerk40t.gui.scene.widget import Widget

TYPE_BOUND = 0
TYPE_POINT = 1
TYPE_MIDDLE = 2
TYPE_CENTER = 3
TYPE_GRID = 4
TYPE_MIDDLE_SMALL = 5


class AttractionWidget(Widget):
    """
    Interface Widget - computes and displays attraction points
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        # Respond to Snap is not necessary, but for the sake of completeness...
        # We want to be unrecognized
        self.transparent = True
        self.context = self.scene.context
        self.attraction_points = None  # Clear all
        self.my_x = None
        self.my_y = None
        self.visible_pen = wx.Pen()
        self.visible_pen.SetWidth(1)
        self.closeup_pen = wx.Pen()
        self.closeup_pen.SetWidth(1)
        self.load_colors()
        self.symbol_size = 1  # Will be replaced anyway
        self.display_points = []

        # Should already be covered in wxmain choice panel, but are used here and thus set here.
        self.context.setting(int, "show_attract_len", 45)
        self.context.setting(int, "action_attract_len", 20)
        self.context.setting(int, "grid_attract_len", 15)
        self.context.setting(bool, "snap_grid", True)
        self.context.setting(bool, "snap_points", False)
        self._show_snap_points = False

    def load_colors(self):
        self.visible_pen.SetColour(self.scene.colors.color_snap_visible)
        self.closeup_pen.SetColour(self.scene.colors.color_snap_closeup)

    def hit(self):
        """
        Hit-Logic - by definition: yes, I want to be involved
        """
        if self.context.snap_points or self.context.snap_grid:
            return HITCHAIN_HIT
        else:
            return HITCHAIN_DELEGATE

    def event(
        self, window_pos=None, space_pos=None, event_type=None, modifiers=None, **kwargs
    ):
        """
        Event-Logic - just note the current position
        """
        # if event_type.startswith("left"):
        #     print(f"Attract - event={event_type}, space={space_pos}")
        response = RESPONSE_CHAIN
        if space_pos is None:
            return response
        self.my_x = space_pos[0]
        self.my_y = space_pos[1]
        if (
            event_type
            in ("leftdown", "leftup", "leftclick", "move", "hover", "hover_start")
            and (self.scene.pane.tool_active or self.scene.modif_active)
            and "shift" not in modifiers
        ):
            self.calculate_display_points()
            self._show_snap_points = True
        else:
            self._show_snap_points = False
        if (
            event_type
            in (
                "leftdown",
                "leftup",
                "leftclick",
                "move",
                # "hover",
            )
            and self._show_snap_points
        ):
            if event_type in ("leftup", "leftclick"):
                # Na, we don't need points to be displayed
                # (but we needed the calculation)
                self._show_snap_points = False
            # Check whether shift key is pressed...
            if "shift" not in modifiers:
                # if event_type.startswith("left"):
                #     print (f"x={self.my_x}, y={self.my_y}, len={len(self.display_points)}")
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
                    # print("Check complete: old x,y = %.1f, %.1f, new = %s,%s, delta=%.1f, threshold=%.1f"
                    #   % ( self.my_x, self.my_y, new_x, new_y, delta, self.context.action_attract_len, ))
                    # fmt:on
                    matrix = self.parent.matrix
                    pixel = self.context.action_attract_len / matrix.value_scale_x()
                    if new_x is not None:
                        if (
                            abs(new_x - self.my_x) <= pixel
                            and abs(new_y - self.my_y) <= pixel
                        ):
                            # Is the distance small enough?
                            response = (RESPONSE_CHAIN, new_x, new_y)
        return response

    def draw_caret(self, gc, x, y, closeup):
        if closeup == 2:  # closest
            pen = self.closeup_pen
            sym_size = 1.5 * self.symbol_size
        elif closeup == 1:  # within snap range
            pen = self.visible_pen
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
        if closeup == 2:  # closest
            pen = self.closeup_pen
            sym_size = self.symbol_size
        elif closeup == 1:  # within snap range
            pen = self.visible_pen
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
        if closeup == 2:  # closest
            pen = self.closeup_pen
            sym_size = 1.5 * self.symbol_size
        elif closeup == 1:  # within snap range
            pen = self.visible_pen
            sym_size = self.symbol_size
        else:
            pen = self.visible_pen
            sym_size = 0.5 * self.symbol_size
        gc.SetPen(pen)
        brush = wx.Brush(colour=pen.GetColour(), style=wx.BRUSHSTYLE_SOLID)
        gc.SetBrush(brush)
        dsize = 1 / 8 * sym_size
        gc.DrawRectangle(x - dsize, y - sym_size / 2, 2 * dsize, sym_size)
        gc.DrawRectangle(
            x - sym_size / 2,
            y - dsize,
            sym_size,
            2 * dsize,
        )

    def draw_midpoint(self, gc, x, y, closeup):
        if closeup == 2:  # closest
            pen = self.closeup_pen
            sym_size = 1.5 * self.symbol_size
        elif closeup == 1:  # within snap range
            pen = self.visible_pen
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
        if self._show_snap_points:
            self.visible_pen.SetColour(self.scene.colors.color_snap_visible)
            self.closeup_pen.SetColour(self.scene.colors.color_snap_closeup)
            matrix = self.parent.matrix
            try:
                # Intentionally big to clearly see shape
                self.symbol_size = 10 / matrix.value_scale_x()
            except ZeroDivisionError:
                matrix.reset()
                return
            # Anything within a 15 Pixel Radius will be attracted, anything within a 45 Pixel Radius will be displayed
            local_attract_len = self.context.show_attract_len / matrix.value_scale_x()
            local_action_attract_len = (
                self.context.action_attract_len / matrix.value_scale_x()
            )
            local_grid_attract_len = (
                self.context.grid_attract_len / matrix.value_scale_x()
            )

            min_delta = float("inf")
            min_x = None
            min_y = None
            min_type = None
            for pts in self.display_points:
                if (
                    abs(pts[0] - self.my_x) <= local_attract_len
                    and abs(pts[1] - self.my_y) <= local_attract_len
                ):
                    closeup = 0
                    delta = sqrt(
                        (pts[0] - self.my_x) * (pts[0] - self.my_x)
                        + (pts[1] - self.my_y) * (pts[1] - self.my_y)
                    )
                    dx = abs(pts[0] - self.my_x)
                    dy = abs(pts[1] - self.my_y)

                    if pts[2] == TYPE_GRID:
                        distance = local_grid_attract_len
                    else:
                        distance = local_action_attract_len
                    if dx <= distance and dy <= distance:
                        closeup = 1
                        if delta < min_delta:
                            min_delta = delta
                            min_x = pts[0]
                            min_y = pts[1]
                            min_type = pts[2]

                    if pts[2] in (TYPE_POINT, TYPE_BOUND):
                        self.draw_caret(gc, pts[0], pts[1], closeup)
                    elif pts[2] == TYPE_MIDDLE:
                        self.draw_midpoint(gc, pts[0], pts[1], closeup)
                    elif pts[2] == TYPE_MIDDLE_SMALL:
                        self.draw_midpoint(gc, pts[0], pts[1], closeup)
                    elif pts[2] == TYPE_CENTER:
                        self.draw_center(gc, pts[0], pts[1], closeup)
                    elif pts[2] == TYPE_GRID:
                        self.draw_gridpoint(gc, pts[0], pts[1], closeup)
            # Draw the closest point
            if min_x is not None:
                closeup = 2  # closest
                if min_type in (TYPE_POINT, TYPE_BOUND):
                    self.draw_caret(gc, min_x, min_y, closeup)
                elif min_type == TYPE_MIDDLE:
                    self.draw_midpoint(gc, min_x, min_y, closeup)
                elif min_type == TYPE_MIDDLE_SMALL:
                    self.draw_midpoint(gc, min_x, min_y, closeup)
                elif min_type == TYPE_CENTER:
                    self.draw_center(gc, min_x, min_y, closeup)
                elif min_type == TYPE_GRID:
                    self.draw_gridpoint(gc, min_x, min_y, closeup)

    def calculate_attraction_points(self):
        """
        Looks at all elements (all_points=True) or at non-selected elements (all_points=False) and identifies all
        attraction points (center, corners, sides)
        """
        # if self.attraction_points is None:
        #     print (f"Array was empty")
        # else:
        #     print (f"Array contained {len(self.attraction_points)} points")
        self.context.elements.set_start_time("attr_calc_points")
        self.attraction_points = []  # Clear all
        translation_table = {
            "bounds top_left": TYPE_BOUND,
            "bounds top_right": TYPE_BOUND,
            "bounds bottom_left": TYPE_BOUND,
            "bounds bottom_right": TYPE_BOUND,
            "bounds center_center": TYPE_CENTER,
            "bounds top_center": TYPE_MIDDLE,
            "bounds bottom_center": TYPE_MIDDLE,
            "bounds center_left": TYPE_MIDDLE,
            "bounds center_right": TYPE_MIDDLE,
            "endpoint": TYPE_POINT,
            "point": TYPE_POINT,
            "midpoint": TYPE_MIDDLE_SMALL,
        }

        for e in self.scene.context.elements.flat(types=elem_nodes):
            emph = e.emphasized
            if hasattr(e, "points"):
                for pt in e.points:
                    try:
                        pt_type = translation_table[pt[2]]
                    except:
                        print(f"Unknown type: {pt[2]}")
                        pt_type = TYPE_POINT
                    self.attraction_points.append([pt[0], pt[1], pt_type, emph])

        self.context.elements.set_end_time(
            "attr_calc_points", message=f"points added={len(self.attraction_points)}"
        )

    def calculate_display_points(self):
        # Inform profiler
        self.context.elements.set_start_time("attr_calc_disp")

        self.display_points = []
        if self.attraction_points is None and self.context.snap_points:
            self.calculate_attraction_points()

        matrix = self.parent.matrix
        pixel = self.context.show_attract_len / matrix.value_scale_x()

        if (
            self.context.snap_points
            and len(self.attraction_points) > 0
            and not self.my_x is None
        ):
            dummy = 0
            for pts in self.attraction_points:
                doit = True  # Not sure why not :-)
                if self.scene.modif_active:
                    doit = not pts[3]  # not emphasized
                if doit:
                    if (
                        abs(pts[0] - self.my_x) <= pixel
                        and abs(pts[1] - self.my_y) <= pixel
                    ):
                        self.display_points.append([pts[0], pts[1], pts[2]])

        if (
            self.context.snap_grid
            and self.scene.grid_points is not None
            and len(self.scene.grid_points) > 0
            and not self.my_x is None
        ):
            for pts in self.scene.grid_points:
                if (
                    abs(pts[0] - self.my_x) <= pixel
                    and abs(pts[1] - self.my_y) <= pixel
                ):
                    self.display_points.append([pts[0], pts[1], TYPE_GRID])

        self.context.elements.set_end_time(
            "attr_calc_disp", message=f"points added={len(self.display_points)}"
        )

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which indicate that we need to refresh / discard some data
        """
        # print ("AttractionWidget receives signal: %s" % signal)
        consumed = False
        if signal == "attraction":
            consumed = True
        elif signal in ("modified", "emphasized", "element_added", "tool_modified"):
            consumed = True
            self.attraction_points = None
        elif signal in ("grid", "guide"):
            consumed = True
            # self.scene.grid_points = None
        elif signal == "theme":
            consumed = True
            self.load_colors()
        if not consumed:
            # print ("Don't know what to do with signal %s" % signal)
            pass
