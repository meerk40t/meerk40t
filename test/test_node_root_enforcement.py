import unittest
from meerk40t.core.node.node import Node
from meerk40t.core.node.rootnode import RootNode

class TestNodeRootEnforcement(unittest.TestCase):
    def test_append_child_rejects_non_branch_on_root(self):
        class MockContext:
            _ = lambda s, x: x
        root = RootNode(MockContext())
        
        # Try to append a group directly to root
        group = Node(type="group")
        root.append_child(group)
        
        # Should be rejected (not added)
        self.assertNotIn(group, root.children)
        self.assertIsNone(group.parent)

    def test_insert_sibling_rejects_non_branch_under_root(self):
        class MockContext:
            _ = lambda s, x: x
        root = RootNode(MockContext())
        
        # Get one of the branches (e.g. branch elems)
        branch = root.children[0]
        self.assertTrue(branch.type.startswith("branch"))
        
        # Try to insert a group as sibling to the branch (which would put it under root)
        group = Node(type="group")
        branch.insert_sibling(group)
        
        # Should be rejected
        self.assertNotIn(group, root.children)
        self.assertIsNone(group.parent)

    def test_append_child_allows_branch_on_root(self):
        class MockContext:
            _ = lambda s, x: x
        root = RootNode(MockContext())
        
        # Try to append a new branch
        new_branch = Node(type="branch custom")
        root.append_child(new_branch)
        
        # Should be allowed
        self.assertIn(new_branch, root.children)
        self.assertIs(new_branch.parent, root)

if __name__ == "__main__":
    unittest.main()
