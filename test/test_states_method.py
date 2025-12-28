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
        # Create a clear state
        self.undo.mark("state1")
        self.undo.mark("state2")
        self.undo.mark("state3")
        
        # Undo twice to be at state1
        self.undo.undo()
        self.undo.undo()
        
        current_index = self.undo._undo_index
        print(f"\nCurrent index: {current_index}")
        print(f"Stack: {[str(s) for s in self.undo._undo_stack]}")
        print(f"Current state: {self.undo._undo_stack[current_index]}")
        
        # Get redo states
        redo_states = list(self.undo.states("redo"))
        print(f"\nRedo states:")
        for idx, state in redo_states:
            print(f"  [{idx}] {state}")
        
        # The FIRST redo state should be at index current_index + 1
        # because that's what redo() would restore
        if redo_states:
            first_redo_idx = redo_states[0][0]
            print(f"\nFirst redo index: {first_redo_idx}")
            print(f"Expected (current_index + 1): {current_index + 1}")
            
            # This should be true: the first redo state is the NEXT state
            self.assertEqual(first_redo_idx, current_index + 1,
                           "First redo state should be at current_index + 1")
            
            # The current state should NOT be in redo states
            redo_indices = [idx for idx, _ in redo_states]
            self.assertNotIn(current_index, redo_indices,
                           "Current state should NOT appear in redo states")

    def test_undo_states(self):
        """Test that undo states correctly excludes the current state."""
        self.undo.mark("state1")
        self.undo.mark("state2")
        self.undo.mark("state3")
        
        current_index = self.undo._undo_index
        print(f"\nCurrent index: {current_index}")
        
        # Get undo states
        undo_states = list(self.undo.states("undo"))
        print(f"\nUndo states:")
        for idx, state in undo_states:
            print(f"  [{idx}] {state}")
        
        # The current state should NOT be in undo states
        undo_indices = [idx for idx, _ in undo_states]
        self.assertNotIn(current_index, undo_indices,
                       "Current state should NOT appear in undo states")
        
        # The LAST undo state should be at index current_index - 1
        # (or earlier, but the closest should be current_index - 1)
        if undo_states:
            # Find the highest index in undo states
            max_undo_idx = max(idx for idx, _ in undo_states)
            print(f"\nHighest undo index: {max_undo_idx}")
            print(f"Expected (current_index - 1): {current_index - 1}")
            self.assertLessEqual(max_undo_idx, current_index - 1,
                               "Highest undo state should be at most current_index - 1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
