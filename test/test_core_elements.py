from __future__ import print_function

import unittest

from meerk40t.kernel import Kernel
from meerk40t.svgelements import Circle, Path, Rect
from test import bootstrap


class TestElements(unittest.TestCase):
    def test_elements_circle(self):
        """
        Intro test for elements

        :return:
        """
        kernel = bootstrap.bootstrap()
        kernel_root = kernel.get_context("/")
        kernel_root.activate("modifier/Elemental")
        kernel_root.setting(int, "bed_width", 310)
        kernel_root.setting(int, "bed_height", 210)
        kernel_root.console("circle 1in 1in 1in\n")
        for element in kernel_root.elements.elems():
            print(element)
            self.assertEqual(element, Circle(center=(1000, 1000), r=1000, stroke="black"))

    def test_elements_rect(self):
        """
        Intro test for elements

        :return:
        """
        kernel = bootstrap.bootstrap()
        kernel_root = kernel.get_context("/")
        kernel_root.console("rect 1in 1in 1in 1in stroke red fill blue\n")
        for element in kernel_root.elements.elems():
            self.assertEqual(element, Rect(1000, 1000, 1000, 1000, stroke="red", fill="blue"))
            self.assertEqual(element.stroke, "red")
            self.assertEqual(element.fill, "blue")
