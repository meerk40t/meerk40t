import random
import unittest

from meerk40t.tools.geomstr import Geomstr, Scanbeam, TYPE_LINE

import unittest
from copy import copy
from math import tau

import numpy as np

from meerk40t.fill.fills import scanline_fill
from meerk40t.svgelements import Matrix, CubicBezier, Line, QuadraticBezier, Arc


def draw(segments, w, h, filename="test.png"):
    from PIL import Image, ImageDraw

    im = Image.new("RGBA", (w, h), "white")
    draw = ImageDraw.Draw(im)
    for segment in segments:
        f = segment[0]
        t = segment[-1]
        draw.line(((f.real, f.imag), (t.real, t.imag)), fill="black")
    im.save(filename)


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
        self.assertTrue(np.all(numpath.segments == numpath2.segments))
        numpath.translate(3, 3)
        self.assertFalse(np.all(numpath.segments == numpath2.segments))
        numpath.translate(-3, -3)
        self.assertTrue(np.all(numpath.segments == numpath2.segments))

    def test_geomstr_bbox(self):
        w = 10000
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
        self.assertEqual(numpath.bbox(), (500.0, 500.0, 9500.0, 9500.0))
        numpath.rotate(tau * 0.25)
        for x, y in zip(numpath.bbox(), (-9500.0, 500.00000000000057, -500.0, 9500.0)):
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

    def test_geomstr_close(self):
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
            for seg in subpath.segments:
                self.assertEqual(seg[2].real, TYPE_LINE)
        self.assertEqual(len(subpaths[0]), 4)
        self.assertEqual(len(subpaths[1]), 4)

    def test_geomstr_scanline(self):
        w = 10000
        h = 10000
        paths = (
            (
                (w * 0.05, h * 0.05),
                (w * 0.95, h * 0.05),
                (w * 0.95, h * 0.95),
                (w * 0.05, h * 0.95),
                (w * 0.05, h * 0.05),
            ),
            (
                (w * 0.25, h * 0.25),
                (w * 0.75, h * 0.25),
                (w * 0.75, h * 0.75),
                (w * 0.25, h * 0.75),
                (w * 0.25, h * 0.25),
            ),
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
        self.assertNotEqual(path, p)
        #
        # print(path.segments)
        # print("Original segments...")
        # print(p.travel_distance())
        # p.two_opt_distance()
        # print(p.travel_distance())
        # print(p.segments)
        # draw(p.segments, w, h)

    def test_geomstr_arc_center(self):
        for i in range(1000):
            start = complex(random.random() * 100, random.random() * 100)
            control = complex(random.random() * 100, random.random() * 100)
            end = complex(random.random() * 100, random.random() * 100)
            c = Arc(start=start, control=control, end=end)

            path = Geomstr()
            path.arc(start, control, end)

            self.assertAlmostEqual(complex(c.center), path.arc_center(0))

    def test_geomstr_arc_radius(self):
        for i in range(1000):
            start = complex(random.random() * 100, random.random() * 100)
            control = complex(random.random() * 100, random.random() * 100)
            end = complex(random.random() * 100, random.random() * 100)
            c = Arc(start=start, control=control, end=end)

            path = Geomstr()
            path.arc(start, control, end)

            self.assertAlmostEqual(c.rx, path.arc_radius(0))
            self.assertAlmostEqual(c.ry, path.arc_radius(0))


    def test_geomstr_line_point(self):
        for i in range(1000):
            start = complex(random.random() * 100, random.random() * 100)
            end = complex(random.random() * 100, random.random() * 100)
            c = Line(start, end)

            path = Geomstr()
            path.line(start, end)
            t = random.random()
            self.assertEqual(c.point(t), path.segment_point(0, t))

    def test_geomstr_quad_point(self):
        for i in range(1000):
            start = complex(random.random() * 100, random.random() * 100)
            control = complex(random.random() * 100, random.random() * 100)
            end = complex(random.random() * 100, random.random() * 100)
            c = QuadraticBezier(start, control, end)

            path = Geomstr()
            path.quad(start, control, end)

            t = random.random()
            self.assertEqual(c.point(t), path.segment_point(0, t))

    def test_geomstr_cubic_point(self):
        for i in range(1000):
            start = complex(random.random() * 100, random.random() * 100)
            c1 = complex(random.random() * 100, random.random() * 100)
            c2 = complex(random.random() * 100, random.random() * 100)
            end = complex(random.random() * 100, random.random() * 100)
            c = CubicBezier(start, c1, c2, end)

            path = Geomstr()
            path.cubic(start, c1, c2, end)

            t = random.random()
            self.assertEqual(c.point(t), path.segment_point(0, t))

    def test_geomstr_line_bounds(self):
        for i in range(1000):
            start = complex(random.random() * 100, random.random() * 100)
            end = complex(random.random() * 100, random.random() * 100)
            c = Line(start, end)

            path = Geomstr()
            path.line(start, end)

            self.assertEqual(c.bbox(), path.segment_bbox(0))

    def test_geomstr_quad_bounds(self):
        for i in range(1000):
            start = complex(random.random() * 100, random.random() * 100)
            control = complex(random.random() * 100, random.random() * 100)
            end = complex(random.random() * 100, random.random() * 100)
            c = QuadraticBezier(start, control, end)

            path = Geomstr()
            path.quad(start, control, end)

            self.assertEqual(c.bbox(), path.segment_bbox(0))

    def test_geomstr_cubic_bounds(self):
        for i in range(1000):
            start = complex(random.random() * 100, random.random() * 100)
            c1 = complex(random.random() * 100, random.random() * 100)
            c2 = complex(random.random() * 100, random.random() * 100)
            end = complex(random.random() * 100, random.random() * 100)
            c = CubicBezier(start, c1, c2, end)

            path = Geomstr()
            path.cubic(start, c1, c2, end)

            self.assertEqual(c.bbox(), path.segment_bbox(0))

    def test_geomstr_point_towards_static(self):
        p = complex(4, 4)
        q = Geomstr.towards(p, complex(6, 6), 0.5)
        self.assertEqual(q, complex(5, 5))

    def test_geomstr_point_distance_static(self):
        from math import sqrt
        p = complex(4, 4)
        m = Geomstr.distance(p, complex(6,6))
        self.assertEqual(m, 2 * sqrt(2))
        m = Geomstr.distance(p, complex(4,0))
        self.assertEqual(m, 4)

    def test_geomstr_point_angle_static(self):
        from math import radians
        p = complex(0,0)
        a = Geomstr.angle(p, complex(3, 3))
        a45 = radians(45)
        self.assertEqual(a, a45)
        a = Geomstr.angle(p, complex(0, 3))
        a90 = radians(90)
        self.assertEqual(a, a90)
        a = Geomstr.angle(p, complex(-3, 0))
        a180 = radians(180)
        self.assertEqual(a, a180)

    def test_geomstr_point_polar_static(self):
        from math import radians, sqrt
        p = complex(0)
        a = radians(45)
        q = Geomstr.polar(p, a, 10)
        self.assertAlmostEqual(q, complex(sqrt(2)/2 * 10, sqrt(2)/2 * 10))

    def test_geomstr_point_reflected_static(self):
        p = complex(0)
        r = Geomstr.reflected(p, complex(10,10))
        self.assertEqual(r, complex(20,20))

    def test_geomstr(self):
        path = Geomstr()
        path.line(complex(0, 0), complex(50, 0))
        self.assertEqual(len(path), 1)
        self.assertEqual(path.length(), 50)
        self.assertEqual(path.bbox(), (0, 0, 50, 0))
        path.line(complex(50, 0), complex(50, 50))
        self.assertEqual(path.length(), 100)

    def test_geomstr_2opt(self):
        path = Geomstr()
        path.line(complex(0, 0), complex(50, 0))
        path.line(complex(50, 50), complex(50, 0))
        self.assertEqual(path.length(), 100)
        self.assertEqual(path.travel_distance(), 50)
        path.two_opt_distance()
        self.assertEqual(path.travel_distance(), 0)

    def test_geomstr_scanbeam_build(self):
        """
        Build the scanbeam. In a correct scanbeam we should be able to iterate
        through the scanbeam adding or removing each segment without issue.

        No remove segment ~x should occur before the append segment x value.
        :return:
        """
        path = Geomstr()
        for i in range(5000):
            path.line(
                complex(random.randint(0, 50), random.randint(0, 50)),
                complex(random.randint(0, 50), random.randint(0, 50)),
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

    def test_geomstr_intersections(self):
        subject = Geomstr()
        subject.line(complex(0, 0), complex(100, 100))
        clip = Geomstr()
        clip.line(complex(100, 0), complex(0, 100))
        results = subject.find_intersections(clip)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], (50, 50, 0, 0, 0))

    def test_geomstr_merge(self):
        subject = Geomstr()
        subject.line(complex(0, 20), complex(100, 100))
        subject.line(complex(20, 0), complex(100, 100))
        clip = Geomstr()
        clip.line(complex(100, 0), complex(0, 100))
        results = subject.merge(clip)
        print(results.segments)

    def test_geomstr_merge_capacity_count(self):
        for j in range(25):
            clip = Geomstr()
            for i in range(50):
                clip.line(
                    complex(random.randint(0, 50), random.randint(0, 50)),
                    complex(random.randint(0, 50), random.randint(0, 50)),
                )
            subject = Geomstr()
            for i in range(50):
                subject.line(
                    complex(random.randint(0, 50), random.randint(0, 50)),
                    complex(random.randint(0, 50), random.randint(0, 50)),
                )
            results = subject.merge(clip)
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
        results = subject.merge(clip)
        print(results)

