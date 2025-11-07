"""
Grid widget is primarily tasked with drawing the grid in the scene. This is the size and shape of the desired bedsize.
"""

from math import atan2, cos, sin, sqrt, tau
from platform import system

import numpy as np
import wx

from meerk40t.core.units import Length
from meerk40t.gui.laserrender import DRAW_MODE_GRID, DRAW_MODE_GUIDES
from meerk40t.gui.scene.widget import Widget


class GridWidget(Widget):
    """
    Scene Widget
    """

    def __init__(self, scene, name=None, suppress_labels=False):
        Widget.__init__(self, scene, all=True)
        self.name = "Standard" if name is None else name
        self.primary_grid_lines = None
        self.secondary_grid_lines = None
        self.background = None
        self.primary_grid_line_pen = wx.Pen()
        self.secondary_grid_line_pen = wx.Pen()
        self.circular_grid_line_pen = wx.Pen()
        self.offset_line_pen = wx.Pen()
        self.last_ticksize = 0
        self.last_w = 0
        self.last_h = 0
        self.last_min_x = float("inf")
        self.last_min_y = float("inf")
        self.last_max_x = -float("inf")
        self.last_max_y = -float("inf")
        if suppress_labels is None:
            suppress_labels = False
        self.suppress_labels_in_all_cases = suppress_labels

        self.draw_grid = True
        self.primary_start_x = 0
        self.primary_start_y = 0
        self.secondary_start_x = 0
        self.secondary_start_y = 0
        self.circular_grid_center_x = 0
        self.circular_grid_center_y = 0
        # Min and max coords of the screen estate
        self.min_x = 0
        self.min_y = 0
        self.max_x = 0
        self.max_y = 0
        self.primary_tick_length_x = 0
        self.primary_tick_length_y = 0
        self.secondary_tick_length_x = 0
        self.secondary_tick_length_y = 0
        self.zero_x = 0
        self.zero_y = 0
        # Circular Grid
        self.min_radius = float("inf")
        self.max_radius = -float("inf")
        self.min_angle = 0
        self.max_angle = tau
        self.os = system()

        # If there is a user margin then display the physical dimensions
        self.draw_offset_lines = False
        # Stuff related to grids and guides
        self.draw_grid_primary = True
        # Secondary grid, perpendicular, but with definable center and scaling
        self.draw_grid_secondary = False
        self.grid_secondary_cx = None
        self.grid_secondary_cy = None
        self.grid_secondary_scale_x = 1
        self.grid_secondary_scale_y = 1
        self.set_secondary_axis_scales()
        # Circular grid
        self.draw_grid_circular = False
        self.grid_circular_cx = None
        self.grid_circular_cy = None
        # self.auto_tick = False  # by definition do not auto_tick
        # Let the grid resize itself
        self.auto_tick = True
        self.tick_distance = 0

        self.grid_points = None  # Points representing the grid - total of primary + secondary + circular

        # Performance optimization caches
        self._grid_cache = {
            "cache_key": None,
            "primary_lines": [],
            "secondary_lines": [],
            # Note: circular and offset lines are drawn procedurally and don't benefit from caching
        }
        self._viewport_cache = {}
        self._viewport_cache_max_size = (
            50  # Limit cache size to prevent unbounded growth
        )
        self._last_matrix_state = None

        self.set_colors()

    def _get_cache_key(self, w, h):
        """Generate cache key for current viewport and grid settings"""
        mat = self.scene.widget_root.scene_widget.matrix

        return (
            w,
            h,
            self.tick_distance,
            self.draw_grid_primary,
            self.draw_grid_secondary,
            self.draw_grid_circular,
            self.draw_offset_lines,
            # Matrix transformation components
            mat.value_scale_x(),
            mat.value_scale_y(),
            mat.value_trans_x(),
            mat.value_trans_y(),
            mat.rotation,
            # Grid parameters
            self.grid_secondary_scale_x,
            self.grid_secondary_scale_y,
            self.grid_secondary_cx,
            self.grid_secondary_cy,
            self.grid_circular_cx,
            self.grid_circular_cy,
        )

    def _calculate_viewport_bounds(self, w, h):
        """Calculate visible bounds efficiently with caching and size limiting"""
        cache_key = (w, h)
        if cache_key in self._viewport_cache:
            return self._viewport_cache[cache_key]

        # Calculate bounds for all four corners
        bounds = [
            self.scene.convert_window_to_scene([0, 0]),
            self.scene.convert_window_to_scene([w, 0]),
            self.scene.convert_window_to_scene([0, h]),
            self.scene.convert_window_to_scene([w, h]),
        ]

        min_x = min(bound[0] for bound in bounds)
        max_x = max(bound[0] for bound in bounds)
        min_y = min(bound[1] for bound in bounds)
        max_y = max(bound[1] for bound in bounds)

        result = (min_x, min_y, max_x, max_y)

        # Implement simple LRU eviction to prevent unbounded cache growth
        if len(self._viewport_cache) >= self._viewport_cache_max_size:
            # Remove oldest entry (first item) to make room for new one
            oldest_key = next(iter(self._viewport_cache))
            del self._viewport_cache[oldest_key]

        self._viewport_cache[cache_key] = result
        return result

    def invalidate_cache(self):
        """Invalidate all cached data to force recalculation"""
        self._grid_cache = {
            "cache_key": None,
            "primary_lines": [],
            "secondary_lines": [],
            # Note: circular and offset lines are drawn procedurally and don't benefit from caching
        }
        self._viewport_cache.clear()
        # Clear legacy instance variables to ensure consistency
        self.primary_grid_lines = None
        self.secondary_grid_lines = None

    def _check_matrix_change(self):
        """Check if matrix has changed since last cache and invalidate if needed"""
        if hasattr(self, "_last_matrix_state"):
            mat = self.scene.widget_root.scene_widget.matrix
            current_state = (
                mat.value_scale_x(),
                mat.value_scale_y(),
                mat.value_trans_x(),
                mat.value_trans_y(),
                mat.rotation,
            )
            if current_state != self._last_matrix_state:
                self.invalidate_cache()
                self._last_matrix_state = current_state
        else:
            # First time - store current matrix state
            mat = self.scene.widget_root.scene_widget.matrix
            self._last_matrix_state = (
                mat.value_scale_x(),
                mat.value_scale_y(),
                mat.value_trans_x(),
                mat.value_trans_y(),
                mat.rotation,
            )

    def set_secondary_axis_scales(self):
        sx = 1.0
        sy = 1.0
        if hasattr(self.scene.context.device, "rotary"):
            if self.scene.context.device.rotary.scale_x is not None:
                sx = self.scene.context.device.rotary.scale_x
            if self.scene.context.device.rotary.scale_y is not None:
                sy = self.scene.context.device.rotary.scale_y

        self.grid_secondary_scale_x = sx
        self.grid_secondary_scale_y = sy

    @property
    def scene_scale(self):
        matrix = self.scene.widget_root.scene_widget.matrix
        try:
            scene_scale = sqrt(abs(matrix.determinant))
            if scene_scale < 1e-8:
                matrix.reset()
                return 1.0
            return scene_scale
        except (OverflowError, ValueError, ZeroDivisionError):
            matrix.reset()
        return 1.0

    ###########################
    # PEN SETUP
    ###########################

    def set_line_width(self, pen, line_width):
        # Sets the linewidth of a wx.pen
        # establish os-system
        if line_width < 1 and self.os == "Darwin":
            # Mac
            line_width = 1
        try:
            pen.SetWidth(line_width)
        except TypeError:
            pen.SetWidth(int(line_width))

    def _set_pen_width_from_matrix(self):
        line_width = 1.0 / self.scene_scale
        self.set_line_width(self.primary_grid_line_pen, line_width)
        self.set_line_width(self.secondary_grid_line_pen, line_width)
        self.set_line_width(self.circular_grid_line_pen, line_width)
        self.set_line_width(self.offset_line_pen, line_width)

    def set_colors(self):
        self.primary_grid_line_pen.SetColour(self.scene.colors.color_grid)
        self.secondary_grid_line_pen.SetColour(self.scene.colors.color_grid2)
        self.circular_grid_line_pen.SetColour(self.scene.colors.color_grid3)
        self.offset_line_pen.SetColour(wx.GREEN)
        self.set_line_width(self.primary_grid_line_pen, 1)
        self.set_line_width(self.secondary_grid_line_pen, 1)
        self.set_line_width(self.circular_grid_line_pen, 1)
        self.set_line_width(self.offset_line_pen, 1)

    ###########################
    # CALCULATE GRID LINES
    ###########################

    def _calc_primary_grid_lines(self):
        """
        Calculate primary grid lines with automatic vectorization for performance.
        Uses vectorized calculations for large grids, falls back to loops for small ones.
        """
        if self._should_use_vectorization():
            self.primary_grid_lines = self._calc_primary_grid_lines_vectorized()
        else:
            self.primary_grid_lines = self._calc_primary_grid_lines_original()

    def _calc_secondary_grid_lines(self):
        """
        Calculate secondary grid lines with automatic vectorization for performance.
        Uses vectorized calculations for large grids, falls back to loops for small ones.
        """
        if self._should_use_vectorization():
            self.secondary_grid_lines = self._calc_secondary_grid_lines_vectorized()
        else:
            self.secondary_grid_lines = self._calc_secondary_grid_lines_original()

    def _should_use_vectorization(self, threshold: int = 80) -> bool:
        """
        Determine if vectorization should be used based on estimated grid complexity.

        Args:
            threshold: Minimum number of lines to trigger vectorization

        Returns:
            True if vectorization is recommended
        """
        try:
            # Estimate grid line count
            dx = abs(self.primary_tick_length_x)
            dy = abs(self.primary_tick_length_y)

            if dx == 0 or dy == 0:
                return False

            # Estimate lines
            width = self.max_x - self.min_x
            height = self.max_y - self.min_y

            vertical_lines = int(width / dx) + 1
            horizontal_lines = int(height / dy) + 1
            total_lines = vertical_lines + horizontal_lines

            return total_lines >= threshold
        except (AttributeError, ZeroDivisionError):
            return False

    def _calc_primary_grid_lines_vectorized(self):
        """Vectorized primary grid calculation using NumPy for better performance."""
        dx = abs(self.primary_tick_length_x)
        dy = abs(self.primary_tick_length_y)

        # Calculate starting points
        start_x = self._calculate_starting_point(self.zero_x, dx, self.min_x)
        start_y = self._calculate_starting_point(self.zero_y, dy, self.min_y)

        # Use linspace for accurate floating point grid generation
        # Calculate number of points to ensure we cover the full range
        num_x = int((self.max_x - start_x) / dx) + 1
        num_y = int((self.max_y - start_y) / dy) + 1

        # Generate coordinates using linspace for precise coverage
        x_coords = np.linspace(start_x, start_x + (num_x - 1) * dx, num_x)
        y_coords = np.linspace(start_y, start_y + (num_y - 1) * dy, num_y)

        # Filter to stay within bounds, using np.isclose for boundary precision
        # This handles floating point precision errors that could exclude boundary grid lines
        tolerance = 1e-10
        x_within_bounds = (x_coords <= self.max_x) | np.isclose(
            x_coords, self.max_x, atol=tolerance
        )
        y_within_bounds = (y_coords <= self.max_y) | np.isclose(
            y_coords, self.max_y, atol=tolerance
        )
        x_coords = x_coords[x_within_bounds]
        y_coords = y_coords[y_within_bounds]

        # Generate line segments
        starts = []
        ends = []

        # Vertical lines
        for x in x_coords:
            starts.append((x, self.min_y))
            ends.append((x, self.max_y))

        # Horizontal lines
        for y in y_coords:
            starts.append((self.min_x, y))
            ends.append((self.max_x, y))

        return starts, ends

    def _calc_secondary_grid_lines_vectorized(self):
        """Vectorized secondary grid calculation using NumPy for better performance."""
        dx = abs(self.secondary_tick_length_x)
        dy = abs(self.secondary_tick_length_y)

        # Calculate starting points
        start_x = self._calculate_starting_point(self.zero_x, dx, self.min_x)
        start_y = self._calculate_starting_point(self.zero_y, dy, self.min_y)

        # Use linspace for accurate floating point grid generation
        # Calculate number of points to ensure we cover the full range
        num_x = int((self.max_x - start_x) / dx) + 1
        num_y = int((self.max_y - start_y) / dy) + 1

        # Generate coordinates using linspace for precise coverage
        x_coords = np.linspace(start_x, start_x + (num_x - 1) * dx, num_x)
        y_coords = np.linspace(start_y, start_y + (num_y - 1) * dy, num_y)

        # Filter to stay within bounds, using np.isclose for boundary precision
        # This handles floating point precision errors that could exclude boundary grid lines
        tolerance = 1e-10
        x_within_bounds = (x_coords <= self.max_x) | np.isclose(
            x_coords, self.max_x, atol=tolerance
        )
        y_within_bounds = (y_coords <= self.max_y) | np.isclose(
            y_coords, self.max_y, atol=tolerance
        )
        x_coords = x_coords[x_within_bounds]
        y_coords = y_coords[y_within_bounds]

        # Generate line segments
        starts = []
        ends = []

        # Vertical lines
        for x in x_coords:
            starts.append((x, self.min_y))
            ends.append((x, self.max_y))

        # Horizontal lines
        for y in y_coords:
            starts.append((self.min_x, y))
            ends.append((self.max_x, y))

        return starts, ends

    def _calculate_starting_point(
        self, zero_pos: float, step: float, min_bound: float
    ) -> float:
        """Calculate optimal starting point for grid lines."""
        start = zero_pos
        while start - step > min_bound:
            start -= step
        while start < min_bound:
            start += step
        return start

    def _calc_primary_grid_lines_original(self):
        """Original loop-based primary grid calculation (preserved for small grids)."""
        starts = []
        ends = []
        # Primary grid
        # We could be way too high
        start_x = self.zero_x
        dx = abs(self.primary_tick_length_x)
        dy = abs(self.primary_tick_length_y)
        while start_x - dx > self.min_x:
            start_x -= dx
        start_y = self.zero_y
        while start_y - dy > self.min_y:
            start_y -= dy
        # But we could be way too low, too
        while start_x < self.min_x:
            start_x += dx
        while start_y < self.min_y:
            start_y += dy

        x = start_x
        while x <= self.max_x:
            starts.append((x, self.min_y))
            ends.append((x, self.max_y))
            x += dx

        y = start_y
        while y <= self.max_y:
            starts.append((self.min_x, y))
            ends.append((self.max_x, y))
            y += dy
        return starts, ends

    def _calc_secondary_grid_lines_original(self):
        """Original loop-based secondary grid calculation (preserved for small grids)."""
        starts2 = []
        ends2 = []
        # Primary grid
        # Secondary grid
        # We could be way too high
        start_x = self.zero_x
        dx = abs(self.secondary_tick_length_x)
        dy = abs(self.secondary_tick_length_y)
        while start_x - dx > self.min_x:
            start_x -= dx
        start_y = self.zero_y
        while start_y - dy > self.min_y:
            start_y -= dy
        # But we could be way too low, too
        while start_x < self.min_x:
            start_x += dx
        while start_y < self.min_y:
            start_y += dy

        x = start_x
        while x <= self.max_x:
            starts2.append((x, self.min_y))
            ends2.append((x, self.max_y))
            x += dx

        y = start_y
        while y <= self.max_y:
            starts2.append((self.min_x, y))
            ends2.append((self.max_x, y))
            y += dy
        return starts2, ends2

    def calculate_grid_lines(self):
        """
        Based on the current matrix calculate the grid within the bed-space.
        """
        d = self.scene.context
        self.set_secondary_axis_scales()
        self.zero_x, self.zero_y = d.space.origin_zero()
        self._calc_primary_grid_lines()
        self._calc_secondary_grid_lines()

    ###########################
    # CALCULATE PROPERTIES
    ###########################

    @property
    def scaled_conversion(self):
        return float(Length(f"1{self.scene.context.units_name}")) * self.scene_scale

    def calculate_tickdistance(self, w, h):
        # Establish the delta for about 15 ticks
        wpoints = w / 30.0
        hpoints = h / 20.0
        points = (wpoints + hpoints) / 2
        scaled_conversion = self.scaled_conversion
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

        self.tick_distance = delta1

    def calculate_center_start(self):
        p = self.scene.context
        self.primary_start_x, self.primary_start_y = p.space.origin_zero()

        if self.grid_secondary_cx is None:
            self.secondary_start_x = self.primary_start_x
        else:
            self.secondary_start_x = self.grid_secondary_cx

        if self.grid_secondary_cy is None:
            self.secondary_start_y = self.primary_start_y
        else:
            self.secondary_start_y = self.grid_secondary_cy

        if self.grid_circular_cx is None:
            self.circular_grid_center_x = self.primary_start_x
        else:
            self.circular_grid_center_x = self.grid_circular_cx

        if self.grid_circular_cy is None:
            self.circular_grid_center_y = self.primary_start_y
        else:
            self.circular_grid_center_y = self.grid_circular_cy

    def calculate_gridsize(self, w, h):
        self.min_x = float("inf")
        self.max_x = -float("inf")
        self.min_y = float("inf")
        self.max_y = -float("inf")
        for xx in (0, w):
            for yy in (0, h):
                x, y = self.scene.convert_window_to_scene([xx, yy])
                self.min_x = min(self.min_x, x)
                self.min_y = min(self.min_y, y)
                self.max_x = max(self.max_x, x)
                self.max_y = max(self.max_y, y)

        # self.min_x, self.min_y = self.scene.convert_window_to_scene([0, 0])
        # self.max_x, self.max_y = self.scene.convert_window_to_scene([w, h])

        self.min_x = max(0, self.min_x)
        self.min_y = max(0, self.min_y)
        self.max_x = min(self.scene.context.space.width, self.max_x)
        self.max_y = min(self.scene.context.space.height, self.max_y)

    def calculate_tick_length(self):
        tick_length = float(
            Length(f"{self.tick_distance}{self.scene.context.units_name}")
        )
        if tick_length == 0:
            tick_length = float(Length("10mm"))
        self.primary_tick_length_x = tick_length
        self.primary_tick_length_y = tick_length
        # print (f"x={self.tlenx1} ({Length(amount=self.tlenx1, digits=3).length_mm})")
        # print (f"y={self.tleny1} ({Length(amount=self.tleny1, digits=3).length_mm})")
        self.secondary_tick_length_x = (
            self.primary_tick_length_x * self.grid_secondary_scale_x
        )
        self.secondary_tick_length_y = (
            self.primary_tick_length_y * self.grid_secondary_scale_y
        )

    def calculate_radii_angles(self):
        # let's establish which circles we really have to draw
        self.min_radius = float("inf")
        self.max_radius = -float("inf")
        test_points = (
            # all 4 corners
            (self.min_x, self.min_y),
            (self.min_x, self.max_y),
            (self.max_x, self.min_y),
            (self.max_x, self.max_y),
            # and the boundary points aligned with the center
            (self.circular_grid_center_x, self.max_y),
            (self.circular_grid_center_x, self.min_y),
            (self.min_x, self.circular_grid_center_y),
            (self.max_x, self.circular_grid_center_y),
        )
        for pt in test_points:
            dx = pt[0] - self.circular_grid_center_x
            dy = pt[1] - self.circular_grid_center_y
            r = sqrt(dx * dx + dy * dy)
            if r < self.min_radius:
                self.min_radius = r
            if r > self.max_radius:
                self.max_radius = r

        # 1 | 2 | 3
        # --+---+--
        # 4 | 5 | 6
        # --+---+--
        # 7 | 8 | 9
        min_a = float("inf")
        max_a = -float("inf")
        if self.circular_grid_center_x <= self.min_x:
            # left
            if self.circular_grid_center_y <= self.min_y:
                # below
                pt1 = (self.min_x, self.max_y)
                pt2 = (self.max_x, self.min_y)
            elif self.circular_grid_center_y >= self.max_y:
                # above
                pt1 = (self.max_x, self.max_y)
                pt2 = (self.min_x, self.min_y)
            else:
                # between
                pt1 = (self.min_x, self.max_y)
                pt2 = (self.min_x, self.min_y)
        elif self.circular_grid_center_x >= self.max_x:
            # right
            if self.circular_grid_center_y <= self.min_y:
                # below
                pt1 = (self.min_x, self.min_y)
                pt2 = (self.max_x, self.max_y)
            elif self.circular_grid_center_y >= self.max_y:
                # above
                pt1 = (self.max_x, self.min_y)
                pt2 = (self.min_x, self.max_y)
            else:
                # between
                pt1 = (self.max_x, self.min_y)
                pt2 = (self.max_x, self.max_y)
        else:
            # between
            if self.circular_grid_center_y <= self.min_y:
                # below
                pt1 = (self.min_x, self.min_y)
                pt2 = (self.max_x, self.min_y)
            elif self.circular_grid_center_y >= self.max_y:
                # above
                pt1 = (self.max_x, self.max_y)
                pt2 = (self.min_x, self.max_y)
            else:
                # between
                pt1 = None
                pt2 = None
                min_a = 0
                max_a = tau
        if pt1 is not None:
            dx1 = pt1[0] - self.circular_grid_center_x
            dy1 = pt1[1] - self.circular_grid_center_y
            dx2 = pt2[0] - self.circular_grid_center_x
            dy2 = pt2[1] - self.circular_grid_center_y
            max_a = atan2(dy1, dx1)
            min_a = atan2(dy2, dx2)

        while max_a < min_a:
            max_a += tau
        while min_a < 0:
            min_a += tau
            max_a += tau
        self.min_angle = min_a
        self.max_angle = max_a
        if (
            self.min_x < self.circular_grid_center_x < self.max_x
            and self.min_y < self.circular_grid_center_y < self.max_y
        ):
            self.min_radius = 0

    ###########################
    # CALCULATE GRID POINTS
    ###########################

    def calculate_scene_grid_points(self):
        """
        Looks at all elements (all_points=True) or at non-selected elements (all_points=False)
        and identifies all attraction points (center, corners, sides)
        Notabene this calculation generates SCREEN coordinates
        """
        self.grid_points = []  # Clear all

        # Let's add grid points - set just the visible part of the grid

        if self.draw_grid_primary:
            self._calculate_grid_points_primary()
        if self.draw_grid_secondary:
            self._calculate_grid_points_secondary()
        if self.draw_grid_circular:
            self._calculate_grid_points_circular()

    def _calculate_grid_points_primary(self):
        # That's easy just the rectangular stuff
        # We could be way too high
        start_x = self.zero_x
        while start_x - self.primary_tick_length_x > self.min_x:
            start_x -= self.primary_tick_length_x
        start_y = self.zero_y
        while start_y - self.primary_tick_length_y > self.min_y:
            start_y -= self.primary_tick_length_y
        # But we could be way too low, too
        while start_x < self.min_x:
            start_x += self.primary_tick_length_x
        while start_y < self.min_y:
            start_y += self.primary_tick_length_y
        x = start_x
        while x <= self.max_x:
            y = start_y
            while y <= self.max_y:
                # mx, my = self.scene.convert_scene_to_window([x, y])
                self.grid_points.append([x, y])
                y += self.primary_tick_length_y
            x += self.primary_tick_length_x

    def _calculate_grid_points_secondary(self):
        if (
            self.draw_grid_primary
            and self.primary_start_x == 0
            and self.primary_start_y == 0
            and self.grid_secondary_scale_x == 1
            and self.grid_secondary_scale_y == 1
        ):
            return  # is it identical to the primary?
        # We could be way too high
        start_x = self.zero_x
        while start_x - self.secondary_tick_length_x > self.min_x:
            start_x -= self.secondary_tick_length_x
        start_y = self.zero_y
        while start_y - self.secondary_tick_length_y > self.min_y:
            start_y -= self.secondary_tick_length_y
        # But we could be way too low, too
        while start_x < self.min_x:
            start_x += self.secondary_tick_length_x
        while start_y < self.min_y:
            start_y += self.secondary_tick_length_y
        x = start_x
        while x <= self.max_x:
            y = start_y
            while y <= self.max_y:
                # mx, my = self.scene.convert_scene_to_window([x, y])
                self.grid_points.append([x, y])
                y += self.secondary_tick_length_y
            x += self.secondary_tick_length_x

    def _calculate_grid_points_circular(self):
        p = self.scene.context
        # Okay, we are drawing on 48 segments line, even from center to outline, odd from 1/3rd to outline
        start_x = self.circular_grid_center_x
        start_y = self.circular_grid_center_y
        x = start_x
        y = start_y
        # mx, my = self.scene.convert_scene_to_window([x, y])
        self.grid_points.append([x, y])
        max_r = abs(
            complex(p.device.view.unit_width, p.device.view.unit_height)
        )  # hypot
        tick_length = (self.primary_tick_length_x + self.primary_tick_length_y) / 2
        r_fourth = max_r // (4 * tick_length) * tick_length
        segments = 48
        r_angle = 0
        i = 0
        while r_angle < self.min_angle:
            r_angle += tau / segments
            i += 1
        while r_angle < self.max_angle:
            c_angle = r_angle
            while c_angle > tau:
                c_angle -= tau
            r = 0 if i % 2 == 0 else r_fourth
            while r < self.min_radius:
                r += tick_length

            while r <= self.max_radius:
                r += tick_length
                x = start_x + r * cos(c_angle)
                y = start_y + r * sin(c_angle)

                if self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y:
                    # mx, my = self.scene.convert_scene_to_window([x, y])
                    self.grid_points.append([x, y])

            i += 1
            r_angle += tau / segments

    ###########################
    # WIDGET DRAW AND PROCESS
    ###########################

    def _ensure_grid_calculated(self, w, h):
        """
        Centralized method to ensure grid data is calculated and cached.
        Returns True if recalculation was needed, False if cache was used.
        """
        # Check for matrix changes that would invalidate cached calculations
        self._check_matrix_change()

        if self.auto_tick:
            self.calculate_tickdistance(w, h)
        self.calculate_center_start()
        self.calculate_gridsize(w, h)
        self.calculate_tick_length()
        self.calculate_radii_angles()

        # Check if we can use cached grid data
        cache_key = self._get_cache_key(w, h)

        if self._grid_cache["cache_key"] != cache_key:
            # Recalculate grid lines and cache them
            self.calculate_grid_lines()
            self.calculate_scene_grid_points()

            # Cache the calculated grid lines
            self._grid_cache["primary_lines"] = self.primary_grid_lines
            self._grid_cache["secondary_lines"] = self.secondary_grid_lines
            self._grid_cache["cache_key"] = cache_key
            return True  # Recalculation performed

        # Use cached data if available
        if self._grid_cache["primary_lines"] is not None:
            self.primary_grid_lines = self._grid_cache["primary_lines"]
        if self._grid_cache["secondary_lines"] is not None:
            self.secondary_grid_lines = self._grid_cache["secondary_lines"]

        return False  # Used cache

    def process_draw(self, gc):
        """
        Draw the grid on the scene.
        """
        # Get proper gridsize
        w, h = gc.Size
        if w < 50 or h < 50:
            # Algorithm is unstable for very low values of w or h.
            return

        if self.scene.context.draw_mode & DRAW_MODE_GRID != 0:
            return  # Do not draw grid.

        # Ensure grid data is calculated and cached
        self._ensure_grid_calculated(w, h)

        # Draw using optimized methods
        self._draw_grid_optimized(gc)

    def _draw_grid_optimized(self, gc):
        """Draw grid using cached data with optimized rendering."""
        # Set up drawing context
        self._set_pen_width_from_matrix()
        gc.SetPen(self.primary_grid_line_pen)
        brush = wx.Brush(
            colour=self.scene.colors.color_bed, style=wx.BRUSHSTYLE_TRANSPARENT
        )
        gc.SetBrush(brush)

        # Draw all grid components
        if self.draw_offset_lines:
            self._draw_boundary(gc)
        if self.draw_grid_circular:
            self._draw_grid_circular(gc)
        if self.draw_grid_secondary:
            self._draw_grid_secondary(gc)
        if self.draw_grid_primary:
            self._draw_grid_primary(gc)

    def _draw_boundary(self, gc):
        gc.SetPen(self.offset_line_pen)
        vw = self.scene.context.device.view
        margin_x = -1 * float(Length(vw.margin_x))
        margin_y = -1 * float(Length(vw.margin_y))
        mx = vw.unit_width
        my = vw.unit_height
        ox = margin_x
        oy = margin_y

        grid_path = gc.CreatePath()
        grid_path.MoveToPoint(ox, oy)
        grid_path.AddLineToPoint(ox, my)
        grid_path.AddLineToPoint(mx, my)
        grid_path.AddLineToPoint(mx, oy)
        grid_path.AddLineToPoint(ox, oy)
        gc.StrokePath(grid_path)

    def _draw_grid_primary(self, gc):
        if self.primary_grid_lines is None:
            return  # No grid data available
        starts, ends = self.primary_grid_lines
        gc.SetPen(self.primary_grid_line_pen)
        if starts and ends:
            # Use efficient batch line drawing instead of individual path segments
            gc.StrokeLineSegments(starts, ends)

    def _draw_grid_secondary(self, gc):
        if self.secondary_grid_lines is None:
            return  # No grid data available
        starts2, ends2 = self.secondary_grid_lines
        gc.SetPen(self.secondary_grid_line_pen)
        if starts2 and ends2:
            # Use efficient batch line drawing instead of individual path segments
            gc.StrokeLineSegments(starts2, ends2)

    def _draw_grid_circular(self, gc):
        gc.SetPen(self.circular_grid_line_pen)
        u_width = float(self.scene.context.device.view.unit_width)
        u_height = float(self.scene.context.device.view.unit_height)
        gc.Clip(0, 0, u_width, u_height)
        # siz = sqrt(u_width * u_width + u_height * u_height)
        # sox = self.circular_grid_center_x / u_width
        # soy = self.circular_grid_center_y / u_height
        step = self.primary_tick_length_x
        # factor = max(2 * (1 - sox), 2 * (1 - soy))
        # Initially I drew a complete circle, which is a waste in most situations,
        # so let's create a path
        circle_path = gc.CreatePath()
        y = 0
        # Start from minimum radius, incrementing by step size
        while y < 2 * self.min_radius:
            y += 2 * step
        # Draw concentric circles from min_radius to max_radius
        while y < 2 * self.max_radius:
            y += 2 * step
            radius = y / 2
            spoint_x = self.circular_grid_center_x + radius * cos(self.min_angle)
            spoint_y = self.circular_grid_center_y + radius * sin(self.min_angle)
            circle_path.MoveToPoint(spoint_x, spoint_y)
            # Draw arc from min_angle to max_angle with specified radius
            circle_path.AddArc(
                self.circular_grid_center_x,
                self.circular_grid_center_y,
                radius,
                self.min_angle,
                self.max_angle,
                True,
            )
        gc.StrokePath(circle_path)
        # (around one fourth of radius)
        mid_y = y // (4 * step) * step
        # print("Last Y=%.1f (%s), mid_y=%.1f (%s)" % (y, Length(amount=y).length_mm, mid_y, Length(amount=mid_y).length_mm))
        radials_start = []
        radials_end = []
        fsize = 10 / self.scene.widget_root.scene_widget.matrix.value_scale_x()
        fsize = max(fsize, 1.0)  # Mac does not allow values lower than 1.
        try:
            font = wx.Font(
                fsize,
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD,
            )
        except TypeError:
            font = wx.Font(
                int(fsize),
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD,
            )
        # gc.SetFont(font, wx.BLACK)
        # debugstr = "Angle= %.1f - %.1f (%d)" % (self.min_angle/tau*360, self.max_angle/tau*360, self.sector)
        # gc.DrawText(debugstr, (self.min_x + self.max_x)/2, (self.min_y + self.max_y)/2)
        gc.SetFont(font, self.scene.colors.color_guide3)
        segments = 48
        r_angle = 0
        i = 0
        while r_angle < self.min_angle:
            r_angle += tau / segments
            i += 1

        # Draw radials...
        while r_angle < self.max_angle:
            c_angle = r_angle
            while c_angle > tau:
                c_angle -= tau
            if i % 2 == 0:
                degang = round(c_angle / tau * 360, 1)
                if degang == 360:
                    degang = 0
                a_text = f"{degang:.0f}°"
                (t_width, t_height) = gc.GetTextExtent(a_text)
                # Make sure text remains legible without breaking your neck... ;-)
                if tau * 1 / 4 < c_angle < tau * 3 / 4:
                    myangle = (-1.0 * c_angle) + tau / 2
                    dx = t_width
                else:
                    myangle = -1.0 * c_angle
                    dx = 0
                if (
                    self.scene.context.draw_mode & DRAW_MODE_GUIDES == 0
                    or self.suppress_labels_in_all_cases
                ):
                    gc.DrawText(
                        a_text,
                        self.circular_grid_center_x + cos(c_angle) * (mid_y + dx),
                        self.circular_grid_center_y + sin(c_angle) * (mid_y + dx),
                        myangle,
                    )
                s_factor = 0
            else:
                s_factor = 1
            radials_start.append(
                (
                    self.circular_grid_center_x + s_factor * 0.5 * mid_y * cos(c_angle),
                    self.circular_grid_center_y + s_factor * 0.5 * mid_y * sin(c_angle),
                )
            )
            radials_end.append(
                (
                    self.circular_grid_center_x + 0.5 * y * cos(c_angle),
                    self.circular_grid_center_y + 0.5 * y * sin(c_angle),
                )
            )
            r_angle += tau / segments
            i += 1
        if radials_start:
            gc.StrokeLineSegments(radials_start, radials_end)
        gc.ResetClip()

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which draw the background and updates the grid when needed to recalculate the lines
        """
        if signal == "grid":
            self.primary_grid_lines = None
            self.invalidate_cache()  # Invalidate optimization cache on grid changes
        elif signal == "theme":
            self.set_colors()
            self.invalidate_cache()  # Invalidate cache on theme changes as colors may have changed
