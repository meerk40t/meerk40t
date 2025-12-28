import unittest

from meerk40t.core.node.node import Node


class TestNodeIntegrityChecker(unittest.TestCase):
    def test_tree_integrity_errors_detects_cycle(self):
        a = Node(type="group")
        b = Node(type="group")
        a.append_child(b)

        # Manually corrupt the tree: create a parent cycle a -> b -> a
        a._parent = b
        b._children.append(a)

        errors = a.tree_integrity_errors()
        self.assertTrue(
            any("CYCLE detected" in e for e in errors),
            f"Expected CYCLE error, got: {errors}"
        )

if __name__ == "__main__":
    unittest.main()
