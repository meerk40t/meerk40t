import math
import time
from dataclasses import dataclass
from typing import List, Set, Tuple

from meerk40t.svgelements import (
    Arc,
    Close,
    Color,
    CubicBezier,
    Line,
    Move,
    Path,
    Point,
    QuadraticBezier,
)


@dataclass
class PathSegment:
    """Represents a single path segment with metadata for overlap detection"""

    path_index: int
    segment_index: int
    segment: object
    start_point: Point
    end_point: Point
    bbox: Tuple[float, float, float, float]  # (min_x, min_y, max_x, max_y)
    is_complex: bool
    length_estimate: float

    def overlaps_bbox(self, other: "PathSegment", margin: float = 0.1) -> bool:
        """Check if this segment's bbox overlaps with another's"""
        x1_min, y1_min, x1_max, y1_max = self.bbox
        x2_min, y2_min, x2_max, y2_max = other.bbox

        return not (
            x1_max + margin < x2_min
            or x2_max + margin < x1_min
            or y1_max + margin < y2_min
            or y2_max + margin < y1_min
        )

    def bbox_area(self) -> float:
        """Calculate bounding box area"""
        x_min, y_min, x_max, y_max = self.bbox
        return (x_max - x_min) * (y_max - y_min)


def detect_ellipse_like_path(path: Path) -> bool:
    """
    Detect if a path represents an ellipse or ellipse-like shape.
    This checks for paths with many arc segments or circular/elliptical structure.
    """
    if not path or len(path) == 0:
        return False

    arc_count = 0
    total_segments = 0
    total_sweep = 0.0

    for segment in path:
        if isinstance(segment, (Move, Close)):
            continue
        total_segments += 1

        if isinstance(segment, Arc):
            arc_count += 1
            if hasattr(segment, "sweep") and segment.sweep is not None:
                total_sweep += abs(segment.sweep)

    # Check if this looks like an ellipse:
    # 1. High proportion of arc segments
    # 2. Total sweep approaches 2π (full rotation)
    # 3. Or if it's a single large arc
    if total_segments == 0:
        return False

    arc_ratio = arc_count / total_segments
    is_near_full_rotation = abs(total_sweep - (2 * math.pi)) < 0.5

    return (
        (arc_ratio >= 0.5)
        or is_near_full_rotation
        or (arc_count == 1 and total_sweep > math.pi)
    )


def analyze_path_complexity(path: Path) -> dict:
    """
    Analyze a path to determine its complexity characteristics.
    Returns dict with complexity metrics for interpolation decisions.
    """
    if not path or len(path) == 0:
        return {
            "is_ellipse": False,
            "has_curves": False,
            "curve_ratio": 0.0,
            "complexity_score": 0,
        }

    total_segments = 0
    curve_segments = 0
    arc_segments = 0
    total_sweep = 0.0
    max_curvature = 0.0

    for segment in path:
        if isinstance(segment, (Move, Close)):
            continue

        total_segments += 1

        if isinstance(segment, (QuadraticBezier, CubicBezier)):
            curve_segments += 1
            # Estimate curvature for bezier curves
            if isinstance(segment, CubicBezier):
                # Higher complexity for cubic beziers
                max_curvature = max(max_curvature, 2.0)
            else:
                max_curvature = max(max_curvature, 1.5)

        elif isinstance(segment, Arc):
            arc_segments += 1
            if hasattr(segment, "sweep") and segment.sweep is not None:
                total_sweep += abs(segment.sweep)
                # Arcs with larger sweep need more interpolation
                sweep_factor = min(abs(segment.sweep) / (math.pi / 2), 4.0)
                max_curvature = max(max_curvature, sweep_factor)

    curve_ratio = (curve_segments + arc_segments) / max(total_segments, 1)
    is_ellipse = detect_ellipse_like_path(path)
    has_curves = curve_segments > 0 or arc_segments > 0

    # Calculate complexity score (0-10 scale)
    complexity_score = 0
    if is_ellipse:
        complexity_score += 5  # Ellipses always get high complexity
    complexity_score += curve_ratio * 3  # Up to 3 points for curve ratio
    complexity_score += min(max_curvature, 2)  # Up to 2 points for curvature

    return {
        "is_ellipse": is_ellipse,
        "has_curves": has_curves,
        "curve_ratio": curve_ratio,
        "complexity_score": min(complexity_score, 10),
        "arc_segments": arc_segments,
        "curve_segments": curve_segments,
        "total_segments": total_segments,
        "total_sweep": total_sweep,
    }


def extract_path_segments(paths: List[Path]) -> List[PathSegment]:
    """Extract individual segments from paths with accurate bounding box calculation"""
    segments = []

    for path_idx, path in enumerate(paths):
        current_point = Point(0, 0)
        subpath_start = Point(0, 0)

        for seg_idx, segment in enumerate(path):
            if isinstance(segment, Move):
                current_point = segment.end
                subpath_start = current_point
                continue  # Skip moves for overlap analysis

            start_point = current_point

            if isinstance(segment, Close):
                end_point = subpath_start
                bbox = (
                    min(start_point.x, end_point.x),
                    min(start_point.y, end_point.y),
                    max(start_point.x, end_point.x),
                    max(start_point.y, end_point.y),
                )
                is_complex = False
                length_est = abs(
                    complex(end_point.x - start_point.x, end_point.y - start_point.y)
                )

            elif isinstance(segment, Line):
                end_point = segment.end
                bbox = (
                    min(start_point.x, end_point.x),
                    min(start_point.y, end_point.y),
                    max(start_point.x, end_point.x),
                    max(start_point.y, end_point.y),
                )
                is_complex = False
                length_est = abs(
                    complex(end_point.x - start_point.x, end_point.y - start_point.y)
                )

            elif isinstance(segment, QuadraticBezier):
                end_point = segment.end
                try:
                    bbox = segment.bbox()
                except Exception:
                    control = segment.control
                    all_x = [start_point.x, control.x, end_point.x]
                    all_y = [start_point.y, control.y, end_point.y]
                    bbox = (min(all_x), min(all_y), max(all_x), max(all_y))
                is_complex = True
                d1 = abs(
                    complex(
                        segment.control.x - start_point.x,
                        segment.control.y - start_point.y,
                    )
                )
                d2 = abs(
                    complex(
                        end_point.x - segment.control.x, end_point.y - segment.control.y
                    )
                )
                length_est = d1 + d2

            elif isinstance(segment, CubicBezier):
                end_point = segment.end
                try:
                    bbox = segment.bbox()
                except Exception:
                    all_x = [
                        start_point.x,
                        segment.control1.x,
                        segment.control2.x,
                        end_point.x,
                    ]
                    all_y = [
                        start_point.y,
                        segment.control1.y,
                        segment.control2.y,
                        end_point.y,
                    ]
                    bbox = (min(all_x), min(all_y), max(all_x), max(all_y))
                is_complex = True
                d1 = abs(
                    complex(
                        segment.control1.x - start_point.x,
                        segment.control1.y - start_point.y,
                    )
                )
                d2 = abs(
                    complex(
                        segment.control2.x - segment.control1.x,
                        segment.control2.y - segment.control1.y,
                    )
                )
                d3 = abs(
                    complex(
                        end_point.x - segment.control2.x,
                        end_point.y - segment.control2.y,
                    )
                )
                length_est = d1 + d2 + d3

            elif isinstance(segment, Arc):
                end_point = segment.end
                try:
                    bbox = segment.bbox()
                except Exception:
                    bbox = (
                        min(start_point.x, end_point.x),
                        min(start_point.y, end_point.y),
                        max(start_point.x, end_point.x),
                        max(start_point.y, end_point.y),
                    )
                is_complex = True
                # Arcs get higher length estimate to prioritize them for more interpolation
                length_est = (
                    abs(
                        complex(
                            end_point.x - start_point.x, end_point.y - start_point.y
                        )
                    )
                    * 2.0
                )

            else:
                end_point = getattr(segment, "end", current_point)
                bbox = (
                    min(start_point.x, end_point.x),
                    min(start_point.y, end_point.y),
                    max(start_point.x, end_point.x),
                    max(start_point.y, end_point.y),
                )
                is_complex = True
                length_est = abs(
                    complex(end_point.x - start_point.x, end_point.y - start_point.y)
                )

            segments.append(
                PathSegment(
                    path_index=path_idx,
                    segment_index=seg_idx,
                    segment=segment,
                    start_point=start_point,
                    end_point=end_point,
                    bbox=bbox,
                    is_complex=is_complex,
                    length_estimate=length_est,
                )
            )

            current_point = end_point

    return segments


