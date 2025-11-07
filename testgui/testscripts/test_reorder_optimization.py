#!/usr/bin/env python3

import sys
import os
import time
# Add the meerk40t module to path
def find_meerk40t_path(start_path=None, max_levels=10):
    """
    Find the meerk40t package path by looking for meerk40t.py file.
    Traverses up the directory tree until found or max_levels reached.

    Args:
        start_path: Starting directory path (defaults to script directory)
        max_levels: Maximum directory levels to traverse up

    Returns:
        str: Path to meerk40t directory containing meerk40t.py, or None if not found
    """
    if start_path is None:
        start_path = os.path.dirname(os.path.abspath(__file__))

    current_path = start_path
    levels_traversed = 0

    while levels_traversed < max_levels:
        # Check if meerk40t.py exists in current directory
        meerk40t_py_path = os.path.join(current_path, "meerk40t.py")
        if os.path.isfile(meerk40t_py_path):
            return current_path

        # Move up one directory level
        parent_path = os.path.dirname(current_path)

        # If we've reached the root directory, stop
        if parent_path == current_path:
            break

        current_path = parent_path
        levels_traversed += 1

    return None


# Find and add meerk40t path
meerk40t_path = find_meerk40t_path()
if meerk40t_path:
    sys.path.insert(0, meerk40t_path)
else:
    print(
        "Warning: Could not find meerk40t.py in directory tree. Using system-installed version."
    )
    print(
        "This may cause import errors if the local development version has different constants."
    )


from meerk40t.core.elements.manual_optimize import _optimize_path_order_greedy, _calculate_total_travel_distance
from meerk40t.core.geomstr import Geomstr

def create_test_channel():
    """Create a mock channel for debugging output"""
    messages = []
    def channel(msg):
        messages.append(msg)
        print(f"DEBUG: {msg}")
    return channel, messages

class MockNode:
    def __init__(self, label, geometry):
        self.type = "elem path"
        self.id = str(id(self))
        self.label = label
        self.geometry = geometry

    def display_label(self):
        return self.label

def create_very_complex_test_case():
    """Create a very complex test case with many paths at different positions including arcs and quads"""

    paths = []
    geom1 = Geomstr()
    geom1.line(38702.552624287855+103206.80699810138j, 103206.80699810055+64504.254373813375j)
    geom1.line(103206.80699810055+64504.254373813375j, 103206.80699810102+129008.50874762674j)
    geom1.line(103206.80699810102+129008.50874762674j, 206413.61399620245+64504.254373813375j)
    geom1.line(206413.61399620245+64504.254373813375j, 245116.16662049064+129008.50874762674j)
    geom2 = Geomstr()
    geom2.line(122558.08331024574+206413.61399620285j, 83855.53068595704+154810.2104971521j)
    geom3 = Geomstr()
    geom3.line(116111.88710957504+77402.56790808897j, 158044.23398766498+108541.20529536426j)
    geom3.line(158044.23398766498+108541.20529536426j, 176838.12520067958+59810.04374380972j)
    geom3.line(176838.12520067958+59810.04374380972j, 184470.43037637533+111479.03222616173j)
    geom3.line(184470.43037637533+111479.03222616173j, 232217.85308666877+90310.18535961187j)
    geom3.line(232217.85308666877+90310.18535961187j, 201079.21569959348+132242.53223850185j)
    geom3.line(201079.21569959348+132242.53223850185j, 249810.377250548+151036.42345151646j)
    geom3.line(249810.377250548+151036.42345151646j, 198141.38876879602+158668.72862721217j)
    geom3.line(198141.38876879602+158668.72862721217j, 219310.23563454585+206416.15133650563j)
    geom3.line(219310.23563454585+206416.15133650563j, 177377.8887564559+175277.51394943034j)
    geom3.line(177377.8887564559+175277.51394943034j, 158583.9975434413+224008.6755013849j)
    geom3.line(158583.9975434413+224008.6755013849j, 150951.69236674556+172339.68701863286j)
    geom3.line(150951.69236674556+172339.68701863286j, 103204.26965745211+193508.53388538273j)
    geom3.line(103204.26965745211+193508.53388538273j, 134342.90704452738+151576.18700629272j)
    geom3.line(134342.90704452738+151576.18700629272j, 85611.74549327287+132782.29579327814j)
    geom3.line(85611.74549327287+132782.29579327814j, 137280.73397532487+125149.9906175824j)
    geom3.line(137280.73397532487+125149.9906175824j, 116111.88710957504+77402.56790808897j)

    # Add some paths with arcs and quads
    geom4 = Geomstr()
    # Create a complex shape with mixed segments
    geom4.line(50000+50000j, 60000+50000j)
    geom4.arc(60000+50000j, 65000+55000j, 70000+60000j)
    geom4.quad(70000+60000j, 75000+65000j, 80000+60000j)
    geom4.line(80000+60000j, 75000+55000j)
    geom4.arc(75000+55000j, 70000+50000j, 65000+55000j)
    geom4.line(65000+55000j, 50000+50000j)

    geom5 = Geomstr()
    # Create a flower-like shape with arcs
    center_x, center_y = 100000, 100000
    radius = 10000
    for i in range(6):
        start = complex(center_x + radius * 0.7, center_y + radius * 0.7)
        control = complex(center_x + radius * 1.2, center_y)
        end = complex(center_x + radius * 0.7, center_y + radius * 0.7)
        geom5.arc(start, control, end)

    paths = [
        (MockNode("Polyline_107", geom1), geom1),
        (MockNode("Polyline_478", geom2), geom2),
        (MockNode("Polyline_316", geom3), geom3),
        (MockNode("Mixed_Shape", geom4), geom4),
        (MockNode("Flower_Arcs", geom5), geom5),
    ]

    return paths

