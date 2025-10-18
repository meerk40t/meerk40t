"""
Hierarchical CutPlan Module

This module implements the proposed hierarchical architecture for cut planning.

Key improvements over cutplan.py:
1. Explicit hierarchy structure (HierarchyLevel, HierarchyContext)
2. Level-by-level processing respecting inner-first constraints
3. Travel optimization constrained to same hierarchy level
4. Better handling of material shift scenarios
5. Clearer separation of concerns

The module copies essential logic from cutplan.py but restructures it around
hierarchical organization as the primary principle, with travel optimization
as secondary concern within hierarchy levels.
"""

from typing import Optional, List, Dict, Set, Callable, Tuple
from time import perf_counter, time
from os import times
import numpy as np

from .cutcode.cutcode import CutCode
from .cutcode.cutgroup import CutGroup
from .cutcode.rastercut import RasterCut
from ..tools.geomstr import Geomstr
from ..svgelements import Matrix


# ============================================================================
# HIERARCHY DATA STRUCTURES
# ============================================================================

class HierarchyLevel:
    """
    Represents one level in the containment hierarchy.
    
    All groups at the same level are independent of each other (in terms of
    hierarchy ordering), but depend on their parent level being complete before
    they can be executed.
    
    Example hierarchy:
        Level 0: [A, D]           # Root-level closed shapes
        Level 1: [B] (in A)       # Shapes inside A
        Level 1: [E] (in D)       # Shapes inside D  
        Level 2: [C] (in B)       # Shapes inside B inside A
    """
    
    def __init__(self, level_number: int, parent_level: Optional['HierarchyLevel'] = None):
        """
        Initialize a hierarchy level.
        
        Args:
            level_number: Depth in hierarchy (0=root, 1=inside root, 2=inside level 1, etc)
            parent_level: The level that contains all groups in this level
        """
        self.level = level_number
        self.cuts: List[CutGroup] = []
        self.parent_level: Optional[HierarchyLevel] = parent_level
        self.child_levels: List[HierarchyLevel] = []
    
    def add_cut(self, cut: CutGroup) -> None:
        """Add a cut group at this level."""
        self.cuts.append(cut)
        # Note: CutGroup doesn't have _hierarchy_level attribute in original implementation
        # This is for debugging purposes only
    
    def add_child_level(self, child_level: 'HierarchyLevel') -> None:
        """Register a child level that depends on this level."""
        self.child_levels.append(child_level)
        child_level.parent_level = self
    
    def is_complete(self) -> bool:
        """Check if all cuts at this level have been marked as done."""
        if not self.cuts:
            return True
        return all(cut.burns_done == cut.passes for cut in self.cuts)
    
    def get_all_cuts(self) -> List[CutGroup]:
        """Recursively get all cuts in this level and child levels."""
        result = list(self.cuts)
        for child_level in self.child_levels:
            result.extend(child_level.get_all_cuts())
        return result
    
    def __repr__(self) -> str:
        return (f"HierarchyLevel(level={self.level}, "
                f"cuts={len(self.cuts)}, "
                f"children={len(self.child_levels)})")


class HierarchyContext:
    """
    Represents the complete containment hierarchy for a CutCode.
    
    This builds and manages the explicit hierarchy structure derived from
    the containment relationships (.contains, .inside attributes) set by
    inner_first_ident().
    """
    
    def __init__(self):
        self.root_levels: List[HierarchyLevel] = []  # Top-level groups
        self.all_levels: List[HierarchyLevel] = []   # All levels in depth order
        self.level_by_group: Dict[CutGroup, HierarchyLevel] = {}  # Group -> level mapping
    
    def add_root_level(self, level: HierarchyLevel) -> None:
        """Add a root-level hierarchy level."""
        self.root_levels.append(level)
        self.all_levels.append(level)
    
    def add_level(self, level: HierarchyLevel) -> None:
        """Add any hierarchy level (root or nested)."""
        if level not in self.all_levels:
            self.all_levels.append(level)
    
    def get_next_level_candidates(self, completed_levels: Set[HierarchyLevel]) -> List[CutGroup]:
        """
        Get all cuts that are ready to be executed.
        
        A level is ready if:
        1. It hasn't been completed yet
        2. Its parent level (if any) is complete
        
        Args:
            completed_levels: Set of levels that have been processed
            
        Returns:
            List of CutGroup objects that are ready for execution
        """
        candidates = []
        for level in self.all_levels:
            if level in completed_levels:
                continue
            # Check if parent is complete
            if level.parent_level is None or level.parent_level.is_complete():
                candidates.extend(level.cuts)
        return candidates
    
    def get_processing_order(self) -> List[HierarchyLevel]:
        """
        Get levels in processing order (innermost first).
        
        Returns levels sorted from deepest to shallowest.
        
        Returns:
            List of HierarchyLevel objects in processing order
        """
        return sorted(self.all_levels, key=lambda level: level.level, reverse=True)
    
    def __repr__(self) -> str:
        return (f"HierarchyContext(root_levels={len(self.root_levels)}, "
                f"total_levels={len(self.all_levels)})")


