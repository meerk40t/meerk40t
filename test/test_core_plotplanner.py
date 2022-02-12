import unittest
from random import randint

from PIL import Image, ImageDraw

from meerk40t.core.cutcode import LaserSettings, LineCut, CutCode
from meerk40t.core.elements import LaserOperation
from meerk40t.core.plotplanner import PlotPlanner, Shift
from meerk40t.device.basedevice import PLOT_AXIS, PLOT_SETTING
from meerk40t.svgelements import Point, SVGImage, Path, Circle


class TestPlotplanner(unittest.TestCase):
    def test_plotplanner_flush(self):
        """
        Intro test for plotplanner.

        This is needlessly complex.

        final value is "on", and provides commands.
        128 means settings were changed.
        64 indicates x_axis major
        32 indicates x_dir, y_dir
        256 indicates ended.
        1 means cut.
        0 means move.

        :return:
        """
        plan = PlotPlanner(LaserSettings(power=1000))
        settings = LaserSettings(power=1000)
        for i in range(211):
            plan.push(LineCut(Point(0, 0), Point(5, 100), settings=settings))
            plan.push(LineCut(Point(100, 50), Point(0, 0), settings=settings))
            plan.push(LineCut(Point(50, -50), Point(100, -100), settings=LaserSettings(power=0)))
            q = 0
            for x, y, on in plan.gen():
                # print(x, y, on)
                if q == i:
                    # for x, y, on in plan.process_plots(None):
                        # print("FLUSH!", x, y, on)
                    plan.clear()
                    break
                q += 1

    def test_plotplanner_walk_raster(self):
        """
        Test plotplanner operation of walking to a raster.

        PLOT_FINISH = 256
        PLOT_RAPID = 4
        PLOT_JOG = 2
        PLOT_SETTING = 128
        PLOT_AXIS = 64
        PLOT_DIRECTION = 32
        PLOT_LEFT_UPPER = 512
        PLOT_RIGHT_LOWER = 1024

        1 means cut.
        0 means move.

        :return:
        """

        rasterop = LaserOperation(operation="Raster")
        svg_image = SVGImage()
        svg_image.image = Image.new("RGBA", (256, 256))
        draw = ImageDraw.Draw(svg_image.image)
        draw.ellipse((0, 0, 255, 255), "black")
        rasterop.add(svg_image, type="opnode")

        vectorop = LaserOperation(operation="Engrave")
        vectorop.add(Path(Circle(cx=127, cy=127, r=128, fill="black")), type="opnode")
        cutcode = CutCode()
        cutcode.extend(vectorop.as_cutobjects())
        cutcode.extend(rasterop.as_cutobjects())

        plan = PlotPlanner(LaserSettings(power=500))
        for c in cutcode.flat():
            plan.push(c)

        setting_changed = False
        for x, y, on in plan.gen():
            if on > 2:
                if setting_changed:
                    # Settings change happens at vector to raster switch and must repost the axis.
                    self.assertEqual(on, PLOT_AXIS)
                if on == PLOT_SETTING:
                    setting_changed = True
                else:
                    setting_changed = False

    def test_plotplanner_shift(self):
        plan = PlotPlanner(LaserSettings(power=1000))
        shft = Shift(plan)

        def test_group(s):
            r = ""
            for i, c in enumerate(s):
                shft.process_add(i, i, 1 if c == "1" else 0)
                if i >= 5:
                    x, y, on = shft.process_pop()
                    r += "1" if on else "0"
            while shft.shift_buffer:
                x, y, on = shft.process_pop()
                r += "1" if on else "0"
            return r

        print()
        print("Group Pulse Test")
        print("================")
        test       = "0111011010101001100110010011100111000110001000110001110001110001110001000111000111000110011100110011001001110110110111010111"
        expected   = "0111100111001001100110010011100111000110001000110001110001110001110001000111000111000110011100110011001001111001110111100111"
        results = test_group(test)
        print("Test", test)
        print("Grpd", results)
        self.assertEqual(expected, results)

        print()
        test       = "100100010010100011011011000110001100011101110111000111000111011100011101110011100111011000110110110001100010101000100010"
        expected   = "011000001100100011100111000110001100011101110111000111000111011100011101110011100111011000111001110001100001110000100010"
        results = test_group(test)
        print("Test", test)
        print("Grpd", results)
        self.assertEqual(expected, results)
