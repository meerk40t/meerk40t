import random
import time
import unittest

from meerk40t.tools.geomstr import Geomstr, Scanbeam, TYPE_LINE, Pattern, Clip, Polygon

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
        for x, y in zip(
            geomstr.bbox(), (-9500.0, 500.00000000000057, -500.0, 9500.0)
        ):
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
            self.assertEqual(c.point(t), path.position(0, t))

    def test_geomstr_quad_point(self):
        for i in range(1000):
            start = complex(random.random() * 100, random.random() * 100)
            control = complex(random.random() * 100, random.random() * 100)
            end = complex(random.random() * 100, random.random() * 100)
            c = QuadraticBezier(start, control, end)

            path = Geomstr()
            path.quad(start, control, end)

            t = random.random()
            self.assertEqual(c.point(t), path.position(0, t))

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
            self.assertEqual(c.point(t), path.position(0, t))

    def test_geomstr_cubic_length(self):
        difference = 0
        t0 = 0
        t1 = 0
        for i in range(50):
            start = complex(random.random() * 100, random.random() * 100)
            c1 = complex(random.random() * 100, random.random() * 100)
            c2 = complex(random.random() * 100, random.random() * 100)
            end = complex(random.random() * 100, random.random() * 100)
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
        print(f"geomstr cubic length time {t0}. svgelements cubic length time {t1}. total difference {difference}")

    def test_geomstr_line_bounds(self):
        for i in range(1000):
            start = complex(random.random() * 100, random.random() * 100)
            end = complex(random.random() * 100, random.random() * 100)
            c = Line(start, end)

            path = Geomstr()
            path.line(start, end)

            self.assertEqual(c.bbox(), path.bbox(0))

    def test_geomstr_quad_bounds(self):
        for i in range(1000):
            start = complex(random.random() * 100, random.random() * 100)
            control = complex(random.random() * 100, random.random() * 100)
            end = complex(random.random() * 100, random.random() * 100)
            c = QuadraticBezier(start, control, end)

            path = Geomstr()
            path.quad(start, control, end)

            self.assertEqual(c.bbox(), path.bbox(0))

    def test_geomstr_cubic_bounds(self):
        for i in range(1000):
            start = complex(random.random() * 100, random.random() * 100)
            c1 = complex(random.random() * 100, random.random() * 100)
            c2 = complex(random.random() * 100, random.random() * 100)
            end = complex(random.random() * 100, random.random() * 100)
            c = CubicBezier(start, c1, c2, end)

            path = Geomstr()
            path.cubic(start, c1, c2, end)

            self.assertEqual(c.bbox(), path.bbox(0))

    def test_geomstr_point_functions(self):
        from math import sqrt,  radians
        p = Geomstr()
        p.point(complex(4,4))
        q = p.towards(0, complex(6,6), 0.5)
        self.assertEqual(q, complex(5,5))

        m = p.distance(0, complex(6,6))
        self.assertEqual(m, 2 * sqrt(2))
        m = p.distance(0, complex(4, 0))
        self.assertEqual(m, 4)
        a45 = radians(45)
        a90 = radians(90)
        a180 = radians(180)

        p.point(complex(0,0))
        a = p.angle(1, complex(3, 3))
        self.assertEqual(a, a45)
        a = p.angle(1, complex(0, 3))
        self.assertEqual(a, a90)
        a = p.angle(1, complex(-3, 0))
        self.assertEqual(a, a180)

        q = p.polar(1, a45, 10)
        self.assertAlmostEqual(q, complex(sqrt(2)/2 * 10, sqrt(2)/2 * 10))

        r = p.reflected(1, complex(10,10))
        self.assertEqual(r, complex(20, 20))

    def test_geomstr_point_towards_static(self):
        p = complex(4, 4)
        q = Geomstr.towards(None, p, complex(6, 6), 0.5)
        self.assertEqual(q, complex(5, 5))

    def test_geomstr_point_distance_static(self):
        from math import sqrt
        p = complex(4, 4)
        m = Geomstr.distance(None, p, complex(6,6))
        self.assertEqual(m, 2 * sqrt(2))
        m = Geomstr.distance(None, p, complex(4,0))
        self.assertEqual(m, 4)

    def test_geomstr_point_angle_static(self):
        from math import radians
        p = complex(0,0)
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
        self.assertAlmostEqual(q, complex(sqrt(2)/2 * 10, sqrt(2)/2 * 10))

    def test_geomstr_point_reflected_static(self):
        p = complex(0)
        r = Geomstr.reflected(None, p, complex(10,10))
        self.assertEqual(r, complex(20,20))

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
        path.polyline([complex(0,0), complex(100,0), complex(50,50), complex(100,100), complex(0,100), complex(0,0)])
        pts = list(path.convex_hull(range(5)))
        self.assertNotIn(complex(50,50), pts)
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

    def test_geomstr_intersections(self):
        subject = Geomstr()
        subject.line(complex(0, 0), complex(100, 100))
        clip = Geomstr()
        clip.line(complex(100, 0), complex(0, 100))
        results = subject.find_intersections(clip)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], (50, 50, 0, 0, 0))

    def test_geomstr_intersect_segments(self):
        path = Geomstr()
        for i in range(50):
            t = random.randint(0, 5)
            if t == 0:
                start = complex(random.random() * 100, random.random() * 100)
                path.point(start)
            if t == 1:
                start = complex(random.random() * 100, random.random() * 100)
                end = complex(random.random() * 100, random.random() * 100)
                path.line(start, end)
            if t == 2:
                start = complex(random.random() * 100, random.random() * 100)
                control = complex(random.random() * 100, random.random() * 100)
                end = complex(random.random() * 100, random.random() * 100)
                path.quad(start, control, end)
            if t == 3:
                start = complex(random.random() * 100, random.random() * 100)
                c1 = complex(random.random() * 100, random.random() * 100)
                c2 = complex(random.random() * 100, random.random() * 100)
                end = complex(random.random() * 100, random.random() * 100)
                path.cubic(start, c1, c2, end)
            if t == 4:
                start = complex(random.random() * 100, random.random() * 100)
                control = complex(random.random() * 100, random.random() * 100)
                end = complex(random.random() * 100, random.random() * 100)
                path.arc(start, control, end)

        for j in range(path.index):
            for k in range(path.index):
                q = f"{path.segment_type(j)} x {path.segment_type(k)}: {list(path.intersections(j, k))}"
                # print(q)

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

    def test_pattern_generation(self):
        from meerk40t.fill.patternfill import set_diamond1

        f = set_diamond1
        p = Pattern()
        p.create_from_pattern(f)
        for s in p.generate(0, 0, 1, 1):
            array = np.array(
                [
                    [0.0 + 0.5j, 0.0 + 0.0j, 41.0 + 0.0j, 0.0 + 0.0j, 0.5 + 0.0j],
                    [0.5 + 0.0j, 0.0 + 0.0j, 41.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.5j],
                    [1.0 + 0.5j, 0.0 + 0.0j, 41.0 + 0.0j, 0.0 + 0.0j, 0.5 + 1.0j],
                    [0.5 + 1.0j, 0.0 + 0.0j, 41.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.5j],
                ]
            )
            array2 = s.segments[:s.index]
            self.assertTrue((array == array2).all())

    def test_pattern_generation_counts(self):
        from meerk40t.fill.patternfill import set_diamond1

        f = set_diamond1
        p = Pattern()
        p.create_from_pattern(f)

        three_x_three_grid = list(p.generate(0, 0, 4, 4))
        self.assertEqual(len(three_x_three_grid), 16)
        p.set_cell_padding(0.5, 0.5)
        three_x_three_grid = list(p.generate(0, 0, 4, 4))
        # 1 0.5 1 0.5 1 = 4, so 4x4 with 0.5 padding fits 3x3
        self.assertEqual(len(three_x_three_grid), 9)
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
        poly = Polygon(0+2j, 4+0j, 4+4j, 0+2j)
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
            pts = np.asarray(pts, dtype='float32')
            polygon = np.asarray(polygon, dtype='float32')
            contour2 = np.vstack((polygon[1:], polygon[:1]))
            test_diff = contour2 - polygon
            mask1 = (pts[:, None] == polygon).all(-1).any(-1)
            m1 = (polygon[:, 1] > pts[:, None, 1]) != (contour2[:, 1] > pts[:, None, 1])
            slope = ((pts[:, None, 0] - polygon[:, 0]) * test_diff[:, 1]) - (
                        test_diff[:, 0] * (pts[:, None, 1] - polygon[:, 1]))
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
        polygon = [[np.sin(x) + 0.5, np.cos(x) + 0.5] for x in np.linspace(0, 2 * np.pi, lenpoly)]
        polygon = np.array(polygon, dtype='float32')

        points = np.random.uniform(-1.5, 1.5, size=(N, 2)).astype('float32')
        t = time.time()
        mask = points_in_polygon(polygon, points)
        t1 = time.time() - t

        # Convert to correct format.
        points = points[:,0] + points[:,1] * 1j
        pg = polygon[:,0] + polygon[:,1] * 1j
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
        print(f"geomstr points in poly took {t2} seconds. Raytraced-numpy took {t1}. Speed-up {t1/t2}x")

    def test_point_in_polygon(self):
        from meerk40t.fill.patternfill import set_diamond1
        t1 = 0
        t2 = 0
        f = set_diamond1
        p = Pattern()
        p.create_from_pattern(f)

        yy = []
        for i in range(100):
            yy.append(complex(random.random() * 5, random.random()*5))
        yy.append(yy[0])
        poly = Polygon(*yy)  # 0,10 20,0 20,20.1 0,10
        poly.geomstr.uscale(5)
        m = Scanbeam(poly.geomstr)

        pts = []
        for i in range(2000):
            pts.append(complex(random.random() * 25, random.random()*25))

        t = time.time()
        r = m.points_in_polygon(pts)
        t1 += time.time() - t

        t = time.time()
        rr = [int(m.is_point_inside(j.real, j.imag)) for j in pts]
        t2 += time.time() - t

        for i, j in enumerate(pts):
            self.assertEqual(rr[i], r[i])
        print(f"is_point_inside takes {t2} numpy version takes {t1} speedup {t2/t1}x")

    def test_point_towards_numpy(self):
        p1 = complex(0, 100)
        p2 = complex(50, 22)
        steps = 5
        q = Geomstr.towards(None, p1, p2, np.linspace(0,1,steps))
        self.assertEqual(len(q), steps)
        self.assertEqual(p1, q[0])
        self.assertEqual(p2, q[-1])