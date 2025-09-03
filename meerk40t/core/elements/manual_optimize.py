
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
    @self.console_command(
        "reorder",
        help=_("reorder elements for optimal cutting within an operation"),
        input_type=("operations", None),
        output_type="operations",
    )
    def element_reorder(channel, _, data=None, post=None, **kwargs):
        oplist = data if data is not None else list(self.ops(selected=True))
        opout = []
        for op in oplist:
            if op.type in op_burnable_nodes:
                optimize_node_travel_under(op, channel)
                opout.append(op)
        self.signal("rebuild_tree")
        return "operations", opout
    
    def optimize_node_travel_under(op, channel, leading=""):
        node_list = []
        child_list = []
        for child in op.children:
            channel(f"{leading}{display_label(child)}")
            if child.type.startswith("effect"):
                # We reorder the children of the effect, not the effect itself
                optimize_node_travel_under(child, channel, leading =f"{leading}  ")
            elif child.type == "reference":
                channel(f"{leading}Reference to {display_label(child.node) if child.node else 'None!!!'}")
                node_list.append(child.node)
                child_list.append(child)
            else:
                channel(f"{leading}Don't know how to handle {child.type} in reorder for {display_label(op)}")
        channel(f"{leading}Nodes:")
        channel(f"{leading}  " + " ".join([str(display_label(n)) for n in node_list if n is not None]))
        channel(f"{leading}Children:")
        channel(f"{leading}  " + ", ".join([str(display_label(n)) for n in child_list if n is not None]))
        if len(node_list) > 1:
            ordered_nodes = optimize_path_order(node_list, channel)
            if ordered_nodes != node_list:
                # Clear old children
                for child in child_list:
                    child.remove_node()
                # Rebuild children in new order
                for node in ordered_nodes:
                    op.add_reference(node)
        else:
            channel(f"No need to reorder {op.display_label()}")

    def optimize_path_order(node_list, channel=None):
        if len(node_list) < 2:
            return node_list

        if channel:
            channel(f"Starting path optimization for {len(node_list)} nodes")

        # Separate nodes with and without as_geometry attribute
        geomstr_nodes = []
        non_geomstr_nodes = []

        for idx, node in enumerate(node_list):
            if hasattr(node, 'as_geometry') and callable(getattr(node, 'as_geometry')):
                try:
                    geomstr = node.as_geometry()
                    # create_dump_of(f"geom{idx+1}", geomstr)
                    if geomstr and geomstr.index > 0:
                        geomstr_nodes.append((node, geomstr))
                        if channel:
                            channel(f"  Node {display_label(node) or 'Unknown'}: {geomstr.index} segments")
                    else:
                        non_geomstr_nodes.append(node)
                        if channel:
                            channel(f"  Node {display_label(node) or 'Unknown'}: Empty geometry")
                except Exception as e:
                    non_geomstr_nodes.append(node)
                    if channel:
                        channel(f"  Node {display_label(node) or 'Unknown'}: Error extracting geometry - {e}")
            else:
                non_geomstr_nodes.append(node)
                if channel:
                    channel(f"  Node {display_label(node) or 'Unknown'}: No as_geometry method")

        if channel:
            channel(f"Found {len(geomstr_nodes)} geomstr nodes and {len(non_geomstr_nodes)} non-geomstr nodes")

        if len(geomstr_nodes) < 2:
            # Not enough geomstr nodes to optimize, return original order
            if channel:
                channel("Not enough geomstr nodes to optimize, returning original order")
            return node_list
        
        # Extract path information for each geomstr node
        path_info = []
        for node, geomstr in geomstr_nodes:
            if channel:
                channel(f"Extracting path info for node {display_label(node) or 'Unknown'}")
            info = _extract_path_info(geomstr, channel)
            path_info.append((node, geomstr, info))
        
        # Calculate original travel distance
        original_distance = _calculate_total_travel_distance(path_info, channel)
        
        # Optimize the order using greedy nearest neighbor with improvements
        ordered_path_info = _optimize_path_order_greedy(path_info, channel)
        
        # Calculate optimized travel distance
        optimized_distance = _calculate_total_travel_distance(ordered_path_info, channel)
        
        # Report results to channel if available
        if channel:
            improvement = original_distance - optimized_distance
            improvement_percent = (improvement / original_distance * 100) if original_distance > 0 else 0
            channel(f"Path optimization for {len(geomstr_nodes)} paths:")
            channel(f"  Original travel distance: {Length(original_distance).length_mm}")
            channel(f"  Optimized travel distance: {Length(optimized_distance).length_mm}")
            channel(f"  Distance saved: {Length(improvement).length_mm}  ({improvement_percent:.1f}%)")
        
        # Reconstruct the ordered node list
        ordered_nodes = [node for node, _, _ in ordered_path_info] + non_geomstr_nodes
        
        return ordered_nodes

