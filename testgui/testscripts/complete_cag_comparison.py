#!/usr/bin/env python3
"""
Complete CAG Implementation Comparison
=====================================

This test provides comprehensive comparison of all three CAG implementations:
- Polybool: Native meerk40t implementation (meerk40t.tools.polybool)
- Pyclipr: Python binding for Clipper2 library
- Geomstr: Settings-based scanbeam algorithm

Features:
- Multiple complex shape types (rectangles, circles, polygons, stars)
- Detailed speed comparisons and scaling analysis
- Memory usage tracking
- Accuracy validation with known geometric properties
- Head-to-head performance comparison across all implementations
"""

import gc
import math
import time
import tracemalloc
from typing import Any, Dict, List, Tuple

# Import all three CAG implementations
try:
    from meerk40t.core.geomstr import TYPE_LINE, BeamTable, Geomstr

    GEOMSTR_AVAILABLE = True
except ImportError:
    print("Warning: Geomstr not available")
    GEOMSTR_AVAILABLE = False

try:
    from meerk40t.tools.polybool import Polygon, difference, intersect, union

    POLYBOOL_AVAILABLE = True
except ImportError:
    print("Warning: Polybool not available")
    POLYBOOL_AVAILABLE = False

try:
    import numpy as np
    import pyclipr

    PYCLIPR_AVAILABLE = True
except ImportError:
    print("Warning: Pyclipr not available")
    PYCLIPR_AVAILABLE = False


class PerformanceProfiler:
    """Profiles performance and memory usage of CAG operations."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset profiling data."""
        self.start_time = None
        self.end_time = None
        self.start_memory = None
        self.end_memory = None
        self.peak_memory = None

    def start_profiling(self):
        """Start profiling session."""
        gc.collect()  # Clean up before measurement
        tracemalloc.start()
        self.start_time = time.perf_counter()
        self.start_memory = tracemalloc.get_traced_memory()[0]

    def end_profiling(self):
        """End profiling session."""
        self.end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        self.end_memory = current
        self.peak_memory = peak
        tracemalloc.stop()

    def get_results(self) -> Dict[str, float]:
        """Get profiling results."""
        if self.start_time is None or self.end_time is None:
            return {}

        return {
            "execution_time": self.end_time - self.start_time,
            "memory_used": (self.end_memory - self.start_memory) / (1024 * 1024)
            if self.end_memory and self.start_memory
            else 0,  # MB
            "peak_memory": self.peak_memory / (1024 * 1024)
            if self.peak_memory
            else 0,  # MB
        }


class ShapeGenerator:
    """Generator for various complex shapes for testing."""

    @staticmethod
    def rectangle(
        x: float, y: float, width: float, height: float
    ) -> List[Tuple[float, float]]:
        """Generate rectangle coordinates."""
        return [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]

    @staticmethod
    def circle(
        cx: float, cy: float, radius: float, segments: int = 32
    ) -> List[Tuple[float, float]]:
        """Generate circle approximation using line segments."""
        points = []
        for i in range(segments):
            angle = (2 * math.pi * i) / segments
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            points.append((x, y))
        return points

    @staticmethod
    def regular_polygon(
        cx: float, cy: float, radius: float, sides: int
    ) -> List[Tuple[float, float]]:
        """Generate regular polygon."""
        points = []
        for i in range(sides):
            angle = (2 * math.pi * i) / sides
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            points.append((x, y))
        return points

    @staticmethod
    def star(
        cx: float, cy: float, outer_radius: float, inner_radius: float, points: int
    ) -> List[Tuple[float, float]]:
        """Generate star shape."""
        coords = []
        for i in range(points * 2):
            angle = (math.pi * i) / points
            if i % 2 == 0:
                radius = outer_radius
            else:
                radius = inner_radius
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            coords.append((x, y))
        return coords


class GeometryValidator:
    """Validates geometric properties of CAG results."""

    @staticmethod
    def shoelace_area(points: List[Tuple[float, float]]) -> float:
        """Calculate polygon area using shoelace formula."""
        if len(points) < 3:
            return 0.0

        # Ensure polygon is closed
        if points[0] != points[-1]:
            points = points + [points[0]]

        area = 0.0
        for i in range(len(points) - 1):
            area += points[i][0] * points[i + 1][1] - points[i + 1][0] * points[i][1]

        return abs(area) / 2.0

    @staticmethod
    def validate_result(
        points: List[Tuple[float, float]],
        expected_area_range: Tuple[float, float],
        test_name: str,
    ) -> Dict[str, Any]:
        """Comprehensive validation of CAG result."""
        if not points:
            return {
                "valid": False,
                "area": 0.0,
                "error": "Empty result",
                "test_name": test_name,
            }

        area = GeometryValidator.shoelace_area(points)
        min_area, max_area = expected_area_range

        return {
            "valid": min_area <= area <= max_area,
            "area": area,
            "num_points": len(points),
            "expected_range": expected_area_range,
            "test_name": test_name,
            "error": None
            if min_area <= area <= max_area
            else f"Area {area:.6f} outside range [{min_area:.6f}, {max_area:.6f}]",
        }


