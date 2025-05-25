import os
import unittest
from test import bootstrap

from PIL import Image, ImageDraw

from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.units import UNITS_PER_MM
from meerk40t.svgelements import Matrix

mos_rect = (
    b"\n\x0e\x0e\x00\x00\x00\x13\x03\x13\x03\x8a\x00\x00\x00\x00\x8a\x00\x00\x00\x00"
    b"\xd5\x8a\x01\x00\x00\xd5\x8a\x01\x8a\x01\xd5\x00\x00\x8a\x01\xd5"
    b"\x00\x00\x00\x00\x80\x80\x80\x80\x80\x80\x80"
)

# Implementation was fixed, so a new image is due
mos_image=(
b'\x02\x01\x00\x00\x007\x00[\x00\x8a\x00\x00\x00\x00\x8a\x00\x00\x00\x00\xa2\x0e\x00\x82&\x00\x88\xfe\xff\x82\x12\x00\xa2\xf8\xff\x82\xe2\xff\x88\xfc\xff'
b'\x82\xf6\xff\xa2\x18\x00\x82,\x00\x88\xfa\xff\x82\x18\x00\xa2\xf2\xff\x82\xde\xff\x88\xf8\xff\x82\xf2\xff\xa2\x1e\x00\x820\x00\x88\xf6\xff\x82\x1c\x00\xa2'
b'\xee\xff\x82\xda\xff\x88\xf4\xff\x82\xee\xff\xa2 \x00\x824\x00\x88\xf2\xff\x82 \x00\xa2\xea\xff\x82\xd8\xff\x88\xf0\xff\x82\xec\xff\xa2"\x00\x826'
b'\x00\x88\xee\xff\x82"\x00\xa2\xe8\xff\x82\xd6\xff\x88\xec\xff\x82\xea\xff\xa2$\x00\x826\x00\x88\xea\xff\x82"\x00\xa2\xe8\xff\x82\xd4\xff\x88\xe8\xff'
b'\x82\xe8\xff\xa2&\x00\x828\x00\x88\xe6\xff\x82$\x00\xa2\xe6\xff\x82\xd4\xff\x88\xe4\xff\x82\xe8\xff\xa2&\x00\x828\x00\x88\xe2\xff\x82$\x00\xa2'
b'\xe6\xff\x82\xd4\xff\x88\xe0\xff\x82\xe8\xff\xa2&\x00\x828\x00\x88\xde\xff\x82$\x00\xa2\xe6\xff\x82\xd4\xff\x88\xdc\xff\x82\xe8\xff\xa2&\x00\x828'
b'\x00\x88\xda\xff\x82"\x00\xa2\xe8\xff\x82\xd6\xff\x88\xd8\xff\x82\xea\xff\xa2$\x00\x826\x00\x88\xd6\xff\x82"\x00\xa2\xe8\xff\x82\xd6\xff\x88\xd4\xff'
b'\x82\xec\xff\xa2"\x00\x824\x00\x88\xd2\xff\x82 \x00\xa2\xea\xff\x82\xd8\xff\x88\xd0\xff\x82\xee\xff\xa2 \x00\x822\x00\x88\xce\xff\x82\x1c\x00\xa2'
b'\xee\xff\x82\xdc\xff\x88\xcc\xff\x82\xf2\xff\xa2\x1c\x00\x82.\x00\x88\xca\xff\x82\x18\x00\xa2\xf2\xff\x82\xe0\xff\x88\xc8\xff\x82\xf6\xff\xa2\x18\x00\x82*'
b"\x00\x88\xc6\xff\x82\x12\x00\xa2\xf8\xff\x82\xe6\xff\x88\xc4\xff\x82\x00\x00\xa2\x0c\x00\x80\x80\x80\x80\x80\x80\x80\n''\x00\x00\x00\x00\x00\x00\x00\x8a"
b'\x00\x00\x00\x00\x80\x80\x80\x80\x80\x80\x80'
)

mos_blank = b""

mos_rect_rotary = (
    b"\n\x0e\x0e\x00\x00\x00\x13\x03'\x06\x8a\x00\x00\x00\x00\x8a\x00\x00\x00\x00"
    b"\xd5\x8a\x01\x00\x00\xd5\x8a\x01\x13\x03\xd5\x00\x00\x13\x03\xd5"
    b"\x00\x00\x00\x00\x80\x80\x80\x80\x80\x80\x80"
)


class TestDriverMoshi(unittest.TestCase):
    def test_reload_devices_moshi(self):
        """
        We start a new bootstrap, delete any services that would have existed previously. Add 1 service and also have
        the default service added by default.
        @return:
        """
        kernel = bootstrap.bootstrap(profile="MeerK40t_MOSHI")
        try:
            for i in range(10):
                kernel.console(f"service device destroy {i}\n")
            kernel.console("service device start -i moshi 0\n")
            kernel.console("service device start -i moshi 1\n")
            kernel.console("service device start -i moshi 2\n")
            kernel.console("service list\n")
            kernel.console("contexts\n")
            kernel.console("plugins\n")
        finally:
            kernel()

        kernel = bootstrap.bootstrap(profile="MeerK40t_MOSHI", ignore_settings=False)
        try:
            devs = [name for name in kernel.contexts if name.startswith("moshi")]
            self.assertGreater(len(devs), 1)
        finally:
            kernel()

    def test_driver_basic_rect_engrave(self):
        """
        @return:
        """
        file1 = "teste.mos"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i moshi 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm engrave -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1, "rb") as f:
            data = f.read()
        self.assertEqual(data, mos_rect)

    def test_driver_basic_rect_cut(self):
        """
        @return:
        """
        file1 = "testc.mos"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i moshi 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm cut -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1, "rb") as f:
            data = f.read()
        self.assertEqual(data, mos_rect)

    def test_driver_basic_rect_raster(self):
        """
        Attempts a raster operation however wxPython isn't available so nothing is produced.

        @return:
        """
        file1 = "testr.mos"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i moshi 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm raster -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1, "rb") as f:
            data = f.read()
        self.assertEqual(data, mos_blank)

    def test_driver_basic_ellipse_image(self):
        """
        Attempts a raster operation however wxPython isn't available so nothing is produced.

        @return:
        """
        file1 = "testi.mos"
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
            kernel.console("service device start -i moshi 0\n")
            kernel.console("operation* remove\n")
            kernel.console(
                f"element0 imageop -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1, "rb") as f:
            data = f.read()
            print ('mos_image=(')
            idx = 0
            while idx < len(data):
                sdata = data[idx:idx+40]
                print (repr(sdata))
                idx += 40
            print (')')
        self.assertEqual(data, mos_image)


class TestDriverMoshiRotary(unittest.TestCase):
    def test_driver_rotary_engrave(self):
        """
        This test creates a moshi device, with a rotary.
        @return:
        """
        file1 = "test_rotary.mos"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap(profile="MeerK40t_TEST_MOSHI_rotary")
        try:
            kernel.console("service device start -i moshi 0\n")
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
        with open(file1, "rb") as f:
            data = f.read()
        # print (f"mos_rect: {mos_rect}")
        # print (f"mos_rect_rotary: {mos_rect_rotary}")
        # print (f"data: {data}")
        self.assertNotEqual(mos_rect, data)
        self.assertEqual(mos_rect_rotary, data)
