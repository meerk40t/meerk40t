import os
import unittest

from PIL import ImageDraw
from PIL import Image

from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.units import UNITS_PER_MM
from meerk40t.svgelements import Matrix
from test import bootstrap


egv_rect = """Document type : LHYMICRO-GL file
File version: 1.0.01
Copyright: Unknown
Creator-Software: MeerK40t v0.0.0-testing

%0%0%0%0%
IBzzzvRzzzvS1P
ICV2490731016000027CNLBS1EDz139Rz139Tz139Lz139FNSE-
"""

egv_image = """Document type : LHYMICRO-GL file
File version: 1.0.01
Copyright: Unknown
Creator-Software: MeerK40t v0.0.0-testing

%0%0%0%0%
IB067R091S1P
IV1552121G002NLTS1EDnU|sB|oD|aU|qT|oD|iU|oB|oD|mU|qT|oD|sU|oB|oD|uU|oT|oD|yU|oB|oD054U|mT|oD054U|oB|oD058U|mT|oD058U|mB|oD058U|oT|oD062U|mB|oD062U|mT|oD062U|mB|oD062U|mT|oD062U|mB|oD062U|mT|oD062U|mB|qD058U|mT|oD058U|mB|oD058U|mT|qD054U|mB|oD054U|mT|qD|yU|mB|qD|uU|mT|qD|qU|mB|qD|mU|mT|qD|iU|mB|sD|aU|mT|uDlFNSE-
"""

egv_blank = """Document type : LHYMICRO-GL file
File version: 1.0.01
Copyright: Unknown
Creator-Software: MeerK40t v0.0.0-testing

%0%0%0%0%
"""

egv_override_speed_1_rect = """Document type : LHYMICRO-GL file
File version: 1.0.01
Copyright: Unknown
Creator-Software: MeerK40t v0.0.0-testing

%0%0%0%0%
ICV2452421011000060CNBRS1EMzzzvFNSE-
ICV2490731016000027CNLBS1EDz139Rz139Tz139Lz139FNSE-
"""

egv_override_speed_2_rect = """Document type : LHYMICRO-GL file
File version: 1.0.01
Copyright: Unknown
Creator-Software: MeerK40t v0.0.0-testing

%0%0%0%0%
ICV2452421011000060CNBRS1EMzzzvFNSE-
ICV2490731016000027CNLBS1EDz139Rz139Tz139Lz139FNSE-
ICV2452421011000060CNBRS1EMzzzwFNSE-
ICV2490731016000027CNLBS1EDz139Rz139Tz139Lz139FNSE-
"""


class TestDriverLihuiyu(unittest.TestCase):
    def test_driver_basic_rect_engrave(self):
        """
        @return:
        """
        file1 = "teste.egv"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i lhystudios 0\n")
            kernel.console("operation* remove\n")
            kernel.console(f"rect 2cm 2cm 1cm 1cm engrave -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n")
        finally:
            kernel.shutdown()
        with open(file1, "r") as f:
            data = f.read()
        self.assertEqual(data, egv_rect)

    def test_driver_basic_rect_cut(self):
        """
        @return:
        """
        file1 = "testc.egv"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i lhystudios 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm cut -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n")
        finally:
            kernel.shutdown()
        with open(file1, "r") as f:
            data = f.read()
        self.assertEqual(data, egv_rect)

    def test_driver_basic_rect_raster(self):
        """
        Attempts a raster operation however wxPython isn't available so nothing is produced.

        @return:
        """
        file1 = "testr.egv"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i lhystudios 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm raster -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n")
        finally:
            kernel.shutdown()
        with open(file1, "r") as f:
            data = f.read()
        self.assertEqual(data, egv_blank)

    def test_driver_basic_ellipse_image(self):
        """
        Attempts a raster operation however wxPython isn't available so nothing is produced.

        @return:
        """
        file1 = "testi.egv"
        self.addCleanup(os.remove, file1)

        image = Image.new("RGBA", (256, 256), "white")
        matrix = Matrix.scale(UNITS_PER_MM / 64)
        matrix.translate(UNITS_PER_MM * 2, UNITS_PER_MM * 2)

        draw = ImageDraw.Draw(image)
        draw.ellipse((50, 50, 150, 150), "black")

        kernel = bootstrap.bootstrap()
        try:
            image_node = ImageNode(image=image, matrix=matrix)
            kernel.elements.elem_branch.add_node(image_node)
            kernel.console("element* list\n")
            kernel.console("service device start -i lhystudios 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"element0 imageop -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n")
        finally:
            kernel.shutdown()
        with open(file1, "r") as f:
            data = f.read()
        self.assertEqual(data, egv_image)

    def test_driver_override_speed_engrave(self):
        """
        This test creates a lihuiyu device, forces the override and speeds in x and y.

        This shall result in the movements not being within rapid speed mode but rather at a given speed:
        'IBzzzvRzzzvS1P\n'

        replaced with:
        'ICV2452421011000060CNBRS1EBzzzvRzzzvFNSE-\n'

        @return:
        """
        file1 = "test_rapid_override.egv"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i lhystudios 0\n")
            kernel.console("operation* delete\n")
            device = kernel.device
            path = kernel.device.path
            device(f"set -p {path} rapid_override True")
            device(f"set -p {path} rapid_override_speed_x 10.0")
            device(f"set -p {path} rapid_override_speed_y 10.0")
            kernel.console(f"rect 2cm 2cm 1cm 1cm engrave -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n")
        finally:
            kernel.shutdown()
        with open(file1, "r") as f:
            data = f.read()
        self.assertEqual(egv_override_speed_1_rect, data)

    def test_driver_override_speed_between(self):
        """
        This test creates a lihuiyu device, forces the override and speeds in x and y.

        Tests the rapid speed feature between two different objects.
        @return:
        """
        file1 = "test_rapid_override_between.egv"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i lhystudios 0\n")
            kernel.console("operation* delete\n")
            device = kernel.device
            path = kernel.device.path
            device(f"set -p {path} rapid_override True")
            device(f"set -p {path} rapid_override_speed_x 10.0")
            device(f"set -p {path} rapid_override_speed_y 10.0")
            kernel.console("rect 2cm 2cm 1cm 1cm\n")
            kernel.console("rect 4cm 4cm 1cm 1cm\n")  # second rect is not overlapping / non-connecting
            kernel.console(f"element* engrave -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n")
        finally:
            kernel.shutdown()
        with open(file1, "r") as f:
            data = f.read()
            print(data)
        self.assertEqual(egv_override_speed_2_rect, data)