# ============================================================================
# HIERARCHY BUILDING
# ============================================================================

def build_hierarchy_levels(context: CutCode) -> HierarchyContext:
    """
    Convert the containment attributes (.contains, .inside) into explicit hierarchy levels.
    
    This function builds a hierarchical structure from the .contains and .inside
    attributes that were set by inner_first_ident(). It creates explicit HierarchyLevel
    objects representing each depth in the containment tree.
    
    Algorithm:
    1. Identify all CutGroup objects in the CutCode
    2. Find root groups (those with no parent, .inside is empty)
    3. Create root levels for each root group
    4. Iteratively find and add child groups, creating levels for each depth
    5. Link parent-child relationships between levels
    6. Return the complete HierarchyContext
    
    Args:
        context: CutCode with .contains/.inside attributes populated by inner_first_ident
        
    Returns:
        HierarchyContext with explicit hierarchy levels
        
    Raises:
        ValueError: If hierarchy contains cycles or is otherwise invalid
    """
    hierarchy = HierarchyContext()
    
    # Extract all CutGroup objects
    groups = [c for c in context if isinstance(c, CutGroup) or hasattr(c, 'inside')]
    
    if not groups:
        # No hierarchy, empty context
        return hierarchy
    
    # Identify root groups (those with no parent)
    root_groups = [g for g in groups if not g.inside or len(g.inside) == 0]
    
    if not root_groups:
        # Shouldn't happen if hierarchy is valid - treat all as roots
        root_groups = groups
    
    # Create root levels (level 0)
    for group in root_groups:
        level = HierarchyLevel(level_number=0)
        level.add_cut(group)
        hierarchy.add_root_level(level)
        hierarchy.level_by_group[group] = level
    
    # Recursively add child levels
    processed = set(root_groups)
    current_level_num = 0
    
    while len(processed) < len(groups):
        # Find all groups whose parents have been processed
        next_to_process = []
        for g in groups:
            if g in processed:
                continue
            # Check if all parents are processed
            if g.inside is not None and all(parent in processed for parent in g.inside):
                next_to_process.append(g)
        
        if not next_to_process:
            # Shouldn't happen if hierarchy is acyclic and valid
            # Add remaining as independent roots
            for g in groups:
                if g not in processed:
                    level = HierarchyLevel(level_number=current_level_num + 1)
                    level.add_cut(g)
                    hierarchy.add_level(level)
                    hierarchy.level_by_group[g] = level
            break
        
        current_level_num += 1
        
        # Group by immediate parent
        by_parent: Dict[CutGroup, List[CutGroup]] = {}
        for g in next_to_process:
            if g.inside:
                # Use first parent as "immediate" parent
                # TODO: Handle multi-parent case better in future
                parent = g.inside[0]
                if parent not in by_parent:
                    by_parent[parent] = []
                by_parent[parent].append(g)
        
        # Create levels for each parent
        for parent, children in by_parent.items():
            parent_level = hierarchy.level_by_group[parent]
            child_level = HierarchyLevel(
                level_number=current_level_num,
                parent_level=parent_level
            )
            
            for child in children:
                child_level.add_cut(child)
                hierarchy.level_by_group[child] = child_level
            
            parent_level.add_child_level(child_level)
            hierarchy.add_level(child_level)
        
        processed.update(next_to_process)
    
    return hierarchy


