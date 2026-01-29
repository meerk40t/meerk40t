"""
Attraction Widget governs over the scenes snap-to-grid and snap-to-elements. It is expected to be the first in the
list of widgets, to modify the later widget's events in the case of snapping.
"""

from math import sqrt
import time

import wx

from meerk40t.gui.scene.sceneconst import HITCHAIN_PRIORITY_HIT, RESPONSE_CHAIN
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui.wxutils import get_matrix_scale

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
        self.snap_attraction_points = None  # Clear all
        self.my_x = None
        self.my_y = None

        # Cache drawing resources to avoid repeated allocations
        self._cached_pens = {}
        self._cached_brushes = {}
        self._cached_matrix_scale = None
        self._cached_scale_value = None
        self._cached_attraction_lengths = {}

        self.visible_pen = wx.Pen()
        self.visible_pen.SetWidth(1)
        self.closeup_pen = wx.Pen()
        self.closeup_pen.SetWidth(1)
        self.load_colors()
        self.symbol_size = 1  # Will be replaced anyway

        # Should already be covered in wxmain choice panel, but are used here and thus set here.
        self.context.setting(int, "show_attract_len", 45)
        self.context.setting(int, "action_attract_len", 20)
        self.context.setting(int, "grid_attract_len", 15)
        self.context.setting(bool, "snap_grid", True)
        self.context.setting(bool, "snap_points", False)
        self.context.setting(bool, "snap_instant", False)
        self._show_snap_points = False
        self.snap_idle_time = 0.2
        self._idle_timer = None
        self._last_move_time = 0.0
        self._pending_snap = None

    def load_colors(self):
        """Load the current theme colors for the attraction widget."""
        self.visible_pen.SetColour(self.scene.colors.color_snap_visible)
        self.closeup_pen.SetColour(self.scene.colors.color_snap_closeup)

    def _get_cached_pen(self, color, width=1):
        """Cache pens to avoid repeated allocations."""
        key = (color, width)
        if key not in self._cached_pens:
            pen = wx.Pen()
            pen.SetColour(color)
            pen.SetWidth(width)
            self._cached_pens[key] = pen
        return self._cached_pens[key]

    def _get_cached_brush(self, color):
        """Cache brushes to avoid repeated allocations."""
        # Create a hashable key from the color
        try:
            # Try to get RGBA values if available
            color_key = (color.Red(), color.Green(), color.Blue(), color.Alpha())
        except AttributeError:
            # Fallback to RGB if Alpha is not available
            color_key = (color.Red(), color.Green(), color.Blue())

        if color_key not in self._cached_brushes:
            self._cached_brushes[color_key] = wx.Brush(colour=color, style=wx.BRUSHSTYLE_SOLID)
        return self._cached_brushes[color_key]

    def _get_matrix_scale(self, matrix):
        """Cache matrix scale calculations."""
        # Create a simple hash of the matrix for caching
        matrix_hash = hash((matrix.a, matrix.b, matrix.c, matrix.d, matrix.e, matrix.f))
        if self._cached_matrix_scale != matrix_hash:
            self._cached_matrix_scale = matrix_hash
            try:
                self._cached_scale_value = get_matrix_scale(matrix)
            except ZeroDivisionError:
                matrix.reset()
                self._cached_scale_value = 1.0
        return self._cached_scale_value

    def _get_attraction_lengths(self, matrix):
        """Cache attraction length calculations."""
        matrix_hash = hash((matrix.a, matrix.b, matrix.c, matrix.d, matrix.e, matrix.f))
        if matrix_hash not in self._cached_attraction_lengths:
            scale = self._get_matrix_scale(matrix)
            self._cached_attraction_lengths[matrix_hash] = {
                'show': self.context.show_attract_len / scale,
                'action': self.context.action_attract_len / scale,
                'grid': self.context.grid_attract_len / scale
            }
        return self._cached_attraction_lengths[matrix_hash]

    def final(self, context):
        """
        Cleanup method called when widget is being removed.
        Ensures timer is properly stopped to prevent memory leaks.
        """
        self._cleanup_timer()
        self._pending_snap = None

    def _cleanup_timer(self):
        """Stop and clear the idle timer if it exists."""
        if self._idle_timer is not None:
            try:
                self._idle_timer.Stop()
            except (AttributeError, RuntimeError):
                # Timer may already be stopped or destroyed
                pass
            self._idle_timer = None

    def hit(self):
        """
        Hit-Logic - by definition: yes, I want to be involved.
        In fact, if there's widgets to be hit, this should be the first (even if it's not)
        """
        return HITCHAIN_PRIORITY_HIT

    def _schedule_idle_update(self, sx, sy, snap_points, snap_grid):
        """Schedule snap point calculation after idle period."""
        if not snap_points and not snap_grid:
            return
        
        # Store pending snap parameters
        self._pending_snap = (sx, sy, snap_points, snap_grid)
        self._last_move_time = time.time()
        
        # Stop any existing timer to prevent race conditions
        self._cleanup_timer()
        
        # Schedule new timer
        self._idle_timer = wx.CallLater(
            int(self.snap_idle_time * 1000), self._run_idle_update
        )

    def _run_idle_update(self):
        """Execute deferred snap calculation after idle period has elapsed."""
        if self._pending_snap is None:
            return
        
        sx, sy, snap_points, snap_grid = self._pending_snap
        
        # Check if enough time has actually elapsed (handles timer precision issues)
        elapsed = time.time() - self._last_move_time
        if elapsed < self.snap_idle_time:
            # Reschedule for remaining time
            remaining = self.snap_idle_time - elapsed
            if remaining < 0:
                remaining = 0
            # Clean up current timer before creating new one
            self._idle_timer = None
            self._idle_timer = wx.CallLater(
                int(remaining * 1000), self._run_idle_update
            )
            return
        
        # Clear timer reference since this execution is complete
        self._idle_timer = None
        
        # Validate conditions before updating
        if self.scene.pane.ignore_snap:
            return
        if not self.scene.pane.tool_active and not self.scene.pane.modif_active:
            return
        
        # Perform snap calculation and refresh display
        self.my_x = sx
        self.my_y = sy
        self._show_snap_points = True
        self.scene.calculate_display_points(sx, sy, snap_points, snap_grid)
        self.scene.request_refresh()

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

        snap_grid = ctx.snap_grid
        snap_points = ctx.snap_points
        self._show_snap_points = False
        if "shift" in modifiers:
            # Shift inverts the on/off of snaps,
            snap_grid = not snap_grid
            snap_points = not snap_points
            # but we just do that for the grid
            if snap_points:
                snap_points = False

        if not snap_points and not snap_grid:
            # We are not going to snap.
            self._pending_snap = None
            self._cleanup_timer()
            return RESPONSE_CHAIN

        if not self.scene.pane.tool_active and not self.scene.pane.modif_active:
            # Nothing is active that would need snapping.
            return RESPONSE_CHAIN

        if self.scene.pane.ignore_snap:
            return RESPONSE_CHAIN

        if event_type in ("move", "hover", "hover_start"):
            # Check if instant snap calculation is enabled
            if not ctx.snap_instant:
                # Use delayed calculation (after idle period)
                self.scene.snap_display_points = []
                self._show_snap_points = False
                self._schedule_idle_update(self.my_x, self.my_y, snap_points, snap_grid)
                return RESPONSE_CHAIN
            # Otherwise fall through to immediate calculation

        self._show_snap_points = True

        # Inform profiler
        ctx.elements.set_start_time("attr_calc_disp")
        self.scene.calculate_display_points(
            self.my_x, self.my_y, snap_points, snap_grid
        )
        ctx.elements.set_end_time(
            "attr_calc_disp",
            message=f"points added={len(self.scene.snap_display_points)}",
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

        res_x, res_y = self.scene.calculate_snap(self.my_x, self.my_y)
        if res_x is None:
            return RESPONSE_CHAIN
        else:
            return RESPONSE_CHAIN, res_x, res_y

    def _get_pen_and_size(self, closeup):
        """Get the appropriate pen and symbol size for the given closeup level."""
        if closeup == 2:  # closest
            pen = self.closeup_pen
            sym_size = 1.5 * self.symbol_size
        elif closeup == 1:  # within snap range
            pen = self.visible_pen
            sym_size = self.symbol_size
        else:  # visible but not in snap range
            pen = self.visible_pen
            sym_size = 0.75 * self.symbol_size
        return pen, sym_size

    def _draw_caret(self, gc, x, y, closeup):
        pen, sym_size = self._get_pen_and_size(closeup)
        gc.SetPen(pen)
        brush = self._get_cached_brush(pen.GetColour())
        gc.SetBrush(brush)

        # Use path-based drawing for GraphicsContext
        half_size = sym_size / 2
        path = gc.CreatePath()
        path.MoveToPoint(x - half_size, y)
        path.AddLineToPoint(x, y - half_size)
        path.AddLineToPoint(x + half_size, y)
        path.AddLineToPoint(x, y + half_size)
        path.CloseSubpath()
        gc.DrawPath(path)

    def _draw_center(self, gc, x, y, closeup):
        pen, sym_size = self._get_pen_and_size(closeup)
        gc.SetPen(pen)
        brush = self._get_cached_brush(pen.GetColour())
        gc.SetBrush(brush)

        half_size = sym_size / 2
        # Draw a star shape using path for GraphicsContext
        path = gc.CreatePath()
        path.MoveToPoint(x - half_size, y - half_size)
        path.AddLineToPoint(x, y)
        path.AddLineToPoint(x + half_size, y - half_size)
        path.AddLineToPoint(x + half_size, y + half_size)
        path.AddLineToPoint(x, y)
        path.AddLineToPoint(x - half_size, y + half_size)
        path.CloseSubpath()
        gc.DrawPath(path)

    def _draw_gridpoint(self, gc, x, y, closeup):
        pen, sym_size = self._get_pen_and_size(closeup)
        gc.SetPen(pen)
        brush = self._get_cached_brush(pen.GetColour())
        gc.SetBrush(brush)

        dsize = sym_size / 8
        half_size = sym_size / 2
        # Draw cross using rectangles for better performance
        gc.DrawRectangle(x - dsize, y - half_size, 2 * dsize, sym_size)
        gc.DrawRectangle(x - half_size, y - dsize, sym_size, 2 * dsize)

    def _draw_midpoint(self, gc, x, y, closeup):
        pen, sym_size = self._get_pen_and_size(closeup)
        gc.SetPen(pen)
        brush = self._get_cached_brush(pen.GetColour())
        gc.SetBrush(brush)

        half_size = sym_size / 2
        # Draw diamond shape using path for GraphicsContext
        path = gc.CreatePath()
        path.MoveToPoint(x - half_size, y)
        path.AddLineToPoint(x, y - half_size)
        path.AddLineToPoint(x + half_size, y)
        path.AddLineToPoint(x, y + half_size)
        path.CloseSubpath()
        gc.DrawPath(path)

    def process_draw(self, gc):
        """
        Draw all attraction points on the scene with optimized calculations and caching.
        """
        if not self._show_snap_points:
            return

        self.visible_pen.SetColour(self.scene.colors.color_snap_visible)
        self.closeup_pen.SetColour(self.scene.colors.color_snap_closeup)

        matrix = self.parent.matrix
        scale = self._get_matrix_scale(matrix)
        if scale == 0:
            return

        # Cache symbol size calculation
        self.symbol_size = 10 / scale

        # Get cached attraction lengths
        lengths = self._get_attraction_lengths(matrix)
        local_attract_len = lengths['show']
        local_action_attract_len = lengths['action']
        local_grid_attract_len = lengths['grid']

        # Pre-calculate squared distances for better performance
        my_x, my_y = self.my_x, self.my_y
        attract_sq = local_attract_len * local_attract_len

        min_delta = float("inf")
        min_x = None
        min_y = None
        min_type = None

        # Use a dictionary to map point types to drawing functions
        draw_funcs = {
            TYPE_POINT: self._draw_caret,
            TYPE_BOUND: self._draw_caret,
            TYPE_MIDDLE: self._draw_midpoint,
            TYPE_MIDDLE_SMALL: self._draw_midpoint,
            TYPE_CENTER: self._draw_center,
            TYPE_GRID: self._draw_gridpoint,
        }

        for pts in self.scene.snap_display_points:
            x, y, pt_type = pts[0], pts[1], pts[2]

            # Early exit if point is outside attraction range
            dx = x - my_x
            dy = y - my_y
            dist_sq = dx * dx + dy * dy
            if dist_sq > attract_sq:
                continue

            delta = sqrt(dist_sq)

            # Determine if point is within snap range
            distance = (
                local_grid_attract_len if pt_type == TYPE_GRID else local_action_attract_len
            )
            closeup = 1 if abs(dx) <= distance and abs(dy) <= distance else 0

            # Track closest visible point regardless of type
            if delta < min_delta:
                min_delta = delta
                min_x, min_y, min_type = x, y, pt_type

            # Draw the point
            if pt_type in draw_funcs:
                draw_funcs[pt_type](gc, x, y, closeup)

        # Draw the closest point with highlight
        if min_x is not None and min_type in draw_funcs:
            draw_funcs[min_type](gc, min_x, min_y, 2)  # closeup = 2 for closest

    def _clear_caches(self):
        """Clear all caches when matrix or settings change."""
        self._cached_pens.clear()
        self._cached_brushes.clear()
        self._cached_matrix_scale = None
        self._cached_scale_value = None
        self._cached_attraction_lengths.clear()

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which indicate that we need to refresh / discard some data
        """
        if signal in ("modified", "emphasized", "element_added", "modified_by_tool"):
            self.scene.context.elements.set_start_time("attraction")
            self.scene.reset_snap_attraction()
            self.scene.context.elements.set_end_time("attraction")
        elif signal == "theme":
            self.load_colors()
            self._clear_caches()  # Clear caches when theme changes
