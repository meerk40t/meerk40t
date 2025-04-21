import os
import unittest
from test import bootstrap

from PIL import Image, ImageDraw

from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.units import UNITS_PER_MM
from meerk40t.svgelements import Matrix

egv_rect = """Document type : LHYMICRO-GL file
File version: 1.0.01
Copyright: Unknown
Creator-Software: MeerK40t v0.0.0-testing

%0%0%0%0%
IBzzzvRzzzvS1P
ICV2490731016000027CNLBS1EDz139Rz139Tz139Lz139FNSE-
"""

egv_image="""Document type : LHYMICRO-GL file
File version: 1.0.01
Copyright: Unknown
Creator-Software: MeerK40t v0.0.0-testing

%0%0%0%0%
IB055R091S1P
IV1552121G002NLBS1EDnUxTtD|aUvBtD|iUtTtD|mUtBtD|sUrTtD|uUtBtD|yUtTtD054UrBtD054UtTtD058UrBtD058UrTtD058UtBtD062UrTtD062UrBtD062UrTtD062UrBtD062UrTtD062UrBtD062UrTvD058UrBtD058UrTtD058UrBvD054UrTtD054UrBvD|yUrTvD|uUrBvD|qUrTvD|mUrBvD|iUrTxD|aUrB|aDlFNSE-
"""

egv_blank = """Document type : LHYMICRO-GL file
File version: 1.0.01
Copyright: Unknown
Creator-Software: MeerK40t v0.0.0-testing

%0%0%0%0%
"""