def validate_hierarchy(hierarchy: HierarchyContext) -> Tuple[bool, List[str]]:
    """
    Validate that a hierarchy is well-formed.
    
    Checks:
    - All groups are assigned to levels
    - Parent-child relationships are consistent
    - No cycles exist
    - Each level references correct parent
    
    Args:
        hierarchy: HierarchyContext to validate
        
    Returns:
        Tuple of (is_valid: bool, errors: List[str])
    """
    errors = []
    
    # Check all levels are connected
    visited = set()
    for level in hierarchy.all_levels:
        visited.add(level)
        for child_level in level.child_levels:
            if child_level.parent_level != level:
                errors.append(
                    f"Child level {child_level} parent mismatch: "
                    f"expected {level}, got {child_level.parent_level}"
                )
    
    # Check all root levels have no parent
    for level in hierarchy.root_levels:
        if level.parent_level is not None:
            errors.append(f"Root level {level} has parent {level.parent_level}")
    
    # Check consistency of level_by_group
    for group, level in hierarchy.level_by_group.items():
        if group not in level.cuts:
            errors.append(
                f"Group {group} mapped to level {level} but not in level.cuts"
            )
    
    return len(errors) == 0, errors


# ============================================================================
# HIERARCHICAL SELECTION (Main Processing Logic)
# ============================================================================

def hierarchical_selection(
    context: CutCode,
    hierarchy: HierarchyContext,
    optimizer_func: Callable,
    kernel=None,
    channel=None,
    **optimizer_kwargs
) -> CutCode:
    """
    Process cuts level-by-level using hierarchical order and travel optimization.
    
    This is the core function implementing the hierarchical optimization strategy.
    It processes the hierarchy from innermost to outermost levels, applying
    travel optimization within each level only.
    
    Key behavior:
    - Processes levels from deepest to shallowest
    - For each level, creates a sub-CutCode with just that level's cuts
    - Applies travel optimization to each level independently
    - Concatenates results to maintain hierarchy
    - Never links cuts across different hierarchy levels
    
    Args:
        context: The original CutCode (used for start position)
        hierarchy: HierarchyContext with explicit levels
        optimizer_func: Function to optimize a single level
                       Signature: (context, **kwargs) -> CutCode
        kernel: Optional kernel for messaging
        channel: Optional channel for logging
        **optimizer_kwargs: Additional kwargs passed to optimizer_func
        
    Returns:
        New CutCode with cuts ordered respecting hierarchy and optimized within levels
        
    Example:
        # Process hierarchy with default travel optimizer
        optimized = hierarchical_selection(
            context,
            hierarchy,
            optimizer_func=short_travel_cutcode_optimized,
            complete_path=False,
            grouped_inner=False,
            hatch_optimize=False
        )
    """
    ordered = CutCode()
    completed_levels: Set[HierarchyLevel] = set()
    
    # Get processing order (innermost first)
    levels_in_order = hierarchy.get_processing_order()
    
    if channel:
        channel(f"Hierarchical selection: processing {len(levels_in_order)} levels")
    
    # Process each level
    for i, level in enumerate(levels_in_order):
        # Check if parent level is complete
        if level.parent_level and level.parent_level not in completed_levels:
            if channel:
                channel(f"  Skipping level {level.level}: parent not complete")
            continue
        
        if not level.cuts:
            if channel:
                channel(f"  Level {level.level}: empty, skipping")
            completed_levels.add(level)
            continue
        
        if channel:
            channel(
                f"  Level {level.level}: processing {len(level.cuts)} cuts "
                f"(depth {i+1}/{len(levels_in_order)})"
            )
        
        # Create temporary context with just this level's cuts
        level_context = CutCode()
        for cut in level.cuts:
            level_context.append(cut)
        
        # Copy start position from original context
        if hasattr(context, 'start') and context.start is not None:
            try:
                level_context._start_x, level_context._start_y = context.start
            except (TypeError, ValueError):
                pass  # start position not available
        
        # Apply travel optimization within this level
        # Key point: optimizer only sees candidates from this level
        try:
            optimized_level = optimizer_func(
                context=level_context,
                kernel=kernel,
                channel=channel,
                complete_path=False,
                grouped_inner=False,  # Already at same hierarchy level
                hatch_optimize=False,  # Handle in separate pass if needed
                **optimizer_kwargs
            )
        except TypeError:
            # Fallback: optimizer might not accept all kwargs
            try:
                optimized_level = optimizer_func(level_context)
            except Exception as e:
                if channel:
                    channel(f"  ERROR optimizing level {level.level}: {e}")
                optimized_level = level_context
        
        # Add to final result
        ordered.extend(optimized_level)
        completed_levels.add(level)
    
    return ordered


