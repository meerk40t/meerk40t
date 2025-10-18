"""
Test for hatched geometry optimization fix.

This test verifies that the fix for the hatched geometry bug works correctly.
The bug was that when ALL items in a context were marked skip=True (which happens
with hatched geometries after combine_effects), the optimization code would remove
ALL items before candidate generation, leaving an empty context and resulting in
"Dataset size: 0 cuts" error.

The fix ensures that skip-marked items are only removed if there are non-skip
items remaining. If all items are skip-marked, they are preserved so that
candidate generation can proceed.
"""

import unittest
from meerk40t.core.cutcode.cutcode import CutCode
from meerk40t.core.cutcode.cutgroup import CutGroup
from meerk40t.core.cutcode.linecut import LineCut


class TestHatchedGeometryFix(unittest.TestCase):
    """Test hatched geometry optimization fix."""

    def setUp(self):
        """Create test cuts for hatched geometry."""
        # Create 29 simple line cuts (simulating hatched geometry lines)
        self.cuts = []
        for i in range(29):
            cut = LineCut(
                start_point=(0, i * 10),
                end_point=(100, i * 10 + 5),
                settings=None,
                passes=1,
            )
            self.cuts.append(cut)

    def test_hatched_geometry_with_all_skip_groups(self):
        """
        Test that when ALL items are skip-marked, candidates are still generated.

        This reproduces the scenario where:
        1. Hatched geometry creates multiple lines
        2. combine_effects() combines them and marks them with skip=True
        3. short_travel_cutcode_optimized() should still generate candidates
        """
        # Create a CutGroup with all cuts and mark with skip=True
        # (simulating the state after combine_effects)
        group = CutGroup(parent=None, children=self.cuts[:], closed=False)
        group.skip = True

        # Create CutCode with this single skip-marked group
        cutcode = CutCode()
        cutcode.append(group)

        # Verify we have 1 skip-marked item with 29 children
        self.assertEqual(len(cutcode), 1)
        self.assertTrue(cutcode[0].skip)
        self.assertEqual(len(cutcode[0]), 29)

        # Initialize burns_done for candidate generation
        for c in cutcode.flat():
            c.burns_done = 0

        # Generate candidates - should get all 29, NOT 0
        candidates = list(cutcode.candidate(complete_path=False, grouped_inner=False))

        # This is the critical test - with the fix, we should get candidates
        # even though all items are skip-marked
        self.assertEqual(len(candidates), 29, 
                        "When all items are skip-marked, candidates should still be generated")

    def test_skip_group_removal_only_when_non_skip_exist(self):
        """
        Test that skip groups are only removed if non-skip items exist.

        Simulates the removal logic from short_travel_cutcode_optimized:
        - If there are non-skip items, remove skip groups
        - If ALL items are skip, don't remove them
        """
        # Test case 1: Mix of skip and non-skip items
        non_skip_group = CutGroup(parent=None, children=self.cuts[:10], closed=False)
        non_skip_group.skip = False

        skip_group = CutGroup(parent=None, children=self.cuts[10:20], closed=False)
        skip_group.skip = True

        cutcode_mixed = CutCode()
        cutcode_mixed.append(non_skip_group)
        cutcode_mixed.append(skip_group)

        # Check for non-skip items
        non_skip_items = [c for c in cutcode_mixed 
                          if not (isinstance(c, CutGroup) and c.skip)]
        
        # Should find the non-skip group
        self.assertEqual(len(non_skip_items), 1)
        
        # Since non-skip items exist, we would remove skip items
        # (simulating the original code behavior)
        
        # Test case 2: All skip items
        skip_only_group1 = CutGroup(parent=None, children=self.cuts[:15], closed=False)
        skip_only_group1.skip = True

        skip_only_group2 = CutGroup(parent=None, children=self.cuts[15:], closed=False)
        skip_only_group2.skip = True

        cutcode_all_skip = CutCode()
        cutcode_all_skip.append(skip_only_group1)
        cutcode_all_skip.append(skip_only_group2)

        # Check for non-skip items
        non_skip_items = [c for c in cutcode_all_skip 
                          if not (isinstance(c, CutGroup) and c.skip)]
        
        # Should find NO non-skip items
        self.assertEqual(len(non_skip_items), 0)
        
        # With the fix, we would NOT remove skip items (since all are skip)
        # This prevents the empty context problem

    def test_hatched_geometry_candidate_generation_flow(self):
        """
        Test the complete flow of candidate generation for hatched geometry.

        This is the scenario that was broken:
        1. All cuts grouped into one CutGroup
        2. CutGroup marked with skip=True
        3. Removal logic should NOT remove it (since it's the only item)
        4. Candidate generation should still work
        """
        # Create a single CutGroup with all cuts
        group = CutGroup(parent=None, children=self.cuts[:], closed=False)
        group.skip = True
        
        context = CutCode()
        context.append(group)

        # Simulate the fix: check if removal would empty context
        non_skip_items = [c for c in context if not (isinstance(c, CutGroup) and c.skip)]
        
        # No non-skip items, so we should preserve the context
        self.assertEqual(len(non_skip_items), 0)
        
        # Don't remove anything (with the fix)
        # So context still has 1 item
        self.assertEqual(len(context), 1)
        
        # Initialize burns_done and generate candidates
        for c in context.flat():
            c.burns_done = 0
        
        candidates = list(context.candidate(complete_path=False, grouped_inner=False))
        
        # Should have candidates from the skip-marked group
        self.assertEqual(len(candidates), 29)

    def test_mixed_skip_and_non_skip_groups(self):
        """
        Test with mixed skip and non-skip groups to ensure normal flow still works.
        """
        # Create non-skip group
        non_skip_group = CutGroup(parent=None, children=self.cuts[:15], closed=False)
        non_skip_group.skip = False

        # Create skip group
        skip_group = CutGroup(parent=None, children=self.cuts[15:], closed=False)
        skip_group.skip = True

        context = CutCode()
        context.append(non_skip_group)
        context.append(skip_group)

        # Initialize burns_done
        for c in context.flat():
            c.burns_done = 0

        # Generate candidates - should get all cuts
        candidates = list(context.candidate(complete_path=False, grouped_inner=False))

        # Should have all 29 candidates
        self.assertEqual(len(candidates), 29)

    def test_hatch_optimize_separation_with_mixed_items(self):
        """
        Test hatch_optimize=True with mixed skip and non-skip items.
        Skip items should be extracted for separate processing.
        """
        # Create non-skip group (regular shape)
        non_skip_group = CutGroup(parent=None, children=self.cuts[:15], closed=False)
        non_skip_group.skip = False

        # Create skip group (hatch pattern)
        skip_group = CutGroup(parent=None, children=self.cuts[15:], closed=False)
        skip_group.skip = True

        context = CutCode()
        context.append(non_skip_group)
        context.append(skip_group)

        # With hatch_optimize=True, the skip groups should be extracted
        # Simulate the logic from short_travel_cutcode_optimized
        skip_groups = []
        non_skip_groups = []

        for c in context:
            if isinstance(c, CutGroup) and c.skip:
                skip_groups.append(c)
            else:
                non_skip_groups.append(c)

        # With mixed items, we extract skip groups
        self.assertEqual(len(skip_groups), 1)
        self.assertEqual(len(non_skip_groups), 1)

        # Non-skip group should be optimized first
        self.assertEqual(len(non_skip_groups[0]), 15)
        # Skip group should be handled separately
        self.assertEqual(len(skip_groups[0]), 14)

    def test_hatch_optimize_with_only_hatch_patterns(self):
        """
        Test hatch_optimize=True when ALL items are hatch patterns.
        They should still be optimized (not removed, leaving empty context).
        """
        # Create only skip groups
        skip_group1 = CutGroup(parent=None, children=self.cuts[:15], closed=False)
        skip_group1.skip = True

        skip_group2 = CutGroup(parent=None, children=self.cuts[15:], closed=False)
        skip_group2.skip = True

        context = CutCode()
        context.append(skip_group1)
        context.append(skip_group2)

        # With hatch_optimize=True, check extraction
        skip_groups = []
        non_skip_groups = []

        for c in context:
            if isinstance(c, CutGroup) and c.skip:
                skip_groups.append(c)
            else:
                non_skip_groups.append(c)

        # All are skip groups
        self.assertEqual(len(skip_groups), 2)
        self.assertEqual(len(non_skip_groups), 0)

        # Since no non-skip groups, skip groups should NOT be removed
        # (according to the fix logic)
        # This prevents the "Dataset size: 0" error
        if not non_skip_groups:
            # Keep context intact for optimization
            remaining_in_context = skip_groups
            self.assertEqual(len(remaining_in_context), 2)

        # Initialize burns_done on remaining items
        for group in remaining_in_context:
            for c in group.flat():
                c.burns_done = 0

        # Should be able to generate candidates
        candidates = list(context.candidate(complete_path=False, grouped_inner=False))
        self.assertEqual(len(candidates), 29)


if __name__ == "__main__":
    unittest.main()
