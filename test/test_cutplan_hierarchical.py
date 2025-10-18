"""
Test suite for hierarchical cut planning module.

Tests the hierarchy building, validation, and selection logic
for the new hierarchical cutplan implementation.
"""

import unittest
from unittest.mock import Mock, MagicMock

# Import the hierarchical cut plan module
from meerk40t.core.cutplan_hierarchical import (
    HierarchyLevel,
    HierarchyContext,
    build_hierarchy_levels,
    validate_hierarchy,
    HierarchicalCutPlan,
    print_hierarchy,
    print_hierarchy_stats,
)

from meerk40t.core.cutcode.cutcode import CutCode


class MockCutGroup:
    """Mock CutGroup for testing hierarchy building."""
    
    def __init__(self, name: str, inside=None, contains=None):
        self.name = name
        self.inside = inside or []
        self.contains = contains or []
        self.burns_done = 0
        self.passes = 1
    
    def __repr__(self) -> str:
        return f"MockCutGroup({self.name})"
    
    def __str__(self) -> str:
        return self.name


class TestHierarchyLevel(unittest.TestCase):
    """Test HierarchyLevel class."""
    
    def test_create_hierarchy_level(self):
        """Test creating a hierarchy level."""
        level = HierarchyLevel(level_number=0)
        self.assertEqual(level.level, 0)
        self.assertEqual(len(level.cuts), 0)
        self.assertIsNone(level.parent_level)
        self.assertEqual(len(level.child_levels), 0)
    
    def test_add_cut_to_level(self):
        """Test adding a cut to a level."""
        level = HierarchyLevel(level_number=0)
        cut = MockCutGroup("A")
        
        level.add_cut(cut)  # type: ignore
        self.assertEqual(len(level.cuts), 1)
        self.assertIn(cut, level.cuts)
    
    def test_is_complete_empty_level(self):
        """Test is_complete() on empty level."""
        level = HierarchyLevel(level_number=0)
        self.assertTrue(level.is_complete())
    
    def test_is_complete_incomplete(self):
        """Test is_complete() with incomplete cuts."""
        level = HierarchyLevel(level_number=0)
        cut = MockCutGroup("A")
        cut.burns_done = 0
        cut.passes = 1
        
        level.add_cut(cut)  # type: ignore
        self.assertFalse(level.is_complete())
    
    def test_is_complete_done(self):
        """Test is_complete() with completed cuts."""
        level = HierarchyLevel(level_number=0)
        cut = MockCutGroup("A")
        cut.burns_done = 1
        cut.passes = 1
        
        level.add_cut(cut)  # type: ignore
        self.assertTrue(level.is_complete())
    
    def test_add_child_level(self):
        """Test adding child level."""
        parent = HierarchyLevel(level_number=0)
        child = HierarchyLevel(level_number=1)
        
        parent.add_child_level(child)
        self.assertEqual(len(parent.child_levels), 1)
        self.assertIs(child.parent_level, parent)


class TestHierarchyContext(unittest.TestCase):
    """Test HierarchyContext class."""
    
    def test_create_context(self):
        """Test creating a hierarchy context."""
        context = HierarchyContext()
        self.assertEqual(len(context.root_levels), 0)
        self.assertEqual(len(context.all_levels), 0)
    
    def test_add_root_level(self):
        """Test adding a root level."""
        context = HierarchyContext()
        level = HierarchyLevel(level_number=0)
        
        context.add_root_level(level)
        self.assertEqual(len(context.root_levels), 1)
        self.assertEqual(len(context.all_levels), 1)
    
    def test_get_processing_order(self):
        """Test getting levels in processing order (innermost first)."""
        context = HierarchyContext()
        
        level0 = HierarchyLevel(level_number=0)
        level1 = HierarchyLevel(level_number=1)
        level2 = HierarchyLevel(level_number=2)
        
        context.add_root_level(level0)
        context.add_level(level1)
        context.add_level(level2)
        
        order = context.get_processing_order()
        # Should be: deepest first
        self.assertEqual(order[0].level, 2)
        self.assertEqual(order[1].level, 1)
        self.assertEqual(order[2].level, 0)


