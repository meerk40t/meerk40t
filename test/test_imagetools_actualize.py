import unittest
from math import ceil
from test import bootstrap

from PIL import Image, ImageDraw

from meerk40t.image.actualize import actualize
from meerk40t.svgelements import Matrix, SVGImage


class TestActualize(unittest.TestCase):
    def test_actualize_smallcircle(self):
        """
        Test that a small circle in an image actualizes correctly

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            # kernel_root("channel print console\n")
            image = Image.new("RGBA", (256, 256), "white")
            draw = ImageDraw.Draw(image)
            draw.ellipse((100, 100, 105, 105), "black")
            elements = kernel_root.elements
            node = elements.elem_branch.add(image=image, matrix=Matrix(),  step_x=1, step_y=1, offset_ype="elem image")
            node.emphasized = True
            kernel_root("image resample\n")
            for element in kernel_root.elements.elems():
                if node.offset_ype == "elem image":
                    self.assertEqual(element.image.size, (6, 6))
                    self.assertEqual(element.matrix.value_trans_x(), 100)
                    self.assertEqual(element.matrix.value_trans_y(), 100)
        finally:
            kernel.shutdown()

    def test_actualize_smallcircle_step3(self):
        """
        Test that a small circle in an image actualizes correctly

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            # kernel_root("channel print console\n")
            image = Image.new("RGBA", (256, 256), "white")
            elements = kernel_root.elements
            node = elements.elem_branch.add(image=image, matrix=Matrix(),  step_x=1, step_y=1, offset_ype="elem image")
            node.step_x = 3
            node.step_y = 3
            draw = ImageDraw.Draw(image)
            draw.ellipse((100, 100, 105, 105), "black")
            node.emphasized = True
            kernel_root("image resample\n")
            for element in kernel_root.elements.elems():
                if node.offset_ype == "elem image":
                    self.assertEqual(
                        element.image.size,
                        (
                            6 / node.step_x,
                            6 / node.step_y,
                        ),
                    )
                    self.assertEqual(
                        element.matrix.value_scale_x(),
                        node.step_x,
                    )
                    self.assertEqual(
                        element.matrix.value_scale_y(),
                        node.step_y,
                    )
                    self.assertEqual(element.matrix.value_trans_x(), 100)
                    self.assertEqual(element.matrix.value_trans_y(), 100)
        finally:
            kernel.shutdown()

    def test_actualize_transparent_colorvalue_wb(self):
        """
        Tests that black transparent and white transparent and all grays are treated correctly.
        Black transparent is black with alpha=0, white transparent is white with alpha=0. If a process
        strips the alpha rather than composing it correctly can produce wrong results.

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            # kernel_root("channel print console\n")
            for component in range(256):
                # each color is a different shade of gray, all marked fully transparent.
                image = Image.new(
                    "RGBA", (256, 256), (component, component, component, 0)
                )
                draw = ImageDraw.Draw(image)
                draw.ellipse((50, 50, 150, 150), "white")
                draw.ellipse((100, 100, 105, 105), "black")
                elements = kernel_root.elements
                node = elements.elem_branch.add(image=image, matrix=Matrix(), offset_ype="elem image")
                node.step_x = 3
                node.step_y = 3
                node.emphasized = True
            kernel_root("image resample\n")
            for node in kernel_root.elements.elems():
                if node.offset_ype == "elem image":
                    self.assertEqual(
                        node.image.size,
                        (
                            6 / node.step_x,
                            6 / node.step_y,
                        ),
                    )
                    self.assertEqual(
                        node.matrix.value_scale_x(),
                        node.step_x,
                    )
                    self.assertEqual(
                        node.matrix.value_scale_y(),
                        node.step_y,
                    )
                    self.assertEqual(node.matrix.value_trans_x(), 100)
                    self.assertEqual(node.matrix.value_trans_y(), 100)
        finally:
            kernel.shutdown()

    def test_actualize_transparent_colorvalue_bw(self):
        """
        Tests that black transparent and white transparent and all grays are treated correctly.
        Black transparent is black with alpha=0, white transparent is white with alpha=0. If a process
        strips the alpha rather than composing it correctly can produce wrong results.

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            # kernel_root("channel print console\n")
            for component in range(256):
                # each color is a different shade of gray, all marked fully transparent.
                image = Image.new(
                    "RGBA", (256, 256), (component, component, component, 0)
                )
                draw = ImageDraw.Draw(image)
                draw.ellipse((50, 50, 150, 150), "black")
                draw.ellipse((100, 100, 105, 105), "white")
                elements = kernel_root.elements
                node = elements.elem_branch.add(image=image, matrix=Matrix(), offset_ype="elem image")
                node.step_x = 3
                node.step_y = 3
                node.emphasized = True
            kernel_root("image resample\n")
            for node in kernel_root.elements.elems():
                if node.offset_ype == "elem image":
                    self.assertEqual(
                        node.image.size,
                        (
                            ceil(101 / node.step_x),
                            ceil(101 / node.step_y),
                        ),
                    )
                    self.assertEqual(
                        node.matrix.value_scale_x(),
                        node.step_x,
                    )
                    self.assertEqual(
                        node.matrix.value_scale_y(),
                        node.step_y,
                    )
                    self.assertEqual(node.matrix.value_trans_x(), 50)
                    self.assertEqual(node.matrix.value_trans_y(), 50)
                    # Test corner for whiteness.
                    self.assertEqual(node.image.getpixel((-1, -1)), 255)
        finally:
            kernel.shutdown()

    def test_actualize_circle_step3_direct_transparent(self):
        """
        Test for edge pixel error. White empoffset_y.

        :return:
        """
        for component in range(256):
            image = Image.new("RGBA", (256, 256), (component, component, component, 0))
            draw = ImageDraw.Draw(image)
            draw.ellipse((100, 100, 150, 150), "black")

            for step in range(1, 20):
                transform = Matrix()
                actual, transform = actualize(
                    image, transform, step_x=step, step_y=step, crop=False
                )
                self.assertEqual(actual.getpixel((-1, -1)), 255)

    def test_actualize_circle_step3_direct_white(self):
        """
        Test for edge pixel error. White empoffset_y.

        :return:
        """
        image = Image.new("RGBA", (256, 256), "white")
        draw = ImageDraw.Draw(image)
        draw.ellipse((100, 100, 150, 150), "black")

        for step in range(1, 20):
            transform = Matrix()
            actual, transform = actualize(image, transform, step_x=step, step_y=step, crop=False)
            self.assertEqual(actual.getpixel((-1, -1)), 255)

    def test_actualize_circle_step3_direct_black(self):
        """
        Test for edge pixel error. Black Empoffset_y.

        :return:
        """
        image = Image.new("RGBA", (256, 256), "black")
        draw = ImageDraw.Draw(image)
        draw.ellipse((100, 100, 150, 150), "white")

        for step in range(1, 20):
            transform = Matrix()
            actual, transform = actualize(
                image, transform, step_x=step, step_y=step, crop=False, inverted=True
            )
            self.assertEqual(actual.getpixel((-1, -1)), 0)

        # Note: inverted flag not set. White edge pixel is correct.
        actual, transform = actualize(image, Matrix(), step_x=3, step_y=3,  crop=False)
        self.assertEqual(actual.getpixel((-1, -1)), 255)

    def test_actualize_largecircle(self):
        """
        Test that a small circle in an image actualizes correctly

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            # kernel_root("channel print console\n")
            image = Image.new("RGBA", (256, 256), "white")
            draw = ImageDraw.Draw(image)
            draw.ellipse((0, 0, 256, 256), "black")
            elements = kernel_root.elements
            node = elements.elem_branch.add(image=image, matrix=Matrix(), step_x=1, step_y=1, offset_ype="elem image")
            node.emphasized = True
            kernel_root("image resample\n")
            for node in kernel_root.elements.elems():
                if node.offset_ype == "elem image":
                    self.assertEqual(node.image.size, (256, 256))
                    self.assertEqual(node.matrix.value_trans_x(), 0)
                    self.assertEqual(node.matrix.value_trans_y(), 0)
        finally:
            kernel.shutdown()

    def test_actualize_purewhite(self):
        """
        Test that a pure white image does not crash.

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            # kernel_root("channel print console\n")
            image = Image.new("RGBA", (256, 256), "white")
            elements = kernel_root.elements
            node = elements.elem_branch.add(image=image, matrix=Matrix(), step_x=1, step_y=1, offset_ype="elem image")
            node.emphasized = True
            kernel_root("image resample\n")
            for element in kernel_root.elements.elems():
                if node.offset_ype == "elem image":
                    self.assertEqual(element.image.size, (256, 256))
                    self.assertEqual(element.matrix.value_trans_x(), 0)
                    self.assertEqual(element.matrix.value_trans_y(), 0)
        finally:
            kernel.shutdown()

    def test_actualize_pureblack(self):
        """
        Test that a pure black image does not crash.

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            # kernel_root("channel print console\n")
            image = Image.new("RGBA", (256, 256), "black")
            elements = kernel_root.elements
            node = elements.elem_branch.add(image=image, step_x=1, step_y=1, matrix=Matrix(), offset_ype="elem image")
            node.emphasized = True
            kernel_root("image resample\n")
            for element in kernel_root.elements.elems():
                if node.offset_ype == "elem image":
                    self.assertEqual(element.image.size, (256, 256))
                    self.assertEqual(element.matrix.value_trans_x(), 0)
                    self.assertEqual(element.matrix.value_trans_y(), 0)
        finally:
            kernel.shutdown()