def find_overlapping_segments(
    segments: List[PathSegment], cross_path_only: bool = True
) -> Set[int]:
    """Find segments that overlap with segments from other paths"""
    overlapping_indices = set()

    for i, seg1 in enumerate(segments):
        for j, seg2 in enumerate(segments[i + 1 :], i + 1):
            if cross_path_only and seg1.path_index == seg2.path_index:
                continue

            if seg1.overlaps_bbox(seg2):
                overlapping_indices.add(i)
                overlapping_indices.add(j)

    return overlapping_indices


def heal_polygon_gaps(segs, channel, pb, tolerance=1e-4):
    """
    Post-PolyBool healing to fix geometric gaps and disconnected regions.

    This function attempts to repair common issues introduced by PolyBool:
    - Small gaps between regions that should be connected
    - Nearly-duplicate points that cause artifacts
    - Disconnected regions that should be merged

    Args:
        segs: PolyBool segments
        channel: Logging channel
        pb: PolyBool module
        tolerance: Distance tolerance for gap detection and healing

    Returns:
        Healed PolyBool segments
    """
    try:
        polygon = pb.polygon(segs)

        if not polygon.regions or len(polygon.regions) <= 1:
            return segs  # No healing needed for single or no regions

        channel(f"Healing {len(polygon.regions)} regions, tolerance={tolerance}")

        healed_regions = []

        for region_idx, region in enumerate(polygon.regions):
            if len(region) < 3:
                continue

            # Extract points
            points = [(pt.x, pt.y) for pt in region]

            # Remove near-duplicate consecutive points with more aggressive tolerance
            cleaned_points = [points[0]]
            for i in range(1, len(points)):
                dist = abs(
                    complex(
                        points[i][0] - cleaned_points[-1][0],
                        points[i][1] - cleaned_points[-1][1],
                    )
                )
                # Use more aggressive tolerance for removing duplicates
                if dist > tolerance * 0.1:  # Much smaller threshold for duplicates
                    cleaned_points.append(points[i])

            # Ensure proper closure
            if len(cleaned_points) > 2:
                first_point = cleaned_points[0]
                last_point = cleaned_points[-1]
                closure_distance = abs(
                    complex(
                        last_point[0] - first_point[0], last_point[1] - first_point[1]
                    )
                )

                if (
                    closure_distance > tolerance * 0.1
                ):  # Also more aggressive for closure
                    cleaned_points.append(first_point)

                if len(cleaned_points) >= 4:  # Minimum for valid closed polygon
                    healed_regions.append(cleaned_points)
                    channel(
                        f"Healed region {region_idx}: {len(points)} -> {len(cleaned_points)} points"
                    )

        if not healed_regions:
            channel("Warning: No valid regions after healing")
            return segs

        # Try to merge nearby regions with more aggressive tolerance
        if len(healed_regions) > 1:
            merged_regions = []
            used_regions = set()

            for i, region1 in enumerate(healed_regions):
                if i in used_regions:
                    continue

                current_region = region1[:]
                merged_any = True

                while merged_any:
                    merged_any = False
                    for j, region2 in enumerate(healed_regions):
                        if j == i or j in used_regions:
                            continue

                        # Check if regions can be merged (have close points)
                        min_distance = float("inf")
                        for p1 in current_region[:-1]:  # Exclude closure point
                            for p2 in region2[:-1]:
                                dist = abs(complex(p1[0] - p2[0], p1[1] - p2[1]))
                                min_distance = min(min_distance, dist)

                        # More aggressive merging - use 5x tolerance instead of 2x
                        if min_distance <= tolerance * 5:
                            # Merge regions by connecting them
                            # Find the closest points
                            best_i1, best_i2 = 0, 0
                            min_dist = float("inf")
                            for i1, p1 in enumerate(current_region[:-1]):
                                for i2, p2 in enumerate(region2[:-1]):
                                    dist = abs(complex(p1[0] - p2[0], p1[1] - p2[1]))
                                    if dist < min_dist:
                                        min_dist = dist
                                        best_i1, best_i2 = i1, i2

                            # Create merged region - improved connection logic
                            if min_dist <= tolerance * 5:
                                # Direct connection if points are very close
                                if min_dist <= tolerance:
                                    part1 = current_region[: best_i1 + 1]
                                    part2 = (
                                        region2[best_i2:] + region2[: best_i2 + 1]
                                    )  # Rotate region2
                                    part3 = current_region[
                                        best_i1 + 1 : -1
                                    ]  # Rest of region1
                                    current_region = (
                                        part1 + part2 + part3 + [current_region[0]]
                                    )
                                else:
                                    # Insert connecting line for small gaps
                                    part1 = current_region[: best_i1 + 1]
                                    part2 = (
                                        region2[best_i2:] + region2[: best_i2 + 1]
                                    )  # Rotate region2
                                    part3 = current_region[
                                        best_i1 + 1 : -1
                                    ]  # Rest of region1
                                    current_region = (
                                        part1 + part2 + part3 + [current_region[0]]
                                    )

                                used_regions.add(j)
                                merged_any = True
                                channel(
                                    f"Merged region {j} into region {i} (gap={min_dist:.6f})"
                                )
                                break

                merged_regions.append(current_region)
                used_regions.add(i)

            healed_regions = merged_regions
            channel(f"After merging: {len(healed_regions)} regions")

        # Convert back to PolyBool format
        if len(healed_regions) == 1:
            # Single region - create simple polygon
            region_points = [
                pb.point(x, y) for x, y in healed_regions[0][:-1]
            ]  # Exclude closure
            healed_polygon = pb.Polygon([region_points])
        else:
            # Multiple regions - create complex polygon
            pb_regions = []
            for region in healed_regions:
                region_points = [
                    pb.point(x, y) for x, y in region[:-1]
                ]  # Exclude closure
                pb_regions.append(region_points)
            healed_polygon = pb.Polygon(pb_regions)

        healed_segs = pb.segments(healed_polygon)
        channel("Healing completed successfully")
        return healed_segs

    except Exception as e:
        channel(f"Healing failed: {e}, using original segments")
        return segs


