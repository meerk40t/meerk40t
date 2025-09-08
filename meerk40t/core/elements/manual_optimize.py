from meerk40t.tools.geomstr import Geomstr
from meerk40t.core.units import Length
from meerk40t.core.elements.element_types import (
    op_burnable_nodes,
)
import numpy as np

# Import TYPE constants for geometric operations
from meerk40t.tools.geomstr import TYPE_QUAD, TYPE_CUBIC, TYPE_ARC

# Import for caching and additional utilities
from functools import lru_cache

# Import test case generation utilities
from .optimization_testcases import generate_random_test_case, DEFAULT_SHAPE_COUNT


# ==========
# OPTIMIZATION CONSTANTS
# ==========

# Path optimization thresholds
MATRIX_OPTIMIZATION_THRESHOLD = 25  # Paths - threshold for using full matrix optimization
MAX_GREEDY_ITERATIONS = 1000  # Maximum iterations for greedy algorithms
DEFAULT_TOLERANCE = 1e-6  # Default geometric tolerance for calculations
DEFAULT_CONTAINMENT_TOLERANCE = 1e-3  # Default tolerance for containment checks
DEFAULT_CONTAINMENT_RESOLUTION = 100  # Default resolution for containment polygon sampling

# Distance calculation constants
DISTANCE_CALCULATION_BATCH_SIZE = 100  # For large distance matrix calculations


# ==========
# SHAPELY UTILITIES
# ==========

def _get_shapely_operations():
    """
    Get Shapely operations if available, None otherwise.
    Centralizes all Shapely dependency handling in one place.
    
    Returns:
        dict or None: Dictionary with Shapely functions if available, None if not available
    """
    try:
        import importlib.util
        if importlib.util.find_spec("shapely") is None:
            return None
        
        # Import all needed Shapely components
        from shapely import contains
        from shapely.geometry import Polygon
        
        return {
            'contains': contains,
            'Polygon': Polygon,
            'available': True
        }
    except ImportError:
        return None


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    # ==========
    # ELEMENT/SHAPE COMMANDS
    # ==========
    @self.console_argument(
        "amount", type=int, help=_("Number of shapes to create"), default=DEFAULT_SHAPE_COUNT
    )
    @self.console_command(
        "testcase",
        help=_("Create test case for optimization"),
        input_type=None,
        output_type="elements",
    )
    def reorder_testcase(channel, _, amount=None, data=None, post=None, **kwargs):
        """Create a random test case for path optimization testing."""
        branch = self.elem_branch
        
        # Generate random test case using the dedicated module
        created_elements = generate_random_test_case(
            branch=branch,
            device_view=self.device.view,
            default_stroke=self.default_stroke,
            default_strokewidth=self.default_strokewidth,
            amount=amount
        )
        
        # Add classification post-processing
        post.append(self.post_classify(created_elements))

    @self.console_argument("rows", type=int, help=_("Number of rows"), default=3)
    @self.console_argument("cols", type=int, help=_("Number of columns"), default=3)  
    @self.console_argument("shape", type=str, help=_("Shape type"), default="rectangle")
    @self.console_command(
        "testcase_grid",
        help=_("Create grid pattern test case for optimization"),
        input_type=None,
        output_type="elements",
    )
    def reorder_testcase_grid(channel, _, rows=None, cols=None, shape=None, data=None, post=None, **kwargs):
        """Create a grid pattern test case for path optimization testing."""
        from .optimization_testcases import generate_grid_test_case
        
        branch = self.elem_branch
        
        created_elements = generate_grid_test_case(
            branch=branch,
            device_view=self.device.view,
            default_stroke=self.default_stroke,
            default_strokewidth=self.default_strokewidth,
            rows=rows or 3,
            cols=cols or 3,
            shape_type=shape or "rectangle"
        )
        
        post.append(self.post_classify(created_elements))

    @self.console_argument("count", type=int, help=_("Number of shapes in circle"), default=8)
    @self.console_argument("radius", type=float, help=_("Circle radius (percentage)"), default=30.0)
    @self.console_command(
        "testcase_circle",
        help=_("Create circular pattern test case for optimization"),
        input_type=None,
        output_type="elements",
    )
    def reorder_testcase_circle(channel, _, count=None, radius=None, data=None, post=None, **kwargs):
        """Create a circular pattern test case for path optimization testing."""
        from .optimization_testcases import generate_circular_pattern_test_case
        
        branch = self.elem_branch
        
        created_elements = generate_circular_pattern_test_case(
            branch=branch,
            device_view=self.device.view,
            default_stroke=self.default_stroke,
            default_strokewidth=self.default_strokewidth,
            count=count or 8,
            radius=radius or 30.0
        )
        
        post.append(self.post_classify(created_elements))

    @self.console_argument("levels", type=int, help=_("Number of nesting levels"), default=3)
    @self.console_command(
        "testcase_nested",
        help=_("Create nested shapes test case for containment testing"),
        input_type=None,
        output_type="elements",
    )
    def reorder_testcase_nested(channel, _, levels=None, data=None, post=None, **kwargs):
        """Create nested shapes test case for containment testing."""
        from .optimization_testcases import generate_nested_shapes_test_case
        
        branch = self.elem_branch
        
        created_elements = generate_nested_shapes_test_case(
            branch=branch,
            device_view=self.device.view,
            default_stroke=self.default_stroke,
            default_strokewidth=self.default_strokewidth,
            levels=levels or 3
        )
        
        post.append(self.post_classify(created_elements))
        return "elements", data

    @self.console_option(
        "debug",
        type=bool,
        action="store_true",
        help=_("Provide detailed debug output"),
    )
    @self.console_argument(
        "start_x", type=float, help=_("Starting X position"), default=0.0)
    @self.console_argument(
        "start_y", type=float, help=_("Starting Y position"), default=0.0)
    @self.console_command(
        "reorder",
        help=_("reorder elements for optimal cutting within an operation"),
        input_type=("ops", None),
        output_type="ops",
    )
    def element_reorder(channel, _, start_x=None, start_y=None, debug=None, data=None, post=None, **kwargs):
        start_position = complex(start_x or 0.0, start_y or 0.0)
        oplist = data if data is not None else list(self.ops(selected=True))
        opout = []
        debug_channel = channel if debug else None
        # Collect optimization results for summary
        total_improvement = 0.0
        optimized_operations = []
        operation_results = []
        if not oplist:
            channel(_("No operations to optimize"))
            return "ops", []
        
        for op in oplist:
            if op.type in op_burnable_nodes:
                optimization_result = optimize_node_travel_under(self, op, channel, debug_channel, start_position=start_position)
                opout.append(op)
                
                # Collect results for summary
                if optimization_result['optimized']:
                    optimized_operations.append(display_label(op))
                    total_improvement += optimization_result['improvement']
                
                operation_results.append((display_label(op), optimization_result))
                
                # New start_position is last position of the last node
                if len(op.children) > 0:
                    last_child = op.children[-1]
                    if last_child.type == "reference" and last_child.node is not None:
                        last_node = last_child.node
                        if hasattr(last_node, "as_geometry") and callable(getattr(last_node, "as_geometry")):
                            try:
                                geomstr = last_node.as_geometry()
                                if geomstr and geomstr.index > 0:
                                    last_segment = geomstr.segments[geomstr.index - 1]
                                    start_point, control1, info, control2, end_point = last_segment
                                    start_position = end_point
                            except Exception as e:
                                channel(f"Error extracting geometry from last node: {e}")
        
        # Display optimization summary
        if operation_results:
            channel(f"\n{'='*60}")
            channel("PATH OPTIMIZATION SUMMARY")
            channel(f"{'='*60}")
            
            total_distance_saved = 0.0
            optimized_count = 0
            
            for op_label, result in operation_results:
                if result['optimized']:
                    channel(f"✓ {op_label}:")
                    channel(f"  Paths optimized: {result['path_count']}")
                    channel(f"  Distance saved: {Length(result['improvement'], digits=0).length_mm}")
                    total_distance_saved += result['improvement']
                    optimized_count += 1
                else:
                    channel(f"○ {op_label}: No optimization needed ({result['path_count']} paths)")
            
            channel(f"{'='*60}")
            if optimized_count > 0:
                channel("Summary:")
                channel(f"  Operations optimized: {optimized_count}")
                channel(f"  Total distance saved: {Length(total_distance_saved, digits=0).length_mm}")
                channel(f"  Optimized operations: {', '.join([op for op, result in operation_results if result['optimized']])}")
            else:
                channel("No operations required optimization")
            channel(f"{'='*60}\n")
        
        self.signal("rebuild_tree")
        return "ops", opout

    def optimize_node_travel_under(self, op, channel, debug_channel, leading="", start_position=0j):
        node_list = []
        child_list = []
        
        # Track optimization results from child operations
        total_optimization_results = {
            'optimized': False,
            'original_distance': 0,
            'optimized_distance': 0,
            'improvement': 0,
            'improvement_percent': 0,
            'path_count': 0
        }
        
        for child in op.children:
            if debug_channel:
                debug_channel(f"{leading}{display_label(child)}")
            if child.type.startswith("effect"):
                # We reorder the children of the effect, not the effect itself
                child_result = optimize_node_travel_under(self, child, channel, debug_channel, leading=f"{leading}  ", start_position=start_position)
                # Accumulate results from child operations
                if child_result['optimized']:
                    total_optimization_results['optimized'] = True
                    total_optimization_results['improvement'] += child_result['improvement']
                    total_optimization_results['path_count'] += child_result['path_count']
            elif child.type == "reference":
                if debug_channel:
                    debug_channel(
                        f"{leading}Reference to {display_label(child.node) if child.node else 'None!!!'}"
                    )
                node_list.append(child.node)
                child_list.append(child)
            else:
                channel(
                    f"{leading}Don't know how to handle {child.type} in reorder for {display_label(op)}"
                )
        if debug_channel:
            debug_channel(f"{leading}Nodes:")
            debug_channel(
                f"{leading}  "
                + " ".join([str(display_label(n)) for n in node_list if n is not None])
            )
            debug_channel(f"{leading}Children:")
            debug_channel(
                f"{leading}  "
                + ", ".join([str(display_label(n)) for n in child_list if n is not None])
            )
        if len(node_list) > 1:
            # We need to make sure we have ids for all nodes (and they should be unique)
            self.validate_ids(node_list)
            ordered_nodes, optimization_results = optimize_path_order(node_list, channel, debug_channel, start_position)
            if ordered_nodes != node_list:
                # Clear old children
                for child in child_list:
                    child.remove_node()
                # Rebuild children in new order
                for node in ordered_nodes:
                    op.add_reference(node)
            
            # Combine with any results from child operations
            if optimization_results['optimized']:
                total_optimization_results['optimized'] = True
                total_optimization_results['improvement'] += optimization_results['improvement']
                total_optimization_results['path_count'] += optimization_results['path_count']
            
            return total_optimization_results
        else:
            channel(f"No need to reorder {display_label(op)}")
            return total_optimization_results

    def optimize_path_order(node_list, channel=None, debug_channel=None, start_position=0j):
        if len(node_list) < 2:
            return node_list

        if debug_channel:
            debug_channel(f"Starting path optimization for {len(node_list)} nodes from position {start_position}")

        # Separate nodes with and without as_geometry attribute
        geomstr_nodes = []
        non_geomstr_nodes = []

        for idx, node in enumerate(node_list):
            if hasattr(node, "as_geometry") and callable(getattr(node, "as_geometry")):
                try:
                    geomstr = node.as_geometry()
                    # create_dump_of(f"geom{idx+1}", geomstr)
                    if geomstr and geomstr.index > 0:
                        geomstr_nodes.append((node, geomstr))
                        if debug_channel:
                            debug_channel(
                                f"  Node {display_label(node)}: {geomstr.index} segments"
                            )
                    else:
                        non_geomstr_nodes.append(node)
                        if debug_channel:
                            debug_channel(
                                f"  Node {display_label(node)}: Empty geometry"
                            )
                except Exception as e:
                    non_geomstr_nodes.append(node)
                    if channel:
                        channel(
                            f"  Node {display_label(node)}: Error extracting geometry - {e}"
                        )
            else:
                non_geomstr_nodes.append(node)
                if debug_channel:
                    debug_channel(
                        f"  Node {display_label(node)}: No as_geometry method"
                    )

        if debug_channel:
            debug_channel(
                f"Found {len(geomstr_nodes)} geomstr nodes and {len(non_geomstr_nodes)} non-geomstr nodes"
            )

        if len(geomstr_nodes) < 2:
            # Not enough geomstr nodes to optimize, return original order
            if debug_channel:
                debug_channel(
                    "Not enough geomstr nodes to optimize, returning original order"
                )
            return node_list

        # Extract path information for each geomstr node
        path_info = []
        for node, geomstr in geomstr_nodes:
            if debug_channel:
                debug_channel(f"Extracting path info for node {display_label(node)}")
            may_extend = hasattr(node, "set_geometry")
            may_reverse = True  # Assume we can reverse unless proven otherwise
            if node.type in ("elem image", "elem text", "elem raster"):                
                may_reverse = False
            info = _extract_path_info(geomstr, may_extend, may_reverse=may_reverse, channel=debug_channel)
            path_info.append((node, geomstr, info))

        # Calculate original travel distance
        original_distance = _calculate_total_travel_distance(path_info, debug_channel, start_position)

        # Optimize the order using greedy nearest neighbor with improvements
        ordered_path_info = _optimize_path_order_greedy(path_info, debug_channel, start_position)

        # Calculate optimized travel distance
        optimized_distance = _calculate_total_travel_distance(
            ordered_path_info, debug_channel, start_position
        )

        # Report results to channel if available
        if channel:
            improvement = original_distance - optimized_distance
            improvement_percent = (
                (improvement / original_distance * 100) if original_distance > 0 else 0
            )
            channel(f"Path optimization for {len(geomstr_nodes)} paths:")
            channel(
                f"  Original travel distance: {Length(original_distance, digits=0).length_mm}"
            )
            channel(
                f"  Optimized travel distance: {Length(optimized_distance, digits=0).length_mm}"
            )
            channel(
                f"  Distance saved: {Length(improvement, digits=0).length_mm}  ({improvement_percent:.1f}%)"
            )

        # Reconstruct the ordered node list
        ordered_nodes = [node for node, _, _ in ordered_path_info] + non_geomstr_nodes

        # Return both the ordered nodes and optimization results
        optimization_results = {
            'optimized': ordered_path_info != path_info,
            'original_distance': original_distance,
            'optimized_distance': optimized_distance,
            'improvement': original_distance - optimized_distance,
            'improvement_percent': (original_distance - optimized_distance) / original_distance * 100 if original_distance > 0 else 0,
            'path_count': len(geomstr_nodes)
        }

        return ordered_nodes, optimization_results


