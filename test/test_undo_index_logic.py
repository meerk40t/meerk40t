"""
Test undo index logic in various scenarios to ensure correctness.
"""
import unittest
from test.bootstrap import bootstrap
from meerk40t.core.undos import Undo


class TestUndoIndexLogic(unittest.TestCase):
    """Test the undo/redo index management."""

    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements
        self.undo = self.elements.undo
        # self.undo.debug_active = True  # Uncomment for verbose debug output

    def tearDown(self):
        self.kernel.shutdown()

    def test_initial_state(self):
        """Test initial state after kernel boot."""
        print("\n=== TEST: Initial State ===")
        print(f"Stack: {[str(s) for s in self.undo._undo_stack]}")
        print(f"Index: {self.undo._undo_index}, Length: {len(self.undo._undo_stack)}")
        # After init, we should have one or two states depending on validate() calls
        # The stack starts with "init" mark
        self.assertGreaterEqual(len(self.undo._undo_stack), 1, "Should have at least 1 state after init")
        self.assertGreaterEqual(self.undo._undo_index, 0, "Index should be >= 0")
        
        # At initial state with just "init", there should be no undo available
        # (because undo requires _undo_index > 0)
        if self.undo._undo_index == 0:
            self.assertFalse(self.undo.has_undo(), "Should not have undo at init index 0")

    def test_mark_sequence(self):
        """Test marking multiple states."""
        print("\n=== TEST: Mark Sequence ===")
        # Record the initial state
        initial_index = self.undo._undo_index
        initial_stack_len = len(self.undo._undo_stack)
        print(f"Initial: index={initial_index}, stack_len={initial_stack_len}")
        
        self.undo.mark("change1")
        print(f"After mark1: index={self.undo._undo_index}, stack_len={len(self.undo._undo_stack)}")
        self.assertEqual(self.undo._undo_index, initial_index + 1, f"Index should be {initial_index + 1} after first mark")
        self.assertEqual(len(self.undo._undo_stack), initial_stack_len + 1, f"Should have {initial_stack_len + 1} states")
        
        self.undo.mark("change2")
        print(f"After mark2: index={self.undo._undo_index}, stack_len={len(self.undo._undo_stack)}")
        self.assertEqual(self.undo._undo_index, initial_index + 2, f"Index should be {initial_index + 2} after second mark")
        self.assertEqual(len(self.undo._undo_stack), initial_stack_len + 2, f"Should have {initial_stack_len + 2} states")
        
        self.undo.mark("change3")
        print(f"After mark3: index={self.undo._undo_index}, stack_len={len(self.undo._undo_stack)}")
        self.assertEqual(self.undo._undo_index, initial_index + 3, f"Index should be {initial_index + 3} after third mark")
        self.assertEqual(len(self.undo._undo_stack), initial_stack_len + 3, f"Should have {initial_stack_len + 3} states")

    def test_undo_sequence(self):
        """Test undoing multiple times."""
        print("\n=== TEST: Undo Sequence ===")
        initial_index = self.undo._undo_index
        
        self.undo.mark("change1")
        self.undo.mark("change2")
        self.undo.mark("change3")
        current_index = self.undo._undo_index
        print(f"Initial: index={current_index}, stack_len={len(self.undo._undo_stack)}")
        
        # First undo should decrement index by 1
        result = self.undo.undo()
        print(f"After undo1: index={self.undo._undo_index}, stack_len={len(self.undo._undo_stack)}, result={result}")
        self.assertTrue(result, "First undo should succeed")
        self.assertEqual(self.undo._undo_index, current_index - 1, "Index should decrement by 1")
        
        # Second undo should decrement index by 1 again
        result = self.undo.undo()
        print(f"After undo2: index={self.undo._undo_index}, stack_len={len(self.undo._undo_stack)}, result={result}")
        self.assertTrue(result, "Second undo should succeed")
        self.assertEqual(self.undo._undo_index, current_index - 2, "Index should decrement by 2 total")
        
        # Third undo should decrement index by 1 again
        result = self.undo.undo()
        print(f"After undo3: index={self.undo._undo_index}, stack_len={len(self.undo._undo_stack)}, result={result}")
        self.assertTrue(result, "Third undo should succeed")
        self.assertEqual(self.undo._undo_index, current_index - 3, "Index should decrement by 3 total")
        
        # At some point we should hit the bottom
        # Keep undoing until we can't anymore (index 0 is the bottom)
        while self.undo._undo_index > 0:
            result = self.undo.undo()
            print(f"After undo: index={self.undo._undo_index}, result={result}")
            if not result:
                break
        
        # Now we should be at index 0
        # One more undo should fail
        result = self.undo.undo()
        print(f"After final undo: index={self.undo._undo_index}, result={result}")
        self.assertFalse(result, "Undo at bottom (index 0) should fail")

    def test_redo_sequence(self):
        """Test redoing after undo."""
        print("\n=== TEST: Redo Sequence ===")
        self.undo.mark("change1")
        self.undo.mark("change2")
        self.undo.mark("change3")
        
        # Undo twice
        self.undo.undo()
        self.undo.undo()
        current_index = self.undo._undo_index
        print(f"After 2 undos: index={current_index}, stack_len={len(self.undo._undo_stack)}")
        
        # First redo should increment index by 1
        result = self.undo.redo()
        print(f"After redo1: index={self.undo._undo_index}, stack_len={len(self.undo._undo_stack)}, result={result}")
        self.assertTrue(result, "First redo should succeed")
        self.assertEqual(self.undo._undo_index, current_index + 1, "Index should increment by 1")
        
        # Second redo should increment index by 1 again
        result = self.undo.redo()
        print(f"After redo2: index={self.undo._undo_index}, stack_len={len(self.undo._undo_stack)}, result={result}")
        self.assertTrue(result, "Second redo should succeed")
        self.assertEqual(self.undo._undo_index, current_index + 2, "Index should increment by 2 total")

    def test_branching_history(self):
        """Test that marking after undo creates a new branch (truncates forward history)."""
        print("\n=== TEST: Branching History ===")
        self.undo.mark("change1")
        self.undo.mark("change2")
        self.undo.mark("change3")
        stack_before_undo = len(self.undo._undo_stack)
        print(f"After 3 marks: index={self.undo._undo_index}, stack_len={stack_before_undo}")
        
        # Undo twice
        self.undo.undo()
        self.undo.undo()
        index_after_undos = self.undo._undo_index
        stack_after_undos = len(self.undo._undo_stack)
        print(f"After 2 undos: index={index_after_undos}, stack_len={stack_after_undos}")
        
        # Mark a new change - this OVERWRITES at current position due to mark() logic
        # When not at LAST_STATE and not at top, mark() doesn't increment - it overwrites
        self.undo.mark("change4")
        print(f"After new mark: index={self.undo._undo_index}, stack_len={len(self.undo._undo_stack)}")
        
        # The mark() logic keeps the index the same when overwriting (not at LAST_STATE)
        # because of the condition: elif _undo_index < len(stack) - 1 and next != LAST_STATE: pass
        self.assertEqual(self.undo._undo_index, index_after_undos, "Index stays same when overwriting")
        # The stack should have been truncated: everything after index_after_undos should be gone
        expected_stack_len = index_after_undos + 1  # All items up to and including current index
        self.assertEqual(len(self.undo._undo_stack), expected_stack_len, f"Stack should have {expected_stack_len} items after branching")
        
        # Verify we can't redo (forward history was truncated)
        self.assertFalse(self.undo.has_redo(), "Should not have redo after branching")

    def test_has_undo_has_redo(self):
        """Test has_undo and has_redo logic."""
        print("\n=== TEST: has_undo/has_redo ===")
        # Initial state: depends on bootstrap - may have "Operations restored" state
        # At index 1, there IS undo available (can go back to index 0)
        initial_has_undo = self.undo.has_undo()
        initial_has_redo = self.undo.has_redo()
        print(f"Initial: has_undo={initial_has_undo}, has_redo={initial_has_redo}, index={self.undo._undo_index}")
        
        self.undo.mark("change1")
        # After one change: definitely has undo, no redo
        self.assertTrue(self.undo.has_undo())
        self.assertFalse(self.undo.has_redo())
        
        self.undo.mark("change2")
        # After two changes: has undo, no redo
        self.assertTrue(self.undo.has_undo())
        self.assertFalse(self.undo.has_redo())
        
        self.undo.undo()
        # After one undo: has undo, has redo
        self.assertTrue(self.undo.has_undo())
        self.assertTrue(self.undo.has_redo())
        
        # Undo until we reach the bottom (index 0)
        while self.undo._undo_index > 0:
            self.undo.undo()
        
        # At bottom (index 0): no undo, has redo
        self.assertFalse(self.undo.has_undo())
        self.assertTrue(self.undo.has_redo())

    def test_validate_adds_last_state(self):
        """Test that validate() adds LAST_STATE when needed."""
        print("\n=== TEST: validate() LAST_STATE ===")
        self.undo.mark("change1")
        initial_len = len(self.undo._undo_stack)
        print(f"Before validate: stack_len={initial_len}, index={self.undo._undo_index}")
        
        # Calling validate should add LAST_STATE if we're at the top
        self.undo.validate()
        print(f"After validate: stack_len={len(self.undo._undo_stack)}, index={self.undo._undo_index}")
        
        # Should have added LAST_STATE
        self.assertEqual(len(self.undo._undo_stack), initial_len + 1, "validate should add LAST_STATE")
        self.assertEqual(self.undo._undo_stack[-1].message, self.undo.LAST_STATE, "Last state should be LAST_STATE")

    def test_undo_with_direct_index(self):
        """Test undo() with explicit index parameter."""
        print("\n=== TEST: Undo with index ===")
        self.undo.mark("change1")
        self.undo.mark("change2")
        self.undo.mark("change3")
        print(f"Initial: index={self.undo._undo_index}, stack_len={len(self.undo._undo_stack)}")
        
        # Undo directly to index 1 (should restore change1 state)
        result = self.undo.undo(index=1)
        print(f"After undo(1): index={self.undo._undo_index}, stack_len={len(self.undo._undo_stack)}, result={result}")
        self.assertTrue(result, "Undo to index 1 should succeed")
        self.assertEqual(self.undo._undo_index, 1, "Index should be 1")

    def test_redo_with_direct_index(self):
        """Test redo() with explicit index parameter."""
        print("\n=== TEST: Redo with index ===")
        self.undo.mark("change1")
        self.undo.mark("change2")
        self.undo.mark("change3")
        self.undo.undo()
        self.undo.undo()
        print(f"After undos: index={self.undo._undo_index}, stack_len={len(self.undo._undo_stack)}")
        
        # Redo directly to index 2 (should restore change3 state)
        result = self.undo.redo(index=2)
        print(f"After redo(2): index={self.undo._undo_index}, stack_len={len(self.undo._undo_stack)}, result={result}")
        self.assertTrue(result, "Redo to index 2 should succeed")
        self.assertEqual(self.undo._undo_index, 3, "Index should be 3 (index+1)")


if __name__ == "__main__":
    unittest.main()