def display_label(node):
    return f"{node.type}.{node.id if node.id is not None else '-'}.{node.label if node.label is not None else '-'}"

def _extract_path_info(geomstr, channel=None):
    """
    Extract start and end points from a geomstr, considering different orientations.
    
    Returns:
        dict with 'start_points', 'end_points', and 'is_closed' keys
    """
    if geomstr.index == 0:
        if channel:
            channel("  Empty geomstr, no path information")
        return {'start_points': [], 'end_points': [], 'is_closed': False, 'segments': []}
    
    segments = geomstr.segments[:geomstr.index]
    if channel:
        channel(f"  Extracting path info from {len(segments)} segments")
    
    # Extract start and end points for forward direction
    start_point = segments[0][0]  # First segment start
    end_point = segments[-1][4]   # Last segment end
    
    # For closed paths, we can start at any segment
    is_closed = geomstr.is_closed() if hasattr(geomstr, 'is_closed') else False
    if channel:
        channel(f"  Path is {'closed' if is_closed else 'open'}")
    
    result = {
        'start_points': [start_point],
        'end_points': [end_point],
        'is_closed': is_closed,
        'segments': segments
    }
    
    # Add reversed orientation
    if len(segments) > 1:
        reversed_start = segments[-1][4]  # Last segment end becomes start
        reversed_end = segments[0][0]     # First segment start becomes end
        result['start_points'].append(reversed_start)
        result['end_points'].append(reversed_end)
    
    # If closed, add alternative start/end points for different starting segments
    if is_closed and len(segments) > 1:
        # Use improved candidate selection for closed paths
        max_alternatives = min(len(segments), 8)  # Limit to avoid excessive computation
        candidate_indices = _select_closed_path_candidates(segments, max_alternatives, channel)
        result['candidate_indices'] = candidate_indices  # Store for later use
        for segment_idx in candidate_indices:
            alt_start = segments[segment_idx][0]
            # For closed paths, the end point when starting at segment i would be the end of segment i-1
            alt_end = segments[segment_idx-1][4] if segment_idx > 0 else segments[-1][4]
            result['start_points'].append(alt_start)
            result['end_points'].append(alt_end)
    
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
                current_length += segment_lengths[i-1]
                if current_length >= target_length * len(candidates) and len(candidates) < max_candidates:
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


