"""
Optimized Fast Vectorizer
========================

High-performance image vectorization using optimized algorithms.
"""

import time
from typing import List, Optional, Tuple

import numpy as np

try:
    import numba
    from numba import njit, prange

    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False

    def njit(*args, **kwargs):
        """Fallback decorator when numba is not available."""

        def decorator(func):
            return func

        return decorator if args and callable(args[0]) else decorator

    def prange(x):
        return range(x)


# Turn policy constants
TURNPOLICY_BLACK = 0
TURNPOLICY_WHITE = 1
TURNPOLICY_LEFT = 2
TURNPOLICY_RIGHT = 3
TURNPOLICY_MINORITY = 4
TURNPOLICY_MAJORITY = 5
TURNPOLICY_RANDOM = 6


@njit
def threshold_image_fast(image: np.ndarray, threshold: float) -> np.ndarray:
    """Fast thresholding using numba."""
    h, w = image.shape
    result = np.zeros((h, w), dtype=np.bool_)

    for y in prange(h):
        for x in range(w):
            result[y, x] = image[y, x] < threshold

    return result


@njit
def flood_fill_component(
    bitmap: np.ndarray, start_x: int, start_y: int, visited: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Fast flood fill to find connected components."""
    h, w = bitmap.shape

    # Stack for flood fill
    stack = [(start_x, start_y)]
    points_x = []
    points_y = []

    while stack:
        x, y = stack.pop()

        if x < 0 or x >= w or y < 0 or y >= h:
            continue
        if visited[y, x] or not bitmap[y, x]:
            continue

        visited[y, x] = True
        points_x.append(x)
        points_y.append(y)

        # Add 4-connected neighbors
        stack.append((x + 1, y))
        stack.append((x - 1, y))
        stack.append((x, y + 1))
        stack.append((x, y - 1))

    return np.array(points_x), np.array(points_y)


@njit
def find_boundary_fast(
    bitmap: np.ndarray, component_x: np.ndarray, component_y: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Find boundary of a component using Moore neighborhood tracing."""
    if len(component_x) == 0:
        empty_x = np.zeros(0, dtype=np.int32)
        empty_y = np.zeros(0, dtype=np.int32)
        return empty_x, empty_y

    h, w = bitmap.shape

    # Find leftmost point as starting point
    min_idx = 0
    min_x = component_x[0]
    for i in range(1, len(component_x)):
        if component_x[i] < min_x:
            min_x = component_x[i]
            min_idx = i

    start_x, start_y = component_x[min_idx], component_y[min_idx]

    # Moore neighborhood directions (8-connected)
    dx = np.array([-1, -1, 0, 1, 1, 1, 0, -1])
    dy = np.array([0, -1, -1, -1, 0, 1, 1, 1])

    # Pre-allocate arrays for boundary points
    max_points = min(1000, len(component_x) * 2)
    boundary_x = np.zeros(max_points, dtype=np.int32)
    boundary_y = np.zeros(max_points, dtype=np.int32)

    curr_x, curr_y = start_x, start_y
    boundary_x[0] = curr_x
    boundary_y[0] = curr_y
    boundary_count = 1

    direction = 0  # Start direction

    for _ in range(max_points - 1):
        found_next = False

        # Look for next boundary point
        for i in range(8):
            next_dir = (direction + i) % 8
            next_x = curr_x + dx[next_dir]
            next_y = curr_y + dy[next_dir]

            if 0 <= next_x < w and 0 <= next_y < h and bitmap[next_y, next_x]:
                # Check if this is on the boundary
                is_boundary = False
                for j in range(8):
                    check_x = next_x + dx[j]
                    check_y = next_y + dy[j]
                    if (
                        check_x < 0
                        or check_x >= w
                        or check_y < 0
                        or check_y >= h
                        or not bitmap[check_y, check_x]
                    ):
                        is_boundary = True
                        break

                if is_boundary:
                    curr_x, curr_y = next_x, next_y
                    boundary_x[boundary_count] = curr_x
                    boundary_y[boundary_count] = curr_y
                    boundary_count += 1
                    direction = (next_dir + 6) % 8  # Update direction
                    found_next = True
                    break

        if not found_next or (
            curr_x == start_x and curr_y == start_y and boundary_count > 3
        ):
            break

    return boundary_x[:boundary_count], boundary_y[:boundary_count]


@njit
def douglas_peucker_fast(
    x: np.ndarray, y: np.ndarray, tolerance: float
) -> Tuple[np.ndarray, np.ndarray]:
    """Simplified Douglas-Peucker implementation for numba."""
    if len(x) <= 2:
        return x, y

    # Simple decimation approach for numba compatibility
    # Keep points that are far enough from the line between start and end
    start_x, start_y = x[0], y[0]
    end_x, end_y = x[-1], y[-1]

    line_len_sq = (end_x - start_x) ** 2 + (end_y - start_y) ** 2

    if line_len_sq < 1e-6:  # Degenerate line
        return x, y

    # Keep start point
    result_x = [start_x]
    result_y = [start_y]

    # Check each intermediate point
    for i in range(1, len(x) - 1):
        px, py = x[i], y[i]

        # Distance from point to line
        cross = abs(
            (end_x - start_x) * (start_y - py) - (start_x - px) * (end_y - start_y)
        )
        dist = cross / np.sqrt(line_len_sq)

        # Keep point if it's far enough from the line
        if dist > tolerance:
            result_x.append(px)
            result_y.append(py)

    # Always keep end point
    result_x.append(end_x)
    result_y.append(end_y)

    return np.array(result_x), np.array(result_y)


def find_components_scipy(bitmap: np.ndarray) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Use scipy for connected components if available."""
    try:
        from scipy import ndimage

        labeled, num_components = ndimage.label(bitmap)

        components = []
        for i in range(1, num_components + 1):
            y_coords, x_coords = np.where(labeled == i)
            if len(x_coords) >= 3:  # Minimum size filter
                components.append((x_coords, y_coords))

        return components
    except ImportError:
        return []


class FastVectorizer:
    """Optimized fast vectorizer with significant performance improvements."""

    def __init__(self):
        self.threshold = 0.5
        self.tolerance = 1.0
        self.min_area = 4.0
        self.turn_policy = TURNPOLICY_MINORITY
        self.use_numba = HAS_NUMBA
        self.use_scipy = True

    def set_parameters(
        self,
        threshold: float = None,
        tolerance: float = None,
        min_area: float = None,
        turn_policy: int = None,
    ):
        """Set vectorization parameters."""
        if threshold is not None:
            self.threshold = float(threshold)
        if tolerance is not None:
            self.tolerance = float(tolerance)
        if min_area is not None:
            self.min_area = float(min_area)
        if turn_policy is not None:
            self.turn_policy = int(turn_policy)

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image with optimizations."""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            # Fast grayscale conversion
            gray = np.dot(image[..., :3], [0.299, 0.587, 0.114])
        else:
            gray = image.copy()

        # Normalize to 0-1 range
        if gray.max() > 1.0:
            gray = gray / 255.0

        # Apply threshold
        if self.use_numba:
            return threshold_image_fast(gray.astype(np.float32), self.threshold)
        else:
            return gray < self.threshold

    def find_contours_optimized(
        self, bitmap: np.ndarray
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Find contours using optimized algorithms."""

        # Try scipy first for best performance
        if self.use_scipy:
            components = find_components_scipy(bitmap)
            if components:
                contours = []
                for comp_x, comp_y in components:
                    if len(comp_x) >= self.min_area:
                        # Find boundary
                        if self.use_numba:
                            boundary_x, boundary_y = find_boundary_fast(
                                bitmap, comp_x, comp_y
                            )
                        else:
                            # Fallback to simple boundary detection
                            boundary_x, boundary_y = self._find_boundary_simple(
                                bitmap, comp_x, comp_y
                            )

                        if len(boundary_x) >= 3:
                            contours.append((boundary_x, boundary_y))

                return contours

        # Fallback to optimized flood fill
        return self._find_contours_flood_fill(bitmap)

    def _find_boundary_simple(
        self, bitmap: np.ndarray, comp_x: np.ndarray, comp_y: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Simple boundary detection fallback."""
        h, w = bitmap.shape
        boundary_points = []

        # Create component mask
        component_mask = np.zeros_like(bitmap)
        for x, y in zip(comp_x, comp_y):
            if 0 <= y < h and 0 <= x < w:
                component_mask[y, x] = True

        # Find boundary points
        for x, y in zip(comp_x, comp_y):
            # Check if point is on boundary
            is_boundary = False
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if (
                        nx < 0
                        or nx >= w
                        or ny < 0
                        or ny >= h
                        or not component_mask[ny, nx]
                    ):
                        is_boundary = True
                        break
                if is_boundary:
                    break

            if is_boundary:
                boundary_points.append((x, y))

        if boundary_points:
            boundary_x, boundary_y = zip(*boundary_points)
            return np.array(boundary_x), np.array(boundary_y)
        else:
            return comp_x, comp_y

    def _find_contours_flood_fill(
        self, bitmap: np.ndarray
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Fallback flood fill implementation."""
        h, w = bitmap.shape
        visited = np.zeros_like(bitmap, dtype=bool)
        contours = []

        # Use larger step size for initial scan
        step = max(1, min(h, w) // 100)  # Adaptive step size

        for y in range(0, h, step):
            for x in range(0, w, step):
                if bitmap[y, x] and not visited[y, x]:
                    if self.use_numba:
                        comp_x, comp_y = flood_fill_component(bitmap, x, y, visited)
                    else:
                        comp_x, comp_y = self._flood_fill_simple(bitmap, x, y, visited)

                    if len(comp_x) >= self.min_area:
                        # Find boundary
                        boundary_x, boundary_y = self._find_boundary_simple(
                            bitmap, comp_x, comp_y
                        )
                        if len(boundary_x) >= 3:
                            contours.append((boundary_x, boundary_y))

        return contours

    def _flood_fill_simple(
        self, bitmap: np.ndarray, start_x: int, start_y: int, visited: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Simple flood fill fallback."""
        h, w = bitmap.shape
        stack = [(start_x, start_y)]
        points = []

        while stack and len(points) < 10000:  # Limit to prevent memory issues
            x, y = stack.pop()

            if x < 0 or x >= w or y < 0 or y >= h or visited[y, x] or not bitmap[y, x]:
                continue

            visited[y, x] = True
            points.append((x, y))

            # 4-connected neighbors
            stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])

        if points:
            points_x, points_y = zip(*points)
            return np.array(points_x), np.array(points_y)
        else:
            return np.array([]), np.array([])

    def simplify_contours(
        self, contours: List[Tuple[np.ndarray, np.ndarray]]
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Simplify contours with optimizations."""
        simplified = []

        for x_coords, y_coords in contours:
            if len(x_coords) < 3:
                continue

            # Pre-filter: remove duplicate consecutive points
            unique_x, unique_y = [x_coords[0]], [y_coords[0]]
            for i in range(1, len(x_coords)):
                if x_coords[i] != unique_x[-1] or y_coords[i] != unique_y[-1]:
                    unique_x.append(x_coords[i])
                    unique_y.append(y_coords[i])

            if len(unique_x) < 3:
                continue

            x_coords, y_coords = np.array(unique_x), np.array(unique_y)

            # Apply Douglas-Peucker
            if self.use_numba and len(x_coords) < 1000:  # Limit for numba efficiency
                simp_x, simp_y = douglas_peucker_fast(
                    x_coords, y_coords, self.tolerance
                )
            else:
                # Simple decimation for very large contours
                step = max(1, len(x_coords) // 100)
                simp_x = x_coords[::step]
                simp_y = y_coords[::step]
                if len(simp_x) > 2:
                    # Ensure closed contour
                    if simp_x[-1] != simp_x[0] or simp_y[-1] != simp_y[0]:
                        simp_x = np.append(simp_x, simp_x[0])
                        simp_y = np.append(simp_y, simp_y[0])

            if len(simp_x) >= 3:
                simplified.append((simp_x, simp_y))

        return simplified

    def contours_to_svg_path(
        self, contours: List[Tuple[np.ndarray, np.ndarray]]
    ) -> str:
        """Convert contours to SVG path string."""
        if not contours:
            return ""

        path_parts = []
        for x_coords, y_coords in contours:
            if len(x_coords) < 3:
                continue

            # Start path
            path_data = f"M {x_coords[0]:.2f},{y_coords[0]:.2f}"

            # Add line segments
            for x, y in zip(x_coords[1:], y_coords[1:]):
                path_data += f" L {x:.2f},{y:.2f}"

            # Close path
            path_data += " Z"
            path_parts.append(path_data)

        return " ".join(path_parts)

    def vectorize(
        self, image: np.ndarray, skip_svg: bool = False
    ) -> Tuple[str, List[Tuple[np.ndarray, np.ndarray]]]:
        """Main vectorization function with optimizations."""

        # Preprocess
        bitmap = self.preprocess_image(image)

        # Find contours
        contours = self.find_contours_optimized(bitmap)

        # Filter by area
        filtered_contours = []
        for x_coords, y_coords in contours:
            if len(x_coords) >= self.min_area:
                filtered_contours.append((x_coords, y_coords))

        # Simplify
        simplified_contours = self.simplify_contours(filtered_contours)

        # Convert to SVG
        if skip_svg:
            svg_path = ""
        else:
            svg_path = self.contours_to_svg_path(simplified_contours)

        return svg_path, simplified_contours
