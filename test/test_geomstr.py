import math
import random
import time
import unittest
from copy import copy
from math import tau

import numpy as np

from meerk40t.fill.fills import scanline_fill
from meerk40t.fill.patterns import set_diamond1, set_line
from meerk40t.svgelements import Arc, CubicBezier, Line, Matrix, QuadraticBezier
from meerk40t.core.geomstr import (
    TYPE_LINE,
    TYPE_POINT,
    BeamTable,
    Clip,
    Geomstr,
    MergeGraph,
    Pattern,
    Polygon,
    Scanbeam,
)


def draw(segments, min_x, min_y, max_x, max_y, buffer=0, filename="test.png"):
    from PIL import Image, ImageDraw

    min_x -= buffer
    min_y -= buffer
    max_x += buffer
    max_y += buffer
    im = Image.new("RGBA", (int(max_x - min_x) + 1, int(max_y - min_y) + 1), "white")

    draw = ImageDraw.Draw(im)
    for i in range(len(segments) - 1):
        # Draw raw segments.
        f = segments[i]
        t = segments[i + 1]
        if f is None or t is None:
            continue
        draw.line(
            ((f.real - min_x, f.imag - min_y), (t.real - min_x, t.imag - min_y)),
            fill="#000000",
        )
    # for segment in segments:
    #     # Draw end points.
    #     f = segment[0]
    #     t = segment[-1]
    #     draw.ellipse((f.real - 3, f.imag - 3, f.real + 3, f.imag + 3), fill="#FF0000")
    #     draw.ellipse((t.real - 2, t.imag - 2, t.real + 2, t.imag + 2), fill="#0000FF")
    im.save(filename)


def draw_geom(segments, min_x, min_y, max_x, max_y, buffer=0, filename="test.png"):
    from PIL import Image, ImageDraw

    min_x -= buffer
    min_y -= buffer
    max_x += buffer
    max_y += buffer
    im = Image.new("RGBA", (int(max_x - min_x) + 1, int(max_y - min_y) + 1), "white")

    draw = ImageDraw.Draw(im)
    for line in segments.segments[: segments.index]:
        if line[2].real == TYPE_POINT:
            f = line[0]
            draw.ellipse(
                (
                    f.real - 3 - min_x,
                    f.imag - 3 - min_y,
                    f.real + 3 - min_x,
                    f.imag + 3 - min_y,
                ),
                fill="#FF0000",
            )
        elif line[2].real == TYPE_LINE:
            # Draw raw segments.
            f = line[0]
            t = line[-1]
            draw.line(
                ((f.real - min_x, f.imag - min_y), (t.real - min_x, t.imag - min_y)),
                fill="#000000",
            )
    im.save(filename)


def random_point(i=100):
    return complex(random.random() * i, random.random() * i)


def random_pointi(i=50):
    return complex(random.randint(0, i), random.randint(0, i))


def random_segment(path, i=100, point=True, line=True, quad=True, cubic=True, arc=True):
    t = random.randint(0, 5)
    if t == 0 and point:
        start = random_point(i=i)
        path.point(start)
    elif t == 1 and line:
        start = random_point(i=i)
        end = random_point(i=i)
        path.line(start, end)
    elif t == 2 and quad:
        start = random_point(i=i)
        control = random_point(i=i)
        end = random_point(i=i)
        path.quad(start, control, end)
    elif t == 3 and cubic:
        start = random_point(i=i)
        c1 = random_point(i=i)
        c2 = random_point(i=i)
        end = random_point(i=i)
        path.cubic(start, c1, c2, end)
    elif t == 4 and arc:
        start = random_point(i=i)
        control = random_point(i=i)
        end = random_point(i=i)
        path.arc(start, control, end)
    else:
        random_segment(
            path, i=i, point=point, line=line, quad=quad, cubic=cubic, arc=arc
        )