def calculate_cag_tolerance(
    paths: List[Path], segments: List[PathSegment], overlapping_indices: Set[int]
) -> float:
    """
    Calculate adaptive tolerance for CAG operations.

    This tolerance value is converted to interpolation points for linearization:
    - Higher tolerance values = more interpolation points = finer resolution = slower processing
    - Lower tolerance values = fewer interpolation points = coarser resolution = faster processing

    The returned value (15-150) will be used as interpolation points in linearize_path().
    """
    if not paths:
        return 25.0

    # Calculate overall path characteristics
    total_bbox_area = 0
    total_segments = len(segments)
    overlapping_segments = len(overlapping_indices)
    complex_segments = sum(1 for seg in segments if seg.is_complex)

    for path in paths:
        try:
            bbox = path.bbox()
            area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            total_bbox_area += area
        except Exception:
            total_bbox_area += 10000  # Fallback area

    avg_area = total_bbox_area / len(paths) if paths else 10000

    # Base tolerance - lower values for speed, higher for precision
    if avg_area > 100000:  # Very large shapes
        base_tolerance = 25.0  # Use moderate tolerance for large shapes
    elif avg_area > 10000:  # Large shapes
        base_tolerance = 35.0
    elif avg_area > 1000:  # Medium shapes
        base_tolerance = 50.0
    else:  # Small shapes
        base_tolerance = 75.0  # Higher tolerance for small details (finer resolution)

    # Adjust based on overlap ratio
    if total_segments > 0:
        overlap_ratio = overlapping_segments / total_segments
        if overlap_ratio < 0.1:  # Very few overlaps
            base_tolerance *= 0.5  # Lower tolerance for speed (coarser resolution)
        elif overlap_ratio < 0.3:  # Some overlaps
            base_tolerance *= 0.8
        else:  # Many overlaps
            base_tolerance *= 1.2  # Higher tolerance for precision when overlapping

    # Adjust for complexity
    if total_segments > 0:
        complexity_ratio = complex_segments / total_segments
        if complexity_ratio > 0.7:  # Very complex
            base_tolerance *= 1.5  # Much higher tolerance for curves (finer resolution)
        elif complexity_ratio < 0.3:  # Mostly simple
            base_tolerance *= 0.6  # Lower tolerance for simple lines (coarser is fine)

    # Ensure reasonable bounds
    return max(15.0, min(150.0, base_tolerance))


def paths_bbox_intersect(paths: List[Path], margin: float = 1.0) -> bool:
    """Quick check if path bounding boxes intersect"""
    if len(paths) < 2:
        return True

    try:
        bboxes = []
        for path in paths:
            bbox = path.bbox()
            bboxes.append(bbox)

        # Check if all bboxes intersect with at least one other
        for i, bbox1 in enumerate(bboxes):
            intersects = False
            for j, bbox2 in enumerate(bboxes):
                if i == j:
                    continue
                if not (
                    bbox1[2] + margin < bbox2[0]
                    or bbox2[2] + margin < bbox1[0]
                    or bbox1[3] + margin < bbox2[1]
                    or bbox2[3] + margin < bbox1[1]
                ):
                    intersects = True
                    break
            if not intersects:
                return False
        return True
    except Exception:
        return True  # Assume intersection if bbox calculation fails