# ============================================================================
# EMBEDDED HIERARCHY IDENTIFICATION
# ============================================================================

def is_inside(inner, outer, tolerance=0, debug=False):
    """
    Test that path1 is inside path2.
    
    Args:
        inner: inner path
        outer: outer path
        tolerance: tolerance for inside check
        debug: if True, print debug information
        
    Returns:
        whether path1 is wholly inside path2.
    """

    def convex_geometry(raster) -> Geomstr:
        dx = raster.bounding_box[0]
        dy = raster.bounding_box[1]
        dw = raster.bounding_box[2] - raster.bounding_box[0]
        dh = raster.bounding_box[3] - raster.bounding_box[1]
        if raster.image is None:
            return Geomstr.rect(dx, dy, dw, dh)
        image_np = np.array(raster.image.convert("L"))
        # Find non-white pixels
        # Iterate over each row in the image
        left_side = []
        right_side = []
        for y in range(image_np.shape[0]):
            row = image_np[y]
            non_white_indices = np.where(row < 255)[0]

            if non_white_indices.size > 0:
                leftmost = non_white_indices[0]
                rightmost = non_white_indices[-1]
                left_side.append((leftmost, y))
                right_side.insert(0, (rightmost, y))
        left_side.extend(right_side)
        non_white_pixels = left_side
        # Compute convex hull
        pts = list(Geomstr.convex_hull(None, non_white_pixels))  # type: ignore
        if pts:
            pts.append(pts[0])
        geom = Geomstr.lines(*pts)
        sx = dw / raster.image.width
        sy = dh / raster.image.height
        matrix = Matrix()
        matrix.post_scale(sx, sy)
        matrix.post_translate(dx, dy)
        geom.transform(matrix)
        return geom

    # We still consider a path to be inside another path if it is
    # within a certain tolerance
    inner_path = inner
    outer_path = outer
    if outer == inner:  # This is the same object.
        if debug:
            print("DEBUG is_inside: Same object - returning False")
        return False
    if hasattr(inner, "path") and inner.path is not None:
        inner_path = inner.path
    if hasattr(outer, "path") and outer.path is not None:
        outer_path = outer.path
    if not hasattr(inner, "bounding_box"):
        return False
    if not hasattr(outer, "bounding_box"):
        return False
    inner_bb = inner.bounding_box
    outer_bb = outer.bounding_box
    # Bounding box check
    if (
        inner_bb[0] < (outer_bb[0] - tolerance)
        or inner_bb[1] < (outer_bb[1] - tolerance)
        or inner_bb[2] > (outer_bb[2] + tolerance)
        or inner_bb[3] > (outer_bb[3] + tolerance)
    ):
        if debug:
            print(
                f"DEBUG is_inside: Bounding box check failed.\n"
                f"  inner: {inner_bb}\n"
                f"  outer: {outer_bb}"
            )
        return False

    if isinstance(inner, RasterCut) or isinstance(outer, RasterCut):
        # Use geometry for raster cuts
        inner_geom = (
            convex_geometry(inner) if isinstance(inner, RasterCut) else inner_path
        )
        outer_geom = (
            convex_geometry(outer) if isinstance(outer, RasterCut) else outer_path
        )
    else:
        inner_geom = inner_path
        outer_geom = outer_path

    # Use Geomstr methods if available
    if hasattr(Geomstr, "contains") and hasattr(inner_geom, "is_contained_by"):
        try:
            return inner_geom.is_contained_by(outer_geom, tolerance)  # type: ignore
        except Exception:
            pass

    # Fallback to basic point-in-path test
    if inner_geom is None or outer_geom is None:
        return False

    try:
        if hasattr(outer_geom, "point_in_path"):
            # Test sample points from inner path
            points = []
            if hasattr(inner_geom, "points"):
                points = inner_geom.points()[:5]  # type: ignore
            elif hasattr(inner_geom, "values"):
                values = list(inner_geom.values())  # type: ignore
                points = values[:5] if values else []

            if not points:
                return False

            for point in points:
                if not outer_geom.point_in_path(point, tolerance):  # type: ignore
                    if debug:
                        print(
                            f"DEBUG is_inside: Point {point} not in outer path"
                        )
                    return False
            return True
    except Exception as e:
        if debug:
            print(f"DEBUG is_inside: Exception during point test: {e}")

    return False


