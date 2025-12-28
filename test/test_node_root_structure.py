import unittest
from meerk40t.core.node.node import Node
from meerk40t.core.node.rootnode import RootNode

class TestNodeRootStructure(unittest.TestCase):
    def test_integrity_check_flags_invalid_root_children(self):
        class MockContext:
            _ = lambda s, x: x
            
        root = RootNode(MockContext())
        # RootNode initializes with 3 branches.
        
        # Manually add an invalid child (e.g. a group directly under root)
        invalid_child = Node(type="group")
        root._children.append(invalid_child)
        invalid_child._parent = root
        
        errors = root.tree_integrity_errors()
        self.assertTrue(any("Invalid child for parent" in e for e in errors),
                        f"Expected invalid child error, got: {errors}")

    def test_integrity_check_allows_branches(self):
        class MockContext:
            _ = lambda s, x: x
            
        root = RootNode(MockContext())
        # Should be valid by default
        errors = root.tree_integrity_errors()
        self.assertFalse(any("Invalid child for parent" in e for e in errors),
                         f"Expected no errors, got: {errors}")

if __name__ == "__main__":
    unittest.main()