def create_complex_test_case():
    """Create a more complex test case with multiple paths at different positions including arcs and quads"""

    # Create mock node objects

    paths = []

    # Path 1: Rectangle with arc corners at (0,0)
    geom1 = Geomstr()
    geom1.line(0+0j, 1.5+0j)   # bottom left
    geom1.arc(1.5+0j, 2+0.5j, 2+1j)  # bottom right arc
    geom1.line(2+1j, 2+2j)   # right side
    geom1.arc(2+2j, 1.5+2j, 1+2j)  # top right arc
    geom1.line(1+2j, 0+2j)   # top side
    geom1.arc(0+2j, 0.5+1.5j, 0+1j)  # top left arc
    geom1.line(0+1j, 0+0j)   # left side

    # Path 2: Triangle with quadratic curves at (5,0) - far from path 1
    geom2 = Geomstr()
    geom2.line(5+0j, 7+0j)   # bottom
    geom2.quad(7+0j, 7.5+1j, 6+2j)   # right side with curve
    geom2.line(6+2j, 5+0j)   # left side (closes)

    # Path 3: Small square with arc at (1,3) - close to path 1
    geom3 = Geomstr()
    geom3.line(1+3j, 1.8+3j)   # bottom left
    geom3.arc(1.8+3j, 2+3.2j, 2+3.8j)  # bottom right arc
    geom3.line(2+3.8j, 2+4j)   # right
    geom3.line(2+4j, 1+4j)   # top
    geom3.line(1+4j, 1+3j)   # left (closes)

    # Path 4: Large L-shape with quadratic curves at (8,1)
    geom4 = Geomstr()
    geom4.line(8+1j, 10+1j)  # bottom long
    geom4.quad(10+1j, 10.5+2j, 10+3j) # right tall with curve
    geom4.line(10+3j, 9+3j)  # top short
    geom4.line(9+3j, 9+2j)   # left down
    geom4.line(9+2j, 8+2j)   # left bottom
    geom4.line(8+2j, 8+1j)   # left up (closes)

    # Path 5: Circle approximation with arcs at (3,5)
    geom5 = Geomstr()
    geom5.arc(3+5j, 3.5+5.5j, 4+6j)   # top right arc
    geom5.arc(4+6j, 3.5+6.5j, 3+7j)   # top left arc
    geom5.arc(3+7j, 2.5+6.5j, 2+6j)   # bottom left arc
    geom5.arc(2+6j, 2.5+5.5j, 3+5j)   # bottom right arc (closes)

    # Path 6: Star shape with mixed lines and arcs at (12,8)
    geom6 = Geomstr()
    geom6.line(12+8j, 13+10j)  # top point
    geom6.arc(13+10j, 12.5+10.5j, 12+11j)  # top right arc
    geom6.line(12+11j, 10+10j)  # right point
    geom6.arc(10+10j, 9.5+9.5j, 11+8j)  # bottom right arc
    geom6.line(11+8j, 13+7j)  # bottom right point
    geom6.arc(13+7j, 13.5+7.5j, 14+8j)  # bottom arc
    geom6.line(14+8j, 12+9j)  # bottom left point
    geom6.arc(12+9j, 12.5+8.5j, 12+8j)  # left arc (closes)

    # Path 7: Wave shape with quadratic curves at (6,12)
    geom7 = Geomstr()
    geom7.line(6+12j, 7+12j)  # start
    geom7.quad(7+12j, 7.5+13j, 8+12j)  # first wave up
    geom7.quad(8+12j, 8.5+11j, 9+12j)  # first wave down
    geom7.quad(9+12j, 9.5+13j, 10+12j) # second wave up
    geom7.quad(10+12j, 10.5+11j, 11+12j) # second wave down
    geom7.line(11+12j, 6+12j)  # back to start (closes)

    paths = [
        (MockNode("Rectangle_with_arcs_0_0", geom1), geom1),
        (MockNode("Triangle_with_quad_5_0", geom2), geom2),
        (MockNode("Square_with_arc_1_3", geom3), geom3),
        (MockNode("L_Shape_with_quad_8_1", geom4), geom4),
        (MockNode("Circle_with_arcs_3_5", geom5), geom5),
        (MockNode("Star_mixed_12_8", geom6), geom6),
        (MockNode("Wave_with_quads_6_12", geom7), geom7),
    ]

    return paths