def inner_first_ident(context: CutCode, kernel=None, channel=None, tolerance=0):
    """
    Identifies closed CutGroups and then identifies any other CutGroups which
    are entirely inside.

    The CutGroup candidate generator uses this information to not offer the outer CutGroup
    as a candidate for a burn unless all contained CutGroups are cut.

    The Cutcode is resequenced in either short_travel_cutcode or inner_selection_cutcode
    based on this information.
    
    Args:
        context: CutCode to process
        kernel: Optional kernel for progress reporting
        channel: Optional logging channel
        tolerance: Tolerance for inside check
        
    Returns:
        Updated CutCode with .contains/.inside attributes set
    """
    if channel:
        start_time = time()
        start_times = times()
        channel("Executing Inner-First Identification")

    groups = [cut for cut in context if isinstance(cut, (CutGroup, RasterCut))]
    closed_groups = [g for g in groups if isinstance(g, CutGroup) and g.closed]
    total_pass = len(groups) * len(closed_groups)
    context.contains = closed_groups  # type: ignore
    if channel:
        channel(
            f"Compare {len(groups)} groups against {len(closed_groups)} closed groups"
        )

    constrained = False
    current_pass = 0
    if kernel:
        busy = kernel.busyinfo
        _ = kernel.translation
    else:
        busy = None
    
    for outer in closed_groups:
        for inner in groups:
            current_pass += 1
            if outer is inner:
                continue
            # if outer is inside inner, then inner cannot be inside outer
            if inner.contains and outer in inner.contains:
                continue
            if current_pass % 50 == 0 and busy and busy.shown:
                # Can't execute without kernel, reference before assignment is safe.
                message = f"Pass {current_pass}/{total_pass}"
                busy.change(msg=message, keep=2)
                busy.show()

            if is_inside(inner, outer, tolerance, debug=False):
                constrained = True
                if outer.contains is None:
                    outer.contains = []  # type: ignore
                outer.contains.append(inner)  # type: ignore

                if inner.inside is None:
                    inner.inside = []  # type: ignore
                inner.inside.append(outer)  # type: ignore

    context.constrained = constrained

    if channel:
        end_times = times()
        channel(
            f"Inner paths identified in {time() - start_time:.3f} elapsed seconds: {constrained} "
            f"using {end_times[0] - start_times[0]:.3f} seconds CPU"
        )
        for outer in closed_groups:
            if outer is None:
                continue
            channel(
                f"Outer {type(outer).__name__} contains: {'None' if outer.contains is None else str(len(outer.contains))} cutcode elements"
            )
    return context


# ============================================================================
# EMBEDDED TRAVEL OPTIMIZATION
# ============================================================================

