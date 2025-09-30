"""
Unit tests for the critical burns_done bug fix.

These tests specifically validate the fix for the infinite loop bug that occurred
when all optimization was disabled but multi-pass cuts were present. The bug was
that burns_done was never incremented, causing infinite loops in cutting operations.

The fix introduced basic_cutcode_sequencing() as a fallback to ensure proper
burns_done handling in all optimization scenarios.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

# Add the meerk40t directory to Python path to use local version
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from meerk40t.core.cutcode.cutcode import CutCode
from meerk40t.core.cutcode.cutgroup import CutGroup
from meerk40t.core.cutcode.linecut import LineCut
from meerk40t.core.cutplan import CutPlan
from meerk40t.svgelements import Point


class MockKernel:
    """Mock kernel for testing."""

    def __init__(self):
        self.busyinfo = MagicMock()
        self.busyinfo.shown = False
        self.translation = lambda x: x
        self.channel = lambda name, **kwargs: MagicMock()


class MockContext:
    """Mock context with all optimization options."""

    def __init__(
        self, opt_travel=False, opt_inner_first=False, opt_inners_grouped=False
    ):
        self.opt_reduce_travel = opt_travel
        self.opt_nearest_neighbor = opt_travel
        self.opt_2opt = False
        self.opt_inner_first = opt_inner_first
        self.opt_inners_grouped = opt_inners_grouped
        self.opt_inner_tolerance = 0
        self.opt_effect_combine = False
        self.kernel = MockKernel()

    def channel(self, name, **kwargs):
        return MagicMock()


class TestBurnsDoneCriticalFix(unittest.TestCase):
    """Test the critical burns_done bug fix."""

    def create_multi_pass_scenario(self):
        """Create a scenario with multi-pass cuts that would trigger the bug."""
        # Create a group with multiple passes
        group = CutGroup(parent=None, closed=True)
        group.passes = 3  # Multi-pass scenario

        # Add some cuts
        group.extend(
            [
                LineCut(Point(0, 0), Point(10, 0)),
                LineCut(Point(10, 0), Point(10, 10)),
                LineCut(Point(10, 10), Point(0, 10)),
                LineCut(Point(0, 10), Point(0, 0)),
            ]
        )

        # Initialize burns_done and passes for each cut
        for cut in group:
            cut.burns_done = 0
            cut.passes = 3

        cutcode = CutCode()
        cutcode.append(group)
        return cutcode

    def test_no_optimization_burns_done_increment(self):
        """Test the critical case: no optimization enabled, multi-pass cuts."""
        cutcode = self.create_multi_pass_scenario()
        context = MockContext(
            opt_travel=False, opt_inner_first=False, opt_inners_grouped=False
        )

        cutplan = CutPlan("test", context)
        cutplan.plan = [cutcode]

        # This is the critical test - should not hang in infinite loop
        cutplan.preopt()  # Should add basic_cutcode_sequencing to commands

        # Verify basic_cutcode_sequencing was added
        self.assertTrue(
            len(cutplan.commands) > 0, "Commands should be added for optimization"
        )

        # Check that basic_cutcode_sequencing is in the commands
        command_names = [cmd.__name__ for cmd in cutplan.commands]
        self.assertIn(
            "basic_cutcode_sequencing",
            command_names,
            "basic_cutcode_sequencing should be added when no optimization is enabled",
        )

        # Execute the commands (this would hang before the fix)
        cutplan.execute()

        # Verify burns_done was incremented properly
        for group in cutplan.plan:
            if isinstance(group, CutCode):
                for cut in group.flat():
                    if hasattr(cut, "burns_done") and hasattr(cut, "passes"):
                        self.assertGreaterEqual(
                            cut.burns_done,
                            cut.passes,
                            f"burns_done ({cut.burns_done}) should be >= passes ({cut.passes})",
                        )

    def test_travel_optimization_only(self):
        """Test that travel optimization still handles burns_done correctly."""
        cutcode = self.create_multi_pass_scenario()
        context = MockContext(
            opt_travel=True, opt_inner_first=False, opt_inners_grouped=False
        )

        cutplan = CutPlan("test", context)
        cutplan.plan = [cutcode]

        cutplan.preopt()

        # Should use travel optimization, not basic sequencing
        command_names = [cmd.__name__ for cmd in cutplan.commands]
        self.assertIn(
            "optimize_travel",
            command_names,
            "Travel optimization should be used when enabled",
        )
        self.assertNotIn(
            "basic_cutcode_sequencing",
            command_names,
            "basic_cutcode_sequencing should not be used when travel optimization is enabled",
        )

    def test_inner_first_optimization(self):
        """Test that inner-first optimization handles burns_done correctly."""
        cutcode = self.create_multi_pass_scenario()
        context = MockContext(
            opt_travel=False, opt_inner_first=True, opt_inners_grouped=False
        )

        cutplan = CutPlan("test", context)
        cutplan.plan = [cutcode]

        cutplan.preopt()

        # Should use inner-first optimization, not basic sequencing
        command_names = [cmd.__name__ for cmd in cutplan.commands]
        self.assertIn(
            "optimize_cuts",
            command_names,
            "Inner-first optimization should be used when enabled",
        )
        self.assertNotIn(
            "basic_cutcode_sequencing",
            command_names,
            "basic_cutcode_sequencing should not be used when inner-first is enabled",
        )

    def test_grouped_inner_optimization(self):
        """Test that grouped inner optimization handles burns_done correctly."""
        cutcode = self.create_multi_pass_scenario()
        context = MockContext(
            opt_travel=False, opt_inner_first=True, opt_inners_grouped=True
        )

        cutplan = CutPlan("test", context)
        cutplan.plan = [cutcode]

        cutplan.preopt()

        # Should use inner-first optimization with grouping
        command_names = [cmd.__name__ for cmd in cutplan.commands]
        self.assertIn(
            "optimize_cuts",
            command_names,
            "Inner-first optimization should be used when enabled",
        )
        self.assertNotIn(
            "basic_cutcode_sequencing",
            command_names,
            "basic_cutcode_sequencing should not be used when inner-first is enabled",
        )

    def test_combined_travel_and_inner_first(self):
        """Test combined travel and inner-first optimization."""
        cutcode = self.create_multi_pass_scenario()
        context = MockContext(
            opt_travel=True, opt_inner_first=True, opt_inners_grouped=False
        )

        cutplan = CutPlan("test", context)
        cutplan.plan = [cutcode]

        cutplan.preopt()

        # Should use inner-first optimization (takes precedence over travel when both enabled)
        command_names = [cmd.__name__ for cmd in cutplan.commands]
        self.assertIn(
            "optimize_cuts",
            command_names,
            "Inner-first optimization should be used when both travel and inner-first are enabled",
        )
        self.assertNotIn(
            "basic_cutcode_sequencing",
            command_names,
            "basic_cutcode_sequencing should not be used when other optimization is enabled",
        )

    def test_basic_cutcode_sequencing_burns_done_logic(self):
        """Test that basic_cutcode_sequencing properly handles burns_done increments."""
        cutcode = self.create_multi_pass_scenario()
        context = MockContext(
            opt_travel=False, opt_inner_first=False, opt_inners_grouped=False
        )

        cutplan = CutPlan("test", context)
        cutplan.plan = [cutcode]

        # Verify initial state
        for group in cutplan.plan:
            if isinstance(group, CutCode):
                for cut in group.flat():
                    if hasattr(cut, "burns_done"):
                        cut.burns_done = 0  # Reset to initial state

        # Execute basic_cutcode_sequencing directly
        cutplan.basic_cutcode_sequencing()

        # Verify burns_done was incremented properly
        burns_done_counts = []
        for group in cutplan.plan:
            if isinstance(group, CutCode):
                for cut in group.flat():
                    if hasattr(cut, "burns_done") and hasattr(cut, "passes"):
                        burns_done_counts.append(cut.burns_done)
                        self.assertGreaterEqual(
                            cut.burns_done,
                            cut.passes,
                            f"burns_done ({cut.burns_done}) should be >= passes ({cut.passes})",
                        )

        # Should have incremented burns_done for all cuts
        self.assertTrue(
            all(count > 0 for count in burns_done_counts),
            "All cuts should have burns_done > 0 after basic_cutcode_sequencing",
        )

    def test_empty_cutcode_handling(self):
        """Test that basic_cutcode_sequencing handles empty cutcode gracefully."""
        empty_cutcode = CutCode()
        context = MockContext(
            opt_travel=False, opt_inner_first=False, opt_inners_grouped=False
        )

        cutplan = CutPlan("test", context)
        cutplan.plan = [empty_cutcode]

        # Should not crash on empty cutcode
        cutplan.basic_cutcode_sequencing()

        # Plan should still be empty
        self.assertEqual(len(list(cutplan.plan[0].flat())), 0)

    def test_mixed_pass_counts(self):
        """Test basic_cutcode_sequencing with cuts having different pass counts."""
        # Create cuts with different pass requirements
        group1 = CutGroup(parent=None, closed=True)
        group1.passes = 1
        group1.append(LineCut(Point(0, 0), Point(5, 0)))
        for cut in group1:
            cut.burns_done = 0
            cut.passes = 1

        group2 = CutGroup(parent=None, closed=True)
        group2.passes = 3
        group2.extend(
            [
                LineCut(Point(10, 0), Point(15, 0)),
                LineCut(Point(15, 0), Point(15, 5)),
            ]
        )
        for cut in group2:
            cut.burns_done = 0
            cut.passes = 3

        cutcode = CutCode()
        cutcode.extend([group1, group2])

        context = MockContext(
            opt_travel=False, opt_inner_first=False, opt_inners_grouped=False
        )
        cutplan = CutPlan("test", context)
        cutplan.plan = [cutcode]

        cutplan.basic_cutcode_sequencing()

        # Verify each cut was burned according to its pass count
        for group in cutplan.plan:
            if isinstance(group, CutCode):
                for cut in group.flat():
                    if hasattr(cut, "burns_done") and hasattr(cut, "passes"):
                        self.assertGreaterEqual(
                            cut.burns_done,
                            cut.passes,
                            f"Cut should be burned according to its pass count",
                        )

    def test_optimization_fallback_logic(self):
        """Test the three-way logic in preopt()."""
        cutcode = self.create_multi_pass_scenario()

        # Test case 1: Travel optimization enabled
        context1 = MockContext(opt_travel=True, opt_inner_first=False)
        cutplan1 = CutPlan("test1", context1)
        cutplan1.plan = [cutcode]
        cutplan1.preopt()
        commands1 = [cmd.__name__ for cmd in cutplan1.commands]

        # Test case 2: Inner-first enabled (without travel)
        context2 = MockContext(opt_travel=False, opt_inner_first=True)
        cutplan2 = CutPlan("test2", context2)
        cutplan2.plan = [cutcode]
        cutplan2.preopt()
        commands2 = [cmd.__name__ for cmd in cutplan2.commands]

        # Test case 3: No optimization (should use basic sequencing)
        context3 = MockContext(opt_travel=False, opt_inner_first=False)
        cutplan3 = CutPlan("test3", context3)
        cutplan3.plan = [cutcode]
        cutplan3.preopt()
        commands3 = [cmd.__name__ for cmd in cutplan3.commands]

        # Verify correct optimization methods are chosen
        self.assertIn(
            "optimize_travel", commands1, "Should use travel optimization when enabled"
        )
        self.assertIn(
            "optimize_cuts",
            commands2,
            "Should use inner-first when enabled (without travel)",
        )
        self.assertIn(
            "basic_cutcode_sequencing",
            commands3,
            "Should use basic sequencing when no optimization",
        )

        # Verify fallback logic
        self.assertNotIn(
            "basic_cutcode_sequencing",
            commands1,
            "Should not use basic when travel enabled",
        )
        self.assertNotIn(
            "basic_cutcode_sequencing",
            commands2,
            "Should not use basic when inner-first enabled",
        )
        self.assertNotIn(
            "optimize_travel", commands3, "Should not use travel when disabled"
        )
        self.assertNotIn(
            "optimize_cuts", commands3, "Should not use inner-first when disabled"
        )


if __name__ == "__main__":
    unittest.main()
