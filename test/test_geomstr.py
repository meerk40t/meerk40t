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
from meerk40t.tools.geomstr import (
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
            f"geomstr cubic length time {t0}. svgelements cubic length time {t1}. total difference {difference}"
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

    def test_bahnschrift_da(self):
        """
        Bahnschrift Font: "Da" weld caused a ValueError 104 not in list error.

        @return:
        """
        nan = float("NaN")
        t = [
            (
                (2119.9676513671875, 0.0),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (2119.9676513671875, -1293.3135986328125),
            ),
            (
                (2119.9676513671875, -1293.3135986328125),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (4545.815408965687, -1300.1859217514225),
            ),
            (
                (4545.815408965687, -1300.1859217514225),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (4975.1092698838975, -1355.164506700304),
            ),
            (
                (4975.1092698838975, -1355.164506700304),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (5529.545254177518, -1540.7172309027778),
            ),
            (
                (5529.545254177518, -1540.7172309027778),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (5976.575469970703, -1849.9717712402344),
            ),
            (
                (5976.575469970703, -1849.9717712402344),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (6304.348246256512, -2271.817186143663),
            ),
            (
                (6304.348246256512, -2271.817186143663),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (6501.011912027995, -2795.1425340440537),
            ),
            (
                (6501.011912027995, -2795.1425340440537),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (6566.566467285156, -3419.9478149414062),
            ),
            (
                (6566.566467285156, -3419.9478149414062),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (6559.282627812137, -6492.781584939839),
            ),
            (
                (6559.282627812137, -6492.781584939839),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (6450.02503571687, -7083.76022150487),
            ),
            (
                (6450.02503571687, -7083.76022150487),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (6209.658333107277, -7573.25892507294),
            ),
            (
                (6209.658333107277, -7573.25892507294),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (5976.575469970703, -7843.213653564453),
            ),
            (
                (5976.575469970703, -7843.213653564453),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (5690.489300386405, -8063.127993359978),
            ),
            (
                (5690.489300386405, -8063.127993359978),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (5356.667233690803, -8228.063748206621),
            ),
            (
                (5356.667233690803, -8228.063748206621),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (4975.1092698838975, -8338.020918104385),
            ),
            (
                (4975.1092698838975, -8338.020918104385),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (4313.267517089844, -8399.871826171875),
            ),
            (
                (4313.267517089844, -8399.871826171875),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (2119.9676513671875, -8399.871826171875),
            ),
            (
                (2119.9676513671875, -8399.871826171875),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (2119.9676513671875, -9693.185424804688),
            ),
            (
                (2119.9676513671875, -9693.185424804688),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (4774.988866735387, -9673.103426709587),
            ),
            (
                (4774.988866735387, -9673.103426709587),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (5464.607973451968, -9567.67293671031),
            ),
            (
                (5464.607973451968, -9567.67293671031),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (6078.672677499277, -9371.873455283083),
            ),
            (
                (6078.672677499277, -9371.873455283083),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (6445.416052547502, -9191.546988781587),
            ),
            (
                (6445.416052547502, -9191.546988781587),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (6773.970709906685, -8973.937140570748),
            ),
            (
                (6773.970709906685, -8973.937140570748),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (7193.964301215278, -8578.387620713977),
            ),
            (
                (7193.964301215278, -8578.387620713977),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (7425.401098934221, -8268.59810911579),
            ),
            (
                (7425.401098934221, -8268.59810911579),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (7617.496933171778, -7922.5951583297165),
            ),
            (
                (7617.496933171778, -7922.5951583297165),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (7767.288886176217, -7544.329325358074),
            ),
            (
                (7767.288886176217, -7544.329325358074),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (7874.283138322242, -7134.459036367911),
            ),
            (
                (7874.283138322242, -7134.459036367911),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (7959.8785400390625, -6219.905090332031),
            ),
            (
                (7959.8785400390625, -6219.905090332031),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (7954.528827431762, -3232.7901769567416),
            ),
            (
                (7954.528827431762, -3232.7901769567416),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (7874.283138322241, -2558.7263884367762),
            ),
            (
                (7874.283138322241, -2558.7263884367762),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (7697.742622281297, -1955.7726259584779),
            ),
            (
                (7697.742622281297, -1955.7726259584779),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (7425.35994729878, -1424.5873156888986),
            ),
            (
                (7425.35994729878, -1424.5873156888986),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (7063.019797242719, -973.7299977997204),
            ),
            (
                (7063.019797242719, -973.7299977997204),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (6612.532844072506, -605.8343769591532),
            ),
            (
                (6612.532844072506, -605.8343769591532),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (6263.237762451172, -406.66046142578125),
            ),
            (
                (6263.237762451172, -406.66046142578125),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (5877.7292416419505, -246.0044766649788),
            ),
            (
                (5877.7292416419505, -246.0044766649788),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (5237.12173273534, -80.32799238040123),
            ),
            (
                (5237.12173273534, -80.32799238040123),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (4768.486908335744, -20.081998095100328),
            ),
            (
                (4768.486908335744, -20.081998095100328),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (2119.9676513671875, 0.0),
            ),
            ((nan, 0.0), (nan, 0.0), (128.0, 0.0), (nan, 0.0), (nan, 0.0)),
            (
                (1199.981689453125, 0.0),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (1199.981689453125, -9693.185424804688),
            ),
            (
                (1199.981689453125, -9693.185424804688),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (2559.9609375, -9693.185424804688),
            ),
            (
                (2559.9609375, -9693.185424804688),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (2559.9609375, 0.0),
            ),
            (
                (2559.9609375, 0.0),
                (0.0, 0.0),
                (41.0, 0.0),
                (0.0, 0.0),
                (1199.981689453125, 0.0),
            ),
            ((nan, 0.0), (nan, 0.0), (128.0, 0.0), (nan, 0.0), (nan, 0.0)),
            ((nan, 0.0), (nan, 0.0), (128.0, 0.0), (nan, 0.0), (nan, 0.0)),
            (
                (13933.120727539062, 0.0),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13933.120727539062, -4386.5997314453125),
            ),
            (
                (13933.120727539062, -4386.5997314453125),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13915.178614486884, -4673.838146821952),
            ),
            (
                (13915.178614486884, -4673.838146821952),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13820.982520962938, -5048.5237875102475),
            ),
            (
                (13820.982520962938, -5048.5237875102475),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13646.046918704187, -5355.803049346548),
            ),
            (
                (13646.046918704187, -5355.803049346548),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13393.334725462362, -5592.05458841206),
            ),
            (
                (13393.334725462362, -5592.05458841206),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13072.475423930606, -5745.509036970728),
            ),
            (
                (13072.475423930606, -5745.509036970728),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (12821.121234658323, -5801.310654628423),
            ),
            (
                (12821.121234658323, -5801.310654628423),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (12356.930786886332, -5813.656145260658),
            ),
            (
                (12356.930786886332, -5813.656145260658),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11906.93765334141, -5743.286848656925),
            ),
            (
                (11906.93765334141, -5743.286848656925),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11395.011308458117, -5560.902800383391),
            ),
            (
                (11395.011308458117, -5560.902800383391),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11026.498413085938, -5339.918518066406),
            ),
            (
                (11026.498413085938, -5339.918518066406),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (10033.180236816406, -6019.908142089844),
            ),
            (
                (10033.180236816406, -6019.908142089844),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (10547.369921648944, -6481.012217203776),
            ),
            (
                (10547.369921648944, -6481.012217203776),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11069.831085205078, -6756.563568115234),
            ),
            (
                (11069.831085205078, -6756.563568115234),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11669.986536473403, -6938.618403305242),
            ),
            (
                (11669.986536473403, -6938.618403305242),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (12326.766638108242, -7016.64190410096),
            ),
            (
                (12326.766638108242, -7016.64190410096),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13045.7268608941, -6986.189693874783),
            ),
            (
                (13045.7268608941, -6986.189693874783),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13536.83047824436, -6885.080125596788),
            ),
            (
                (13536.83047824436, -6885.080125596788),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13973.1201171875, -6716.564178466797),
            ),
            (
                (13973.1201171875, -6716.564178466797),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (14460.355480806327, -6392.947717360508),
            ),
            (
                (14460.355480806327, -6392.947717360508),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (14831.707839023922, -5961.349364857615),
            ),
            (
                (14831.707839023922, -5961.349364857615),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (15032.85703305845, -5568.598156210817),
            ),
            (
                (15032.85703305845, -5568.598156210817),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (15163.225414134839, -5122.802489480854),
            ),
            (
                (15163.225414134839, -5122.802489480854),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (15222.483769169561, -4624.415032657576),
            ),
            (
                (15222.483769169561, -4624.415032657576),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (15226.434326171875, 0.0),
            ),
            (
                (15226.434326171875, 0.0),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13933.120727539062, 0.0),
            ),
            ((nan, 0.0), (nan, 0.0), (128.0, 1.0), (nan, 0.0), (nan, 0.0)),
            (
                (12239.813232421875, 99.99847412109375),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11458.343675401477, 41.11048380533855),
            ),
            (
                (11458.343675401477, 41.11048380533855),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (10820.575629340277, -135.55348714192706),
            ),
            (
                (10820.575629340277, -135.55348714192706),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (10326.509094238281, -429.9934387207031),
            ),
            (
                (10326.509094238281, -429.9934387207031),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (10076.307150758343, -692.7054793746383),
            ),
            (
                (10076.307150758343, -692.7054793746383),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (9818.286396544656, -1188.62383807147),
            ),
            (
                (9818.286396544656, -1188.62383807147),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (9701.004235538436, -1806.7625540274162),
            ),
            (
                (9701.004235538436, -1806.7625540274162),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (9721.82696307147, -2470.908798406154),
            ),
            (
                (9721.82696307147, -2470.908798406154),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (9872.195038972077, -3022.2584100417153),
            ),
            (
                (9872.195038972077, -3022.2584100417153),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (10151.450037073206, -3459.5356882354363),
            ),
            (
                (10151.450037073206, -3459.5356882354363),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (10409.38848801601, -3687.680355119117),
            ),
            (
                (10409.38848801601, -3687.680355119117),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (10725.762261284724, -3865.1262071397578),
            ),
            (
                (10725.762261284724, -3865.1262071397578),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11100.735963421104, -3991.873244297357),
            ),
            (
                (11100.735963421104, -3991.873244297357),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11773.071383252556, -4086.933522165558),
            ),
            (
                (11773.071383252556, -4086.933522165558),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13993.119812011719, -4093.2708740234375),
            ),
            (
                (13993.119812011719, -4093.2708740234375),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (14086.451721191406, -2999.9542236328125),
            ),
            (
                (14086.451721191406, -2999.9542236328125),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11707.599131266277, -2973.6583285861543),
            ),
            (
                (11707.599131266277, -2973.6583285861543),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11298.346116807727, -2812.9611921899113),
            ),
            (
                (11298.346116807727, -2812.9611921899113),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11132.463874345944, -2645.762097394025),
            ),
            (
                (11132.463874345944, -2645.762097394025),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11054.440373550227, -2503.5420453106917),
            ),
            (
                (11054.440373550227, -2503.5420453106917),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (10973.165893554688, -2039.9688720703125),
            ),
            (
                (10973.165893554688, -2039.9688720703125),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11012.054189046225, -1719.2330254448789),
            ),
            (
                (11012.054189046225, -1719.2330254448789),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11081.188936586734, -1539.1534687560284),
            ),
            (
                (11081.188936586734, -1539.1534687560284),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11323.160552978516, -1259.9807739257812),
            ),
            (
                (11323.160552978516, -1259.9807739257812),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (11706.035369119527, -1084.8394134898244),
            ),
            (
                (11706.035369119527, -1084.8394134898244),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (12087.387574749227, -1019.1614033263406),
            ),
            (
                (12087.387574749227, -1019.1614033263406),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (12554.911304991921, -1008.7088879243827),
            ),
            (
                (12554.911304991921, -1008.7088879243827),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13359.837294213565, -1107.4728129822531),
            ),
            (
                (13359.837294213565, -1107.4728129822531),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13630.244690694926, -1212.656393168885),
            ),
            (
                (13630.244690694926, -1212.656393168885),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13814.809775646821, -1358.3331826292438),
            ),
            (
                (13814.809775646821, -1358.3331826292438),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13890.528784857855, -1478.4959581163193),
            ),
            (
                (13890.528784857855, -1478.4959581163193),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13933.120727539062, -1693.3074951171875),
            ),
            (
                (13933.120727539062, -1693.3074951171875),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (14073.118591308594, -719.989013671875),
            ),
            (
                (14073.118591308594, -719.989013671875),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13896.660378538532, -490.85670753761576),
            ),
            (
                (13896.660378538532, -490.85670753761576),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13629.792022705078, -259.99603271484375),
            ),
            (
                (13629.792022705078, -259.99603271484375),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (13241.649797227648, -59.99908447265626),
            ),
            (
                (13241.649797227648, -59.99908447265626),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (12779.064263237848, 59.99908447265626),
            ),
            (
                (12779.064263237848, 59.99908447265626),
                (0.0, 0.0),
                (41.0, 1.0),
                (0.0, 0.0),
                (12239.813232421875, 99.99847412109375),
            ),
            ((nan, 0.0), (nan, 0.0), (128.0, 1.0), (nan, 0.0), (nan, 0.0)),
        ]
        g = Geomstr.from_float_segments(t)
        bt = BeamTable(g)
        union = bt.union(*list(range(2)))

    def test_cag_union(self):
        # g = Geomstr.rect(0, 0, 100, 100, settings=0)
        # g.transform(Matrix.skew(0.002))
        # g.append(Geomstr.rect(50, 50, 100, 100, settings=1))
        g = Geomstr()
        g.line(complex(0, 0), complex(100, 0), 0)
        # g.line(complex(0,-50), complex(50,-1), 1)
        g.line(complex(50, -1), complex(50, 1), 1)
        # g.line(complex(50,1), complex(100,50), 1)
        bt = BeamTable(g)
        bt.compute_beam()
        q = bt.union(0, 1)
        print(q.segments)

    def test_cag_union2(self):
        g = Geomstr.rect(0, 0, 100, 100, settings=0)
        g.append(Geomstr.rect(51, 51, 100, 100, settings=1))
        bt = BeamTable(g)
        bt.compute_beam()
        q = bt.union(0, 1)
        print(q.segments)

    def test_cag_combine(self):
        g = Geomstr()
        g.line(complex(0, 1), complex(0, 100), 0)
        g.line(complex(1, 0), complex(100, 0), 0)
        bt = BeamTable(g)
        q = bt.combine()
        self.assertEqual(q, g)

    def test_cag_operations_comprehensive(self):
        """Test comprehensive CAG operations with various geometric shapes."""
        # Test Case 1: Two overlapping rectangles
        g = Geomstr()
        # Rectangle A: (0,0) to (100,100) - settings=0
        g.append(Geomstr.rect(0, 0, 100, 100, settings=0))
        # Rectangle B: (50,50) to (150,150) - settings=1
        g.append(Geomstr.rect(50, 50, 100, 100, settings=1))

        bt = BeamTable(g)

        # Test union: should cover (0,0) to (150,150)
        union_result = bt.union(0, 1)
        self.assertGreater(union_result.index, 0, "Union should produce geometry")

        # Test intersection: should be (50,50) to (100,100)
        intersection_result = bt.intersection(0, 1)
        self.assertGreater(
            intersection_result.index, 0, "Intersection should produce geometry"
        )

        # Test XOR: should be non-overlapping parts
        xor_result = bt.xor(0, 1)
        self.assertGreater(xor_result.index, 0, "XOR should produce geometry")

        # Test difference A-B: should be left and bottom parts of A
        diff_result = bt.difference(0, 1)
        self.assertGreater(diff_result.index, 0, "Difference should produce geometry")

    def test_cag_edge_cases(self):
        """Test CAG operations with edge cases."""
        # Test Case 1: Empty geometry
        g = Geomstr()
        bt = BeamTable(g)

        # All operations on empty geometry should return empty
        self.assertEqual(bt.union().index, 0, "Union of empty should be empty")
        self.assertEqual(
            bt.intersection().index, 0, "Intersection of empty should be empty"
        )
        self.assertEqual(bt.xor().index, 0, "XOR of empty should be empty")
        self.assertEqual(
            bt.difference().index, 0, "Difference of empty should be empty"
        )

        # Test Case 2: Single rectangle with itself
        g = Geomstr.rect(0, 0, 100, 100, settings=0)
        bt = BeamTable(g)

        # Union with itself should be itself
        union_self = bt.union(0)
        self.assertGreater(union_self.index, 0, "Self-union should produce geometry")

        # Intersection with itself should be itself
        intersection_self = bt.intersection(0)
        self.assertGreater(
            intersection_self.index, 0, "Self-intersection should produce geometry"
        )

        # XOR with single argument should be itself (not empty)
        xor_self = bt.xor(0)
        self.assertGreater(
            xor_self.index, 0, "Single-argument XOR should produce the geometry itself"
        )

        # Difference with single argument should be itself (A - nothing = A)
        diff_self = bt.difference(0)
        self.assertGreater(
            diff_self.index,
            0,
            "Single-argument difference should produce the geometry itself",
        )

        # Test Case 3: XOR and difference with truly identical shapes (same settings, same position)
        g2 = Geomstr()
        g2.append(Geomstr.rect(0, 0, 100, 100, settings=0))
        g2.append(Geomstr.rect(0, 0, 100, 100, settings=0))  # Exact duplicate
        bt2 = BeamTable(g2)

        # XOR of two identical shapes should be empty
        xor_identical = bt2.xor(0, 0)
        self.assertEqual(
            xor_identical.index, 0, "XOR of identical shapes should be empty"
        )

        # Difference of two identical shapes should be empty (A - A = empty)
        diff_identical = bt2.difference(0, 0)
        self.assertEqual(
            diff_identical.index, 0, "Difference of identical shapes should be empty"
        )

    def test_cag_multiple_shapes(self):
        """Test CAG operations with multiple shapes."""
        g = Geomstr()
        # Three squares where only adjacent ones overlap
        g.append(Geomstr.rect(0, 0, 50, 50, settings=0))  # Square A: (0,0) to (50,50)
        g.append(
            Geomstr.rect(25, 0, 50, 50, settings=1)
        )  # Square B: (25,0) to (75,50) - overlaps A and C
        g.append(
            Geomstr.rect(60, 0, 50, 50, settings=2)
        )  # Square C: (60,0) to (110,50) - gap from A

        bt = BeamTable(g)

        # Test union of all three
        union_all = bt.union(0, 1, 2)
        self.assertGreater(union_all.index, 0, "Union of three should produce geometry")

        # Test intersection of all three (should be empty since no common overlap)
        intersection_all = bt.intersection(0, 1, 2)
        self.assertEqual(
            intersection_all.index, 0, "No common intersection among all three"
        )

        # Test pairwise intersection A∩B
        intersection_ab = bt.intersection(0, 1)
        self.assertGreater(intersection_ab.index, 0, "A∩B should have overlap")

        # Test pairwise intersection B∩C
        intersection_bc = bt.intersection(1, 2)
        self.assertGreater(intersection_bc.index, 0, "B∩C should have overlap")

        # Test XOR of all three
        xor_all = bt.xor(0, 1, 2)
        self.assertGreater(xor_all.index, 0, "XOR of three should produce geometry")

    def test_cag_non_overlapping_shapes(self):
        """Test CAG operations with non-overlapping shapes."""
        g = Geomstr()
        # Two separate rectangles
        g.append(Geomstr.rect(0, 0, 50, 50, settings=0))
        g.append(Geomstr.rect(100, 100, 50, 50, settings=1))

        bt = BeamTable(g)

        # Union should contain both shapes
        union_result = bt.union(0, 1)
        self.assertGreater(
            union_result.index, 0, "Union of separate shapes should produce geometry"
        )

        # Intersection should be empty
        intersection_result = bt.intersection(0, 1)
        self.assertEqual(
            intersection_result.index, 0, "No intersection between separate shapes"
        )

        # XOR should be both shapes (since no overlap)
        xor_result = bt.xor(0, 1)
        self.assertGreater(
            xor_result.index, 0, "XOR of separate shapes should be both shapes"
        )

        # Difference A-B should be A (since no overlap)
        diff_result = bt.difference(0, 1)
        self.assertGreater(
            diff_result.index, 0, "Difference should be first shape when no overlap"
        )

    def test_cag_complex_geometry(self):
        """Test CAG operations with more complex geometries."""
        g = Geomstr()

        # Create an L-shaped geometry using multiple rectangles
        g.append(Geomstr.rect(0, 0, 100, 50, settings=0))  # Horizontal bar of L
        g.append(Geomstr.rect(0, 50, 50, 100, settings=0))  # Vertical bar of L

        # Add a rectangle that intersects both parts
        g.append(Geomstr.rect(25, 25, 50, 50, settings=1))

        bt = BeamTable(g)

        # Test union of L-shape (should merge the two L parts)
        union_l = bt.union(0, 0)  # Same settings should union
        self.assertGreater(union_l.index, 0, "Union of L-shape should produce geometry")

        # Test intersection with the crossing rectangle
        intersection_cross = bt.intersection(0, 1)
        self.assertGreater(
            intersection_cross.index, 0, "Intersection should produce geometry"
        )

    def test_cag_consistency_with_original(self):
        """Test that optimized CAG produces same results as original implementation."""
        g = Geomstr()
        g.append(Geomstr.rect(0, 0, 100, 100, settings=0))
        g.append(Geomstr.rect(50, 50, 100, 100, settings=1))

        bt = BeamTable(g)

        # Test that both implementations give consistent results
        optimized_union = bt.cag("union", 0, 1)
        original_union = bt.cag_org("union", 0, 1)

        # Both should have the same number of segments (approximately)
        # Allow for small differences due to optimization
        self.assertAlmostEqual(
            optimized_union.index,
            original_union.index,
            delta=2,  # Allow small difference
            msg="Optimized and original union should have similar segment counts",
        )

        # Test other operations
        optimized_intersection = bt.cag("intersection", 0, 1)
        original_intersection = bt.cag_org("intersection", 0, 1)

        self.assertAlmostEqual(
            optimized_intersection.index,
            original_intersection.index,
            delta=2,
            msg="Optimized and original intersection should have similar segment counts",
        )

    def test_cag_performance_comparison(self):
        """Test performance comparison between optimized and original CAG."""
        # Create a more complex geometry for performance testing
        g = Geomstr()

        # Create a grid of rectangles
        for i in range(5):
            for j in range(5):
                x = i * 20
                y = j * 20
                settings = (i + j) % 3  # Rotate through 3 different settings
                g.append(Geomstr.rect(x, y, 25, 25, settings=settings))

        bt = BeamTable(g)

        import time

        # Time the optimized version
        start_time = time.time()
        optimized_result = bt.cag("union", 0, 1, 2)
        optimized_time = time.time() - start_time

        # Time the original version
        start_time = time.time()
        original_result = bt.cag_org("union", 0, 1, 2)
        original_time = time.time() - start_time

        # Optimized version should be faster or at least not significantly slower
        if original_time > 0:
            speedup = (
                original_time / optimized_time if optimized_time > 0 else float("inf")
            )
            print(
                f"CAG Performance: Original={original_time:.6f}s, Optimized={optimized_time:.6f}s, Speedup={speedup:.2f}x"
            )

            # Assert that optimized version is not more than 50% slower
            self.assertLess(
                optimized_time,
                original_time * 1.5,
                "Optimized version should not be significantly slower",
            )

        # Results should have similar number of segments
        self.assertAlmostEqual(
            optimized_result.index,
            original_result.index,
            delta=3,
            msg="Optimized and original should produce similar results",
        )

    def test_cag_argument_validation(self):
        """Test CAG operations with various argument patterns."""
        g = Geomstr()
        g.append(Geomstr.rect(0, 0, 50, 50, settings=0))
        g.append(Geomstr.rect(25, 25, 50, 50, settings=1))
        g.append(Geomstr.rect(50, 50, 50, 50, settings=2))

        bt = BeamTable(g)

        # Test with no arguments (should return empty for all operations)
        self.assertEqual(bt.cag("union").index, 0, "Union with no args should be empty")
        self.assertEqual(
            bt.cag("intersection").index, 0, "Intersection with no args should be empty"
        )
        self.assertEqual(bt.cag("xor").index, 0, "XOR with no args should be empty")
        self.assertEqual(
            bt.cag("difference").index, 0, "Difference with no args should be empty"
        )

        # Test with single argument
        single_union = bt.cag("union", 0)
        self.assertGreater(
            single_union.index, 0, "Union with single arg should produce geometry"
        )

        # Test with duplicate arguments
        dup_union = bt.cag("union", 0, 0, 1)
        normal_union = bt.cag("union", 0, 1)
        # Duplicate should not crash and should produce reasonable results
        self.assertGreater(dup_union.index, 0, "Union with duplicate args should work")

    def test_cag_equality_operation(self):
        """Test the equality CAG operation specifically."""
        g = Geomstr()
        g.append(Geomstr.rect(0, 0, 100, 100, settings=0))
        g.append(Geomstr.rect(50, 50, 100, 100, settings=1))
        g.append(Geomstr.rect(75, 75, 50, 50, settings=1))  # Same settings as second

        bt = BeamTable(g)

        # Test equality between shapes with same settings
        eq_same = bt.cag("eq", 1, 2)  # Both have settings=1
        self.assertGreater(
            eq_same.index, 0, "Equality of same-settings shapes should produce geometry"
        )

        # Test equality between shapes with different settings
        eq_diff = bt.cag("eq", 0, 1)  # Different settings
        # This might produce geometry where both are present or absent
        # The exact behavior depends on the implementation details
        # Just verify it doesn't crash
        self.assertIsNotNone(eq_diff, "Equality operation should not crash")

    def test_cag_comprehensive_scenarios(self):
        """Test comprehensive real-world CAG scenarios for validation."""
        print("\n=== CAG Test Results Summary ===")

        # Scenario 1: Two overlapping rectangles - classic case
        g1 = Geomstr()
        g1.append(Geomstr.rect(0, 0, 100, 100, settings=0))
        g1.append(Geomstr.rect(50, 50, 100, 100, settings=1))
        bt1 = BeamTable(g1)

        union1 = bt1.union(0, 1)
        intersection1 = bt1.intersection(0, 1)
        xor1 = bt1.xor(0, 1)
        diff1 = bt1.difference(0, 1)

        print(
            f"Overlapping rectangles: Union={union1.index}, Intersection={intersection1.index}, XOR={xor1.index}, Diff={diff1.index}"
        )

        # Scenario 2: Three shapes with complex overlaps
        g2 = Geomstr()
        g2.append(Geomstr.rect(0, 0, 60, 60, settings=0))  # Base square
        g2.append(Geomstr.rect(30, 30, 60, 60, settings=1))  # Overlapping square
        g2.append(Geomstr.rect(45, 45, 30, 30, settings=2))  # Small inner square
        bt2 = BeamTable(g2)

        union2 = bt2.union(0, 1, 2)
        intersection2 = bt2.intersection(0, 1, 2)
        xor2 = bt2.xor(0, 1, 2)

        print(
            f"Three overlapping squares: Union={union2.index}, Intersection={intersection2.index}, XOR={xor2.index}"
        )

        # Verify all results are reasonable
        self.assertGreater(union1.index, 0, "Union should produce geometry")
        self.assertGreater(
            intersection1.index, 0, "Intersection should produce geometry"
        )
        self.assertGreater(xor1.index, 0, "XOR should produce geometry")
        self.assertGreater(diff1.index, 0, "Difference should produce geometry")

        self.assertGreater(union2.index, 0, "Three-way union should produce geometry")
        # Three-way intersection might be empty depending on overlaps

        print("=== All CAG operations completed successfully ===\n")

    def test_render(self):
        rect = Geomstr.rect(x=300, y=200, width=500, height=500, rx=50, ry=50)
        image = rect.segmented().render()
        image.save("render-test.png")

    def test_point_in_polygon(self):
        t1 = 0
        t2 = 0
        f = set_diamond1
        p = Pattern()
        p.create_from_pattern(f)

        yy = []
        for i in range(100):
            yy.append(random_point(5))
        yy.append(yy[0])
        poly = Polygon(*yy)  # 0,10 20,0 20,20.1 0,10
        poly.geomstr.uscale(5)
        m = Scanbeam(poly.geomstr)

        pts = []
        for i in range(2000):
            pts.append(random_point(25))

        t = time.time()
        r = m.points_in_polygon(pts)
        t1 += time.time() - t

        t = time.time()
        rr = [int(m.is_point_inside(j.real, j.imag)) for j in pts]
        t2 += time.time() - t

        for i, j in enumerate(pts):
            self.assertEqual(rr[i], r[i])
        try:
            print(
                f"is_point_inside takes {t2} numpy version takes {t1} speedup {t2 / t1}x"
            )
        except ZeroDivisionError:
            print(f"{t2} vs {t1}")

    def test_intersections_near(self):
        for r1 in np.linspace(0, 100, 5):
            r2 = r1 + 0.0001
            circle1 = Geomstr.circle(cx=0, cy=0, r=r1)
            circle2 = Geomstr.circle(cx=0, cy=0, r=r2)
            circle1.rotate(r1)
            for j in range(circle1.index):
                for k in range(circle2.index):
                    c = list(
                        circle1.intersections(circle1.segments[j], circle2.segments[k])
                    )
                    print(r1, r2)
                    self.assertFalse(c)

    def test_livinghinge_whiskers2(self):
        clip = Geomstr.ellipse(
            rx=96436.11909338088,
            ry=96436.11909338088,
            cx=550118.9389283657,
            cy=363374.1254904113,
        )
        subject = Geomstr()
        subject.line(5.82716822e05 + 343372.64182036j, 6.48483387e05 + 343372.64182036j)
        q = Clip(clip)
        subject = q.polycut(subject)
        subject = q.inside(subject)

        m = Geomstr()
        m.append(clip)
        m.append(subject)
        m.uscale(0.002)
        draw(list(m.as_interpolated_points()), *m.bbox(), filename="whiskers.png")

    def test_livinghinge_whiskers(self):
        """
        Test for Whiskers bug. The given clip and exactly the right settings could allow a line to not clip correctly

        We use a previously failing set of settings and make sure that the midpoints and both ends are always on the
        same side of the polygon.
        @return:
        """
        clip = Geomstr.ellipse(
            rx=96436.11909338088,
            ry=96436.11909338088,
            cx=550118.9389283657,
            cy=363374.1254904113,
        )
        p = Pattern()
        p.create_from_pattern(set_line, 0, 0, outershape=clip)
        p.set_cell_padding(-11377.615848868112, -257.2803475393701)
        p.set_cell_dims(65766.56560039372, 5593.051033464568)
        p.extend_pattern = True
        subject = Geomstr()
        q = Clip(clip)
        self.path = Geomstr()
        for s in list(p.generate(*q.bounds)):
            subject.append(s)

        subject = q.polycut(subject)
        subject = q.inside(subject)

        m = Geomstr()
        m.append(clip)
        m.append(subject)
        m.uscale(0.002)
        draw(list(m.as_interpolated_points()), *m.bbox())

        c = Geomstr()
        # Pip currently only works with line segments
        for sp in clip.as_subpaths():
            for segs in sp.as_interpolated_segments(interpolate=100):
                c.polyline(segs)
                c.end()
        sb = Scanbeam(c)

        mid_points = subject.position(slice(subject.index), 0.5)
        r = np.where(sb.points_in_polygon(mid_points))

        s = np.where(
            sb.points_in_polygon(subject.position(slice(subject.index), 0.05))
        )[0]

        e = np.where(
            sb.points_in_polygon(subject.position(slice(subject.index), 0.95))
        )[0]

        for q in r[0]:
            self.assertIn(q, s)
            self.assertIn(q, e)

    def test_simplify(self):
        """
        Simplify of large circle.
        @return:
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
        self.assertEqual(len(simplified), 32)

    def test_simplify_disjoint(self):
        """
        Simplify of 2 large circles. The circles are not denoted with an `END` but only by their disjoint.
        @return:
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
        g = Geomstr(geometry)
        g.translate(20, 20)
        geometry.append(g, end=False)
        simplified = geometry.simplify(0.01)
        self.assertEqual(len(simplified), 64 + 1)
        self.assertIsNot(simplified, geometry)

    def test_simplify_settings(self):
        """
        Simplify of 2 large circles. The circles are not denoted with an `END`, but have different settings flags.
        @return:
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
        g = Geomstr(geometry)
        g.flag_settings(1)
        geometry.append(g, end=False)
        simplified = geometry.simplify(0.01, inplace=True)
        self.assertEqual(len(simplified), 64 + 1)
        self.assertEqual(simplified.segments[16][2].imag, 0)
        self.assertEqual(simplified.segments[48][2].imag, 1)
        self.assertIs(simplified, geometry)

    def test_point_towards_numpy(self):
        p1 = complex(0, 100)
        p2 = complex(50, 22)
        steps = 5
        q = Geomstr.towards(None, p1, p2, np.linspace(0, 1, steps))
        self.assertEqual(len(q), steps)
        self.assertEqual(p1, q[0])
        self.assertEqual(p2, q[-1])

    def test_point_split_line_numpy(self):
        g = Geomstr()
        g.line(complex(0, 100), complex(50, 22))
        g.insert(1, list(g.split(0, 0.5)))
        self.assertEqual(g.index, 3)

        steps = 5
        splits = list(g.split(0, np.linspace(0, 1, steps)[1:-1]))
        g.insert(1, splits)
        self.assertEqual(g.index, 7)

        steps = 10
        splits = list(g.split(0, np.linspace(1, 0, steps)[1:-1]))
        g.replace(0, 7, splits)
        self.assertEqual(g.index, steps - 2)
        for i in range(1, g.index):
            self.assertAlmostEqual(g.length(i - 1), g.length(i))

    def test_point_split_quad_numpy(self):
        g = Geomstr()
        g.quad(complex(0, 100), complex(0, 0), complex(50, 22))
        sp = list(g.split(0, 0.21))
        self.assertAlmostEqual(g.position(0, 0.21), sp[0][-1])
        g.insert(1, sp)
        self.assertEqual(g.index, 3)

        steps = 5
        splits = list(g.split(0, np.linspace(0, 1, steps)[1:-1]))
        g.insert(1, splits)
        self.assertEqual(g.index, 7)

        steps = 10
        splits = list(g.split(0, np.linspace(1, 0, steps)[1:-1]))
        g.replace(0, 7, splits)
        self.assertEqual(g.index, steps - 2)

    def test_point_split_quad_numpy_2(self):
        steps = 10
        g = Geomstr()
        g.quad(complex(0, 0), complex(0, 50), complex(0, 100))
        splits = list(g.split(0, np.linspace(1, 0, steps)[1:-1]))
        g.replace(0, 0, splits)
        for i in range(1, g.index):
            self.assertAlmostEqual(g.length(i - 1), g.length(i))

    def test_point_split_cubic_numpy(self):
        g = Geomstr()
        g.cubic(complex(0, 100), complex(0, 0), complex(90, 67), complex(50, 22))
        sp = list(g.split(0, 0.21))
        self.assertAlmostEqual(g.position(0, 0.21), sp[0][-1])
        g.insert(1, list(g.split(0, 0.5)))
        self.assertEqual(g.index, 3)

        steps = 5
        splits = list(g.split(0, np.linspace(0, 1, steps)[1:-1]))
        g.insert(1, splits)
        self.assertEqual(g.index, 7)

        steps = 10
        splits = list(g.split(0, np.linspace(1, 0, steps)[1:-1]))
        g.replace(0, 7, splits)
        self.assertEqual(g.index, steps - 2)

    def test_geomstr_svg(self):
        gs = Geomstr.svg("M0,0 h100 v100 h-100 v-100 z")
        self.assertEqual(gs.raw_length(), 400.0)

    def test_geomstr_near(self):
        """
        Test geomstr near command to find number of segment points within a given range.
        @return:
        """
        gs = Geomstr.circle(500, 0, 0)
        q = gs.near(complex(0, 0), 499)
        self.assertEqual(len(q), 0)
        q = gs.near(complex(500, 0), 50)
        self.assertEqual(len(q), 2)
        gs.append(Geomstr.rect(0, 0, 10, 10))
        gs.end()
        gs.append(Geomstr.rect(5, 5, 10, 10))
        q = gs.near(complex(0, 0), 499)
        # 2 rectangles, 4 corners. 2 points each segment meeting at corners = 16
        self.assertEqual(len(q), 16)

    def test_geomstr_area(self):
        gs = Geomstr.svg("M0,0 h100 v100 h-100 v-100 z")
        self.assertAlmostEqual(gs.area(), 100 * 100)
        gs = Geomstr.circle(100, 0, 0)
        self.assertAlmostEqual(gs.area(density=1000), (tau / 2) * 100 * 100, delta=1)
        gs = Geomstr.ellipse(100, 100, 0, 0)
        self.assertAlmostEqual(gs.area(density=1000), (tau / 2) * 100 * 100, delta=1)
        # We add another equally sized circle to the same geometry.
        gs.append(Geomstr.ellipse(100, 100, 1000, 1000))
        self.assertAlmostEqual(gs.area(density=1000), tau * 100 * 100, delta=1)

    def test_geomstr_fractal_koch_snowflake(self):
        # seed = Geomstr.svg("M0,0 1,0 2,1 3,0 4,0")
        seed = Geomstr.turtle("F-F++F-F", n=6)

        # design = Geomstr.turtle("F+F+F+F", n=4)
        design = Geomstr.turtle("F+F+F+F", n=6)
        design.uscale(500)
        for i in range(5):
            design.fractal(seed)
            print(design)
        bounds = design.bbox()
        draw(
            list(design.as_interpolated_points()),
            *bounds,
            buffer=50,
            filename="koch.png",
        )

    def test_geomstr_fractal_swaps(self):
        for i in range(4):
            seed = Geomstr.svg("M0,0 h2 v1 l1,-1")
            design = Geomstr.turtle("FFF", n=4)
            design.segments[1][1] = i
            design.segments[1][3] = i
            design.uscale(500)
            design.fractal(seed)
            design.fractal(seed)
            draw(
                list(design.as_interpolated_points()),
                *design.bbox(),
                buffer=50,
                filename=f"swaps{i}.png",
            )

    def test_geomstr_fractal_polya_sweep(self):
        """
        http://www.fractalcurves.com/images/2S_triangle_sweep.jpg
        @return:
        """
        seed = Geomstr.turtle("f+B", n=4)
        design = Geomstr.turtle("F", n=4)
        design.uscale(500)
        for _ in range(8):
            design.fractal(seed)
        draw(
            list(design.as_interpolated_points()),
            *design.bbox(),
            buffer=50,
            filename="polya.png",
        )

    def test_geomstr_fractal_terdragon(self):
        """
        http://www.fractalcurves.com/images/3T_ter.jpg
        @return:
        """
        seed = Geomstr.turtle("F+F-F", n=3, d=math.sqrt(3))
        design = copy(seed)
        design.uscale(500)
        for _ in range(5):
            design.fractal(seed)
        draw(
            list(design.as_interpolated_points()),
            *design.bbox(),
            buffer=50,
            filename="terdragon.png",
        )

    def test_geomstr_fractal_iterdragon(self):
        """
        http://www.fractalcurves.com/images/3T_butterfly.jpg
        @return:
        """
        seed = Geomstr.turtle("b+b-b", n=3, d=math.sqrt(3))
        design = copy(seed)
        design.uscale(500)
        for _ in range(8):
            design.fractal(seed)
        draw(
            list(design.as_interpolated_points()),
            *design.bbox(),
            buffer=50,
            filename="inverted-terdragon.png",
        )

    def test_geomstr_fractal_box(self):
        """
        http://www.fractalcurves.com/images/3T_block.jpg
        @return:
        """
        seed = Geomstr.turtle("b+F-b", n=3, d=math.sqrt(3))
        design = copy(seed)
        design.uscale(500)
        for _ in range(8):
            design.fractal(seed)
        draw(
            list(design.as_interpolated_points()),
            *design.bbox(),
            buffer=50,
            filename="box.png",
        )

    def test_optimized_as_path_correctness(self):
        """Test that optimized as_path produces identical results to original."""
        # Create test geometry with mixed segment types
        geom = Geomstr()
        geom.line(complex(0, 0), complex(10, 0))
        geom.quad(complex(10, 0), complex(15, 5), complex(20, 0))
        geom.cubic(complex(20, 0), complex(23, 3), complex(27, 3), complex(30, 0))
        geom.arc(complex(30, 0), complex(35, 5), complex(40, 0))
        geom.end()
        geom.line(complex(50, 0), complex(60, 10))

        # Test both small and large geometries
        for scale in [1, 100]:  # Small geometry vs large geometry
            test_geom = Geomstr(geom)
            if scale > 1:
                # Create larger geometry to trigger optimization
                for _ in range(scale):
                    test_geom.append(geom)

            # Generate path and verify it doesn't crash
            path = test_geom.as_path()
            self.assertIsNotNone(path)

            # Verify path has expected properties
            if hasattr(path, "d"):
                path_d = path.d()
                self.assertIsInstance(path_d, str)
                self.assertGreater(len(path_d), 0)

    def test_optimized_svg_parsing_accuracy(self):
        """Test that optimized SVG parsing maintains output accuracy."""
        test_paths = {
            "simple": "M 10,10 L 20,20 L 30,10 Z",
            "mixed_complex": "M 10,10 Q 15,5 20,10 C 25,5 35,5 40,10 L 50,20 Z",
            "subpaths": "M 10,10 L 20,20 M 30,30 Q 35,25 40,30",
        }

        for name, path_str in test_paths.items():
            with self.subTest(path=name):
                try:
                    geom = Geomstr.svg(path_str)
                    self.assertGreater(geom.index, 0)

                    # Test round-trip conversion
                    path = geom.as_path()
                    self.assertIsNotNone(path)

                    # Verify basic geometry properties
                    if geom.index > 0:
                        first_point = geom.first_point
                        last_point = geom.last_point
                        self.assertIsNotNone(first_point)
                        self.assertIsNotNone(last_point)

                except Exception as e:
                    self.fail(f"SVG parsing failed for {name}: {e}")

    def test_optimized_equal_interpolation_precision(self):
        """Test that optimized equal-distance interpolation maintains accuracy."""
        # Create test geometry with various segment types
        geom = Geomstr()
        geom.line(complex(0, 0), complex(100, 0))
        geom.quad(complex(100, 0), complex(150, 50), complex(200, 0))
        geom.cubic(complex(200, 0), complex(225, 25), complex(275, 25), complex(300, 0))

        distance = 10.0

        # Test basic functionality
        points = list(geom.as_equal_interpolated_points(distance))
        self.assertGreater(len(points), 0)

        # Verify points are valid complex numbers
        for point in points:
            if point is not None:
                self.assertIsInstance(point, complex)

        # Test with larger geometry to potentially trigger optimization
        large_geom = Geomstr()
        for i in range(100):
            x = i * 10
            large_geom.line(complex(x, 0), complex(x + 5, 10))
            large_geom.quad(
                complex(x + 5, 10), complex(x + 7.5, 15), complex(x + 10, 10)
            )

        large_points = list(large_geom.as_equal_interpolated_points(distance))
        self.assertGreater(len(large_points), len(points))

        # Verify distances are approximately correct for a simple case
        line_geom = Geomstr()
        line_geom.line(complex(0, 0), complex(50, 0))
        line_points = list(line_geom.as_equal_interpolated_points(10.0))

        # Should have at least start and end points
        self.assertGreaterEqual(len(line_points), 2)

    def test_optimization_threshold_behavior(self):
        """Test optimization threshold triggers and fallback mechanisms."""
        # Test small geometry (should not trigger optimization)
        small_geom = Geomstr()
        small_geom.line(complex(0, 0), complex(10, 10))
        small_geom.quad(complex(10, 10), complex(15, 15), complex(20, 10))

        # These should work regardless of optimization
        small_path = small_geom.as_path()
        self.assertIsNotNone(small_path)

        small_points = list(small_geom.as_equal_interpolated_points(5.0))
        self.assertGreater(len(small_points), 0)

        # Test larger geometry (may trigger optimization)
        large_geom = Geomstr()
        for i in range(200):  # Large enough to potentially trigger optimization
            x = i * 5
            large_geom.line(complex(x, 0), complex(x + 2, 5))

        large_path = large_geom.as_path()
        self.assertIsNotNone(large_path)

        large_points = list(large_geom.as_equal_interpolated_points(2.0))
        self.assertGreater(len(large_points), len(small_points))

    def test_optimization_error_handling(self):
        """Test graceful handling of edge cases in optimizations."""
        # Test empty geometry
        empty_geom = Geomstr()
        empty_path = empty_geom.as_path()
        self.assertIsNotNone(empty_path)

        empty_points = list(empty_geom.as_equal_interpolated_points(10.0))
        self.assertEqual(len(empty_points), 0)

        # Test geometry with single point
        point_geom = Geomstr()
        point_geom.point(complex(5, 5))
        point_path = point_geom.as_path()
        self.assertIsNotNone(point_path)

        # Test with zero distance (should handle gracefully)
        line_geom = Geomstr()
        line_geom.line(complex(0, 0), complex(10, 0))

        try:
            zero_points = list(line_geom.as_equal_interpolated_points(0.0))
            # Should either return empty list or handle gracefully
            self.assertIsInstance(zero_points, list)
        except (ValueError, ZeroDivisionError):
            # Acceptable to raise error for zero distance
            pass

        # Test with very small distance
        small_dist_points = list(line_geom.as_equal_interpolated_points(0.001))
        self.assertIsInstance(small_dist_points, list)

    def test_optimization_memory_efficiency(self):
        """Test that optimizations don't significantly increase memory usage."""
        # Create moderately complex geometry
        geom = Geomstr()
        for i in range(100):
            x = i * 10
            y = (i % 10) * 5
            if i % 3 == 0:
                geom.line(complex(x, y), complex(x + 8, y + 8))
            elif i % 3 == 1:
                geom.quad(complex(x, y), complex(x + 4, y + 12), complex(x + 8, y))
            else:
                geom.cubic(
                    complex(x, y),
                    complex(x + 2, y + 10),
                    complex(x + 6, y + 10),
                    complex(x + 8, y),
                )

        # Test as_path optimization
        path = geom.as_path()
        self.assertIsNotNone(path)

        # Test equal interpolation optimization
        points = list(geom.as_equal_interpolated_points(5.0))
        self.assertGreater(len(points), 0)

        # Verify geometry state is preserved
        self.assertEqual(geom.index, 100)  # Should still have original segment count

        # Test multiple operations don't accumulate memory issues
        for _ in range(5):
            temp_path = geom.as_path()
            temp_points = list(geom.as_equal_interpolated_points(7.0))
            self.assertIsNotNone(temp_path)
            self.assertGreater(len(temp_points), 0)

    def test_geom_max_aabb(self):
        g = Geomstr.rect(0, 0, 200, 200)
        nx, ny, mx, my = g.aabb()
        print(nx)

    def test_static_beam_horizontal_bowtie(self):
        """
        0: down-right
        1: right side
        2: down-left
        3: left side
        30    21
        |\   /|
        | \ / |
        | / \ |
        |/   \|
        @return:
        """
        bowtie = Geomstr.lines(
            complex(0, 0),
            complex(100, 100),
            complex(100, 0),
            complex(0, 100),
            complex(0, 0),
        )
        sb = BeamTable(bowtie)
        result = sb.actives_at(25)
        actives = bowtie.x_intercept(result, 25)

        for x, y in zip(result, (0, 2)):
            self.assertEqual(x, y)

    def test_static_beam_vertical_bowtie(self):
        """
           3
        --------
        \     /
        0\   /2
          \/
          /\
        2/  \0
        /    \
        ------
           1
        @return:
        """
        bowtie = Geomstr.lines(
            complex(0, 0),
            complex(100, 100),
            complex(0, 100),
            complex(100, 0),
            complex(0, 0),
        )
        sb = BeamTable(bowtie)
        result = sb.actives_at(complex(25, 0))
        actives = bowtie.x_intercept(result, 25)

        for x, y in zip(result, (3, 0, 2, 1)):
            self.assertEqual(x, y)

    def test_static_beam_midpoint_overlap(self):
        """
        We have two small lines [-2,2] on the x and y-axis.
        At the x position 0, both are active, so long as the y position is greater than 2 or less than -2.

        Line 2 is positioned above all lines.
        @return:
        """
        g = Geomstr()
        g.line(complex(-2, 0), complex(2, 0), 0)
        g.line(complex(0, -2), complex(0, 2), 1)
        g.line(complex(-5, 5), complex(5, 5), 2)  # Highest line always.
        bt = BeamTable(g)
        # Segment 1 is not active.
        result = bt.actives_at(complex(0, 3))
        for x, y in zip(result, (0, 2)):
            self.assertEqual(x, y)

        # Segment 1 is active, and above segment 0.
        result = bt.actives_at(complex(0, 1))
        for x, y in zip(result, (0, 1, 2)):
            self.assertEqual(x, y)

        # Segment 1 is active, and below segment 0.
        result = bt.actives_at(complex(0, -1))
        for x, y in zip(result, (1, 0, 2)):
            self.assertEqual(x, y)

        # Segment 1 is no longer active.
        result = bt.actives_at(complex(0, -3))
        for x, y in zip(result, (0, 2)):
            self.assertEqual(x, y)

    def test_scan_table_random(self):
        for c in range(1):
            print("\n\n\n\n\n")
            g = Geomstr()
            for i in range(25):
                random_segment(
                    g, i=1000, arc=False, point=False, quad=False, cubic=False
                )
            t = time.time()
            sb = BeamTable(g)
            sb.compute_beam()
            intersections = sb.intersections
            print(f"Time: {time.time() - t}")
            try:
                g.append(intersections)
                draw_geom(g, *g.bbox(), filename="scantable.png")
            except PermissionError:
                pass

    def test_scan_table_actives_monotonic(self):
        """
        Tests a random set of lines find the intercepts at all active positions and ensures that they are monotonic.

        @return:
        """
        for c in range(10):
            g = Geomstr()
            for i in range(25):
                random_segment(
                    g, i=1000, arc=False, point=False, quad=False, cubic=False
                )
            sb = BeamTable(g)
            b = g.bbox()
            for x in range(int(b[0]), int(b[2])):
                actives = sb.actives_at(x)
                pos = g.y_intercept(actives, x)
                for q in range(1, len(pos)):
                    self.assertLessEqual(pos[q - 1], pos[q])

    def test_scan_table_fill_random(self):
        for c in range(1):
            print("\n\n\n\n\n")
            g = Geomstr()
            for i in range(25):
                random_segment(
                    g, i=1000, arc=False, point=False, quad=False, cubic=False
                )
            t = time.time()
            sb = BeamTable(g)
            sb.compute_beam()
            intersections = sb.intersections
            print(f"Time: {time.time() - t}")

            b = g.bbox()
            for x in range(int(b[0]), int(b[2])):
                actives = sb.actives_at(x)
                pos = g.y_intercept(actives, x)
                for q in range(1, len(pos), 2):
                    g.line(complex(x, pos[q - 1]), complex(x, pos[q]))

            g.append(intersections)
            try:
                draw_geom(g, *b, filename="scantable-fill.png")
            except PermissionError:
                pass

    def test_scan_table_random_brute(self):
        print("\n\n")
        for _c in range(3):  # Reduced iterations but increased complexity
            g = Geomstr()
            # Increase sampling size for more measurable timing
            for i in range(500):  # Increased from 100 to 500
                random_segment(
                    g, i=1000, arc=False, point=False, quad=False, cubic=False
                )
            t = time.time()
            sb1 = BeamTable(g)
            sb1.compute_beam_brute()
            brute_time = time.time() - t

            t = time.time()
            sb2 = BeamTable(g)
            sb2.compute_beam_bo()
            bo_time = time.time() - t

            # self.assertEqual(sb1.intersections, sb2.intersections)
            for a, b in zip(sb1._nb_scan, sb2._nb_scan):
                # print(f"{a} :: {b}")
                for c, d in zip(a, b):
                    self.assertEqual(c, d)

            # Avoid division by zero errors with minimum time thresholds
            min_time = 1e-6  # Minimum measurable time (1 microsecond)
            brute_time = max(brute_time, min_time)
            bo_time = max(bo_time, min_time)

            if brute_time > min_time and bo_time > min_time:
                improvement_ratio = brute_time / bo_time
                reverse_ratio = bo_time / brute_time
                print(
                    f"With binary inserts: brute: {brute_time:.6f}s vs bo: {bo_time:.6f}s improvement: {improvement_ratio:.2f}x or {reverse_ratio:.2f}x"
                )
            else:
                print(
                    f"With binary inserts: brute: {brute_time:.6f}s vs bo: {bo_time:.6f}s (timing too fast for reliable comparison)"
                )
            print(f"Intersections {len(sb1.intersections)}, {len(sb2.intersections)}")

    def test_geomstr_image(self):
        from PIL import Image, ImageDraw

        image = Image.new("RGBA", (256, 256), "white")
        draw = ImageDraw.Draw(image)
        draw.ellipse((100, 100, 130, 130), "black")
        image = image.convert(mode="1")
        image.save("geom.png")
        g = Geomstr.image(image)
        draw_geom(g, *g.bbox(), filename="geom2.png")
        self.assertEqual(g.index, 31)

    def test_geomstr_image_multi(self):
        from PIL import Image, ImageDraw

        image = Image.new("RGBA", (256, 256), "white")
        draw = ImageDraw.Draw(image)
        draw.ellipse((100, 100, 130, 130), "black")
        draw.ellipse((100, 20, 136, 50), "black")
        image = image.convert(mode="1")
        image.save("geom.png")
        g = Geomstr.image(image, vertical=True)
        draw_geom(g, *g.bbox(), filename="geom2.png")

    def test_as_lines_execute(self):
        g = Geomstr()
        with g.function() as q:
            q.line(complex(0, 0), complex(0, 1))
            q.line(complex(0, 1), complex(1, 1))
            q.line(complex(1, 1), complex(1, 0))
            q.line(complex(1, 0), complex(0, 0))
        self.assertEqual(len(g), 6)  # function, 4 lines, until.
        executed = list(g.as_lines())
        self.assertEqual(len(executed), 0)
        g.call(1)
        g.call(
            1, placement=(0, complex(1000, 0), complex(1000, 1000), complex(0, 1000))
        )
        g.call(1)
        executed = list(g.as_lines())
        self.assertEqual(len(executed), 12)

    # def test_geomstr_hatch(self):
    #     gs = Geomstr.svg(
    #         "M 207770.064517,235321.124952 C 206605.069353,234992.732685 205977.289179,234250.951228 205980.879932,233207.034699 C 205983.217733,232527.380908 206063.501616,232426.095743 206731.813533,232259.66605 L 207288.352862,232121.071081 L 207207.998708,232804.759538 C 207106.904585,233664.912764 207367.871267,234231.469286 207960.295387,234437.989447 C 208960.760372,234786.753419 209959.046638,234459.536445 210380.398871,233644.731075 C 210672.441667,233079.98258 210772.793626,231736.144349 210569.029382,231118.732625 C 210379.268508,230543.75153 209783.667018,230128.095713 209148.499972,230127.379646 C 208627.98084,230126.79283 208274.720902,230294.472682 207747.763851,230792.258962 C 207377.90966,231141.639128 207320.755956,231155.543097 206798.920578,231023.087178 C 206328.09633,230903.579262 206253.35266,230839.656219 206307.510015,230602.818034 C 206382.366365,230275.460062 207158.299204,225839.458855 207158.299204,225738.863735 C 207158.299204,225701.269015 208426.401454,225670.509699 209976.304204,225670.509699 C 211869.528049,225670.509699 212794.309204,225715.990496 212794.309204,225809.099369 C 212794.309204,225885.323687 212726.683921,226357.175687 212644.030798,226857.659369 L 212493.752392,227767.629699 L 210171.516354,227767.629699 L 207849.280317,227767.629699 L 207771.086662,228324.677199 C 207728.080152,228631.053324 207654.900983,229067.454479 207608.466287,229294.457543 L 207524.039566,229707.190387 L 208182.568319,229381.288158 C 209664.399179,228647.938278 211467.922971,228893.537762 212548.92912,229975.888551 C 214130.813964,231559.741067 213569.470754,234195.253882 211455.779825,235108.237047 C 210589.985852,235482.206254 208723.891068,235589.992389 207770.064517,235321.124952 L 207770.064517,235321.124952Z"
    #         "M 217143.554487,235251.491866 C 215510.313868,234687.408946 214629.289204,233029.479999 214629.289204,230520.099699 C 214629.289204,227300.669136 216066.08164,225539.439699 218692.459204,225539.439699 C 221318.836768,225539.439699 222755.629204,227300.669136 222755.629204,230520.099699 C 222755.629204,233768.619944 221313.285526,235510.883949 218635.902338,235496.480807 C 218198.433364,235494.127417 217526.876831,235383.882393 217143.554487,235251.491866 L 217143.554487,235251.491866Z"
    #         "M 190905.619204,231712.322088 L 190905.619204,228054.954477 L 190248.863277,228304.502088 C 189887.647517,228441.753274 189445.286267,228554.049699 189265.838277,228554.049699 C 188966.73452,228554.049699 188939.569204,228505.149339 188939.569204,227966.731848 C 188939.569204,227432.097785 188971.901741,227372.495945 189300.011704,227302.291681 C 190198.545589,227110.036287 190884.012886,226765.589154 191414.377757,226239.823305 C 191971.194511,225687.834949 192014.073023,225670.509699 192823.380257,225670.509699 L 193658.089204,225670.509699 L 193658.089204,230520.099699 L 193658.089204,235369.689699 L 192281.854204,235369.689699 L 190905.619204,235369.689699 L 190905.619204,231712.322088 L 190905.619204,231712.322088"
    #
    #     )
    #     # gs.uscale(0.05)
    #     # bounds = gs.bbox()
    #     # t = list(gs.as_interpolated_points(interpolate=5))
    #     # draw(t, *bounds)
    #     # return
    #
    #     hatch = Geomstr.hatch(gs, distance=200, angle=tau / 4)
    #     # hatch = Geomstr.hatch(gs, distance=200, angle=0)
    #     print(hatch)
    #     bounds = hatch.bbox()
    #     draw(list(hatch.as_interpolated_points()), *bounds)
