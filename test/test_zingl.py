import unittest
from math import ceil

from meerk40t.svgelements import Arc
from meerk40t.tools.zinglplotter import ZinglPlotter


class TestZingl(unittest.TestCase):

    def test_line(self):
        for x, y in ZinglPlotter.plot_line(0, 0, 100, 100):
            self.assertEqual(x, y)

        for i, v in enumerate(ZinglPlotter.plot_line(0, 0, 100, 0)):
            x, y = v
            self.assertEqual(y, 0)
            self.assertEqual(x, i)

        for i, v in enumerate(ZinglPlotter.plot_line(0, 0, 0, 100)):
            x, y = v
            self.assertEqual(x, 0)
            self.assertEqual(y, i)

        for i, v in enumerate(ZinglPlotter.plot_line(0, 0, 100, 300)):
            x, y = v
            self.assertEqual(x, int(round(i / 3.0)))
            self.assertEqual(y, i)

        for i, v in enumerate(ZinglPlotter.plot_line(0, 0, 300, 100)):
            x, y = v
            self.assertEqual(y, int(round(i / 3.0)))
            self.assertEqual(x, i)

        for i, v in enumerate(ZinglPlotter.plot_line(0, 0, 100, 200)):
            x, y = v
            self.assertEqual(x, int(ceil(i / 2.0)))
            self.assertEqual(y, i)

    def test_quad_bezier(self):
        for x, y in ZinglPlotter.plot_quad_bezier(0, 0, 50, 50, 100, 100):
            self.assertEqual(x, y)
        for x, y in ZinglPlotter.plot_quad_bezier(0, 0, 50, 50, 0, 0):
            self.assertEqual(x, y)

    def test_cubic_bezier(self):
        for x, y in ZinglPlotter.plot_cubic_bezier(0, 0, 50, 50, 100, 100, 150, 150):
            self.assertEqual(x, y)
        for x, y in ZinglPlotter.plot_cubic_bezier(0, 0, 100, 100, 100, 100, 0, 0):
            self.assertEqual(x, y)

    def test_arc(self):
        from math import tau, sqrt
        arc = Arc(start=(0, 100), center=(0, 0), end=(0, 100), sweep=tau)
        for x, y in ZinglPlotter.plot_arc(arc):
            r = sqrt(x * x + y * y)
            self.assertAlmostEqual(r, 100.0, delta=2)

    def test_random_cubic(self):
        import random
        plotter = ZinglPlotter()
        for i in range(1000):
            x, y = random.randint(0, 100), random.randint(0, 100)
            plotter.single_x = x
            plotter.single_y = y
            for plot in plotter.plot_cubic_bezier(x, y,
                                                  (random.random() * 100), (random.random() * 100),
                                                  (random.random() * 100), (random.random() * 100),
                                                  random.randint(0, 100), random.randint(0, 100)):
                pass

    def test_random_quad(self):
        import random
        plotter = ZinglPlotter()
        for i in range(1000):
            x, y = random.randint(0, 100), random.randint(0, 100)
            for plot in plotter.plot_quad_bezier(x, y,
                                                 (random.random() * 100), (random.random() * 100),
                                                 random.randint(0, 100), random.randint(0, 100)):
                pass

    def test_random_line(self):
        import random
        plotter = ZinglPlotter()
        for i in range(100000):
            x, y = random.randint(0, 100), random.randint(0, 100)

            for plot in plotter.plot_line(x, y, random.randint(0, 100), random.randint(0, 100)):
                pass

    def test_random_arc(self):
        import random
        from math import isnan
        for i in range(1000):
            sx, sy = random.randint(0, 100), random.randint(0, 100)
            cx, cy = random.randint(0, 100), random.randint(0, 100)
            ex, ey = random.randint(0, 100), random.randint(0, 100)
            try:
                arc = Arc(start=(sx, sy), control=(cx, cy), end=(ex, ey))
            except ZeroDivisionError:
                # Coincident
                continue
            if isnan(arc.rx):
                # Colinear.
                continue
            plotter = ZinglPlotter()
            for plot in plotter.plot_arc(arc):
                pass