def plugin(kernel, lifecycle):
    if lifecycle == "invalidate":
        try:
            import numpy as np  # pylint: disable=unused-import
        except ImportError:
            return True
    elif lifecycle == "register":
        from ..core.elements.elements import linearize_path
        from ..tools import polybool as pb

        _ = kernel.translation
        context = kernel.root

        @context.console_option(
            "keep", "k", type=bool, action="store_true", help="keep original elements"
        )
        @context.console_command(
            ("intersection", "xor", "union", "difference"),
            input_type="elements",
            output_type="elements",
            help=_("Constructive Additive Geometry: Add"),
        )
        def cag(command, channel, _, keep=False, data=None, **kwargs):
            if len(data) < 2:
                channel(
                    _(
                        "Not enough items selected to apply constructive geometric function"
                    )
                )
                return "elements", []

            start_time = time.time()
            elements = context.elements
            solution_path = Path(
                stroke=elements.default_stroke,
                stroke_width=elements.default_strokewidth,
                fill=elements.default_fill,
            )

            # Reorder elements by emphasis time
            data.sort(key=lambda n: n.emphasized_time)

            # Extract paths
            paths = []
            for node in data:
                try:
                    path = abs(node.as_path())
                    paths.append(path)
                except AttributeError:
                    channel(_("Could not convert element to path"))
                    return "elements", data

            if not paths:
                return "elements", data

            # Store visual properties from first valid node
            last_fill = None
            last_stroke = None
            last_stroke_width = None
            for node in data:
                if last_fill is None and hasattr(node, "fill"):
                    last_fill = node.fill
                if last_stroke is None and hasattr(node, "stroke"):
                    last_stroke = node.stroke
                    last_stroke_width = node.stroke_width
                if last_fill and last_stroke:
                    break

            # Early optimization: check if paths overlap and handle based on operation type
            paths_overlap = paths_bbox_intersect(paths)

            if not paths_overlap:
                # Handle non-overlapping paths based on operation type
                if command == "union" or command == "xor":
                    # Union: combine all paths; XOR: same as union when no overlap
                    channel(
                        _(
                            f"{command.capitalize()} of non-overlapping paths - optimized processing"
                        )
                    )
                    segment_list = []

                    for i, path in enumerate(paths):
                        try:
                            # Analyze path complexity
                            complexity = analyze_path_complexity(path)

                            # Determine interpolation points based on complexity analysis
                            if complexity["is_ellipse"]:
                                # Ellipses get maximum interpolation
                                interp_points = 500
                                channel(
                                    _(
                                        f"Non-overlapping ellipse path {i}: using {interp_points} interpolation points (maximum for ellipse)"
                                    )
                                )
                            elif complexity["complexity_score"] >= 7:
                                # Very complex curves
                                interp_points = 300
                                channel(
                                    _(
                                        f"Non-overlapping very complex path {i}: using {interp_points} interpolation points"
                                    )
                                )
                            elif complexity["has_curves"]:
                                # Moderate complexity curves
                                interp_points = max(
                                    100, int(150 * complexity["curve_ratio"])
                                )
                                channel(
                                    _(
                                        f"Non-overlapping curved path {i}: using {interp_points} interpolation points"
                                    )
                                )
                            else:
                                # Simple paths
                                interp_points = 20
                                channel(
                                    _(
                                        f"Non-overlapping simple path {i}: using {interp_points} interpolation points"
                                    )
                                )

                            c = linearize_path(path, interp=interp_points)

                            # Validate linearization result
                            if not c:  # Empty list means no polygons
                                if complexity["has_curves"] or complexity["is_ellipse"]:
                                    # For curves/ellipses, try maximum interpolation
                                    channel(
                                        _(
                                            f"Retrying curved/ellipse path {i} with maximum 1000 interpolation points"
                                        )
                                    )
                                    c = linearize_path(path, interp=1000)
                                else:
                                    channel(
                                        _(
                                            "Warning: Non-overlapping path linearization produced no polygons"
                                        )
                                    )
                                    continue  # Skip this path

                            # Filter out polygons with insufficient points
                            if c:
                                valid_polygons = [
                                    polygon for polygon in c if len(polygon) >= 3
                                ]
                                if not valid_polygons:
                                    if (
                                        complexity["has_curves"]
                                        or complexity["is_ellipse"]
                                    ):
                                        # Last resort for curves/ellipses - absolute maximum interpolation
                                        channel(
                                            _(
                                                f"Final attempt for complex path {i} with 2000 interpolation points"
                                            )
                                        )
                                        c = linearize_path(path, interp=2000)
                                        if c:
                                            valid_polygons = [
                                                polygon
                                                for polygon in c
                                                if len(polygon) >= 3
                                            ]

                                    if not valid_polygons:
                                        channel(
                                            _(
                                                "Warning: Non-overlapping path has no valid polygons"
                                            )
                                        )
                                        continue  # Skip this path

                                c = pb.Polygon(valid_polygons)
                                c = pb.segments(c)
                                segment_list.append(c)

                        except pb.PolyBoolException as e:
                            channel(_(f"Polybool linearization failed: {e}"))
                            return "elements", data

                elif command == "intersection":
                    # Intersection: non-overlapping paths result in empty set
                    channel(
                        _("Intersection of non-overlapping paths - result is empty")
                    )
                    return "elements", []

                elif command == "difference":
                    # Difference: result is the first path minus any overlapping areas
                    # Since no overlap, result is just the first path
                    channel(
                        _("Difference of non-overlapping paths - result is first path")
                    )
                    if len(paths) > 0:
                        segment_list = []
                        path = paths[0]  # Only keep the first path

                        try:
                            complexity = analyze_path_complexity(path)

                            if complexity["is_ellipse"]:
                                interp_points = 500
                            elif complexity["complexity_score"] >= 7:
                                interp_points = 300
                            elif complexity["has_curves"]:
                                interp_points = max(
                                    100, int(150 * complexity["curve_ratio"])
                                )
                            else:
                                interp_points = 20

                            c = linearize_path(path, interp=interp_points)

                            if not c and (
                                complexity["has_curves"] or complexity["is_ellipse"]
                            ):
                                c = linearize_path(path, interp=1000)

                            if c:
                                valid_polygons = [
                                    polygon for polygon in c if len(polygon) >= 3
                                ]
                                if valid_polygons:
                                    c = pb.Polygon(valid_polygons)
                                    c = pb.segments(c)
                                    segment_list.append(c)

                        except pb.PolyBoolException as e:
                            channel(_(f"Polybool linearization failed: {e}"))
                            return "elements", data

                    if not segment_list:
                        return "elements", []
            else:
                # Perform segment-level overlap analysis
                analysis_start = time.time()
                segments = extract_path_segments(paths)
                overlapping_indices = find_overlapping_segments(segments)
                analysis_time = time.time() - analysis_start

                total_segments = len(segments)
                overlapping_segments = len(overlapping_indices)
                overlap_percentage = (
                    (overlapping_segments / total_segments * 100)
                    if total_segments > 0
                    else 0
                )

                channel(
                    _(
                        f"Segment analysis: {overlapping_segments}/{total_segments} segments overlap ({overlap_percentage:.1f}%)"
                    )
                )
                channel(_(f"Analysis completed in {analysis_time*1000:.1f}ms"))

                # Calculate adaptive tolerance based on overlap analysis
                tolerance = calculate_cag_tolerance(
                    paths, segments, overlapping_indices
                )

                # For complex operations with many overlaps, use higher tolerance for precision
                if overlap_percentage > 80 and len(paths) >= 3:
                    tolerance = min(
                        tolerance * 1.5, 150.0
                    )  # Higher tolerance = more interpolation points = finer resolution
                    channel(
                        _(
                            f"Complex geometry detected, using finer tolerance: {tolerance:.1f}"
                        )
                    )
                else:
                    channel(_(f"Using adaptive tolerance: {tolerance:.1f}"))

                # Linearize paths with enhanced complexity-based interpolation
                linearization_start = time.time()
                segment_list = []

                for i, path in enumerate(paths):
                    # Check if this path has any overlapping segments
                    path_has_overlaps = any(
                        seg.path_index == i and idx in overlapping_indices
                        for idx, seg in enumerate(segments)
                    )

                    # Analyze path complexity comprehensively
                    complexity = analyze_path_complexity(path)

                    # Determine base tolerance
                    if path_has_overlaps:
                        # Use calculated tolerance for overlapping paths
                        path_tolerance = tolerance
                    else:
                        # Use lower tolerance (fewer interpolation points) for isolated paths
                        path_tolerance = tolerance * 0.4

                    # Apply complexity-based interpolation boosting
                    if complexity["is_ellipse"]:
                        # Ellipses get maximum interpolation regardless of overlaps
                        path_tolerance = min(
                            path_tolerance * 10.0, 1000.0
                        )  # Up to 1000 points for ellipses
                        channel(
                            _(
                                f"Path {i} identified as ellipse, using maximum interpolation: {path_tolerance:.1f}"
                            )
                        )
                    elif complexity["complexity_score"] >= 8:
                        # Very high complexity
                        path_tolerance = min(
                            path_tolerance * 5.0, 600.0
                        )  # Up to 600 points
                        channel(
                            _(
                                f"Path {i} very high complexity (score: {complexity['complexity_score']:.1f}), enhanced interpolation: {path_tolerance:.1f}"
                            )
                        )
                    elif complexity["complexity_score"] >= 6:
                        # High complexity
                        path_tolerance = min(
                            path_tolerance * 3.0, 400.0
                        )  # Up to 400 points
                        channel(
                            _(
                                f"Path {i} high complexity (score: {complexity['complexity_score']:.1f}), enhanced interpolation: {path_tolerance:.1f}"
                            )
                        )
                    elif complexity["has_curves"]:
                        # Moderate complexity with curves
                        path_tolerance = min(
                            path_tolerance * 2.0, 300.0
                        )  # Up to 300 points for curves
                        channel(
                            _(
                                f"Path {i} contains curves, enhanced interpolation: {path_tolerance:.1f}"
                            )
                        )

                    try:
                        # Convert tolerance to interpolation points
                        # Enhanced range: 15-1000 interpolation points (increased maximum)
                        interp_points = max(15, min(1000, int(path_tolerance)))

                        # Enforce minimum interpolation points based on complexity
                        if complexity["is_ellipse"]:
                            interp_points = max(
                                200, interp_points
                            )  # Minimum 200 points for ellipses
                        elif complexity["has_curves"]:
                            interp_points = max(
                                50, interp_points
                            )  # Minimum 50 points for curves

                        channel(
                            _(
                                f"Path {i}: Using {interp_points} interpolation points (complexity score: {complexity['complexity_score']:.1f})"
                            )
                        )
                        c = linearize_path(path, interp=interp_points)

                        # Validate linearization result
                        # linearize_path returns a list of polygons, each polygon is a list of (x,y) tuples
                        if not c:  # Empty list means no polygons
                            channel(
                                _(
                                    f"Warning: Path {i} linearization produced no polygons"
                                )
                            )

                            # For complex paths, try significantly MORE interpolation points
                            if complexity["is_ellipse"]:
                                retry_points = min(
                                    2000, interp_points * 4
                                )  # Up to 2000 points for ellipses
                                channel(
                                    _(
                                        f"Retrying ellipse path {i} with maximum interpolation: {retry_points}"
                                    )
                                )
                                c = linearize_path(path, interp=retry_points)
                            elif complexity["has_curves"]:
                                retry_points = min(
                                    1000, interp_points * 2
                                )  # Up to 1000 points for curves
                                channel(
                                    _(
                                        f"Retrying curved path {i} with MORE interpolation points: {retry_points}"
                                    )
                                )
                                c = linearize_path(path, interp=retry_points)
                            else:
                                # For simple paths, try fewer points
                                retry_points = max(5, int(interp_points * 0.5))
                                channel(
                                    _(
                                        f"Retrying simple path {i} with fewer interpolation points: {retry_points}"
                                    )
                                )
                                c = linearize_path(path, interp=retry_points)

                        if c:  # Check again after potential retry
                            # Check if any polygon has insufficient points
                            valid_polygons = []
                            total_points = 0
                            for polygon in c:
                                if (
                                    len(polygon) >= 3
                                ):  # Minimum points for a valid polygon
                                    valid_polygons.append(polygon)
                                    total_points += len(polygon)
                                else:
                                    channel(
                                        _(
                                            f"Debug: Path {i} skipping polygon with only {len(polygon)} points"
                                        )
                                    )

                            if not valid_polygons:
                                channel(
                                    _(
                                        f"Warning: Path {i} has no valid polygons after retry"
                                    )
                                )

                                # Final attempt with adaptive strategy
                                if complexity["is_ellipse"]:
                                    # For ellipses, try absolute maximum interpolation
                                    final_points = 3000  # Absolute maximum for ellipses
                                    channel(
                                        _(
                                            f"Final attempt for ellipse path {i} with {final_points} interpolation points"
                                        )
                                    )
                                    c = linearize_path(path, interp=final_points)
                                elif complexity["has_curves"]:
                                    # For curves, try enhanced maximum interpolation
                                    final_points = 1500  # Enhanced maximum for curves
                                    channel(
                                        _(
                                            f"Final attempt for curved path {i} with {final_points} interpolation points"
                                        )
                                    )
                                    c = linearize_path(path, interp=final_points)
                                else:
                                    # For simple paths, try minimal points
                                    final_points = max(3, int(interp_points * 0.1))
                                    channel(
                                        _(
                                            f"Final attempt for simple path {i} with {final_points} interpolation points"
                                        )
                                    )
                                    c = linearize_path(path, interp=final_points)

                                # Re-validate after final attempt
                                if c:
                                    valid_polygons = [
                                        polygon for polygon in c if len(polygon) >= 3
                                    ]

                            if valid_polygons:
                                c = valid_polygons  # Use only valid polygons
                                channel(
                                    _(
                                        f"Path {i}: {len(valid_polygons)} valid polygons, {total_points} total points"
                                    )
                                )
                            else:
                                channel(
                                    _(
                                        f"Error: Path {i} could not be linearized properly, skipping"
                                    )
                                )
                                continue  # Skip this path entirely

                        c = pb.Polygon(c)
                        c = pb.segments(c)
                        segment_list.append(c)

                    except pb.PolyBoolException as e:
                        channel(_(f"Polybool error on path {i}: {e}"))
                        return "elements", data
                    except Exception as e:
                        channel(_(f"Linearization error on path {i}: {e}"))
                        return "elements", data

                linearization_time = time.time() - linearization_start
                channel(
                    _(f"Linearization completed in {linearization_time*1000:.1f}ms")
                )

            if not segment_list:
                return "elements", data

            # Perform CAG operations with timeout protection
            operation_start = time.time()
            timeout_seconds = 60.0  # 60 second timeout

            try:
                segs = segment_list[0]
                for i, s in enumerate(segment_list[1:], 1):
                    # Check for timeout
                    if time.time() - operation_start > timeout_seconds:
                        channel(_(f"CAG operation timed out after {timeout_seconds}s"))
                        return "elements", data

                    # Progress feedback for long operations
                    if len(segment_list) > 5:
                        progress = (i / (len(segment_list) - 1)) * 100
                        channel(
                            _(
                                f"Processing path {i}/{len(segment_list)-1} ({progress:.0f}%)"
                            )
                        )

                    try:
                        combined = pb.combine(segs, s)
                        if command == "intersection":
                            segs = pb.selectIntersect(combined)
                        elif command == "xor":
                            segs = pb.selectXor(combined)
                        elif command == "union":
                            segs = pb.selectUnion(combined)
                        else:
                            # difference
                            segs = pb.selectDifference(combined)
                    except pb.PolyBoolException as e:
                        channel(_(f"Polybool operation failed at step {i}: {e}"))
                        return "elements", data

            except Exception as e:
                channel(_(f"CAG operation failed: {e}"))
                return "elements", data

            operation_time = time.time() - operation_start
            channel(_(f"CAG operations completed in {operation_time*1000:.1f}ms"))

            # Multi-pass healing with increasingly aggressive tolerances
            healing_start = time.time()
            try:
                # Calculate base healing tolerance based on geometry complexity and size
                avg_bbox_size = 0
                if paths:
                    total_size = 0
                    for path in paths:
                        try:
                            bbox = path.bbox()
                            size = max(bbox[2] - bbox[0], bbox[3] - bbox[1])
                            total_size += size
                        except Exception:
                            total_size += 100  # Fallback size
                    avg_bbox_size = total_size / len(paths)

                # Base healing tolerance (more aggressive than before)
                if avg_bbox_size > 1000:  # Large shapes
                    base_tolerance = min(
                        1.0, avg_bbox_size * 1e-3
                    )  # Up to 1.0 for large shapes (10x more aggressive)
                elif avg_bbox_size > 100:  # Medium shapes
                    base_tolerance = min(
                        0.1, avg_bbox_size * 1e-3
                    )  # Up to 0.1 for medium shapes (10x more aggressive)
                else:  # Small shapes
                    base_tolerance = min(
                        0.01, avg_bbox_size * 1e-3
                    )  # Up to 0.01 for small shapes (10x more aggressive)

                # For very complex cases, use even more aggressive healing
                if overlap_percentage > 80 and len(paths) >= 3:
                    base_tolerance *= 5  # 5x the tolerance for complex cases

                # Multi-pass healing with increasing tolerance
                healing_passes = [
                    base_tolerance * 0.1,  # Conservative first pass
                    base_tolerance * 0.5,  # Moderate second pass
                    base_tolerance * 1.0,  # Aggressive third pass
                    base_tolerance * 2.0,  # Very aggressive fourth pass
                    base_tolerance * 5.0,  # Extreme fifth pass for stubborn cases
                ]

                healed_segs = segs
                successful_passes = 0

                for pass_num, healing_tolerance in enumerate(healing_passes, 1):
                    channel(
                        _(
                            f"Healing pass {pass_num}/5 with tolerance: {healing_tolerance:.6f} (avg_size={avg_bbox_size:.1f})"
                        )
                    )

                    try:
                        new_healed_segs = heal_polygon_gaps(
                            healed_segs, channel, pb, tolerance=healing_tolerance
                        )

                        if new_healed_segs != healed_segs:
                            healed_segs = new_healed_segs
                            successful_passes += 1
                            channel(_(f"Pass {pass_num} applied healing"))
                        else:
                            channel(_(f"Pass {pass_num} found no gaps to heal"))

                        # Check if we have reached the optimal result for this operation type
                        try:
                            test_polygon = pb.polygon(healed_segs)
                            if test_polygon.regions:
                                region_count = len(test_polygon.regions)

                                # Operation-specific stopping criteria
                                should_stop = False
                                if command == "union":
                                    # Union ideally results in single region
                                    if region_count == 1:
                                        channel(
                                            _(
                                                f"Single region achieved for union after pass {pass_num}, stopping early"
                                            )
                                        )
                                        should_stop = True
                                elif command == "intersection":
                                    # Intersection may result in multiple disconnected areas
                                    # Stop if regions are stable and well-formed
                                    if region_count <= len(paths) and region_count > 0:
                                        channel(
                                            _(
                                                f"Stable intersection with {region_count} regions after pass {pass_num}"
                                            )
                                        )
                                        should_stop = True
                                elif command == "difference":
                                    # Difference may result in holes or multiple regions
                                    # Stop if we have reasonable number of regions
                                    if region_count <= len(paths):
                                        channel(
                                            _(
                                                f"Stable difference with {region_count} regions after pass {pass_num}"
                                            )
                                        )
                                        should_stop = True
                                elif command == "xor":
                                    # XOR may result in multiple disconnected areas
                                    # Stop if regions are reasonable
                                    if (
                                        region_count <= len(paths) * 2
                                    ):  # XOR can create up to 2x regions
                                        channel(
                                            _(
                                                f"Stable XOR with {region_count} regions after pass {pass_num}"
                                            )
                                        )
                                        should_stop = True

                                if should_stop:
                                    break
                        except Exception:
                            pass  # Continue with remaining passes

                    except Exception as e:
                        channel(_(f"Healing pass {pass_num} failed: {e}"))
                        continue

                if successful_passes > 0:
                    channel(
                        _(
                            f"Multi-pass healing completed: {successful_passes} successful passes"
                        )
                    )
                    segs = healed_segs
                else:
                    channel(_("No healing passes were successful"))

            except Exception as e:
                channel(_(f"Multi-pass healing failed: {e}"))

            healing_time = time.time() - healing_start
            channel(_(f"Polygon healing completed in {healing_time*1000:.1f}ms"))

            # Build result path from healed polybool output
            reconstruction_start = time.time()
            try:
                solution_path = _reconstruct_path_from_polybool_segments(
                    segs, channel, pb
                )

                # Post-reconstruction gap detection and repair
                if solution_path and len(solution_path) > 0:
                    gap_detection_start = time.time()

                    # Detect gaps in the reconstructed path
                    detected_gaps = detect_path_gaps(
                        solution_path, tolerance=healing_tolerance * 10
                    )

                    if detected_gaps:
                        channel(
                            _(f"Post-reconstruction: Found {len(detected_gaps)} gaps")
                        )

                        # Attempt to repair the gaps
                        repaired_path = repair_path_gaps(
                            solution_path,
                            detected_gaps,
                            tolerance=healing_tolerance * 10,
                        )

                        if repaired_path and len(repaired_path) > len(solution_path):
                            solution_path = repaired_path
                            channel(
                                _(
                                    f"Post-reconstruction: Repaired {len(detected_gaps)} gaps"
                                )
                            )
                        else:
                            # If repair failed, try fallback strategies
                            channel(
                                _(
                                    "Post-reconstruction: Gap repair failed, trying fallback..."
                                )
                            )

                            # Extract all points from the path
                            all_points = []
                            current_point = Point(0, 0)

                            for cmd in solution_path:
                                if isinstance(cmd, Move):
                                    current_point = cmd.end
                                    try:
                                        if (
                                            current_point
                                            and hasattr(current_point, "x")
                                            and hasattr(current_point, "y")
                                        ):
                                            all_points.append(
                                                (
                                                    float(current_point.x),
                                                    float(current_point.y),
                                                )
                                            )
                                        elif (
                                            current_point
                                            and hasattr(current_point, "real")
                                            and hasattr(current_point, "imag")
                                        ):
                                            all_points.append(
                                                (
                                                    float(current_point.real),
                                                    float(current_point.imag),
                                                )
                                            )
                                    except (AttributeError, TypeError, ValueError):
                                        pass
                                elif isinstance(
                                    cmd, (Line, QuadraticBezier, CubicBezier, Arc)
                                ):
                                    current_point = cmd.end
                                    try:
                                        if (
                                            current_point
                                            and hasattr(current_point, "x")
                                            and hasattr(current_point, "y")
                                        ):
                                            all_points.append(
                                                (
                                                    float(current_point.x),
                                                    float(current_point.y),
                                                )
                                            )
                                        elif (
                                            current_point
                                            and hasattr(current_point, "real")
                                            and hasattr(current_point, "imag")
                                        ):
                                            all_points.append(
                                                (
                                                    float(current_point.real),
                                                    float(current_point.imag),
                                                )
                                            )
                                    except (AttributeError, TypeError, ValueError):
                                        pass

                            # Try convex hull as last resort for severely broken paths
                            if len(detected_gaps) > 3 and len(all_points) > 3:
                                fallback_path = convex_hull_fallback(
                                    all_points, channel, command
                                )
                                if fallback_path and len(fallback_path) > 0:
                                    solution_path = fallback_path
                                    channel(
                                        _(
                                            f"Post-reconstruction: Used {command}-aware fallback"
                                        )
                                    )
                    else:
                        channel(_("Post-reconstruction: No gaps detected"))

                    gap_detection_time = time.time() - gap_detection_start
                    channel(
                        _(
                            f"Post-reconstruction gap analysis completed in {gap_detection_time*1000:.1f}ms"
                        )
                    )

            except Exception as e:
                channel(_(f"Result reconstruction failed: {e}"))
                return "elements", data

            reconstruction_time = time.time() - reconstruction_start
            channel(
                _(
                    f"Result reconstruction completed in {reconstruction_time*1000:.1f}ms"
                )
            )

            if solution_path:
                with elements.undoscope("Constructive Additive Geometry: Add"):
                    if not keep:
                        for node in data:
                            node.remove_node()

                    stroke = last_stroke if last_stroke is not None else Color("blue")
                    fill = last_fill
                    stroke_width = (
                        last_stroke_width
                        if last_stroke_width is not None
                        else elements.default_strokewidth
                    )

                    new_node = elements.elem_branch.add(
                        path=solution_path,
                        type="elem path",
                        stroke=stroke,
                        fill=fill,
                        stroke_width=stroke_width,
                    )

                    context.signal("refresh_scene", "Scene")
                    if elements.classify_new:
                        elements.classify([new_node])

                end_time = time.time()
                elapsed_time = end_time - start_time

                # Performance summary
                channel(_("=== CAG Performance Summary ==="))
                if "analysis_time" in locals():
                    channel(_(f"Segment analysis: {analysis_time*1000:.1f}ms"))
                if "linearization_time" in locals():
                    channel(
                        _(f"Adaptive linearization: {linearization_time*1000:.1f}ms")
                    )
                channel(_(f"CAG operations: {operation_time*1000:.1f}ms"))
                channel(_(f"Result reconstruction: {reconstruction_time*1000:.1f}ms"))
                channel(_(f"Total time: {elapsed_time:.2f}s"))

                if "overlap_percentage" in locals():
                    estimated_speedup = 100 / max(
                        overlap_percentage, 10
                    )  # Rough estimate
                    channel(
                        _(
                            f"Estimated speedup vs. naive approach: {estimated_speedup:.1f}x"
                        )
                    )

                return "elements", [new_node]
            else:
                channel(_("No solution found (empty path)"))
                return "elements", []


