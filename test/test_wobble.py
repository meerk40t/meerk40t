import unittest

from meerk40t.fill.fills import (
    Wobble,
    circle,
    gear,
    jigsaw,
    sawtooth,
    sinewave,
    slowtooth,
)


class TestWobble(unittest.TestCase):
    """Tests the functionality of wobble."""

    def test_wobble_circle_fract(self):
        wobble = Wobble(
            algorithm=circle,
            radius=10,
            speed=5,
            interval=1,
        )
        for i in range(1000):
            if (i + 1) % 10 == 0:
                self.assertEqual(1, len(list(wobble(i / 10, 0, (i + 1) / 10, 0))))
            else:
                self.assertEqual(0, len(list(wobble(i / 10, 0, (i + 1) / 10, 0))))
        self.assertEqual(50, len(list(wobble(0, 0, 50.5, 0))))
        self.assertEqual(51, len(list(wobble(0, 0, 50.5, 0))))
        self.assertEqual(201, wobble._total_distance)

    def test_wobble_circle_1(self):
        wobble = Wobble(
            algorithm=circle,
            radius=10,
            speed=5,
            interval=1,
        )
        self.assertEqual(100, len(list(wobble(0, 0, 100, 0))))
        self.assertEqual(50, len(list(wobble(0, 0, 50.5, 0))))
        self.assertEqual(51, len(list(wobble(0, 0, 50.5, 0))))
        self.assertEqual(201, wobble._total_distance)

    def test_wobble_circle_10(self):
        wobble = Wobble(
            algorithm=circle,
            radius=10,
            speed=5,
            interval=10,
        )
        self.assertEqual(10, len(list(wobble(0, 0, 100, 0))))
        self.assertEqual(5, len(list(wobble(0, 0, 55, 0))))
        self.assertEqual(6, len(list(wobble(0, 0, 55, 0))))
        self.assertEqual(210, wobble._total_distance)

    def test_wobble_circle_10_2(self):
        wobble = Wobble(
            algorithm=circle,
            radius=10,
            speed=5,
            interval=10,
        )
        self.assertEqual(10, len(list(wobble(0, 0, 100, 0))))
        self.assertEqual(5, len(list(wobble(0, 0, 55.1, 0))))
        self.assertEqual(6, len(list(wobble(0, 0, 55, 0))))
        self.assertAlmostEqual(0.1 / 10, wobble._remainder)
        self.assertEqual(210, wobble._total_distance)

    def test_wobble_sinewave_10_2(self):
        wobble = Wobble(
            algorithm=sinewave,
            radius=10,
            speed=5,
            interval=10,
        )
        self.assertEqual(10, len(list(wobble(0, 0, 100, 0))))
        self.assertEqual(5, len(list(wobble(0, 0, 55.1, 0))))
        self.assertEqual(6, len(list(wobble(0, 0, 55, 0))))
        self.assertAlmostEqual(0.1 / 10, wobble._remainder)
        self.assertEqual(210, wobble._total_distance)

    def test_wobble_sawtooth_10_2(self):
        wobble = Wobble(
            algorithm=sawtooth,
            radius=10,
            speed=5,
            interval=10,
        )
        self.assertEqual(10, len(list(wobble(0, 0, 100, 0))))
        self.assertEqual(5, len(list(wobble(0, 0, 55.1, 0))))
        self.assertEqual(6, len(list(wobble(0, 0, 55, 0))))
        self.assertAlmostEqual(0.1 / 10, wobble._remainder)
        self.assertEqual(210, wobble._total_distance)

    def test_wobble_jigsaw_10_2(self):
        wobble = Wobble(
            algorithm=jigsaw,
            radius=10,
            speed=5,
            interval=10,
        )
        self.assertEqual(10, len(list(wobble(0, 0, 100, 0))))
        self.assertEqual(5, len(list(wobble(0, 0, 55.1, 0))))
        self.assertEqual(6, len(list(wobble(0, 0, 55, 0))))
        self.assertAlmostEqual(0.1 / 10, wobble._remainder)
        self.assertEqual(210, wobble._total_distance)

    def test_wobble_gear_10_2(self):
        wobble = Wobble(
            algorithm=gear,
            radius=10,
            speed=5,
            interval=10,
        )
        self.assertEqual(10, len(list(wobble(0, 0, 100, 0))))
        self.assertEqual(5, len(list(wobble(0, 0, 55.1, 0))))
        self.assertEqual(6, len(list(wobble(0, 0, 55, 0))))
        self.assertAlmostEqual(0.1 / 10, wobble._remainder)
        self.assertEqual(210, wobble._total_distance)

    def test_wobble_slowtooth_10_2(self):
        wobble = Wobble(
            algorithm=slowtooth,
            radius=10,
            speed=5,
            interval=10,
        )
        self.assertEqual(10, len(list(wobble(0, 0, 100, 0))))
        self.assertEqual(5, len(list(wobble(0, 0, 55.1, 0))))
        self.assertEqual(6, len(list(wobble(0, 0, 55, 0))))
        self.assertAlmostEqual(0.1 / 10, wobble._remainder)
        self.assertEqual(210, wobble._total_distance)