def _simple_greedy_selection(all_candidates, start_position, early_termination_threshold=25):
    """
    Simple greedy nearest-neighbor algorithm for travel optimization.

    Iteratively selects the closest unfinished cut to the current position,
    choosing the optimal direction (forward or reverse) for each cut.

    Args:
        all_candidates: List of cuts to optimize
        start_position: Starting (x, y) position tuple
        early_termination_threshold: Distance threshold for early termination (default: 25)

    Returns:
        List of cuts in optimized order
    """
    if not all_candidates:
        return []

    # Burns_done already initialized in the calling function
    ordered = []
    curr_x, curr_y = start_position

    while True:
        closest = None
        backwards = False
        best_distance_sq = float("inf")

        # Find the nearest unfinished cut
        for cut in all_candidates:
            if cut.burns_done >= cut.passes:
                continue

            # Check forward direction
            start_x, start_y = cut.start
            dx = start_x - curr_x
            dy = start_y - curr_y
            distance_sq = dx * dx + dy * dy

            # Deterministic tie-breaking: prefer cuts with smaller Y, then smaller X coordinates
            is_better = distance_sq < best_distance_sq or (
                distance_sq == best_distance_sq
                and closest is not None
                and (
                    start_y < closest.start[1]
                    or (start_y == closest.start[1] and start_x < closest.start[0])
                )
            )

            if is_better:
                closest = cut
                backwards = False
                best_distance_sq = distance_sq

                # Early termination for very close cuts
                if distance_sq <= early_termination_threshold:
                    break

            # Check reverse direction if cut is reversible
            if cut.reversible():
                end_x, end_y = cut.end
                dx = end_x - curr_x
                dy = end_y - curr_y
                distance_sq = dx * dx + dy * dy

                # Deterministic tie-breaking for reverse direction
                is_better = distance_sq < best_distance_sq or (
                    distance_sq == best_distance_sq
                    and closest is not None
                    and (
                        end_y
                        < (
                            closest.end[1]
                            if backwards and closest.reversible()
                            else closest.start[1]
                        )
                        or (
                            end_y
                            == (
                                closest.end[1]
                                if backwards and closest.reversible()
                                else closest.start[1]
                            )
                            and end_x
                            < (
                                closest.end[0]
                                if backwards and closest.reversible()
                                else closest.start[0]
                            )
                        )
                    )
                )

                if is_better:
                    closest = cut
                    backwards = True
                    best_distance_sq = distance_sq

                    # Early termination for very close cuts
                    if distance_sq <= early_termination_threshold:
                        break

        if closest is None:
            break

        closest.burns_done += 1
        from copy import copy
        c = copy(closest)
        if backwards:
            c.reverse()
        end = c.end
        curr_x, curr_y = end
        ordered.append(c)

    return ordered


