import os
import unittest

from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.units import Length
from test import bootstrap

class TestFileSVG(unittest.TestCase):

    def test_load_save_svg(self):
        """
        test svg saving and loading of various files.
        """
        file1 = "test.svg"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("operation* delete\n")
            node = EngraveOpNode(
                id="E1",
                label="My label",
                color="green",
                lock=True,
                allowed_attributes=["number_of_unicorns"],
                stroke="green",
                fill="gray",
                stroke_width=7,
                dancing_bear=0.2,
            )
            kernel.elements.op_branch.add_node(node)
            kernel.console(f"rect 2cm 2cm 1cm 1cm engrave -s 15\n")
            kernel.console(f"save {file1}\n")
            kernel.console("element* delete\n")
            kernel.console("operation* delete\n")
            kernel.console(f"load {file1}\n")
            f = list(kernel.elements.elem_branch.flat(types="elem rect"))[0]
            self.assertEqual(f.width, float(Length("1cm")))

            ns = list(kernel.elements.op_branch.flat(types="op engrave"))
            node_copy = ns[0]
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
            print(f)

        finally:
            kernel.shutdown()

    def test_load_save_svg_int_id(self):
        """
        tests that the validation of id prevents integer value.
        """
        file1 = "test.svg"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("operation* delete\n")
            node = EngraveOpNode(id="1", label="1")
            kernel.elements.op_branch.add_node(node)
            kernel.console(f"save {file1}\n")
            kernel.console("operation* delete\n")
            kernel.console(f"load {file1}\n")
            node_copy = list(kernel.elements.op_branch.flat(types="op engrave"))[0]
            self.assertEqual(node_copy.id, node.id)
            self.assertEqual(node_copy.label, node.label)
        finally:
            kernel.shutdown()
