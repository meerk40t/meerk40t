import unittest
from math import tau

from meerk40t.core.units import Angle


class TestElementAngle(unittest.TestCase):
    """These tests ensure the basic functions of the Angle element."""

    def test_angle_init(self):
        self.assertEqual(Angle.from_degrees(90).turns, 0.25)
        self.assertEqual(Angle.from_degrees(180).turns, 0.50)
        self.assertEqual(Angle.from_degrees(360).turns, 1.0)
        self.assertEqual(Angle.from_degrees(720).turns, 2.0)
        self.assertEqual(Angle.from_radians(tau).turns, 1.0)
        self.assertEqual(Angle.from_radians(tau / 50.0).turns, 1.0 / 50.0)
        self.assertEqual(Angle.from_gradians(100).turns, 0.25)
        self.assertEqual(Angle.from_turns(100).turns, 100)
        self.assertEqual(Angle.from_gradians(100).gradians, 100)
        self.assertEqual(Angle.from_degrees(100).degrees, 100)
        self.assertEqual(Angle.from_radians(100).radians, 100)
        self.assertEqual(Angle("90deg").radians, tau / 4.0)
        self.assertEqual(Angle("90turn").radians, tau * 90)

    def test_angle_equal(self):
        self.assertEqual(Angle.from_degrees(0), Angle.from_degrees(-360))
        self.assertEqual(Angle.from_degrees(0), Angle.from_degrees(360))
        self.assertEqual(Angle.from_degrees(0), Angle.from_degrees(1080))
        self.assertNotEqual(Angle.from_degrees(0), Angle.from_degrees(180))
        self.assertEqual(Angle.from_degrees(0), Angle.from_turns(5))

    def test_orth(self):
        self.assertTrue(Angle.from_degrees(0).is_orthogonal())
        self.assertTrue(Angle.from_degrees(90).is_orthogonal())
        self.assertTrue(Angle.from_degrees(180).is_orthogonal())
        self.assertTrue(Angle.from_degrees(270).is_orthogonal())
        self.assertTrue(Angle.from_degrees(360).is_orthogonal())

        self.assertFalse(Angle.from_degrees(1).is_orthogonal())
        self.assertFalse(Angle.from_degrees(91).is_orthogonal())
        self.assertFalse(Angle.from_degrees(181).is_orthogonal())
        self.assertFalse(Angle.from_degrees(271).is_orthogonal())
        self.assertFalse(Angle.from_degrees(361).is_orthogonal())