def create_large_scale_polyline_test_case():
    """Create a large scale test case with approximately 500 polylines for performance testing"""
    import random
    import math

    paths = []
    random.seed(42)  # For reproducible results

    # Generate 500 random polylines
    for i in range(500):
        # Random position in a large area
        center_x = random.uniform(0, 100000)
        center_y = random.uniform(0, 100000)

        # Create a polyline with 3-8 segments (mix of lines, arcs, and quads)
        geom = Geomstr()
        num_segments = random.randint(3, 8)

        # Start point
        x = center_x + random.uniform(-1000, 1000)
        y = center_y + random.uniform(-1000, 1000)

        for j in range(num_segments):
            # Random direction and length for each segment
            angle = random.uniform(0, 2 * math.pi)
            length = random.uniform(500, 2000)

            next_x = x + length * math.cos(angle)
            next_y = y + length * math.sin(angle)

            # Randomly choose segment type
            segment_type = random.choice(['line', 'arc', 'quad'])

            if segment_type == 'line':
                geom.line(complex(x, y), complex(next_x, next_y))
            elif segment_type == 'arc':
                # Create arc with control point
                control_x = (x + next_x) / 2 + random.uniform(-500, 500)
                control_y = (y + next_y) / 2 + random.uniform(-500, 500)
                geom.arc(complex(x, y), complex(control_x, control_y), complex(next_x, next_y))
            elif segment_type == 'quad':
                # Create quadratic curve with control point
                control_x = (x + next_x) / 2 + random.uniform(-500, 500)
                control_y = (y + next_y) / 2 + random.uniform(-500, 500)
                geom.quad(complex(x, y), complex(control_x, control_y), complex(next_x, next_y))

            x, y = next_x, next_y

        paths.append((MockNode(f"Polyline_{i}", geom), geom))

    return paths

