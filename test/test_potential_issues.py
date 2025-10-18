"""
Test for potential issues with:
a) Containment hierarchy when skip groups are extracted
b) Algorithm selection based on total size vs filtered size
"""

import unittest
from meerk40t.core.cutcode.cutcode import CutCode
from meerk40t.core.cutcode.cutgroup import CutGroup
from meerk40t.core.cutcode.linecut import LineCut


class TestContainmentHierarchy(unittest.TestCase):
    """Test containment hierarchy preservation when extracting skip groups."""

    def test_hierarchy_with_skip_marked_inner_group(self):
        """
        Test scenario: outer group contains inner groups, some marked skip.
        Issue: If we remove skip-marked inner groups, the outer group's
        .contains reference becomes invalid.
        """
        # Create inner groups
        inner_cuts_1 = [LineCut((0, 0), (10, 10), settings=None, passes=1) for _ in range(5)]
        inner_group_1 = CutGroup(parent=None, children=inner_cuts_1, closed=False)
        inner_group_1.skip = False
        
        inner_cuts_2 = [LineCut((20, 20), (30, 30), settings=None, passes=1) for _ in range(5)]
        inner_group_2 = CutGroup(parent=None, children=inner_cuts_2, closed=False)
        inner_group_2.skip = True  # This is hatched
        
        # Create outer group containing both inner groups
        outer_group = CutGroup(parent=None, children=[], closed=False)
        outer_group.contains = [inner_group_1, inner_group_2]
        outer_group.skip = False
        
        # Outer group needs to process inner groups first
        inner_group_1.inside = outer_group
        inner_group_2.inside = outer_group
        
        context = CutCode()
        context.append(inner_group_1)
        context.append(inner_group_2)
        context.append(outer_group)
        
        print("\n=== Before skip group extraction ===")
        print(f"Context items: {len(context)}")
        for i, item in enumerate(context):
            skip_status = "SKIP" if item.skip else "REGULAR"
            has_contains = hasattr(item, 'contains') and item.contains is not None
            contains_ref = len(item.contains) if has_contains else 0
            print(f"  [{i}] {skip_status} contains={contains_ref}")
        
        # Simulate the extraction logic
        skip_groups = [c for c in context if isinstance(c, CutGroup) and c.skip]
        non_skip_groups = [c for c in context if not (isinstance(c, CutGroup) and c.skip)]
        
        print(f"\nSkip groups: {len(skip_groups)}")
        print(f"Non-skip groups: {len(non_skip_groups)}")
        
        if non_skip_groups:
            # This is what our fix does
            context.clear()
            context.extend(non_skip_groups)
            
            print("\n=== After skip group extraction ===")
            print(f"Context items: {len(context)}")
            
            # Check if containment hierarchy is broken
            for item in context:
                if hasattr(item, 'contains') and item.contains is not None:
                    print(f"Group has contains: {len(item.contains)} references")
                    for ref_idx, ref in enumerate(item.contains):
                        is_in_context = ref in context
                        print(f"  Reference {ref_idx}: {'IN context' if is_in_context else 'NOT IN context (BROKEN!)'}")
        
        # ISSUE: The outer group still contains references to the removed skip groups!
        # This could cause problems in hierarchy-aware algorithms


class TestAlgorithmSelectionSize(unittest.TestCase):
    """Test if algorithm selection should use total size or filtered size."""

    def test_algorithm_selection_with_mixed_items(self):
        """
        Test: Should algorithm selection be based on:
        a) Total size (900 = 50 regular + 850 hatches) → uses legacy
        b) Filtered size (50 = only regular) → uses spatial or greedy
        
        Current implementation uses total size BEFORE extraction.
        Is this correct?
        """
        print("\n=== Algorithm Selection Size Question ===")
        
        # Create 50 regular cuts
        regular_cuts = [
            LineCut((i*10, 0), (i*10+5, 100), settings=None, passes=1) 
            for i in range(50)
        ]
        regular_group = CutGroup(parent=None, children=regular_cuts, closed=False)
        regular_group.skip = False
        
        # Create 850 hatch cuts
        hatch_cuts = [
            LineCut((i*10, 200), (i*10+5, 300), settings=None, passes=1) 
            for i in range(850)
        ]
        hatch_group = CutGroup(parent=None, children=hatch_cuts, closed=False)
        hatch_group.skip = True
        
        context = CutCode()
        context.append(regular_group)
        context.append(hatch_group)
        
        # Initialize
        for c in context.flat():
            c.burns_done = 0
        
        # Get candidates (this is what determines dataset_size)
        all_candidates = list(context.candidate(complete_path=False, grouped_inner=False))
        dataset_size = len(all_candidates)
        
        print(f"\nTotal items in context: {sum(len(item) if isinstance(item, CutGroup) else 1 for item in context)}")
        print(f"Candidates found: {dataset_size}")
        print("Algorithm selected: ", end="")
        
        if dataset_size < 50:
            print("simple_greedy (< 50)")
        elif dataset_size < 100:
            print("improved_greedy (50-100)")
        elif dataset_size <= 500:
            print("spatial_optimized (100-500)")
        else:
            print("legacy (> 500)")
        
        print(f"\nAfter skip group extraction (if hatch_optimize=True):")
        
        # Simulate extraction
        non_skip_groups = [c for c in context if not (isinstance(c, CutGroup) and c.skip)]
        
        if non_skip_groups:
            filtered_context = CutCode()
            filtered_context.extend(non_skip_groups)
            
            # Would get different candidates
            filtered_candidates = list(filtered_context.candidate(complete_path=False, grouped_inner=False))
            filtered_size = len(filtered_candidates)
            
            print(f"Filtered items: {sum(len(item) if isinstance(item, CutGroup) else 1 for item in filtered_context)}")
            print(f"Filtered candidates: {filtered_size}")
            print("Algorithm would select: ", end="")
            
            if filtered_size < 50:
                print("simple_greedy (< 50)")
            elif filtered_size < 100:
                print("improved_greedy (50-100)")
            elif filtered_size <= 500:
                print("spatial_optimized (100-500)")
            else:
                print("legacy (> 500)")
            
            print("\nISSUE: Algorithm selection uses TOTAL (900) not FILTERED (50)")
            print("   This means we use legacy algorithm for 50 regular cuts!")
            print("   Legacy is designed for LARGE datasets and may be overkill.")


if __name__ == "__main__":
    unittest.main()
