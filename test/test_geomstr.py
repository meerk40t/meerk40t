import math
import random
import time
import unittest
from copy import copy
from math import tau

import numpy as np

from meerk40t.fill.fills import scanline_fill
from meerk40t.svgelements import Arc, CubicBezier, Line, Matrix, QuadraticBezier
from meerk40t.tools.geomstr import (
    TYPE_LINE,
    Clip,
    Geomstr,
    MergeGraph,
    Pattern,
    Polygon,
    Scanbeam,
)


def draw(segments, min_x, min_y, max_x, max_y, filename="test.png"):
    from PIL import Image, ImageDraw

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
        self.assertNotEqual(path, p)
        #
        # print(path.segments)
        # print("Original segments...")
        # print(p.travel_distance())
        # p.two_opt_distance()
        # print(p.travel_distance())
        # print(p.segments)
        # draw(p.segments, w, h)

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

    def test_geomstr_cubic_length(self):
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

    def test_geomstr_2opt(self):
        path = Geomstr()
        path.line(complex(0, 0), complex(50, 0))
        path.line(complex(50, 50), complex(50, 0))
        self.assertEqual(path.raw_length(), 100)
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
        from meerk40t.fill.patternfill import set_diamond1

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
        from meerk40t.fill.patternfill import set_diamond1

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
        from meerk40t.fill.patternfill import set_diamond1

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
                f"geomstr points in poly took {t2} seconds. Raytraced-numpy took {t1}. Speed-up {t1/t2}x"
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
            assert (bool(p1), bool(p2))
        try:
            print(
                f"geomstr points in poly took {t2} seconds. Simple Scanline {t1}. Speed-up {t1 / t2}x"
            )
        except ZeroDivisionError:
            pass

    def test_point_in_polygon(self):
        from meerk40t.fill.patternfill import set_diamond1

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
                f"is_point_inside takes {t2} numpy version takes {t1} speedup {t2/t1}x"
            )
        except ZeroDivisionError:
            print(f"{t2} vs {t1}")

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

    #
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
