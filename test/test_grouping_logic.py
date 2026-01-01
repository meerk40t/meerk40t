
import unittest
from meerk40t.core.node.node import Node
from meerk40t.core.elements.groups import filter_redundant_ancestors
from io import StringIO
from contextlib import redirect_stdout

class TestGroupingAndTreeCheckBehavior(unittest.TestCase):
    """
    Regression tests for:
    1. New grouping behavior in groups.py – descendants are filtered out when both
       ancestor and descendant are selected.
    2. `tree check` console command – reports `tree_integrity_errors`.
    """

    def _build_simple_hierarchy(self):
        """
        Build a small, easy-to-reason-about hierarchy:

        root
        ├── parent
        │   └── child
        └── sibling
        """
        root = Node(type="root")
        root._root = root
        parent = Node(type="group")
        child = Node(type="elem")
        sibling = Node(type="elem")

        root.append_child(parent)
        root.append_child(sibling)
        parent.append_child(child)

        return root, parent, child, sibling

    def test_grouping_ignores_descendants_when_ancestor_selected(self):
        """
        When both an ancestor and its descendant are selected for grouping, only
        the ancestor (and other non-descendant nodes) should be grouped.
        """
        root, parent, child, sibling = self._build_simple_hierarchy()

        # Simulate the selected nodes list containing both ancestor and descendant.
        selected_nodes = [parent, child, sibling]

        filtered = list(filter_redundant_ancestors(selected_nodes))

        # The ancestor and the independent sibling must remain, the descendant must be removed.
        self.assertIn(parent, filtered)
        self.assertIn(sibling, filtered)
        self.assertNotIn(child, filtered)

    def test_tree_check_reports_no_issues_for_valid_tree(self):
        """
        `tree check` should report no issues when the tree is well-formed.
        """
        root, parent, child, sibling = self._build_simple_hierarchy()

        # Mock the console command context
        # Since we can't easily import the command itself without the full kernel,
        # we will test the underlying integrity function which the command calls.
        # The command is just a wrapper around tree_integrity_errors.
        
        errors = root.tree_integrity_errors()
        self.assertEqual(len(errors), 0)

    def test_tree_check_reports_errors_for_corrupted_tree(self):
        """
        `tree check` should report the errors returned by `tree_integrity_errors`
        when the tree has a structural problem (e.g. a cycle).
        """
        root, parent, child, sibling = self._build_simple_hierarchy()

        # Introduce a cycle: make `root` a child of `child`.
        # We have to bypass append_child's cycle check to create corruption
        child._children.append(root)
        root._parent = child

        errors = root.tree_integrity_errors()
        
        self.assertTrue(any("CYCLE detected" in e for e in errors))

if __name__ == "__main__":
    unittest.main()
