import unittest
from meerk40t.core.node.node import Node
from meerk40t.core.node.rootnode import RootNode

class TestNodeRootUpdate(unittest.TestCase):
    def test_append_child_updates_root(self):
        # Mock context for RootNode
        class MockContext:
            _ = lambda s, x: x
        
        root = RootNode(MockContext())
        # Use a branch type so it's allowed under root
        parent = Node(type="branch custom")
        root.add_node(parent)
        
        # Create a detached node
        child = Node(type="group")
        self.assertIsNone(getattr(child, "_root", None))
        
        # Append to parent (which is a branch, so it can have children)
        parent.append_child(child)
        
        # Check if root is updated
        self.assertIs(child._root, root)
        
    def test_insert_sibling_updates_root(self):
        class MockContext:
            _ = lambda s, x: x
            
        root = RootNode(MockContext())
        # Use a branch type so it's allowed under root
        sibling1 = Node(type="branch custom")
        root.add_node(sibling1)
        
        # Create a detached node (also a branch so it's allowed)
        sibling2 = Node(type="branch other")
        self.assertIsNone(getattr(sibling2, "_root", None))
        
        # Insert as sibling
        sibling1.insert_sibling(sibling2)
        
        # Check if root is updated
        self.assertIs(sibling2._root, root)

if __name__ == "__main__":
    unittest.main()
