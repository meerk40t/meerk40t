from meerk40t.tools.geomstr import Geomstr
from meerk40t.core.units import Length
from meerk40t.core.elements.element_types import (
    op_burnable_nodes,
)
import numpy as np
import itertools


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
        "amount", type=int, help=_("Number of shapes to create"), default=10
    )
    @self.console_command(
        "testcase",
        help=_("Create test case for optimization"),
        input_type=None,
        output_type="elements",
    )
    def reorder_testcase(channel, _, amount=None, data=None, post=None, **kwargs):
        if amount is None or amount < 1:
            amount = 10
        branch = self.elem_branch
        import random

        random.seed(42)
        data = []
        for i in range(amount):
            x = random.uniform(5, 95)
            y = random.uniform(5, 95)
            w = random.uniform(5, 20)
            h = random.uniform(5, 20)
            type_selector = random.randint(
                0, 3
            )  # 0=line, 1=poly open, 2=poly closed, 3=rectangle, 4=ellipse
            if type_selector == 0:
                # Line
                x2 = min(100, max(0, x + w))
                y2 = min(100, max(0, y + h))
                node = branch.add(
                    "elem line",
                    x1=float(Length(f"{x}%", relative_length=self.device.view.width)),
                    y1=float(Length(f"{y}%", relative_length=self.device.view.height)),
                    x2=float(Length(f"{x2}%", relative_length=self.device.view.width)),
                    y2=float(Length(f"{y2}%", relative_length=self.device.view.height)),
                    stroke=self.default_stroke,
                    stroke_width=self.default_strokewidth,
                    label=f"Testline #{i + 1}",
                )
            elif type_selector == 1:
                # Polyline open
                points = []
                n_points = random.randint(3, 6)
                px = x
                py = y
                for _ in range(n_points):
                    px += random.uniform(-10, 10)
                    py += random.uniform(-10, 10)
                    px = min(max(px, 0), 100)
                    py = min(max(py, 0), 100)
                    points.append(
                        (
                            float(
                                Length(f"{px}%", relative_length=self.device.view.width)
                            ),
                            float(
                                Length(
                                    f"{py}%", relative_length=self.device.view.height
                                )
                            ),
                        )
                    )
                node = branch.add(
                    "elem polyline",
                    geometry=Geomstr().lines(*points),
                    stroke=self.default_stroke,
                    stroke_width=self.default_strokewidth,
                    fill=None,
                    label=f"Polyline open #{i + 1}",
                )
            elif type_selector == 2:
                # Polyline open
                points = []
                n_points = random.randint(3, 6)
                px = x
                py = y
                for _ in range(n_points):
                    px += random.uniform(-10, 10)
                    py += random.uniform(-10, 10)
                    px = min(max(px, 0), 100)
                    py = min(max(py, 0), 100)

                    points.append(
                        (
                            float(
                                Length(f"{px}%", relative_length=self.device.view.width)
                            ),
                            float(
                                Length(
                                    f"{py}%", relative_length=self.device.view.height
                                )
                            ),
                        )
                    )
                points.append(points[0])  # Close the polyline
                node = branch.add(
                    "elem polyline",
                    geometry=Geomstr().lines(*points),
                    stroke=self.default_stroke,
                    stroke_width=self.default_strokewidth,
                    fill=None,
                    label=f"Polyline closed #{i + 1}",
                )
            elif type_selector == 3:
                # Rectangle
                x = min(max(x, w), 100 - w)
                y = min(max(y, h), 100 - h)
                node = branch.add(
                    "elem rect",
                    x=float(Length(f"{x}%", relative_length=self.device.view.height)),
                    y=float(Length(f"{y}%", relative_length=self.device.view.width)),
                    width=float(
                        Length(f"{w}%", relative_length=self.device.view.height)
                    ),
                    height=float(
                        Length(f"{h}%", relative_length=self.device.view.width)
                    ),
                    stroke=self.default_stroke,
                    stroke_width=self.default_strokewidth,
                    fill=None,
                    label=f"Rectangle #{i + 1}",
                )
            else:
                # Ellipse
                x = min(max(x, w), 100 - w)
                y = min(max(y, h), 100 - h)
                node = branch.add(
                    "elem ellipse",
                    cx=float(Length(f"{x}%", relative_length=self.device.view.height)),
                    cy=float(Length(f"{y}%", relative_length=self.device.view.width)),
                    rx=float(Length(f"{w}%", relative_length=self.device.view.height)),
                    ry=float(Length(f"{h}%", relative_length=self.device.view.width)),
                    stroke=self.default_stroke,
                    stroke_width=self.default_strokewidth,
                    fill=None,
                    label=f"Ellipse #{i + 1}",
                )
            data.append(node)
        post.append(self.post_classify(data))
        return "elements", data

    @self.console_argument(
        "start_x", type=float, help=_("Starting X position"), default=0.0)
    @self.console_argument(
        "start_y", type=float, help=_("Starting Y position"), default=0.0)
    @self.console_command(
        "reorder",
        help=_("reorder elements for optimal cutting within an operation"),
        input_type=("operations", None),
        output_type="operations",
    )
    def element_reorder(channel, _, start_x=None, start_y=None, data=None, post=None, **kwargs):
        start_position = complex(start_x or 0.0, start_y or 0.0)
        oplist = data if data is not None else list(self.ops(selected=True))
        opout = []
        for op in oplist:
            if op.type in op_burnable_nodes:
                optimize_node_travel_under(op, channel, start_position)
                opout.append(op)
        self.signal("rebuild_tree")
        return "operations", opout

    def optimize_node_travel_under(op, channel, leading="", start_position=0j):
        node_list = []
        child_list = []
        for child in op.children:
            channel(f"{leading}{display_label(child)}")
            if child.type.startswith("effect"):
                # We reorder the children of the effect, not the effect itself
                optimize_node_travel_under(child, channel, leading=f"{leading}  ", start_position=start_position)
            elif child.type == "reference":
                channel(
                    f"{leading}Reference to {display_label(child.node) if child.node else 'None!!!'}"
                )
                node_list.append(child.node)
                child_list.append(child)
            else:
                channel(
                    f"{leading}Don't know how to handle {child.type} in reorder for {display_label(op)}"
                )
        channel(f"{leading}Nodes:")
        channel(
            f"{leading}  "
            + " ".join([str(display_label(n)) for n in node_list if n is not None])
        )
        channel(f"{leading}Children:")
        channel(
            f"{leading}  "
            + ", ".join([str(display_label(n)) for n in child_list if n is not None])
        )
        if len(node_list) > 1:
            # We need to make sure we have ids for all nodes (and they should be unique)
            self.validate_ids(node_list)
            ordered_nodes = optimize_path_order(node_list, channel, start_position)
            if ordered_nodes != node_list:
                # Clear old children
                for child in child_list:
                    child.remove_node()
                # Rebuild children in new order
                for node in ordered_nodes:
                    op.add_reference(node)
        else:
            channel(f"No need to reorder {op.display_label()}")

    def optimize_path_order(node_list, channel=None, start_position=0j):
        if len(node_list) < 2:
            return node_list

        if channel:
            channel(f"Starting path optimization for {len(node_list)} nodes from position {start_position}")

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
                        if channel:
                            channel(
                                f"  Node {display_label(node) or 'Unknown'}: {geomstr.index} segments"
                            )
                    else:
                        non_geomstr_nodes.append(node)
                        if channel:
                            channel(
                                f"  Node {display_label(node) or 'Unknown'}: Empty geometry"
                            )
                except Exception as e:
                    non_geomstr_nodes.append(node)
                    if channel:
                        channel(
                            f"  Node {display_label(node) or 'Unknown'}: Error extracting geometry - {e}"
                        )
            else:
                non_geomstr_nodes.append(node)
                if channel:
                    channel(
                        f"  Node {display_label(node) or 'Unknown'}: No as_geometry method"
                    )

        if channel:
            channel(
                f"Found {len(geomstr_nodes)} geomstr nodes and {len(non_geomstr_nodes)} non-geomstr nodes"
            )

        if len(geomstr_nodes) < 2:
            # Not enough geomstr nodes to optimize, return original order
            if channel:
                channel(
                    "Not enough geomstr nodes to optimize, returning original order"
                )
            return node_list

        # Extract path information for each geomstr node
        path_info = []
        for node, geomstr in geomstr_nodes:
            if channel:
                channel(f"Extracting path info for node {display_label(node)}")
            may_extend = hasattr(node, "set_geometry")
            info = _extract_path_info(geomstr, may_extend, channel)
            path_info.append((node, geomstr, info))

        # Calculate original travel distance
        original_distance = _calculate_total_travel_distance(path_info, channel)

        # Optimize the order using greedy nearest neighbor with improvements
        ordered_path_info = _optimize_path_order_greedy(path_info, channel, start_position)

        # Calculate optimized travel distance
        optimized_distance = _calculate_total_travel_distance(
            ordered_path_info, channel
        )

        # Report results to channel if available
        if channel:
            improvement = original_distance - optimized_distance
            improvement_percent = (
                (improvement / original_distance * 100) if original_distance > 0 else 0
            )
            channel(f"Path optimization for {len(geomstr_nodes)} paths:")
            channel(
                f"  Original travel distance: {Length(original_distance).length_mm}"
            )
            channel(
                f"  Optimized travel distance: {Length(optimized_distance).length_mm}"
            )
            channel(
                f"  Distance saved: {Length(improvement).length_mm}  ({improvement_percent:.1f}%)"
            )

        # Reconstruct the ordered node list
        ordered_nodes = [node for node, _, _ in ordered_path_info] + non_geomstr_nodes

        return ordered_nodes