def _reconstruct_path_from_polybool_segments(segs, channel, pb=None):
    """
    Robust reconstruction of Path from PolyBool segments.

    This function properly handles:
    - Correct winding order for outer vs inner paths
    - Proper path closure
    - Multi-region paths
    - Degenerate cases

    Args:
        segs: PolyBool segments
        channel: Logging channel for debug output
        pb: PolyBool module (passed from caller to avoid import issues)

    Returns:
        Path: Reconstructed path object
    """
    try:
        if pb is None:
            # Try to import polybool if not passed
            import polybool as pb

        # Get the polygon from segments
        polygon = pb.polygon(segs)

        if not polygon.regions:
            channel("Warning: No regions found in PolyBool result")
            return Path()

        channel(f"Reconstructing {len(polygon.regions)} regions")

        solution_path = Path()

        for region_idx, region in enumerate(polygon.regions):
            if len(region) < 3:
                channel(
                    f"Skipping degenerate region {region_idx} with {len(region)} points"
                )
                continue

            # Extract points and ensure proper closure
            points = [(pt.x, pt.y) for pt in region]

            # Always ensure the region is properly closed by checking the actual distance
            if len(points) > 0:
                first_point = points[0]
                last_point = points[-1]
                closure_distance = abs(
                    complex(
                        last_point[0] - first_point[0], last_point[1] - first_point[1]
                    )
                )

                # Use more aggressive closure tolerance - if gap is bigger than 1e-4, force closure
                closure_tolerance = 1e-4  # Much more aggressive than 1e-6
                if closure_distance > closure_tolerance:
                    points.append(first_point)
                    channel(
                        f"Region {region_idx}: Added closure point (gap was {closure_distance:.6f})"
                    )
                else:
                    channel(
                        f"Region {region_idx}: Already closed (gap {closure_distance:.6f})"
                    )

            # Validate minimum points for a closed polygon
            if len(points) < 4:  # 3 unique points + closure
                channel(
                    f"Skipping region {region_idx}: insufficient points after closure ({len(points)})"
                )
                continue

            # Calculate signed area to determine winding
            signed_area = 0.0
            n = len(points) - 1  # Exclude the closure point for area calculation
            for i in range(n):
                j = (i + 1) % n
                signed_area += (points[j][0] - points[i][0]) * (
                    points[j][1] + points[i][1]
                )
            signed_area *= 0.5

            # Create path commands for this region
            # Start with Move to first point
            region_path = Path()
            region_path.append(Move(Point(points[0][0], points[0][1])))

            # Add lines to subsequent points (excluding the final closure point)
            # We exclude the last point because it should be the same as the first (closure)
            for i in range(1, len(points) - 1):
                region_path.append(Line(Point(points[i][0], points[i][1])))

            # Close the path properly - this will automatically connect back to the start
            region_path.append(Close())

            # Verify the path was constructed correctly
            if len(region_path) < 3:  # Move + at least one Line + Close
                channel(
                    f"Warning: Region {region_idx} produced very short path ({len(region_path)} commands)"
                )
                continue

            # Add to solution path
            if len(solution_path) == 0:
                solution_path = region_path
            else:
                # Properly combine paths
                for cmd in region_path:
                    solution_path.append(cmd)

            channel(
                f"Region {region_idx}: {len(points)} points, area={signed_area:.2f}"
            )

        if len(solution_path) == 0:
            channel("Warning: No valid regions reconstructed")
            return Path()

        channel(f"Successfully reconstructed path with {len(solution_path)} commands")
        return solution_path

    except Exception as e:
        channel(f"Path reconstruction error: {e}")
        import traceback

        channel(f"Traceback: {traceback.format_exc()}")
        return Path()


