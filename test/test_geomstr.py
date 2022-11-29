import random
import unittest

from meerk40t.tools.geomstr import Geomstr, Scanbeam


class TestGeomstr(unittest.TestCase):
    """These tests ensure the basic functions of the Geomstr elements."""

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
        self.assertTrue(len(results), 1)
        self.assertEqual(results[0], (50, 50, 0, 0))

    def test_geomstr_polycut(self):
        subject = Geomstr()
        # subject.line(complex(0, 25), complex(100, 25))
        # clip = Geomstr()
        # clip.line(complex(10, 10), complex(40, 10))
        # clip.line(complex(40, 10), complex(40, 40))
        # clip.line(complex(40, 40), complex(10, 40))
        # clip.line(complex(10, 40), complex(10, 10))
        # clip.close()
        # result = subject.subtract(clip)
        # results = list(result.as_segments())
        # self.assertTrue(len(results), 1)
        # self.assertEqual(results[0], ("line", (10, 25), (40, 25)))