class TestGeomstr(unittest.TestCase):
    """These tests ensure the basic functions of the Geomstr elements."""

    def test_geomstr_translate_scale(self):
        w = 10000
        h = 10000
        numpath = Geomstr()
        numpath.polyline(
            (
                complex(0.05, 0.05),
                complex(0.95, 0.05),
                complex(0.95, 0.95),
                complex(0.05, 0.95),
                complex(0.05, 0.05),
            )
        )
        numpath.polyline(
            (
                complex(0.25, 0.25),
                complex(0.75, 0.25),
                complex(0.75, 0.75),
                complex(0.25, 0.75),
                complex(0.25, 0.25),
            )
        )
        numpath.uscale(w)

        numpath2 = Geomstr()
        numpath2.polyline(
            (
                complex(w * 0.05, h * 0.05),
                complex(w * 0.95, h * 0.05),
                complex(w * 0.95, h * 0.95),
                complex(w * 0.05, h * 0.95),
                complex(w * 0.05, h * 0.05),
            )
        )
        numpath2.polyline(
            (
                complex(w * 0.25, h * 0.25),
                complex(w * 0.75, h * 0.25),
                complex(w * 0.75, h * 0.75),
                complex(w * 0.25, h * 0.75),
                complex(w * 0.25, h * 0.25),
            )
        )
        q = numpath.segments == numpath2.segments
        self.assertTrue(np.all(numpath.segments == numpath2.segments))
        numpath.translate(3, 3)
        self.assertFalse(np.all(numpath.segments == numpath2.segments))
        numpath.translate(-3, -3)
        self.assertTrue(np.all(numpath.segments == numpath2.segments))

    def test_geomstr_bbox(self):
        w = 10000
        geomstr = Geomstr()
        geomstr.polyline(
            (
                complex(0.05, 0.05),
                complex(0.95, 0.05),
                complex(0.95, 0.95),
                complex(0.05, 0.95),
                complex(0.05, 0.05),
            )
        )
        geomstr.polyline(
            (
                complex(0.25, 0.25),
                complex(0.75, 0.25),
                complex(0.75, 0.75),
                complex(0.25, 0.75),
                complex(0.25, 0.25),
            )
        )
        geomstr.uscale(w)
        self.assertEqual(geomstr.bbox(), (500.0, 500.0, 9500.0, 9500.0))
        geomstr.rotate(tau * 0.25)
        for x, y in zip(geomstr.bbox(), (-9500.0, 500.00000000000057, -500.0, 9500.0)):
            self.assertAlmostEqual(x, y)

    def test_geomstr_transform(self):
        numpath = Geomstr()
        numpath.polyline(
            (
                complex(0.05, 0.05),
                complex(0.95, 0.05),
                complex(0.95, 0.95),
                complex(0.05, 0.95),
                complex(0.05, 0.05),
            )
        )
        numpath.polyline(
            (
                complex(0.25, 0.25),
                complex(0.75, 0.25),
                complex(0.75, 0.75),
                complex(0.25, 0.75),
                complex(0.25, 0.25),
            )
        )
        numpath.uscale(10000)
        c = copy(numpath)
        numpath.rotate(tau * 0.25)
        c.transform(Matrix("rotate(.25turn)"))
        t = numpath.segments == c.segments
        self.assertTrue(np.all(t))

    def test_geomstr_subpath(self):
        """
        Adds two shapes and tests whether they are detected as subshapes with an `end` between them.
        @return:
        """
        numpath = Geomstr()
        numpath.polyline(
            (
                complex(0.05, 0.05),
                complex(0.95, 0.05),
                complex(0.95, 0.95),
                complex(0.05, 0.95),
                complex(0.05, 0.05),
            )
        )
        numpath.close()
        numpath.end()
        numpath.polyline(
            (
                complex(0.25, 0.25),
                complex(0.75, 0.25),
                complex(0.75, 0.75),
                complex(0.25, 0.75),
                complex(0.25, 0.25),
            )
        )
        numpath.uscale(10000)
        numpath.rotate(tau * 0.25)
        subpaths = list(numpath.as_subpaths())
        for subpath in subpaths:
            print(subpath.segments)
            for seg in subpath.segments:
                self.assertEqual(seg[2].real, TYPE_LINE)
        self.assertEqual(len(subpaths[0]), 4)
        self.assertEqual(len(subpaths[1]), 4)

    def test_geomstr_contiguous(self):
        """
        Tests two disconnected polylines without marked ends between them and determines whether two
        shapes are correctly detected.
        @return:
        """
        numpath = Geomstr()
        numpath.polyline(
            (
                complex(0.05, 0.05),
                complex(0.95, 0.05),
                complex(0.95, 0.95),
                complex(0.05, 0.95),
                complex(0.05, 0.05),
            )
        )
        numpath.polyline(
            (
                complex(0.25, 0.25),
                complex(0.75, 0.25),
                complex(0.75, 0.75),
                complex(0.25, 0.75),
                complex(0.25, 0.25),
            )
        )
        numpath.uscale(10000)
        numpath.rotate(tau * 0.25)
        subpaths = list(numpath.as_contiguous())
        print("")
        for subpath in subpaths:
            print(subpath.segments)
            for seg in subpath.segments:
                self.assertEqual(seg[2].real, TYPE_LINE)
        self.assertEqual(len(subpaths[0]), 4)
        self.assertEqual(len(subpaths[1]), 4)

    def test_geomstr_subpath_contiguous(self):
        """
        Create a 2-contour path within a single subpath geomstr
        @return:
        """
        numpath = Geomstr()
        numpath.polyline(
            (
                complex(0.05, 0.05),
                complex(0.95, 0.05),
                complex(0.95, 0.95),
                complex(0.05, 0.95),
                complex(0.05, 0.05),
            )
        )
        numpath.polyline(
            (
                complex(0.25, 0.25),
                complex(0.75, 0.25),
                complex(0.75, 0.75),
                complex(0.25, 0.75),
                complex(0.25, 0.25),
            )
        )
        subpaths = list(numpath.as_subpaths())
        self.assertEqual(len(subpaths), 1)
        contigs = list(numpath.as_contiguous())
        self.assertEqual(len(contigs), 2)

    def test_geomstr_scanline(self):
        w = 10000
        h = 10000
        paths = (
            complex(w * 0.05, h * 0.05),
            complex(w * 0.95, h * 0.05),
            complex(w * 0.95, h * 0.95),
            complex(w * 0.05, h * 0.95),
            complex(w * 0.05, h * 0.05),
            None,
            complex(w * 0.25, h * 0.25),
            complex(w * 0.75, h * 0.25),
            complex(w * 0.75, h * 0.75),
            complex(w * 0.25, h * 0.75),
            complex(w * 0.25, h * 0.25),
        )

        fill = list(
            scanline_fill(
                settings={"hatch_distance": "0.02mm"}, outlines=paths, matrix=None
            )
        )
        path = Geomstr()
        last_x = None
        last_y = None
        for p in fill:
            if p is None:
                last_x = None
                last_y = None
                continue
            x, y = p
            if last_x is not None:
                path.line(complex(last_x, last_y), complex(x, y))
            last_x, last_y = x, y
        p = copy(path)
        self.assertEqual(path, p)
        #
        # print(path.segments)
        # print("Original segments...")
        # print(p.travel_distance())
        # p.two_opt_distance()
        # print(p.travel_distance())
        # print(p.segments)
        # draw(p.segments, w, h)

    def test_geomstr_y_intercepts(self):
        """
        Draws, 6 perfectly horizontal lines. Queries the y_intercepts
        @return:
        """
        g = Geomstr()
        g.line(complex(0, 0), complex(100, 0))
        g.line(complex(0, 20), complex(100, 20))
        g.line(complex(0, 40), complex(100, 40))
        g.line(complex(0, 80), complex(100, 80))
        g.line(complex(0, 60), complex(100, 60))
        g.line(complex(0, 100), complex(100, 100))
        q = g.y_intercept([0, 1, 2, 3, 4, 5], 10, 1)
        self.assertEqual(q[0], 0)
        self.assertEqual(q[1], 20.0)
        self.assertEqual(q[2], 40.0)
        self.assertEqual(q[3], 80.0)
        self.assertEqual(q[4], 60.0)
        self.assertEqual(q[5], 100.0)

    def test_geomstr_y_intercepts_vertical(self):
        """
        Draws 2 lines along the y-axis queries the intercept points.

        Since there is no solution, default is returned.
        @return:
        """
        g = Geomstr()
        g.line(complex(0, 0), complex(0, 100))
        g.line(complex(20, 0), complex(20, 100))
        q = g.y_intercept([0, 1], 10, 1)
        self.assertEqual(q[0], 1)
        self.assertEqual(q[1], 1)

    def test_geomstr_x_intercepts(self):
        """
        Draws, 6 perfectly vertical lines, including y-axis.
        @return:
        """
        g = Geomstr()
        g.line(complex(0, 0), complex(0, 100))
        g.line(complex(20, 0), complex(20, 100))
        g.line(complex(40, 0), complex(40, 100))
        g.line(complex(80, 0), complex(80, 100))
        g.line(complex(60, 0), complex(60, 100))
        g.line(complex(100, 0), complex(100, 100))
        q = g.x_intercept([0, 1, 2, 3, 4, 5], 10, 1)
        self.assertEqual(q[0], 0)
        self.assertEqual(q[1], 20.0)
        self.assertEqual(q[2], 40.0)
        self.assertEqual(q[3], 80.0)
        self.assertEqual(q[4], 60.0)
        self.assertEqual(q[5], 100.0)

    def test_geomstr_x_intercepts_horizontal(self):
        """
        Draws 2 lines along the x-axis queries the intercept points.

        Since there is no solution, default is returned.
        @return:
        """
        g = Geomstr()
        g.line(complex(0, 0), complex(100, 0))
        g.line(complex(0, 20), complex(100, 20))
        q = g.x_intercept([0, 1, 2, 3, 4, 5], 10, 1)
        self.assertEqual(q[0], 1)
        self.assertEqual(q[1], 1)

    def test_geomstr_classmethods(self):
        """
        Test various classmethods for making defined geomstr shapes.
        @return:
        """
        path = Geomstr.lines(0, 1, 0, 101)
        self.assertEqual(len(path), 1)
        self.assertEqual(path.length(0), 100)
        path = Geomstr.lines(100, 100, 0, 100)
        self.assertEqual(len(path), 1)
        self.assertEqual(path.length(0), 100)
        path = Geomstr.lines(0, 0, 1, 1)
        self.assertEqual(len(path), 1)
        self.assertEqual(path.length(0), math.sqrt(2))

        path = Geomstr.lines(0, 0, 1, 1, 2, 2)
        self.assertEqual(len(path), 2)
        self.assertEqual(path.length(0), math.sqrt(2))
        self.assertEqual(path.length(1), math.sqrt(2))

        path = Geomstr.lines((0, 0), (1, 1), (2, 2))
        self.assertEqual(len(path), 2)
        self.assertEqual(path.length(0), math.sqrt(2))
        self.assertEqual(path.length(1), math.sqrt(2))

        path = Geomstr.lines(complex(0, 0), complex(1, 1), complex(2, 2))
        self.assertEqual(len(path), 2)
        self.assertEqual(path.length(0), math.sqrt(2))
        self.assertEqual(path.length(1), math.sqrt(2))

        for i in range(50):
            path = Geomstr.regular_polygon(
                i, 100 + 100j, radius=50, radius_inner=30, alt_seq=1, density=5
            )
            # draw(path.segments[:path.index], 200, 200, filename=f"test{i}.png")

        q = np.array([complex(0, 0), complex(1, 1), complex(2, 2)])
        path = Geomstr.lines(q)
        self.assertEqual(len(path), 2)
        self.assertEqual(path.length(0), math.sqrt(2))
        self.assertEqual(path.length(1), math.sqrt(2))

        r = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]])
        path = Geomstr.lines(r)
        self.assertEqual(len(path), 2)
        self.assertEqual(path.length(0), math.sqrt(2))
        self.assertEqual(path.length(1), math.sqrt(2))

    def test_geomstr_copies(self):
        path = Geomstr.lines(complex(0, 0), complex(1, 1), complex(2, 2))
        path.copies(2)
        self.assertEqual(len(path), 4)
        self.assertTrue(np.all(path.segments[:][0] == path.segments[:][2]))
        self.assertTrue(np.all(path.segments[:][1] == path.segments[:][3]))

    def test_geomstr_interpolated_points(self):
        path = Geomstr.lines(complex(0, 0), complex(1, 1), complex(2, 2))
        path.quad(complex(2, 2), complex(5, 0), complex(4, 4))
        self.assertEqual(len(path), 3)
        pts = list(path.as_interpolated_points(interpolate=100))
        self.assertEqual(102, len(pts))

    def test_geomstr_arc_center(self):
        for i in range(1000):
            start = random_point()
            control = random_point()
            end = random_point()
            c = Arc(start=start, control=control, end=end)

            path = Geomstr()
            path.arc(start, control, end)

            self.assertAlmostEqual(complex(c.center), path.arc_center(0))

    def test_geomstr_arc_radius(self):
        for i in range(1000):
            start = random_point()
            control = random_point()
            end = random_point()
            c = Arc(start=start, control=control, end=end)

            path = Geomstr()
            path.arc(start, control, end)

            self.assertAlmostEqual(c.rx, path.arc_radius(0))
            self.assertAlmostEqual(c.ry, path.arc_radius(0))

    def test_geomstr_line_point(self):
        for i in range(1000):
            start = random_point()
            end = random_point()
            c = Line(start, end)

            path = Geomstr()
            path.line(start, end)
            t = random.random()
            self.assertEqual(c.point(t), path.position(0, t))

    def test_geomstr_quad_point(self):
        for i in range(1000):
            start = random_point()
            control = random_point()
            end = random_point()
            c = QuadraticBezier(start, control, end)

            path = Geomstr()
            path.quad(start, control, end)

            t = random.random()
            self.assertEqual(c.point(t), path.position(0, t))

    def test_geomstr_cubic_point(self):
        for i in range(1000):
            start = random_point()
            c1 = random_point()
            c2 = random_point()
            end = random_point()
            c = CubicBezier(start, c1, c2, end)

            path = Geomstr()
            path.cubic(start, c1, c2, end)

            t = random.random()
            self.assertEqual(c.point(t), path.position(0, t))

    def test_geomstr_quad_equal_distances(self):
        """
        Ballpark estimate that the lines are 5 units apart. Really due to speed and curvature they could be less.
        Also with distribution of the remaining length it could be more.
        @return:
        """
        path = Geomstr()
        path.quad(
            (2.4597240004342713 + 51.217173195366975j),
            (58.07775791133034 + 9.86075895321774j),
            (58.09621943136784 + 98.90335897241886j),
        )
        p = np.array(list(path.as_equal_interpolated_points(5)))
        distances = np.abs(p[:-1] - p[1:])
        for d in distances:
            self.assertAlmostEqual(d, 5, delta=1)

    def test_geomstr_cubic_equal_distances(self):
        """
        Ballpark estimate that the lines are 5 units apart. Really due to speed and curvature they could be less.
        Also with distribution of the remaining length it could be more.
        @return:
        """
        path = Geomstr()
        path.cubic(
            (77.46150486344618 + 8.372252124023593j),
            (99.5707686371264 + 1.7675099427501895j),
            (48.146907914727855 + 48.97717310792103j),
            (26.350415653100136 + 77.5272640600043j),
        )
        p = np.array(list(path.as_equal_interpolated_points(5)))
        distances = np.abs(p[:-1] - p[1:])
        for d in distances:
            self.assertAlmostEqual(d, 5, delta=1)

    # def test_geomstr_cubic_equal_distances(self):
    #     for i in range(5):
    #         start = random_point()
    #         c1 = random_point()
    #         c2 = random_point()
    #         end = random_point()
    #         path = Geomstr()
    #         path.cubic(start, c1, c2, end)
    #         print(f"curve: {start}, {c1}, {c2}, {end}")
    #         p = np.array(list(path.as_equal_interpolated_points(5)))
    #         distances = np.abs(p[:-1] - p[1:])
    #         print(p)
    #         print(distances)
    #         for d in distances:
    #             self.assertAlmostEqual(d, 5, delta=1)
    #         print("\n")

    def test_geomstr_cubic_length(self):
        """
        This test is too time-consuming without scipy installed
        @return:
        """
        try:
            import scipy
        except ImportError:
            return
        difference = 0
        t0 = 0
        t1 = 0
        for i in range(50):
            start = random_point()
            c1 = random_point()
            c2 = random_point()
            end = random_point()
            c = CubicBezier(start, c1, c2, end)

            path = Geomstr()
            path.cubic(start, c1, c2, end)
            t = time.time()
            clen = c.length()
            t0 += time.time() - t

            t = time.time()
            plen = path.length(0)
            t1 += time.time() - t
            self.assertAlmostEqual(clen, plen, delta=0.1)
            difference += clen
            difference -= plen
        print(
            f"geomstr cubic length time {t0:.3f}. svgelements cubic length time {t1:.3f}. total difference {difference:.3f}"
        )

    def test_geomstr_line_bounds(self):
        for i in range(1000):
            start = random_point()
            end = random_point()
            c = Line(start, end)

            path = Geomstr()
            path.line(start, end)

            self.assertEqual(c.bbox(), path.bbox(0))

    def test_geomstr_quad_bounds(self):
        for i in range(1000):
            start = random_point()
            control = random_point()
            end = random_point()
            c = QuadraticBezier(start, control, end)

            path = Geomstr()
            path.quad(start, control, end)

            self.assertEqual(c.bbox(), path.bbox(0))

    def test_geomstr_cubic_bounds(self):
        for i in range(1000):
            start = random_point()
            c1 = random_point()
            c2 = random_point()
            end = random_point()
            c = CubicBezier(start, c1, c2, end)

            path = Geomstr()
            path.cubic(start, c1, c2, end)

            self.assertEqual(c.bbox(), path.bbox(0))

    def test_geomstr_point_functions(self):
        from math import radians, sqrt

        p = Geomstr()
        p.point(complex(4, 4))
        q = p.towards(0, complex(6, 6), 0.5)
        self.assertEqual(q, complex(5, 5))

        m = p.distance(0, complex(6, 6))
        self.assertEqual(m, 2 * sqrt(2))
        m = p.distance(0, complex(4, 0))
        self.assertEqual(m, 4)
        a45 = radians(45)
        a90 = radians(90)
        a180 = radians(180)

        p.point(complex(0, 0))
        a = p.angle(1, complex(3, 3))
        self.assertEqual(a, a45)
        a = p.angle(1, complex(0, 3))
        self.assertEqual(a, a90)
        a = p.angle(1, complex(-3, 0))
        self.assertEqual(a, a180)

        q = p.polar(1, a45, 10)
        self.assertAlmostEqual(q, complex(sqrt(2) / 2 * 10, sqrt(2) / 2 * 10))

        r = p.reflected(1, complex(10, 10))
        self.assertEqual(r, complex(20, 20))

    def test_geomstr_point_towards_static(self):
        p = complex(4, 4)
        q = Geomstr.towards(None, p, complex(6, 6), 0.5)
        self.assertEqual(q, complex(5, 5))

    def test_geomstr_point_distance_static(self):
        from math import sqrt

        p = complex(4, 4)
        m = Geomstr.distance(None, p, complex(6, 6))
        self.assertEqual(m, 2 * sqrt(2))
        m = Geomstr.distance(None, p, complex(4, 0))
        self.assertEqual(m, 4)

    def test_geomstr_point_angle_static(self):
        from math import radians

        p = complex(0, 0)
        a = Geomstr.angle(None, p, complex(3, 3))
        a45 = radians(45)
        self.assertEqual(a, a45)
        a = Geomstr.angle(None, p, complex(0, 3))
        a90 = radians(90)
        self.assertEqual(a, a90)
        a = Geomstr.angle(None, p, complex(-3, 0))
        a180 = radians(180)
        self.assertEqual(a, a180)

    def test_geomstr_point_polar_static(self):
        from math import radians, sqrt

        p = complex(0)
        a = radians(45)
        q = Geomstr.polar(None, p, a, 10)
        self.assertAlmostEqual(q, complex(sqrt(2) / 2 * 10, sqrt(2) / 2 * 10))

    def test_geomstr_point_reflected_static(self):
        p = complex(0)
        r = Geomstr.reflected(None, p, complex(10, 10))
        self.assertEqual(r, complex(20, 20))

    def test_geomstr_simple_length_bbox(self):
        path = Geomstr()
        path.line(complex(0, 0), complex(50, 0))
        self.assertEqual(len(path), 1)
        self.assertEqual(path.raw_length(), 50)
        self.assertEqual(path.bbox(), (0, 0, 50, 0))
        path.line(complex(50, 0), complex(50, 50))
        self.assertEqual(path.raw_length(), 100)

    def test_geomstr_convex_hull(self):
        path = Geomstr()
        path.polyline(
            [
                complex(0, 0),
                complex(100, 0),
                complex(50, 50),
                complex(100, 100),
                complex(0, 100),
                complex(0, 0),
            ]
        )
        pts = list(path.convex_hull(range(5)))
        self.assertNotIn(complex(50, 50), pts)
        self.assertEqual(len(pts), 4)

    def test_geomstr_0_length(self):
        path = Geomstr()
        path.polyline(
            [
                complex(0, 0),
                complex(100, 0),
                complex(50, 50),
                complex(100, 100),
                complex(100, 100),
                complex(0, 100),
                complex(0, 0),
            ]
        )
        path.end()
        self.assertEqual(len(path), 7)
        path.remove_0_length()
        self.assertEqual(len(path), 6)

    def test_geomstr_2opt(self):
        path = Geomstr()
        path.line(complex(0, 0), complex(50, 0))
        path.line(complex(50, 50), complex(50, 0))
        self.assertEqual(path.raw_length(), 100)
        self.assertEqual(path.travel_distance(), 50)
        path.two_opt_distance()
        self.assertEqual(path.travel_distance(), 0)

    def test_geomstr_greedy(self):
        path = Geomstr()
        path.line(complex(0, 0), complex(50, 0))
        path.line(complex(50, 50), complex(50, 0))
        self.assertEqual(path.raw_length(), 100)
        self.assertEqual(path.travel_distance(), 50)
        path.greedy_distance()
        self.assertEqual(path.travel_distance(), 0)

    def test_geomstr_greedy_random(self):
        for trials in range(50):
            path = Geomstr()
            for i in range(500):
                path.line(
                    random_point(50),
                    random_point(50),
                )
            d1 = path.travel_distance()
            path.greedy_distance()
            d2 = path.travel_distance()
            path.two_opt_distance()
            d3 = path.travel_distance()
            self.assertGreaterEqual(d1, d2)
            self.assertGreaterEqual(d2, d3)
            print(f"{d1} < {d2} < {d3}")

    def test_geomstr_scanbeam_build(self):
        """
        Build the scanbeam. In a correct scanbeam we should be able to iterate
        through the scanbeam adding or removing each segment without issue.

        No remove segment ~x should occur before the append segment x value.
        :return:
        """
        for trials in range(50):
            path = Geomstr()
            for i in range(500):
                path.line(
                    random_point(50),
                    random_point(50),
                )

            beam = Scanbeam(path)
            m = list()
            for v, idx in beam._sorted_edge_list:
                if idx >= 0:
                    m.append(idx)
                else:
                    try:
                        m.remove(~idx)
                    except ValueError as e:
                        raise e
            self.assertEqual(len(m), 0)
            beam.compute_beam()

    def test_geomstr_scanbeam_increment(self):
        path = Geomstr()
        path.line(complex(0, 0), complex(50, 0))  # 0
        path.line(complex(50, 0), complex(50, 50))  # 1 ACTIVE
        path.line(complex(50, 50), complex(0, 50))  # 2
        path.line(complex(0, 50), complex(0, 0))  # 3 ACTIVE
        path.close()
        self.assertEqual(path.travel_distance(), 0)
        beam = Scanbeam(path)
        beam.scanline_to(25)
        self.assertEqual(len(beam._active_edge_list), 2)

    def test_geomstr_scanbeam_decrement(self):
        path = Geomstr()
        path.line(complex(0, 0), complex(50, 0))  # 0
        path.line(complex(50, 0), complex(50, 50))  # 1 ACTIVE
        path.line(complex(50, 50), complex(0, 50))  # 2
        path.line(complex(0, 50), complex(0, 0))  # 3 ACTIVE
        path.close()
        self.assertEqual(path.travel_distance(), 0)
        beam = Scanbeam(path)
        beam.scanline_to(float("inf"))
        self.assertEqual(len(beam._active_edge_list), 0)
        beam.scanline_to(25)
        self.assertEqual(len(beam._active_edge_list), 2)

    def test_geomstr_isinside(self):
        path = Geomstr()
        path.line(complex(0, 0), complex(50, 0))
        path.line(complex(50, 0), complex(50, 50))
        path.line(complex(50, 50), complex(0, 50))
        path.line(complex(0, 50), complex(0, 0))
        beam = Scanbeam(path)
        self.assertTrue(beam.is_point_inside(25, 25))

        path.line(complex(10, 10), complex(40, 10))
        path.line(complex(40, 10), complex(40, 40))
        path.line(complex(40, 40), complex(10, 40))
        path.line(complex(10, 40), complex(10, 10))
        beam = Scanbeam(path)
        self.assertFalse(beam.is_point_inside(25, 25))
        self.assertTrue(beam.is_point_inside(5, 25))

    def test_geomstr_merge_intersections(self):
        subject = Geomstr()
        subject.line(complex(0, 0), complex(100, 100))
        clip = Geomstr()
        clip.line(complex(100, 0), complex(0, 100))
        mg = MergeGraph(subject)
        results = mg.find_intersections(clip)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], (50, 50, 0, 0, 0))

    def test_geomstr_intersect_segments(self):
        path = Geomstr()
        for i in range(50):
            random_segment(path)

        for j in range(path.index):
            for k in range(path.index):
                q = f"{path.segment_type(j)} x {path.segment_type(k)}: {list(path.intersections(j, k))}"
                # print(q)

    def test_geomstr_merge_merge(self):
        subject = Geomstr()
        subject.line(complex(0, 20), complex(100, 100))
        subject.line(complex(20, 0), complex(100, 100))
        clip = Geomstr()
        clip.line(complex(100, 0), complex(0, 100))
        mg = MergeGraph(subject)
        results = mg.merge(clip)
        print(results.segments)

    def test_geomstr_merge_capacity_count(self):
        for j in range(25):
            clip = Geomstr()
            for i in range(50):
                clip.line(
                    random_pointi(50),
                    random_pointi(50),
                )
            subject = Geomstr()
            for i in range(50):
                subject.line(
                    random_pointi(50),
                    random_pointi(50),
                )
            mg = MergeGraph(subject)
            results = mg.merge(clip)
            self.assertEqual(results.index, results.capacity)

    def test_geomstr_merge_order(self):
        subject = Geomstr()
        subject.line(complex(50, 0), complex(50, 100))
        clip = Geomstr()
        clip.line(complex(0, 20), complex(100, 20))
        clip.line(complex(0, 40), complex(100, 40))
        clip.line(complex(0, 80), complex(100, 80))
        clip.line(complex(0, 60), complex(100, 60))
        clip.line(complex(0, 100), complex(100, 100))
        mg = MergeGraph(subject)
        results = mg.merge(clip)
        print(results)

    def test_pattern_generation(self):
        f = set_diamond1
        p = Pattern()
        p.create_from_pattern(f)
        for s in p.generate(0, 0, 1, 1):
            array = np.array(
                [
                    [-1.0 + 0.0j, 0.0 + 0.0j, 41.0 + 0.0j, 0.0 + 0.0j, -0.5 - 0.5j],
                    [-0.5 - 0.5j, 0.0 + 0.0j, 41.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                    [0.0 + 0.0j, 0.0 + 0.0j, 41.0 + 0.0j, 0.0 + 0.0j, -0.5 + 0.5j],
                    [-0.5 + 0.5j, 0.0 + 0.0j, 41.0 + 0.0j, 0.0 + 0.0j, -1.0 + 0.0j],
                ]
            )
            array2 = s.segments[: s.index]
            # self.assertTrue((array == array2).all())

    def test_pattern_generation_counts(self):
        f = set_diamond1
        p = Pattern()
        p.create_from_pattern(f)

        three_x_three_grid = list(p.generate(0, 0, 4, 4))
        # self.assertEqual(len(three_x_three_grid), 16)
        p.set_cell_padding(0.5, 0.5)
        three_x_three_grid = list(p.generate(0, 0, 4, 4))
        # 1 0.5 1 0.5 1 = 4, so 4x4 with 0.5 padding fits 3x3
        # self.assertEqual(len(three_x_three_grid), 9)
        p.set_cell_padding(0, 0)
        for s in p.generate(0, 0, 2, 2):
            print(repr(s))
        print("finished.")

    def test_pattern_clip(self):
        t = time.time()
        f = set_diamond1
        p = Pattern()
        p.create_from_pattern(f)
        poly = Polygon(0 + 2j, 4 + 0j, 4 + 4j, 0 + 2j)
        for i in range(5):
            for e in range(poly.geomstr.index):
                poly.geomstr.split(e, 0.5)
        poly.geomstr.uscale(15)
        q = Clip(poly.geomstr)

        clip = Geomstr()
        for s in list(p.generate(*q.bounds)):
            clip.append(s)

        clipped = q.clip(clip)
        # clipped.uscale(20)
        # print(f"Time took {time.time() - t}")
        #
        # from PIL import ImageDraw, Image
        #
        # x0, y0, x1, y1 = clipped.bbox()
        #
        # img = Image.new("L", size=(int(x1-x0)+20, int(y1-y0) + 20), color="white")
        # draw = ImageDraw.Draw(img)
        # clipped.draw(draw, int(x0) + 10, int(y0) +10)
        # img.save("test.png")

    def test_point_in_polygon_beat(self):
        """
        Raytraced comparison with our geomstr version.

        See:
        https://stackoverflow.com/questions/36399381/whats-the-fastest-way-of-checking-if-a-point-is-inside-a-polygon-in-python
        @return:
        """

        def points_in_polygon(polygon, pts):
            pts = np.asarray(pts, dtype="float32")
            polygon = np.asarray(polygon, dtype="float32")
            contour2 = np.vstack((polygon[1:], polygon[:1]))
            test_diff = contour2 - polygon
            mask1 = (pts[:, None] == polygon).all(-1).any(-1)
            m1 = (polygon[:, 1] > pts[:, None, 1]) != (contour2[:, 1] > pts[:, None, 1])
            slope = ((pts[:, None, 0] - polygon[:, 0]) * test_diff[:, 1]) - (
                test_diff[:, 0] * (pts[:, None, 1] - polygon[:, 1])
            )
            m2 = slope == 0
            mask2 = (m1 & m2).any(-1)
            m3 = (slope < 0) != (contour2[:, 1] < polygon[:, 1])
            m4 = m1 & m3
            count = np.count_nonzero(m4, axis=-1)
            mask3 = ~(count % 2 == 0)
            mask = mask1 | mask2 | mask3
            return mask

        N = 50000
        lenpoly = 1000
        polygon = [
            [np.sin(x) + 0.5, np.cos(x) + 0.5]
            for x in np.linspace(0, 2 * np.pi, lenpoly)
        ]
        polygon = np.array(polygon, dtype="float32")

        points = np.random.uniform(-1.5, 1.5, size=(N, 2)).astype("float32")
        t = time.time()
        mask = points_in_polygon(polygon, points)
        t1 = time.time() - t

        # Convert to correct format.
        points = points[:, 0] + points[:, 1] * 1j
        pg = polygon[:, 0] + polygon[:, 1] * 1j
        poly = Polygon(*pg)
        t = time.time()
        q = Scanbeam(poly.geomstr)
        r = q.points_in_polygon(points)
        t2 = time.time() - t
        for i in range(N):
            if mask[i]:
                self.assertTrue(r[i])
            else:
                self.assertFalse(r[i])
        try:
            print(
                f"geomstr points in poly took {t2} seconds. Raytraced-numpy took {t1}. Speed-up {t1 / t2}x"
            )
        except ZeroDivisionError:
            pass

    def test_point_in_polygon_scanline_beat(self):
        """
        Test point in poly for Scanbeam against simplified version of same algorithm
        @return:
        """

        def build_edge_list(polygon):
            edge_list = []
            for i in range(0, len(polygon) - 1):
                if (polygon[i].imag, polygon[i].real) < (
                    polygon[i + 1].imag,
                    polygon[i + 1].real,
                ):
                    edge_list.append((polygon[i], i))
                    edge_list.append((polygon[i + 1], ~i))
                else:
                    edge_list.append((polygon[i], ~i))
                    edge_list.append((polygon[i + 1], i))

            def sort_key(e):
                return e[0].imag, e[0].real, ~e[1]

            edge_list.sort(key=sort_key)
            return edge_list

        def build_scanbeam(edge_list):
            actives = []
            actives_table = []
            events = []
            y = -float("inf")
            for pt, index in edge_list:
                if y != pt.imag:
                    actives_table.append(list(actives))
                    events.append(pt.imag)
                if index >= 0:
                    actives.append(index)
                else:
                    actives.remove(~index)
                y = pt.imag
            actives_table.append(list(actives))
            largest_actives = max([len(a) for a in actives_table])
            scan = np.zeros((len(actives_table), largest_actives), dtype=int)
            scan -= 1
            for i, active in enumerate(actives_table):
                scan[i, 0 : len(active)] = active
            return scan, events

        def points_in_polygon(polygon, point):
            edge_list = build_edge_list(polygon)
            scan, events = build_scanbeam(edge_list)
            pts_y = np.imag(point)
            idx = np.searchsorted(events, pts_y)
            actives = scan[idx]
            a = polygon[actives]
            b = polygon[actives + 1]

            a = np.where(actives == -1, np.nan + np.nan * 1j, a)
            b = np.where(actives == -1, np.nan + np.nan * 1j, b)

            old_np_seterr = np.seterr(invalid="ignore", divide="ignore")
            try:
                # If horizontal slope is undefined. But, all x-ints are at x since x0=x1
                m = (b.imag - a.imag) / (b.real - a.real)
                y0 = a.imag - (m * a.real)
                ys = np.reshape(np.repeat(np.imag(point), y0.shape[1]), y0.shape)
                x_intercepts = np.where(~np.isinf(m), (ys - y0) / m, a.real)
            finally:
                np.seterr(**old_np_seterr)

            xs = np.reshape(np.repeat(np.real(point), y0.shape[1]), y0.shape)
            results = np.sum(x_intercepts <= xs, axis=1)
            results %= 2
            return results

        N = 5000
        lenpoly = 1000
        polygon = [
            [np.sin(x) + 0.5, np.cos(x) + 0.5]
            for x in np.linspace(0, 2 * np.pi, lenpoly)
        ]
        polygon = np.array(polygon, dtype="float32")

        points = np.random.uniform(-1.5, 1.5, size=(N, 2)).astype("float32")
        points = points[:, 0] + points[:, 1] * 1j
        pg = polygon[:, 0] + polygon[:, 1] * 1j

        t = time.time()
        mask = points_in_polygon(pg, points)
        t1 = time.time() - t

        # Convert to correct format.

        poly = Polygon(*pg)
        t = time.time()
        q = Scanbeam(poly.geomstr)
        r = q.points_in_polygon(points)
        t2 = time.time() - t
        for p1, p2 in zip(r, mask):
            assert bool(p1) == bool(p2)
        try:
            print(
                f"geomstr points in poly took {t2} seconds. Simple Scanline {t1}. Speed-up {t1 / t2}x"
            )
        except ZeroDivisionError:
            pass

    def test_point_in_polygon_beamtable_beat(self):
        """
        Test point in poly for Scanbeam against BeamTable.
        @return:
        """

        N = 100000
        lenpoly = 1000
        polygon = [
            [np.sin(x) + 0.5, np.cos(x) + 0.5]
            for x in np.linspace(0, 2 * np.pi, lenpoly)
        ]
        polygon = np.array(polygon, dtype="float32")

        points = np.random.uniform(-1.5, 1.5, size=(N, 2)).astype("float32")
        points = points[:, 0] + points[:, 1] * 1j
        pg = polygon[:, 0] + polygon[:, 1] * 1j

        # Convert to correct format.
        poly = Polygon(*pg)

        # Scanbeam Timing
        sb1 = time.time()
        q = Scanbeam(poly.geomstr)
        q.compute_beam()

        # ScanBeam PiP
        sb2 = time.time()
        r1 = q.points_in_polygon(points)
        sb3 = time.time()

        # Beam Table calculation.
        bt1 = time.time()
        q = BeamTable(poly.geomstr)
        q.compute_beam()

        # BeamTable Pip
        bt2 = time.time()
        r2 = q.points_in_polygon(points)
        bt3 = time.time()

        for p1, p2 in zip(r1, r2):
            self.assertEqual(bool(p1), bool(p2))
        try:
            print(
                f"ScanBeam PiP: {sb3 - sb2} seconds, {sb3 - sb1} total. Beamtable PiP {bt3 - bt2} seconds, {bt3 - bt1} total."
            )
        except ZeroDivisionError:
            pass

    def test_simplify(self):
        """
        Simplify of large circle.
        """
        lenpoly = 1000
        polygon = [
            [np.sin(x) + 0.5, np.cos(x) + 0.5]
            for x in np.linspace(0, 2 * np.pi, lenpoly)
        ]
        polygon = np.array(polygon, dtype="float32")
        pg = polygon[:, 0] + polygon[:, 1] * 1j
        poly = Polygon(*pg)
        geometry = poly.geomstr
        simplified = geometry.simplify(0.01)
        # With enhanced geometric shape protection, circular shapes preserve more points
        self.assertLessEqual(len(simplified), 150)
        self.assertGreater(len(simplified), 5)

    def test_simplify_rectangle(self):
        """Test rectangle protection from over-simplification."""
        rectangle_points = np.array([(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)], dtype=np.float32)
        rectangle_complex = rectangle_points[:, 0] + rectangle_points[:, 1] * 1j
        poly = Polygon(*rectangle_complex)
        poly.geomstr.close()
        geometry = poly.geomstr
        simplified = geometry.simplify(1.0)
        self.assertEqual(len(simplified), 4, "Rectangle should preserve all 4 vertices")

    def test_simplify_triangle(self):
        """Test triangle protection from over-simplification."""
        triangle_points = np.array([(0.0, 0.0), (5.0, 10.0), (10.0, 0.0)], dtype=np.float32)
        triangle_complex = triangle_points[:, 0] + triangle_points[:, 1] * 1j
        poly = Polygon(*triangle_complex)
        poly.geomstr.close()
        geometry = poly.geomstr
        simplified = geometry.simplify(1.0)
        self.assertEqual(len(simplified), 3, "Triangle should preserve all 3 vertices")

    def test_simplify_regular_polygon(self):
        """Test regular polygon protection from over-simplification."""
        geometry = Geomstr.regular_polygon(6, 0 + 0j, radius=10)
        simplified = geometry.simplify(1.0)
        self.assertEqual(len(simplified), 6, "Regular hexagon should preserve all 6 vertices")

    def test_simplify_small_shape_high_tolerance(self):
        """Test protection of small shapes with high tolerance values."""
        small_rect = np.array([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)], dtype=np.float32)
        small_rect_complex = small_rect[:, 0] + small_rect[:, 1] * 1j
        poly = Polygon(*small_rect_complex)
        poly.geomstr.close()
        geometry = poly.geomstr
        simplified = geometry.simplify(10.0)
        self.assertGreaterEqual(len(simplified), 4, "Small rectangle should be protected even with high tolerance")

    def test_simplify_star_shape(self):
        """Test star shape protection from over-simplification."""
        import math
        n = 5
        outer_r = 10
        inner_r = 4
        star_points = []
        for i in range(n):
            angle = 2 * math.pi * i / n - math.pi / 2
            star_points.append((outer_r * math.cos(angle), outer_r * math.sin(angle)))
            angle += math.pi / n
            star_points.append((inner_r * math.cos(angle), inner_r * math.sin(angle)))
        
        star_array = np.array(star_points, dtype=np.float32)
        star_complex = star_array[:, 0] + star_array[:, 1] * 1j
        poly = Polygon(*star_complex)
        poly.geomstr.close()
        geometry = poly.geomstr
        simplified = geometry.simplify(1.0)
        self.assertEqual(len(simplified), 10, "Star should preserve all 10 vertices")

    def test_simplify_large_shape_low_tolerance(self):
        """Test that large shapes with low tolerance still get simplified appropriately."""
        base_rect = np.array([(0.0, 0.0), (100.0, 0.0), (100.0, 50.0), (0.0, 50.0)], dtype=np.float32)
        noisy_points = []
        for i, point in enumerate(base_rect):
            noisy_points.append(point)
            if i < len(base_rect) - 1:
                for j in range(3):
                    noise_x = point[0] + (0.01 * (j + 1))
                    noise_y = point[1] + (0.01 * (j + 1) if j % 2 else -0.01 * (j + 1))
                    noisy_points.append((noise_x, noise_y))
        
        noisy_array = np.array(noisy_points, dtype=np.float32)
        noisy_complex = noisy_array[:, 0] + noisy_array[:, 1] * 1j
        poly = Polygon(*noisy_complex)
        poly.geomstr.close()
        geometry = poly.geomstr
        simplified = geometry.simplify(0.5)
        self.assertGreaterEqual(len(simplified), 4, "Should preserve at least the 4 core rectangle vertices")
        self.assertLess(len(simplified), len(noisy_points), "Should simplify some noise points")

    def test_simplify_convex_shape(self):
        """Test protection of convex shapes (like rounded rectangles)."""
        points = []
        # Top line
        points.extend([(-5 + i, 5) for i in np.linspace(0, 10, 10)])
        # Right arc
        points.extend([(5 + 5 * np.cos(a), 5 * np.sin(a)) for a in np.linspace(np.pi/2, -np.pi/2, 10)])
        # Bottom line
        points.extend([(5 - i, -5) for i in np.linspace(0, 10, 10)])
        # Left arc
        points.extend([(-5 + 5 * np.cos(a), 5 * np.sin(a)) for a in np.linspace(-np.pi/2, -3*np.pi/2, 10)])
        
        points_array = np.array(points, dtype=np.float32)
        points_complex = points_array[:, 0] + points_array[:, 1] * 1j
        
        poly = Polygon(*points_complex)
        poly.geomstr.close()
        geometry = poly.geomstr
        
        # Simplify with a tolerance that would normally turn this into a rectangle
        simplified = geometry.simplify(1.0)
        
        # Should preserve curvature, so significantly more than 4 points
        self.assertGreater(len(simplified), 10, "Rounded rectangle should preserve curvature")

    def test_simplify_tiny_artifact(self):
        """Test protection of very small shapes using adaptive tolerance."""
        w, h = 1.9, 0.4
        points = [(0, 0), (w, 0), (w, h), (0, h)]
        points_array = np.array(points, dtype=np.float32)
        points_complex = points_array[:, 0] + points_array[:, 1] * 1j
        
        poly = Polygon(*points_complex)
        poly.geomstr.close()
        geometry = poly.geomstr
        
        # Simplify with a tolerance that is large relative to the shape
        # But the adaptive logic should clamp it to ~2% of diagonal
        simplified = geometry.simplify(0.1)
        
        self.assertEqual(len(simplified), 4, "Tiny rectangle should be preserved")
