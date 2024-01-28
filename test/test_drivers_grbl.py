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

gcode_rect_rotary = """G90
G94
G21
M4
G0 X19.990 Y410.007 S0.0 F600.0
G1 X19.990 Y429.997 S1000.0 F900.0
G1 X29.997 Y429.997
G1 X29.997 Y410.007
G1 X19.990 Y410.007
G1 S0
M5
"""

gcode_blank = ""


class TestDriverGRBL(unittest.TestCase):
    def test_reload_devices_grbl(self):
        """
        We start a new bootstrap, delete any services that would have existed previously. Add several grbl services.
        Shutdown the bootstrap. Reload. Test if those other services also booted back up.
        @return:
        """
        kernel = bootstrap.bootstrap(profile="MeerK40t_GRBL")
        try:
            for i in range(10):
                kernel.console(f"service device destroy {i}\n")
            kernel.console("service device start -i grbl 0\n")
            kernel.console("service device start -i grbl 1\n")
            kernel.console("service device start -i grbl 2\n")
            kernel.console("service list\n")
            kernel.console("contexts\n")
            kernel.console("plugins\n")
        finally:
            kernel()

        kernel = bootstrap.bootstrap(profile="MeerK40t_GRBL", ignore_settings=False)
        try:
            devs = [name for name in kernel.contexts if name.startswith("grbl")]
            self.assertGreater(len(devs), 1)
        finally:
            kernel()

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
            kernel()
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
            kernel()
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
            kernel()
        with open(file1) as f:
            data = f.read()
        self.assertEqual(data, gcode_blank)


class TestDriverGRBLRotary(unittest.TestCase):
    def test_driver_rotary_engrave(self):
        """
        This test creates a GRBL device, with a rotary.
        @return:
        """
        file1 = "test_rotary.gcode"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap(profile="MeerK40t_TEST_rotary")
        try:
            kernel.console("service device start -i grbl 0\n")
            kernel.console("operation* delete\n")
            device = kernel.device
            rotary_path = device.path
            device(f"set -p {rotary_path} rotary_active True")
            device(f"set -p {rotary_path} rotary_scale_y 2.0")
            device.signal("rotary_active", True)
            kernel.device.rotary.realize()  # In case signal doesn't update the device settings quickly enough.
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm engrave -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1) as f:
            data = f.read()
        self.assertNotEqual(gcode_rect, data)
        self.assertEqual(gcode_rect_rotary, data)
