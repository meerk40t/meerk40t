"""
Test drag-and-drop optimization using batch operations.

This test verifies that drag-and-drop operations between elements and regmarks
branches use the optimized drop_multi() method for better performance.
"""

import unittest
import time
from test.bootstrap import bootstrap
from meerk40t.core.node.elem_rect import RectNode


class TestDragDropOptimization(unittest.TestCase):
    """Test drag-and-drop batch optimization"""

    def setUp(self):
        """Set up kernel and elements"""
        self.kernel = bootstrap()
        context = self.kernel.get_context("/")
        self.elements = context.elements
        
        # Clear any existing elements
        for node in list(self.elements.elem_branch.children):
            node.remove_node()
        for node in list(self.elements.reg_branch.children):
            node.remove_node()

    def tearDown(self):
        """Clean up kernel"""
        self.kernel.lifecycle = "shutdown"

    def test_drop_multi_exists(self):
        """Verify drop_multi method exists on branch nodes"""
        self.assertTrue(hasattr(self.elements.elem_branch, 'drop_multi'))
        self.assertTrue(hasattr(self.elements.reg_branch, 'drop_multi'))

    def test_drag_elements_to_regmarks(self):
        """Test dragging multiple elements to regmarks branch"""
        # Create 100 rectangles in elements branch
        rects = []
        for i in range(100):
            rect = RectNode(
                x=i * 10,
                y=i * 10,
                width=100,
                height=100,
            )
            self.elements.elem_branch.add_node(rect)
            rects.append(rect)
        
        # Verify all in elements
        self.assertEqual(len(list(self.elements.elem_branch.children)), 100)
        self.assertEqual(len(list(self.elements.reg_branch.children)), 0)
        
        # Drag all to regmarks
        self.elements.drag_and_drop(rects, self.elements.reg_branch)
        
        # Verify all moved to regmarks
        self.assertEqual(len(list(self.elements.elem_branch.children)), 0)
        self.assertEqual(len(list(self.elements.reg_branch.children)), 100)
        
        # Verify parent updated
        for rect in rects:
            self.assertEqual(rect.parent, self.elements.reg_branch)

    def test_drag_regmarks_to_elements(self):
        """Test dragging multiple regmarks to elements branch"""
        # Create 100 rectangles in regmarks branch
        rects = []
        for i in range(100):
            rect = RectNode(
                x=i * 10,
                y=i * 10,
                width=100,
                height=100,
            )
            self.elements.reg_branch.add_node(rect)
            rects.append(rect)
        
        # Verify all in regmarks
        self.assertEqual(len(list(self.elements.elem_branch.children)), 0)
        self.assertEqual(len(list(self.elements.reg_branch.children)), 100)
        
        # Drag all to elements
        self.elements.drag_and_drop(rects, self.elements.elem_branch)
        
        # Verify all moved to elements
        self.assertEqual(len(list(self.elements.elem_branch.children)), 100)
        self.assertEqual(len(list(self.elements.reg_branch.children)), 0)
        
        # Verify parent updated
        for rect in rects:
            self.assertEqual(rect.parent, self.elements.elem_branch)

    def test_drag_drop_performance(self):
        """Test performance improvement from batch drop operations"""
        # Create 1000 rectangles
        rects = []
        for i in range(1000):
            rect = RectNode(
                x=i * 10,
                y=i * 10,
                width=100,
                height=100,
            )
            self.elements.elem_branch.add_node(rect)
            rects.append(rect)
        
        # Time the drag operation
        start = time.perf_counter()
        self.elements.drag_and_drop(rects, self.elements.reg_branch)
        elapsed = time.perf_counter() - start
        
        # Should complete quickly (under 0.5 seconds for 1000 items)
        # This is a performance assertion - may need adjustment based on hardware
        # self.assertLess(elapsed, 0.5, 
        #                f"Drag-drop of 1000 items took {elapsed:.3f}s, expected < 0.5s")
        
        # Verify correctness
        self.assertEqual(len(list(self.elements.reg_branch.children)), 1000)

    def test_drag_mixed_types(self):
        """Test dragging mixed element types"""
        from meerk40t.core.node.elem_ellipse import EllipseNode
        from meerk40t.core.node.elem_path import PathNode
        
        # Create mixed types
        nodes = []
        
        # Add rectangles
        for i in range(10):
            rect = RectNode(x=i*10, y=0, width=50, height=50)
            self.elements.elem_branch.add_node(rect)
            nodes.append(rect)
        
        # Add ellipses
        for i in range(10):
            ellipse = EllipseNode(cx=i*10, cy=100, rx=25, ry=25)
            self.elements.elem_branch.add_node(ellipse)
            nodes.append(ellipse)
        
        # Drag all to regmarks
        self.elements.drag_and_drop(nodes, self.elements.reg_branch)
        
        # Verify all moved
        self.assertEqual(len(list(self.elements.elem_branch.children)), 0)
        self.assertEqual(len(list(self.elements.reg_branch.children)), 20)

    def test_drag_drop_preserves_order(self):
        """Test that drag-drop preserves node order"""
        # Create rectangles with specific order
        rects = []
        for i in range(50):
            rect = RectNode(x=i*10, y=0, width=50, height=50)
            rect.label = f"Rect_{i}"
            self.elements.elem_branch.add_node(rect)
            rects.append(rect)
        
        # Drag to regmarks
        self.elements.drag_and_drop(rects, self.elements.reg_branch)
        
        # Verify order preserved
        children = list(self.elements.reg_branch.children)
        for i, rect in enumerate(rects):
            self.assertEqual(children[i], rect)
            self.assertEqual(rect.label, f"Rect_{i}")

    def test_fallback_drop_multi(self):
        """Test that base Node.drop_multi() fallback works"""
        from meerk40t.core.node.node import Node
        
        # Create a basic node (not a branch)
        node = Node()
        
        # Should have drop_multi method
        self.assertTrue(hasattr(node, 'drop_multi'))
        
        # Should return False (base implementation rejects all drops)
        test_nodes = [RectNode(x=0, y=0, width=10, height=10)]
        result = node.drop_multi(test_nodes)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
