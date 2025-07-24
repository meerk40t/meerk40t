import unittest
from meerk40t.core.view import View
from meerk40t.core.units import UNITS_PER_INCH, MM_PER_INCH, Length
from meerk40t.svgelements import Matrix, Point


class TestView(unittest.TestCase):
    def test_init_and_properties(self):
        # Arrange

        # Act
        v = View(100, 200, 96)
        # Assert
        self.assertEqual(v.width, 100)
        self.assertEqual(v.height, 200)
        self.assertIsNotNone(v._source)
        self.assertIsNotNone(v._destination)
        self.assertTrue(isinstance(str(v), str))
        self.assertGreater(v.native_scale_x, 0)
        self.assertGreater(v.native_scale_y, 0)
        self.assertGreater(v.mm, 0)

    def test_set_native_scale_and_set_dims_and_set_margins(self):
        # Arrange
        v = View(100, 200)
        # Act
        v.set_native_scale(2, 4)
        v.set_dims(300, 400)
        v.set_margins(10, 20)
        # Assert
        self.assertEqual(v.dpi_x, UNITS_PER_INCH / 2)
        self.assertEqual(v.dpi_y, UNITS_PER_INCH / 4)
        self.assertEqual(v.width, 300)
        self.assertEqual(v.height, 400)
        self.assertEqual(v.margin_x, 10)
        self.assertEqual(v.margin_y, 20)

    def test_reset_and_scale_and_origin_and_flip_and_swap(self):
        # Arrange
        v = View(100, 200)
        # Act
        v.reset()
        v.scale(2, 0.5)
        v.origin(0.1, 0.2)
        v.flip_x()
        v.flip_y()
        v.swap_xy()
        v.rotate_ccw()
        v.rotate_cw()
        # Assert
        self.assertIsNotNone(v._destination)
        self.assertEqual(len(v._destination), 4)

    def test_destination_contains_and_source_contains(self):
        # Arrange
        v = View(100, 200)
        # Act & Assert
        self.assertTrue(v.destination_contains(50, 100))
        self.assertTrue(v.destination_contains(0, 0))
        self.assertFalse(v.destination_contains(200, 400))
        self.assertTrue(v.source_contains(50, 100))
        self.assertTrue(v.source_contains(0, 0))
        self.assertFalse(v.source_contains(200, 400))

    def test_destination_bbox_and_source_bbox(self):
        # Arrange
        v = View(100, 200)
        # Act
        dbbox = v.destination_bbox()
        sbbox = v.source_bbox()
        # Assert
        self.assertEqual(dbbox, (0, 0, 100, 200))
        self.assertEqual(sbbox, (0, 0, 100, 200))

    def test_transform_all_options(self):
        # Arrange
        v = View(100, 200)
        # Act
        v.transform(
            user_scale_x=2.0,
            user_scale_y=0.5,
            flip_x=True,
            flip_y=True,
            swap_xy=True,
            origin_x=0.1,
            origin_y=0.2,
        )
        # Assert
        self.assertIsNotNone(v._destination)

    def test_position_and_iposition_and_scene_position(self):
        # Arrange
        v = View(100, 200)
        v.set_margins(5, 10)
        # Act
        pos = v.position(10, 20)
        self.assertEqual(pos, (15, 30))
        pos_vec = v.position(10, 20, vector=True)
        pos_nomargin = v.position(10, 20, margins=False)
        scene = v.scene_position("30", "40")
        ipos = v.iposition(15, 30)
        self.assertEqual(ipos, (10, 20))
        ipos_vec = v.iposition(10, 20, vector=True)
        # Assert
        self.assertIsInstance(pos, (Point, tuple, list))
        self.assertIsInstance(pos_vec, (Point, tuple, list))
        self.assertIsInstance(pos_nomargin, (Point, tuple, list))
        self.assertEqual(scene, (30, 40))
        self.assertIsInstance(ipos, (Point, tuple, list))
        self.assertIsInstance(ipos_vec, (Point, tuple, list))

    def test_position_invalid_margins(self):
        # Arrange
        v = View(100, 200)
        v.margin_x = "notanumber"
        v.margin_y = 10
        # Act
        pos = v.position(10, 20)
        # Assert
        self.assertIsInstance(pos, (Point, tuple, list))

        # Arrange
        v.margin_x = 5
        v.margin_y = "notanumber"
        # Act
        pos = v.position(10, 20)
        # Assert
        self.assertIsInstance(pos, (Point, tuple, list))

    def test_iposition_invalid_margins(self):
        # Arrange
        v = View(100, 200)
        v.margin_x = "notanumber"
        v.margin_y = 10
        # Act
        ipos = v.iposition(10, 20)
        # Assert
        self.assertIsInstance(ipos, (Point, tuple, list))

        # Arrange
        v.margin_x = 5
        v.margin_y = "notanumber"
        # Act
        ipos = v.iposition(10, 20)
        # Assert
        self.assertIsInstance(ipos, (Point, tuple, list))

    def test_matrix_property_and_lazy_init(self):
        # Arrange
        v = View(100, 200)
        v._matrix = None
        # Act
        m = v.matrix
        # Assert
        self.assertIsInstance(m, Matrix)

    def test_get_sensible_dpi_values_and_dpi_to_steps(self):
        # Arrange
        v = View(100, 200)
        # Act
        dpis = v.get_sensible_dpi_values()
        step_x, step_y = v.dpi_to_steps(100)
        # Assert
        self.assertIsInstance(dpis, list)
        for d in dpis:
            self.assertIsInstance(d, int)
        self.assertIsInstance(step_x, float)
        self.assertIsInstance(step_y, float)

    def test_unit_width_and_unit_height(self):
        # Arrange
        v = View("100mm", "200mm")
        # Act
        uw = v.unit_width
        uh = v.unit_height
        # Assert
        self.assertEqual(uw, float(Length("100mm")))
        self.assertEqual(uh, float(Length("200mm")))


if __name__ == "__main__":
    unittest.main()