class TestBuildHierarchyLevels(unittest.TestCase):
    """Test build_hierarchy_levels function."""
    
    def test_empty_cutcode(self):
        """Test building hierarchy from empty CutCode."""
        context = CutCode()
        hierarchy = build_hierarchy_levels(context)
        
        self.assertEqual(len(hierarchy.all_levels), 0)
        self.assertEqual(len(hierarchy.root_levels), 0)
    
    def test_single_root_group(self):
        """Test building hierarchy with single root group."""
        # Create mock groups
        group_a = MockCutGroup("A", inside=[], contains=[])
        
        # Create mock CutCode
        context = MagicMock()
        context.__iter__ = Mock(return_value=iter([group_a]))
        
        hierarchy = build_hierarchy_levels(context)
        
        self.assertEqual(len(hierarchy.root_levels), 1)
        self.assertEqual(len(hierarchy.all_levels), 1)
        self.assertIn(group_a, hierarchy.root_levels[0].cuts)
    
    def test_nested_hierarchy(self):
        """Test building hierarchy with nested groups."""
        # Create hierarchy: A contains B, B contains C
        group_a = MockCutGroup("A", inside=[], contains=[])
        group_b = MockCutGroup("B", inside=[group_a], contains=[])
        group_c = MockCutGroup("C", inside=[group_b], contains=[])
        
        # Create mock CutCode
        context = MagicMock()
        context.__iter__ = Mock(return_value=iter([group_a, group_b, group_c]))
        
        hierarchy = build_hierarchy_levels(context)
        
        # Check structure
        self.assertEqual(len(hierarchy.root_levels), 1)
        self.assertEqual(len(hierarchy.all_levels), 3)
        
        # Check levels
        self.assertEqual(hierarchy.root_levels[0].level, 0)
        self.assertIn(group_a, hierarchy.root_levels[0].cuts)
        
        # Check that B is at level 1
        level_by_num_1 = [level for level in hierarchy.all_levels if level.level == 1]
        self.assertEqual(len(level_by_num_1), 1)
        self.assertIn(group_b, level_by_num_1[0].cuts)
        
        # Check that C is at level 2
        level_by_num_2 = [level for level in hierarchy.all_levels if level.level == 2]
        self.assertEqual(len(level_by_num_2), 1)
        self.assertIn(group_c, level_by_num_2[0].cuts)
    
    def test_multiple_roots(self):
        """Test building hierarchy with multiple independent roots."""
        # Create two independent hierarchies: A, B (roots)
        group_a = MockCutGroup("A", inside=[], contains=[])
        group_b = MockCutGroup("B", inside=[], contains=[])
        
        # Create mock CutCode
        context = MagicMock()
        context.__iter__ = Mock(return_value=iter([group_a, group_b]))
        
        hierarchy = build_hierarchy_levels(context)
        
        self.assertEqual(len(hierarchy.root_levels), 2)
        self.assertEqual(len(hierarchy.all_levels), 2)


class TestValidateHierarchy(unittest.TestCase):
    """Test validate_hierarchy function."""
    
    def test_valid_hierarchy(self):
        """Test validation of valid hierarchy."""
        hierarchy = HierarchyContext()
        level0 = HierarchyLevel(level_number=0)
        level1 = HierarchyLevel(level_number=1, parent_level=level0)
        
        hierarchy.add_root_level(level0)
        hierarchy.add_level(level1)
        level0.add_child_level(level1)
        
        is_valid, errors = validate_hierarchy(hierarchy)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)


class TestHierarchicalCutPlan(unittest.TestCase):
    """Test HierarchicalCutPlan class."""
    
    def test_create_optimizer(self):
        """Test creating a hierarchical cut plan optimizer."""
        optimizer = HierarchicalCutPlan()
        self.assertIsNotNone(optimizer)
    
    def test_optimize_with_empty_cutcode(self):
        """Test optimizing an empty CutCode."""
        optimizer = HierarchicalCutPlan()
        context = CutCode()
        
        result = optimizer.optimize_with_hierarchy(
            context,
            use_inner_first=False
        )
        
        # Should return valid CutCode (though possibly empty)
        self.assertIsInstance(result, CutCode)


class TestPrintFunctions(unittest.TestCase):
    """Test debugging print functions."""
    
    def test_print_hierarchy(self):
        """Test print_hierarchy function."""
        hierarchy = HierarchyContext()
        level0 = HierarchyLevel(level_number=0)
        hierarchy.add_root_level(level0)
        
        output = print_hierarchy(hierarchy)
        self.assertIn("Hierarchy Structure", output)
        self.assertIn("Root levels: 1", output)
    
    def test_print_hierarchy_stats(self):
        """Test print_hierarchy_stats function."""
        hierarchy = HierarchyContext()
        level0 = HierarchyLevel(level_number=0)
        group = MockCutGroup("A")
        level0.add_cut(group)  # type: ignore
        hierarchy.add_root_level(level0)
        
        output = print_hierarchy_stats(hierarchy)
        self.assertIn("Hierarchy Statistics", output)
        self.assertIn("Total cuts: 1", output)


if __name__ == '__main__':
    unittest.main()
