import unittest
from test.bootstrap import bootstrap, destroy


class TestElementsCache(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        destroy(self.kernel)

    def test_cache_invalidated_on_fast_add(self):
        # Ensure a known baseline
        with self.elements.node_lock:
            self.elements.clear_elements(fast=True)
            self.elements._elems_cache = None
            # create initial nodes
            for i in range(3):
                self.elements.elem_branch.add(type="elem path")
        # Build cache
        _ = list(self.elements.elems())
        self.assertIsNotNone(self.elements._elems_cache)
        initial_count = len(list(self.elements.elems()))

        # Add with fast=True -> should invalidate cache
        with self.elements.node_lock:
            self.elements.elem_branch.add(type="elem path", fast=True)
        # After fast add, cache should be invalidated (None)
        self.assertIsNone(self.elements._elems_cache)
        # And elems should include the new node
        after_count = len(list(self.elements.elems()))
        self.assertEqual(after_count, initial_count + 1)

    def test_cache_invalidated_on_fast_remove(self):
        with self.elements.node_lock:
            self.elements.clear_elements(fast=True)
            self.elements._elems_cache = None
            for i in range(10):
                self.elements.elem_branch.add(type="elem path")
        # Build cache
        _ = list(self.elements.elems())
        self.assertIsNotNone(self.elements._elems_cache)

        # Remove all children with fast=True
        with self.elements.node_lock:
            self.elements.clear_elements(fast=True)
        # Cache should be invalidated
        self.assertIsNone(self.elements._elems_cache)
        self.assertEqual(len(list(self.elements.elems())), 0)

    def test_flat_tracker_and_cache(self):
        # Use elements-level flat tracker
        self.elements.flat_tracker.reset()
        with self.elements.node_lock:
            self.elements.clear_elements(fast=True)
            for i in range(50):
                self.elements.elem_branch.add(type="elem path")
        # First build should call flat
        _ = list(self.elements.elems())
        first_calls = self.elements.flat_tracker.get()
        self.assertGreater(first_calls, 0)
        # Repeated calls should not call flat because cache is used
        _ = list(self.elements.elems())
        second_calls = self.elements.flat_tracker.get()
        self.assertEqual(first_calls, second_calls)

    def test_ops_cache_invalidated_on_clear(self):
        with self.elements.node_lock:
            self.elements.clear_operations(fast=True)
            self.elements._ops_cache = None
            # Add a couple operations
            from meerk40t.core.node.node import Node
            for i in range(5):
                op = Node().create(type="op cut")
                self.elements.op_branch.add_node(op)
        # Build ops cache
        _ = list(self.elements.ops())
        self.assertIsNotNone(self.elements._ops_cache)
        # Clear with fast=True should invalidate ops cache
        self.elements.clear_operations(fast=True)
        self.assertIsNone(self.elements._ops_cache)

    def test_append_children_fast_invalidates_cache(self):
        with self.elements.node_lock:
            self.elements.clear_elements(fast=True)
            self.elements._elems_cache = None
            # Prepare three nodes
            nodes = []
            for i in range(3):
                nodes.append(self.elements.elem_branch.add(type="elem path"))
            # Build cache
            _ = list(self.elements.elems())
            self.assertIsNotNone(self.elements._elems_cache)
            # Create group and append children with fast=True
            group = self.elements.elem_branch.add(type="group")
            group.append_children(list(nodes), fast=True)
        self.assertIsNone(self.elements._elems_cache)

    def test_flat_stats_console_command(self):
        # Use elements-level flat tracker
        self.elements.flat_tracker.reset()
        # Trigger some flats
        with self.elements.node_lock:
            for i in range(10):
                self.elements.elem_branch.add(type="elem path")
        _ = list(self.elements.elems())
        # Ensure counter increased
        self.assertGreater(self.elements.flat_tracker.get(), 0)
        # Call console command to reset
        self.kernel.console("flat-stats reset\n")
        self.assertEqual(self.elements.flat_tracker.get(), 0)


if __name__ == "__main__":
    unittest.main()
