"""
Regression tests for node.py cycle-prevention and integrity-checking fixes.

This test file documents and verifies the following bug fixes:
1. is_a_child_of() - Now correctly checks only ancestors, not self
2. insert_sibling() - Now safely handles None parent case
3. tree_integrity_errors() - Now properly distinguishes cycle vs shared-subtree errors
"""

import unittest

from meerk40t.core.node.node import Node


class TestNodeCyclePreventionFixes(unittest.TestCase):
    def test_is_a_child_of_checks_ancestors_not_self(self):
        """
        BUG FIX: is_a_child_of() should return False if checking against self.
        Previously it could return True because it checked candidate before adding to visited.
        """
        a = Node(type="group")
        # A node is never a child of itself
        self.assertFalse(a.is_a_child_of(a))

    def test_is_a_child_of_cycle_safe(self):
        """
        BUG FIX: is_a_child_of() must not infinite-loop even if tree is corrupted with cycles.
        """
        a = Node(type="group")
        b = Node(type="group")
        a.append_child(b)

        # Manually create corruption: cycle a -> b -> a
        a._parent = b
        b._children.append(a)

        # This should NOT infinite-loop and should return True (a is ancestor of b)
        self.assertTrue(b.is_a_child_of(a))

    def test_insert_sibling_handles_none_parent(self):
        """
        BUG FIX: insert_sibling() must not crash with AttributeError when
        reference_sibling has no parent (is a root).
        Previously it would access destination_parent.children without checking for None.
        """
        root_a = Node(type="root")
        root_b = Node(type="root")

        # This should not raise AttributeError
        root_a.insert_sibling(root_b)

        # root_a and root_b should remain unchanged (insert_sibling early-returns)
        self.assertIsNone(root_a.parent)
        self.assertIsNone(root_b.parent)

    def test_append_child_prevents_cycle(self):
        """
        BUG FIX: append_child() must prevent creating parent cycles.
        Example: parent.append_child(child); child.append_child(parent) -> cycle
        """
        parent = Node(type="group")
        child = Node(type="group")

        parent.append_child(child)
        self.assertIs(child.parent, parent)

        # Attempting to create a cycle should be silently prevented
        child.append_child(parent)

        # Tree should remain uncorrupted
        self.assertIs(child.parent, parent)
        self.assertIsNone(parent.parent)


class TestNodeIntegrityCheckerFixes(unittest.TestCase):
    def test_tree_integrity_detects_cycle(self):
        """
        tree_integrity_errors() must detect parent cycles.
        """
        a = Node(type="group")
        b = Node(type="group")
        a.append_child(b)

        # Corrupt: a -> b -> a
        a._parent = b
        b._children.append(a)

        errors = a.tree_integrity_errors()
        self.assertTrue(
            any("CYCLE detected" in e for e in errors),
            f"Expected CYCLE error, got: {errors}"
        )

    def test_tree_integrity_detects_shared_subtree(self):
        """
        tree_integrity_errors() must detect when a node appears under multiple parents.
        """
        root = Node(type="root")
        parent_a = Node(type="group")
        parent_b = Node(type="group")
        shared_child = Node(type="group")

        root._children.extend([parent_a, parent_b])
        parent_a._parent = root
        parent_b._parent = root
        shared_child._parent = root

        parent_a._children.append(shared_child)
        # Manually add to parent_b too (simulating corruption)
        parent_b._children.append(shared_child)

        errors = root.tree_integrity_errors()
        # Should detect that shared_child appears twice
        self.assertTrue(
            any("shared" in e.lower() for e in errors),
            f"Expected shared subtree error, got: {errors}"
        )

    def test_tree_integrity_cycle_safe(self):
        """
        tree_integrity_errors() must not infinite-loop on cycles.
        """
        a = Node(type="group")
        b = Node(type="group")
        a.append_child(b)

        # Corrupt: a -> b -> a
        a._parent = b
        b._children.append(a)

        # This should complete in reasonable time
        errors = a.tree_integrity_errors()
        # Should report the cycle
        self.assertTrue(len(errors) > 0)


if __name__ == "__main__":
    unittest.main()
