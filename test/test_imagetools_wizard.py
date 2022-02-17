import unittest
from math import floor
from test import bootstrap

from PIL import Image, ImageDraw

from meerk40t.svgelements import SVGImage


class TestRasterWizard(unittest.TestCase):
    def test_rasterwizard_smallcircle(self):
        """
        Test that a small circle in an image wizards correctly

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
            kernel_root("image wizard Gravy\n")
            for element in kernel_root.elements.elems():
                if isinstance(element, SVGImage):
                    self.assertEqual(
                        element.image.size, (2, 2)
                    )  # Gravy is step=3 by default
                    self.assertEqual(element.transform.value_trans_x(), 100)
                    self.assertEqual(element.transform.value_trans_y(), 100)
        finally:
            kernel.shutdown()

    def test_rasterwizard_smallcircle_step3(self):
        """
        Test that a small circle in an image wizards correctly

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
            kernel_root("image wizard Gravy\n")
            for element in kernel_root.elements.elems():
                if isinstance(element, SVGImage):
                    self.assertEqual(
                        element.image.size, (2, 2)
                    )  # Gravy is step=3 by default
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

    def test_rasterwizard_image_types(self):
        """
        Test that different images modes work without error.

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            # kernel_root("channel print console\n")
            for script in kernel.match("raster_script/.*", suffix=True):
                for mode in ("RGBA", "RGB", "L", "1", "P", "F", "LA", "HSV"):
                    svg_image = SVGImage()
                    svg_image.image = Image.new("RGBA", (256, 256), "white")
                    draw = ImageDraw.Draw(svg_image.image)
                    draw.ellipse((50, 50, 150, 150), "black")
                    draw.ellipse((75, 75, 125, 125), "blue")
                    draw.ellipse((95, 95, 105, 105), "green")
                    svg_image.image = svg_image.image.convert(mode)
                    node = kernel_root.elements.add_elem(svg_image)
                    node.emphasized = True
                kernel_root("image wizard %s\n" % script)
                # Solve for step.
                step = 1
                for op in kernel_root.registered["raster_script/%s" % script]:
                    if op["name"] == "resample" and op["enable"]:
                        step = op["step"]
                for element in kernel_root.elements.elems():
                    if isinstance(element, SVGImage):
                        self.assertEqual(
                            element.transform.value_scale_x(),
                            step,
                        )
                        self.assertEqual(
                            element.transform.value_scale_y(),
                            step,
                        )
                        self.assertEqual(element.transform.value_trans_x(), 50)
                        self.assertEqual(element.transform.value_trans_y(), 50)
                kernel_root("element* delete\n")
        finally:
            kernel.shutdown()

    def test_rasterwizard_transparent_colorvalue_wb(self):
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
                svg_image.image = Image.new(
                    "RGBA", (256, 256), (component, component, component, 0)
                )
                svg_image.values["raster_step"] = 3
                draw = ImageDraw.Draw(svg_image.image)
                draw.rectangle((50, 50, 150, 150), "white")
                draw.ellipse((100, 100, 105, 105), "black")
                node = kernel_root.elements.add_elem(svg_image)
                node.emphasized = True
            kernel_root("image wizard Gravy\n")
            for element in kernel_root.elements.elems():
                if isinstance(element, SVGImage):
                    self.assertEqual(
                        element.image.size, (2, 2)
                    )  # Gravy is step=3 by default
                    self.assertEqual(
                        element.transform.value_scale_x(),
                        3,
                    )
                    self.assertEqual(
                        element.transform.value_scale_y(),
                        3,
                    )
                    self.assertEqual(element.transform.value_trans_x(), 100)
                    self.assertEqual(element.transform.value_trans_y(), 100)
        finally:
            kernel.shutdown()

    def test_rasterwizard_transparent_colorvalue_bw(self):
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
                svg_image.image = Image.new(
                    "RGBA", (256, 256), (component, component, component, 0)
                )
                svg_image.values["raster_step"] = 3
                draw = ImageDraw.Draw(svg_image.image)
                draw.ellipse((50, 50, 150, 150), "black")
                draw.ellipse((100, 100, 105, 105), "white")
                node = kernel_root.elements.add_elem(svg_image)
                node.emphasized = True
            kernel_root("image wizard Gravy\n")
            for element in kernel_root.elements.elems():
                if isinstance(element, SVGImage):
                    self.assertEqual(
                        element.image.size, (34, 34)
                    )  # Gravy is step=3 by default
                    self.assertEqual(
                        element.transform.value_scale_x(),
                        3,
                    )
                    self.assertEqual(
                        element.transform.value_scale_y(),
                        3,
                    )
                    self.assertEqual(element.transform.value_trans_x(), 50)
                    self.assertEqual(element.transform.value_trans_y(), 50)
                    #  Test corner for whiteness.
                    self.assertEqual(element.image.getpixel((-1, -1)), 255)
        finally:
            kernel.shutdown()

    def test_rasterwizard_purewhite(self):
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
            kernel_root("image wizard Gravy\n")
            for element in kernel_root.elements.elems():
                if isinstance(element, SVGImage):
                    self.assertEqual(
                        element.image.size, (floor(256 / 3) + 1, floor(256 / 3) + 1)
                    )
                    # Gravy is default 3 step.
                    # Remainder line is added to edge, so + 1
                    self.assertEqual(element.transform.value_trans_x(), 0)
                    self.assertEqual(element.transform.value_trans_y(), 0)
        finally:
            kernel.shutdown()

    def test_rasterwizard_pureblack(self):
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
            kernel_root("image wizard Gravy\n")
            for element in kernel_root.elements.elems():
                if isinstance(element, SVGImage):
                    self.assertEqual(
                        element.image.size, (floor(256 / 3), floor(256 / 3))
                    )
                    # Gravy is default 3 step.
                    # Default non-inverted gives white line at edge which is cropped, therefore floor()
                    # since the additional line does not count as part of the image.
                    self.assertEqual(element.transform.value_trans_x(), 0)
                    self.assertEqual(element.transform.value_trans_y(), 0)
        finally:
            kernel.shutdown()
