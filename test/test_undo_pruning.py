"""
Test undo stack pruning logic to ensure index stays within valid bounds.
"""
import unittest
from test.bootstrap import bootstrap


class TestUndoPruning(unittest.TestCase):
    """Test the undo stack pruning when levels limit is exceeded."""

    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements
        self.undo = self.elements.undo

    def tearDown(self):
        self.kernel.shutdown()

    def test_validate_prunes_and_maintains_functionality(self):
        """Test that validate() prunes correctly and maintains functionality."""
        # Set a small number of levels to force aggressive pruning
        self.undo.levels = 3
        
        # Create many more states than the limit
        for i in range(10):
            self.undo.mark(f"change_{i}")
        
        # Call validate which should add LAST_STATE and prune
        self.undo.validate()
        
        # After pruning, undo/redo should still work
        has_undo = self.undo.has_undo()
        has_redo = self.undo.has_redo()
        
        # Verify functionality is preserved
        self.assertIsNotNone(has_undo, "has_undo should return boolean")
        self.assertIsNotNone(has_redo, "has_redo should return boolean")
        
        if has_undo:
            result = self.undo.undo()
            self.assertTrue(result, "Undo should succeed after pruning")
            # Verify we can get strings without errors
            self.assertIsNotNone(self.undo.redo_string())

    def test_aggressive_pruning_preserves_operations(self):
        """Test pruning when drastically reducing levels limit."""
        # Start with default levels and create many states
        for i in range(20):
            self.undo.mark(f"state_{i}")
        
        # Drastically reduce the levels limit
        self.undo.levels = 3
        
        # Call validate which will trigger aggressive pruning
        self.undo.validate()
        
        # Critical: operations should still work
        self.assertIsNotNone(self.undo.has_undo(), "has_undo should work after pruning")
        self.assertIsNotNone(self.undo.has_redo(), "has_redo should work after pruning")
        
        # Should be able to get undo/redo strings without error
        try:
            undo_str = self.undo.undo_string()
            self.assertIsInstance(undo_str, str, "undo_string should return string")
        except (IndexError, AttributeError) as e:
            self.fail(f"Getting undo_string should not raise {type(e).__name__}: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
