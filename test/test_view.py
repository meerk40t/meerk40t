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
        if not getattr(v, "MARGIN_NONWORKING", False):
            v.set_margins(10, 20)
        # Assert
        self.assertEqual(v.dpi_x, UNITS_PER_INCH / 2)
        self.assertEqual(v.dpi_y, UNITS_PER_INCH / 4)
        self.assertEqual(v.width, 300)
        self.assertEqual(v.height, 400)
        if not getattr(v, "MARGIN_NONWORKING", False):
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
        tl, tr, br, bl = v._destination
        # print (v._destination)
        self.assertEqual(tl, (80.0, 180.0))
        self.assertEqual(tr, (80.0, -20.0))
        self.assertEqual(br, (-20.0, -20.0))
        self.assertEqual(bl, (-20.0, 180.0))

    def test_position_and_iposition_and_scene_position(self):
        # Arrange
        TX = 10
        TY = 20
        MX = 5
        MY = 10
        SX = 2
        SY = 3
        v = View(100, 200, native_scale_x=SX, native_scale_y=SY)
        if getattr(v, "MARGIN_NONWORKING", False):
            MX = 0
            MY = 0
        v.set_margins(MX, MY)
        v.realize()
        # Act
        off_x, off_y = v.calc_margins(vector=False, margins=True)
        self.assertEqual((off_x, off_y), (MX, MY))
        off_x, off_y = v.calc_margins(vector=True, margins=True)
        self.assertEqual((off_x, off_y), (0, 0))
        pos_x, pos_y = v.position(TX, TY)
        pos_vec_x, pos_vec_y = v.position(TX, TY, vector=True)
        pos_nomargin_x, pos_nomargin_y = v.position(TX, TY, margins=False)
        scene_x, scene_y = v.scene_position("30", "40")
        ipos_x, ipos_y = v.iposition(pos_x, pos_y)
        ipos_vec_x, ipos_vec_y = v.iposition(pos_vec_x, pos_vec_y, vector=True)
        # print (f"\nRegular of {TX}, {TY} -> {pos_x:.2f}, {pos_y:.2f} -> {ipos_x:.2f}, {ipos_y:.2f}")
        # print (f"Vector of {TX}, {TY} -> {pos_vec_x:.2f}, {pos_vec_y:.2f} -> {ipos_vec_x:.2f}, {ipos_vec_y:.2f}")
        # Assert position with vector=False
        self.assertAlmostEqual(pos_x * SX, TX + MX)        
        self.assertAlmostEqual(pos_y * SY, TY + MY)
        # Assert position with vector=True
        self.assertAlmostEqual(pos_vec_x * SX, TX)        
        self.assertAlmostEqual(pos_vec_y * SY, TY)
        # Assert inverse position 
        self.assertAlmostEqual(ipos_x, TX)        
        self.assertAlmostEqual(ipos_y, TY)
        # Assert inverse position with vector = True
        self.assertAlmostEqual(ipos_vec_x, TX)        
        self.assertAlmostEqual(ipos_vec_y, TY)

        self.assertEqual((pos_nomargin_x * SX, pos_nomargin_y * SY), (TX, TY))
        self.assertEqual((scene_x, scene_y), (30, 40))

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