def _optimize_path_order_greedy(path_info, channel=None):
    """
    Optimize path order using greedy nearest neighbor algorithm with improvements.
    
    Args:
        path_info: List of (node, geomstr, info) tuples
        channel: Channel for debug output
        
    Returns:
        Ordered list of (node, geomstr, info) tuples
    """
    if len(path_info) < 2:
        return path_info
    
    if channel:
        channel(f"Starting greedy optimization for {len(path_info)} paths")
    
    # Pre-calculate all pairwise distances
    n_paths = len(path_info)
    
    # Calculate maximum number of orientations (start/end point combinations)
    max_end_points = max(len(info['end_points']) for _, _, info in path_info) if path_info else 1
    max_start_points = max(len(info['start_points']) for _, _, info in path_info) if path_info else 1
    
    if channel:
        channel(f"  Maximum orientations: {max_end_points} end points, {max_start_points} start points")
    
    distance_matrix = np.zeros((n_paths, n_paths, max_end_points, max_start_points))  # [from_idx, to_idx, from_orientation, to_orientation]
    
    if channel:
        channel("  Pre-calculating distance matrix...")
    
    for i, j in itertools.product(range(n_paths), repeat=2):
        if i != j:
            info_i = path_info[i][2]
            info_j = path_info[j][2]
            
            # Calculate distances between all combinations of end/start points
            n_end_points = len(info_i['end_points'])
            n_start_points = len(info_j['start_points'])
            
            for end_idx in range(n_end_points):
                for start_idx in range(n_start_points):
                    end_pt = info_i['end_points'][end_idx]
                    start_pt = info_j['start_points'][start_idx]
                    distance_matrix[i, j, end_idx, start_idx] = abs(end_pt - start_pt)
    
    # Start with the first path
    ordered_indices = [0]
    used = {0}
    orientation_choices = [(0, 0)]  # (path_idx, orientation_idx) for each ordered path
    
    if channel:
        channel(f"  Starting with path 0: {display_label(path_info[0][0]) or 'Unknown'}")
    
    # Greedily add the closest unused path
    while len(ordered_indices) < n_paths:
        best_distance = float('inf')
        best_idx = -1
        best_start_ori = 0
        
        current_path_idx = ordered_indices[-1]
        current_end_points = path_info[current_path_idx][2]['end_points']
        
        if channel:
            channel(f"  Finding next path after {display_label(path_info[current_path_idx][0])}")
        
        for candidate_idx in range(n_paths):
            if candidate_idx in used:
                continue
                
            candidate_start_points = path_info[candidate_idx][2]['start_points']
            
            # Find the best orientation combination
            for end_ori, start_ori in itertools.product(range(len(current_end_points)), range(len(candidate_start_points))):
                distance = distance_matrix[current_path_idx, candidate_idx, end_ori, start_ori]
                if distance < best_distance:
                    best_distance = distance
                    best_idx = candidate_idx
                    best_start_ori = start_ori
        
        if best_idx == -1:
            # No more candidates, add remaining paths in original order
            if channel:
                channel("  No more candidates found, adding remaining paths in original order")
            for i in range(n_paths):
                if i not in used:
                    ordered_indices.append(i)
                    used.add(i)
                    orientation_choices.append((i, 0))  # Default orientation
            break
            
        ordered_indices.append(best_idx)
        used.add(best_idx)
        orientation_choices.append((best_idx, best_start_ori))
        
        if channel:
            channel(f"  Added path {best_idx}: {display_label(path_info[best_idx][0])} (distance: {Length(best_distance).length_mm}, orientation: {best_start_ori})")
    
    if channel:
        channel(f"  Optimization complete. Final order: {[display_label(path_info[i][0]) for i in ordered_indices]}")
    
    # Reconstruct ordered path_info with optimal orientations
    ordered_path_info = []
    for path_idx, orientation_idx in orientation_choices:
        node, original_geomstr, info = path_info[path_idx]
        
        # Apply orientation transformation if needed
        if orientation_idx == 0 or orientation_idx >= len(info['start_points']):
            # Original orientation or invalid orientation index
            final_geomstr = original_geomstr
            if channel:
                channel(f"  Node {display_label(node) or 'Unknown'}: Using original orientation (idx={orientation_idx}, available={len(info['start_points'])})")
        elif orientation_idx == 1 and len(info['start_points']) > 1:
            # Reversed orientation - use reversed start point
            final_geomstr = _reverse_geomstr(original_geomstr, channel)
            # Reassign the changed geometry to the node
            if hasattr(node, 'geometry'):
                node.geometry = final_geomstr
                if channel:
                    channel(f"  Node {display_label(node) or 'Unknown'}: Applied reversed geometry")
        elif info['is_closed'] and orientation_idx >= 2 and len(info['start_points']) > orientation_idx:
            # Closed path with different starting segment
            candidate_idx = orientation_idx - 2  # Adjust for the first two being forward/reverse
            if 'candidate_indices' in info and candidate_idx < len(info['candidate_indices']):
                start_segment_idx = info['candidate_indices'][candidate_idx]
                final_geomstr = _reshuffle_closed_geomstr(original_geomstr, start_segment_idx, channel)
                # Reassign the changed geometry to the node
                if hasattr(node, 'geometry'):
                    node.geometry = final_geomstr
                    if channel:
                        channel(f"  Node {display_label(node) or 'Unknown'}: Applied reshuffled geometry, starting at segment {start_segment_idx}")
            else:
                final_geomstr = original_geomstr
                if channel:
                    channel(f"  Node {display_label(node) or 'Unknown'}: Fallback to original (invalid candidate index)")
        else:
            # Fallback to original
            final_geomstr = original_geomstr
            if channel:
                channel(f"  Node {display_label(node) or 'Unknown'}: Fallback to original orientation (orientation_idx={orientation_idx}, available={len(info['start_points'])})")
        
        ordered_path_info.append((node, final_geomstr, info))
    
    return ordered_path_info


