import os
import unittest

from test import bootstrap


egv_rect = """Document type : LHYMICRO-GL file
File version: 1.0.01
Copyright: Unknown
Creator-Software: MeerK40t v0.0.0-testing

%0%0%0%0%
IBzzzvRzzzvS1P
ICV2490731016000027CNLBS1EDz139Rz139Tz139Lz139FNSE-
"""

egv_blank = """Document type : LHYMICRO-GL file
File version: 1.0.01
Copyright: Unknown
Creator-Software: MeerK40t v0.0.0-testing

%0%0%0%0%
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
