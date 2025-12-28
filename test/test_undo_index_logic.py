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

    def tearDown(self):
        self.kernel.shutdown()

    def test_initial_state(self):
        """Test initial state after kernel boot."""
        # After init, undo behavior should be well-defined
        # Initial state may or may not have undo available depending on bootstrap
        has_undo = self.undo.has_undo()
        has_redo = self.undo.has_redo()
        
        # Initially should not have redo (nothing ahead in history)
        self.assertFalse(has_redo, "Should not have redo at initial state")

    def test_mark_sequence(self):
        """Test marking multiple states creates undo history."""
        # Initially may or may not have undo
        initial_has_undo = self.undo.has_undo()
        
        self.undo.mark("change1")
        # After first change, should have undo
        self.assertTrue(self.undo.has_undo(), "Should have undo after first mark")
        self.assertFalse(self.undo.has_redo(), "Should not have redo at top of history")
        
        self.undo.mark("change2")
        self.assertTrue(self.undo.has_undo(), "Should have undo after second mark")
        
        self.undo.mark("change3")
        self.assertTrue(self.undo.has_undo(), "Should have undo after third mark")
        
        # Verify undo strings are accessible
        undo_str = self.undo.undo_string()
        self.assertIn("change", undo_str.lower(), "Undo string should reference a change")

    def test_undo_sequence(self):
        """Test undoing multiple times."""
        self.undo.mark("change1")
        self.undo.mark("change2")
        self.undo.mark("change3")
        
        # Should be at top of history
        self.assertTrue(self.undo.has_undo(), "Should have undo after marks")
        self.assertFalse(self.undo.has_redo(), "Should not have redo at top")
        
        # Undo should succeed
        result = self.undo.undo()
        self.assertTrue(result, "First undo should succeed")
        self.assertTrue(self.undo.has_undo(), "Should still have undo")
        self.assertTrue(self.undo.has_redo(), "Should now have redo")
        
        # Continue undoing
        self.assertTrue(self.undo.undo(), "Second undo should succeed")
        self.assertTrue(self.undo.undo(), "Third undo should succeed")
        
        # Keep undoing until we can't anymore
        undo_count = 0
        while self.undo.has_undo() and undo_count < 100:  # Safety limit
            if not self.undo.undo():
                break
            undo_count += 1
        
        # At bottom: no undo available, redo available
        self.assertFalse(self.undo.has_undo(), "Should not have undo at bottom")
        self.assertTrue(self.undo.has_redo(), "Should have redo at bottom")
        
        # One more undo should fail
        self.assertFalse(self.undo.undo(), "Undo at bottom should fail")

    def test_redo_sequence(self):
        """Test redoing after undo."""
        self.undo.mark("change1")
        self.undo.mark("change2")
        self.undo.mark("change3")
        
        # Undo twice to enable redo
        self.assertTrue(self.undo.undo(), "First undo should succeed")
        self.assertTrue(self.undo.undo(), "Second undo should succeed")
        
        # Should have both undo and redo available
        self.assertTrue(self.undo.has_undo(), "Should have undo after undoing twice")
        self.assertTrue(self.undo.has_redo(), "Should have redo after undoing")
        
        # Redo should succeed
        result = self.undo.redo()
        self.assertTrue(result, "First redo should succeed")
        self.assertTrue(self.undo.has_redo(), "Should still have redo")
        
        # Second redo should also succeed
        result = self.undo.redo()
        self.assertTrue(result, "Second redo should succeed")
        
        # Verify we're back to having undo available
        self.assertTrue(self.undo.has_undo(), "Should have undo after redo")

    def test_branching_history(self):
        """Test that marking after undo creates a new branch (truncates forward history)."""
        self.undo.mark("change1")
        self.undo.mark("change2")
        self.undo.mark("change3")
        
        # Undo twice to enable redo
        self.undo.undo()
        self.undo.undo()
        
        # Should have redo available
        self.assertTrue(self.undo.has_redo(), "Should have redo after undoing")
        
        # Mark a new change - this creates a branch, truncating forward history
        self.undo.mark("change4")
        
        # Verify forward history was truncated
        self.assertFalse(self.undo.has_redo(), "Should not have redo after branching")
        self.assertTrue(self.undo.has_undo(), "Should still have undo after branching")

    def test_has_undo_has_redo(self):
        """Test has_undo and has_redo logic."""
        self.undo.mark("change1")
        # After one change: has undo, no redo
        self.assertTrue(self.undo.has_undo(), "Should have undo after change")
        self.assertFalse(self.undo.has_redo(), "Should not have redo at top")
        
        self.undo.mark("change2")
        # After two changes: has undo, no redo
        self.assertTrue(self.undo.has_undo())
        self.assertFalse(self.undo.has_redo())
        
        self.undo.undo()
        # After one undo: has undo, has redo
        self.assertTrue(self.undo.has_undo(), "Should have undo after one undo")
        self.assertTrue(self.undo.has_redo(), "Should have redo after undo")
        
        # Undo until we can't anymore
        undo_count = 0
        while self.undo.has_undo() and undo_count < 100:
            self.undo.undo()
            undo_count += 1
        
        # At bottom: no undo, has redo
        self.assertFalse(self.undo.has_undo(), "Should not have undo at bottom")
        self.assertTrue(self.undo.has_redo(), "Should have redo at bottom")

    def test_validate_preserves_functionality(self):
        """Test that validate() maintains undo/redo functionality."""
        self.undo.mark("change1")
        
        # Calling validate should not break undo/redo
        self.undo.validate()
        
        # Should still be able to check undo/redo status
        has_undo = self.undo.has_undo()
        has_redo = self.undo.has_redo()
        self.assertIsNotNone(has_undo, "has_undo should return a boolean")
        self.assertIsNotNone(has_redo, "has_redo should return a boolean")
        
        # Should be able to get undo/redo strings without error
        if has_undo:
            undo_str = self.undo.undo_string()
            self.assertIsInstance(undo_str, str, "undo_string should return a string")

    def test_undo_with_direct_index(self):
        """Test undo() with explicit index parameter."""
        self.undo.mark("change1")
        self.undo.mark("change2")
        self.undo.mark("change3")
        
        # Undo directly to a specific index
        result = self.undo.undo(index=1)
        self.assertTrue(result, "Undo to specific index should succeed")
        # After undo to index 1, we should be at that state with redo available
        self.assertTrue(self.undo.has_redo(), "Should have redo after undo to index")

    def test_redo_with_direct_index(self):
        """Test redo() with explicit index parameter."""
        self.undo.mark("change1")
        self.undo.mark("change2")
        self.undo.mark("change3")
        self.undo.undo()
        self.undo.undo()
        
        # Redo directly to a specific index
        result = self.undo.redo(index=2)
        self.assertTrue(result, "Redo to specific index should succeed")
        # After redo, should be able to check state
        self.assertTrue(self.undo.has_undo(), "Should have undo after redo to index")


if __name__ == "__main__":
    unittest.main()