def _calculate_total_travel_distance(path_info, channel=None):
    """
    Calculate the total travel distance for a sequence of paths.

    Args:
        path_info: List of (node, geomstr, info) tuples in order
        channel: Channel for debug output

    Returns:
        Total travel distance as float
    """
    if len(path_info) < 2:
        if channel:
            channel("  No travel distance to calculate (less than 2 paths)")
        return 0.0

    total_distance = 0.0

    if channel:
        channel(f"  Calculating travel distance for {len(path_info)} paths")

    for i in range(len(path_info) - 1):
        current_node, current_geomstr, current_info = path_info[i]
        next_node, next_geomstr, next_info = path_info[i + 1]

        # Use the actual current geometry's end point, not the cached info
        if current_geomstr.index > 0:
            current_end = current_geomstr.segments[current_geomstr.index - 1][4]  # Last segment end
        else:
            current_end = current_info['end_points'][0] if current_info['end_points'] else 0j

        # Use the actual next geometry's start point, not the cached info
        if next_geomstr.index > 0:
            next_start = next_geomstr.segments[0][0]  # First segment start
        else:
            next_start = next_info['start_points'][0] if next_info['start_points'] else 0j

        # Calculate distance between end of current and start of next
        distance = abs(current_end - next_start)
        total_distance += distance

        if channel:
            current_label = display_label(current_node)
            next_label = display_label(next_node)
            channel(f"    {current_label} -> {next_label}: {distance:.8f}mm")

    if channel:
        channel(f"  Total travel distance: {total_distance:.8f}mm")

    return total_distance


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
    segments = geomstr.segments[:geomstr.index]
    
    for segment in reversed(segments):
        start, c0, info, c1, end = segment
        # Reverse the segment: end becomes start, start becomes end
        # For Bezier curves, we need to reverse the control points
        reversed_segment = (end, c1, info, c0, start)
        reversed_geomstr.append_segment(*reversed_segment)
    
    if channel:
        channel(f"  Reversed geomstr created with {reversed_geomstr.index} segments")
    
    return reversed_geomstr


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
    
    segments = geomstr.segments[:geomstr.index]
    reshuffled_geomstr = Geomstr()
    
    # Add segments from start_segment_idx to end
    for i in range(start_segment_idx, len(segments)):
        reshuffled_geomstr.append_segment(*segments[i])
    
    # Add segments from beginning to start_segment_idx
    for i in range(start_segment_idx):
        reshuffled_geomstr.append_segment(*segments[i])
    
    if channel:
        channel(f"  Reshuffled geomstr created with {reshuffled_geomstr.index} segments")
    
    return reshuffled_geomstr

# Routine to recreate the goemetries for testing
# def create_dump_of(gname, geomstr):
#     indentation = " "*4
#     print (f"{indentation}{gname} = Geomstr()")
#     last = None
#     for point in geomstr.as_points():
#         if last is not None:
#             print(f"{indentation}{gname}.line({last.real}+{last.imag}j, {point.real}+{point.imag}j)")   
#         last = point
