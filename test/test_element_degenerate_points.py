import os
import unittest

from meerk40t.core.element_types import elem_nodes
from meerk40t.core.node.elem_point import PointNode
from test import bootstrap


class TestShapePoints(unittest.TestCase):
    def test_shapes_are_points(self):
        """
        Test the ability shapes to convert to points if they meet criteria set in 0.7.x

        :return:
        """
        file1 = "text.svg"
        self.addCleanup(os.remove, file1)
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            elements = kernel_root.elements
            with open(file1, "w") as f:
                f.write("""<svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:ev="http://www.w3.org/2001/xml-events" xmlns:meerk40t="https://github.com/meerk40t/meerk40t/wiki/Namespace" width="110.0mm" height="110.0mm" viewBox="0 0 416 416" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
<element type="elem point" x="36.65648536929456" y="77.38541766211871" id="meerk40t:24" stroke_width="1000.0" lock="False" stroke="#0000ff" stroke-width="none" fill="none" />
<path d="M36.65648536929456,77.38541766211871" id="degenerate_dot" lock="True" stroke="#0000ff"/>
<path d="M36.65648536929456,77.38541766211871Z" id="degenerate_dot_z" lock="True" stroke="#0000ff"/>
<path d="M0,0Z" transform="translate(36.65648536929456,77.38541766211871)" lock="True" stroke="#0000ff"/>
<polygon points="36.65648536929456,77.38541766211871" lock="False" stroke="#0000ff"/>
<polyline points="36.65648536929456,77.38541766211871" lock="False" stroke="#0000ff"/>
<line x1="36.65648536929456" y1="77.38541766211871" x2="36.65648536929456" y2="77.38541766211871" lock="False" stroke="cornflower blue"/>
                </svg>""")
            elements.load(file1)
            results = list(elements.elem_branch.flat(types=elem_nodes))
            self.assertEqual(len(results), 7)
            for i in range(1, len(results)):
                self.assertEqual(results[i-1].bbox(), results[i].bbox())
            for n in results:
                self.assertEqual(n.type, "elem point")
                self.assertEqual(type(n), PointNode)
        finally:
            kernel.shutdown()
