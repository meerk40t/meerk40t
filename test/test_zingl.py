from __future__ import print_function

import unittest
import os
import ZinglPlotter


class TestZingl(unittest.TestCase):

    def test_line(self):
        for x, y, on in ZinglPlotter.plot_line(0, 0, 100, 100):
            self.assertEquals(x,y)
        for i, v in enumerate(ZinglPlotter.plot_line(0, 0, 100, 0)):
            x, y, on = v
            self.assertEquals(y,0)
            self.assertEqual(x, i)
        for i, v in enumerate(ZinglPlotter.plot_line(0, 0, 0, 100)):
            x, y, on = v
            self.assertEqual(x, 0)
            self.assertEquals(y,i)
        for i, v in enumerate(ZinglPlotter.plot_line(0, 0, 100, 200)):
            x, y, on = v
            self.assertEqual(x,round(i/2.0))
            self.assertEquals(y, i)
        for i, v in enumerate(ZinglPlotter.plot_line(0, 0, 100, 300)):
            x, y, on = v
            self.assertEqual(x,round(i/3.0))
            self.assertEquals(y, i)
        for i, v in enumerate(ZinglPlotter.plot_line(0, 0, 300, 100)):
            x, y, on = v
            self.assertEqual(y, round(i / 3.0))
            self.assertEquals(x, i)

    def test_quad_bezier(self):
        for x, y, on in ZinglPlotter.plot_quad_bezier(0, 0, 50, 50, 100, 100):
            self.assertEquals(x,y)
        for x, y, on in ZinglPlotter.plot_quad_bezier(0, 0, 50, 50, 0, 0):
            self.assertEquals(x, y)

    def test_cubic_bezier(self):
        for x, y, on in ZinglPlotter.plot_cubic_bezier(0, 0, 50, 50, 100, 100, 150, 150):
            self.assertEquals(x,y)
        for x, y, on in ZinglPlotter.plot_cubic_bezier(0, 0, 100, 100, 100, 100, 0, 0):
            self.assertEquals(x, y)