def display_label(node):
    return f"{node.type}.{node.id if node.id is not None else '-'}.{node.label if node.label is not None else '-'}"


def _extract_path_info(geomstr, may_extend, may_reverse=True, channel=None):
    """
    Extract start and end points from a geomstr, considering different orientations.

    Returns:
        dict with 'start_points', 'end_points', and 'is_closed' keys
    """
    if geomstr.index == 0:
        if channel:
            channel("  Empty geomstr, no path information")
        return {
            "start_points": [],
            "end_points": [],
            "is_closed": False,
            "segments": [],
        }

    segments = geomstr.segments[: geomstr.index]
    if channel:
        channel(f"  Extracting path info from {len(segments)} segments")

    # Extract start and end points for forward direction
    start_point = segments[0][0]  # First segment start
    end_point = segments[-1][4]  # Last segment end
    # For closed paths, we can start at any segment
    is_closed = may_extend and (
        geomstr.is_closed() if hasattr(geomstr, "is_closed") else False
    )
    if channel:
        channel(f"  Path is {'closed' if is_closed else 'open'}")

    result = {
        "start_points": [start_point],
        "end_points": [end_point],
        "is_closed": is_closed,
        "segments": segments,
    }

    # Add reversed orientation
    if len(segments) > 1 and may_reverse:
        reversed_start = segments[-1][4]  # Last segment end becomes start
        reversed_end = segments[0][0]  # First segment start becomes end
        result["start_points"].append(reversed_start)
        result["end_points"].append(reversed_end)

    # If closed, add alternative start/end points for different starting segments
    if is_closed and len(segments) > 1:
        # Use improved candidate selection for closed paths
        max_alternatives = min(len(segments), 8)  # Limit to avoid excessive computation
        candidate_indices = _select_closed_path_candidates(
            segments, max_alternatives, channel
        )
        result["candidate_indices"] = candidate_indices  # Store for later use
        for segment_idx in candidate_indices:
            alt_start = segments[segment_idx][0]
            # For closed paths, the end point when starting at segment i would be the end of segment i-1
            alt_end = (
                segments[segment_idx - 1][4] if segment_idx > 0 else segments[-1][4]
            )
            result["start_points"].append(alt_start)
            result["end_points"].append(alt_end)

    return result


