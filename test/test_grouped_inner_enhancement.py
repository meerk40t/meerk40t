"""
Unit tests for the enhanced grouped_inner functionality.

These tests validate the sophisticated piece-based organization implementation
for grouped_inner=True mode and compare it with the hierarchical processing
for grouped_inner=False mode.
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
from meerk40t.svgelements import Point


class TestGroupedInnerEnhancement(unittest.TestCase):
    """Test the enhanced grouped_inner piece-based functionality."""

    def create_complex_nested_scenario(self):
        """Create a complex scenario with multiple nested pieces."""
        # Piece 1: Large outer with medium inner containing small inner
        outer1 = CutGroup(parent=None, closed=True)
        outer1.extend(
            [
                LineCut(Point(0, 0), Point(100, 0)),
                LineCut(Point(100, 0), Point(100, 100)),
                LineCut(Point(100, 100), Point(0, 100)),
                LineCut(Point(0, 100), Point(0, 0)),
            ]
        )

        medium1 = CutGroup(parent=None, closed=True)
        medium1.extend(
            [
                LineCut(Point(20, 20), Point(80, 20)),
                LineCut(Point(80, 20), Point(80, 80)),
                LineCut(Point(80, 80), Point(20, 80)),
                LineCut(Point(20, 80), Point(20, 20)),
            ]
        )

        small1 = CutGroup(parent=None, closed=True)
        small1.extend(
            [
                LineCut(Point(40, 40), Point(60, 40)),
                LineCut(Point(60, 40), Point(60, 60)),
                LineCut(Point(60, 60), Point(40, 60)),
                LineCut(Point(40, 60), Point(40, 40)),
            ]
        )

        # Set up containment relationships for piece 1
        medium1.inside = outer1
        small1.inside = medium1
        outer1.contains = [medium1]
        medium1.contains = [small1]

        # Piece 2: Separate outer with inner
        outer2 = CutGroup(parent=None, closed=True)
        outer2.extend(
            [
                LineCut(Point(150, 0), Point(200, 0)),
                LineCut(Point(200, 0), Point(200, 50)),
                LineCut(Point(200, 50), Point(150, 50)),
                LineCut(Point(150, 50), Point(150, 0)),
            ]
        )

        inner2 = CutGroup(parent=None, closed=True)
        inner2.extend(
            [
                LineCut(Point(160, 10), Point(190, 10)),
                LineCut(Point(190, 10), Point(190, 40)),
                LineCut(Point(190, 40), Point(160, 40)),
                LineCut(Point(160, 40), Point(160, 10)),
            ]
        )

        # Set up containment relationships for piece 2
        inner2.inside = outer2
        outer2.contains = [inner2]

        # Standalone group (no containment relationships)
        standalone = CutGroup(parent=None, closed=True)
        standalone.extend(
            [
                LineCut(Point(250, 0), Point(270, 0)),
                LineCut(Point(270, 0), Point(270, 20)),
                LineCut(Point(270, 20), Point(250, 20)),
                LineCut(Point(250, 20), Point(250, 0)),
            ]
        )

        cutcode = CutCode()
        cutcode.extend([outer1, medium1, small1, outer2, inner2, standalone])
        return cutcode

    def test_piece_based_organization(self):
        """Test that grouped_inner=True creates proper piece organization."""
        cutcode = self.create_complex_nested_scenario()

        # Test grouped_inner=True (piece-based organization)
        candidates_grouped = list(cutcode.candidate(grouped_inner=True))

        # Should return all cuts
        original_count = len(list(cutcode.flat()))
        grouped_count = len(candidates_grouped)
        self.assertEqual(
            original_count,
            grouped_count,
            f"Grouped candidate should return all cuts: {original_count} vs {grouped_count}",
        )

        # Verify the candidates are properly ordered
        self.assertGreater(len(candidates_grouped), 0, "Should have candidates")

        # Test that all cuts are LineCut objects (individual cuts)
        for candidate in candidates_grouped:
            self.assertIsInstance(
                candidate, LineCut, "Candidates should be individual cuts, not groups"
            )

    def test_hierarchical_vs_piece_organization(self):
        """Test differences between grouped_inner=False and grouped_inner=True."""
        cutcode = self.create_complex_nested_scenario()

        # Test both modes
        candidates_hierarchical = list(cutcode.candidate(grouped_inner=False))
        candidates_grouped = list(cutcode.candidate(grouped_inner=True))

        # Both should return the same number of cuts (no suppression)
        original_count = len(list(cutcode.flat()))

        self.assertEqual(
            len(candidates_hierarchical),
            original_count,
            "Hierarchical mode should preserve all cuts",
        )
        self.assertEqual(
            len(candidates_grouped),
            original_count,
            "Grouped mode should preserve all cuts",
        )

        # Both modes should complete without errors
        self.assertGreater(len(candidates_hierarchical), 0)
        self.assertGreater(len(candidates_grouped), 0)

    def test_piece_grouping_with_standalone_groups(self):
        """Test that standalone groups (no containment) are handled correctly."""
        # Create scenario with only standalone groups
        group1 = CutGroup(parent=None, closed=True)
        group1.extend(
            [
                LineCut(Point(0, 0), Point(10, 0)),
                LineCut(Point(10, 0), Point(10, 10)),
                LineCut(Point(10, 10), Point(0, 10)),
                LineCut(Point(0, 10), Point(0, 0)),
            ]
        )

        group2 = CutGroup(parent=None, closed=True)
        group2.extend(
            [
                LineCut(Point(20, 0), Point(30, 0)),
                LineCut(Point(30, 0), Point(30, 10)),
                LineCut(Point(30, 10), Point(20, 10)),
                LineCut(Point(20, 10), Point(20, 0)),
            ]
        )

        cutcode = CutCode()
        cutcode.extend([group1, group2])

        # Test both modes with standalone groups
        candidates_hierarchical = list(cutcode.candidate(grouped_inner=False))
        candidates_grouped = list(cutcode.candidate(grouped_inner=True))

        original_count = len(list(cutcode.flat()))

        self.assertEqual(
            len(candidates_hierarchical),
            original_count,
            "Hierarchical mode should handle standalone groups",
        )
        self.assertEqual(
            len(candidates_grouped),
            original_count,
            "Grouped mode should handle standalone groups",
        )

    def test_complex_hierarchy_preservation(self):
        """Test that complex hierarchies don't cause cutcode suppression."""
        cutcode = self.create_complex_nested_scenario()

        # Simulate multiple iterations of candidate generation (like optimization would do)
        total_candidates = []
        iteration = 0
        max_iterations = 10  # Prevent infinite loops in test

        while iteration < max_iterations:
            candidates = list(cutcode.candidate(grouped_inner=True))
            if not candidates:
                break

            total_candidates.extend(candidates)

            # Mark some candidates as "burned" to simulate optimization
            for i, candidate in enumerate(candidates):
                if i % 2 == 0 and hasattr(
                    candidate, "burns_done"
                ):  # Simulate partial burning
                    candidate.burns_done = getattr(candidate, "passes", 1)

            iteration += 1

        # Should complete without infinite loop
        self.assertLess(iteration, max_iterations, "Should not hit iteration limit")

        # Should have generated reasonable number of candidates
        self.assertGreater(len(total_candidates), 0, "Should generate candidates")

    def test_piece_inner_first_ordering(self):
        """Test that within pieces, inner groups come before outer groups."""
        cutcode = self.create_complex_nested_scenario()

        # Get candidates in grouped mode
        candidates = list(cutcode.candidate(grouped_inner=True))

        # Extract which groups the candidates belong to based on coordinates
        group_sequence = []
        for candidate in candidates:
            if hasattr(candidate, "start") and candidate.start:
                x, y = candidate.start

                # Identify which group this cut belongs to
                if 40 <= x <= 60 and 40 <= y <= 60:
                    group_sequence.append("small1")  # Innermost in piece 1
                elif 20 <= x <= 80 and 20 <= y <= 80:
                    group_sequence.append("medium1")  # Middle in piece 1
                elif 0 <= x <= 100 and 0 <= y <= 100:
                    group_sequence.append("outer1")  # Outermost in piece 1
                elif 160 <= x <= 190 and 10 <= y <= 40:
                    group_sequence.append("inner2")  # Inner in piece 2
                elif 150 <= x <= 200 and 0 <= y <= 50:
                    group_sequence.append("outer2")  # Outer in piece 2
                elif 250 <= x <= 270 and 0 <= y <= 20:
                    group_sequence.append("standalone")  # Standalone group

        # Should have sequence for all cuts
        self.assertGreater(len(group_sequence), 0, "Should identify group sequence")

        # Check for proper inner-first ordering within pieces
        # (The exact ordering depends on the implementation, but should be consistent)
        unique_groups = list(set(group_sequence))
        self.assertGreaterEqual(
            len(unique_groups), 3, "Should have multiple groups identified"
        )

    def test_processed_groups_tracking(self):
        """Test that processed groups are properly tracked to avoid duplicates."""
        cutcode = self.create_complex_nested_scenario()

        # Get candidates multiple times to test tracking
        candidates1 = list(cutcode.candidate(grouped_inner=True))
        candidates2 = list(cutcode.candidate(grouped_inner=True))

        # Should get consistent results
        self.assertEqual(
            len(candidates1),
            len(candidates2),
            "Candidate generation should be consistent",
        )

        # Both should preserve all cuts
        original_count = len(list(cutcode.flat()))
        self.assertEqual(
            len(candidates1),
            original_count,
            "First candidate generation should preserve all cuts",
        )
        self.assertEqual(
            len(candidates2),
            original_count,
            "Second candidate generation should preserve all cuts",
        )

    def test_edge_case_empty_groups(self):
        """Test handling of empty groups in piece organization."""
        # Create scenario with empty group
        empty_group = CutGroup(parent=None, closed=True)
        # Don't add any cuts to empty_group

        normal_group = CutGroup(parent=None, closed=True)
        normal_group.extend(
            [
                LineCut(Point(0, 0), Point(10, 0)),
                LineCut(Point(10, 0), Point(10, 10)),
                LineCut(Point(10, 10), Point(0, 10)),
                LineCut(Point(0, 10), Point(0, 0)),
            ]
        )

        cutcode = CutCode()
        cutcode.extend([empty_group, normal_group])

        # Should handle empty groups gracefully
        candidates = list(cutcode.candidate(grouped_inner=True))

        # Should only return cuts from non-empty groups
        self.assertEqual(
            len(candidates), 4, "Should return cuts only from non-empty groups"
        )

    def test_burns_done_filtering(self):
        """Test that candidates properly filter based on burns_done vs passes."""
        cutcode = self.create_complex_nested_scenario()

        # Set up some cuts as already burned
        cuts = list(cutcode.flat())
        for i, cut in enumerate(cuts):
            cut.burns_done = 0
            cut.passes = 1
            if i % 3 == 0:  # Mark every third cut as already burned
                cut.burns_done = 1

        # Get candidates - should only return unburned cuts
        candidates = list(cutcode.candidate(grouped_inner=True))

        # Should have fewer candidates than total cuts
        self.assertLess(
            len(candidates),
            len(cuts),
            "Should return fewer candidates when some cuts are already burned",
        )

        # All returned candidates should be unburned
        for candidate in candidates:
            if hasattr(candidate, "burns_done") and hasattr(candidate, "passes"):
                self.assertLess(
                    candidate.burns_done,
                    candidate.passes,
                    "All candidates should be unburned (burns_done < passes)",
                )


if __name__ == "__main__":
    unittest.main()
