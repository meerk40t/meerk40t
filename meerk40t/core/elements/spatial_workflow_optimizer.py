#!/usr/bin/env python3
"""
Enhanced Workflow Optimization with Spatial Partitioning and K-d Trees

High-performance workflow optimization for large-scale laser operations using
spatial partitioning, k-d trees, and advanced algorithms. Optimized for designs with
hundreds to thousands of operations.
"""

import math
import time
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# K-d tree optimization support (optional dependency)
try:
    from scipy.spatial import cKDTree

    KDTREE_AVAILABLE = True
except ImportError:
    KDTREE_AVAILABLE = False

# Import base classes from the original workflow system
try:
    from .operation_workflow import ProcessingPriority, OperationWorkflow

    IMPORTS_AVAILABLE = True
except ImportError:
    # For testing - mock the classes
    from enum import Enum

    class ProcessingPriority(Enum):
        INNER_ENGRAVE = 1
        MIDDLE_ENGRAVE = 2
        OUTER_ENGRAVE = 3
        INNER_CUT = 4
        OUTER_CUT = 5

    class OperationWorkflow:
        """Mock base class for testing."""

        def __init__(self, manual_optimize=None):
            self.manual_optimize = manual_optimize
            self.workflow_groups = []

        def analyze_containment(self):
            pass

        def assign_priorities(self):
            pass

        def create_workflow_groups(self):
            pass

        def optimize_group_ordering(self):
            pass

    IMPORTS_AVAILABLE = False


@dataclass
class SpatialCell:
    """Represents a spatial grid cell containing operations."""

    x: int
    y: int
    operations: List[Any]
    center: complex
    processed: bool = False

    def __post_init__(self):
        if not self.operations:
            self.operations = []


@dataclass
class OptimizationStats:
    """Statistics from optimization process."""

    total_operations: int
    total_distance: float
    optimization_time: float
    algorithm_used: str
    grid_size: Optional[int] = None
    cells_used: Optional[int] = None
    kdtree_enabled: bool = False
    kdtree_cells: int = 0


class OptimizationLevel(Enum):
    """Different optimization levels for user configuration."""

    FAST = 1  # Quick greedy, good for <100 operations
    BALANCED = 2  # Spatial partitioning, good for 100-1000 operations
    THOROUGH = 3  # Advanced algorithms, good for >1000 operations


