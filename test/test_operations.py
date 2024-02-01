import unittest
from copy import copy
from test import bootstrap

from meerk40t.core.node.op_cut import CutOpNode
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.node.op_image import ImageOpNode
from meerk40t.core.node.op_raster import RasterOpNode
from meerk40t.core.node.rootnode import RootNode


class TestOperations(unittest.TestCase):
    def test_operation_copy_engrave(self):
        """
        Test code to ensure operations copy correctly

        :return:
        """
        node = EngraveOpNode(
            id="fake_id",
            label="My label",
            color="green",
            lock=True,
            allowed_attributes=["number_of_unicorns"],
            stroke="green",
            fill="gray",
            stroke_width=7,
            dancing_bear=0.2,
        )
        node_copy = copy(node)
        for attr in (
            "id",
            "label",
            "color",
            "lock",
            "allowed_attributes",
            "stroke",
            "fill",
            "stroke_width",
            "stroke_scaled",
        ):
            if hasattr(node, attr):
                self.assertEqual(getattr(node_copy, attr), getattr(node, attr))
        for item in node.settings:
            self.assertEqual(node.settings[item], node_copy.settings[item])

    def test_operation_copy_engrave_nodedict(self):
        """
        Test code to ensure operations copy correctly

        :return:
        """
        node = EngraveOpNode(
            id="fake_id",
            label="My label",
            color="green",
            lock=True,
            allowed_attributes=["number_of_unicorns"],
            stroke="green",
            fill="gray",
            stroke_width=7,
            dancing_bear=0.2,
            speed=30.0,
        )
        node.speed = 20.0
        node_copy = copy(node)
        self.assertEqual(node_copy.speed, 20.0)
        node_copy.speed = 100.0
        for attr in (
            "id",
            "label",
            "color",
            "lock",
            "allowed_attributes",
            "stroke",
            "fill",
            "stroke_width",
            "stroke_scaled",
        ):
            if hasattr(node, attr):
                self.assertEqual(getattr(node_copy, attr), getattr(node, attr))
        for item in node.settings:
            if item == "speed":
                continue
            self.assertEqual(node.settings[item], node_copy.settings[item])
        self.assertEqual(node_copy.speed, 100.0)
        self.assertEqual(node.speed, 20.0)

    def test_operation_copy_knockon(self):
        """
        Ensure test copy is not reusing the same data.

        :return:
        """
        node = EngraveOpNode(
            id="fake_id",
            label="My label",
            color="green",
            lock=True,
            allowed_attributes=["number_of_unicorns"],
            stroke="green",
            fill="gray",
            stroke_width=7,
            dancing_bear=0.2,
        )
        node_copy = copy(node)
        for item in node.settings:
            self.assertEqual(node.settings[item], node_copy.settings[item])
        node_copy.dancing_bear = 0.5
        self.assertNotEqual(node_copy.dancing_bear, node.dancing_bear)
        node_copy_copy = copy(node_copy)
        self.assertEqual(node_copy_copy.dancing_bear, node_copy.dancing_bear)
        node.allowed_attributes.append("Fancy pants")
        self.assertNotEqual(node_copy_copy.allowed_attributes, node.allowed_attributes)

    def test_operation_copy_root(self):
        """
        Ensure that copy, does not copy the root of the node (it's a copy of the node not in the tree).

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")

            root = RootNode(context=kernel_root, label="RootNode")
            node = EngraveOpNode(
                id="fake_id",
                label="My label",
                color="green",
                lock=True,
                allowed_attributes=["number_of_unicorns"],
                stroke="green",
                fill="gray",
                stroke_width=7,
                dancing_bear=0.2,
            )
            root.add_node(node)
            self.assertIs(root, node._root)

            node_copy = copy(node)
            self.assertIsNot(node_copy._root, root)

        finally:
            kernel()

    def test_operation_copy_cut(self):
        """
        Test code to ensure operations copy correctly

        :return:
        """
        node = CutOpNode(
            id="fake_id",
            label="My label",
            color="green",
            lock=True,
            allowed_attributes=["number_of_unicorns"],
            stroke="green",
            fill="gray",
            stroke_width=7,
            dancing_bear=0.2,
        )
        node_copy = copy(node)
        for attr in (
            "id",
            "label",
            "color",
            "lock",
            "allowed_attributes",
            "stroke",
            "fill",
            "stroke_width",
            "stroke_scaled",
        ):
            if hasattr(node, attr):
                self.assertEqual(getattr(node_copy, attr), getattr(node, attr))
        self.assertEqual(node_copy.settings["dancing_bear"], 0.2)
        for item in node.settings:
            self.assertEqual(node.settings[item], node_copy.settings[item])

    def test_operation_copy_image(self):
        """
        Test code to ensure operations copy correctly

        :return:
        """
        node = ImageOpNode(
            id="fake_id",
            label="My label",
            color="green",
            lock=True,
            allowed_attributes=["number_of_unicorns"],
            stroke="green",
            fill="gray",
            stroke_width=7,
            dancing_bear=0.2,
        )
        node_copy = copy(node)
        for attr in (
            "id",
            "label",
            "color",
            "lock",
            "allowed_attributes",
            "stroke",
            "fill",
            "stroke_width",
            "stroke_scaled",
        ):
            if hasattr(node, attr):
                self.assertEqual(getattr(node_copy, attr), getattr(node, attr))
        self.assertEqual(node_copy.settings["dancing_bear"], 0.2)
        for item in node.settings:
            self.assertEqual(node.settings[item], node_copy.settings[item])

    def test_operation_copy_raster(self):
        """
        Test code to ensure operations copy correctly

        :return:
        """
        node = RasterOpNode(
            id="fake_id",
            label="My label",
            color="green",
            lock=True,
            allowed_attributes=["number_of_unicorns"],
            stroke="green",
            fill="gray",
            stroke_width=7,
            dancing_bear=0.2,
        )
        node_copy = copy(node)
        for attr in (
            "id",
            "label",
            "color",
            "lock",
            "allowed_attributes",
            "stroke",
            "fill",
            "stroke_width",
            "stroke_scaled",
        ):
            if hasattr(node, attr):
                self.assertEqual(getattr(node_copy, attr), getattr(node, attr))
        self.assertEqual(node_copy.settings["dancing_bear"], 0.2)
        for item in node.settings:
            self.assertEqual(node.settings[item], node_copy.settings[item])
