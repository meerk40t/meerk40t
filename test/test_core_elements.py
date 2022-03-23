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
            for element in kernel_root.elements.elems():
                # print(element)
                self.assertEqual(
                    element,
                    Circle(
                        center=(1000 * UNITS_PER_MIL, 1000 * UNITS_PER_MIL),
                        r=1000 * UNITS_PER_MIL,
                        stroke="black",
                    ),
                )
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
            for element in kernel_root.elements.elems():
                self.assertEqual(
                    element,
                    Rect(
                        1000 * UNITS_PER_MIL,
                        1000 * UNITS_PER_MIL,
                        1000 * UNITS_PER_MIL,
                        1000 * UNITS_PER_MIL,
                        stroke="red",
                        fill="blue",
                    ),
                )
                self.assertEqual(element.stroke, "red")
                self.assertEqual(element.fill, "blue")
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
