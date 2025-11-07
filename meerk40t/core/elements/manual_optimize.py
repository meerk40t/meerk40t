from meerk40t.core.geomstr import Geomstr
from meerk40t.core.units import Length
from meerk40t.core.elements.element_types import (
    op_burnable_nodes,
)
import numpy as np

# Import TYPE constants for geometric operations
from meerk40t.core.geomstr import TYPE_QUAD, TYPE_CUBIC, TYPE_ARC

# Import for caching and additional utilities
from functools import lru_cache


# ==========
# OPTIMIZATION CONSTANTS
# ==========

# Path optimization thresholds
MATRIX_OPTIMIZATION_THRESHOLD = (
    25  # Paths - threshold for using full matrix optimization
)
MAX_GREEDY_ITERATIONS = 1000  # Maximum iterations for greedy algorithms
DEFAULT_TOLERANCE = 1e-6  # Default geometric tolerance for calculations
DEFAULT_CONTAINMENT_TOLERANCE = 1e-3  # Default tolerance for containment checks
DEFAULT_CONTAINMENT_RESOLUTION = (
    100  # Default resolution for containment polygon sampling
)

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

        return {"contains": contains, "Polygon": Polygon, "available": True}
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
    # OPTIMIZATION COMMANDS  
    # ==========
    @self.console_option(
        "debug",
        type=bool,
        action="store_true",
        help=_("Provide detailed debug output"),
    )
    @self.console_argument(
        "start_x", type=float, help=_("Starting X position"), default=0.0
    )
    @self.console_argument(
        "start_y", type=float, help=_("Starting Y position"), default=0.0
    )
    @self.console_command(
        "reorder",
        help=_("reorder elements for optimal cutting within an operation"),
        input_type=("ops", None),
        output_type="ops",
    )
    def element_reorder(
        channel,
        _,
        start_x=None,
        start_y=None,
        debug=None,
        data=None,
        post=None,
        **kwargs,
    ):
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
                optimization_result = optimize_node_travel_under(
                    self, op, channel, debug_channel, start_position=start_position
                )
                opout.append(op)

                # Collect results for summary
                if optimization_result["optimized"]:
                    optimized_operations.append(display_label(op))
                    total_improvement += optimization_result["improvement"]

                operation_results.append((display_label(op), optimization_result))

                # New start_position is last position of the last node
                if len(op.children) > 0:
                    last_child = op.children[-1]
                    if last_child.type == "reference" and last_child.node is not None:
                        last_node = last_child.node
                        if hasattr(last_node, "as_geometry") and callable(
                            getattr(last_node, "as_geometry")
                        ):
                            try:
                                geomstr = last_node.as_geometry()
                                if geomstr and geomstr.index > 0:
                                    last_segment = geomstr.segments[geomstr.index - 1]
                                    start_point, control1, info, control2, end_point = (
                                        last_segment
                                    )
                                    start_position = end_point
                            except Exception as e:
                                channel(
                                    f"Error extracting geometry from last node: {e}"
                                )

        # Display optimization summary
        if operation_results:
            channel(f"\n{'=' * 60}")
            channel("PATH OPTIMIZATION SUMMARY")
            channel(f"{'=' * 60}")

            total_distance_saved = 0.0
            optimized_count = 0

            for op_label, result in operation_results:
                if result["optimized"]:
                    channel(f"✓ {op_label}:")
                    channel(f"  Paths optimized: {result['path_count']}")
                    channel(
                        f"  Distance saved: {Length(result['improvement'], digits=0).length_mm}"
                    )
                    total_distance_saved += result["improvement"]
                    optimized_count += 1
                else:
                    channel(
                        f"○ {op_label}: No optimization needed ({result['path_count']} paths)"
                    )

            channel(f"{'=' * 60}")
            if optimized_count > 0:
                channel("Summary:")
                channel(f"  Operations optimized: {optimized_count}")
                channel(
                    f"  Total distance saved: {Length(total_distance_saved, digits=0).length_mm}"
                )
                channel(
                    f"  Optimized operations: {', '.join([op_label for op_label, result in operation_results if result['optimized'] and op_label is not None])}"
                )
            else:
                channel("No operations required optimization")
            channel(f"{'=' * 60}\n")

        self.signal("rebuild_tree")
        return "ops", opout

    def optimize_node_travel_under(
        self, op, channel, debug_channel, leading="", start_position=0j
    ):
        node_list = []
        child_list = []

        # Track optimization results from child operations
        total_optimization_results = {
            "optimized": False,
            "original_distance": 0,
            "optimized_distance": 0,
            "improvement": 0,
            "improvement_percent": 0,
            "path_count": 0,
        }

        for child in op.children:
            if debug_channel:
                debug_channel(f"{leading}{display_label(child)}")
            if child.type.startswith("effect"):
                # We reorder the children of the effect, not the effect itself
                child_result = optimize_node_travel_under(
                    self,
                    child,
                    channel,
                    debug_channel,
                    leading=f"{leading}  ",
                    start_position=start_position,
                )
                # Accumulate results from child operations
                if child_result["optimized"]:
                    total_optimization_results["optimized"] = True
                    total_optimization_results["improvement"] += child_result[
                        "improvement"
                    ]
                    total_optimization_results["path_count"] += child_result[
                        "path_count"
                    ]
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
                + ", ".join(
                    [str(display_label(n)) for n in child_list if n is not None]
                )
            )
        if len(node_list) > 1:
            # We need to make sure we have ids for all nodes (and they should be unique)
            self.validate_ids(node_list)
            ordered_nodes, optimization_results = optimize_path_order(
                node_list, channel, debug_channel, start_position
            )
            if ordered_nodes != node_list:
                # Clear old children
                for child in child_list:
                    child.remove_node()
                # Rebuild children in new order
                for node in ordered_nodes:
                    op.add_reference(node)

            # Combine with any results from child operations
            if optimization_results["optimized"]:
                total_optimization_results["optimized"] = True
                total_optimization_results["improvement"] += optimization_results[
                    "improvement"
                ]
                total_optimization_results["path_count"] += optimization_results[
                    "path_count"
                ]

            return total_optimization_results
        else:
            channel(f"No need to reorder {display_label(op)}")
            return total_optimization_results

    def optimize_path_order(
        node_list, channel=None, debug_channel=None, start_position=0j
    ):
        if len(node_list) < 2:
            # Return consistent tuple format even when no optimization is needed
            return node_list, {
                "optimized": False,
                "original_distance": 0.0,
                "optimized_distance": 0.0,
                "improvement": 0.0,
                "improvement_percent": 0.0,
                "path_count": 0,
            }

        if debug_channel:
            debug_channel(
                f"Starting path optimization for {len(node_list)} nodes from position {start_position}"
            )

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
            # Return consistent tuple format
            return node_list, {
                "optimized": False,
                "original_distance": 0.0,
                "optimized_distance": 0.0,
                "improvement": 0.0,
                "improvement_percent": 0.0,
                "path_count": len(geomstr_nodes),
            }

        # Extract path information for each geomstr node
        path_info = []
        for node, geomstr in geomstr_nodes:
            if debug_channel:
                debug_channel(f"Extracting path info for node {display_label(node)}")
            may_extend = hasattr(node, "set_geometry")
            may_reverse = True  # Assume we can reverse unless proven otherwise
            if node.type in ("elem image", "elem text", "elem raster"):
                may_reverse = False
            info = _extract_path_info(
                geomstr, may_extend, may_reverse=may_reverse, channel=debug_channel
            )
            path_info.append((node, geomstr, info))

        # Calculate original travel distance
        original_distance = _calculate_total_travel_distance(
            path_info, debug_channel, start_position
        )

        # Optimize the order using greedy nearest neighbor with improvements
        ordered_path_info = _optimize_path_order_greedy(
            path_info, debug_channel, start_position
        )

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
            "optimized": ordered_path_info != path_info,
            "original_distance": original_distance,
            "optimized_distance": optimized_distance,
            "improvement": original_distance - optimized_distance,
            "improvement_percent": (original_distance - optimized_distance)
            / original_distance
            * 100
            if original_distance > 0
            else 0,
            "path_count": len(geomstr_nodes),
        }

        return ordered_nodes, optimization_results

    # ==========
    # WORKFLOW MANAGEMENT COMMANDS
    # ==========

    @self.console_option(
        "tolerance",
        type=float,
        default=DEFAULT_CONTAINMENT_TOLERANCE,
        help=_("Geometric tolerance for containment analysis"),
    )
    @self.console_command(
        "workflow_optimize",
        help=_("Optimize selected operations using containment-aware workflow"),
        input_type="ops",
        output_type="ops",
    )
    def workflow_optimize(channel, _, tolerance=None, data=None, post=None, **kwargs):
        """Optimize operations using containment-aware workflow scheduling."""
        try:
            from .operation_workflow import create_operation_workflow

            operations = data if data is not None else list(self.ops(selected=True))

            if not operations:
                channel(_("No operations selected for workflow optimization"))
                return "ops", []

            # Convert to workflow format
            workflow_ops = []
            for op in operations:
                op_type = getattr(op, "type", "op cut")
                workflow_ops.append((op, op_type))

            # Create and process workflow
            workflow = create_operation_workflow(workflow_ops, tolerance=tolerance)
            optimized_order = workflow.generate_workflow()

            # Get summary statistics
            summary = workflow.get_workflow_summary()

            # Report results
            channel(_("Workflow Optimization Results:"))
            channel(f"  Total operations: {summary['total_operations']}")
            channel(f"  Processing groups: {summary['total_groups']}")
            channel(
                f"  Containment relationships: {summary['containment_relationships']}"
            )
            channel(f"  Total travel distance: {summary['total_travel_distance']:.2f}")

            # Show group details
            for group in summary["groups"]:
                channel(
                    f"  Group {group['priority']}: {group['operation_count']} operations"
                )

            return "ops", optimized_order

        except ImportError as e:
            channel(f"Workflow optimization not available: {e}")
            return "ops", data
        except Exception as e:
            channel(f"Error in workflow optimization: {e}")
            return "ops", data




