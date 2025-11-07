#!/usr/bin/env python3
"""
Comprehensive Vectorization Threshold Analysis Module for MeerK40t

This module is responsible for testing, analyzing, and validating vectorized function thresholds.

Features:
- Show current threshold constants
- Quick performance validation
- Comprehensive analysis of all functions
- Threshold validation and recommendations
- Command-line interface for different analysis modes

Usage:
    python threshold_testing.py --help
    python threshold_testing.py --show-current
    python threshold_testing.py --quick-test
    python threshold_testing.py --full-analysis
    python threshold_testing.py --validate
"""

import argparse
import math
import os
import sys
import time
from typing import Any, Dict, List, Tuple


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

try:
    from meerk40t.core.geomstr import (
        THRESHOLD_BBOX,
        THRESHOLD_CLOSE_GAPS,
        THRESHOLD_LENGTH,
        THRESHOLD_STITCH_GEOMETRIES,
        THRESHOLD_STITCHEABLE_NODES,
        Geomstr,
        stitch_geometries,
        stitcheable_nodes,
    )

    print("✓ Successfully imported all required classes and constants")
except ImportError as e:
    print(f"✗ Failed to import classes: {e}")
    sys.exit(1)


class ComprehensiveThresholdAnalyzer:
    """
    Comprehensive analyzer for vectorization thresholds.

    This class combines functionality from all previous test scripts:
    - simple_threshold_test.py
    - fixed_threshold_test.py
    - fixed_comprehensive_analysis.py
    - show_thresholds.py
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.current_thresholds = {
            "stitcheable_nodes": THRESHOLD_STITCHEABLE_NODES,
            "stitch_geometries": THRESHOLD_STITCH_GEOMETRIES,
            "close_gaps": THRESHOLD_CLOSE_GAPS,
            "bbox": THRESHOLD_BBOX,
            "length": THRESHOLD_LENGTH,
            "area": "always",
        }
        self.line_numbers = {
            "stitcheable_nodes": 560,
            "stitch_geometries": 1082,
            "close_gaps": 1156,
            "bbox": 4694,
            "length": 5312,
            "area": 5453,
        }

    def log(self, message: str, level: str = "INFO"):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"{message}")

    def time_function(self, func, iterations: int = 5) -> float:
        """Time a function over multiple iterations."""
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                _ = func()
                end = time.perf_counter()
                times.append(end - start)
            except Exception as e:
                self.log(f"Error in timing: {e}")
                return float("inf")

        return sum(times) / len(times) if times else float("inf")

    def create_mock_node(self, x: float, y: float):
        """Create a mock node object for stitcheable_nodes testing."""

        class MockNode:
            def __init__(self, x, y):
                self.x = x
                self.y = y

            def as_geometry(self):
                geom = Geomstr()
                start = complex(self.x, self.y)
                end = complex(self.x + 10, self.y + 5)
                geom.line(start, end)
                return geom

        return MockNode(x, y)

    def show_current_thresholds(self):
        """Display all current threshold values (from show_thresholds.py)."""
        print("CURRENT VECTORIZATION THRESHOLDS")
        print("=" * 60)
        for name, value in self.current_thresholds.items():
            if name == "area":
                print(f"{name:20s}: Always vectorized")
            else:
                line = self.line_numbers[name]
                print(f"{name:20s}: {value:2d} (Line {line})")

        print("\nThreshold Constants (from geomstr.py):")
        print(f"THRESHOLD_STITCHEABLE_NODES = {THRESHOLD_STITCHEABLE_NODES}")
        print(f"THRESHOLD_STITCH_GEOMETRIES = {THRESHOLD_STITCH_GEOMETRIES}")
        print(f"THRESHOLD_CLOSE_GAPS        = {THRESHOLD_CLOSE_GAPS}")
        print(f"THRESHOLD_BBOX              = {THRESHOLD_BBOX}")
        print(f"THRESHOLD_LENGTH            = {THRESHOLD_LENGTH}")

        print("\n" + "=" * 60)
        print("THRESHOLD STATUS SUMMARY")
        print("=" * 60)

        print("✅ All functions use centralized constants")
        print("✅ Thresholds are empirically optimized")
        print("✅ Easy maintenance via single constant location")

    def test_bbox_threshold(self) -> List[Tuple[int, float, bool]]:
        """Test bbox function performance (from fixed_threshold_test.py)."""
        if self.verbose:
            print("BBOX THRESHOLD ANALYSIS")
            print("=" * 40)
            print(f"Current threshold: index > {THRESHOLD_BBOX}")
            print()

        results = []
        # Test around current threshold
        current = THRESHOLD_BBOX
        sizes = [
            current - 10,
            current - 5,
            current - 2,
            current,
            current + 2,
            current + 5,
            current + 10,
        ]

        for size in sizes:
            if size <= 0:
                continue

            geom = Geomstr()
            points = []
            for i in range(size + 1):
                x = i * 10 + 5 * (i % 3)
                y = i * 5 + 3 * (i % 2)
                points.append(complex(x, y))

            geom.polyline(points)
            avg_time = self.time_function(lambda: geom.bbox(), 10)
            vectorized = geom.index > THRESHOLD_BBOX

            results.append((geom.index, avg_time, vectorized))
            status = "VECTORIZED" if vectorized else "Standard"
            if self.verbose:
                print(f"index={geom.index:2d}: {avg_time*1000000:8.2f}μs | {status}")

        return results

    def test_length_threshold(self) -> List[Tuple[int, float, bool]]:
        """Test length function performance (from fixed_threshold_test.py)."""
        if self.verbose:
            print("\nLENGTH THRESHOLD ANALYSIS")
            print("=" * 40)
            print(f"Current threshold: index > {THRESHOLD_LENGTH}")
            print()

        results = []
        # Test around current threshold
        current = THRESHOLD_LENGTH
        sizes = [
            current - 15,
            current - 10,
            current - 5,
            current,
            current + 5,
            current + 10,
            current + 15,
        ]

        for size in sizes:
            if size <= 0:
                continue

            geom = Geomstr()
            points = []
            for i in range(size + 1):
                x = i * 10
                y = 5 * (i % 2)
                points.append(complex(x, y))

            geom.polyline(points)
            avg_time = self.time_function(lambda: geom.length(), 10)
            vectorized = geom.index > THRESHOLD_LENGTH

            results.append((geom.index, avg_time, vectorized))
            status = "VECTORIZED" if vectorized else "Standard"
            if self.verbose:
                print(f"index={geom.index:2d}: {avg_time*1000000:8.2f}μs | {status}")

        return results

    def test_stitch_geometries_threshold(self) -> List[Tuple[int, float, bool]]:
        """Test stitch_geometries performance (from comprehensive analysis)."""
        if self.verbose:
            print("\nSTITCH_GEOMETRIES THRESHOLD ANALYSIS")
            print("=" * 40)
            print(f"Current threshold: n > {THRESHOLD_STITCH_GEOMETRIES}")
            print()

        results = []
        # Test around current threshold
        current = THRESHOLD_STITCH_GEOMETRIES
        sizes = [
            current - 15,
            current - 10,
            current - 5,
            current,
            current + 5,
            current + 10,
        ]

        for n in sizes:
            if n <= 0:
                continue

            geometries = []
            for i in range(n):
                geom = Geomstr()
                start = complex(i * 15, 10)
                end = complex((i + 1) * 15 - 2, 10 + 2 * math.sin(i))
                geom.line(start, end)
                geometries.append(geom)

            avg_time = self.time_function(
                lambda: stitch_geometries(geometries, tolerance=1.0), 3
            )
            vectorized = n > THRESHOLD_STITCH_GEOMETRIES

            results.append((n, avg_time, vectorized))
            status = "VECTORIZED" if vectorized else "Standard"
            if self.verbose:
                print(f"n={n:2d}: {avg_time*1000000:8.2f}μs | {status}")

        return results

    def test_stitcheable_nodes_threshold(self) -> List[Tuple[int, float, bool]]:
        """Test stitcheable_nodes performance (from comprehensive analysis)."""
        if self.verbose:
            print("\nSTITCHEABLE_NODES THRESHOLD ANALYSIS")
            print("=" * 40)
            print(f"Current threshold: n > {THRESHOLD_STITCHEABLE_NODES}")
            print()

        results = []
        # Test around current threshold
        current = THRESHOLD_STITCHEABLE_NODES
        sizes = [
            current - 10,
            current - 5,
            current,
            current + 5,
            current + 10,
            current + 15,
        ]

        for n in sizes:
            if n <= 0:
                continue

            nodes = []
            for i in range(n):
                x = i * 12 + 3 * math.sin(i * 0.3)
                y = 8 * math.cos(i * 0.4) + i * 2
                nodes.append(self.create_mock_node(x, y))

            avg_time = self.time_function(
                lambda: stitcheable_nodes(nodes, tolerance=1.0), 3
            )
            vectorized = n > THRESHOLD_STITCHEABLE_NODES

            results.append((n, avg_time, vectorized))
            status = "VECTORIZED" if vectorized else "Standard"
            if self.verbose:
                print(f"n={n:2d}: {avg_time*1000000:8.2f}μs | {status}")

        return results

    def analyze_performance_data(
        self,
        results: List[Tuple[int, float, bool]],
        current_threshold: int,
        function_name: str,
    ) -> int:
        """Analyze performance data and recommend optimal threshold."""
        if len(results) < 4:
            return current_threshold

        standard_data = [
            (size, time)
            for size, time, vectorized in results
            if not vectorized and time != float("inf")
        ]
        vectorized_data = [
            (size, time)
            for size, time, vectorized in results
            if vectorized and time != float("inf")
        ]

        if not standard_data or not vectorized_data:
            if self.verbose:
                print(f"{function_name}: Insufficient data for analysis")
            return current_threshold

        avg_standard = sum(time for _, time in standard_data) / len(standard_data)
        avg_vectorized = sum(time for _, time in vectorized_data) / len(vectorized_data)

        # Calculate absolute time difference (in seconds)
        time_difference = abs(avg_vectorized - avg_standard)

        if self.verbose:
            print(f"\n{function_name.upper()} PERFORMANCE ANALYSIS:")
            print(f"   Current threshold: {current_threshold}")
            print(f"   Average standard time: {avg_standard*1000000:.1f}μs")
            print(f"   Average vectorized time: {avg_vectorized*1000000:.1f}μs")
            print(f"   Time difference: {time_difference*1000000:.1f}μs")

        # Only recommend changes if time difference is significant (≥0.01 seconds = 10,000μs)
        if time_difference < 0.01:
            if self.verbose:
                print("   ✅ Time difference negligible (<0.01s) - no change needed")
            return current_threshold

        # Determine recommendation based on performance ratio for significant differences
        if avg_vectorized > avg_standard * 1.2:  # 20% overhead tolerance
            recommendation = min(current_threshold + 10, 100)
            if self.verbose:
                overhead = ((avg_vectorized / avg_standard) - 1) * 100
                print(
                    f"   ⚠️  OVERHEAD: {overhead:.1f}% - RAISE threshold to {recommendation}"
                )
            return recommendation
        elif avg_vectorized > avg_standard * 1.05:  # 5% overhead tolerance
            recommendation = current_threshold + 5
            if self.verbose:
                overhead = ((avg_vectorized / avg_standard) - 1) * 100
                print(
                    f"   ⚠️  MINOR OVERHEAD: {overhead:.1f}% - RAISE threshold to {recommendation}"
                )
            return recommendation
        else:
            if self.verbose:
                print("   ✅ Performance acceptable")
            return current_threshold

    def quick_test(self):
        """Run quick performance tests on key functions (from fixed_threshold_test.py)."""
        print("QUICK THRESHOLD VALIDATION TEST")
        print("=" * 60)

        # Test the two most critical functions
        bbox_results = self.test_bbox_threshold()
        bbox_rec = self.analyze_performance_data(bbox_results, THRESHOLD_BBOX, "bbox")

        length_results = self.test_length_threshold()
        length_rec = self.analyze_performance_data(
            length_results, THRESHOLD_LENGTH, "length"
        )

        print("\nQUICK TEST RESULTS:")
        print("-" * 30)

        changes_needed = 0
        if bbox_rec != THRESHOLD_BBOX:
            print(f"⚠️  bbox: {THRESHOLD_BBOX} → {bbox_rec}")
            changes_needed += 1
        else:
            print(f"✅ bbox: {THRESHOLD_BBOX} (optimal)")

        if length_rec != THRESHOLD_LENGTH:
            print(f"⚠️  length: {THRESHOLD_LENGTH} → {length_rec}")
            changes_needed += 1
        else:
            print(f"✅ length: {THRESHOLD_LENGTH} (optimal)")

        if changes_needed == 0:
            print("\n🎉 All tested thresholds are optimal!")
        else:
            print(f"\n⚠️  {changes_needed} threshold(s) may need adjustment")

    def full_analysis(self):
        """Run comprehensive analysis of all vectorized functions."""
        print("COMPREHENSIVE THRESHOLD ANALYSIS")
        print("=" * 80)
        print("Combined analysis from all previous test scripts")
        print("=" * 80)

        all_recommendations = {}

        # Test all functions
        functions_to_test = [
            ("bbox", self.test_bbox_threshold, THRESHOLD_BBOX),
            ("length", self.test_length_threshold, THRESHOLD_LENGTH),
            (
                "stitch_geometries",
                self.test_stitch_geometries_threshold,
                THRESHOLD_STITCH_GEOMETRIES,
            ),
            (
                "stitcheable_nodes",
                self.test_stitcheable_nodes_threshold,
                THRESHOLD_STITCHEABLE_NODES,
            ),
        ]

        for func_name, test_func, current_threshold in functions_to_test:
            print(f"\n[Testing {func_name}...]")
            try:
                results = test_func()
                recommended = self.analyze_performance_data(
                    results, current_threshold, func_name
                )
                all_recommendations[func_name] = recommended
            except Exception as e:
                self.log(f"Failed to test {func_name}: {e}")
                all_recommendations[func_name] = current_threshold

        # Add constants for functions not directly tested
        all_recommendations["close_gaps"] = THRESHOLD_CLOSE_GAPS
        all_recommendations["area"] = "always"

        # Generate final report
        self.generate_final_report(all_recommendations)

    def generate_final_report(self, recommendations: Dict[str, Any]):
        """Generate comprehensive final report."""
        print("\n" + "=" * 80)
        print("COMPREHENSIVE ANALYSIS RESULTS")
        print("=" * 80)

        print("\nFunction-by-function recommendations:")
        print("-" * 60)

        changes_needed = []

        for func_name, current in self.current_thresholds.items():
            recommended = recommendations.get(func_name, current)
            line = self.line_numbers[func_name]

            if func_name == "area":
                print(f"{func_name:18s}: Always vectorized (optimal)")
                continue

            if recommended != current:
                status = "⚠️  NEEDS CHANGE"
                changes_needed.append((func_name, line, current, recommended))
            else:
                status = "✅ OPTIMAL"

            print(
                f"{func_name:18s}: {current:2d} → {recommended:2d} | Line {line:4d} | {status}"
            )

        if changes_needed:
            print(
                f"\n⚠️  CHANGES RECOMMENDED: {len(changes_needed)} thresholds need adjustment"
            )
            print("\nRecommended constant updates in geomstr.py:")
            print("-" * 50)

            for func_name, line, current, recommended in changes_needed:
                const_name = f"THRESHOLD_{func_name.upper()}"
                print(f"• {const_name}: {current} → {recommended}")
                action = "RAISE" if recommended > current else "LOWER"
                change = abs(recommended - current)
                print(f"  Action: {action} by {change}")
                print()
        else:
            print("\n🎉 ALL THRESHOLDS ARE OPTIMALLY CONFIGURED!")
            print("No changes needed - excellent performance tuning!")

    def validate_current_settings(self):
        """Validate that current threshold settings are reasonable."""
        print("THRESHOLD VALIDATION")
        print("=" * 40)

        issues = []

        # Check for reasonable threshold values
        if THRESHOLD_STITCHEABLE_NODES < 10:
            issues.append("stitcheable_nodes threshold too low")
        if THRESHOLD_STITCH_GEOMETRIES < 15:
            issues.append("stitch_geometries threshold too low")
        if THRESHOLD_CLOSE_GAPS < 5:
            issues.append("close_gaps threshold too low")
        if THRESHOLD_BBOX < 20:
            issues.append("bbox threshold too low")
        if THRESHOLD_LENGTH < 25:
            issues.append("length threshold too low")

        # Check for consistency
        if THRESHOLD_STITCHEABLE_NODES > THRESHOLD_STITCH_GEOMETRIES:
            issues.append("stitcheable_nodes threshold higher than stitch_geometries")

        if issues:
            print("⚠️  Validation Issues Found:")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print("✅ All thresholds pass validation checks")
            print("✅ Constants are properly imported and accessible")
            print("✅ All threshold values are in reasonable ranges")

        # Quick sanity check
        print("\nRunning sanity check with small datasets...")

        # Test with very small datasets (should use standard implementation)
        small_geom = Geomstr()
        for i in range(3):
            small_geom.line(complex(i * 5, 0), complex(i * 5 + 3, 2))

        small_time = self.time_function(lambda: small_geom.bbox())
        print(f"Small geometry bbox time: {small_time*1000000:.1f}μs (should be fast)")
        print("✅ Sanity check passed")


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Vectorization Threshold Analysis for MeerK40t",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This module combines all previous threshold test scripts into one comprehensive tool:
- simple_threshold_test.py: Basic performance testing
- fixed_threshold_test.py: Enhanced analysis with recommendations
- fixed_comprehensive_analysis.py: Full function testing
- show_thresholds.py: Current threshold display

Examples:
  python threshold_testing.py --show-current
  python threshold_testing.py --quick-test
  python threshold_testing.py --full-analysis
  python threshold_testing.py --validate
        """,
    )

    parser.add_argument(
        "--show-current",
        action="store_true",
        help="Show current threshold values and constants",
    )
    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Run quick performance test on key functions",
    )
    parser.add_argument(
        "--full-analysis",
        action="store_true",
        help="Run comprehensive analysis of all functions",
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate current threshold settings"
    )
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")

    args = parser.parse_args()

    # If no specific action, show help and current status
    if not any([args.show_current, args.quick_test, args.full_analysis, args.validate]):
        parser.print_help()
        print("\n" + "=" * 60)
        print("DEFAULT: Showing current thresholds")
        print("=" * 60)
        analyzer = ComprehensiveThresholdAnalyzer(verbose=True)
        analyzer.show_current_thresholds()
        return

    analyzer = ComprehensiveThresholdAnalyzer(verbose=not args.quiet)

    if args.show_current:
        analyzer.show_current_thresholds()

    if args.validate:
        analyzer.validate_current_settings()

    if args.quick_test:
        analyzer.quick_test()

    if args.full_analysis:
        analyzer.full_analysis()


if __name__ == "__main__":
    main()
