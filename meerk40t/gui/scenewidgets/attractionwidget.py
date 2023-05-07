"""
Attraction Widget governs over the scenes snap-to-grid and snap-to-elements. It is expected to be the first in the
list of widgets, to modify the later widget's events in the case of snapping.
"""

from math import sqrt

import wx

from meerk40t.core.elements.element_types import elem_nodes
from meerk40t.gui.scene.sceneconst import HITCHAIN_PRIORITY_HIT, RESPONSE_CHAIN
from meerk40t.gui.scene.widget import Widget

TYPE_BOUND = 0
TYPE_POINT = 1
TYPE_MIDDLE = 2
TYPE_CENTER = 3
TYPE_GRID = 4
TYPE_MIDDLE_SMALL = 5


class AttractionWidget(Widget):
    """
    Interface Widget - computes and displays attraction points, performs snapping.
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
        self._snap_grid = False
        self._snap_points = False

    def load_colors(self):
        self.visible_pen.SetColour(self.scene.colors.color_snap_visible)
        self.closeup_pen.SetColour(self.scene.colors.color_snap_closeup)

    def hit(self):
        """
        Hit-Logic - by definition: yes, I want to be involved.
        In fact, if there's widgets to be hit, this should be the first (even if it's not)
        """
        return HITCHAIN_PRIORITY_HIT

    def event(
        self, window_pos=None, space_pos=None, event_type=None, modifiers=None, **kwargs
    ):
        """
        Process the events. In all cases we will chain all events. The only way this widget affects the underlying
        widgets is by returning values with the chain during a registered snap, when all criteria are met.
        """

        if space_pos is None:
            return RESPONSE_CHAIN

        if event_type not in (
            "leftdown",
            "leftup",
            "leftclick",
            "move",
            "hover",
            "hover_start",
        ):
            return RESPONSE_CHAIN

        self.my_x = space_pos[0]
        self.my_y = space_pos[1]
        ctx = self.context

        self._snap_grid = ctx.snap_grid
        self._snap_points = ctx.snap_points
        self._show_snap_points = False
        if "shift" in modifiers:
            # Shift inverts the on/off of snaps.
            self._snap_grid = not self._snap_grid
            self._snap_points = not self._snap_points

        if not self._snap_points and not self._snap_grid:
            # We are not going to snap.
            return RESPONSE_CHAIN

        if not self.scene.pane.tool_active and not self.scene.pane.modif_active:
            # Nothing is active that would need snapping.
            return RESPONSE_CHAIN

        self._show_snap_points = True

        # Inform profiler
        ctx.elements.set_start_time("attr_calc_disp")
        self._calculate_display_points()
        ctx.elements.set_end_time(
            "attr_calc_disp", message=f"points added={len(self.display_points)}"
        )

        if event_type in (
            "hover",
            "hover_start",
        ):
            # Hovers show snaps, but they do not snap.
            return RESPONSE_CHAIN

        if event_type in ("leftup", "leftclick"):
            # We are finished, turn off the snow snap.

            # Na, we don't need points to be displayed
            # (but we needed the calculation)
            self._show_snap_points = False

        # Loop through display points, find closest.
        if self.display_points and self.my_x is not None:
            # Has to be lower than the action threshold
            min_delta = float("inf")
            new_x = None
            new_y = None
            for pt in self.display_points:
                dx = pt[0] - self.my_x
                dy = pt[1] - self.my_y
                delta = dx * dx + dy * dy
                if delta < min_delta:
                    new_x = pt[0]
                    new_y = pt[1]
                    min_delta = delta
            if new_x is None:
                return RESPONSE_CHAIN
            matrix = self.parent.matrix
            pixel = self.context.action_attract_len / matrix.value_scale_x()
            if abs(new_x - self.my_x) <= pixel and abs(new_y - self.my_y) <= pixel:
                # If the distance small enough, snap.
                return RESPONSE_CHAIN, new_x, new_y
        return RESPONSE_CHAIN

    def _draw_caret(self, gc, x, y, closeup):
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

    def _draw_center(self, gc, x, y, closeup):
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

    def _draw_gridpoint(self, gc, x, y, closeup):
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

    def _draw_midpoint(self, gc, x, y, closeup):
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
        if not self._show_snap_points:
            return

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
        local_grid_attract_len = self.context.grid_attract_len / matrix.value_scale_x()

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
                    self._draw_caret(gc, pts[0], pts[1], closeup)
                elif pts[2] == TYPE_MIDDLE:
                    self._draw_midpoint(gc, pts[0], pts[1], closeup)
                elif pts[2] == TYPE_MIDDLE_SMALL:
                    self._draw_midpoint(gc, pts[0], pts[1], closeup)
                elif pts[2] == TYPE_CENTER:
                    self._draw_center(gc, pts[0], pts[1], closeup)
                elif pts[2] == TYPE_GRID:
                    self._draw_gridpoint(gc, pts[0], pts[1], closeup)
        # Draw the closest point
        if min_x is not None:
            closeup = 2  # closest
            if min_type in (TYPE_POINT, TYPE_BOUND):
                self._draw_caret(gc, min_x, min_y, closeup)
            elif min_type == TYPE_MIDDLE:
                self._draw_midpoint(gc, min_x, min_y, closeup)
            elif min_type == TYPE_MIDDLE_SMALL:
                self._draw_midpoint(gc, min_x, min_y, closeup)
            elif min_type == TYPE_CENTER:
                self._draw_center(gc, min_x, min_y, closeup)
            elif min_type == TYPE_GRID:
                self._draw_gridpoint(gc, min_x, min_y, closeup)

    def _calculate_attraction_points(self):
        """
        Looks at all elements (all_points=True) or at non-selected elements (all_points=False) and identifies all
        attraction points (center, corners, sides)
        """
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

    def _calculate_snap_points(self, length):
        """
        Recalculate the snap element attraction points

        @param length:
        @return:
        """
        for pts in self.attraction_points:
            if self.scene.pane.modif_active:
                if pts[3]:
                    # No snap points for emphasized objects.
                    continue
            if abs(pts[0] - self.my_x) <= length and abs(pts[1] - self.my_y) <= length:
                self.display_points.append([pts[0], pts[1], pts[2]])

    def _calculate_grid_points(self, length):
        """
        Recalculate the local grid points

        @param length:
        @return:
        """
        for pts in self.scene.pane.grid.grid_points:
            if abs(pts[0] - self.my_x) <= length and abs(pts[1] - self.my_y) <= length:
                self.display_points.append([pts[0], pts[1], TYPE_GRID])

    def _calculate_display_points(self):
        """
        Recalcuate the points that need to be displayed for the user.

        @return:
        """
        self.display_points = []
        if self.my_x is None:
            return
        if self.attraction_points is None and self._snap_points:
            self._calculate_attraction_points()

        matrix = self.parent.matrix
        length = self.context.show_attract_len / matrix.value_scale_x()

        if self._snap_points and self.attraction_points:
            self._calculate_snap_points(length)

        if self._snap_grid and self.scene.pane.grid.grid_points:
            self._calculate_grid_points(length)

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which indicate that we need to refresh / discard some data
        """
        if signal in ("modified", "emphasized", "element_added", "tool_modified"):
            self.attraction_points = None
        elif signal == "theme":
            self.load_colors()