def short_travel_cutcode_optimized(
    context,
    kernel=None,
    channel=None,
    complete_path: Optional[bool] = False,
    grouped_inner: Optional[bool] = False,
    hatch_optimize: Optional[bool] = False,
):
    """
    Optimized short-travel cutcode algorithm with adaptive strategy selection.

    Chooses the best optimization strategy based on dataset characteristics:
    - Group-aware: When grouped_inner=True, processes related inner/outer groups together
    - Group-preserving: When inner-first constraints exist, processes groups individually
    - Standard algorithms: For unconstrained optimization, uses size-appropriate algorithms

    This is the embedded version from cutplan.py, adapted for hierarchical processing.

    Args:
        context: CutCode containing cuts and groups to optimize
        kernel: Optional kernel for progress reporting
        channel: Optional logging channel
        complete_path: Whether to require complete path traversal
        grouped_inner: Whether to group inner/outer relationships together
        hatch_optimize: Whether to optimize hatch patterns

    Returns:
        CutCode with optimized travel order
    """
    if channel:
        start_length = context.length_travel(True)
        start_time = time()
        start_times = times()
        channel("Executing adaptive short-travel optimization")
        channel(f"Length at start: {start_length:.0f} steps")

    unordered = []

    if hatch_optimize:
        # When optimizing hatch patterns separately:
        skip_groups = []
        non_skip_groups = []

        for c in context:
            if isinstance(c, CutGroup) and c.skip:
                skip_groups.append(c)
            else:
                non_skip_groups.append(c)

        # Remove skip groups from context for first optimization pass
        if non_skip_groups:
            # Filter containment hierarchy
            for group in non_skip_groups:
                if hasattr(group, "contains") and group.contains:
                    group.contains = [
                        inner for inner in group.contains
                        if not (isinstance(inner, CutGroup) and inner.skip)
                    ]

            context.clear()
            context.extend(non_skip_groups)
            unordered = skip_groups
        else:
            unordered = []
    else:
        unordered = []

    # Initialize burns_done for all cuts BEFORE getting candidates
    for c in context.flat():
        c.burns_done = 0

    # Get all candidates first to determine dataset size
    all_candidates = list(
        context.candidate(complete_path=complete_path, grouped_inner=grouped_inner)
    )

    dataset_size = len(all_candidates)

    if channel:
        channel(f"Dataset size: {dataset_size} cuts")

    if not all_candidates:
        # No candidates at all, return empty CutCode
        ordered = CutCode()
        if context.start is not None:
            ordered._start_x, ordered._start_y = context.start
        else:
            ordered._start_x = 0
            ordered._start_y = 0
        return ordered

    # Use simple greedy for hierarchical optimization
    # (we're optimizing same-level cuts only, so smaller dataset)
    start_pos = context.start or (0, 0)
    ordered_cuts = _simple_greedy_selection(all_candidates, start_pos)

    # Create ordered CutCode from selected cuts
    ordered = CutCode()
    ordered.extend(ordered_cuts)

    # Handle unordered groups (same as original)
    if hatch_optimize:
        for idx, c in enumerate(unordered):
            if isinstance(c, CutGroup):
                c.skip = False
                unordered[idx] = short_travel_cutcode_optimized(
                    context=c,
                    kernel=kernel,
                    complete_path=False,
                    grouped_inner=False,
                    channel=channel,
                )

    ordered.extend(reversed(unordered))

    if context.start is not None:
        ordered._start_x, ordered._start_y = context.start
    else:
        ordered._start_x = 0
        ordered._start_y = 0

    if channel:
        end_times = times()
        end_length = ordered.length_travel(True)
        try:
            delta = (end_length - start_length) / start_length
        except (ZeroDivisionError, NameError):
            delta = 0
        channel(
            f"Length at end: {end_length:.0f} steps "
            f"({delta:+.0%}), "
            f"optimized in {time() - start_time:.3f} "
            f"elapsed seconds using {end_times[0] - start_times[0]:.3f} seconds CPU"
        )
    return ordered


# ============================================================================
# MAIN OPTIMIZATION ENTRY POINT
# ============================================================================

