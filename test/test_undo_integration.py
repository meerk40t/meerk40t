"""
Integration tests for undo/redo after backup_tree / restore_tree optimizations.

These tests exercise the full undo/redo cycle through console commands,
matching the real application flow where:
- Element creation uses post_classify (mark happens AFTER element is in tree)
- Element modification uses undoscope (mark happens BEFORE modification)
- Undo/redo use the console 'undo'/'redo' commands

Tests verify that:
1. Adding elements and undoing removes them
2. Redo restores them
3. Multiple undo/redo cycles work
4. Element attributes are preserved through undo/redo
5. Copy independence (backup doesn't share mutable state)
"""

import unittest

from test.bootstrap import bootstrap


class TestUndoRedoIntegration(unittest.TestCase):
    """Integration tests for undo/redo with optimized backup/restore."""

    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        if hasattr(self, "kernel") and self.kernel:
            self.kernel()

    def count_elem_children(self):
        """Count direct children in the elements branch."""
        return len(self.elements.elem_branch.children)

    def test_undo_add_element(self):
        """Add an element via console, undo it, verify it's gone."""
        initial_count = self.count_elem_children()

        self.kernel.console("rect 0 0 1cm 1cm\n")
        self.assertEqual(self.count_elem_children(), initial_count + 1)

        self.kernel.console("undo\n")
        self.assertEqual(self.count_elem_children(), initial_count)

    def test_redo_add_element(self):
        """Add an element, undo, redo — element should reappear."""
        initial_count = self.count_elem_children()

        self.kernel.console("rect 0 0 1cm 1cm\n")
        self.assertEqual(self.count_elem_children(), initial_count + 1)

        self.kernel.console("undo\n")
        self.assertEqual(self.count_elem_children(), initial_count)

        self.kernel.console("redo\n")
        self.assertEqual(self.count_elem_children(), initial_count + 1)

    def test_multiple_undo_redo(self):
        """Add multiple elements, undo them one by one, redo them."""
        initial_count = self.count_elem_children()

        self.kernel.console("rect 0 0 1cm 1cm\n")
        self.assertEqual(self.count_elem_children(), initial_count + 1)

        self.kernel.console("rect 2cm 0 1cm 1cm\n")
        self.assertEqual(self.count_elem_children(), initial_count + 2)

        self.kernel.console("rect 4cm 0 1cm 1cm\n")
        self.assertEqual(self.count_elem_children(), initial_count + 3)

        # Undo all three
        self.kernel.console("undo\n")
        self.assertEqual(self.count_elem_children(), initial_count + 2)
        self.kernel.console("undo\n")
        self.assertEqual(self.count_elem_children(), initial_count + 1)
        self.kernel.console("undo\n")
        self.assertEqual(self.count_elem_children(), initial_count)

        # Redo all three
        self.kernel.console("redo\n")
        self.assertEqual(self.count_elem_children(), initial_count + 1)
        self.kernel.console("redo\n")
        self.assertEqual(self.count_elem_children(), initial_count + 2)
        self.kernel.console("redo\n")
        self.assertEqual(self.count_elem_children(), initial_count + 3)

    def test_undo_preserves_attributes(self):
        """Verify that undo restores element types correctly."""
        initial_count = self.count_elem_children()

        # Add a rect and a circle
        self.kernel.console("rect 0 0 1cm 1cm\n")
        self.kernel.console("circle 3cm 3cm 1cm\n")
        self.assertEqual(self.count_elem_children(), initial_count + 2)

        # Undo circle
        self.kernel.console("undo\n")
        self.assertEqual(self.count_elem_children(), initial_count + 1)

        # Remaining element should be the rect, not the circle
        last_child = self.elements.elem_branch.children[-1]
        self.assertEqual(last_child.type, "elem rect")

    def test_undo_redo_with_undoscope(self):
        """Test undo/redo with direct undoscope for property mutations."""
        initial_count = self.count_elem_children()

        # Add element via console (creates proper undo mark)
        self.kernel.console("rect 0 0 1cm 1cm\n")
        self.assertEqual(self.count_elem_children(), initial_count + 1)

        node = self.elements.elem_branch.children[-1]
        original_label = node.label

        # Modify label via undoscope (mark captures state WITH rect)
        with self.elements.undoscope("Modify label"):
            node.label = "Modified"

        # Undo the modification
        self.kernel.console("undo\n")

        # The element should still be there with original label
        self.assertEqual(self.count_elem_children(), initial_count + 1)
        restored = self.elements.elem_branch.children[-1]
        self.assertEqual(restored.label, original_label)

    def test_undo_redo_independence(self):
        """Verify that undo doesn't corrupt later redo states."""
        initial_count = self.count_elem_children()

        self.kernel.console("rect 0 0 1cm 1cm\n")
        self.kernel.console("circle 3cm 3cm 1cm\n")
        self.assertEqual(self.count_elem_children(), initial_count + 2)

        # Undo circle
        self.kernel.console("undo\n")
        self.assertEqual(self.count_elem_children(), initial_count + 1)

        # Redo circle
        self.kernel.console("redo\n")
        self.assertEqual(self.count_elem_children(), initial_count + 2)

        # First child should still be rect
        first = self.elements.elem_branch.children[-2]
        self.assertEqual(first.type, "elem rect")

    def test_copy_independence_after_backup(self):
        """Verify that modifying nodes after backup doesn't affect undo state.

        When backup_tree runs, the returned copies must be fully independent
        of the live tree.  Mutating a live node should never bleed through to
        an earlier snapshot.
        """
        initial_count = self.count_elem_children()

        # Create element via console (proper undo mark)
        self.kernel.console("rect 0 0 1cm 1cm\n")
        self.assertEqual(self.count_elem_children(), initial_count + 1)

        # Take a manual backup of the tree
        backup = self.elements._tree.backup_tree()

        # Mutate the live node AFTER backup
        node = self.elements.elem_branch.children[-1]
        node.label = "Mutated_After_Backup"
        node.x = 99999

        # The backup should be completely independent of live mutations
        # Find the elem branch in the backup and check its last child
        for b in backup:
            if b.type == "branch elems":
                backup_node = b.children[-1]
                self.assertNotEqual(backup_node.label, "Mutated_After_Backup")
                self.assertNotEqual(backup_node.x, 99999)
                break
        else:
            self.fail("Could not find elem branch in backup")

    def test_undo_full_cycle(self):
        """Test a full undo/redo cycle: add, undo, redo, undo again."""
        initial_count = self.count_elem_children()

        self.kernel.console("rect 0 0 1cm 1cm\n")
        self.assertEqual(self.count_elem_children(), initial_count + 1)

        # Undo
        self.kernel.console("undo\n")
        self.assertEqual(self.count_elem_children(), initial_count)

        # Redo
        self.kernel.console("redo\n")
        self.assertEqual(self.count_elem_children(), initial_count + 1)

        # Undo again
        self.kernel.console("undo\n")
        self.assertEqual(self.count_elem_children(), initial_count)


if __name__ == "__main__":
    unittest.main()
