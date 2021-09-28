
import unittest

from meerk40t.svgelements import Circle, Rect
from test import bootstrap


class TestElements(unittest.TestCase):
    def test_elements_circle(self):
        """
        Intro test for elements

        :return:
        """
        kernel = bootstrap.bootstrap()
        kernel_root = kernel.get_context("/")
        kernel_root("circle 1in 1in 1in\n")
        for element in kernel_root.elements.elems():
            print(element)
            self.assertEqual(element, Circle(center=(1000, 1000), r=1000, stroke="black"))
        kernel.shutdown()

    def test_elements_rect(self):
        """
        Intro test for elements

        :return:
        """
        kernel = bootstrap.bootstrap()
        kernel_root = kernel.get_context("/")
        kernel_root("rect 1in 1in 1in 1in stroke red fill blue\n")
        for element in kernel_root.elements.elems():
            self.assertEqual(element, Rect(1000, 1000, 1000, 1000, stroke="red", fill="blue"))
            self.assertEqual(element.stroke, "red")
            self.assertEqual(element.fill, "blue")
        kernel.shutdown()
