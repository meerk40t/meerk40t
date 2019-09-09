from __future__ import print_function

import unittest

import ZinglPlotter

from math import ceil

class TestZingl(unittest.TestCase):

    def test_line(self):
        for x, y, on in ZinglPlotter.plot_line(0, 0, 100, 100):
            self.assertEqual(x, y)

        for i, v in enumerate(ZinglPlotter.plot_line(0, 0, 100, 0)):
            x, y, on = v
            self.assertEqual(y, 0)
            self.assertEqual(x, i)

        for i, v in enumerate(ZinglPlotter.plot_line(0, 0, 0, 100)):
            x, y, on = v
            self.assertEqual(x, 0)
            self.assertEqual(y, i)

        for i, v in enumerate(ZinglPlotter.plot_line(0, 0, 100, 300)):
            x, y, on = v
            self.assertEqual(x, int(round(i / 3.0)))
            self.assertEqual(y, i)

        for i, v in enumerate(ZinglPlotter.plot_line(0, 0, 300, 100)):
            x, y, on = v
            self.assertEqual(y, int(round(i / 3.0)))
            self.assertEqual(x, i)

        for i, v in enumerate(ZinglPlotter.plot_line(0, 0, 100, 200)):
            x, y, on = v
            self.assertEqual(x, int(ceil(i / 2.0)))
            self.assertEqual(y, i)


    def test_quad_bezier(self):
        for x, y, on in ZinglPlotter.plot_quad_bezier(0, 0, 50, 50, 100, 100):
            self.assertEqual(x, y)
        for x, y, on in ZinglPlotter.plot_quad_bezier(0, 0, 50, 50, 0, 0):
            self.assertEqual(x, y)

    def test_cubic_bezier(self):
        for x, y, on in ZinglPlotter.plot_cubic_bezier(0, 0, 50, 50, 100, 100, 150, 150):
            self.assertEqual(x, y)
        for x, y, on in ZinglPlotter.plot_cubic_bezier(0, 0, 100, 100, 100, 100, 0, 0):
            self.assertEqual(x, y)