def _select_closed_path_candidates(segments, max_candidates, channel=None):
    """
    Select optimal candidate starting points for closed paths.

    Uses multiple strategies:
    1. Spatial distribution around the geometry
    2. Points of high curvature/direction changes
    3. Regular intervals as fallback

    Args:
        segments: List of geomstr segments
        max_candidates: Maximum number of candidates to return
        channel: Channel for debug output

    Returns:
        List of segment indices to use as starting points
    """
    if len(segments) <= max_candidates:
        # If we have fewer segments than max candidates, use all of them
        candidates = list(range(1, len(segments)))
        if channel:
            channel(f"  Using all {len(candidates)} segments as candidates")
        return candidates

    candidates = []
    n_segments = len(segments)

    if channel:
        channel(f"  Selecting {max_candidates} candidates from {n_segments} segments")

    # Strategy 1: Spatial distribution - divide the path into roughly equal arcs
    if n_segments >= 4:
        # Calculate approximate arc lengths to distribute candidates evenly
        segment_lengths = []
        total_length = 0

        for segment in segments:
            # Approximate segment length using start and end points
            start_pt, control1, info, control2, end_pt = segment
            length = abs(end_pt - start_pt)
            segment_lengths.append(length)
            total_length += length

        if total_length > 0:
            # Distribute candidates evenly by arc length
            target_length = total_length / max_candidates
            current_length = 0
            candidates.append(0)  # Always include the original start

            for i in range(1, n_segments):
                current_length += segment_lengths[i - 1]
                if (
                    current_length >= target_length * len(candidates)
                    and len(candidates) < max_candidates
                ):
                    candidates.append(i)
                    if len(candidates) >= max_candidates:
                        break

    # Strategy 2: Curvature-based selection (fallback to regular intervals)
    if len(candidates) < max_candidates:
        # Fill remaining slots with regular intervals
        remaining_slots = max_candidates - len(candidates)
        if remaining_slots > 0:
            step = max(1, n_segments // (remaining_slots + 1))
            for i in range(step, n_segments, step):
                if i not in candidates and len(candidates) < max_candidates:
                    candidates.append(i)

    # Ensure we don't include index 0 (original start) and remove duplicates
    candidates = [idx for idx in candidates if idx != 0]
    candidates = sorted(set(candidates))  # Remove duplicates and sort

    # Limit to max_candidates
    candidates = candidates[:max_candidates]
    if channel:
        channel(f"  Selected {len(candidates)} candidate starting points: {candidates}")
    return candidates


def _optimize_path_order_greedy(path_info, channel=None, start_position=0j):
    """
    Optimize path order using greedy nearest neighbor algorithm with lazy distance calculation.

    Args:
        path_info: List of (node, geomstr, info) tuples
        channel: Channel for debug output
        start_position: Starting position (complex number) to minimize total travel from

    Returns:
        Ordered list of (node, geomstr, info) tuples
    """
    if len(path_info) < 2:
        return path_info

    if channel:
        channel(f"Starting greedy optimization for {len(path_info)} paths")

    # Use lazy distance calculation instead of pre-calculating all distances
    n_paths = len(path_info)

    # Calculate maximum number of orientations (start/end point combinations)
    max_end_points = (
        max(len(info["end_points"]) for _, _, info in path_info) if path_info else 1
    )
    max_start_points = (
        max(len(info["start_points"]) for _, _, info in path_info) if path_info else 1
    )

    if channel:
        channel(
            f"  Maximum orientations: {max_end_points} end points, {max_start_points} start points"
        )

    # Remove cache - it's not effective for this algorithm and adds memory overhead
    # distance_cache = {}  # Key: (from_idx, to_idx, from_ori, to_ori) -> distance
    # cache_access_order = []  # For LRU eviction: most recently used at end
    # cache_hits = 0
    # cache_misses = 0
    # cache_evictions = 0

    # def get_cached_distance(cache_key):
    #     """Get distance from cache with LRU update"""
    #     nonlocal cache_hits, cache_access_order
    #     if cache_key in distance_cache:
    #         # Move to end (most recently used)
    #         if cache_key in cache_access_order:
    #             cache_access_order.remove(cache_key)
    #         cache_access_order.append(cache_key)
    #         cache_hits += 1
    #         return distance_cache[cache_key]
    #     return None

    # def set_cached_distance(cache_key, distance):
    #     """Set distance in cache with eviction if needed"""
    #     nonlocal cache_evictions, cache_access_order, cache_misses
    #     if len(distance_cache) >= max_cache_size:
    #         # Evict least recently used
    #         if cache_access_order:
    #             evicted_key = cache_access_order.pop(0)
    #         if evicted_key in distance_cache:
    #             del distance_cache[evicted_key]
    #             cache_evictions += 1

    #     distance_cache[cache_key] = distance
    #     cache_access_order.append(cache_key)
    #     cache_misses += 1

    if channel:
        channel(
            "  Using direct distance calculation (no cache needed for greedy algorithm)..."
        )

    # Find the optimal starting path to minimize total travel from start_position
    best_start_idx = 0
    best_start_distance = float("inf")
    best_start_ori = 0

    if channel:
        channel(f"  Finding optimal starting path from position {start_position}")

    # Find the optimal starting path using vectorized operations
    best_start_idx = 0
    best_start_distance = float("inf")
    best_start_ori = 0

    if channel:
        channel(f"  Finding optimal starting path from position {start_position}")

    # Vectorized approach: calculate all distances at once
    for start_idx in range(n_paths):
        start_info = path_info[start_idx][2]
        start_points = np.array(start_info["start_points"], dtype=complex)

        # Calculate distances from start_position to all start points for this path
        distances_from_start = np.abs(start_points - start_position)

        # Find the minimum distance for this path
        min_distance = np.min(distances_from_start)
        min_ori = np.argmin(distances_from_start)

        if min_distance < best_start_distance:
            best_start_distance = min_distance
            best_start_idx = start_idx
            best_start_ori = min_ori

    if channel:
        channel(
            f"  Optimal starting path: {best_start_idx} ({display_label(path_info[best_start_idx][0])}) at distance {best_start_distance:.6f}"
        )

    # Start with the optimal path
    ordered_indices = [best_start_idx]
    used = {best_start_idx}
    orientation_choices = [(best_start_idx, best_start_ori)]  # (path_idx, orientation_idx) for each ordered path

    if channel:
        channel(
            f"  Starting with path {best_start_idx}: {display_label(path_info[best_start_idx][0])}"
        )

    # Greedily add the closest unused path with early termination based on complete iterations
    total_iterations = 0

    while len(ordered_indices) < n_paths:
        # Perform a complete iteration through all remaining paths
        iteration_shuffles = 0
        best_distance = float("inf")
        best_idx = -1
        best_start_ori = 0
        path_iterations = 0
        path_candidates_evaluated = 0

        current_path_idx = ordered_indices[-1]
        current_end_points = path_info[current_path_idx][2]["end_points"]

        if channel:
            channel(
                f"  Iteration {total_iterations + 1}: Finding next path after {display_label(path_info[current_path_idx][0])}"
            )

        for candidate_idx in range(n_paths):
            if candidate_idx in used:
                continue

            candidate_start_points = path_info[candidate_idx][2]["start_points"]

            # Find the best orientation combination using vectorized distance calculation
            current_ends = np.array(current_end_points, dtype=complex)
            candidate_starts = np.array(candidate_start_points, dtype=complex)

            # Vectorized distance calculation: all combinations at once
            distances = np.abs(current_ends[:, np.newaxis] - candidate_starts)

            # Find minimum distance and corresponding indices
            min_idx = np.unravel_index(np.argmin(distances), distances.shape)
            distance = distances[min_idx]

            if distance < best_distance:
                best_distance = distance
                best_idx = candidate_idx
                best_start_ori = min_idx[1]  # start_ori is the second index

            path_iterations += len(current_end_points) * len(candidate_start_points)
            iteration_shuffles += len(current_end_points) * len(candidate_start_points)

            path_candidates_evaluated += 1

        if best_idx == -1:
            # No more candidates, add remaining paths in original order
            if channel:
                channel(
                    "  No more candidates found, adding remaining paths in original order"
                )
            for i in range(n_paths):
                if i not in used:
                    ordered_indices.append(i)
                    used.add(i)
                    orientation_choices.append((i, 0))  # Default orientation
            break

        # Add the best path found in this iteration
        ordered_indices.append(best_idx)
        used.add(best_idx)
        orientation_choices.append((best_idx, best_start_ori))
        total_iterations += 1
        if channel:
            channel(
                f"  Added path {best_idx}: {display_label(path_info[best_idx][0])} (distance: {Length(best_distance, digits=0).length_mm}, orientation: {best_start_ori})"
            )

    # Report algorithm statistics
    if channel:
        channel(f"  Total optimization iterations: {total_iterations}")
        channel(
            f"  Optimization complete. Final order: {[display_label(path_info[i][0]) for i in ordered_indices]}"
        )

    # Reconstruct ordered path_info with optimal orientations
    ordered_path_info = []
    for path_idx, orientation_idx in orientation_choices:
        node, original_geomstr, info = path_info[path_idx]

        # Apply orientation transformation if needed
        if orientation_idx == 0 or orientation_idx >= len(info["start_points"]):
            # Original orientation or invalid orientation index
            final_geomstr = original_geomstr
            if channel:
                channel(
                    f"  Node {display_label(node)}: Using original orientation (idx={orientation_idx}, available={len(info['start_points'])})"
                )
        elif orientation_idx == 1 and len(info["start_points"]) > 1:
            # Reversed orientation - use reversed start point
            final_geomstr = _reverse_geomstr(original_geomstr, channel)
            # Reassign the changed geometry to the node
            if hasattr(node, "set_geometry"):
                oldtype = node.type
                newnode = node.set_geometry(final_geomstr)
                path_info[path_idx] = (newnode, final_geomstr, info)  # Update reference
                if channel:
                    channel(
                        f"  Node {display_label(newnode)}: Applied reversed geometry {'' if oldtype == newnode.type else ' (type changed)'}"
                    )
        elif (
            info["is_closed"]
            and orientation_idx >= 2
            and len(info["start_points"]) > orientation_idx
        ):
            # Closed path with different starting segment
            candidate_idx = (
                orientation_idx - 2
            )  # Adjust for the first two being forward/reverse
            if "candidate_indices" in info and candidate_idx < len(
                info["candidate_indices"]
            ):
                start_segment_idx = info["candidate_indices"][candidate_idx]
                final_geomstr = _reshuffle_closed_geomstr(
                    original_geomstr, start_segment_idx, channel
                )
                # Reassign the changed geometry to the node
                if hasattr(node, "set_geometry"):
                    oldtype = node.type
                    newnode = node.set_geometry(final_geomstr)
                    if channel:
                        channel(
                            f"  Node {display_label(node)}: Applied reshuffled geometry, starting at segment {start_segment_idx}{'' if oldtype == newnode.type else ' (type changed)'}"
                        )
            else:
                final_geomstr = original_geomstr
                if channel:
                    channel(
                        f"  Node {display_label(node)}: Fallback to original (invalid candidate index)"
                    )
        else:
            # Fallback to original
            final_geomstr = original_geomstr
            if channel:
                channel(
                    f"  Node {display_label(node)}: Fallback to original orientation (orientation_idx={orientation_idx}, available={len(info['start_points'])})"
                )

        ordered_path_info.append((node, final_geomstr, info))

    return ordered_path_info


def _reverse_geomstr(geomstr, channel=None):
    """
    Reverse the order of segments in a geomstr.

    For each segment (start, c0, info, c1, end), we need to:
    - Swap start and end
    - Reverse control points c0 and c1
    - Keep info unchanged
    """
    if geomstr.index == 0:
        if channel:
            channel("  Reversing empty geomstr")
        return geomstr

    if channel:
        channel(f"  Reversing geomstr with {geomstr.index} segments")

    reversed_geomstr = Geomstr()
    segments = geomstr.segments[: geomstr.index]

    for segment in reversed(segments):
        start, c0, info, c1, end = segment
        # Reverse the segment: end becomes start, start becomes end
        # For Bezier curves, we need to reverse the control points
        reversed_segment = (end, c1, info, c0, start)
        reversed_geomstr.append_segment(*reversed_segment)

    if channel:
        channel(f"  Reversed geomstr created with {reversed_geomstr.index} segments")

    return reversed_geomstr


def _optimize_path_order_greedy_optimized(
    path_info, channel=None, max_iterations=None, start_position=0j
):
    """
    Optimized greedy path optimization algorithm with lazy evaluation.

    Args:
        path_info: List of (node, geom, info) tuples
        channel: Channel for debug output
        max_iterations: Maximum number of optimization iterations (None = no limit)
        start_position: Starting position (complex number) to minimize total travel from

    Returns:
        Optimized path order as list of (node, geom, info) tuples
    """
    if not path_info:
        return []

    if len(path_info) == 1:
        return path_info

    # Use global threshold for matrix optimization
    if len(path_info) <= MATRIX_OPTIMIZATION_THRESHOLD:
        # Use simplified approach for small numbers of paths
        return _optimize_path_order_greedy_simple(path_info, channel, max_iterations, start_position)

    # For larger numbers of paths, use the full matrix optimization
    if channel:
        channel(f"  Using full matrix optimization for {len(path_info)} paths (> {MATRIX_OPTIMIZATION_THRESHOLD})")

    if channel:
        channel(
            f"Starting optimized greedy path optimization with {len(path_info)} paths"
        )
        if max_iterations:
            channel(f"Max iterations: {max_iterations}")

    # Find the optimal starting path to minimize total travel from start_position
    best_start_idx = 0
    best_start_distance = float("inf")

    if channel:
        channel(f"  Finding optimal starting path from position {start_position}")

    # Vectorized approach: calculate all distances at once
    for start_idx in range(len(path_info)):
        start_info = path_info[start_idx][2]
        start_points = np.array(start_info["start_points"], dtype=complex)

        # Calculate distances from start_position to all start points for this path
        distances_from_start = np.abs(start_points - start_position)

        # Find the minimum distance for this path
        min_distance = np.min(distances_from_start)

        if min_distance < best_start_distance:
            best_start_distance = min_distance
            best_start_idx = start_idx

    if channel:
        channel(
            f"  Optimal starting path: {best_start_idx} at distance {best_start_distance:.6f}"
        )

    # Initialize with the optimal starting path
    optimized_paths = [path_info[best_start_idx]]
    remaining_paths = [p for i, p in enumerate(path_info) if i != best_start_idx]

    # Distance cache for frequently accessed distances
    distance_cache = {}
    cache_stats = {"hits": 0, "misses": 0}

    total_iterations = 0

    while remaining_paths and (
        max_iterations is None or total_iterations < max_iterations
    ):
        total_iterations += 1

        best_insertion_idx = None
        best_path_idx = None
        best_distance = float("inf")
        best_improvement = 0

        current_distance = _calculate_total_travel_distance_optimized(
            optimized_paths, distance_cache, cache_stats
        )

        # Try inserting each remaining path at each possible position
        for path_idx, (node, geom, info) in enumerate(remaining_paths):
            for insert_idx in range(len(optimized_paths) + 1):
                # Create test path order
                test_paths = (
                    optimized_paths[:insert_idx]
                    + [(node, geom, info)]
                    + optimized_paths[insert_idx:]
                )

                # Calculate new total distance with caching
                new_distance = _calculate_total_travel_distance_optimized(
                    test_paths, distance_cache, cache_stats
                )

                if new_distance < best_distance:
                    best_distance = new_distance
                    best_insertion_idx = insert_idx
                    best_path_idx = path_idx
                    best_improvement = current_distance - new_distance

        # If no improvement found, we're done
        if best_path_idx is None:
            if channel:
                channel("No further improvements possible")
            break

        # Insert the best path
        node, geom, info = remaining_paths.pop(best_path_idx)
        optimized_paths.insert(best_insertion_idx, (node, geom, info))

        if channel:
            channel(
                f"Iteration {total_iterations}: Inserted '{display_label(node)}' at position {best_insertion_idx}"
            )
            channel(
                f"  Improvement: {best_improvement:.6f}, New distance: {best_distance:.6f}"
            )

    # Update cache statistics
    if channel and (cache_stats["hits"] + cache_stats["misses"]) > 0:
        hit_rate = (
            cache_stats["hits"] / (cache_stats["hits"] + cache_stats["misses"]) * 100
        )
        channel(
            f"Cache statistics: {cache_stats['hits']} hits, {cache_stats['misses']} misses ({hit_rate:.1f}% hit rate)"
        )

    if channel:
        channel(f"Optimization completed in {total_iterations} iterations")
        channel(
            f"Final path order: {[display_label(node) for node, _, _ in optimized_paths]}"
        )

    return optimized_paths


def _calculate_total_travel_distance(path_info, channel=None, start_position=0j):
    """
    Calculate total travel distance for a sequence of paths, including distance from start position.

    Args:
        path_info: List of (node, geomstr, info) tuples
        channel: Channel for debug output (optional)
        start_position: Starting position to calculate distance from

    Returns:
        Total travel distance
    """
    if len(path_info) == 0:
        return 0.0

    total_distance = 0.0

    # Calculate distance from start position to first path
    if len(path_info) > 0:
        first_node, first_geom, first_info = path_info[0]
        first_start_points = first_info["start_points"]

        if first_start_points:
            # Find the minimum distance from start_position to any start point of the first path
            min_distance_to_first = min(abs(start_point - start_position) for start_point in first_start_points)
            total_distance += min_distance_to_first

            if channel:
                channel(f"  Distance from start position {start_position} to first path: {min_distance_to_first:.6f}")

    # Calculate distances between consecutive paths
    for i in range(len(path_info) - 1):
        current_node, current_geom, current_info = path_info[i]
        next_node, next_geom, next_info = path_info[i + 1]

        # Calculate distance between end of current path and start of next path
        distance = _calculate_path_to_path_distance_optimized(current_info, next_info)
        total_distance += distance

        if channel:
            channel(f"  Distance from path {i} to path {i+1}: {distance:.6f}")

    if channel:
        channel(f"  Total travel distance: {total_distance:.6f}")

    return total_distance


def _calculate_total_travel_distance_optimized(path_info, distance_cache):
    """
    Calculate total travel distance with distance caching for optimization.

    Args:
        path_info: List of (node, geom, info) tuples
        distance_cache: Dictionary for caching distances

    Returns:
        Total travel distance
    """
    if len(path_info) <= 1:
        return 0.0

    total_distance = 0.0

    for i in range(len(path_info) - 1):
        current_node, current_geom, current_info = path_info[i]
        next_node, next_geom, next_info = path_info[i + 1]

        # Create cache key using stable node identifiers
        current_id = getattr(
            current_node,
            "label",
            f"{current_node.type}.{getattr(current_node, 'id', 'unknown')}",
        )
        next_id = getattr(
            next_node,
            "label",
            f"{next_node.type}.{getattr(next_node, 'id', 'unknown')}",
        )
        cache_key = (current_id, next_id)

        # Check cache first
        if cache_key in distance_cache:
            distance = distance_cache[cache_key]
        else:
            # Calculate distance between end of current path and start of next path
            distance = _calculate_path_to_path_distance_optimized(
                current_info, next_info
            )
            distance_cache[cache_key] = distance

        total_distance += distance

    return total_distance


def _calculate_path_to_path_distance_optimized(current_info, next_info):
    """
    Calculate the travel distance from the end of one path to the start of another.
    Optimized version with numpy vectorization for significant performance gains.

    Args:
        current_info: Path info for current path
        next_info: Path info for next path

    Returns:
        Minimum distance between path end and next path start
    """
    # Get possible end points from current path
    current_end_points = current_info["end_points"]
    next_start_points = next_info["start_points"]

    # If either path has no points, return 0
    if not current_end_points or not next_start_points:
        return 0.0

    # Convert to numpy arrays for vectorized operations
    current_ends = np.array(current_end_points, dtype=complex)
    next_starts = np.array(next_start_points, dtype=complex)

    # Vectorized distance calculation: compute all pairwise distances at once
    # This replaces the nested loops with a single vectorized operation
    distances = np.abs(current_ends[:, np.newaxis] - next_starts)

    # Return minimum distance
    return np.min(distances)


def _reshuffle_closed_geomstr(geomstr, start_segment_idx, channel=None):
    """
    Reshuffle a closed geomstr to start at a different segment.

    Args:
        geomstr: The original geomstr
        start_segment_idx: Index of the segment to start with
        channel: Channel for debug output

    Returns:
        Reshuffled geomstr
    """
    if geomstr.index == 0 or start_segment_idx == 0:
        if channel:
            channel("  No reshuffling needed (empty geomstr or start_segment_idx=0)")
        return geomstr

    if channel:
        channel(f"  Reshuffling geomstr to start at segment {start_segment_idx}")

    segments = geomstr.segments[: geomstr.index]
    reshuffled_geomstr = Geomstr()

    # Add segments from start_segment_idx to end
    for i in range(start_segment_idx, len(segments)):
        reshuffled_geomstr.append_segment(*segments[i])

    # Add segments from beginning to start_segment_idx
    for i in range(start_segment_idx):
        reshuffled_geomstr.append_segment(*segments[i])

    if channel:
        channel(
            f"  Reshuffled geomstr created with {reshuffled_geomstr.index} segments"
        )

    return reshuffled_geomstr


def _optimize_path_order_greedy_simple(path_info, channel=None, max_iterations=None, start_position=0j):
    """
    Simple greedy path optimization for small numbers of paths.
    Uses on-demand distance calculation to avoid matrix overhead.

    Args:
        path_info: List of (node, geom, info) tuples
        channel: Channel for debug output
        max_iterations: Maximum number of optimization iterations (None = no limit)
        start_position: Starting position (complex number) to minimize total travel from

    Returns:
        Optimized path order as list of (node, geom, info) tuples
    """
    if len(path_info) < 2:
        return path_info

    if channel:
        channel(f"Starting simple greedy optimization for {len(path_info)} paths")

    n_paths = len(path_info)

    # Find the optimal starting path to minimize total travel from start_position
    best_start_idx = 0
    best_start_distance = float("inf")
    best_start_ori = 0

    if channel:
        channel(f"  Finding optimal starting path from position {start_position}")

    # Simple loop approach for small numbers of paths
    for start_idx in range(n_paths):
        start_info = path_info[start_idx][2]
        start_points = start_info["start_points"]

        # Calculate distances from start_position to all start points for this path
        distances_from_start = [abs(point - start_position) for point in start_points]

        # Find the minimum distance for this path
        min_distance = min(distances_from_start)
        min_ori = distances_from_start.index(min_distance)

        if min_distance < best_start_distance:
            best_start_distance = min_distance
            best_start_idx = start_idx
            best_start_ori = min_ori

    if channel:
        channel(
            f"  Optimal starting path: {best_start_idx} at distance {best_start_distance:.6f}"
        )

    # Start with the optimal path
    ordered_indices = [best_start_idx]
    used = {best_start_idx}
    orientation_choices = [(best_start_idx, best_start_ori)]

    if channel:
        channel(
            f"  Starting with path {best_start_idx}: {display_label(path_info[best_start_idx][0])}"
        )

    # Greedily add the closest unused path with on-demand distance calculation
    total_iterations = 0

    while len(ordered_indices) < n_paths and (
        max_iterations is None or total_iterations < max_iterations
    ):
        total_iterations += 1

        best_distance = float("inf")
        best_idx = -1
        best_start_ori = 0

        current_path_idx = ordered_indices[-1]
        current_end_points = path_info[current_path_idx][2]["end_points"]

        if channel:
            channel(
                f"  Iteration {total_iterations}: Finding next path after {display_label(path_info[current_path_idx][0])}"
            )

        for candidate_idx in range(n_paths):
            if candidate_idx in used:
                continue

            candidate_start_points = path_info[candidate_idx][2]["start_points"]

            # Simple nested loops for small numbers of paths - more efficient than matrix
            for end_ori, end_point in enumerate(current_end_points):
                for start_ori, start_point in enumerate(candidate_start_points):
                    distance = abs(end_point - start_point)

                    if distance < best_distance:
                        best_distance = distance
                        best_idx = candidate_idx
                        best_start_ori = start_ori

        if best_idx == -1:
            # No more candidates found, break
            break

        ordered_indices.append(best_idx)
        used.add(best_idx)
        orientation_choices.append((best_idx, best_start_ori))

        if channel:
            channel(
                f"  Added path {best_idx}: {display_label(path_info[best_idx][0])} at distance {best_distance:.6f}"
            )

    # Reconstruct the ordered path_info with proper orientations
    ordered_path_info = []
    for path_idx, orientation_idx in orientation_choices:
        node, geom, info = path_info[path_idx]

        # Apply the optimal orientation if needed
        if orientation_idx > 0:
            # Reverse the geomstr to start at the optimal segment
            geom = _reshuffle_closed_geomstr(geom, orientation_idx, channel)

        ordered_path_info.append((node, geom, info))

    if channel:
        channel(f"  Completed simple optimization with {len(ordered_path_info)} paths")

    return ordered_path_info


def _optimize_path_order_greedy_optimized(
    path_info, channel=None, max_iterations=None, start_position=0j
):
    """
    Optimized greedy path optimization algorithm that maintains result integrity with the original.

    Args:
        path_info: List of (node, geomstr, info) tuples
        channel: Channel for debug output
        max_iterations: Maximum number of optimization iterations (None = no limit)
        start_position: Starting position (complex number) to minimize total travel from

    Returns:
        Optimized path order as list of (node, geomstr, info) tuples
    """
    if len(path_info) < 2:
        return path_info

    if channel:
        channel(f"Starting optimized greedy optimization for {len(path_info)} paths")
        if max_iterations:
            channel(f"Max iterations: {max_iterations}")

    # Use the same approach as original but with optimizations
    n_paths = len(path_info)

    # Define threshold for when to use full matrix optimization
    # Use global threshold for matrix optimization
    if n_paths <= MATRIX_OPTIMIZATION_THRESHOLD:
        # Use simplified approach for small numbers of paths
        return _optimize_path_order_greedy_simple(path_info, channel, max_iterations, start_position)

    # For larger numbers of paths, use the full matrix optimization
    if channel:
        channel(f"  Using full matrix optimization for {n_paths} paths (> {MATRIX_OPTIMIZATION_THRESHOLD})")

    # Calculate maximum number of orientations (start/end point combinations)
    max_end_points = (
        max(len(info["end_points"]) for _, _, info in path_info) if path_info else 1
    )
    max_start_points = (
        max(len(info["start_points"]) for _, _, info in path_info) if path_info else 1
    )

    if channel:
        channel(
            f"  Maximum orientations: {max_end_points} end points, {max_start_points} start points"
        )

    # Pre-calculate distance matrix using numpy vectorization (MAJOR PERFORMANCE IMPROVEMENT)
    distance_matrix = np.zeros((n_paths, n_paths, max_end_points, max_start_points))

    if channel:
        channel("  Pre-calculating distance matrix using vectorized operations...")

    # Vectorized distance calculation - replaces nested loops with single operation
    for i in range(n_paths):
        for j in range(n_paths):
            if i != j:
                info_i = path_info[i][2]
                info_j = path_info[j][2]

                # Get points as numpy arrays
                end_points = np.array(info_i["end_points"], dtype=complex)
                start_points = np.array(info_j["start_points"], dtype=complex)

                # Vectorized distance calculation: all combinations at once
                # This replaces the nested loops: for end_idx, for start_idx: abs(end_pt - start_pt)
                distances = np.abs(end_points[:, np.newaxis] - start_points)

                # Store in the distance matrix
                n_ends = len(end_points)
                n_starts = len(start_points)
                distance_matrix[i, j, :n_ends, :n_starts] = distances

    # Find the optimal starting path to minimize total travel from start_position
    best_start_idx = 0
    best_start_distance = float("inf")
    best_start_ori = 0

    if channel:
        channel(f"  Finding optimal starting path from position {start_position}")

    # Vectorized approach: calculate all distances at once
    for start_idx in range(n_paths):
        start_info = path_info[start_idx][2]
        start_points = np.array(start_info["start_points"], dtype=complex)

        # Calculate distances from start_position to all start points for this path
        distances_from_start = np.abs(start_points - start_position)

        # Find the minimum distance for this path
        min_distance = np.min(distances_from_start)
        min_ori = np.argmin(distances_from_start)

        if min_distance < best_start_distance:
            best_start_distance = min_distance
            best_start_idx = start_idx
            best_start_ori = min_ori

    if channel:
        channel(
            f"  Optimal starting path: {best_start_idx} at distance {best_start_distance:.6f}"
        )

    # Start with the optimal path
    ordered_indices = [best_start_idx]
    used = {best_start_idx}
    orientation_choices = [(best_start_idx, best_start_ori)]  # (path_idx, orientation_idx) for each ordered path

    if channel:
        channel(
            f"  Starting with path {best_start_idx}: {display_label(path_info[best_start_idx][0])}"
        )

    # Greedily add the closest unused path
    total_iterations = 0

    while len(ordered_indices) < n_paths and (
        max_iterations is None or total_iterations < max_iterations
    ):
        total_iterations += 1

        best_distance = float("inf")
        best_idx = -1
        best_end_ori = 0
        best_start_ori = 0

        current_path_idx = ordered_indices[-1]
        current_end_points = path_info[current_path_idx][2]["end_points"]

        if channel:
            channel(
                f"  Finding next path after {display_label(path_info[current_path_idx][0])}"
            )

        for candidate_idx in range(n_paths):
            if candidate_idx in used:
                continue

            candidate_start_points = path_info[candidate_idx][2]["start_points"]

            # Find the best orientation combination for this candidate using vectorized min
            # This replaces the nested loops with a single numpy operation
            candidate_distances = distance_matrix[current_path_idx, candidate_idx,
                                                :len(current_end_points),
                                                :len(candidate_start_points)]

            # Find the minimum distance and its indices in one operation
            min_idx = np.unravel_index(np.argmin(candidate_distances), candidate_distances.shape)
            distance = candidate_distances[min_idx]

            if distance < best_distance:
                best_distance = distance
                best_idx = candidate_idx
                best_end_ori = min_idx[0]
                best_start_ori = min_idx[1]

        # If no improvement found, we're done
        if best_idx == -1:
            if channel:
                channel("No further improvements possible")
            break

        # Insert the best path
        ordered_indices.append(best_idx)
        used.add(best_idx)
        orientation_choices.append((best_end_ori, best_start_ori))

        if channel:
            channel(
                f"Iteration {total_iterations}: Added '{display_label(path_info[best_idx][0])}' at position {len(ordered_indices) - 1}"
            )
            channel(
                f"  Distance: {best_distance:.6f}, End ori: {best_end_ori}, Start ori: {best_start_ori}"
            )

    # Reconstruct the ordered path_info list
    ordered_path_info = [path_info[idx] for idx in ordered_indices]

    if channel:
        channel(f"Optimization completed in {total_iterations} iterations")
        channel(
            f"Final path order: {[display_label(node) for node, _, _ in ordered_path_info]}"
        )

    return ordered_path_info


def _calculate_total_travel_distance_from_indices(path_info, indices, distance_matrix):
    """
    Calculate total travel distance for a given path order using pre-calculated distance matrix.

    Args:
        path_info: List of (node, geomstr, info) tuples
        indices: List of indices representing the path order
        distance_matrix: Pre-calculated distance matrix

    Returns:
        Total travel distance
    """
    if len(indices) <= 1:
        return 0.0

    total_distance = 0.0

    for i in range(len(indices) - 1):
        current_idx = indices[i]
        next_idx = indices[i + 1]

        # Use the stored orientation choices or default to (0,0)
        current_end_ori = 0
        next_start_ori = 0

        # Get the actual number of orientations available
        current_end_points = len(path_info[current_idx][2]["end_points"])
        next_start_points = len(path_info[next_idx][2]["start_points"])

        # Ensure orientations are within bounds
        current_end_ori = min(current_end_ori, current_end_points - 1)
        next_start_ori = min(next_start_ori, next_start_points - 1)

        distance = distance_matrix[
            current_idx, next_idx, current_end_ori, next_start_ori
        ]
        total_distance += distance

    return total_distance


def create_dump_of(identifier, geom: Geomstr):
    print (f"  {identifier}=Geomstr()")
    for segment in geom.segments[: geom.index]:
        start, c0, info, c1, end = segment
        print(f"  {identifier}.append_segment({start}, {c0}, {info}, {c1}, {end})")


def is_geomstr_contained(outer_geom, inner_geom, tolerance: float = DEFAULT_CONTAINMENT_TOLERANCE, resolution: int = DEFAULT_CONTAINMENT_RESOLUTION) -> bool:
    """
    Determine if inner_geom is completely contained within outer_geom.

    This function combines the best of both approaches:
    - High-performance Shapely containment detection
    - Robust Scanbeam fallback with geometric sampling
    - Fast bounding box pre-checks for early rejection
    - Support for various input types (elements with .path attribute)
    - Special handling for raster images
    - LRU caching for repeated polygon computations

    Args:
        outer_geom: The outer geometry (container) - can be Geomstr or object with .path
        inner_geom: The inner geometry (contained) - can be Geomstr or object with .path
        tolerance: Tolerance for geometric operations
        resolution: Resolution for polygon sampling (higher = more accurate but slower)

    Returns:
        True if inner_geom is completely contained within outer_geom, False otherwise
    """
    if outer_geom is None or inner_geom is None:
        return False

    # Handle different input types - extract paths if needed
    outer_path = outer_geom
    inner_path = inner_geom

    if outer_geom == inner_geom:  # Same object
        return False

    # Extract paths from objects if they have .path attribute
    if hasattr(outer_geom, "path") and outer_geom.path is not None:
        outer_path = outer_geom.path
    if hasattr(inner_geom, "path") and inner_geom.path is not None:
        inner_path = inner_geom.path

    # Convert to Geomstr if needed
    if not isinstance(outer_path, Geomstr):
        try:
            outer_geomstr = Geomstr.svg(outer_path)
        except Exception:
            outer_geomstr = Geomstr()
    else:
        outer_geomstr = outer_path

    if not isinstance(inner_path, Geomstr):
        try:
            inner_geomstr = Geomstr.svg(inner_path)
        except Exception:
            inner_geomstr = Geomstr()
    else:
        inner_geomstr = inner_path

    if outer_geomstr.index == 0 or inner_geomstr.index == 0:
        return False

    # Fast bounding box pre-check for early rejection
    if not _bounding_box_contained(outer_geomstr, inner_geomstr, tolerance):
        return False

    # Try Shapely first for high-performance containment detection
    shapely_ops = _get_shapely_operations()
    if shapely_ops:
        try:
            # Convert Geomstr objects to Shapely geometries with caching
            outer_poly = _get_cached_shapely_polygon(outer_geomstr, resolution)
            inner_poly = _get_cached_shapely_polygon(inner_geomstr, resolution)

            if outer_poly is None or inner_poly is None:
                raise ImportError("Could not convert geometries to Shapely format")

            # Use Shapely's contains function for efficient containment detection
            return shapely_ops['contains'](outer_poly, inner_poly)

        except Exception as e:
            # Shapely operation failed, fall back to Scanbeam method
            print(f"Warning: Shapely containment failed ({e}), falling back to Scanbeam")

    # Fallback to Scanbeam-based containment detection
    return _scanbeam_containment_check(outer_geomstr, inner_geomstr, tolerance, resolution)


@lru_cache(maxsize=128)
def _geomstr_to_shapely_polygon_cached(geom_id: int, resolution: int):
    """
    Cached version of Geomstr to Shapely polygon conversion using object ID.

    Args:
        geom_id: ID of the Geomstr object to convert
        resolution: Resolution for polygon sampling

    Returns:
        Shapely Polygon or None if conversion fails
    """
    # This function is a placeholder - actual conversion happens in the main function
    return None


# Global cache for Shapely polygon conversions
_shapely_cache = {}

def _get_cached_shapely_polygon(geom: Geomstr, resolution: int):
    """
    Get cached Shapely polygon conversion with size-limited cache.

    Args:
        geom: Geomstr object to convert
        resolution: Resolution for polygon sampling

    Returns:
        Shapely Polygon or None if conversion fails
    """
    # Create cache key using object id and resolution
    cache_key = (id(geom), resolution)

    if cache_key in _shapely_cache:
        return _shapely_cache[cache_key]

    # Convert and cache
    polygon = _geomstr_to_shapely_polygon(geom, resolution)

    # Implement simple LRU by clearing cache if it gets too large
    if len(_shapely_cache) >= 128:  # Max cache size
        # Clear half the cache (simple approximation of LRU)
        items_to_remove = list(_shapely_cache.keys())[:64]
        for key in items_to_remove:
            del _shapely_cache[key]

    _shapely_cache[cache_key] = polygon
    return polygon


def _bounding_box_contained(outer_geom: Geomstr, inner_geom: Geomstr, tolerance: float = DEFAULT_CONTAINMENT_TOLERANCE) -> bool:
    """
    Fast bounding box containment check for early rejection.

    Args:
        outer_geom: Outer geometry
        inner_geom: Inner geometry
        tolerance: Tolerance for bounding box checks

    Returns:
        True if inner bounding box is contained within outer bounding box
    """
    try:
        # Get bounding boxes
        outer_bbox = outer_geom.bbox()
        inner_bbox = inner_geom.bbox()

        if outer_bbox is None or inner_bbox is None:
            return False

        # Check if inner bbox is completely contained within outer bbox
        return (outer_bbox[0] <= inner_bbox[0] - tolerance and  # outer minx <= inner minx
                outer_bbox[1] <= inner_bbox[1] - tolerance and  # outer miny <= inner miny
                outer_bbox[2] >= inner_bbox[2] + tolerance and  # outer maxx >= inner maxx
                outer_bbox[3] >= inner_bbox[3] + tolerance)     # outer maxy >= inner maxy

    except Exception:
        # If bbox calculation fails, assume containment is possible
        return True


def _scanbeam_containment_check(outer_geom: Geomstr, inner_geom: Geomstr, tolerance: float = DEFAULT_CONTAINMENT_TOLERANCE, resolution: int = DEFAULT_CONTAINMENT_RESOLUTION) -> bool:
    """
    Check containment using the Scanbeam algorithm from Geomstr with improved sampling.

    Args:
        outer_geom: The outer geometry (container)
        inner_geom: The inner geometry (contained)
        tolerance: Tolerance for geometric operations
        resolution: Resolution for point sampling

    Returns:
        True if inner_geom is contained within outer_geom, False otherwise
    """
    try:
        from meerk40t.tools.geomstr import Scanbeam

        # Create Scanbeam for the outer geometry
        scanbeam = Scanbeam(outer_geom)

        # Check if all points of inner_geom are inside outer_geom
        all_points_inside = True

        # Sample points from inner geometry for testing
        test_points = _sample_geometry_points(inner_geom, resolution)

        if not test_points:
            return False

        for point in test_points:
            if not scanbeam.is_point_inside(point.real, point.imag, tolerance):
                all_points_inside = False
                break

        return all_points_inside

    except Exception as e:
        print(f"Warning: Scanbeam containment check failed: {e}")
        return False


def _sample_geometry_points(geom: Geomstr, resolution: int = 100):
    """
    Sample points from a geometry for containment testing.

    Args:
        geom: Geometry to sample points from
        resolution: Number of interpolation points per segment

    Returns:
        List of complex points for testing
    """
    try:
        # Use Geomstr's optimized interpolation method
        points = list(geom.as_interpolated_points(interpolate=resolution))
        # Filter out None values (disconnected segments)
        return [p for p in points if p is not None]
    except Exception:
        # Fallback to manual sampling using geomstr.position method
        points = []
        for i, segment in enumerate(geom.segments[:geom.index]):
            # Always include start and end points
            start_point, control1, info, control2, end_point = segment
            points.extend([start_point, end_point])

            # For curved segments, sample additional points using position method
            segtype = geom._segtype(segment)
            if segtype in (TYPE_QUAD, TYPE_CUBIC, TYPE_ARC):
                # Sample points along curved segments using geomstr.position
                num_samples = max(5, resolution // 10)  # Adaptive sampling
                for j in range(1, num_samples):
                    t = j / num_samples
                    try:
                        point = geom.position(i, t)
                        if point is not None:
                            points.append(point)
                    except Exception:
                        # If position method fails, skip this point
                        continue
        return points


def _geomstr_to_shapely_polygon(geom: Geomstr, resolution: int = 100):
    """
    Convert a Geomstr object to a Shapely Polygon with configurable resolution.

    Args:
        geom: Geomstr object to convert
        resolution: Number of points to sample per segment for curve approximation

    Returns:
        Shapely Polygon or None if conversion fails
    """
    shapely_ops = _get_shapely_operations()
    if not shapely_ops:
        return None
    
    try:
        # Extract all subpaths from the Geomstr
        subpaths = list(geom.as_subpaths())

        if not subpaths:
            return None

        # Use the first closed subpath as the main polygon
        main_path = None
        holes = []

        for subpath in subpaths:
            if subpath.is_closed():
                # Use Geomstr's built-in interpolation for accurate point sampling
                coords = []
                try:
                    # Try as_interpolated_points first
                    interpolated_points = list(subpath.as_interpolated_points(interpolate=resolution))
                    
                    if len(interpolated_points) >= 3:
                        for point in interpolated_points:
                            if point is not None:  # Skip None values (disconnected segments)
                                coords.append((point.real, point.imag))
                    else:
                        # Fallback: manually extract points from segments
                        for segment in subpath.segments[:subpath.index]:
                            start_point, control1, info, control2, end_point = segment
                            start_coord = (start_point.real, start_point.imag)
                            end_coord = (end_point.real, end_point.imag)
                            if not coords:
                                coords.append(start_coord)
                            coords.append(end_coord)
                    
                    # Ensure we have enough points for a valid polygon
                    if len(coords) < 3:
                        continue
                        
                except Exception:
                    # Fallback to manual point extraction if interpolation fails
                    for segment in subpath.segments[:subpath.index]:
                        start_point, control1, info, control2, end_point = segment
                        if not coords:
                            coords.append((start_point.real, start_point.imag))
                        coords.append((end_point.real, end_point.imag))
                    
                    if len(coords) < 3:
                        continue

                # Ensure polygon is closed
                if coords[0] != coords[-1]:
                    coords.append(coords[0])

                if main_path is None:
                    main_path = coords
                else:
                    holes.append(coords)

        if main_path is None:
            return None

        # Create Shapely Polygon with holes if any
        polygon = shapely_ops['Polygon'](main_path, holes) if holes else shapely_ops['Polygon'](main_path)
        
        # Check if polygon is valid
        if not polygon.is_valid:
            return None
        
        return polygon

    except Exception as e:
        print(f"Warning: Failed to convert Geomstr to Shapely polygon: {e}")
        return None


def _collect_geometric_elements(elements_collection):
    """
    Collect all elements with geometry and build initial data structures.
    
    Args:
        elements_collection: Collection of elements to analyze
        
    Returns:
        tuple: (geometry_nodes, node_geometries, node_info)
    """
    geometry_nodes = []
    node_geometries = {}
    node_info = {}

    print("Collecting geometric elements...")
    for elem in elements_collection:
        node_id = id(elem)  # Use object ID as unique identifier
        
        # Special handling for image elements
        if getattr(elem, 'type', None) in ("elem image", "elem raster"):
            try:
                # For images, use as_image() to get PIL image and create geometry from bounds
                if hasattr(elem, 'as_image') and callable(getattr(elem, 'as_image')):
                    pil_image = elem.as_image()
                    if pil_image:
                        bbox = elem.bbox()
                        # Create a rectangular geometry from the image bounds
                        geom = Geomstr.rect(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1])
                        
                        if geom and geom.index > 0:
                            geometry_nodes.append(elem)
                            node_geometries[node_id] = geom
                            node_info[node_id] = {
                                'element': elem,
                                'bbox': geom.bbox(),
                                'type': 'elem image',
                                'label': getattr(elem, 'label', str(elem))
                            }
            except Exception as e:
                print(f"Warning: Failed to process image element {elem}: {e}")
        
        # Standard geometry extraction for other elements
        elif hasattr(elem, 'as_geometry') and callable(getattr(elem, 'as_geometry')):
            try:
                geom = elem.as_geometry()
                if geom and geom.index > 0:  # Only include non-empty geometries
                    geometry_nodes.append(elem)
                    node_geometries[node_id] = geom
                    node_info[node_id] = {
                        'element': elem,
                        'bbox': geom.bbox(),
                        'type': getattr(elem, 'type', 'unknown'),
                        'label': getattr(elem, 'label', str(elem))
                    }
            except Exception as e:
                print(f"Warning: Failed to get geometry for element {elem}: {e}")
                continue

    print(f"Found {len(geometry_nodes)} geometric elements")
    return geometry_nodes, node_geometries, node_info


def _compute_bbox_cache(node_info):
    """
    Pre-compute bounding boxes for fast rejection.
    
    Args:
        node_info: Dictionary mapping node_id -> node information
        
    Returns:
        dict: bbox_cache mapping node_id -> bbox
    """
    print("Pre-computing bounding boxes...")
    bbox_cache = {}
    for node_id, info in node_info.items():
        bbox_cache[node_id] = info['bbox']
    return bbox_cache


def _analyze_containment_relationships(geometry_nodes, node_geometries, node_info, bbox_cache, tolerance, resolution):
    """
    Analyze containment relationships between geometric elements.
    
    Args:
        geometry_nodes: List of geometry nodes
        node_geometries: Dict mapping node_id -> geometry
        node_info: Dict mapping node_id -> node information
        bbox_cache: Dict mapping node_id -> bbox
        tolerance: Tolerance for geometric operations
        resolution: Resolution for polygon sampling
        
    Returns:
        tuple: (containment_tree, containment_map, contained_nodes, comparisons_made)
    """
    from collections import defaultdict
    
    containment_tree = defaultdict(list)  # node_id -> list of contained node_ids
    containment_map = {}  # (outer_id, inner_id) -> containment result
    contained_nodes = set()  # Track nodes that are contained by others

    print("Analyzing containment relationships...")

    # Sort nodes by bounding box area (smaller first) for optimization
    def bbox_area(bbox):
        if bbox is None:
            return 0
        return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])

    sorted_nodes = sorted(geometry_nodes, key=lambda elem: bbox_area(bbox_cache[id(elem)]))

    comparisons_made = 0
    total_comparisons = len(geometry_nodes) * (len(geometry_nodes) - 1) // 2

    for i, outer_elem in enumerate(sorted_nodes):
        outer_id = id(outer_elem)
        outer_bbox = bbox_cache[outer_id]
        
        if i % 10 == 0:
            print(f"  Processing element {i + 1}/{len(sorted_nodes)}...")

        for inner_elem in sorted_nodes[i + 1:]:
            inner_id = id(inner_elem)
            inner_bbox = bbox_cache[inner_id]
            
            # Quick bounding box rejection
            if not _bbox_might_contain(outer_bbox, inner_bbox, tolerance):
                continue

            comparisons_made += 1
            
            # Perform detailed containment check
            try:
                outer_geom = node_geometries[outer_id]
                inner_geom = node_geometries[inner_id]
                
                is_contained = is_geomstr_contained(outer_geom, inner_geom, tolerance, resolution)
                containment_map[(outer_id, inner_id)] = is_contained
                
                if is_contained:
                    containment_tree[outer_id].append(inner_id)
                    contained_nodes.add(inner_id)
                    
            except Exception as e:
                print(f"Warning: Failed containment check between {outer_elem} and {inner_elem}: {e}")

    print(f"  Made {comparisons_made} detailed comparisons out of {total_comparisons} possible")
    
    return containment_tree, containment_map, contained_nodes, comparisons_made