class CAGComparison:
    """Compare all three CAG implementations."""

    def __init__(self):
        self.profiler = PerformanceProfiler()
        self.generator = ShapeGenerator()
        self.validator = GeometryValidator()

    def test_polybool_cag(
        self,
        shape1: List[Tuple[float, float]],
        shape2: List[Tuple[float, float]],
        operation: str = "union",
    ) -> Dict[str, Any]:
        """Test native polybool CAG implementation."""
        if not POLYBOOL_AVAILABLE:
            return {"error": "Polybool not available", "method": "polybool"}

        try:
            # Start profiling
            self.profiler.start_profiling()

            # Convert to polybool format (list of points as regions)
            poly1 = Polygon([shape1])
            poly2 = Polygon([shape2])

            # Perform operation
            if operation == "union":
                result = union(poly1, poly2)
            elif operation == "intersection":
                result = intersect(poly1, poly2)
            elif operation == "difference":
                result = difference(poly1, poly2)
            else:
                raise ValueError(f"Unsupported operation: {operation}")

            # End profiling
            self.profiler.end_profiling()
            performance = self.profiler.get_results()

            # Extract result points
            if result and hasattr(result, "regions") and result.regions:
                # Get points from first region
                region = result.regions[0]
                result_points = []

                # Extract points from the region
                for pt in region:
                    if hasattr(pt, "x") and hasattr(pt, "y"):
                        result_points.append((pt.x, pt.y))
                    else:
                        # Fallback for different point formats
                        result_points.append((float(pt[0]), float(pt[1])))

                return {
                    "method": "polybool",
                    "operation": operation,
                    "success": True,
                    "points": result_points,
                    "performance": performance,
                }
            else:
                return {
                    "method": "polybool",
                    "operation": operation,
                    "success": False,
                    "error": "Empty result",
                    "performance": performance,
                }

        except Exception as e:
            return {
                "method": "polybool",
                "operation": operation,
                "success": False,
                "error": f"Polybool error: {str(e)}",
                "performance": self.profiler.get_results(),
            }

    def test_pyclipr_cag(
        self,
        shape1: List[Tuple[float, float]],
        shape2: List[Tuple[float, float]],
        operation: str = "union",
    ) -> Dict[str, Any]:
        """Test pyclipr CAG implementation."""
        if not PYCLIPR_AVAILABLE:
            return {"error": "Pyclipr not available", "method": "pyclipr"}

        try:
            # Start profiling
            self.profiler.start_profiling()

            # Create clipper object following the working implementation
            clipper = pyclipr.Clipper()
            clipper.scaleFactor = 1000

            # Convert to numpy arrays as required by pyclipr
            path1 = np.array(shape1, dtype=np.float64)
            path2 = np.array(shape2, dtype=np.float64)

            # Add paths to clipper
            clipper.addPath(path1, pyclipr.PathType.Subject, False)  # Closed polygon
            clipper.addPath(path2, pyclipr.PathType.Clip, False)  # Closed polygon

            # Determine operation type and fill rule
            if operation == "union":
                clip_type = pyclipr.ClipType.Union
            elif operation == "intersection":
                clip_type = pyclipr.ClipType.Intersection
            elif operation == "difference":
                clip_type = pyclipr.ClipType.Difference
            else:
                raise ValueError(f"Unsupported operation: {operation}")

            # Use FillRule/FillType with compatibility (following offset_clpr.py pattern)
            try:
                fill_rule = pyclipr.FillRule.EvenOdd
            except AttributeError:
                fill_rule = pyclipr.FillType.EvenOdd

            # Execute the operation
            result = clipper.execute(clip_type, fill_rule)

            # End profiling
            self.profiler.end_profiling()
            performance = self.profiler.get_results()

            if result and len(result) > 0:
                # Get first result polygon
                result_points = (
                    result[0].tolist()
                    if hasattr(result[0], "tolist")
                    else list(result[0])
                )

                return {
                    "method": "pyclipr",
                    "operation": operation,
                    "success": True,
                    "points": result_points,
                    "performance": performance,
                }
            else:
                return {
                    "method": "pyclipr",
                    "operation": operation,
                    "success": False,
                    "error": "Empty result",
                    "performance": performance,
                }

        except Exception as e:
            return {
                "method": "pyclipr",
                "operation": operation,
                "success": False,
                "error": f"Pyclipr error: {str(e)}",
                "performance": self.profiler.get_results(),
            }

    def test_geomstr_cag(
        self,
        shape1: List[Tuple[float, float]],
        shape2: List[Tuple[float, float]],
        operation: str = "union",
    ) -> Dict[str, Any]:
        """Test Geomstr CAG with corrected settings-based approach."""
        if not GEOMSTR_AVAILABLE:
            return {"error": "Geomstr not available", "method": "geomstr"}

        try:
            # Start profiling
            self.profiler.start_profiling()

            # Create Geomstr objects with settings
            g = Geomstr()

            # Convert point lists to Geomstr lines with different settings
            lines1 = Geomstr.lines(*[complex(x, y) for x, y in shape1], settings=0)
            lines2 = Geomstr.lines(*[complex(x, y) for x, y in shape2], settings=1)

            # Combine geometries
            g.append(lines1)
            g.append(lines2)

            # Create BeamTable and perform operation
            bt = BeamTable(g)
            bt.compute_beam()

            if operation == "union":
                result_geom = bt.union(0, 1)
            elif operation == "intersection":
                result_geom = bt.intersection(0, 1)
            elif operation == "difference":
                result_geom = bt.difference(0, 1)
            else:
                raise ValueError(f"Unsupported operation: {operation}")

            # End profiling
            self.profiler.end_profiling()
            performance = self.profiler.get_results()

            # Extract result points
            if result_geom and len(result_geom) > 0:
                result_points = self._extract_geomstr_points(result_geom)

                return {
                    "method": "geomstr",
                    "operation": operation,
                    "success": True,
                    "points": result_points,
                    "performance": performance,
                }
            else:
                return {
                    "method": "geomstr",
                    "operation": operation,
                    "success": False,
                    "error": "Empty result",
                    "performance": performance,
                }

        except Exception as e:
            return {
                "method": "geomstr",
                "operation": operation,
                "success": False,
                "error": f"Geomstr error: {str(e)}",
                "performance": self.profiler.get_results(),
            }

    def _extract_geomstr_points(self, geom: Geomstr) -> List[Tuple[float, float]]:
        """Extract points from Geomstr result using proper segment traversal."""
        # Collect all unique points from line segments
        all_points = set()

        for segment in geom.segments[: geom.index]:
            if len(segment) >= 5:
                seg_type = int(segment[2].real) & 0xFF
                if seg_type == TYPE_LINE:
                    start_point = segment[0]
                    end_point = segment[4]

                    start_coord = (float(start_point.real), float(start_point.imag))
                    end_coord = (float(end_point.real), float(end_point.imag))

                    all_points.add(start_coord)
                    all_points.add(end_coord)

        if not all_points:
            return []

        result_points = list(all_points)

        # Sort points to form a polygon (by angle from centroid)
        if len(result_points) > 2:
            cx = sum(x for x, y in result_points) / len(result_points)
            cy = sum(y for x, y in result_points) / len(result_points)

            def angle_from_centroid(point):
                x, y = point
                return math.atan2(y - cy, x - cx)

            result_points.sort(key=angle_from_centroid)

        return result_points

    def test_shape_comparison(
        self,
        shape1: List[Tuple[float, float]],
        shape2: List[Tuple[float, float]],
        expected_area_range: Tuple[float, float],
        test_name: str,
        operation: str = "union",
    ) -> Dict[str, Any]:
        """Test a pair of shapes with all available CAG implementations."""

        print(f"\n{'='*80}")
        print(f"Testing: {test_name} ({operation})")
        print(f"{'='*80}")

        results = {}

        # Test each implementation
        test_methods = []
        if POLYBOOL_AVAILABLE:
            test_methods.append(("polybool", self.test_polybool_cag))
        if PYCLIPR_AVAILABLE:
            test_methods.append(("pyclipr", self.test_pyclipr_cag))
        if GEOMSTR_AVAILABLE:
            test_methods.append(("geomstr", self.test_geomstr_cag))

        for method_name, test_method in test_methods:
            result = test_method(shape1, shape2, operation)
            results[method_name] = result

            if result.get("success", False):
                # Validate geometry
                validation = self.validator.validate_result(
                    result["points"], expected_area_range, test_name
                )

                result.update(validation)

                # Print results
                perf = result.get("performance", {})
                exec_time = perf.get("execution_time", 0) * 1000  # ms
                memory = perf.get("memory_used", 0)  # MB

                status = "✓" if result.get("valid", False) else "✗"
                print(
                    f"{status} {method_name:10}: Area={result.get('area', 0):8.6f}, "
                    f"Time={exec_time:7.3f}ms, Memory={memory:6.2f}MB, "
                    f"Points={result.get('num_points', 0):4d}"
                )

                if not result.get("valid", False) and result.get("error"):
                    print(f"   Error: {result['error']}")
            else:
                print(
                    f"✗ {method_name:10}: Failed - {result.get('error', 'Unknown error')}"
                )

        return results

    def run_performance_scaling_test(self):
        """Test performance scaling with increasing complexity."""
        print(f"\n{'='*80}")
        print("PERFORMANCE SCALING ANALYSIS")
        print(f"{'='*80}")

        complexities = [8, 16, 32, 64, 128]
        operations = ["union"]  # Focus on union for scaling test

        for operation in operations:
            print(f"\nTesting {operation} performance scaling:")
            print(
                f"{'Sides':>6} | {'Polybool (ms)':>12} | {'Pyclipr (ms)':>12} | {'Geomstr (ms)':>12}"
            )
            print("-" * 55)

            for complexity in complexities:
                # Create two complex polygons
                poly1 = self.generator.regular_polygon(0, 0, 1, complexity)
                poly2 = self.generator.regular_polygon(0.5, 0, 1, complexity)

                times = {}

                # Test each available method
                test_methods = []
                if POLYBOOL_AVAILABLE:
                    test_methods.append(("polybool", self.test_polybool_cag))
                if PYCLIPR_AVAILABLE:
                    test_methods.append(("pyclipr", self.test_pyclipr_cag))
                if GEOMSTR_AVAILABLE:
                    test_methods.append(("geomstr", self.test_geomstr_cag))

                for method_name, test_method in test_methods:
                    result = test_method(poly1, poly2, operation)

                    if result.get("success", False):
                        exec_time = (
                            result.get("performance", {}).get("execution_time", 0)
                            * 1000
                        )
                        times[method_name] = exec_time
                    else:
                        times[method_name] = -1  # Failed

                # Print timing row
                polybool_time = times.get("polybool", -1)
                pyclipr_time = times.get("pyclipr", -1)
                geomstr_time = times.get("geomstr", -1)

                print(
                    f"{complexity:>6} | {polybool_time:>9.3f} | "
                    f"{pyclipr_time:>9.3f} | {geomstr_time:>9.3f}"
                )

    def run_comprehensive_comparison(self):
        """Run comprehensive CAG comparison across all implementations."""

        print("COMPLETE CAG IMPLEMENTATION COMPARISON")
        print("=" * 80)
        print("Testing all available CAG implementations:")
        available_impls = []
        if POLYBOOL_AVAILABLE:
            available_impls.append("Polybool (native)")
        if PYCLIPR_AVAILABLE:
            available_impls.append("Pyclipr (Clipper2)")
        if GEOMSTR_AVAILABLE:
            available_impls.append("Geomstr (scanbeam)")

        print(f"Available: {', '.join(available_impls)}")
        print()

        all_results = []

        # Test 1: Simple rectangles
        rect1 = self.generator.rectangle(0, 0, 2, 2)  # 4 area
        rect2 = self.generator.rectangle(1, 1, 2, 2)  # 4 area, overlap = 1
        expected_union_area = (6.5, 7.5)  # Should be 7

        results = self.test_shape_comparison(
            rect1, rect2, expected_union_area, "Overlapping Rectangles", "union"
        )
        all_results.append(("rectangles", results))

        # Test 2: Circles
        circle1 = self.generator.circle(0, 0, 1, 32)  # Area ≈ π
        circle2 = self.generator.circle(1, 0, 1, 32)  # Area ≈ π, overlap varies
        expected_circle_union = (4.5, 6.5)  # Should be ≈ 2π - overlap

        results = self.test_shape_comparison(
            circle1, circle2, expected_circle_union, "Overlapping Circles", "union"
        )
        all_results.append(("circles", results))

        # Test 3: Regular polygons
        hex1 = self.generator.regular_polygon(0, 0, 1, 6)
        hex2 = self.generator.regular_polygon(0.8, 0, 1, 6)
        expected_hex_union = (2.0, 4.0)  # Hexagon area ≈ 2.598, union varies

        results = self.test_shape_comparison(
            hex1, hex2, expected_hex_union, "Overlapping Hexagons", "union"
        )
        all_results.append(("hexagons", results))

        # Test 4: Star shapes
        star1 = self.generator.star(0, 0, 2, 1, 5)
        star2 = self.generator.star(1.5, 0, 2, 1, 5)
        expected_star_union = (8.0, 20.0)  # Rough estimate for complex shapes

        results = self.test_shape_comparison(
            star1, star2, expected_star_union, "Overlapping Stars", "union"
        )
        all_results.append(("stars", results))

        # Performance scaling test
        self.run_performance_scaling_test()

        # Analysis
        self.analyze_comprehensive_results(all_results)

        return all_results

    def analyze_comprehensive_results(
        self, all_results: List[Tuple[str, Dict[str, Any]]]
    ):
        """Analyze comprehensive comparison results."""

        print(f"\n{'='*80}")
        print("COMPREHENSIVE ANALYSIS")
        print("=" * 80)

        # Collect statistics
        method_stats = {}
        available_methods = []
        if POLYBOOL_AVAILABLE:
            available_methods.append("polybool")
        if PYCLIPR_AVAILABLE:
            available_methods.append("pyclipr")
        if GEOMSTR_AVAILABLE:
            available_methods.append("geomstr")

        for method in available_methods:
            method_stats[method] = {
                "successes": 0,
                "failures": 0,
                "total_time": 0,
                "total_memory": 0,
                "valid_results": 0,
            }

        # Analyze results
        for test_name, results in all_results:
            for method, result in results.items():
                if method in method_stats:
                    stats = method_stats[method]

                    if result.get("success", False):
                        stats["successes"] += 1
                        perf = result.get("performance", {})
                        stats["total_time"] += perf.get("execution_time", 0)
                        stats["total_memory"] += perf.get("memory_used", 0)

                        if result.get("valid", False):
                            stats["valid_results"] += 1
                    else:
                        stats["failures"] += 1

        # Print summary statistics
        print("\nSUCCESS RATES:")
        for method, stats in method_stats.items():
            total = stats["successes"] + stats["failures"]
            if total > 0:
                success_rate = (stats["successes"] / total) * 100
                valid_rate = (
                    (stats["valid_results"] / stats["successes"]) * 100
                    if stats["successes"] > 0
                    else 0
                )
                print(
                    f"  {method:10}: {stats['successes']}/{total} success ({success_rate:.1f}%), "
                    f"{stats['valid_results']}/{stats['successes']} valid ({valid_rate:.1f}%)"
                )

        print("\nAVERAGE PERFORMANCE (successful tests only):")
        for method, stats in method_stats.items():
            if stats["successes"] > 0:
                avg_time = (stats["total_time"] / stats["successes"]) * 1000  # ms
                avg_memory = stats["total_memory"] / stats["successes"]  # MB
                print(f"  {method:10}: {avg_time:7.3f}ms avg, {avg_memory:6.2f}MB avg")

        # Speed comparison
        if len([m for m in method_stats.values() if m["successes"] > 0]) > 1:
            print("\nSPEED COMPARISON (average execution time):")
            speed_data = {}
            for method, stats in method_stats.items():
                if stats["successes"] > 0:
                    speed_data[method] = stats["total_time"] / stats["successes"]

            if speed_data:
                fastest_method = min(speed_data.keys(), key=lambda k: speed_data[k])
                fastest_time = speed_data[fastest_method]

                sorted_methods = sorted(speed_data.items(), key=lambda x: x[1])
                for i, (method, avg_time) in enumerate(sorted_methods):
                    speedup = avg_time / fastest_time
                    print(
                        f"  {i+1}. {method:10}: {avg_time*1000:.3f}ms ({speedup:.1f}x)"
                    )

        print("\nIMPLEMENTATION CHARACTERISTICS:")
        if POLYBOOL_AVAILABLE:
            print(
                "  • Polybool:  Native implementation, optimized for Meerk40t workflows"
            )
        if PYCLIPR_AVAILABLE:
            print("  • Pyclipr:   Clipper2 binding, industry-standard polygon clipping")
        if GEOMSTR_AVAILABLE:
            print(
                "  • Geomstr:   Settings-based scanbeam algorithm, integrated geometry"
            )


def main():
    """Main execution function."""
    comparison = CAGComparison()
    results = comparison.run_comprehensive_comparison()

    print(f"\n{'='*80}")
    print("Complete CAG implementation comparison finished!")
    print("All available implementations tested across multiple shape types.")
    print(f"{'='*80}")

    return results


if __name__ == "__main__":
    main()
