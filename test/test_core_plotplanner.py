import unittest

from PIL import Image, ImageDraw

from meerk40t.core.cutcode import Parameters, LineCut, CutCode
from meerk40t.core.node.laserop import RasterOpNode, EngraveOpNode
from meerk40t.core.plotplanner import PlotPlanner
from meerk40t.device.basedevice import PLOT_AXIS, PLOT_SETTING
from meerk40t.svgelements import Circle, Path, Point, SVGImage


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
        settings = {"power": 1000}
        plan = PlotPlanner(settings)

        for i in range(211):
            plan.push(LineCut(Point(0, 0), Point(5, 100), settings=settings))
            plan.push(LineCut(Point(100, 50), Point(0, 0), settings=settings))
            plan.push(
                LineCut(
                    Point(50, -50), Point(100, -100), settings={"power": 0}
                )
            )
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

        rasterop = RasterOpNode()
        svg_image = SVGImage()
        svg_image.image = Image.new("RGBA", (256, 256))
        draw = ImageDraw.Draw(svg_image.image)
        draw.ellipse((0, 0, 255, 255), "black")
        rasterop.add(svg_image, type="ref elem")

        vectorop = EngraveOpNode()
        vectorop.add(Path(Circle(cx=127, cy=127, r=128, fill="black")), type="ref elem")
        cutcode = CutCode()
        cutcode.extend(vectorop.as_cutobjects())
        cutcode.extend(rasterop.as_cutobjects())
        settings = { "power": 500}
        plan = PlotPlanner(settings)
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
