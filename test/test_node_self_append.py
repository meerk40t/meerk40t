
import unittest
from meerk40t.core.node.node import Node

class TestNodeSelfAppend(unittest.TestCase):
    def test_append_child_self_is_prevented(self):
        """
        Test that appending a node to itself is prevented.
        """
        node = Node(type="group")
        node._root = node
        
        # Try to append self
        node.append_child(node)
        
        # Should not be its own parent
        self.assertIsNone(node.parent)
        self.assertNotIn(node, node.children)

    def test_insert_sibling_self_parent_is_prevented(self):
        """
        Test that inserting a sibling where the destination parent is the node itself is prevented.
        This is effectively the same as append_child(self) but via insert_sibling logic.
        """
        parent = Node(type="group")
        child = Node(type="elem")
        parent.append_child(child)
        
        # parent is child's parent.
        # If we try child.insert_sibling(parent), destination_parent is parent.
        # new_sibling is parent.
        # destination_parent IS new_sibling.
        
        child.insert_sibling(parent)
        
        # Parent should still be parent of child
        self.assertIs(child.parent, parent)
        # Parent should not be a child of itself (which would happen if the check failed)
        self.assertNotEqual(parent.parent, parent)

if __name__ == "__main__":
    unittest.main()