def build_geometry_hierarchy(elements_collection, tolerance: float = DEFAULT_TOLERANCE, resolution: int = 50):
    """
    Build a hierarchical tree representation of geometric containment relationships.

    This function analyzes all elements with as_geometry() method and establishes
    parent-child relationships based on geometric containment. Uses optimization
    to avoid redundant comparisons.

    Args:
        elements_collection: Collection of elements (e.g., from kernel.elements.elems())
        tolerance: Tolerance for geometric operations
        resolution: Resolution for polygon sampling

    Returns:
        Dictionary with hierarchy information:
        {
            'nodes': list of all nodes with geometry,
            'containment_tree': dict mapping node_id -> list of contained node_ids,
            'containment_map': dict mapping (outer_id, inner_id) -> containment result,
            'root_nodes': list of nodes not contained by any other,
            'stats': dict with statistics about the analysis
        }
    """
    # Step 1: Collect all elements with geometry
    geometry_nodes, node_geometries, node_info = _collect_geometric_elements(elements_collection)

    if len(geometry_nodes) < 2:
        return {
            'nodes': geometry_nodes,
            'containment_tree': {},
            'containment_map': {},
            'root_nodes': geometry_nodes,
            'stats': {'total_elements': len(geometry_nodes), 'comparisons_made': 0}
        }

    # Step 2: Pre-compute bounding boxes for fast rejection
    bbox_cache = _compute_bbox_cache(node_info)

    # Step 3: Build containment relationships with optimization
    containment_tree, containment_map, contained_nodes, comparisons_made = _analyze_containment_relationships(
        geometry_nodes, node_geometries, node_info, bbox_cache, tolerance, resolution
    )

    # Step 4: Identify root nodes (not contained by any other)
    root_nodes = []
    for elem in geometry_nodes:
        node_id = id(elem)
        if node_id not in contained_nodes:
            root_nodes.append(elem)

    # Step 5: Build statistics
    stats = {
        'total_elements': len(geometry_nodes),
        'comparisons_made': comparisons_made,
        'contained_elements': len(contained_nodes),
        'root_elements': len(root_nodes),
        'containment_relationships': sum(len(children) for children in containment_tree.values())
    }

    print("Hierarchy analysis complete:")
    print(f"  - Total elements: {stats['total_elements']}")
    print(f"  - Containment relationships: {stats['containment_relationships']}")
    print(f"  - Root elements: {stats['root_elements']}")
    print(f"  - Comparisons made: {stats['comparisons_made']}")

    return {
        'nodes': geometry_nodes,
        'containment_tree': dict(containment_tree),
        'containment_map': containment_map,
        'root_nodes': root_nodes,
        'node_info': node_info,
        'stats': stats
    }


