import random
import unittest

from meerk40t.core.units import UNITS_PER_MIL, Length, ViewPort


class TestViewport(unittest.TestCase):
    def test_viewport_arbitrary(self):
        """
        Test arbitrary viewport.

        :return:
        """
        bed_width = Length(amount=random.randint(0, 65535 * 1000)).length_mm
        bed_height = Length(amount=random.randint(0, 65535 * 1000)).length_mm
        for i in range(100):
            view = ViewPort(
                bed_width,
                bed_height,
                user_scale_x=1.0,
                user_scale_y=1.0,
                native_scale_x=UNITS_PER_MIL,
                native_scale_y=UNITS_PER_MIL,
                origin_x=random.random(),
                origin_y=random.random(),
                flip_x=bool(random.randint(0, 1)),
                flip_y=bool(random.randint(0, 1)),
                swap_xy=bool(random.randint(0, 1)),
                show_origin_x=random.random(),
                show_origin_y=random.random(),
                show_flip_x=bool(random.randint(0, 1)),
                show_flip_y=bool(random.randint(0, 1)),
            )

            x, y = view.scene_to_device_position(0, 0)
            x, y = view.device_to_scene_position(x, y)
            self.assertAlmostEqual(x, 0, delta=10)
            self.assertAlmostEqual(y, 0, delta=10)

            x, y = view.show_to_device_position(0, 0)
            x, y = view.device_to_show_position(x, y)
            self.assertAlmostEqual(x, 0, delta=10)
            self.assertAlmostEqual(y, 0, delta=10)

    def test_viewport_lihuiyu_user_scale(self):
        """
        Test Lihuiyu-esque viewport. User-scaled to mm

        :return:
        """
        bed_width = "330mm"
        bed_height = "225mm"

        view = ViewPort(
            bed_width,
            bed_height,
            user_scale_x=1.2,
            user_scale_y=1.0,
            native_scale_x=UNITS_PER_MIL,
            native_scale_y=UNITS_PER_MIL,
            origin_x=0,
            origin_y=0,
        )
        x, y = view.scene_to_device_position(0, 0)
        self.assertAlmostEqual(x, 0, delta=10)
        self.assertAlmostEqual(y, 0, delta=10)

        x, y = view.scene_to_device_position(0, 0)
        self.assertAlmostEqual(x, 0, delta=10)
        self.assertAlmostEqual(y, 0, delta=10)

        x, y = view.device_to_scene_position(0, Length(bed_height).mil)
        self.assertAlmostEqual(x, 0, delta=10)
        self.assertAlmostEqual(y, float(Length(bed_height)), delta=10)

        x, y = view.device_to_scene_position(
            Length(bed_width).mil, Length(bed_height).mil
        )
        self.assertAlmostEqual(x, float(Length(bed_width)) * 1.2, delta=10)
        self.assertAlmostEqual(y, float(Length(bed_height)), delta=10)

    def test_viewport_lihuiyu_swap_xy(self):
        """
        Test Lihuiyu-esque viewport. User-scaled to mm

        :return:
        """
        bed_width = "330mm"
        bed_height = "225mm"

        view = ViewPort(
            bed_width,
            bed_height,
            user_scale_x=1.2,
            user_scale_y=1.0,
            native_scale_x=UNITS_PER_MIL,
            native_scale_y=UNITS_PER_MIL,
            origin_x=0,
            origin_y=0,
            swap_xy=True,
        )
        x, y = view.scene_to_device_position(0, 0)
        self.assertAlmostEqual(x, 0, delta=2)
        self.assertAlmostEqual(y, 0, delta=2)

        x, y = view.scene_to_device_position(0, 0)
        self.assertAlmostEqual(x, 0, delta=10)
        self.assertAlmostEqual(y, 0, delta=10)

        x, y = view.device_to_scene_position(0, Length(bed_height).mil)
        self.assertAlmostEqual(x, float(Length(bed_height)), delta=10)
        self.assertAlmostEqual(y, 0, delta=10)

        x, y = view.device_to_scene_position(
            Length(bed_width).mil, Length(bed_height).mil
        )
        self.assertAlmostEqual(x, float(Length(bed_height)), delta=10)
        self.assertAlmostEqual(y, float(Length(bed_width)) * 1.2, delta=10)

    def test_viewport_grbl(self):
        """
        Test GRBL-esque viewport.

        :return:
        """
        bed_size = "225mm"

        view = ViewPort(
            bed_size,
            bed_size,
            native_scale_x=UNITS_PER_MIL,
            native_scale_y=UNITS_PER_MIL,
            origin_x=0,
            origin_y=0,
            flip_y=True,
        )
        x, y = view.scene_to_device_position(0, 0)
        self.assertAlmostEqual(x, 0, delta=10)
        self.assertAlmostEqual(y, Length(bed_size).mil, delta=10)

        x, y = view.scene_to_device_position(0, float(Length(bed_size)))
        self.assertAlmostEqual(x, 0, delta=10)
        self.assertAlmostEqual(y, 0, delta=10)

        x, y = view.device_to_scene_position(0, Length(bed_size).mil)
        self.assertAlmostEqual(x, 0, delta=10)
        self.assertAlmostEqual(y, 0, delta=10)

    def test_viewport_grbl_user_scale(self):
        """
        Test GRBL-esque viewport. User-scaled to mm

        :return:
        """
        bed_size = "225mm"

        view = ViewPort(
            bed_size,
            bed_size,
            user_scale_x=1.0 / Length("1mil").mm,
            user_scale_y=1.0 / Length("1mil").mm,
            native_scale_x=UNITS_PER_MIL,
            native_scale_y=UNITS_PER_MIL,
            origin_x=0,
            origin_y=1,
            flip_y=True,
        )
        x, y = view.scene_to_device_position(0, 0)
        self.assertAlmostEqual(x, 0, delta=10)
        self.assertAlmostEqual(y, Length(bed_size).mm, delta=1)

        x, y = view.scene_to_device_position(0, float(Length(bed_size)))
        self.assertAlmostEqual(x, 0, delta=10)
        self.assertAlmostEqual(y, 0, delta=10)

        x, y = view.device_to_scene_position(0, Length(bed_size).mm)
        self.assertAlmostEqual(x, 0, delta=10)
        self.assertAlmostEqual(y, 0, delta=10)

    def test_viewport_balor_device_to_scene(self):
        """
        Test Balor-esque viewport.
        Center x, y. normal_x/flip_x, normal_y/flip_y, swap and non-linear

        Device to show position.

        :return:
        """
        lens_size_x = "110mm"
        lens_size_y = "100mm"  # 10mm less
        unit_size_x = float(Length(lens_size_x))
        unit_size_y = float(Length(lens_size_y))
        galvo_range = 0xFFFF
        units_per_galvo_x = unit_size_x / galvo_range
        units_per_galvo_y = unit_size_y / galvo_range

        for flip_x in (False, True):
            for flip_y in (False, True):
                for swap_xy in (False, True):
                    for show_flip_x in (False, True):
                        for show_flip_y in (False, True):
                            view = ViewPort(
                                lens_size_x,
                                lens_size_y,
                                native_scale_x=units_per_galvo_x,
                                native_scale_y=units_per_galvo_y,
                                origin_x=0,
                                origin_y=0,
                                flip_x=flip_x,
                                flip_y=flip_y,
                                swap_xy=swap_xy,
                                show_origin_x=0.5,
                                show_origin_y=0.5,
                                show_flip_x=show_flip_x,
                                show_flip_y=show_flip_y,
                            )
                            sx, sy = view.device_to_scene_position(0x7FFF, 0x7FFF)
                            # print((flip_x, flip_y, swap_xy, show_flip_x, show_flip_y))
                            self.assertAlmostEqual(sx, unit_size_x / 2, delta=10)
                            self.assertAlmostEqual(sy, unit_size_y / 2, delta=10)
                            vx, vy = view.physical_to_device_position("50%", "50%")
                            self.assertAlmostEqual(vx, 0x7FFF, delta=10)
                            self.assertAlmostEqual(vy, 0x7FFF, delta=10)

    def test_viewport_balor_device_to_show(self):
        """
        Test Balor-esque viewport.
        Center x, y. normal_x/flip_x, normal_y/flip_y, swap and non-linear

        Device to show position.

        :return:
        """
        lens_size_x = "110mm"
        lens_size_y = "100mm"  # 10mm less
        unit_size_x = float(Length(lens_size_x))
        unit_size_y = float(Length(lens_size_y))
        galvo_range = 0xFFFF
        units_per_galvo_x = unit_size_x / galvo_range
        units_per_galvo_y = unit_size_y / galvo_range

        for flip_x in (False, True):
            for flip_y in (False, True):
                for swap_xy in (False, True):
                    for show_flip_x in (False, True):
                        for show_flip_y in (False, True):
                            view = ViewPort(
                                lens_size_x,
                                lens_size_y,
                                native_scale_x=units_per_galvo_x,
                                native_scale_y=units_per_galvo_y,
                                origin_x=1.0 if flip_x else 0.0,
                                origin_y=1.0 if flip_y else 0.0,
                                flip_x=flip_x,
                                flip_y=flip_y,
                                swap_xy=swap_xy,
                                show_origin_x=0.5,
                                show_origin_y=0.5,
                                show_flip_x=show_flip_x,
                                show_flip_y=show_flip_y,
                            )
                            x, y = view.device_to_show_position(0x7FFF, 0x7FFF)
                            self.assertAlmostEqual(x, 0, delta=10)
                            self.assertAlmostEqual(y, 0, delta=10)
                            x, y = view.show_to_device_position(0, 0)
                            self.assertAlmostEqual(x, 0x7FFF, delta=10)
                            self.assertAlmostEqual(y, 0x7FFF, delta=10)

    def test_viewport_balor_physical_to_show(self):
        """
        Test Balor-esque viewport.
        Center x, y. flip_x, flip_y, swap and offset

        :return:
        """
        lens_size_x = "110mm"
        lens_size_y = "100mm"  # 10mm less
        unit_size_x = float(Length(lens_size_x))
        unit_size_y = float(Length(lens_size_y))
        galvo_range = 0xFFFF
        units_per_galvo_x = unit_size_x / galvo_range
        units_per_galvo_y = unit_size_y / galvo_range

        for flip_x in (False, True):
            for flip_y in (False, True):
                for swap_xy in (False, True):
                    view = ViewPort(
                        lens_size_x,
                        lens_size_y,
                        native_scale_x=units_per_galvo_x,
                        native_scale_y=units_per_galvo_y,
                        origin_x=1.0 if flip_x else 0.0,
                        origin_y=1.0 if flip_y else 0.0,
                        show_origin_x=0.5,
                        show_origin_y=0.5,
                        flip_x=flip_x,
                        flip_y=flip_y,
                        swap_xy=swap_xy,
                    )
                    hx, hy = view.physical_to_show_position("55mm", "50mm")
                    self.assertAlmostEqual(hx, 0)
                    self.assertAlmostEqual(hy, 0)

    def test_viewport_balor_physical_to_scene(self):
        """
        Test Balor-esque viewport.
        Center x, y. flip_x, flip_y, swap and offset

        :return:
        """
        lens_size_x = "110mm"
        lens_size_y = "100mm"  # 10mm less
        unit_size_x = float(Length(lens_size_x))
        unit_size_y = float(Length(lens_size_y))
        galvo_range = 0xFFFF
        units_per_galvo_x = unit_size_x / galvo_range
        units_per_galvo_y = unit_size_y / galvo_range

        for flip_x in (False, True):
            for flip_y in (False, True):
                for swap_xy in (False, True):
                    view = ViewPort(
                        lens_size_x,
                        lens_size_y,
                        native_scale_x=units_per_galvo_x,
                        native_scale_y=units_per_galvo_y,
                        origin_x=0.0,
                        origin_y=0.0,
                        show_origin_x=0.5,
                        show_origin_y=0.5,
                        flip_x=flip_x,
                        flip_y=flip_y,
                        swap_xy=swap_xy,
                    )
                    sx, sy = view.physical_to_scene_position("50%", "50%")

                    dim0 = view.unit_width / 2
                    dim1 = view.unit_height / 2
                    self.assertAlmostEqual(sx, dim0)
                    self.assertAlmostEqual(sy, dim1)

                    cx, cy = view.device_to_scene_position(0x7FFF, 0x7FFF)
                    self.assertAlmostEqual(sx, cx, delta=10)
                    self.assertAlmostEqual(sy, cy, delta=10)
