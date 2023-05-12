import unittest
from test import bootstrap

from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_MIL
from meerk40t.svgelements import Circle, Rect


class TestElements(unittest.TestCase):
    def test_elements_type(self):
        """
        Tests some generic elements commands and validates output as correct type
        """
        kernel = bootstrap.bootstrap()

        @kernel.console_command("validate_type", input_type="elements")
        def validation_type(command, data=None, **kwargs):
            for node in data:
                self.assertTrue(isinstance(node, Node))

        try:
            for cmd, path, command in kernel.find("command/elements.*"):
                kernel.console(
                    "element* " + command.split("/")[-1] + " validate_type\n"
                )
        finally:
            kernel.shutdown()

    def test_elements_specific(self):
        """
        Tests specific elements for correct non-failure.
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel.console("polyline grid 3 3\n")
            kernel.console("polyline 3cm 3cm  2cm 2cm 1cm 1cm grid 3 3\n")
            kernel.console("circle 2cm 2cm 1cm grid 3 3\n")
            kernel.console("rect 2cm 2cm 1cm 1cm grid 3 3\n")
            kernel.console("ellipse 2cm 2cm 1cm 1cm grid 3 3\n")
            kernel.console("line 2cm 2cm 1cm 1cm grid 3 3\n")
        finally:
            kernel.shutdown()

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
                shape = node.shape
                self.assertEqual(
                    shape,
                    Circle(
                        center=(1000 * UNITS_PER_MIL, 1000 * UNITS_PER_MIL),
                        r=1000 * UNITS_PER_MIL,
                        stroke_width=shape.stroke_width,
                        fill=shape.fill,
                        stroke=shape.stroke,
                    ),
                )
                self.assertEqual(node.stroke, "blue")
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
                shape = node.shape
                self.assertEqual(
                    shape,
                    Rect(
                        1000 * UNITS_PER_MIL,
                        1000 * UNITS_PER_MIL,
                        1000 * UNITS_PER_MIL,
                        1000 * UNITS_PER_MIL,
                        stroke_width=shape.stroke_width,
                        fill=shape.fill,
                        stroke=shape.stroke,
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

    def test_elements_bad_grid(self):
        """
        Intro test for elements

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            kernel_root("shape 5 2in 2in 1in\n")
            kernel_root("grid 2 2 1in 1foo\n")
        finally:
            kernel.shutdown()