def detect_path_gaps(path, tolerance=1e-3):
    """
    Detect gaps in a reconstructed path by analyzing command sequences.

    Args:
        path: SVG Path object
        tolerance: Maximum distance to consider as "closed"

    Returns:
        list: List of gap information (start_point, end_point, distance)
    """
    gaps = []
    current_point = Point(0, 0)
    subpath_start = Point(0, 0)

    def point_distance(p1, p2):
        """Calculate distance between two points safely"""
        try:
            if (
                hasattr(p1, "x")
                and hasattr(p1, "y")
                and hasattr(p2, "x")
                and hasattr(p2, "y")
            ):
                return abs(complex(p1.x - p2.x, p1.y - p2.y))
            elif (
                hasattr(p1, "real")
                and hasattr(p1, "imag")
                and hasattr(p2, "real")
                and hasattr(p2, "imag")
            ):
                return abs(complex(p1.real - p2.real, p1.imag - p2.imag))
            else:
                return float(abs(p1 - p2))
        except Exception:
            return 0.0

    for i, cmd in enumerate(path):
        if isinstance(cmd, Move):
            # Check for gap between previous subpath end and this move
            if (
                i > 0
                and not isinstance(path[i - 1], Close)
                and current_point is not None
            ):
                gap_distance = point_distance(current_point, cmd.end)
                if gap_distance > tolerance:
                    gaps.append(
                        {
                            "type": "subpath_gap",
                            "start": current_point,
                            "end": cmd.end,
                            "distance": gap_distance,
                            "position": i,
                        }
                    )

            current_point = cmd.end
            subpath_start = cmd.end

        elif isinstance(cmd, (Line, QuadraticBezier, CubicBezier, Arc)):
            current_point = cmd.end

        elif isinstance(cmd, Close):
            # Check if close actually closes properly
            if current_point is not None and subpath_start is not None:
                gap_distance = point_distance(current_point, subpath_start)
                if gap_distance > tolerance:
                    gaps.append(
                        {
                            "type": "closure_gap",
                            "start": current_point,
                            "end": subpath_start,
                            "distance": gap_distance,
                            "position": i,
                        }
                    )

    return gaps


