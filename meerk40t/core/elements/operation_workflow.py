"""
Operation Workflow Management System for MeerK40t

This module provides sophisticated workflow management for laser operations,
ensuring proper processing order to prevent material fallout while optimizing
travel efficiency.

Key Architecture Understanding:
- Operations live under 'branch ops' and contain references as children
- Elements live under 'branch elems'
- References are nodes that point to actual elements via .node property
- Multiple operations can reference the same element through different references
- Workflow must respect containment hierarchy to prevent material fallout

The system analyzes containment relationships between the actual elements
referenced by operations and creates an optimal processing order.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict


class OperationType(Enum):
    """Types of laser operations with priority implications."""

    CUT = "op cut"
    ENGRAVE = "op engrave"
    IMAGE = "op image"
    RASTER = "op raster"


class ProcessingPriority(Enum):
    """Processing priority levels for workflow organization."""

    INNER_ENGRAVE = 1  # Innermost engraving/details (highest priority)
    MIDDLE_ENGRAVE = 2  # Mid-level engraving/details
    OUTER_ENGRAVE = 3  # Outer engraving/details
    INNER_CUT = 4  # Inner cuts (more contained)
    OUTER_CUT = 5  # Outer cuts (least contained, lowest priority)


@dataclass
class OperationNode:
    """
    Represents a single operation in the workflow with its referenced elements.
    """

    operation: Any  # The actual operation node
    operation_type: str  # "op cut", "op engrave", etc.
    referenced_elements: List[Any]  # List of actual elements (not references)
    references: List[Any]  # List of reference nodes
    priority: ProcessingPriority = ProcessingPriority.OUTER_CUT
    containment_level: int = 0  # Depth in containment hierarchy
    label: str = ""
    bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)
    travel_start: Optional[complex] = None
    travel_end: Optional[complex] = None

    def __post_init__(self):
        if hasattr(self.operation, "label"):
            self.label = (
                self.operation.label
                or f"{self.operation_type.replace('op ', '').title()}"
            )
        else:
            self.label = f"{self.operation_type.replace('op ', '').title()}"


@dataclass
class WorkflowGroup:
    """
    Groups operations by processing priority for batch optimization.
    """

    priority: ProcessingPriority
    operations: List[OperationNode] = field(default_factory=list)
    total_travel_distance: float = 0.0

    def add_operation(self, op_node: OperationNode):
        """Add an operation to this group."""
        self.operations.append(op_node)

    def __len__(self):
        return len(self.operations)


class OperationWorkflow:
    """
    Main workflow orchestrator that analyzes MeerK40t operations and creates
    optimal processing sequences based on containment relationships.
    """

    def __init__(self, tolerance: float = 1e-3):
        self.operations: List[OperationNode] = []
        self.workflow_groups: List[WorkflowGroup] = []
        self.tolerance = tolerance
        self.containment_hierarchy = {}
        self.element_geometries = {}

    def add_operation(self, operation_node, operation_type: str):
        """
        Add an operation to the workflow.

        Args:
            operation_node: The operation node from MeerK40t tree
            operation_type: Type string like "op cut", "op engrave"
        """
        # Extract referenced elements from the operation
        referenced_elements = []
        references = []

        # Navigate through the operation's children to find references
        if hasattr(operation_node, "children"):
            for child in operation_node.children:
                if hasattr(child, "type") and child.type == "reference":
                    references.append(child)
                    if hasattr(child, "node") and child.node is not None:
                        referenced_elements.append(child.node)

        # Calculate bounding box from all referenced elements
        bbox = self._calculate_combined_bbox(referenced_elements)

        # Create operation node
        op_node = OperationNode(
            operation=operation_node,
            operation_type=operation_type,
            referenced_elements=referenced_elements,
            references=references,
            bbox=bbox,
        )

        self.operations.append(op_node)

    def _calculate_combined_bbox(
        self, elements: List[Any]
    ) -> Tuple[float, float, float, float]:
        """Calculate combined bounding box for a list of elements."""
        if not elements:
            return (0, 0, 0, 0)

        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")

        for element in elements:
            try:
                if hasattr(element, "bbox"):
                    bbox = element.bbox()
                elif hasattr(element, "bounds"):
                    bbox = element.bounds
                else:
                    continue

                if bbox and len(bbox) >= 4:
                    min_x = min(min_x, float(bbox[0]))
                    min_y = min(min_y, float(bbox[1]))
                    max_x = max(max_x, float(bbox[2]))
                    max_y = max(max_y, float(bbox[3]))
            except (AttributeError, TypeError, ValueError):
                continue

        if min_x == float("inf"):
            return (0, 0, 0, 0)

        return (min_x, min_y, max_x, max_y)

    def _extract_element_geometries(self):
        """
        Extract geometries from all referenced elements for containment analysis.
        """
        self.element_geometries.clear()

        for op_node in self.operations:
            for element in op_node.referenced_elements:
                if element not in self.element_geometries:
                    try:
                        # Try to get geometry from the element
                        if hasattr(element, "as_geometry"):
                            geom = element.as_geometry()
                        elif hasattr(element, "geometry"):
                            geom = element.geometry
                        else:
                            geom = None

                        if geom is not None:
                            self.element_geometries[element] = geom

                    except (AttributeError, TypeError):
                        # Skip elements without geometry
                        pass

    def analyze_containment(self):
        """
        Analyze containment relationships between elements referenced by operations.
        Uses the existing geometry hierarchy analysis but works with actual elements.
        """
        try:
            # Import here to avoid circular imports
            from .manual_optimize import build_geometry_hierarchy

            # Extract geometries from all referenced elements
            self._extract_element_geometries()

            if not self.element_geometries:
                # No geometries to analyze
                return

            # Create geometry list for hierarchy analysis
            geometry_list = []
            element_to_index = {}

            for idx, (element, geometry) in enumerate(self.element_geometries.items()):
                geometry_list.append(geometry)
                element_to_index[element] = idx

            # Build containment hierarchy
            hierarchy = build_geometry_hierarchy(
                geometry_list, tolerance=self.tolerance
            )

            # Map hierarchy results back to operations
            for op_node in self.operations:
                max_level = 0
                for element in op_node.referenced_elements:
                    if element in element_to_index:
                        idx = element_to_index[element]
                        if idx in hierarchy:
                            level = hierarchy[idx].get("level", 0)
                            max_level = max(max_level, level)

                op_node.containment_level = max_level

        except ImportError:
            # Fallback if manual_optimize is not available
            pass

    def assign_priorities(self):
        """
        Assign processing priorities based on operation type and containment level.
        """
        for op_node in self.operations:
            op_type = op_node.operation_type
            level = op_node.containment_level

            if op_type == "op cut":
                # For cuts: higher containment level = process first (inner cuts before outer)
                if level >= 2:
                    op_node.priority = ProcessingPriority.INNER_CUT
                else:
                    op_node.priority = ProcessingPriority.OUTER_CUT
            else:
                # For non-cuts (engrave, image, raster): higher containment = process first
                if level >= 2:
                    op_node.priority = ProcessingPriority.INNER_ENGRAVE
                elif level >= 1:
                    op_node.priority = ProcessingPriority.MIDDLE_ENGRAVE
                else:
                    op_node.priority = ProcessingPriority.OUTER_ENGRAVE

    def create_workflow_groups(self):
        """
        Group operations by processing priority.
        """
        self.workflow_groups.clear()
        groups_by_priority = defaultdict(list)

        # Group operations by priority
        for op_node in self.operations:
            groups_by_priority[op_node.priority].append(op_node)

        # Create WorkflowGroup objects
        for priority in ProcessingPriority:
            if priority in groups_by_priority:
                group = WorkflowGroup(priority=priority)
                group.operations = groups_by_priority[priority]
                self.workflow_groups.append(group)

    def optimize_travel_within_groups(self):
        """
        Optimize travel distance within each workflow group.
        Uses simple greedy nearest-neighbor for now.
        """
        for group in self.workflow_groups:
            if len(group.operations) <= 1:
                continue

            # Simple greedy optimization
            optimized = [group.operations[0]]  # Start with first operation
            remaining = group.operations[1:]

            while remaining:
                current_pos = self._get_operation_end_point(optimized[-1])

                # Find nearest remaining operation
                nearest_idx = 0
                nearest_dist = float("inf")

                for i, op_node in enumerate(remaining):
                    next_pos = self._get_operation_start_point(op_node)
                    dist = abs(next_pos - current_pos)
                    if isinstance(dist, complex):
                        dist = abs(dist)

                    if dist < nearest_dist:
                        nearest_dist = dist
                        nearest_idx = i

                # Move nearest to optimized list
                optimized.append(remaining.pop(nearest_idx))

            group.operations = optimized

    def optimize_group_ordering(self):
        """
        Optimize the order of workflow groups to minimize travel between groups,
        while respecting containment-based priority constraints.
        """
        if len(self.workflow_groups) <= 1:
            return

        # Group groups by their priority level categories
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

        # Optimize order within each category
        optimized_engraves = self._optimize_groups_by_travel(engrave_groups)
        optimized_cuts = self._optimize_groups_by_travel(cut_groups)

        # Rebuild workflow groups in optimized order
        self.workflow_groups = optimized_engraves + optimized_cuts

    def _optimize_groups_by_travel(
        self, groups: List[WorkflowGroup]
    ) -> List[WorkflowGroup]:
        """
        Optimize the order of groups to minimize travel distance between them.
        Uses greedy nearest-neighbor approach.
        """
        if len(groups) <= 1:
            return groups

        # Start with the first group
        optimized = [groups[0]]
        remaining = groups[1:]

        while remaining:
            # Get ending position of last group
            last_group = optimized[-1]
            last_position = self._get_group_end_point(last_group)

            # Find nearest remaining group
            nearest_idx = 0
            nearest_dist = float("inf")

            for i, group in enumerate(remaining):
                group_start = self._get_group_start_point(group)
                dist = abs(group_start - last_position)
                if isinstance(dist, complex):
                    dist = abs(dist)

                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = i

            # Move nearest group to optimized list
            optimized.append(remaining.pop(nearest_idx))

        return optimized

    def _get_group_start_point(self, group: WorkflowGroup) -> complex:
        """Get the starting point of the first operation in a group."""
        if not group.operations:
            return complex(0, 0)
        return self._get_operation_start_point(group.operations[0])

    def _get_group_end_point(self, group: WorkflowGroup) -> complex:
        """Get the ending point of the last operation in a group."""
        if not group.operations:
            return complex(0, 0)
        return self._get_operation_end_point(group.operations[-1])

    def generate_workflow(self) -> List[Any]:
        """
        Generate the final optimized workflow.

        Returns:
            List of operation nodes in optimal processing order
        """
        # Analyze containment relationships
        self.analyze_containment()

        # Assign priorities based on containment and type
        self.assign_priorities()

        # Create workflow groups
        self.create_workflow_groups()

        # Optimize travel within groups
        self.optimize_travel_within_groups()

        # Optimize travel between groups at same containment level
        self.optimize_group_ordering()

        # Generate final operation list
        workflow = []

        for group in self.workflow_groups:
            group_operations = [op_node.operation for op_node in group.operations]
            workflow.extend(group_operations)

            # Calculate travel distance for this group
            group_travel = self._calculate_group_travel_distance(group)
            group.total_travel_distance = group_travel

        return workflow

    def _get_operation_start_point(self, op_node: OperationNode) -> complex:
        """Get the starting point for an operation."""
        if op_node.travel_start is not None:
            return op_node.travel_start

        bbox = op_node.bbox
        # Use bottom-left corner as default start point
        return complex(float(bbox[0]), float(bbox[1]))

    def _get_operation_end_point(self, op_node: OperationNode) -> complex:
        """Get the ending point for an operation."""
        if op_node.travel_end is not None:
            return op_node.travel_end

        bbox = op_node.bbox
        # Use top-right corner as default end point
        return complex(float(bbox[2]), float(bbox[3]))

    def _calculate_group_travel_distance(self, group: WorkflowGroup) -> float:
        """Calculate total travel distance for operations in a group."""
        if len(group.operations) < 2:
            return 0.0

        total_distance = 0.0

        for i in range(len(group.operations) - 1):
            current_end = self._get_operation_end_point(group.operations[i])
            next_start = self._get_operation_start_point(group.operations[i + 1])

            # Ensure we get real distance by computing magnitude of complex difference
            distance = abs(next_start - current_end)
            if isinstance(distance, complex):
                distance = abs(distance)  # Get magnitude if still complex

            total_distance += float(distance)

        return total_distance

    def get_workflow_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the generated workflow.

        Returns:
            Dictionary with workflow statistics and information
        """
        total_operations = len(self.operations)
        total_groups = len(self.workflow_groups)

        # Count containment relationships
        containment_relationships = sum(
            1 for op in self.operations if op.containment_level > 0
        )

        # Calculate total travel distance
        total_travel = sum(
            group.total_travel_distance for group in self.workflow_groups
        )

        # Group details
        groups = []
        for group in self.workflow_groups:
            groups.append(
                {
                    "priority": group.priority.name,
                    "operation_count": len(group.operations),
                    "travel_distance": group.total_travel_distance,
                    "operations": [op.label for op in group.operations],
                }
            )

        return {
            "total_operations": total_operations,
            "total_groups": total_groups,
            "containment_relationships": containment_relationships,
            "total_travel_distance": total_travel,
            "groups": groups,
        }


def create_operation_workflow(
    operations: List[Tuple[Any, str]], tolerance: float = 1e-3
) -> OperationWorkflow:
    """
    Create and populate an OperationWorkflow from a list of operations.

    Args:
        operations: List of (operation_node, operation_type) tuples
        tolerance: Geometric tolerance for containment analysis

    Returns:
        Configured OperationWorkflow instance
    """
    workflow = OperationWorkflow(tolerance=tolerance)

    for operation_node, operation_type in operations:
        workflow.add_operation(operation_node, operation_type)

    return workflow