def display_label(node):
    try:
        res = f"{node.type}.{node.id if node.id is not None else '-'}.{node.label if node.label is not None else '-'}"
    except Exception:
        res = f"Err-{node}"
    return res


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
    orientation_choices = [
        (best_start_idx, best_start_ori)
    ]  # (path_idx, orientation_idx) for each ordered path

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
        return _optimize_path_order_greedy_simple(
            path_info, channel, max_iterations, start_position
        )

    # For larger numbers of paths, use the full matrix optimization
    if channel:
        channel(
            f"  Using full matrix optimization for {len(path_info)} paths (> {MATRIX_OPTIMIZATION_THRESHOLD})"
        )

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
            min_distance_to_first = min(
                abs(start_point - start_position) for start_point in first_start_points
            )
            total_distance += min_distance_to_first

            if channel:
                channel(
                    f"  Distance from start position {start_position} to first path: {min_distance_to_first:.6f}"
                )

    # Calculate distances between consecutive paths
    for i in range(len(path_info) - 1):
        current_node, current_geom, current_info = path_info[i]
        next_node, next_geom, next_info = path_info[i + 1]

        # Calculate distance between end of current path and start of next path
        distance = _calculate_path_to_path_distance_optimized(current_info, next_info)
        total_distance += distance

        if channel:
            channel(f"  Distance from path {i} to path {i + 1}: {distance:.6f}")

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


def _optimize_path_order_greedy_simple(
    path_info, channel=None, max_iterations=None, start_position=0j
):
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