def display_label(node):
    return f"{node.type}.{node.id if node.id is not None else '-'}.{node.label if node.label is not None else '-'}"


def _extract_path_info(geomstr, may_extend, channel=None):
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
    if len(segments) > 1:
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
            start_pt = segment[0]
            end_pt = segment[4]
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

    for start_idx in range(n_paths):
        start_info = path_info[start_idx][2]
        start_points = start_info["start_points"]

        for start_ori in range(len(start_points)):
            distance_from_start = abs(start_points[start_ori] - start_position)
            if distance_from_start < best_start_distance:
                best_start_distance = distance_from_start
                best_start_idx = start_idx
                best_start_ori = start_ori

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
            f"  Starting with path {best_start_idx}: {display_label(path_info[best_start_idx][0]) or 'Unknown'}"
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

            # Find the best orientation combination using direct distance calculation
            for end_ori, start_ori in itertools.product(
                range(len(current_end_points)), range(len(candidate_start_points))
            ):
                # Calculate distance directly (no cache needed)
                end_pt = current_end_points[end_ori]
                start_pt = candidate_start_points[start_ori]
                distance = abs(end_pt - start_pt)

                if distance < best_distance:
                    best_distance = distance
                    best_idx = candidate_idx
                    best_start_ori = start_ori

                path_iterations += 1
                iteration_shuffles += 1

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
                f"  Added path {best_idx}: {display_label(path_info[best_idx][0])} (distance: {Length(best_distance).length_mm}, orientation: {best_start_ori})"
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
                            f"  Node {display_label(node) or 'Unknown'}: Applied reshuffled geometry, starting at segment {start_segment_idx}{'' if oldtype == newnode.type else ' (type changed)'}"
                        )
            else:
                final_geomstr = original_geomstr
                if channel:
                    channel(
                        f"  Node {display_label(node) or 'Unknown'}: Fallback to original (invalid candidate index)"
                    )
        else:
            # Fallback to original
            final_geomstr = original_geomstr
            if channel:
                channel(
                    f"  Node {display_label(node) or 'Unknown'}: Fallback to original orientation (orientation_idx={orientation_idx}, available={len(info['start_points'])})"
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
    path_info, channel=None, max_iterations=None
):
    """
    Optimized greedy path optimization algorithm with lazy evaluation.

    Args:
        path_info: List of (node, geom, info) tuples
        channel: Channel for debug output
        max_iterations: Maximum number of optimization iterations (None = no limit)

    Returns:
        Optimized path order as list of (node, geom, info) tuples
    """
    if not path_info:
        return []

    if len(path_info) == 1:
        return path_info

    if channel:
        channel(
            f"Starting optimized greedy path optimization with {len(path_info)} paths"
        )
        if max_iterations:
            channel(f"Max iterations: {max_iterations}")

    # Initialize with first path
    optimized_paths = [path_info[0]]
    remaining_paths = path_info[1:]

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
                f"Iteration {total_iterations}: Inserted '{node.display_label()}' at position {best_insertion_idx}"
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
            f"Final path order: {[node.display_label() for node, _, _ in optimized_paths]}"
        )

    return optimized_paths


