import unittest

from meerk40t.fill.fills import eulerian_fill
from meerk40t.svgelements import Path, Polyline


class TestFill(unittest.TestCase):
    """Tests the functionality of fills."""

    def test_fill_euler(self):
        w = 10000
        h = 10000
        paths = Path(Polyline(
            (w * 0.05, h * 0.05),
            (w * 0.95, h * 0.05),
            (w * 0.95, h * 0.95),
            (w * 0.05, h * 0.95),
            (w * 0.05, h * 0.05),
        )), Path(Polyline(
            (w * 0.25, h * 0.25),
            (w * 0.75, h * 0.25),
            (w * 0.75, h * 0.75),
            (w * 0.25, h * 0.75),
            (w * 0.25, h * 0.25),
        ))
        fills = list(eulerian_fill(None, {}, None, paths))
        self.assertEqual(len(fills), 1)
        fill = fills[0]
        self.assertEqual(len(fill), 13)
        for x, y in fill:
            self.assertIn(x, (500, 2500, 7500, 9500))
