import os
import unittest
from test import bootstrap

from PIL import Image, ImageDraw

from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.units import UNITS_PER_MM
from meerk40t.svgelements import Matrix

hpgl_rect = "ZZZFile0;VP100;VK100;SP2;VQ20;VJ10;VS10;PR;PU787,787;ZED;ZZZFile0;DW;VP100;VK100;SP0;DA0;VQ20;VJ10;VS10;PR;PD0,394;PD394,0;PD0,-394;PD-394,0;ZED;GZ;VP100;VK100;SP1;DA51;VS177;PR;PD0,394;PD394,0;PD0,-394;PD-394,0;ZED;ZZZFile0;ZG0;ZED;"

hpgl_blank = "ZZZFile0;VP100;VK100;SP2;VQ20;VJ10;VS10;PR;PU787,787;ZED;ZZZFile0;DW;VP100;VK100;SP0;DA0;VQ20;VJ10;VS10;PR;PD0,394;PD394,0;PD0,-394;PD-394,0;ZED;GZ;ZED;ZZZFile0;ZG0;ZED;"

hpgl_image = (
'ZZZFile0;VP100;VK100;SP2;VQ20;VJ10;VS10;'
'PR;PU31,31;ZED;ZZZFile0;DW;VP100;VK100;S'
'P0;DA0;VQ20;VJ10;VS10;PR;PD0,62;PD62,0;P'
'D0,-62;PD-62,0;ZED;GZ;IN;VP100;VK100;SP2'
';VQ20;VJ10;VS10;PR;PU60,24;DA51;BT1;BC0;'
'BD1;SP0;VQ20;VJ8;VS2;YF\x00\x00\x01\x00;YZ\x00\x00"ÿ?\x00\x00\x00;P'
'R;PU-2,0;YF\x00\x00<\x00Àÿÿÿ\x00\x00\x00;PR;PU-2,0;YZ\x00\x00F\x00\x00'
'ÿÿÿÿ\x03\x00\x00;PR;PU-2,0;YF\x00\x00L\x00\x00üÿÿÿÿ\x00\x00\x00;PR;PU-'
'2,0;YZ\x00\x00R\x00\x00üÿÿÿÿ?\x00\x00\x00;PR;PU-2,0;YF\x00\x00V\x00\x00ðÿ'
'ÿÿÿÿ\x03\x00\x00;PR;PU-2,0;YZ\x00\x00X\x00\x00üÿÿÿÿÿ\x0f\x00\x00;PR;PU'
'-2,0;YF\x00\x00\\\x00\x00üÿÿÿÿÿÿ\x00\x00\x00;PR;PU-2,0;YZ\x00\x00^\x00\x00'
'ðÿÿÿÿÿÿ\x03\x00\x00;PR;PU-2,0;YF\x00\x00`\x00\x00üÿÿÿÿÿÿ\x0f\x00\x00;P'
'R;PU-2,0;YZ\x00\x00b\x00\x00ðÿÿÿÿÿÿ?\x00\x00\x00;PR;PU-2,0;YF'
'\x00\x00b\x00\x00ðÿÿÿÿÿÿ?\x00\x00\x00;PR;PU-2,0;YZ\x00\x00d\x00\x00üÿÿÿÿÿ'
'ÿÿ\x00\x00\x00;PR;PU-2,0;YF\x00\x00f\x00\x00ðÿÿÿÿÿÿÿ\x03\x00\x00;PR;PU'
'-2,0;YZ\x00\x00f\x00\x00ðÿÿÿÿÿÿÿ\x03\x00\x00;PR;PU-2,0;YF\x00\x00f\x00'
'\x00ðÿÿÿÿÿÿÿ\x03\x00\x00;PR;PU-2,0;YZ\x00\x00f\x00\x00ðÿÿÿÿÿÿÿ\x03\x00'
'\x00;PR;PU-2,0;YF\x00\x00f\x00\x00ðÿÿÿÿÿÿÿ\x03\x00\x00;PR;PU-2,0'
';YZ\x00\x00f\x00\x00ðÿÿÿÿÿÿÿ\x03\x00\x00;PR;PU-2,0;YF\x00\x00d\x00\x00Àÿÿ'
'ÿÿÿÿÿ\x00\x00\x00;PR;PU-2,0;YZ\x00\x00b\x00\x00ðÿÿÿÿÿÿ?\x00\x00\x00;PR'
';PU-2,0;YF\x00\x00b\x00\x00ðÿÿÿÿÿÿ?\x00\x00\x00;PR;PU-2,0;YZ\x00'
'\x00`\x00\x00Àÿÿÿÿÿÿ\x0f\x00\x00;PR;PU-2,0;YF\x00\x00^\x00\x00ðÿÿÿÿÿÿ\x03'
'\x00\x00;PR;PU-2,0;YZ\x00\x00\\\x00\x00Àÿÿÿÿÿÿ\x00\x00\x00;PR;PU-2,0'
';YF\x00\x00X\x00\x00Àÿÿÿÿÿ\x0f\x00\x00;PR;PU-2,0;YZ\x00\x00T\x00\x00Àÿÿÿÿ'
'ÿ\x00\x00\x00;PR;PU-2,0;YF\x00\x00P\x00\x00Àÿÿÿÿ\x0f\x00\x00;PR;PU-2,0'
';YZ\x00\x00L\x00\x00Àÿÿÿÿ\x00\x00\x00;PR;PU-2,0;YF\x00\x00F\x00\x00\x00ÿÿÿ\x03\x00'
'\x00;PR;PU-2,0;YZ\x00\x00<\x00\x00\x00üÿ\x00\x00\x00;SP2;VQ20;VJ10;'
'VS10;PU0,-57;ZED;ZZZFile0;ZG0;ZED;'
)

