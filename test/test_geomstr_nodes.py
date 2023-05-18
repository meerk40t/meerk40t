import unittest

from meerk40t.core.node.elem_polyline import PolylineNode
from meerk40t.tools.geomstr import Geomstr


class TestGeomstr(unittest.TestCase):
    """These tests ensure the basic functions of the Geomstr node types"""

    def test_polynode_points(self):
        node = PolylineNode(Geomstr.lines(0, 0, 1, 1, 2, 2, 3, 3, 4, 4))
        self.assertEqual(len(node.geometry), 4)
        node = PolylineNode(0, 0, 1, 1, 2, 2, 3, 3, 4, 4)
        self.assertEqual(len(node.geometry), 4)
