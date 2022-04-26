import unittest
from test import bootstrap

from meerk40t.core.units import UNITS_PER_MIL
from meerk40t.svgelements import Circle, Rect


class TestElements(unittest.TestCase):
    def test_elements_circle(self):
        """
        Intro test for elements

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            kernel_root("circle 1in 1in 1in\n")
            for node in kernel_root.elements.elems():
                # print(element)
                self.assertEqual(
                    node.shape,
                    Circle(
                        center=(1000 * UNITS_PER_MIL, 1000 * UNITS_PER_MIL),
                        r=1000 * UNITS_PER_MIL,
                    ),
                )
                self.assertEqual(node.stroke, "black")
        finally:
            kernel.shutdown()

    def test_elements_rect(self):
        """
        Intro test for elements

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            kernel_root("rect 1in 1in 1in 1in stroke red fill blue\n")
            for node in kernel_root.elements.elems():
                self.assertEqual(
                    node.shape,
                    Rect(
                        1000 * UNITS_PER_MIL,
                        1000 * UNITS_PER_MIL,
                        1000 * UNITS_PER_MIL,
                        1000 * UNITS_PER_MIL,
                    ),
                )
                self.assertEqual(node.stroke, "red")
                self.assertEqual(node.fill, "blue")
        finally:
            kernel.shutdown()

    def test_elements_clipboard(self):
        """
        Intro test for elements

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            kernel_root("rect 1in 1in 1in 1in stroke red fill blue\n")
            kernel_root("clipboard copy\n")
            kernel_root("clipboard paste -xy 2in 2in\n")
            kernel_root("grid 2 4\n")
        finally:
            kernel.shutdown()

    def test_elements_shapes(self):
        """
        Intro test for elements

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            kernel_root("shape 5 2in 2in 1in\n")
            # kernel_root("polygon 1in 1in 2in 2in 0in 4cm\n")

        finally:
            kernel.shutdown()