egv_rect_y2_rotary = """Document type : LHYMICRO-GL file
File version: 1.0.01
Copyright: Unknown
Creator-Software: MeerK40t v0.0.0-testing

%0%0%0%0%
IBzzzvRzzzzzz|tS1P
ICV2490731016000027CNLBS1EDz139RzzzvTz139LzzzvFNSE-
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
    def test_reload_devices_lihuiyu(self):
        """
        We start a new bootstrap, delete any services that would have existed previously. Add 1 service and also have
        the default service added by default.
        @return:
        """
        kernel = bootstrap.bootstrap(profile="MeerK40t_LHY")
        try:
            for i in range(10):
                kernel.console(f"service device destroy {i}\n")
            kernel.console("service device start -i lhystudios 0\n")
            kernel.console("service device start -i lhystudios 1\n")
            kernel.console("service device start -i lhystudios 2\n")
            kernel.console("service list\n")
            kernel.console("contexts\n")
            kernel.console("plugins\n")
        finally:
            kernel()

        kernel = bootstrap.bootstrap(profile="MeerK40t_LHY", ignore_settings=False)
        try:
            devs = [name for name in kernel.contexts if name.startswith("lhystudios")]
            self.assertGreater(len(devs), 1)
        finally:
            kernel()

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
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm engrave -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1) as f:
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
                f"rect 2cm 2cm 1cm 1cm cut -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1) as f:
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
                f"rect 2cm 2cm 1cm 1cm raster -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1) as f:
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
                f"element0 imageop -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1) as f:
            data = f.read()
            print (f'egv_image="""{data}"""')
        self.assertEqual(data, egv_image)


class TestDriverLihuiyuRotary(unittest.TestCase):
    def test_driver_rotary_engrave(self):
        """
        This test creates a lihuiyu device, with a rotary.
        @return:
        """
        file1 = "test_rotary.egv"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap(profile="MeerK40t_TEST_rotary")
        try:
            kernel.console("service device start -i lhystudios 0\n")
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
        self.assertEqual(egv_rect_y2_rotary, data)


class TestDriverLihuiyuOverrideSpeed(unittest.TestCase):
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
            kernel.console(
                f"rect 2cm 2cm 1cm 1cm engrave -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
            device(f"set -p {path} rapid_override False")
        finally:
            kernel()
        with open(file1) as f:
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
            kernel.console(
                "rect 4cm 4cm 1cm 1cm\n"
            )  # second rect is not overlapping / non-connecting
            kernel.console(
                f"element* engrave -s 15 plan copy-selected preprocess validate blob preopt optimize save_job {file1}\n"
            )
        finally:
            kernel()
        with open(file1) as f:
            data = f.read()
            print(data)
        self.assertEqual(egv_override_speed_2_rect, data)

    def test_driver_override_speed_shifts(self):
        """
        This test creates a lihuiyu device, forces the override and speeds in x and y at different rates.

        Tests the rapid speed feature between two different objects.
        @return:
        """
        file1 = "test_rapid_fast_long.egv"
        self.addCleanup(os.remove, file1)
        rect_1in_at_15 = "ICV2490731016000027CNLBS1EDzzz235Rzzz235Tzzz235Lzzz235FNSE-\n"

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("service device start -i lhystudios 0\n")

            # X fast, X long.
            kernel.console("operation* delete\n")
            kernel.console("element* delete\n")
            kernel.console("rapid_override 10 1\n")
            kernel.console("rect 2in 2in 1in 1in\n")
            kernel.console("rect 4in 2.1in 1in 1in\n")
            kernel.console(
                f"element* engrave -s 15 plan preprocess validate blob save_job {file1}\n"
            )
            kernel.console("plan clear\n")
            with open(file1) as f:
                data = f.readlines()
            self.assertEqual("ICV1551941002013022CNBRS1EMzzzzzzz215FNSE-\n", data[-4])
            self.assertEqual(rect_1in_at_15, data[-3])
            self.assertEqual(
                "ICV2452421011000060CNRBS1Ezzzzzzz215@NSECV1551941002013022CNRBS1ER100FNSE-\n",
                data[-2],
            )
            self.assertEqual(data[-3], data[-1])

            # X fast, Y long.
            kernel.console("operation* delete\n")
            kernel.console("element* delete\n")
            kernel.console("rapid_override 10 1\n")
            kernel.console("rect 2in 2in 1in 1in\n")
            kernel.console("rect 2.1in 4in 1in 1in\n")
            kernel.console(
                f"element* engrave -s 15 plan preprocess validate blob save_job {file1} clear\n"
            )
            kernel.console("plan clear\n")
            with open(file1) as f:
                data = f.readlines()
            self.assertEqual("ICV1551941002013022CNBRS1EMzzzzzzz215FNSE-\n", data[-4])
            self.assertEqual(rect_1in_at_15, data[-3])
            self.assertEqual(
                "ICV1551941002013022CNBRS1EM100Rzzzzzzz115FNSE-\n", data[-2]
            )
            self.assertEqual(data[-3], data[-1])

            # Y fast, Y long.
            kernel.console("operation* delete\n")
            kernel.console("element* delete\n")
            kernel.console("rapid_override 1 10\n")
            kernel.console("rect 2in 2in 1in 1in\n")
            kernel.console("rect 2.1in 4in 1in 1in\n")
            kernel.console(
                f"element* engrave -s 15 plan preprocess validate blob save_job {file1} clear\n"
            )
            kernel.console("plan clear\n")
            with open(file1) as f:
                data = f.readlines()
            self.assertEqual("ICV1551941002013022CNBRS1EMzzzzzzz215FNSE-\n", data[-4])
            self.assertEqual(rect_1in_at_15, data[-3])
            self.assertEqual(
                "ICV1551941002013022CNBRS1EB100@NSECV2452421011000060CNBRS1Ezzzzzzz215FNSE-\n",
                data[-2],
            )
            self.assertEqual(data[-3], data[-1])

            # Y fast, X long
            kernel.console("operation* delete\n")
            kernel.console("element* delete\n")
            kernel.console("rapid_override 1 10\n")
            kernel.console("rect 2in 2in 1in 1in\n")
            kernel.console("rect 4in 2.1in 1in 1in\n")
            kernel.console(
                f"element* engrave -s 15 plan preprocess validate blob save_job {file1}\n"
            )
            kernel.console("plan clear\n")
            with open(file1) as f:
                data = f.readlines()
            self.assertEqual("ICV1551941002013022CNBRS1EMzzzzzzz215FNSE-\n", data[-4])
            self.assertEqual(rect_1in_at_15, data[-3])
            # RB switch, RB 100, B 1900
            self.assertEqual(
                "ICV1551941002013022CNRBS1EM100Bzzzzzzz115FNSE-\n", data[-2]
            )
            self.assertEqual(data[-3], data[-1])

            # Y fast, X long (Negative Values)
            kernel.console("operation* delete\n")
            kernel.console("element* delete\n")
            kernel.console("rapid_override 1 10\n")
            kernel.console("rect 2in 2in 1in 1in\n")
            kernel.console("rect 0in 0.1in 1in 1in\n")
            kernel.console(
                f"element* engrave -s 15 plan preprocess validate blob save_job {file1}\n"
            )
            kernel.console("plan clear\n")
            with open(file1) as f:
                data = f.readlines()
            self.assertEqual("ICV1551941002013022CNBRS1EMzzzzzzz215FNSE-\n", data[-4])
            self.assertEqual(rect_1in_at_15, data[-3])
            # LT switch, LT 1900, T 100
            self.assertEqual(
                "ICV1551941002013022CNLTS1EMzzzzzzz115T100FNSE-\n", data[-2]
            )
            self.assertEqual(data[-3], data[-1])

            # Y fast, X long (+/- Values)
            kernel.console("operation* delete\n")
            kernel.console("element* delete\n")
            kernel.console("rapid_override 1 10\n")
            kernel.console("rect 2in 2in 1in 1in\n")
            kernel.console("rect 4in 0.1in 1in 1in\n")
            kernel.console(
                f"element* engrave -s 15 plan preprocess validate blob save_job {file1}\n"
            )
            kernel.console("plan clear\n")
            with open(file1) as f:
                data = f.readlines()
            self.assertEqual("ICV1551941002013022CNBRS1EMzzzzzzz215FNSE-\n", data[-4])
            self.assertEqual(rect_1in_at_15, data[-3])
            # LB switch, LB 1900, B 100
            self.assertEqual(
                "ICV1551941002013022CNLBS1EMzzzzzzz115B100FNSE-\n", data[-2]
            )
            self.assertEqual(data[-3], data[-1])

            # Y fast, X long (-/+ Values)
            kernel.console("operation* delete\n")
            kernel.console("element* delete\n")
            kernel.console("rapid_override 1 10\n")
            kernel.console("rect 2in 2in 1in 1in\n")
            kernel.console("rect 0in 2.1in 1in 1in\n")
            kernel.console(
                f"element* engrave -s 15 plan preprocess validate blob save_job {file1}\n"
            )
            kernel.console("plan clear\n")
            with open(file1) as f:
                data = f.readlines()
            self.assertEqual("ICV1551941002013022CNBRS1EMzzzzzzz215FNSE-\n", data[-4])
            self.assertEqual(rect_1in_at_15, data[-3])
            # RT switch, RT 100 , T 1900
            self.assertEqual(
                "ICV1551941002013022CNRTS1EM100Tzzzzzzz115FNSE-\n", data[-2]
            )
            self.assertEqual(data[-3], data[-1])

            # Y fast, X long (-/0 Values)
            kernel.console("operation* delete\n")
            kernel.console("element* delete\n")
            kernel.console("rapid_override 1 10\n")
            kernel.console("rect 2in 2in 1in 1in\n")
            kernel.console("rect 0in 2in 1in 1in\n")
            kernel.console(
                f"element* engrave -s 15 plan preprocess validate blob save_job {file1}\n"
            )
            kernel.console("plan clear\n")
            with open(file1) as f:
                data = f.readlines()
            self.assertEqual("ICV1551941002013022CNBRS1EMzzzzzzz215FNSE-\n", data[-4])
            self.assertEqual(rect_1in_at_15, data[-3])
            # RT switch, RT 0 , T 2000
            self.assertEqual("ICV1551941002013022CNRTS1Ezzzzzzz215FNSE-\n", data[-2])
            self.assertEqual(data[-3], data[-1])

            # Same as previous but changed Y rather than X (should change speed)
            kernel.console("operation* delete\n")
            kernel.console("element* delete\n")
            kernel.console("rapid_override 1 10\n")
            kernel.console("rect 2in 2in 1in 1in\n")
            kernel.console("rect 2in 0in 1in 1in\n")
            kernel.console(
                f"element* engrave -s 15 plan preprocess validate blob save_job {file1}\n"
            )
            kernel.console("plan clear\n")
            with open(file1) as f:
                data = f.readlines()
            self.assertEqual("ICV1551941002013022CNBRS1EMzzzzzzz215FNSE-\n", data[-4])
            self.assertEqual(rect_1in_at_15, data[-3])
            # BL switch, BL 0 , L 2000
            self.assertEqual("ICV2452421011000060CNBLS1Ezzzzzzz215FNSE-\n", data[-2])
            self.assertEqual(data[-3], data[-1])
        finally:
            bootstrap.destroy(kernel)
            kernel()
