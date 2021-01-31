from __future__ import print_function

import unittest

from meerk40t.kernel import Kernel
from meerk40t.svgelements import Circle, Path, Rect


class TestElements(unittest.TestCase):
    def test_elements_circle(self):
        """
        Intro test for elements

        :return:
        """
        kernel = Kernel("MeerK40t", "testing", "MeerK40t", '')
        bootstrap(kernel)
        kernel_root = kernel.get_context("/")
        kernel_root.activate("modifier/Elemental")
        kernel_root.setting(int, "bed_width", 310)
        kernel_root.setting(int, "bed_height", 210)
        kernel_root.console("circle 1in 1in 1in\n")
        for element in kernel_root.elements.elems():
            self.assertEqual(element, Path(Circle(center=(1000, 1000), r=1000)))

    def test_elements_rect(self):
        """
        Intro test for elements

        :return:
        """
        kernel = Kernel("MeerK40t", "testing", "MeerK40t", '')
        bootstrap(kernel)
        kernel_root = kernel.get_context("/")
        kernel_root.activate("modifier/Elemental")
        kernel_root.setting(int, "bed_width", 310)
        kernel_root.setting(int, "bed_height", 210)
        kernel_root.console("rect 1in 1in 1in 1in -s red -f blue\n")
        for element in kernel_root.elements.elems():
            self.assertEqual(element, Path(Rect(1000, 1000, 1000, 1000, stroke="red")))
            self.assertEqual(element.stroke, "red")
            self.assertEqual(element.fill, "blue")