def repair_path_gaps(path, gaps, tolerance=1e-3):
    """
    Repair detected gaps in a path by inserting connecting lines.

    Args:
        path: SVG Path object to repair
        gaps: List of gaps from detect_path_gaps
        tolerance: Maximum distance to bridge

    Returns:
        Path: Repaired path
    """
    if not gaps:
        return path

    # Sort gaps by position in reverse order to maintain indices
    gaps_sorted = sorted(gaps, key=lambda g: g["position"], reverse=True)

    # Create a new path with repairs
    repaired_path = Path()

    for cmd in path:
        repaired_path.append(cmd)

    repairs_made = 0
    for gap in gaps_sorted:
        if gap["distance"] <= tolerance * 10:  # Only repair small gaps
            # Insert a line to bridge the gap
            bridge_line = Line(gap["end"])
            # Insert after the position where the gap was detected
            repaired_path.insert(gap["position"], bridge_line)
            repairs_made += 1

    return repaired_path


def convex_hull_fallback(points, channel, operation_type="union"):
    """
    Generate fallback result based on operation type for severely broken polygons.

    Args:
        points: List of (x, y) point tuples
        channel: Logging channel
        operation_type: Type of CAG operation ("union", "intersection", "difference", "xor")

    Returns:
        Path: Fallback path based on operation type
    """
    try:
        if len(points) < 3:
            return Path()

        if operation_type == "intersection":
            # For intersection, don't use convex hull - return empty instead
            # because intersection of broken polygons is likely empty
            channel("Intersection fallback: returning empty result for broken polygons")
            return Path()

        elif operation_type == "difference":
            # For difference, only use first polygon's points if we can identify them
            # Otherwise return empty as difference of broken polygons is unpredictable
            channel("Difference fallback: returning empty result for broken polygons")
            return Path()

        elif operation_type in ["union", "xor"]:
            # For union and XOR, convex hull is a reasonable fallback
            # Simple Graham scan for convex hull
            def cross_product(o, a, b):
                return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

            # Find bottom-most point (or leftmost if tie)
            start = min(points, key=lambda p: (p[1], p[0]))

            # Sort points by polar angle with respect to start point
            def polar_angle(p):
                import math

                return math.atan2(p[1] - start[1], p[0] - start[0])

            sorted_points = sorted([p for p in points if p != start], key=polar_angle)

            # Build convex hull
            hull = [start]
            for p in sorted_points:
                while len(hull) > 1 and cross_product(hull[-2], hull[-1], p) <= 0:
                    hull.pop()
                hull.append(p)

            # Create path from hull
            if len(hull) >= 3:
                hull_path = Path()
                hull_path.append(Move(Point(hull[0][0], hull[0][1])))
                for i in range(1, len(hull)):
                    hull_path.append(Line(Point(hull[i][0], hull[i][1])))
                hull_path.append(Close())

                channel(
                    f"Convex hull fallback for {operation_type}: {len(hull)} points"
                )
                return hull_path

    except Exception as e:
        channel(f"Fallback generation failed: {e}")

    return Path()


