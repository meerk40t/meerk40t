import math
import unittest

from PIL import Image, ImageDraw

from meerk40t.core.node.elem_image import ImageNode
from meerk40t.svgelements import Matrix
from test import bootstrap


SOURCE_SIZE = 256
CONTENT_INSET = 50
CONTENT_SIZE = SOURCE_SIZE - 2 * CONTENT_INSET


def _padded_source():
    img = Image.new("RGBA", (SOURCE_SIZE, SOURCE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    inset = CONTENT_INSET
    draw.rectangle(
        (inset, inset, SOURCE_SIZE - inset - 1, SOURCE_SIZE - inset - 1),
        fill=(0, 0, 0, 255),
    )
    return img


def _unpadded_source():
    return Image.new("RGBA", (SOURCE_SIZE, SOURCE_SIZE), (0, 0, 0, 255))


class TestProcessImageCropTranslate(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap.bootstrap()

    def tearDown(self):
        self.kernel()

    def _process(self, source_image, matrix):
        node = ImageNode(image=source_image, matrix=Matrix(matrix))
        node.step_x = 1
        node.step_y = 1
        node.process_image(step_x=1, step_y=1, crop=True)
        return node

    def _assert_origin_matches_bbox(self, node):
        bbox = node.bbox()
        ax0, ay0 = node.active_matrix.point_in_matrix_space((0, 0))
        self.assertAlmostEqual(ax0, bbox[0], delta=1.0)
        self.assertAlmostEqual(ay0, bbox[1], delta=1.0)

    def test_padded_rotated(self):
        m = Matrix()
        m.post_rotate(math.radians(9))
        m.post_scale(10, 10)
        m.post_translate(1000, 2000)
        self._assert_origin_matches_bbox(self._process(_padded_source(), m))

    def test_padded_unrotated(self):
        m = Matrix.scale(10, 10)
        m.post_translate(1000, 2000)
        self._assert_origin_matches_bbox(self._process(_padded_source(), m))

    def test_unpadded_rotated(self):
        m = Matrix()
        m.post_rotate(math.radians(9))
        m.post_scale(10, 10)
        m.post_translate(1000, 2000)
        self._assert_origin_matches_bbox(self._process(_unpadded_source(), m))

    def test_as_image_bounds_match_bbox(self):
        node = self._process(_padded_source(), Matrix.scale(10, 10))
        _img, asimage_bounds = node.as_image()
        self.assertEqual(tuple(asimage_bounds), tuple(node.bbox()))
