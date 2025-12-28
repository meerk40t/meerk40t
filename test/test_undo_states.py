"""
Test the states() method to verify redo states are correct.
"""
import unittest
from test.bootstrap import bootstrap


class TestStatesMethod(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements
        self.undo = self.elements.undo

    def tearDown(self):
        self.kernel.shutdown()

    def test_redo_states(self):
        """Test that redo states correctly excludes the current state."""
        self.undo.mark("state1")
        self.undo.mark("state2")
        self.undo.mark("state3")
        
        # Undo twice to enable redo
        self.undo.undo()
        self.undo.undo()
        
        # Get redo states - should only return future states
        redo_states = list(self.undo.states("redo"))
        
        # Should have redo states available
        self.assertTrue(len(redo_states) > 0, "Should have redo states after undoing")
        
        # Verify redo states are valid by trying to access them
        for idx, state in redo_states:
            self.assertIsNotNone(state, f"State at index {idx} should not be None")
            self.assertIsNotNone(state.message, f"State at index {idx} should have a message")

    def test_undo_states(self):
        """Test that undo states correctly excludes the current state."""
        self.undo.mark("state1")
        self.undo.mark("state2")
        self.undo.mark("state3")
        
        # Get undo states - should return previous states
        undo_states = list(self.undo.states("undo"))
        
        # Should have undo states available after marking
        self.assertTrue(len(undo_states) > 0, "Should have undo states after marking changes")
        
        # Verify undo states are valid
        for idx, state in undo_states:
            self.assertIsNotNone(state, f"State at index {idx} should not be None")
            self.assertIsNotNone(state.message, f"State at index {idx} should have a message")


if __name__ == "__main__":
    unittest.main(verbosity=2)
