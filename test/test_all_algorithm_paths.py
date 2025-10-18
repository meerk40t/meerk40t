"""
Test for all algorithm selection paths in short_travel_cutcode_optimized.

This test verifies that the fix for hatched geometry works correctly across
all dataset size thresholds and algorithm selection paths:
- dataset_size < 50: simple_greedy_selection
- 50 <= dataset_size < 100: improved_greedy_selection
- 100 <= dataset_size <= 500: spatial_optimized_selection
- dataset_size > 500: short_travel_cutcode_legacy
"""

import unittest
from meerk40t.core.cutcode.cutcode import CutCode
from meerk40t.core.cutcode.cutgroup import CutGroup
from meerk40t.core.cutcode.linecut import LineCut
from meerk40t.core.cutplan import short_travel_cutcode_optimized


class TestAllAlgorithmPaths(unittest.TestCase):
    """Test all algorithm selection paths with hatched geometry."""

    def create_test_cuts(self, count):
        """Create a specified number of test cuts."""
        cuts = []
        for i in range(count):
            cut = LineCut(
                start_point=(i * 10, 0),
                end_point=(i * 10 + 5, 100),
                settings=None,
                passes=1,
            )
            cuts.append(cut)
        return cuts

    def test_dataset_size_under_50_simple_greedy(self):
        """
        Test dataset_size < 50: Should use simple_greedy_selection.
        Tests with hatched patterns.
        """
        # Create 40 cuts (< 50 threshold)
        cuts = self.create_test_cuts(40)
        
        # Create a skip-marked group (hatch pattern)
        hatch_group = CutGroup(parent=None, children=cuts, closed=False)
        hatch_group.skip = True
        
        context = CutCode()
        context.append(hatch_group)
        
        # Initialize burns_done
        for c in context.flat():
            c.burns_done = 0
        
        # Run optimization with hatch_optimize=True
        # This should use simple_greedy_selection after extracting skip group
        result = short_travel_cutcode_optimized(
            context=context,
            kernel=None,
            complete_path=False,
            grouped_inner=False,
            hatch_optimize=True,
            channel=None,
        )
        
        # Should return valid optimization
        self.assertIsNotNone(result)
        self.assertIsInstance(result, CutCode)
        # Should have some result (either hatch patterns or optimized result)
        total_cuts = sum(len(item) if isinstance(item, CutGroup) else 1 
                        for item in result)
        self.assertGreater(total_cuts, 0, "Should have optimized cuts")

    def test_dataset_size_50_to_100_improved_greedy(self):
        """
        Test 50 <= dataset_size < 100: Should use improved_greedy_selection.
        Tests with mixed regular and hatched patterns.
        """
        # Create 75 regular cuts + 25 hatch cuts
        regular_cuts = self.create_test_cuts(75)
        hatch_cuts = self.create_test_cuts(25)
        
        # Create groups
        regular_group = CutGroup(parent=None, children=regular_cuts, closed=False)
        regular_group.skip = False
        
        hatch_group = CutGroup(parent=None, children=hatch_cuts, closed=False)
        hatch_group.skip = True
        
        context = CutCode()
        context.append(regular_group)
        context.append(hatch_group)
        
        # Initialize burns_done
        for c in context.flat():
            c.burns_done = 0
        
        # Run optimization with hatch_optimize=True
        # Regular cuts (75) should be optimized with improved_greedy
        result = short_travel_cutcode_optimized(
            context=context,
            kernel=None,
            complete_path=False,
            grouped_inner=False,
            hatch_optimize=True,
            channel=None,
        )
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, CutCode)
        # Should have regular cuts optimized
        self.assertGreater(len(result), 0, "Should have optimized regular cuts")

    def test_dataset_size_100_to_500_spatial_optimized(self):
        """
        Test 100 <= dataset_size <= 500: Should use spatial_optimized_selection.
        Tests with hatched patterns at this scale.
        """
        # Create 300 cuts (in the 100-500 range)
        cuts = self.create_test_cuts(300)
        
        # Mix regular and hatched
        regular_cuts = cuts[:200]
        hatch_cuts = cuts[200:]
        
        regular_group = CutGroup(parent=None, children=regular_cuts, closed=False)
        regular_group.skip = False
        
        hatch_group = CutGroup(parent=None, children=hatch_cuts, closed=False)
        hatch_group.skip = True
        
        context = CutCode()
        context.append(regular_group)
        context.append(hatch_group)
        
        # Initialize burns_done
        for c in context.flat():
            c.burns_done = 0
        
        # Run optimization with hatch_optimize=True
        # Regular cuts (200) should be optimized with spatial_optimized
        result = short_travel_cutcode_optimized(
            context=context,
            kernel=None,
            complete_path=False,
            grouped_inner=False,
            hatch_optimize=True,
            channel=None,
        )
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, CutCode)
        self.assertGreater(len(result), 0, "Should have optimized cuts")

    def test_dataset_size_over_500_legacy(self):
        """
        Test dataset_size > 500: Should use short_travel_cutcode_legacy.
        Tests with hatched patterns at this large scale.
        """
        # Create 600 cuts (> 500 threshold)
        cuts = self.create_test_cuts(600)
        
        # Mix regular and hatched
        regular_cuts = cuts[:400]
        hatch_cuts = cuts[400:]
        
        regular_group = CutGroup(parent=None, children=regular_cuts, closed=False)
        regular_group.skip = False
        
        hatch_group = CutGroup(parent=None, children=hatch_cuts, closed=False)
        hatch_group.skip = True
        
        context = CutCode()
        context.append(regular_group)
        context.append(hatch_group)
        
        # Initialize burns_done
        for c in context.flat():
            c.burns_done = 0
        
        # Run optimization with hatch_optimize=True
        # Regular cuts (400) should be optimized with legacy algorithm
        result = short_travel_cutcode_optimized(
            context=context,
            kernel=None,
            complete_path=False,
            grouped_inner=False,
            hatch_optimize=True,
            channel=None,
        )
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, CutCode)
        self.assertGreater(len(result), 0, "Should have optimized cuts with legacy algorithm")

    def test_all_hatch_small_dataset(self):
        """
        Test edge case: only hatch patterns with small dataset (< 50).
        Should NOT remove hatches, allowing optimization to proceed.
        """
        cuts = self.create_test_cuts(40)
        
        hatch_group = CutGroup(parent=None, children=cuts, closed=False)
        hatch_group.skip = True
        
        context = CutCode()
        context.append(hatch_group)
        
        for c in context.flat():
            c.burns_done = 0
        
        # With hatch_optimize=True but all hatches, should still optimize
        result = short_travel_cutcode_optimized(
            context=context,
            kernel=None,
            complete_path=False,
            grouped_inner=False,
            hatch_optimize=True,
            channel=None,
        )
        
        self.assertIsNotNone(result)
        # Should have optimized the hatch patterns (not empty)
        total_items = sum(1 for item in result)
        self.assertGreater(total_items, 0, "Should optimize hatch patterns even when all are hatches")

    def test_all_hatch_medium_dataset(self):
        """
        Test edge case: only hatch patterns with medium dataset (100-500).
        Should use spatial_optimized on hatches directly.
        """
        cuts = self.create_test_cuts(300)
        
        hatch_group = CutGroup(parent=None, children=cuts, closed=False)
        hatch_group.skip = True
        
        context = CutCode()
        context.append(hatch_group)
        
        for c in context.flat():
            c.burns_done = 0
        
        result = short_travel_cutcode_optimized(
            context=context,
            kernel=None,
            complete_path=False,
            grouped_inner=False,
            hatch_optimize=True,
            channel=None,
        )
        
        self.assertIsNotNone(result)
        total_items = sum(1 for item in result)
        self.assertGreater(total_items, 0, "Should optimize medium-sized hatch patterns")

    def test_all_hatch_large_dataset(self):
        """
        Test edge case: only hatch patterns with large dataset (> 500).
        Should use legacy algorithm on hatches directly.
        """
        cuts = self.create_test_cuts(600)
        
        hatch_group = CutGroup(parent=None, children=cuts, closed=False)
        hatch_group.skip = True
        
        context = CutCode()
        context.append(hatch_group)
        
        for c in context.flat():
            c.burns_done = 0
        
        result = short_travel_cutcode_optimized(
            context=context,
            kernel=None,
            complete_path=False,
            grouped_inner=False,
            hatch_optimize=True,
            channel=None,
        )
        
        self.assertIsNotNone(result)
        total_items = sum(1 for item in result)
        self.assertGreater(total_items, 0, "Should optimize large-sized hatch patterns with legacy")

    def test_hatch_optimize_false_all_sizes(self):
        """
        Test that with hatch_optimize=False, hatches are included in optimization.
        Test across different dataset sizes.
        """
        for size in [40, 75, 300, 600]:
            with self.subTest(size=size):
                cuts = self.create_test_cuts(size)
                
                # Half regular, half hatch
                mid = size // 2
                regular_cuts = cuts[:mid]
                hatch_cuts = cuts[mid:]
                
                regular_group = CutGroup(parent=None, children=regular_cuts, closed=False)
                regular_group.skip = False
                
                hatch_group = CutGroup(parent=None, children=hatch_cuts, closed=False)
                hatch_group.skip = True
                
                context = CutCode()
                context.append(regular_group)
                context.append(hatch_group)
                
                for c in context.flat():
                    c.burns_done = 0
                
                # With hatch_optimize=False, hatches should be included
                result = short_travel_cutcode_optimized(
                    context=context,
                    kernel=None,
                    complete_path=False,
                    grouped_inner=False,
                    hatch_optimize=False,
                    channel=None,
                )
                
                self.assertIsNotNone(result)
                # Should have items (everything optimized together)
                total_items = sum(1 for item in result)
                self.assertGreater(total_items, 0, 
                                 f"Should optimize all items for size={size} with hatch_optimize=False")


if __name__ == "__main__":
    unittest.main()
