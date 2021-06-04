
import unittest

from meerk40t.core.cutcode import LaserSettings, LineCut
from meerk40t.core.plotplanner import PlotPlanner
from meerk40t.svgelements import Point


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
        settings = LaserSettings()
        for i in range(211):
            q = 0
            plan.push(LineCut(Point(0, 0), Point(5, 100), settings=settings))
            plan.push(LineCut(Point(100, 50), Point(0, 0), settings=settings))
            plan.push(LineCut(Point(50, -50), Point(100, -100), settings=LaserSettings()))
            for x, y, on in plan.gen():
                print(x, y, on)
                if q == i:
                    for x, y, on in plan.process_plots(None):
                        print("FLUSH!", x, y, on)
                    # plan.clear()
                    # break
                q += 1
