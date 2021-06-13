
import unittest

from meerk40t.core.cutcode import LaserSettings, LineCut, CutCode, QuadCut
from meerk40t.core.elements import LaserOperation
from meerk40t.svgelements import Point, Path


class TestCutcode(unittest.TestCase):
    def test_cutcode(self):
        """
        Test intro to Cutcode.

        :return:
        """
        cutcode = CutCode()
        settings = LaserSettings()
        cutcode.append(LineCut(Point(0, 0), Point(100, 100), settings=settings))
        cutcode.append(LineCut(Point(100, 100), Point(0, 0), settings=settings))
        cutcode.append(LineCut(Point(50, -50), Point(100, -100), settings=settings))
        cutcode.append(
            QuadCut(Point(0, 0), Point(100, 100), Point(200, 0), settings=settings)
        )
        path = Path(*cutcode.as_elements())
        self.assertEqual(
            path, "M 0,0 L 100,100 L 0,0 M 50,-50 L 100,-100 M 0,0 Q 100,100 200,0"
        )

    def test_cutcode_cut(self):
        """
        Convert and Engrave Operation into Cutcode and Back.

        :return:
        """
        initial = "M 0,0 L 100,100 L 0,0 M 50,-50 L 100,-100 M 0,0 Q 100,100 200,0"
        path = Path(initial)
        laserop = LaserOperation()
        laserop.operation = "Cut"
        laserop.add(path, type="opnode")
        cutcode = list(laserop.as_blob)[0]
        path = Path(*cutcode.as_elements())
        self.assertEqual(path, initial)

    def test_cutcode_engrave(self):
        """
        Convert and Engrave Operation into Cutcode and Back.

        :return:
        """
        initial = "M 0,0 L 100,100 L 0,0 M 50,-50 L 100,-100 M 0,0 Q 100,100 200,0"
        path = Path(initial)
        laserop = LaserOperation()
        laserop.operation = "Engrave"
        laserop.add(path, type="opnode")
        cutcode = list(laserop.as_blob)[0]
        path = Path(*cutcode.as_elements())
        self.assertEqual(path, initial)

    def test_cutcode_no_type(self):
        """
        Convert and Engrave Operation into Cutcode and Back.

        :return:
        """
        initial = "M 0,0 L 100,100 L 0,0 M 50,-50 L 100,-100 M 0,0 Q 100,100 200,0"
        path = Path(initial)
        laserop = LaserOperation()
        # Operation type is unset.
        laserop.add(path, type="opnode")
        cutcode = list(laserop.as_blob)[0]
        self.assertEqual(cutcode, None)

    def test_cutcode_raster(self):
        """
        Convert and Raster Operation

        :return:
        """
        initial = "M 0,0 L 100,100 L 0,0 M 50,-50 L 100,-100 M 0,0 Q 100,100 200,0"
        path = Path(initial)
        laserop = LaserOperation()
        laserop.operation = "Raster"
        laserop.add(path, type="opnode")
        # There is no method of turning the path into a raster image without a renderer.