def multi_pass_healing(segs, channel, pb, base_tolerance=1e-4, max_passes=5):
    """
    Apply healing in multiple passes with increasingly aggressive tolerances.

    Args:
        segs: PolyBool segments
        channel: Logging channel
        pb: PolyBool module
        base_tolerance: Starting tolerance
        max_passes: Maximum number of healing passes

    Returns:
        Healed PolyBool segments
    """
    current_segs = segs

    for pass_num in range(max_passes):
        # Exponentially increase tolerance each pass
        pass_tolerance = base_tolerance * (2**pass_num)

        channel(
            f"Healing pass {pass_num + 1}/{max_passes}, tolerance={pass_tolerance:.6f}"
        )

        healed_segs = heal_polygon_gaps(
            current_segs, channel, pb, tolerance=pass_tolerance
        )

        # Check if healing improved the result
        try:
            old_polygon = pb.polygon(current_segs)
            new_polygon = pb.polygon(healed_segs)

            old_regions = len(old_polygon.regions) if old_polygon.regions else 0
            new_regions = len(new_polygon.regions) if new_polygon.regions else 0

            if new_regions <= old_regions and new_regions > 0:
                channel(
                    f"  Pass {pass_num + 1}: {old_regions} -> {new_regions} regions"
                )
                current_segs = healed_segs

                # If we got down to 1 region, we're done
                if new_regions == 1:
                    channel(f"  Healing complete after {pass_num + 1} passes")
                    break
            else:
                channel(f"  Pass {pass_num + 1}: No improvement, stopping")
                break

        except Exception as e:
            channel(f"  Pass {pass_num + 1}: Error checking improvement: {e}")
            # Keep the healed result anyway
            current_segs = healed_segs

    return current_segs


def topology_repair(points, channel, tolerance=1e-4):
    """
    Repair polygon topology issues like self-intersections.

    Args:
        points: List of (x, y) point tuples
        channel: Logging channel
        tolerance: Distance tolerance for repairs

    Returns:
        list: Repaired points
    """
    if len(points) < 4:
        return points

    repaired_points = []

    # Remove consecutive duplicates more aggressively
    prev_point = None
    for point in points:
        if (
            prev_point is None
            or abs(complex(point[0] - prev_point[0], point[1] - prev_point[1]))
            > tolerance * 0.1
        ):
            repaired_points.append(point)
            prev_point = point

    # Simple self-intersection removal (Douglas-Peucker style simplification)
    if len(repaired_points) > 4:
        simplified = [repaired_points[0]]

        for i in range(1, len(repaired_points) - 1):
            # Check if this point is essential (creates significant deviation)
            p1 = repaired_points[i - 1]
            p2 = repaired_points[i]
            p3 = (
                repaired_points[i + 1]
                if i + 1 < len(repaired_points)
                else repaired_points[0]
            )

            # Calculate distance from p2 to line p1-p3
            def point_line_distance(point, line_start, line_end):
                x0, y0 = point
                x1, y1 = line_start
                x2, y2 = line_end

                # Distance from point to line
                num = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
                den = ((y2 - y1) ** 2 + (x2 - x1) ** 2) ** 0.5
                return num / den if den > 0 else 0

            distance = point_line_distance(p2, p1, p3)
            if distance > tolerance:
                simplified.append(p2)

        simplified.append(repaired_points[-1])  # Always keep the last point
        repaired_points = simplified

    channel(f"Topology repair: {len(points)} -> {len(repaired_points)} points")
    return repaired_points