def test_path_optimization(header, testcase_func):
    """Test path optimization with complex geometries and measure actual distance improvements"""

    print("=" * 60)
    print(f"PATH OPTIMIZATION TEST: {header}")
    print("=" * 60)

    # Create test data
    paths = testcase_func()
    channel, messages = create_test_channel()

    # Extract path information
    from meerk40t.core.elements.manual_optimize import _extract_path_info

    path_info = []
    for node, geom in paths:
        info = _extract_path_info(geom, channel)
        path_info.append((node, geom, info))
        print(f"Path: {node.display_label()} - {len(info['start_points'])} start points, {len(info['end_points'])} end points, {'closed' if info['is_closed'] else 'open'}")

    print(f"\nOriginal order: {[node.display_label() for node, _, _ in path_info]}")

    # Calculate original travel distance
    original_distance = _calculate_total_travel_distance(path_info, channel)
    print(f"Original travel distance: {original_distance:.3f}mm")

    # Run optimization
    print("\n" + "="*40)
    print("RUNNING OPTIMIZATION...")
    print("="*40)

    start_time = time.time()
    optimized_path_info = _optimize_path_order_greedy(path_info, channel)
    end_time = time.time()
    optimization_time = end_time - start_time

    # Calculate optimized travel distance
    optimized_distance = _calculate_total_travel_distance(optimized_path_info, channel)

    print(f"\nOptimized order: {[node.display_label() for node, _, _ in optimized_path_info]}")
    print(f"Optimized travel distance: {optimized_distance:.3f}mm")
    print(f"Optimization time: {optimization_time:.3f} seconds")

    # Calculate improvement
    if original_distance > 0:
        improvement = original_distance - optimized_distance
        improvement_percent = (improvement / original_distance) * 100
        print(f"Distance improvement: {improvement:.3f}mm ({improvement_percent:.1f}%)")

        if improvement > 0:
            print("SUCCESS: Travel distance reduced!")
        elif improvement < 0:
            print("WARNING: Travel distance increased!")
        else:
            print("INFO: No change in travel distance")
    else:
        print("INFO: No travel distance to optimize (single path or empty)")

    return optimized_path_info, original_distance, optimized_distance, optimization_time

def test_edge_cases():
    """Test edge cases that might cause issues"""

    print("\n" + "=" * 60)
    print("EDGE CASE TESTS")
    print("=" * 60)

    channel, _ = create_test_channel()

    # Test 1: Single path with mixed segments
    print("\nTest 1: Single path")
    geom = Geomstr()
    geom.line(0+0j, 1+0j)
    geom.arc(1+0j, 1.5+0.5j, 1+1j)
    geom.quad(1+1j, 0.5+1j, 0+1j)
    geom.line(0+1j, 0+0j)

    from meerk40t.core.elements.manual_optimize import _extract_path_info
    info = _extract_path_info(geom, channel)
    path_info = [(MockNode("Mixed_Path", geom), geom, info)]

    result = _optimize_path_order_greedy(path_info, channel)
    print(f"Mixed path test: {'PASS' if len(result) == 1 else 'FAIL'}")

    # Test 2: Empty paths
    print("\nTest 2: Empty geometry")
    empty_geom = Geomstr()
    info = _extract_path_info(empty_geom, channel)
    path_info = [(MockNode("Empty_Path", empty_geom), empty_geom, info)]

    result = _optimize_path_order_greedy(path_info, channel)
    print(f"Empty path test: {'PASS' if len(result) == 1 else 'FAIL'}")

if __name__ == "__main__":
    try:
        # Run complex test
        optimized_paths_1, orig_dist_1, opt_dist_1, time_1 = test_path_optimization("Complex", create_complex_test_case )
        optimized_paths_2, orig_dist_2, opt_dist_2, time_2 = test_path_optimization("Really Complex", create_very_complex_test_case)
        optimized_paths_3, orig_dist_3, opt_dist_3, time_3 = test_path_optimization("Large Scale (500 polylines)", create_large_scale_polyline_test_case)

        # Run edge case tests
        test_edge_cases()

        print("\n" + "=" * 60)
        print("TEST SUMMARY - complex test 1")
        print("=" * 60)
        print(f"Original distance: {orig_dist_1:.3f}")
        print(f"Optimized distance: {opt_dist_1:.3f}")
        print(f"Optimization time: {time_1:.3f} seconds")

        def summary(orig_dist, opt_dist, opt_time):
            if orig_dist > 0:
                improvement = orig_dist - opt_dist
                percent = (improvement / orig_dist) * 100
                print(f"Improvement: {improvement:.3f}mm ({percent:.1f}%)")
                print(f"Runtime: {opt_time:.3f} seconds")
                print("SUCCESS" if improvement > 0 else "DISTANCE INCREASED")
            else:
                print("SUCCESS (no optimization needed)")

        summary(orig_dist_1, opt_dist_1, time_1)
        print("\n" + "=" * 60)
        print("TEST SUMMARY - complex test 2")
        summary(orig_dist_2, opt_dist_2, time_2)
        print("\n" + "=" * 60)
        print("TEST SUMMARY - large scale test (500 polylines)")
        summary(orig_dist_3, opt_dist_3, time_3)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        traceback.print_exc()
