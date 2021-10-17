import unittest
from math import floor, ceil

from PIL import Image, ImageDraw

from meerk40t.image.actualize import actualize
from meerk40t.svgelements import SVGImage, Matrix
from test import bootstrap


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
            svg_image = SVGImage()
            svg_image.image = Image.new("RGBA", (256, 256), "white")
            draw = ImageDraw.Draw(svg_image.image)
            draw.ellipse((100, 100, 105, 105), "black")
            node = kernel_root.elements.add_elem(svg_image)
            node.emphasized = True
            kernel_root("image resample\n")
            for element in kernel_root.elements.elems():
                if isinstance(element, SVGImage):
                    self.assertEqual(element.image.size, (6, 6))
                    self.assertEqual(element.transform.value_trans_x(), 100)
                    self.assertEqual(element.transform.value_trans_y(), 100)
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
            svg_image = SVGImage()
            svg_image.image = Image.new("RGBA", (256, 256), "white")
            svg_image.values["raster_step"] = 3
            draw = ImageDraw.Draw(svg_image.image)
            draw.ellipse((100, 100, 105, 105), "black")
            node = kernel_root.elements.add_elem(svg_image)
            node.emphasized = True
            kernel_root("image resample\n")
            for element in kernel_root.elements.elems():
                if isinstance(element, SVGImage):
                    self.assertEqual(
                        element.image.size,
                        (
                            6 / svg_image.values["raster_step"],
                            6 / svg_image.values["raster_step"],
                        ),
                    )
                    self.assertEqual(
                        element.transform.value_scale_x(),
                        svg_image.values["raster_step"],
                    )
                    self.assertEqual(
                        element.transform.value_scale_y(),
                        svg_image.values["raster_step"],
                    )
                    self.assertEqual(element.transform.value_trans_x(), 100)
                    self.assertEqual(element.transform.value_trans_y(), 100)
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
                svg_image = SVGImage()
                # each color is a different shade of gray, all marked fully transparent.
                svg_image.image = Image.new("RGBA", (256, 256), (component, component, component, 0))
                svg_image.values["raster_step"] = 3
                draw = ImageDraw.Draw(svg_image.image)
                draw.ellipse((50, 50, 150, 150), "white")
                draw.ellipse((100, 100, 105, 105), "black")
                node = kernel_root.elements.add_elem(svg_image)
                node.emphasized = True
            kernel_root("image resample\n")
            for element in kernel_root.elements.elems():
                if isinstance(element, SVGImage):
                    self.assertEqual(
                        element.image.size,
                        (
                            6 / svg_image.values["raster_step"],
                            6 / svg_image.values["raster_step"],
                        ),
                    )
                    self.assertEqual(
                        element.transform.value_scale_x(),
                        svg_image.values["raster_step"],
                    )
                    self.assertEqual(
                        element.transform.value_scale_y(),
                        svg_image.values["raster_step"],
                    )
                    self.assertEqual(element.transform.value_trans_x(), 100)
                    self.assertEqual(element.transform.value_trans_y(), 100)
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
                svg_image = SVGImage()
                # each color is a different shade of gray, all marked fully transparent.
                svg_image.image = Image.new("RGBA", (256, 256), (component, component, component, 0))
                svg_image.values["raster_step"] = 3
                draw = ImageDraw.Draw(svg_image.image)
                draw.ellipse((50, 50, 150, 150), "black")
                draw.ellipse((100, 100, 105, 105), "white")
                node = kernel_root.elements.add_elem(svg_image)
                node.emphasized = True
            kernel_root("image resample\n")
            for element in kernel_root.elements.elems():
                if isinstance(element, SVGImage):
                    self.assertEqual(
                        element.image.size,
                        (
                            ceil(101 / svg_image.values["raster_step"]),
                            ceil(101 / svg_image.values["raster_step"]),
                        ),
                    )
                    self.assertEqual(
                        element.transform.value_scale_x(),
                        svg_image.values["raster_step"],
                    )
                    self.assertEqual(
                        element.transform.value_scale_y(),
                        svg_image.values["raster_step"],
                    )
                    self.assertEqual(element.transform.value_trans_x(), 50)
                    self.assertEqual(element.transform.value_trans_y(), 50)
                    # Test corner for whiteness.
                    self.assertEqual(element.image.getpixel((-1, -1)), 255)
        finally:
            kernel.shutdown()

    def test_actualize_circle_step3_direct_transparent(self):
        """
        Test for edge pixel error. White empty.

        :return:
        """
        for component in range(256):
            image = Image.new("RGBA", (256, 256), (component, component, component,0))
            draw = ImageDraw.Draw(image)
            draw.ellipse((100, 100, 150, 150), "black")

            for step in range(1, 20):
                transform = Matrix()
                actual, transform = actualize(image, transform, step_level=step, crop=False)
                self.assertEqual(actual.getpixel((-1, -1)), 255)

    def test_actualize_circle_step3_direct_white(self):
        """
        Test for edge pixel error. White empty.

        :return:
        """
        image = Image.new("RGBA", (256, 256), "white")
        draw = ImageDraw.Draw(image)
        draw.ellipse((100, 100, 150, 150), "black")

        for step in range(1, 20):
            transform = Matrix()
            actual, transform = actualize(image, transform, step_level=step, crop=False)
            self.assertEqual(actual.getpixel((-1, -1)), 255)

    def test_actualize_circle_step3_direct_black(self):
        """
        Test for edge pixel error. Black Empty.

        :return:
        """
        image = Image.new("RGBA", (256, 256), "black")
        draw = ImageDraw.Draw(image)
        draw.ellipse((100, 100, 150, 150), "white")

        for step in range(1, 20):
            transform = Matrix()
            actual, transform = actualize(image, transform, step_level=step, crop=False, inverted=True)
            self.assertEqual(actual.getpixel((-1, -1)), 0)

        # Note: inverted flag not set. White edge pixel is correct.
        actual, transform = actualize(image, Matrix(), step_level=3, crop=False)
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
            svg_image = SVGImage()
            svg_image.image = Image.new("RGBA", (256, 256), "white")
            draw = ImageDraw.Draw(svg_image.image)
            draw.ellipse((0, 0, 256, 256), "black")
            node = kernel_root.elements.add_elem(svg_image)
            node.emphasized = True
            kernel_root("image resample\n")
            for element in kernel_root.elements.elems():
                if isinstance(element, SVGImage):
                    self.assertEqual(element.image.size, (256, 256))
                    self.assertEqual(element.transform.value_trans_x(), 0)
                    self.assertEqual(element.transform.value_trans_y(), 0)
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
            svg_image = SVGImage()
            svg_image.image = Image.new("RGBA", (256, 256), "white")
            node = kernel_root.elements.add_elem(svg_image)
            node.emphasized = True
            kernel_root("image resample\n")
            for element in kernel_root.elements.elems():
                if isinstance(element, SVGImage):
                    self.assertEqual(element.image.size, (256, 256))
                    self.assertEqual(element.transform.value_trans_x(), 0)
                    self.assertEqual(element.transform.value_trans_y(), 0)
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
            svg_image = SVGImage()
            svg_image.image = Image.new("RGBA", (256, 256), "black")
            node = kernel_root.elements.add_elem(svg_image)
            node.emphasized = True
            kernel_root("image resample\n")
            for element in kernel_root.elements.elems():
                if isinstance(element, SVGImage):
                    self.assertEqual(element.image.size, (256, 256))
                    self.assertEqual(element.transform.value_trans_x(), 0)
                    self.assertEqual(element.transform.value_trans_y(), 0)
        finally:
            kernel.shutdown()
