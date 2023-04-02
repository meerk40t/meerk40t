import os
import unittest
from test import bootstrap

gcode_rect = """G90
G94
G21
M4
G0 X19.990 Y205.003 S0.0 F600.0
G1 X19.990 Y215.011 S1000.0 F900.0
G1 X29.997 Y215.011
G1 X29.997 Y205.003
G1 X19.990 Y205.003
G1 S0
M5
"""

gcode_blank = ""


class TestDriverGRBL(unittest.TestCase):
    def test_driver_basic_rect_engrave(self):
        """
        @return:
        """
        file1 = "te.gcode"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i grbl 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm engrave -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel.shutdown()
        with open(file1) as f:
            data = f.read()
        self.assertEqual(gcode_rect, data)

    def test_driver_basic_rect_cut(self):
        """
        @return:
        """
        file1 = "tc.gcode"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i grbl 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm cut -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel.shutdown()
        with open(file1) as f:
            data = f.read()
        self.assertEqual(gcode_rect, data)

    def test_driver_basic_rect_raster(self):
        """
        Attempts a raster operation however wxPython isn't available so nothing is produced.

        @return:
        """
        file1 = "tr.gcode"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i grbl 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm raster -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel.shutdown()
        with open(file1) as f:
            data = f.read()
        self.assertEqual(data, gcode_blank)