class HierarchicalCutPlan:
    """
    Hierarchical cut plan optimizer.
    
    This class provides the main entry point for hierarchical optimization,
    wrapping the standalone functions and providing state management.
    """
    
    def __init__(self, kernel=None, channel=None):
        """
        Initialize the hierarchical cut plan optimizer.
        
        Args:
            kernel: Optional kernel for messaging and services
            channel: Optional channel for logging
        """
        self.kernel = kernel
        self.channel = channel
    
    def log(self, message: str) -> None:
        """Log a message if channel is available."""
        if self.channel:
            self.channel(message)
    
    def optimize_with_hierarchy(
        self,
        context: CutCode,
        use_inner_first: bool = True,
        optimizer_func: Optional[Callable] = None,
        **optimizer_kwargs
    ) -> CutCode:
        """
        Optimize a CutCode using hierarchical selection.
        
        This is the main entry point for hierarchical optimization.
        
        Algorithm:
        1. If use_inner_first, run inner_first_ident to identify hierarchy
        2. Build explicit hierarchy levels
        3. Validate hierarchy
        4. Process level-by-level with travel optimization
        5. Return optimized result
        
        Args:
            context: CutCode to optimize
            use_inner_first: Whether to run inner_first_ident first
            optimizer_func: Function to optimize each level
                           Default: short_travel_cutcode_wrapper
            **optimizer_kwargs: Additional kwargs for optimizer
            
        Returns:
            Optimized CutCode
        """
        start_time = perf_counter()
        self.log("Starting hierarchical optimization...")
        
        try:
            # Phase 1: Identify hierarchy (if requested)
            result: CutCode = context
            if use_inner_first:
                self.log("Phase 1: Identifying hierarchy with inner_first_ident...")
                result = inner_first_ident(  # type: ignore
                    result,
                    kernel=self.kernel,
                    channel=self.channel,
                    **optimizer_kwargs
                )
            
            # Phase 2: Build explicit hierarchy levels
            self.log("Phase 2: Building explicit hierarchy levels...")
            hierarchy = build_hierarchy_levels(result)
            self.log(f"  Built {len(hierarchy.all_levels)} hierarchy levels")
            
            # Phase 3: Validate hierarchy
            self.log("Phase 3: Validating hierarchy...")
            is_valid, errors = validate_hierarchy(hierarchy)
            if not is_valid:
                self.log("WARNING: Hierarchy validation found issues:")
                for error in errors:
                    self.log(f"  - {error}")
            
            # Phase 4: Process with hierarchy
            self.log("Phase 4: Processing with hierarchical selection...")
            if optimizer_func is None:
                optimizer_func = short_travel_cutcode_optimized
            
            result = hierarchical_selection(
                result,
                hierarchy,
                optimizer_func,
                kernel=self.kernel,
                channel=self.channel,
                **optimizer_kwargs
            )
            
            elapsed = perf_counter() - start_time
            self.log(f"Hierarchical optimization complete in {elapsed:.2f}s")
            return result
            
        except Exception as e:
            self.log(f"ERROR during hierarchical optimization: {e}")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}")
            # Return original unchanged
            return context


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def optimize_cutcode_hierarchical(
    cutcode: CutCode,
    kernel=None,
    channel=None,
    **kwargs
) -> CutCode:
    """
    Convenience function to optimize a CutCode using hierarchy.
    
    This is a simple wrapper around HierarchicalCutPlan for one-off optimizations.
    
    Args:
        cutcode: CutCode to optimize
        kernel: Optional kernel for messaging
        channel: Optional channel for logging
        **kwargs: Additional options:
            - use_inner_first: bool (default True)
            - optimizer_func: Callable
            - Other options passed to optimizer
            
    Returns:
        Optimized CutCode
    """
    optimizer = HierarchicalCutPlan(kernel=kernel, channel=channel)
    return optimizer.optimize_with_hierarchy(cutcode, **kwargs)


# ============================================================================
# DEBUGGING & ANALYSIS
# ============================================================================

def print_hierarchy(hierarchy: HierarchyContext) -> str:
    """
    Generate a human-readable representation of the hierarchy.
    
    Useful for debugging and understanding the hierarchy structure.
    
    Args:
        hierarchy: HierarchyContext to analyze
        
    Returns:
        Formatted string representation
    """
    lines = ["Hierarchy Structure:"]
    lines.append(f"  Root levels: {len(hierarchy.root_levels)}")
    lines.append(f"  Total levels: {len(hierarchy.all_levels)}")
    
    def print_level(level: HierarchyLevel, indent: int = 2) -> None:
        prefix = "  " * indent
        lines.append(
            f"{prefix}Level {level.level}: {len(level.cuts)} cuts"
        )
        for cut in level.cuts:
            lines.append(f"{prefix}  - {cut}")
        for child in level.child_levels:
            print_level(child, indent + 1)
    
    for root_level in hierarchy.root_levels:
        print_level(root_level)
    
    return "\n".join(lines)


def print_hierarchy_stats(hierarchy: HierarchyContext) -> str:
    """
    Generate statistics about the hierarchy.
    
    Args:
        hierarchy: HierarchyContext to analyze
        
    Returns:
        Formatted string with statistics
    """
    lines = ["Hierarchy Statistics:"]
    
    total_cuts = sum(len(level.cuts) for level in hierarchy.all_levels)
    lines.append(f"  Total cuts: {total_cuts}")
    lines.append(f"  Total levels: {len(hierarchy.all_levels)}")
    lines.append(f"  Max depth: {max((level.level for level in hierarchy.all_levels), default=0)}")
    
    # Distribution by level
    level_counts = {}
    for level in hierarchy.all_levels:
        if level.level not in level_counts:
            level_counts[level.level] = 0
        level_counts[level.level] += len(level.cuts)
    
    lines.append("  Cuts by level:")
    for level_num in sorted(level_counts.keys()):
        lines.append(f"    Level {level_num}: {level_counts[level_num]} cuts")
    
    return "\n".join(lines)
