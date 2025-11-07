#!/usr/bin/env python3

"""
Unit tests for cutplan travel optimization and piece-based processing.

These tests validate the critical fixes and enhancements made to the cutplan optimization system:

1. **Optimization Priority Hierarchy**: Tests that inner-first optimization takes precedence
   over travel-only optimization when both are enabled, fixing the original conflict.

2. **Piece-Based Processing**: Tests that related inner/outer groups are spatially grouped
   into pieces, with travel optimization between pieces while maintaining inner-first
   constraints within each piece.

3. **Travel Optimization Between Pieces**: Tests that pieces are processed in distance-
   optimized order from the starting position.

4. **Inner-First Within Pieces**: Tests that inner-first constraints are maintained
   within each spatial piece rather than globally across all pieces.

5. **End-to-End Integration**: Comprehensive tests validating the complete optimization
   pipeline from CutPlan.preopt() through to final cut sequencing.
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
from meerk40t.core.cutplan import (
    CutPlan,
    inner_first_ident,
    short_travel_cutcode_optimized,
)
from meerk40t.svgelements import Point


class MockKernel:
    """Mock kernel for testing."""

    def __init__(self):
        self.busyinfo = MagicMock()
        self.busyinfo.shown = False
        self.translation = lambda x: x
        self.channel = lambda name, **kwargs: MagicMock()


class MockDevice:
    """Mock device for testing."""

    def __init__(self):
        self.view = MagicMock()
        self.view.native_scale_x = 1.0
        self.view.native_scale_y = 1.0


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
        self.device = MockDevice()

    def channel(self, name, **kwargs):
        return MagicMock()


class TestCutplanTravelOptimization(unittest.TestCase):
    """Test travel optimization and piece-based processing in cutplan."""

    def create_two_piece_scenario(self):
        """Create a scenario with two distinct spatial pieces for testing."""
        # Piece 1: Far from start at (100, 100)
        piece1_inner_cuts = [
            LineCut((90, 90), (110, 90)),
            LineCut((110, 90), (110, 110)),
            LineCut((110, 110), (90, 110)),
            LineCut((90, 110), (90, 90)),
        ]

        piece1_outer_cuts = [
            LineCut((80, 80), (120, 80)),
            LineCut((120, 80), (120, 120)),
            LineCut((120, 120), (80, 120)),
            LineCut((80, 120), (80, 80)),
        ]

        # Piece 2: Close to start at (10, 10)
        piece2_inner_cuts = [
            LineCut((5, 5), (15, 5)),
            LineCut((15, 5), (15, 15)),
            LineCut((15, 15), (5, 15)),
            LineCut((5, 15), (5, 5)),
        ]

        piece2_outer_cuts = [
            LineCut((0, 0), (20, 0)),
            LineCut((20, 0), (20, 20)),
            LineCut((20, 20), (0, 20)),
            LineCut((0, 20), (0, 0)),
        ]

        # Create groups
        piece1_inner = CutGroup(parent=None, children=piece1_inner_cuts, closed=True)
        piece1_outer = CutGroup(parent=None, children=piece1_outer_cuts, closed=True)
        piece2_inner = CutGroup(parent=None, children=piece2_inner_cuts, closed=True)
        piece2_outer = CutGroup(parent=None, children=piece2_outer_cuts, closed=True)

        # Set parent relationships and initialize cuts
        for cut in piece1_inner_cuts:
            cut.parent = piece1_inner
            cut.passes = 1
            cut.burns_done = 0
        for cut in piece1_outer_cuts:
            cut.parent = piece1_outer
            cut.passes = 1
            cut.burns_done = 0
        for cut in piece2_inner_cuts:
            cut.parent = piece2_inner
            cut.passes = 1
            cut.burns_done = 0
        for cut in piece2_outer_cuts:
            cut.parent = piece2_outer
            cut.passes = 1
            cut.burns_done = 0

        # Set up containment relationships (ignore lint errors for test mocking)
        try:
            piece1_outer.contains = [piece1_inner]
            piece1_inner.inside = piece1_outer
            piece2_outer.contains = [piece2_inner]
            piece2_inner.inside = piece2_outer
        except Exception:
            pass  # Expected for mock attributes

        return piece1_inner, piece1_outer, piece2_inner, piece2_outer

    def analyze_cut_sequence(self, result_cuts):
        """Analyze cut sequence to determine piece order and inner-first compliance."""
        piece1_positions = []
        piece2_positions = []

        for i, cut in enumerate(result_cuts):
            start = (round(cut.start[0]), round(cut.start[1]))

            # Piece 1 coordinates (around 100, 100)
            if start in [
                (90, 90),
                (110, 90),
                (110, 110),
                (90, 110),
                (80, 80),
                (120, 80),
                (120, 120),
                (80, 120),
            ]:
                piece1_positions.append(i)
            # Piece 2 coordinates (around 10, 10)
            elif start in [
                (5, 5),
                (15, 5),
                (15, 15),
                (5, 15),
                (0, 0),
                (20, 0),
                (20, 20),
                (0, 20),
            ]:
                piece2_positions.append(i)

        return piece1_positions, piece2_positions

    def test_optimization_priority_hierarchy(self):
        """Test that inner-first takes precedence over travel optimization when both enabled."""
        (
            piece1_inner,
            piece1_outer,
            piece2_inner,
            piece2_outer,
        ) = self.create_two_piece_scenario()

        context = MockContext(
            opt_travel=True, opt_inner_first=True, opt_inners_grouped=False
        )
        cutcode = CutCode()
        cutcode.extend([piece1_inner, piece1_outer, piece2_inner, piece2_outer])

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
            "optimize_travel",
            command_names,
            "Travel-only optimization should not be used when inner-first is enabled",
        )

    def test_travel_optimization_only(self):
        """Test travel optimization when inner-first is disabled."""
        (
            piece1_inner,
            piece1_outer,
            piece2_inner,
            piece2_outer,
        ) = self.create_two_piece_scenario()

        context = MockContext(
            opt_travel=True, opt_inner_first=False, opt_inners_grouped=False
        )
        cutcode = CutCode()
        cutcode.extend([piece1_inner, piece1_outer, piece2_inner, piece2_outer])

        cutplan = CutPlan("test", context)
        cutplan.plan = [cutcode]
        cutplan.preopt()

        # Should use travel optimization when inner-first is disabled
        command_names = [cmd.__name__ for cmd in cutplan.commands]
        self.assertIn(
            "optimize_travel",
            command_names,
            "Travel optimization should be used when enabled without inner-first",
        )
        self.assertNotIn(
            "optimize_cuts",
            command_names,
            "Inner-first optimization should not be used when disabled",
        )

    def test_piece_based_processing_travel_order(self):
        """Test that pieces are processed in travel-optimized order (closer first)."""
        (
            piece1_inner,
            piece1_outer,
            piece2_inner,
            piece2_outer,
        ) = self.create_two_piece_scenario()

        context = CutCode()
        context.extend([piece1_inner, piece1_outer, piece2_inner, piece2_outer])
        context._start_x, context._start_y = 0, 0

        # Run inner-first identification
        inner_first_ident(context, tolerance=0)

        # Test with grouped_inner=True (piece-based processing)
        result = short_travel_cutcode_optimized(
            context=context, complete_path=False, grouped_inner=True
        )

        result_cuts = list(result)
        piece1_positions, piece2_positions = self.analyze_cut_sequence(result_cuts)

        # Verify travel optimization: closer piece (2) should be processed before farther piece (1)
        self.assertTrue(piece2_positions, "Piece 2 should have cuts in the result")
        self.assertTrue(piece1_positions, "Piece 1 should have cuts in the result")

        piece2_start = min(piece2_positions)
        piece1_start = min(piece1_positions)

        self.assertLess(
            piece2_start,
            piece1_start,
            f"Piece 2 (closer) should be processed before Piece 1 (farther). "
            f"Piece 2 starts at position {piece2_start}, Piece 1 starts at position {piece1_start}",
        )

    def test_inner_first_within_pieces(self):
        """Test that inner-first constraints are maintained within each piece."""
        (
            piece1_inner,
            piece1_outer,
            piece2_inner,
            piece2_outer,
        ) = self.create_two_piece_scenario()

        context = CutCode()
        context.extend([piece1_inner, piece1_outer, piece2_inner, piece2_outer])
        context._start_x, context._start_y = 0, 0

        # Run inner-first identification
        inner_first_ident(context, tolerance=0)

        # Test with grouped_inner=True (piece-based processing)
        result = short_travel_cutcode_optimized(
            context=context, complete_path=False, grouped_inner=True
        )

        result_cuts = list(result)

        # Analyze inner/outer positions within each piece
        piece1_inner_positions = []
        piece1_outer_positions = []
        piece2_inner_positions = []
        piece2_outer_positions = []

        for i, cut in enumerate(result_cuts):
            start = (round(cut.start[0]), round(cut.start[1]))
            # Piece 1 inner
            if start in [(90, 90), (110, 90), (110, 110), (90, 110)]:
                piece1_inner_positions.append(i)
            # Piece 1 outer
            elif start in [(80, 80), (120, 80), (120, 120), (80, 120)]:
                piece1_outer_positions.append(i)
            # Piece 2 inner
            elif start in [(5, 5), (15, 5), (15, 15), (5, 15)]:
                piece2_inner_positions.append(i)
            # Piece 2 outer
            elif start in [(0, 0), (20, 0), (20, 20), (0, 20)]:
                piece2_outer_positions.append(i)

        # Check inner-first within piece 2
        if piece2_inner_positions and piece2_outer_positions:
            self.assertLess(
                max(piece2_inner_positions),
                min(piece2_outer_positions),
                "Inner cuts should come before outer cuts in Piece 2",
            )

        # Check inner-first within piece 1
        if piece1_inner_positions and piece1_outer_positions:
            self.assertLess(
                max(piece1_inner_positions),
                min(piece1_outer_positions),
                "Inner cuts should come before outer cuts in Piece 1",
            )

    def test_piece_identification_grouping(self):
        """Test that related inner/outer groups are correctly identified as pieces."""
        (
            piece1_inner,
            piece1_outer,
            piece2_inner,
            piece2_outer,
        ) = self.create_two_piece_scenario()

        context = CutCode()
        context.extend([piece1_inner, piece1_outer, piece2_inner, piece2_outer])
        context._start_x, context._start_y = 0, 0

        # Run inner-first identification
        inner_first_ident(context, tolerance=0)

        # Check that containment relationships were established
        inner_count = sum(1 for g in context if hasattr(g, "inside") and g.inside)
        outer_count = sum(1 for g in context if hasattr(g, "contains") and g.contains)

        self.assertEqual(inner_count, 2, "Should have 2 inner groups")
        self.assertEqual(outer_count, 2, "Should have 2 outer groups")

    def test_piece_based_vs_hierarchical_processing(self):
        """Test the difference between piece-based (grouped_inner=True) and hierarchical (grouped_inner=False) processing."""
        (
            piece1_inner,
            piece1_outer,
            piece2_inner,
            piece2_outer,
        ) = self.create_two_piece_scenario()

        context = CutCode()
        context.extend([piece1_inner, piece1_outer, piece2_inner, piece2_outer])
        context._start_x, context._start_y = 0, 0

        # Run inner-first identification
        inner_first_ident(context, tolerance=0)

        # Test hierarchical processing (grouped_inner=False)
        result_hierarchical = short_travel_cutcode_optimized(
            context=context, complete_path=False, grouped_inner=False
        )

        # Reset burns_done for second test
        for group in context:
            for cut in group.flat():
                cut.burns_done = 0

        # Test piece-based processing (grouped_inner=True)
        result_pieces = short_travel_cutcode_optimized(
            context=context, complete_path=False, grouped_inner=True
        )

        hierarchical_cuts = list(result_hierarchical)
        piece_cuts = list(result_pieces)

        # Both should produce the same number of cuts
        self.assertEqual(
            len(hierarchical_cuts),
            len(piece_cuts),
            "Both processing modes should produce the same number of cuts",
        )

        # Both should maintain inner-first constraints (tested differently)
        # Piece-based should optimize travel between pieces
        piece1_pos, piece2_pos = self.analyze_cut_sequence(piece_cuts)

        if piece1_pos and piece2_pos:
            # In piece-based mode, closer piece should come first
            self.assertLess(
                min(piece2_pos),
                min(piece1_pos),
                "Piece-based processing should process closer piece first",
            )

    def test_empty_and_edge_cases(self):
        """Test edge cases like empty cutcode and single groups."""
        # Test empty cutcode
        empty_context = CutCode()
        empty_context._start_x, empty_context._start_y = 0, 0

        result = short_travel_cutcode_optimized(
            context=empty_context, complete_path=False, grouped_inner=True
        )

        empty_cuts = list(result)
        self.assertEqual(len(empty_cuts), 0, "Empty cutcode should produce no cuts")

        # Test single group
        single_cuts = [
            LineCut((0, 0), (10, 0)),
            LineCut((10, 0), (10, 10)),
            LineCut((10, 10), (0, 10)),
            LineCut((0, 10), (0, 0)),
        ]

        single_group = CutGroup(parent=None, children=single_cuts, closed=True)
        for cut in single_cuts:
            cut.parent = single_group
            cut.passes = 1
            cut.burns_done = 0

        single_context = CutCode()
        single_context.append(single_group)
        single_context._start_x, single_context._start_y = 0, 0

        result = short_travel_cutcode_optimized(
            context=single_context, complete_path=False, grouped_inner=True
        )

        single_result = list(result)
        self.assertEqual(len(single_result), 4, "Single group should produce 4 cuts")

    def test_end_to_end_cutplan_integration(self):
        """Test the complete CutPlan pipeline with our optimization fixes."""
        (
            piece1_inner,
            piece1_outer,
            piece2_inner,
            piece2_outer,
        ) = self.create_two_piece_scenario()

        # Test the complete pipeline with inner-first priority
        context = MockContext(
            opt_travel=True, opt_inner_first=True, opt_inners_grouped=True
        )
        cutcode = CutCode()
        cutcode.extend([piece1_inner, piece1_outer, piece2_inner, piece2_outer])

        cutplan = CutPlan("test", context)
        cutplan.plan = [cutcode]

        # Test preopt selects correct optimization
        cutplan.preopt()
        command_names = [cmd.__name__ for cmd in cutplan.commands]

        self.assertIn(
            "optimize_cuts", command_names, "Should use inner-first optimization"
        )
        self.assertNotIn(
            "optimize_travel", command_names, "Should not use travel-only optimization"
        )
        self.assertNotIn(
            "basic_cutcode_sequencing", command_names, "Should not use basic sequencing"
        )

        # Execute the optimization
        cutplan.execute()

        # Verify cuts were processed
        total_cuts = sum(
            len(list(group.flat()))
            for group in cutplan.plan
            if isinstance(group, CutCode)
        )
        self.assertGreater(total_cuts, 0, "Should have processed cuts")


if __name__ == "__main__":
    unittest.main()