hpgl_rect_rot = "ZZZFile0;VP100;VK100;SP2;VQ20;VJ10;VS10;PR;PU1575,787;ZED;ZZZFile0;DW;VP100;VK100;SP0;DA0;VQ20;VJ10;VS10;PR;PD0,394;PD787,0;PD0,-394;PD-787,0;ZED;GZ;VP100;VK100;SP1;DA51;VS177;PR;PD0,394;PD787,0;PD0,-394;PD-787,0;ZED;ZZZFile0;ZG0;ZED;"


class TestDriverNewly(unittest.TestCase):
    def test_driver_basic_rect_engrave(self):
        """
        @return:
        """
        file1 = "te.hpgl"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i newly 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm engrave -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1) as f:
            data = f.read()
        self.assertEqual(hpgl_rect, data)

    def test_driver_basic_rect_cut(self):
        """
        @return:
        """
        file1 = "tc.hpgl"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i newly 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm cut -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1) as f:
            data = f.read()
        self.assertEqual(hpgl_rect, data)

    def test_driver_basic_rect_raster(self):
        """
        Attempts a raster operation however wxPython isn't available so nothing is produced.

        @return:
        """
        file1 = "tr.gcode"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i newly 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm raster -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1) as f:
            data = f.read()
        self.assertEqual(data, hpgl_blank)

    def test_driver_basic_ellipse_image(self):
        """
        Attempts a raster operation however wxPython isn't available so nothing is produced.

        @return:
        """
        file1 = "testi.hpgl"
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
            kernel.console("service device start -i newly 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"element0 imageop -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1, "rb") as f:
            data = f.read()
            data = data.decode(encoding="latin-1")
            # print ("hpgl_image = (")
            # idx = 0
            # while idx < len(data):
            #     sdata = data[idx:idx+40]
            #     print (repr(sdata))
            #     idx += 40
            # print (")")
        self.assertEqual(data, hpgl_image)


class TestDriverNewlyRotary(unittest.TestCase):
    def test_driver_rotary_engrave(self):
        """
        This test creates a newly device, with a rotary.
        @return:
        """
        file1 = "test_rotary.hpgl"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap(profile="MeerK40t_TEST_rotary")
        try:
            kernel.console("service device start -i newly 0\n")
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
        self.assertNotEqual(hpgl_rect, data)
        self.assertEqual(hpgl_rect_rot, data)
        print(data)
