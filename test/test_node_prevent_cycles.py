import unittest

from meerk40t.core.node.node import Node


class TestNodePreventCycles(unittest.TestCase):
    def test_append_child_prevents_parent_cycle(self):
        parent = Node(type="group")
        child = Node(type="group")

        parent.append_child(child)
        self.assertIs(child.parent, parent)
        self.assertIsNone(parent.parent)

        # This would previously create a parent-cycle:
        # parent -> child -> parent -> ... and recurse in notify_attached.
        child.append_child(parent)

        # Tree should remain unchanged and not be corrupted.
        self.assertIsNone(parent.parent)
        self.assertIs(child.parent, parent)


if __name__ == "__main__":
    unittest.main()