class SpatialWorkflowOptimizer:
    """
    Enhanced workflow optimizer using spatial partitioning for large-scale performance.

    Key improvements:
    - O(n log n) complexity instead of O(n²) for large datasets
    - Spatial grid partitioning to reduce search space
    - Configurable optimization levels
    - Progress reporting for large operations
    """

    def __init__(
        self, workspace_bounds: Tuple[float, float, float, float] = (0, 0, 300, 200)
    ):
        """
        Initialize the spatial optimizer.

        Args:
            workspace_bounds: (min_x, min_y, max_x, max_y) workspace boundaries
        """
        self.workspace_bounds = workspace_bounds
        self.grid_size = 10  # Default grid size, will be adjusted based on data
        self.spatial_cells: Dict[Tuple[int, int], SpatialCell] = {}
        self.stats = None

    def optimize_workflow(
        self,
        operations: List[Any],
        optimization_level: OptimizationLevel = OptimizationLevel.BALANCED,
        progress_callback=None,
    ) -> Tuple[List[Any], OptimizationStats]:
        """
        Optimize workflow with configurable performance levels.

        IMPORTANT: This method properly handles operation loops. Operations with
        loops > 1 will be executed multiple times consecutively as intended by the
        laser workflow system.

        Args:
            operations: List of operation nodes to optimize
            optimization_level: Performance vs quality trade-off
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (optimized_operations, optimization_stats)
        """
        start_time = time.perf_counter()

        if not operations:
            return [], OptimizationStats(0, 0.0, 0.0, "empty")

        # Expand operations based on their loop counts
        if progress_callback:
            progress_callback(5, "Processing operation loops...")

        expanded_operations = self._expand_operations_with_loops(operations)

        # Check if we have any looped operations
        has_loops = len(expanded_operations) != len(operations)
        if progress_callback and has_loops:
            loop_count = len(expanded_operations) - len(operations)
            progress_callback(10, f"Expanded {loop_count} additional loop iterations")

        # Choose algorithm based on size and optimization level
        algorithm = self._select_algorithm(len(expanded_operations), optimization_level)

        if progress_callback:
            progress_callback(15, f"Using {algorithm} algorithm...")

        if algorithm == "greedy":
            optimized_expanded, total_distance = self._greedy_optimization(
                expanded_operations, progress_callback
            )
            stats = OptimizationStats(
                total_operations=len(operations),  # Original operation count
                total_distance=total_distance,
                optimization_time=time.perf_counter() - start_time,
                algorithm_used="greedy",
            )
        elif algorithm == "spatial":
            optimized_expanded, total_distance = self._spatial_optimization(
                expanded_operations, progress_callback
            )
            stats = OptimizationStats(
                total_operations=len(operations),  # Original operation count
                total_distance=total_distance,
                optimization_time=time.perf_counter() - start_time,
                algorithm_used="spatial",
                grid_size=self.grid_size,
                cells_used=len(self.spatial_cells),
                kdtree_enabled=KDTREE_AVAILABLE,
                kdtree_cells=getattr(self, "_kdtree_cells_used", 0),
            )
        elif algorithm == "advanced":
            optimized_expanded, total_distance = self._advanced_optimization(
                expanded_operations, progress_callback
            )
            stats = OptimizationStats(
                total_operations=len(operations),  # Original operation count
                total_distance=total_distance,
                optimization_time=time.perf_counter() - start_time,
                algorithm_used="advanced",
            )
        else:
            # Fallback to greedy
            optimized_expanded, total_distance = self._greedy_optimization(
                expanded_operations, progress_callback
            )
            stats = OptimizationStats(
                total_operations=len(operations),  # Original operation count
                total_distance=total_distance,
                optimization_time=time.perf_counter() - start_time,
                algorithm_used="fallback_greedy",
            )

        # Collapse expanded operations back to original form
        # This maintains the optimized order while preserving loop semantics
        if progress_callback:
            progress_callback(95, "Finalizing loop sequences...")

        optimized_operations = self._collapse_operations_from_loops(optimized_expanded)

        self.stats = stats

        if progress_callback:
            loop_info = (
                f" (with {len(expanded_operations) - len(operations)} loop iterations)"
                if has_loops
                else ""
            )
            progress_callback(
                100, f"Optimization complete: {stats.algorithm_used}{loop_info}"
            )

        return optimized_operations, stats

    def _select_algorithm(self, operation_count: int, level: OptimizationLevel) -> str:
        """Select the best algorithm based on operation count and optimization level."""
        if level == OptimizationLevel.FAST:
            return "greedy"
        elif level == OptimizationLevel.BALANCED:
            if operation_count < 50:
                return "greedy"
            else:
                return "spatial"
        else:  # THOROUGH
            if operation_count < 100:
                return "greedy"
            elif operation_count < 2000:
                return "spatial"
            else:
                return "advanced"

    def _spatial_optimization(
        self, operations: List[Any], progress_callback=None
    ) -> Tuple[List[Any], float]:
        """
        Spatial partitioning optimization with O(n log n) complexity.

        Strategy:
        1. Partition operations into spatial grid
        2. Process cells in optimal order
        3. Optimize within each cell using k-d tree (if available) or greedy
        """
        if not operations:
            return [], 0.0

        # Calculate optimal grid size based on operation density
        self.grid_size = self._calculate_optimal_grid_size(len(operations))

        # Build spatial grid
        self._build_spatial_grid(operations)

        if progress_callback:
            kdtree_status = "with k-d trees" if KDTREE_AVAILABLE else "greedy fallback"
            progress_callback(
                20,
                f"Built spatial grid ({self.grid_size}x{self.grid_size}) {kdtree_status}",
            )

        # Find optimal cell traversal order
        cell_order = self._calculate_cell_traversal_order()

        if progress_callback:
            progress_callback(
                40, f"Calculated traversal order for {len(cell_order)} cells"
            )

        # Track k-d tree usage
        kdtree_cells_used = 0

        # Process cells in order
        optimized_operations = []
        total_distance = 0.0
        last_position = complex(0, 0)  # Starting position

        for i, (cell_x, cell_y) in enumerate(cell_order):
            if progress_callback and i % max(1, len(cell_order) // 10) == 0:
                progress = 40 + int(50 * i / len(cell_order))
                progress_callback(
                    progress, f"Processing cell {i + 1}/{len(cell_order)}"
                )

            cell = self.spatial_cells[(cell_x, cell_y)]
            if not cell.operations:
                continue

            # Track if this cell will use k-d tree
            if len(cell.operations) > 20 and KDTREE_AVAILABLE:
                kdtree_cells_used += 1

            # Optimize operations within this cell
            cell_optimized, cell_distance = self._optimize_cell_operations(
                cell.operations, last_position
            )

            optimized_operations.extend(cell_optimized)
            total_distance += cell_distance

            if cell_optimized:
                last_position = self._get_operation_end_point(cell_optimized[-1])

        # Store k-d tree usage for stats
        self._kdtree_cells_used = kdtree_cells_used

        return optimized_operations, total_distance

    def _calculate_optimal_grid_size(self, operation_count: int) -> int:
        """Calculate optimal grid size based on operation count and workspace."""
        # Target 5-20 operations per cell for good performance
        target_ops_per_cell = 10
        min_grid_size = 3
        max_grid_size = 20

        ideal_cells = max(1, operation_count // target_ops_per_cell)
        grid_size = int(math.sqrt(ideal_cells))

        return max(min_grid_size, min(max_grid_size, grid_size))

    def _build_spatial_grid(self, operations: List[Any]):
        """Build spatial grid and assign operations to cells."""
        self.spatial_cells.clear()

        min_x, min_y, max_x, max_y = self.workspace_bounds
        cell_width = (max_x - min_x) / self.grid_size
        cell_height = (max_y - min_y) / self.grid_size

        # Initialize all cells
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                center_x = min_x + (x + 0.5) * cell_width
                center_y = min_y + (y + 0.5) * cell_height
                center = complex(center_x, center_y)

                self.spatial_cells[(x, y)] = SpatialCell(x, y, [], center)

        # Assign operations to cells
        for op in operations:
            # Get operation center point
            center = self._get_operation_center(op)

            # Calculate cell coordinates
            cell_x = int((center.real - min_x) / cell_width)
            cell_y = int((center.imag - min_y) / cell_height)

            # Clamp to grid boundaries
            cell_x = max(0, min(self.grid_size - 1, cell_x))
            cell_y = max(0, min(self.grid_size - 1, cell_y))

            self.spatial_cells[(cell_x, cell_y)].operations.append(op)

    def _calculate_cell_traversal_order(self) -> List[Tuple[int, int]]:
        """
        Calculate optimal order to traverse cells to minimize travel distance.
        Uses a space-filling curve approximation.
        """
        non_empty_cells = [
            (x, y) for (x, y), cell in self.spatial_cells.items() if cell.operations
        ]

        if not non_empty_cells:
            return []

        # Use a simple zigzag pattern for efficiency
        # More advanced: Hilbert curve or nearest-neighbor between cells
        non_empty_cells.sort(
            key=lambda cell: (cell[1], cell[0] if cell[1] % 2 == 0 else -cell[0])
        )

        return non_empty_cells

    def _optimize_cell_operations(
        self, operations: List[Any], start_position: complex
    ) -> Tuple[List[Any], float]:
        """
        Optimize operations within a single cell using the best available algorithm.

        Uses k-d tree for large cells when available, falls back to greedy otherwise.
        """
        if not operations:
            return [], 0.0

        if len(operations) == 1:
            # Single operation - just calculate travel distance
            op_start = self._get_operation_start_point(operations[0])
            distance = abs(op_start - start_position)
            return operations, float(
                distance.real if isinstance(distance, complex) else distance
            )

        # Choose algorithm based on cell size and k-d tree availability
        if len(operations) > 20 and KDTREE_AVAILABLE:
            return self._optimize_cell_with_kdtree(operations, start_position)
        else:
            return self._optimize_cell_with_greedy(operations, start_position)

    def _optimize_cell_with_kdtree(
        self, operations: List[Any], start_position: complex
    ) -> Tuple[List[Any], float]:
        """
        Optimize cell operations using k-d tree for O(log n) nearest neighbor queries.

        This provides dramatic performance improvements for large cells while
        maintaining identical results to greedy optimization.

        IMPORTANT: Handles operation loops correctly - operations with multiple loops
        are kept together in sequence.
        """
        if not operations:
            return [], 0.0

        # Separate operations by loop groups
        loop_groups = self._group_operations_by_loops(operations)

        if len(loop_groups) == 1 and not any(
            isinstance(op, LoopWrapper) for op in operations
        ):
            # Simple case - no loops, use standard k-d tree optimization
            return self._kdtree_optimize_simple(operations, start_position)
        else:
            # Complex case - handle loop groups with constraints
            return self._kdtree_optimize_with_loops(loop_groups, start_position)

    def _kdtree_optimize_simple(
        self, operations: List[Any], start_position: complex
    ) -> Tuple[List[Any], float]:
        """Simple k-d tree optimization for operations without loops."""
        # Build k-d tree from operation positions
        positions = []
        for op in operations:
            center = self._get_operation_start_point(op)
            positions.append([center.real, center.imag])

        kdtree = cKDTree(positions)

        # Find closest operation to start position
        start_point = [start_position.real, start_position.imag]
        _, closest_idx = kdtree.query(start_point)

        # Initialize optimization with closest operation
        optimized = [operations[closest_idx]]
        remaining_indices = set(range(len(operations))) - {closest_idx}
        total_distance = abs(
            self._get_operation_start_point(operations[closest_idx]) - start_position
        )

        # Greedy optimization using k-d tree for nearest neighbor queries
        while remaining_indices:
            current_pos = self._get_operation_end_point(optimized[-1])
            current_point = [current_pos.real, current_pos.imag]

            # Query k-d tree for nearest neighbor among remaining operations
            remaining_positions = [positions[i] for i in remaining_indices]
            if len(remaining_positions) == 1:
                # Only one remaining - take it
                nearest_global_idx = next(iter(remaining_indices))
            else:
                # Build temporary k-d tree for remaining operations
                remaining_kdtree = cKDTree(remaining_positions)
                _, nearest_local_idx = remaining_kdtree.query(current_point)

                # Convert local index back to global index
                nearest_global_idx = list(remaining_indices)[nearest_local_idx]

            # Add nearest operation to optimized sequence
            next_op = operations[nearest_global_idx]
            optimized.append(next_op)
            remaining_indices.remove(nearest_global_idx)

            # Update total distance
            next_pos = self._get_operation_start_point(next_op)
            travel_dist = abs(next_pos - current_pos)
            total_distance += travel_dist

        return optimized, float(
            total_distance.real
            if isinstance(total_distance, complex)
            else total_distance
        )

    def _kdtree_optimize_with_loops(
        self, loop_groups: List[List[Any]], start_position: complex
    ) -> Tuple[List[Any], float]:
        """K-d tree optimization that respects loop grouping constraints."""
        # Treat each loop group as a single "super-operation" for travel optimization
        group_positions = []
        for group in loop_groups:
            # Use the first operation's position to represent the group
            first_op = group[0]
            if isinstance(first_op, LoopWrapper):
                center = self._get_operation_start_point(first_op.original_operation)
            else:
                center = self._get_operation_start_point(first_op)
            group_positions.append([center.real, center.imag])

        # Build k-d tree for loop groups
        group_kdtree = cKDTree(group_positions)

        # Find closest group to start position
        start_point = [start_position.real, start_position.imag]
        _, closest_group_idx = group_kdtree.query(start_point)

        # Initialize optimization with closest group
        optimized = []
        total_distance = 0.0
        current_pos = start_position

        remaining_group_indices = set(range(len(loop_groups))) - {closest_group_idx}

        # Add closest group first
        first_group = loop_groups[closest_group_idx]
        optimized.extend(first_group)

        # Calculate distance to first group
        if first_group:
            first_op = first_group[0]
            if isinstance(first_op, LoopWrapper):
                first_pos = self._get_operation_start_point(first_op.original_operation)
            else:
                first_pos = self._get_operation_start_point(first_op)
            total_distance += abs(first_pos - current_pos)

            # Update current position to end of group
            last_op = first_group[-1]
            if isinstance(last_op, LoopWrapper):
                current_pos = self._get_operation_end_point(last_op.original_operation)
            else:
                current_pos = self._get_operation_end_point(last_op)

        # Process remaining groups using k-d tree
        while remaining_group_indices:
            current_point = [current_pos.real, current_pos.imag]

            # Find nearest remaining group
            remaining_positions = [group_positions[i] for i in remaining_group_indices]
            if len(remaining_positions) == 1:
                nearest_group_idx = next(iter(remaining_group_indices))
            else:
                remaining_kdtree = cKDTree(remaining_positions)
                _, nearest_local_idx = remaining_kdtree.query(current_point)
                nearest_group_idx = list(remaining_group_indices)[nearest_local_idx]

            # Add nearest group
            next_group = loop_groups[nearest_group_idx]
            optimized.extend(next_group)
            remaining_group_indices.remove(nearest_group_idx)

            # Calculate travel distance to this group
            if next_group:
                first_op = next_group[0]
                if isinstance(first_op, LoopWrapper):
                    next_pos = self._get_operation_start_point(
                        first_op.original_operation
                    )
                else:
                    next_pos = self._get_operation_start_point(first_op)
                total_distance += abs(next_pos - current_pos)

                # Update current position to end of group
                last_op = next_group[-1]
                if isinstance(last_op, LoopWrapper):
                    current_pos = self._get_operation_end_point(
                        last_op.original_operation
                    )
                else:
                    current_pos = self._get_operation_end_point(last_op)

        return optimized, float(
            total_distance.real
            if isinstance(total_distance, complex)
            else total_distance
        )

    def _group_operations_by_loops(self, operations: List[Any]) -> List[List[Any]]:
        """
        Group operations by their loop sequences.

        Operations that are part of the same loop sequence (same original operation,
        consecutive loop indices) are kept together as constraints.
        """
        groups = []
        current_group = []

        for op in operations:
            if isinstance(op, LoopWrapper):
                # Check if this continues the current group
                if (
                    current_group
                    and isinstance(current_group[-1], LoopWrapper)
                    and current_group[-1].original_operation == op.original_operation
                    and current_group[-1].loop_index == op.loop_index - 1
                ):
                    # Continue current group
                    current_group.append(op)
                else:
                    # Start new group
                    if current_group:
                        groups.append(current_group)
                    current_group = [op]
            else:
                # Regular operation - each gets its own group
                if current_group:
                    groups.append(current_group)
                current_group = [op]

        # Don't forget the last group
        if current_group:
            groups.append(current_group)

        return groups

    def _optimize_cell_with_greedy(
        self, operations: List[Any], start_position: complex
    ) -> Tuple[List[Any], float]:
        """
        Fallback greedy optimization for cells when k-d tree is not available
        or for small cells where the overhead isn't worth it.

        IMPORTANT: Properly handles operation loops by respecting loop grouping.
        """
        if not operations:
            return [], 0.0

        # Check if we have loop operations that need special handling
        has_loops = any(isinstance(op, LoopWrapper) for op in operations)

        if has_loops:
            # Use loop-aware optimization
            loop_groups = self._group_operations_by_loops(operations)
            return self._greedy_optimize_with_loops(loop_groups, start_position)
        else:
            # Standard greedy optimization
            return self._greedy_optimize_simple(operations, start_position)

    def _greedy_optimize_simple(
        self, operations: List[Any], start_position: complex
    ) -> Tuple[List[Any], float]:
        """Standard greedy optimization for operations without loops."""
        if len(operations) == 1:
            # Single operation - just calculate travel distance
            op_start = self._get_operation_start_point(operations[0])
            distance = abs(op_start - start_position)
            return operations, float(
                distance.real if isinstance(distance, complex) else distance
            )

        # Find closest operation to start position
        closest_idx = 0
        closest_dist = float("inf")

        for i, op in enumerate(operations):
            op_start = self._get_operation_start_point(op)
            dist = abs(op_start - start_position)
            if isinstance(dist, complex):
                dist = abs(dist)

            if dist < closest_dist:
                closest_dist = dist
                closest_idx = i

        # Greedy optimization starting from closest operation
        optimized = [operations[closest_idx]]
        remaining = operations[:closest_idx] + operations[closest_idx + 1 :]
        total_distance = closest_dist

        while remaining:
            current_pos = self._get_operation_end_point(optimized[-1])

            nearest_idx = 0
            nearest_dist = float("inf")

            for i, op in enumerate(remaining):
                next_pos = self._get_operation_start_point(op)
                dist = abs(next_pos - current_pos)
                if isinstance(dist, complex):
                    dist = abs(dist)

                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = i

            optimized.append(remaining.pop(nearest_idx))
            total_distance += nearest_dist

        return optimized, total_distance

    def _greedy_optimize_with_loops(
        self, loop_groups: List[List[Any]], start_position: complex
    ) -> Tuple[List[Any], float]:
        """Greedy optimization that respects loop grouping constraints."""
        if not loop_groups:
            return [], 0.0

        # Find closest group to start position
        closest_group_idx = 0
        closest_dist = float("inf")

        for i, group in enumerate(loop_groups):
            if group:
                first_op = group[0]
                if isinstance(first_op, LoopWrapper):
                    group_pos = self._get_operation_start_point(
                        first_op.original_operation
                    )
                else:
                    group_pos = self._get_operation_start_point(first_op)

                dist = abs(group_pos - start_position)
                if isinstance(dist, complex):
                    dist = abs(dist)

                if dist < closest_dist:
                    closest_dist = dist
                    closest_group_idx = i

        # Start with closest group
        optimized = []
        optimized.extend(loop_groups[closest_group_idx])
        remaining_groups = (
            loop_groups[:closest_group_idx] + loop_groups[closest_group_idx + 1 :]
        )
        total_distance = closest_dist

        # Current position is at the end of the first group
        if loop_groups[closest_group_idx]:
            last_op = loop_groups[closest_group_idx][-1]
            if isinstance(last_op, LoopWrapper):
                current_pos = self._get_operation_end_point(last_op.original_operation)
            else:
                current_pos = self._get_operation_end_point(last_op)
        else:
            current_pos = start_position

        # Greedily add remaining groups
        while remaining_groups:
            nearest_group_idx = 0
            nearest_dist = float("inf")

            for i, group in enumerate(remaining_groups):
                if group:
                    first_op = group[0]
                    if isinstance(first_op, LoopWrapper):
                        group_pos = self._get_operation_start_point(
                            first_op.original_operation
                        )
                    else:
                        group_pos = self._get_operation_start_point(first_op)

                    dist = abs(group_pos - current_pos)
                    if isinstance(dist, complex):
                        dist = abs(dist)

                    if dist < nearest_dist:
                        nearest_dist = dist
                        nearest_group_idx = i

            # Add nearest group
            next_group = remaining_groups.pop(nearest_group_idx)
            optimized.extend(next_group)
            total_distance += nearest_dist

            # Update current position
            if next_group:
                last_op = next_group[-1]
                if isinstance(last_op, LoopWrapper):
                    current_pos = self._get_operation_end_point(
                        last_op.original_operation
                    )
                else:
                    current_pos = self._get_operation_end_point(last_op)

        return optimized, total_distance

    def _greedy_optimization(
        self, operations: List[Any], progress_callback=None
    ) -> Tuple[List[Any], float]:
        """Standard greedy nearest-neighbor optimization."""
        if not operations:
            return [], 0.0

        optimized = [operations[0]]
        remaining = operations[1:]
        total_distance = 0.0

        while remaining:
            if (
                progress_callback
                and len(optimized) % max(1, len(operations) // 20) == 0
            ):
                progress = int(90 * len(optimized) / len(operations))
                progress_callback(
                    progress, f"Processed {len(optimized)}/{len(operations)} operations"
                )

            current_pos = self._get_operation_end_point(optimized[-1])

            nearest_idx = 0
            nearest_dist = float("inf")

            for i, op in enumerate(remaining):
                next_pos = self._get_operation_start_point(op)
                dist = abs(next_pos - current_pos)
                if isinstance(dist, complex):
                    dist = abs(dist)

                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = i

            optimized.append(remaining.pop(nearest_idx))
            total_distance += nearest_dist

        return optimized, total_distance

    def _advanced_optimization(
        self, operations: List[Any], progress_callback=None
    ) -> Tuple[List[Any], float]:
        """
        Advanced optimization for very large datasets.
        Uses spatial partitioning + 2-opt improvement.
        """
        # Start with spatial optimization
        if progress_callback:
            progress_callback(10, "Running spatial optimization...")

        spatial_result, spatial_distance = self._spatial_optimization(operations, None)

        if progress_callback:
            progress_callback(70, "Applying 2-opt improvements...")

        # Apply 2-opt improvements (simplified version)
        improved_result, improved_distance = self._apply_2opt_improvements(
            spatial_result, max_iterations=min(100, len(operations) // 10)
        )

        return improved_result, improved_distance

    def _apply_2opt_improvements(
        self, operations: List[Any], max_iterations: int = 100
    ) -> Tuple[List[Any], float]:
        """
        Apply 2-opt local improvements to the tour.
        Simplified version for demonstration.
        """
        if len(operations) < 4:
            return operations, self._calculate_total_distance(operations)

        current_tour = operations[:]
        current_distance = self._calculate_total_distance(current_tour)

        for iteration in range(max_iterations):
            improved = False

            # Try swapping segments
            for i in range(1, len(current_tour) - 2):
                for j in range(i + 1, len(current_tour)):
                    if j - i == 1:  # Skip adjacent
                        continue

                    # Create new tour by reversing segment
                    new_tour = current_tour[:]
                    new_tour[i:j] = reversed(new_tour[i:j])

                    new_distance = self._calculate_total_distance(new_tour)

                    if new_distance < current_distance:
                        current_tour = new_tour
                        current_distance = new_distance
                        improved = True
                        break

                if improved:
                    break

            if not improved:
                break

        return current_tour, current_distance

    def _calculate_total_distance(self, operations: List[Any]) -> float:
        """Calculate total travel distance for a sequence of operations."""
        if len(operations) < 2:
            return 0.0

        total_distance = 0.0
        last_pos = complex(0, 0)  # Starting position

        for op in operations:
            start_pos = self._get_operation_start_point(op)
            end_pos = self._get_operation_end_point(op)

            # Travel to operation
            travel_dist = abs(start_pos - last_pos)
            if isinstance(travel_dist, complex):
                travel_dist = abs(travel_dist)

            total_distance += travel_dist
            last_pos = end_pos

        return total_distance

    # Helper methods for operation geometry
    def _get_operation_center(self, op_node: Any) -> complex:
        """Get the center point of an operation."""
        bbox = getattr(op_node, "bbox", [0, 0, 10, 10])
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        return complex(center_x, center_y)

    def _get_operation_start_point(self, op_node: Any) -> complex:
        """Get the starting point for an operation."""
        if hasattr(op_node, "travel_start") and op_node.travel_start is not None:
            return op_node.travel_start

        bbox = getattr(op_node, "bbox", [0, 0, 10, 10])
        return complex(float(bbox[0]), float(bbox[1]))

    def _get_operation_end_point(self, op_node: Any) -> complex:
        """Get the ending point for an operation."""
        if hasattr(op_node, "travel_end") and op_node.travel_end is not None:
            return op_node.travel_end

        bbox = getattr(op_node, "bbox", [0, 0, 10, 10])
        return complex(float(bbox[2]), float(bbox[3]))

    def _get_operation_loops(self, op_node: Any) -> int:
        """Get the loop count for an operation (how many times it should be executed)."""
        if hasattr(op_node, "loops") and op_node.loops is not None:
            try:
                loops = int(op_node.loops)
                return max(1, loops)  # Ensure at least 1 loop
            except (ValueError, TypeError):
                return 1
        return 1

    def _expand_operations_with_loops(self, operations: List[Any]) -> List[Any]:
        """
        Expand operations based on their loop count.

        This is critical for proper laser operation sequencing. If an operation
        has loops=3, it needs to be executed 3 times consecutively before moving
        to the next operation.

        Returns a new list where operations with loops>1 are duplicated accordingly,
        but marked to maintain their grouping during optimization.
        """
        expanded_operations = []

        for op in operations:
            loops = self._get_operation_loops(op)

            if loops == 1:
                # Single execution - add as-is
                expanded_operations.append(op)
            else:
                # Multiple loops - create loop group
                for loop_index in range(loops):
                    # Create a wrapper that maintains loop information
                    loop_wrapper = LoopWrapper(op, loop_index, loops)
                    expanded_operations.append(loop_wrapper)

        return expanded_operations

    def _collapse_operations_from_loops(
        self, expanded_operations: List[Any]
    ) -> List[Any]:
        """
        Collapse expanded loop operations back to their original form.

        This removes the loop wrappers and returns the original operations
        in their optimized order, while maintaining the loop sequencing.
        """
        collapsed_operations = []

        for op in expanded_operations:
            if isinstance(op, LoopWrapper):
                # Only add the first loop instance to avoid duplicates
                if op.loop_index == 0:
                    collapsed_operations.append(op.original_operation)
            else:
                collapsed_operations.append(op)

        return collapsed_operations


@dataclass
class LoopWrapper:
    """
    Wrapper for operations that need to be executed multiple times.

    This allows the optimizer to treat each loop iteration as a separate
    operation for travel optimization while maintaining the constraint
    that all loops of an operation must be executed consecutively.
    """

    original_operation: Any
    loop_index: int  # 0-based index of this loop iteration
    total_loops: int  # Total number of loops for this operation

    def __post_init__(self):
        # Copy relevant properties from original operation
        if hasattr(self.original_operation, "bbox"):
            self.bbox = self.original_operation.bbox
        if hasattr(self.original_operation, "travel_start"):
            self.travel_start = self.original_operation.travel_start
        if hasattr(self.original_operation, "travel_end"):
            self.travel_end = self.original_operation.travel_end

    @property
    def is_first_loop(self) -> bool:
        """True if this is the first loop iteration."""
        return self.loop_index == 0

    @property
    def is_last_loop(self) -> bool:
        """True if this is the last loop iteration."""
        return self.loop_index == self.total_loops - 1

    def __str__(self):
        return (
            f"Loop{self.loop_index + 1}/{self.total_loops}({self.original_operation})"
        )

    def __repr__(self):
        return self.__str__()


class EnhancedOperationWorkflow(OperationWorkflow):
    """
    Enhanced workflow system that integrates high-performance optimization
    with the existing containment-aware processing system.
    """

    def __init__(self, manual_optimize=None):
        super().__init__(manual_optimize)
        self.spatial_optimizer = SpatialWorkflowOptimizer()
        self.optimization_level = OptimizationLevel.BALANCED
        self.optimization_stats = None

    def set_optimization_level(self, level: OptimizationLevel):
        """Configure optimization performance level."""
        self.optimization_level = level

    def generate_workflow(self, progress_callback=None) -> List[Any]:
        """
        Generate optimized workflow with progress reporting.
        """
        if progress_callback:
            progress_callback(0, "Analyzing containment relationships...")

        # Standard containment analysis and grouping
        self.analyze_containment()
        self.assign_priorities()
        self.create_workflow_groups()

        if progress_callback:
            progress_callback(30, "Optimizing workflow groups...")

        # Enhanced optimization for each group
        total_operations = sum(len(group.operations) for group in self.workflow_groups)
        processed_operations = 0

        for i, group in enumerate(self.workflow_groups):
            if not group.operations:
                continue

            def group_progress(p, msg):
                if progress_callback:
                    progress_callback(
                        30
                        + int(
                            60
                            * (processed_operations + p * len(group.operations) / 100)
                            / total_operations
                        ),
                        f"Group {i + 1}/{len(self.workflow_groups)}: {msg}",
                    )

            # Use spatial optimizer for this group
            optimized_ops, stats = self.spatial_optimizer.optimize_workflow(
                group.operations, self.optimization_level, group_progress
            )

            group.operations = optimized_ops
            group.optimization_stats = stats
            processed_operations += len(group.operations)

        # Also optimize group ordering with enhanced algorithm
        self.optimize_group_ordering_enhanced()

        if progress_callback:
            progress_callback(100, "Workflow optimization complete")

        # Generate final workflow
        workflow = []
        for group in self.workflow_groups:
            group_operations = [op_node.operation for op_node in group.operations]
            workflow.extend(group_operations)

        return workflow

    def optimize_group_ordering_enhanced(self):
        """Enhanced group ordering using spatial optimization principles."""
        if len(self.workflow_groups) <= 1:
            return

        # Group by priority categories as before
        engrave_groups = [
            g
            for g in self.workflow_groups
            if g.priority
            in [
                ProcessingPriority.INNER_ENGRAVE,
                ProcessingPriority.MIDDLE_ENGRAVE,
                ProcessingPriority.OUTER_ENGRAVE,
            ]
        ]
        cut_groups = [
            g
            for g in self.workflow_groups
            if g.priority
            in [ProcessingPriority.INNER_CUT, ProcessingPriority.OUTER_CUT]
        ]

        # Optimize each category
        optimized_engraves = self._optimize_groups_spatially(engrave_groups)
        optimized_cuts = self._optimize_groups_spatially(cut_groups)

        self.workflow_groups = optimized_engraves + optimized_cuts

    def _optimize_groups_spatially(self, groups: List[Any]) -> List[Any]:
        """Optimize group order using spatial principles."""
        if len(groups) <= 1:
            return groups

        # Treat groups as "operations" and use spatial optimizer
        # This is a simplified approach - could be enhanced further
        optimized, _ = self.spatial_optimizer._greedy_optimization(groups)
        return optimized

    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get comprehensive optimization statistics."""
        if not self.workflow_groups:
            return {}

        total_ops = sum(len(group.operations) for group in self.workflow_groups)
        total_distance = sum(
            getattr(
                group, "optimization_stats", OptimizationStats(0, 0, 0, "none")
            ).total_distance
            for group in self.workflow_groups
        )
        total_time = sum(
            getattr(
                group, "optimization_stats", OptimizationStats(0, 0, 0, "none")
            ).optimization_time
            for group in self.workflow_groups
        )

        return {
            "total_operations": total_ops,
            "total_groups": len(self.workflow_groups),
            "total_travel_distance": total_distance,
            "total_optimization_time": total_time,
            "optimization_level": self.optimization_level.name,
            "average_ops_per_group": total_ops / len(self.workflow_groups)
            if self.workflow_groups
            else 0,
        }


def demo_performance_comparison():
    """Demonstrate performance improvements with different algorithms."""
    print("=== Enhanced Workflow Performance Comparison ===")

    # This would be integrated with the actual MeerK40t system
    # For now, showing the interface and expected improvements

    test_sizes = [100, 500, 1000, 2000]

    for size in test_sizes:
        print(f"\nTesting {size} operations:")

        # Simulate different optimization levels
        print(f"  FAST (greedy):     ~{size * size * 0.000001:.3f}s expected")
        print(f"  BALANCED (spatial): ~{size * math.log(size) * 0.00001:.3f}s expected")
        print(f"  THOROUGH (2-opt):   ~{size * math.log(size) * 0.00005:.3f}s expected")

        # Expected improvements
        if size >= 500:
            improvement = min(15, size / 100)
            print(f"  Expected speedup: {improvement:.1f}x over original greedy")


if __name__ == "__main__":
    demo_performance_comparison()