def _calculate_total_travel_distance(path_info, channel=None):
    """
    Calculate total travel distance for a sequence of paths.

    Args:
        path_info: List of (node, geomstr, info) tuples
        channel: Channel for debug output (optional)

    Returns:
        Total travel distance
    """
    if len(path_info) <= 1:
        return 0.0

    total_distance = 0.0

    for i in range(len(path_info) - 1):
        current_node, current_geom, current_info = path_info[i]
        next_node, next_geom, next_info = path_info[i + 1]

        # Calculate distance between end of current path and start of next path
        distance = _calculate_path_to_path_distance_optimized(current_info, next_info)
        total_distance += distance

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
    Optimized version with orientation pruning.

    Args:
        current_info: Path info for current path
        next_info: Path info for next path

    Returns:
        Minimum distance between path end and next path start
    """
    min_distance = float("inf")

    # Get possible end points from current path
    current_end_points = current_info["end_points"]

    # Get possible start points from next path
    next_start_points = next_info["start_points"]

    # If either path has no points, return 0
    if not current_end_points or not next_start_points:
        return 0.0

    # For efficiency, limit the number of orientations we check
    max_orientations = min(4, len(current_end_points), len(next_start_points))

    # Use only the most promising orientations (first few)
    current_ends = current_end_points[:max_orientations]
    next_starts = next_start_points[:max_orientations]

    # Calculate distances for all combinations
    for end_point in current_ends:
        for start_point in next_starts:
            # Calculate Euclidean distance
            distance = abs(end_point - start_point)
            if distance < min_distance:
                min_distance = distance

    return min_distance


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


def _optimize_path_order_greedy_optimized(
    path_info, channel=None, max_iterations=None
):
    """
    Optimized greedy path optimization algorithm that maintains result integrity with the original.

    Args:
        path_info: List of (node, geomstr, info) tuples
        channel: Channel for debug output
        max_iterations: Maximum number of optimization iterations (None = no limit)

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

    # Pre-calculate distance matrix (same as original for result integrity)
    distance_matrix = np.zeros((n_paths, n_paths, max_end_points, max_start_points))

    if channel:
        channel("  Pre-calculating distance matrix...")

    for i, j in itertools.product(range(n_paths), repeat=2):
        if i != j:
            info_i = path_info[i][2]
            info_j = path_info[j][2]

            # Calculate distances between all combinations of end/start points
            n_end_points = len(info_i["end_points"])
            n_start_points = len(info_j["start_points"])

            for end_idx in range(n_end_points):
                for start_idx in range(n_start_points):
                    end_pt = info_i["end_points"][end_idx]
                    start_pt = info_j["start_points"][start_idx]
                    distance_matrix[i, j, end_idx, start_idx] = abs(end_pt - start_pt)

    # Start with the first path
    ordered_indices = [0]
    used = {0}
    orientation_choices = [(0, 0)]  # (path_idx, orientation_idx) for each ordered path

    if channel:
        channel(
            f"  Starting with path 0: {display_label(path_info[0][0]) or 'Unknown'}"
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

            # Find the best orientation combination for this candidate
            for end_ori in range(len(current_end_points)):
                for start_ori in range(len(candidate_start_points)):
                    distance = distance_matrix[
                        current_path_idx, candidate_idx, end_ori, start_ori
                    ]

                    if distance < best_distance:
                        best_distance = distance
                        best_idx = candidate_idx
                        best_end_ori = end_ori
                        best_start_ori = start_ori

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


def _calculate_path_to_path_distance_optimized(current_info, next_info):
    """
    Calculate the travel distance from the end of one path to the start of another.
    Optimized version with orientation pruning.

    Args:
        current_info: Path info for current path
        next_info: Path info for next path

    Returns:
        Minimum distance between path end and next path start
    """
    min_distance = float("inf")

    # Get possible end points from current path
    current_end_points = current_info["end_points"]

    # Get possible start points from next path
    next_start_points = next_info["start_points"]

    # If either path has no points, return 0
    if not current_end_points or not next_start_points:
        return 0.0

    # For efficiency, limit the number of orientations we check
    max_orientations = min(4, len(current_end_points), len(next_start_points))

    # Use only the most promising orientations (first few)
    current_ends = current_end_points[:max_orientations]
    next_starts = next_start_points[:max_orientations]

    # Calculate distances for all combinations
    for end_point in current_ends:
        for start_point in next_starts:
            # Calculate Euclidean distance
            distance = abs(end_point - start_point)
            if distance < min_distance:
                min_distance = distance

    return min_distance


def _calculate_total_travel_distance_optimized(
    path_info, distance_cache, cache_stats=None
):
    """
    Calculate total travel distance with distance caching for optimization.

    Args:
        path_info: List of (node, geomstr, info) tuples
        distance_cache: Dictionary for caching distances
        cache_stats: Dictionary to track cache hits/misses (optional)

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
            if cache_stats is not None:
                cache_stats["hits"] = cache_stats.get("hits", 0) + 1
        else:
            # Calculate distance between end of current path and start of next path
            distance = _calculate_path_to_path_distance_optimized(
                current_info, next_info
            )
            distance_cache[cache_key] = distance
            if cache_stats is not None:
                cache_stats["misses"] = cache_stats.get("misses", 0) + 1

        total_distance += distance

    return total_distance
