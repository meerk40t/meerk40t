import os
import unittest
from test import bootstrap

from PIL import Image, ImageDraw

from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.units import UNITS_PER_MM
from meerk40t.svgelements import Matrix

mos_rect = (
    b"\n\t\t\x00\x00\x00\x13\x03\x13\x03\x8a\x00\x00\x00\x00\x8a\x00\x00\x00\x00"
    b"\xd5\x8a\x01\x00\x00\xd5\x8a\x01\x8a\x01\xd5\x00\x00\x8a\x01\xd5"
    b"\x00\x00\x00\x00\x80\x80\x80\x80\x80\x80\x80"
)

mos_image = (
    b"\n\t\t\x00\x00\x00C\x00[\x00\x8a\x00\x00\x00\x00\x8a\x00\x00\x00\x00"
    b"\x8a\x00\x00\x00\x00\xd5\xf2\xff\x00\x00\x8a\xc6\xff\x00\x00\x8a"
    b"\xc6\xff\xfe\xff\x8a\xee\xff\xfe\xff\xd5\x08\x00\xfe\xff\x8a2"
    b"\x00\xfe\xff\x8a2\x00\xfc\xff\x8a\n\x00\xfc\xff\xd5\xe8\xff\xfc\xff\x8a\xc0"
    b"\xff\xfc\xff\x8a\xc0\xff\xfa\xff\x8a\xe8\xff\xfa\xff\xd5\x0e\x00"
    b"\xfa\xff\x8a8\x00\xfa\xff\x8a8\x00\xf8\xff\x8a\x10\x00\xf8\xff\xd5\xe4\xff"
    b"\xf8\xff\x8a\xbd\xff\xf8\xff\x8a\xbd\xff\xf6\xff\x8a\xe4\xff\xf6"
    b"\xff\xd5\x12\x00\xf6\xff\x8a:\x00\xf6\xff\x8a:\x00\xf4\xff\x8a\x12\x00\xf4"
    b"\xff\xd5\xe0\xff\xf4\xff\x8a\xbd\xff\xf4\xff\x8a\xbd\xff\xf2\xff"
    b"\x8a\xe0\xff\xf2\xff\xd5\x16\x00\xf2\xff\x8a<\x00\xf2\xff\x8a<\x00\xf0\xff"
    b"\x8a\x14\x00\xf0\xff\xd5\xde\xff\xf0\xff\x8a\xbd\xff\xf0\xff\x8a"
    b"\xbd\xff\xee\xff\x8a\xde\xff\xee\xff\xd5\x18\x00\xee\xff\x8a>"
    b"\x00\xee\xff\x8a>\x00\xec\xff\x8a\x16\x00\xec\xff\xd5\xdc\xff"
    b"\xec\xff\x8a\xbd\xff\xec\xff\x8a\xbd\xff\xea\xff\x8a\xde\xff\xea"
    b"\xff\xd5\x18\x00\xea\xff\x8a@\x00\xea\xff\x8a@\x00\xe8\xff\x8a\x18\x00\xe8"
    b"\xff\xd5\xda\xff\xe8\xff\x8a\xbd\xff\xe8\xff\x8a\xbd\xff\xe6\xff"
    b"\x8a\xdc\xff\xe6\xff\xd5\x1a\x00\xe6\xff\x8a@\x00\xe6\xff\x8a@\x00\xe4\xff"
    b"\x8a\x18\x00\xe4\xff\xd5\xda\xff\xe4\xff\x8a\xbd\xff\xe4\xff\x8a"
    b"\xbd\xff\xe2\xff\x8a\xdc\xff\xe2\xff\xd5\x1a\x00\xe2\xff\x8a@"
    b"\x00\xe2\xff\x8a@\x00\xe0\xff\x8a\x18\x00\xe0\xff\xd5\xda\xff"
    b"\xe0\xff\x8a\xbd\xff\xe0\xff\x8a\xbd\xff\xde\xff\x8a\xdc\xff\xde"
    b"\xff\xd5\x1a\x00\xde\xff\x8a@\x00\xde\xff\x8a@\x00\xdc\xff\x8a\x18\x00\xdc"
    b"\xff\xd5\xda\xff\xdc\xff\x8a\xbd\xff\xdc\xff\x8a\xbd\xff\xda\xff"
    b"\x8a\xde\xff\xda\xff\xd5\x18\x00\xda\xff\x8a>\x00\xda\xff\x8a>\x00\xd8\xff"
    b"\x8a\x16\x00\xd8\xff\xd5\xdc\xff\xd8\xff\x8a\xbd\xff\xd8\xff\x8a"
    b"\xbd\xff\xd6\xff\x8a\xde\xff\xd6\xff\xd5\x18\x00\xd6\xff\x8a>"
    b"\x00\xd6\xff\x8a>\x00\xd4\xff\x8a\x14\x00\xd4\xff\xd5\xde\xff"
    b"\xd4\xff\x8a\xbd\xff\xd4\xff\x8a\xbd\xff\xd2\xff\x8a\xe0\xff\xd2"
    b"\xff\xd5\x16\x00\xd2\xff\x8a<\x00\xd2\xff\x8a<\x00\xd0\xff\x8a\x12\x00\xd0"
    b"\xff\xd5\xe0\xff\xd0\xff\x8a\xbd\xff\xd0\xff\x8a\xbd\xff\xce\xff"
    b"\x8a\xe4\xff\xce\xff\xd5\x12\x00\xce\xff\x8a8\x00\xce\xff\x8a8\x00\xcc\xff"
    b"\x8a\x0e\x00\xcc\xff\xd5\xe4\xff\xcc\xff\x8a\xbe\xff\xcc\xff\x8a"
    b"\xbe\xff\xca\xff\x8a\xe8\xff\xca\xff\xd5\x0e\x00\xca\xff\x8a4"
    b"\x00\xca\xff\x8a4\x00\xc8\xff\x8a\n\x00\xc8\xff\xd5\xe8\xff\xc8\xff\x8a\xc2"
    b"\xff\xc8\xff\x8a\xc2\xff\xc6\xff\x8a\xee\xff\xc6\xff\xd5\x08\x00"
    b"\xc6\xff\x8a.\x00\xc6\xff\x8a.\x00\xc4\xff\x8a\x00\x00\xc4\xff\xd5\xf4\xff"
    b"\xc4\xff\x80\x80\x80\x80\x80\x80\x80"
)

mos_blank = b""

mos_rect_rotary = (
    b"\n\t\t\x00\x00\x00\x13\x03'\x06\x8a\x00\x00\x00\x00\x8a\x00\x00\x00\x00"
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
