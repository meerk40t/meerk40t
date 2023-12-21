import os
import unittest
from test import bootstrap

lmc_rect = """listReadyMark        0000 0000 0000 0000 0000
listDelayTime        0320 0000 0000 0000 0000
listWritePort        0001 0000 0000 0000 0000
listJumpSpeed        04a7 0000 0000 0000 0000
listMarkCurrent      0fff 0000 0000 0000 0000
listQSwitchPeriod    03e8 0000 0000 0000 0000
listMarkSpeed        0008 0000 0000 0000 0000
listLaserOnDelay     0064 0000 0000 0000 0000
listLaserOffDelay    0064 0000 0000 0000 0000
listPolygonDelay     0064 0000 0000 0000 0000
listJumpTo           ba2e 45d1 0000 5248 0000
listMarkTo           ba2e 2e8b 0000 1746 0000
listMarkTo           d174 2e8b 0000 1746 0000
listMarkTo           d174 45d1 0000 1746 0000
listMarkTo           ba2e 45d1 0000 1746 0000
listDelayTime        001e 0000 0000 0000 0000
listEndOfList        0000 0000 0000 0000 0000
"""

lmc_rect_rotary = """listReadyMark        0000 0000 0000 0000 0000
listDelayTime        0320 0000 0000 0000 0000
listWritePort        0001 0000 0000 0000 0000
listJumpSpeed        04a7 0000 0000 0000 0000
listMarkCurrent      0fff 0000 0000 0000 0000
listQSwitchPeriod    03e8 0000 0000 0000 0000
listMarkSpeed        0008 0000 0000 0000 0000
listLaserOnDelay     0064 0000 0000 0000 0000
listLaserOffDelay    0064 0000 0000 0000 0000
listPolygonDelay     0064 0000 0000 0000 0000
listJumpTo           ba2e 8ba2 0000 3b54 0000
listMarkTo           ba2e 5d17 0000 2e8b 0000
listMarkTo           d174 5d17 0000 1746 0000
listMarkTo           d174 8ba2 0000 2e8b 0000
listMarkTo           ba2e 8ba2 0000 1746 0000
listDelayTime        001e 0000 0000 0000 0000
listEndOfList        0000 0000 0000 0000 0000
"""

lmc_blank = ""


class TestDriverGRBL(unittest.TestCase):
    def test_reload_devices_galvo(self):
        """
        We start a new bootstrap, delete any services that would have existed previously. Add several galvo services.
        Shutdown the bootstrap. Reload. Test if those other services also booted back up.
        @return:
        """
        kernel = bootstrap.bootstrap(profile="MeerK40t_GALVO")
        try:
            for i in range(10):
                kernel.console(f"service device destroy {i}\n")
            kernel.console("service device start -i balor 0\n")
            kernel.console("service device start -i balor 1\n")
            kernel.console("service device start -i balor 2\n")
            kernel.console("service list\n")
            kernel.console("contexts\n")
            kernel.console("plugins\n")
        finally:
            kernel()

        kernel = bootstrap.bootstrap(profile="MeerK40t_GALVO", ignore_settings=False)
        try:
            devs = [name for name in kernel.contexts if name.startswith("balor")]
            self.assertGreater(len(devs), 1)
        finally:
            kernel()

    def test_driver_basic_rect_engrave(self):
        """
        @return:
        """
        file1 = "te.lmc"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i balor 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm engrave -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1) as f:
            data = f.read()
        self.assertEqual(lmc_rect, data)

    def test_driver_basic_rect_cut(self):
        """
        @return:
        """
        file1 = "tc.lmc"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i balor 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm cut -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1) as f:
            data = f.read()
        self.assertEqual(lmc_rect, data)

    def test_driver_basic_rect_raster(self):
        """
        Attempts a raster operation however wxPython isn't available so nothing is produced.

        @return:
        """
        file1 = "tr.gcode"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i balor 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm raster -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1) as f:
            data = f.read()
        self.assertEqual(data, lmc_blank)


class TestDriverGalvoRotary(unittest.TestCase):
    def test_driver_rotary_engrave(self):
        """
        This test creates a Galvo device, with a rotary.

        The rotary enabled is a y-axis rotary. Galvo devices strictly have their own rotary ports mostly and there
        are no stepper motors to replace a y-axis stepper with.
        @return:
        """
        file1 = "test_rotary.lmc"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap(profile="MeerK40t_GALVO_rotary")
        try:
            kernel.console("service device start -i balor 0\n")
            kernel.console("operation* delete\n")
            device = kernel.device
            rotary_path = kernel.device.path
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
        self.assertNotEqual(lmc_rect, data)
        self.assertEqual(lmc_rect_rotary, data)
