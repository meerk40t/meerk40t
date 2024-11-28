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
'ZZZFile0;ZED;ZZZFile0;DW;VP100;VK100;SP0'
';DA0;VQ20;VJ10;VS10;PR;PD0,157;PD157,0;P'
'D0,-157;PD-157,0;ZED;GZ;IN;VP100;VK100;S'
'P2;VQ20;VJ10;VS10;PR;PU92,57;DA51;BT1;BC'
'0;BD1;SP0;VQ20;VJ8;VS2;YZ\x00\x00\x1dÿ\x01\x00\x00;YF\x00\x004\x00\x00'
'þÿ\x00\x00\x00;PR;PU-1,0;YZ\x00\x009\x00\x00üÿ\x1f\x00\x00\x00;PR;PU-1,0;'
'YF\x00\x00=\x00\x00üÿÿ\x01\x00\x00;YZ\x00\x00@\x00\x00øÿÿ\x0f\x00\x00;PR;PU-1,0;YF'
'\x00\x00B\x00\x00øÿÿ?\x00\x00\x00;YZ\x00\x00D\x00\x00üÿÿÿ\x01\x00\x00;PR;PU-1,0;YF'
'\x00\x00F\x00\x00üÿÿÿ\x07\x00\x00;PR;PU-1,0;YZ\x00\x00H\x00\x00øÿÿÿ\x0f\x00\x00;YF'
'\x00\x00J\x00\x00üÿÿÿ\x7f\x00\x00\x00;PR;PU-1,0;YZ\x00\x00L\x00\x00øÿÿÿÿ\x00\x00\x00;'
'YF\x00\x00N\x00\x00øÿÿÿÿ\x03\x00\x00;PR;PU-1,0;YZ\x00\x00P\x00\x00øÿÿÿÿ\x0f\x00'
'\x00;PR;PU-1,0;YF\x00\x00Q\x00\x00øÿÿÿÿ?\x00\x00\x00;YZ\x00\x00R\x00\x00øÿÿÿ'
'ÿ?\x00\x00\x00;PR;PU-1,0;YF\x00\x00T\x00\x00øÿÿÿÿÿ\x00\x00\x00;PR;PU-1'
',0;YZ\x00\x00U\x00\x00øÿÿÿÿÿ\x03\x00\x00;YF\x00\x00V\x00\x00øÿÿÿÿÿ\x03\x00\x00;PR;'
'PU-1,0;YZ\x00\x00W\x00\x00ðÿÿÿÿÿ\x07\x00\x00;YF\x00\x00W\x00\x00øÿÿÿÿÿ\x0f\x00\x00'
';PR;PU-1,0;YZ\x00\x00X\x00\x00øÿÿÿÿÿ\x0f\x00\x00;PR;PU-1,0;YF'
'\x00\x00Z\x00\x00øÿÿÿÿÿ?\x00\x00\x00;YZ\x00\x00[\x00\x00ðÿÿÿÿÿ\x7f\x00\x00\x00;PR;PU-'
'1,0;YF\x00\x00[\x00\x00øÿÿÿÿÿÿ\x00\x00\x00;YZ\x00\x00\\\x00\x00øÿÿÿÿÿÿ\x00\x00\x00;'
'PR;PU-1,0;YF\x00\x00]\x00\x00ðÿÿÿÿÿÿ\x01\x00\x00;PR;PU-1,0;YZ'
'\x00\x00^\x00\x00øÿÿÿÿÿÿ\x03\x00\x00;YF\x00\x00_\x00\x00ðÿÿÿÿÿÿ\x07\x00\x00;PR;PU-'
'1,0;YZ\x00\x00_\x00\x00ðÿÿÿÿÿÿ\x0f\x00\x00;PR;PU-1,0;YF\x00\x00_\x00\x00ø'
'ÿÿÿÿÿÿ\x07\x00\x00;YZ\x00\x00`\x00\x00øÿÿÿÿÿÿ\x0f\x00\x00;PR;PU-1,0;YF'
'\x00\x00a\x00\x00ðÿÿÿÿÿÿ\x1f\x00\x00\x00;YZ\x00\x00a\x00\x00øÿÿÿÿÿÿ?\x00\x00\x00;PR;P'
'U-1,0;YF\x00\x00a\x00\x00øÿÿÿÿÿÿ?\x00\x00\x00;PR;PU-1,0;YZ\x00\x00a'
'\x00\x00øÿÿÿÿÿÿ?\x00\x00\x00;YF\x00\x00b\x00\x00øÿÿÿÿÿÿ?\x00\x00\x00;PR;PU-1'
',0;YZ\x00\x00c\x00\x00ðÿÿÿÿÿÿ\x7f\x00\x00\x00;YF\x00\x00c\x00\x00ðÿÿÿÿÿÿ\x7f\x00\x00\x00'
';PR;PU-1,0;YZ\x00\x00d\x00\x00øÿÿÿÿÿÿÿ\x00\x00\x00;PR;PU-1,0;'
'YF\x00\x00e\x00\x00ðÿÿÿÿÿÿÿ\x01\x00\x00;YZ\x00\x00e\x00\x00ðÿÿÿÿÿÿÿ\x01\x00\x00;PR'
';PU-1,0;YF\x00\x00e\x00\x00ðÿÿÿÿÿÿÿ\x01\x00\x00;PR;PU-1,0;YZ\x00'
'\x00e\x00\x00ðÿÿÿÿÿÿÿ\x01\x00\x00;YF\x00\x00e\x00\x00øÿÿÿÿÿÿÿ\x03\x00\x00;PR;PU'
'-1,0;YZ\x00\x00e\x00\x00øÿÿÿÿÿÿÿ\x03\x00\x00;YF\x00\x00e\x00\x00øÿÿÿÿÿÿÿ\x03'
'\x00\x00;PR;PU-1,0;YZ\x00\x00e\x00\x00øÿÿÿÿÿÿÿ\x03\x00\x00;PR;PU-1,'
'0;YF\x00\x00e\x00\x00øÿÿÿÿÿÿÿ\x03\x00\x00;YZ\x00\x00e\x00\x00øÿÿÿÿÿÿÿ\x03\x00\x00;'
'PR;PU-1,0;YF\x00\x00e\x00\x00øÿÿÿÿÿÿÿ\x03\x00\x00;YZ\x00\x00e\x00\x00øÿÿÿ'
'ÿÿÿÿ\x03\x00\x00;PR;PU-1,0;YF\x00\x00e\x00\x00øÿÿÿÿÿÿÿ\x03\x00\x00;PR;'
'PU-1,0;YZ\x00\x00e\x00\x00øÿÿÿÿÿÿÿ\x03\x00\x00;YF\x00\x00e\x00\x00øÿÿÿÿÿÿ'
'ÿ\x03\x00\x00;PR;PU-1,0;YZ\x00\x00e\x00\x00øÿÿÿÿÿÿÿ\x03\x00\x00;PR;PU-'
'1,0;YF\x00\x00e\x00\x00øÿÿÿÿÿÿÿ\x03\x00\x00;YZ\x00\x00e\x00\x00øÿÿÿÿÿÿÿ\x03\x00'
'\x00;PR;PU-1,0;YF\x00\x00e\x00\x00øÿÿÿÿÿÿÿ\x03\x00\x00;YZ\x00\x00e\x00\x00ðÿ'
'ÿÿÿÿÿÿ\x01\x00\x00;PR;PU-1,0;YF\x00\x00e\x00\x00ðÿÿÿÿÿÿÿ\x01\x00\x00;P'
'R;PU-1,0;YZ\x00\x00e\x00\x00ðÿÿÿÿÿÿÿ\x01\x00\x00;YF\x00\x00e\x00\x00ðÿÿÿÿ'
'ÿÿÿ\x01\x00\x00;PR;PU-1,0;YZ\x00\x00e\x00\x00ðÿÿÿÿÿÿÿ\x01\x00\x00;YF\x00\x00'
'd\x00\x00àÿÿÿÿÿÿÿ\x00\x00\x00;PR;PU-1,0;YZ\x00\x00c\x00\x00ðÿÿÿÿÿÿ\x7f'
'\x00\x00\x00;PR;PU-1,0;YF\x00\x00c\x00\x00ðÿÿÿÿÿÿ\x7f\x00\x00\x00;YZ\x00\x00b\x00\x00'
'ðÿÿÿÿÿÿ\x7f\x00\x00\x00;PR;PU-1,0;YF\x00\x00a\x00\x00øÿÿÿÿÿÿ?\x00\x00\x00'
';PR;PU-1,0;YZ\x00\x00a\x00\x00øÿÿÿÿÿÿ?\x00\x00\x00;YF\x00\x00a\x00\x00ðÿÿ'
'ÿÿÿÿ\x1f\x00\x00\x00;PR;PU-1,0;YZ\x00\x00a\x00\x00ðÿÿÿÿÿÿ\x1f\x00\x00\x00;YF'
'\x00\x00`\x00\x00ðÿÿÿÿÿÿ\x0f\x00\x00;PR;PU-1,0;YZ\x00\x00_\x00\x00ðÿÿÿÿÿÿ'
'\x0f\x00\x00;PR;PU-1,0;YF\x00\x00_\x00\x00ðÿÿÿÿÿÿ\x07\x00\x00;YZ\x00\x00_\x00\x00ð'
'ÿÿÿÿÿÿ\x07\x00\x00;PR;PU-1,0;YF\x00\x00^\x00\x00àÿÿÿÿÿÿ\x03\x00\x00;YZ'
'\x00\x00]\x00\x00ðÿÿÿÿÿÿ\x01\x00\x00;PR;PU-1,0;YF\x00\x00\\\x00\x00ðÿÿÿÿÿÿ'
'\x01\x00\x00;PR;PU-1,0;YZ\x00\x00[\x00\x00ðÿÿÿÿÿ\x7f\x00\x00\x00;YF\x00\x00[\x00\x00ð'
'ÿÿÿÿÿ\x7f\x00\x00\x00;PR;PU-1,0;YZ\x00\x00Z\x00\x00àÿÿÿÿÿ?\x00\x00\x00;PR'
';PU-1,0;YF\x00\x00X\x00\x00ðÿÿÿÿÿ\x1f\x00\x00;YZ\x00\x00W\x00\x00ðÿÿÿÿÿ\x07\x00'
'\x00;PR;PU-1,0;YF\x00\x00W\x00\x00ðÿÿÿÿÿ\x07\x00\x00;YZ\x00\x00V\x00\x00ðÿÿÿ'
'ÿÿ\x07\x00\x00;PR;PU-1,0;YF\x00\x00U\x00\x00ðÿÿÿÿÿ\x01\x00\x00;PR;PU-1'
',0;YZ\x00\x00T\x00\x00àÿÿÿÿÿ\x00\x00\x00;YF\x00\x00R\x00\x00ðÿÿÿÿ\x7f\x00\x00\x00;PR;'
'PU-1,0;YZ\x00\x00Q\x00\x00ðÿÿÿÿ\x1f\x00\x00\x00;YF\x00\x00P\x00\x00àÿÿÿÿ\x0f\x00\x00;'
'PR;PU-1,0;YZ\x00\x00N\x00\x00àÿÿÿÿ\x03\x00\x00;PR;PU-1,0;YF\x00\x00'
'L\x00\x00ðÿÿÿÿ\x01\x00\x00;YZ\x00\x00J\x00\x00àÿÿÿ?\x00\x00\x00;PR;PU-1,0;YF'
'\x00\x00H\x00\x00ðÿÿÿ\x1f\x00\x00;PR;PU-1,0;YZ\x00\x00F\x00\x00ðÿÿÿ\x07\x00\x00;YF'
'\x00\x00D\x00\x00àÿÿÿ\x00\x00\x00;PR;PU-1,0;YZ\x00\x00B\x00\x00àÿÿ?\x00\x00\x00;YF'
'\x00\x00@\x00\x00àÿÿ\x0f\x00\x00;PR;PU-1,0;YZ\x00\x00=\x00\x00Àÿÿ\x01\x00\x00;PR;P'
'U-1,0;YF\x00\x009\x00\x00Àÿ\x1f\x00\x00\x00;YZ\x00\x004\x00\x00\x80ÿ\x00\x00\x00;SP2;VQ2'
'0;VJ10;VS10;PU-31,-86;ZED;ZZZFile0;ZG0;Z'
'ED;'
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