def _bbox_might_contain(outer_bbox, inner_bbox, tolerance: float = 0) -> bool:
    """
    Fast bounding box check to see if outer might contain inner.

    Args:
        outer_bbox: Outer bounding box (x1, y1, x2, y2)
        inner_bbox: Inner bounding box (x1, y1, x2, y2)
        tolerance: Tolerance for comparison

    Returns:
        True if inner bbox is potentially contained within outer bbox
    """
    if outer_bbox is None or inner_bbox is None:
        return False

    # Check if containment is impossible (inner extends outside outer in any dimension)
    containment_impossible = (inner_bbox[0] - tolerance > outer_bbox[2] or  # inner.left - tolerance > outer.right
                              inner_bbox[2] + tolerance < outer_bbox[0] or  # inner.right + tolerance < outer.left
                              inner_bbox[1] - tolerance > outer_bbox[3] or  # inner.top - tolerance > outer.bottom
                              inner_bbox[3] + tolerance < outer_bbox[1])    # inner.bottom + tolerance < outer.top

    return not containment_impossible  # If containment is not impossible, it might be possible


def _mark_descendants_as_contained(containment_tree, ancestor_id, parent_id, contained_nodes):
    """
    Recursively mark all descendants of parent_id as contained by ancestor_id.

    This optimization avoids redundant containment checks by leveraging the
    transitive property: if A contains B and B contains C, then A contains C.

    Args:
        containment_tree: Current containment relationships
        ancestor_id: The ancestor node that contains everything
        parent_id: The parent node whose descendants we're marking
        contained_nodes: Set of nodes known to be contained
    """
    if parent_id not in containment_tree:
        return

    for child_id in containment_tree[parent_id]:
        if child_id not in contained_nodes:
            contained_nodes.add(child_id)
            # Recursively mark descendants
            _mark_descendants_as_contained(containment_tree, ancestor_id, child_id, contained_nodes)


