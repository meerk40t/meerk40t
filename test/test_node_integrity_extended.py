
import unittest
from meerk40t.core.node.node import Node

class TestNodeIntegrityCheckerAdditionalCases(unittest.TestCase):
    def _assert_error_contains(self, errors, *substrings):
        self.assertTrue(
            any(all(s in err for s in substrings) for err in errors),
            msg=f"Expected an error containing {substrings}, got: {errors}",
        )

    def test_parent_child_mismatch_is_reported(self):
        # Build a small, valid tree
        root = Node(type="root")
        root._root = root
        parent_a = Node(type="group")
        parent_b = Node(type="group")
        child = Node(type="elem")

        root.append_child(parent_a)
        root.append_child(parent_b)
        parent_a.append_child(child)

        # Corrupt the tree: child is listed under parent_a but points to parent_b
        parent_a._children.append(child)  # ensure child appears under parent_a
        child._parent = parent_b          # but child's _parent says parent_b

        errors = root.tree_integrity_errors()
        self.assertTrue(errors, "Expected at least one integrity error for parent mismatch")
        self._assert_error_contains(errors, "Parent mismatch")

    def test_duplicate_child_in_children_list_is_reported(self):
        root = Node(type="root")
        root._root = root
        parent = Node(type="group")
        child = Node(type="elem")

        root.append_child(parent)
        parent.append_child(child)

        # Duplicate the same child in the parent's children list
        parent._children.append(child)

        errors = root.tree_integrity_errors()
        self.assertTrue(errors, "Expected integrity errors for duplicate child")
        self._assert_error_contains(errors, "Duplicate child")

    def test_max_nodes_abort_is_reported(self):
        # Build a simple chain of nodes
        root = Node(type="root")
        root._root = root
        current = root
        for i in range(1, 6):
            nxt = Node(type="elem")
            current.append_child(nxt)
            current = nxt

        # Set max_nodes low enough so traversal aborts early
        errors = root.tree_integrity_errors(max_nodes=2)
        self.assertTrue(errors, "Expected an integrity error due to max_nodes abort")
        # Error message should explain that checking was aborted early
        self._assert_error_contains(errors, "Traversal aborted")

    def test_reference_backlink_mismatch_is_reported(self):
        """
        A reference node should have a consistent backlink relationship with its target
        via the target's _references collection. Corrupt that invariant and verify
        the checker reports it.
        """
        root = Node(type="root")
        root._root = root
        target = Node(type="elem")
        ref = Node(type="reference")

        root.append_child(target)
        root.append_child(ref)

        # Establish an intended reference relationship
        ref.node = target
        if not hasattr(target, "_references"):
            target._references = []
        target._references.append(ref)

        # Now corrupt the backlink: target "forgets" about ref
        target._references.remove(ref)

        errors = root.tree_integrity_errors()
        self.assertTrue(errors, "Expected integrity errors for broken reference backlink")
        self._assert_error_contains(errors, "Reference node missing")

if __name__ == "__main__":
    unittest.main()