def print_geometry_hierarchy(hierarchy_result, max_depth: int = 3):
    """
    Print a human-readable representation of the geometry hierarchy.

    Args:
        hierarchy_result: Result from build_geometry_hierarchy()
        max_depth: Maximum depth to display
    """
    print("\n" + "="*60)
    print("GEOMETRY CONTAINMENT HIERARCHY")
    print("="*60)

    containment_tree = hierarchy_result['containment_tree']
    node_info = hierarchy_result['node_info']
    root_nodes = hierarchy_result['root_nodes']

    def print_node(node_id, depth=0, prefix=""):
        if depth > max_depth:
            print(f"{'  ' * depth}{prefix}... (truncated)")
            return

        info = node_info.get(node_id, {})
        elem = info.get('element', f"Node {node_id}")
        node_type = info.get('type', 'unknown')
        label = info.get('label', str(elem))

        print(f"{'  ' * depth}{prefix}{node_type}: {label}")

        if node_id in containment_tree:
            children = containment_tree[node_id]
            for i, child_id in enumerate(children):
                next_prefix = "└── " if i == len(children) - 1 else "├── "
                print_node(child_id, depth + 1, next_prefix)

    print(f"Root nodes ({len(root_nodes)}):")
    for i, root_elem in enumerate(root_nodes):
        root_id = id(root_elem)
        prefix = "└── " if i == len(root_nodes) - 1 else "├── "
        print_node(root_id, 0, prefix)

    # Print statistics
    stats = hierarchy_result['stats']
    print("\nStatistics:")
    print(f"  Total elements: {stats['total_elements']}")
    print(f"  Containment relationships: {stats['containment_relationships']}")
    print(f"  Root elements: {stats['root_elements']}")
    print(f"  Comparisons made: {stats['comparisons_made']}")
    if 'cache_hits' in stats:
        print(f"  Cache efficiency: {stats.get('cache_hits', 0)} cached results used")


def get_containment_depth(hierarchy_result, node_id):
    """
    Get the containment depth of a node in the hierarchy.

    Args:
        hierarchy_result: Result from build_geometry_hierarchy()
        node_id: ID of the node to check

    Returns:
        Depth level (0 = root, higher numbers = deeper nesting)
    """
    containment_tree = hierarchy_result['containment_tree']

    def find_depth(current_id, visited=None):
        if visited is None:
            visited = set()

        if current_id in visited:
            return 0  # Avoid cycles

        visited.add(current_id)
        max_depth = 0

        # Find all parents of this node
        for parent_id, children in containment_tree.items():
            if current_id in children:
                parent_depth = find_depth(parent_id, visited.copy())
                max_depth = max(max_depth, parent_depth + 1)

        return max_depth

    return find_depth(node_id)


def find_nested_groups(hierarchy_result, min_group_size: int = 2):
    """
    Find groups of nested elements for optimization opportunities.

    Args:
        hierarchy_result: Result from build_geometry_hierarchy()
        min_group_size: Minimum number of elements to consider a group

    Returns:
        List of nested groups, each containing the parent and its direct children
    """
    containment_tree = hierarchy_result['containment_tree']
    nested_groups = []

    for parent_id, children in containment_tree.items():
        if len(children) >= min_group_size:
            group = {
                'parent': parent_id,
                'children': children,
                'group_size': len(children) + 1,  # +1 for parent
                'parent_info': hierarchy_result['node_info'].get(parent_id, {})
            }
            nested_groups.append(group)

    # Sort by group size (largest first)
    nested_groups.sort(key=lambda g: g['group_size'], reverse=True)

    return nested_groups
