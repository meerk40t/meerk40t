"""
This is a giant list of console commands that deal with and often implement the elements system in the program.
"""


from meerk40t.kernel import Service
from ..units import NATIVE_UNIT_PER_INCH, UNITS_PER_MM
from ..view import View


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "register":
        kernel.add_service("coord", CoordinateSystem(kernel))


class CoordinateSystem(Service):
    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "coord")
        _ = kernel.translation
        choices = [
            {
                "attr": "origin_x",
                "object": self,
                "default": 0.0,
                "type": float,
                "label": _("Origin X"),
                "tip": _("Value between 0-1 for the location of the origin x parameter"),
            },
            {
                "attr": "origin_y",
                "object": self,
                "default": 0.0,
                "type": float,
                "label": _("Origin Y"),
                "tip": _("Value between 0-1 for the location of the origin x parameter"),
            },
            {
                "attr": "right_positive",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Right Positive"),
                "tip": _("Are positive values to the right?"),
            },
            {
                "attr": "bottom_positive",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Bottom Positive"),
                "tip": _("Are positive values towards the bottom?"),
            },
            {
                "attr": "swap_xy",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Swap XY"),
                "tip": _("XY coordinates are swapped"),
            },
            {
                "attr": "rotation",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Rotation"),
                "tip": _("Rotation in degrees"),
            },
            {
                "attr": "units",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Preferred Units"),
                "tip": _("Set default units for positions"),
                "style": "option",
                "display": (_("tat"), _("mm"), _("cm"), _("inch"), _("mil")),
                "choices": (0, 1, 2, 3, 4),
            },
        ]
        kernel.register_choices("coords", choices)

        self.display = View(100.0, 100.0, dpi_x=UNITS_PER_MM, dpi_y=UNITS_PER_MM)

        # calculate show view
        self.display.transform(
            origin_x=self.origin_x,
            origin_y=self.origin_y,
            flip_x=self.right_positive,
            flip_y=self.bottom_positive,
            swap_xy=self.show_swap_xy,
        )


    def physical_to_device_position(self, x, y, unitless=1):
        """
        Converts a physical X,Y position into device units.

        @param x:
        @param y:
        @param unitless:
        @return:
        """
        px, py = self.scene_view.physical(x, y)
        return self.scene_to_device_position(px, py)

    def physical_to_scene_position(self, x, y, unitless=1):
        """
        Converts a physical X,Y position into viewport units.

        This does not depend on the device except for the width/height for converting percent values.

        @param x:
        @param y:
        @param unitless:
        @return:
        """
        return self.scene_view.physical(x, y)

    def physical_to_show_position(self, x, y, unitless=1):
        """
        Converts a physical X,Y position into show units.

        @param x:
        @param y:
        @param unitless:
        @return:
        """
        px, py = self.scene_view.physical(x, y)
        return self.scene_to_show_position(px, py)


    def device_to_show_matrix(self):
        """
        Returns the device-to-scene matrix.
        """
        return self.device_to_show.matrix


    def scene_to_show_matrix(self):
        """
        Returns the scene-to-device matrix.
        """
        return self.scene_to_show.matrix

    def show_to_device_matrix(self):
        """
        Returns the scene-to-device matrix.
        """
        return self.show_to_device.matrix

    def show_to_scene_matrix(self):
        """
        Returns the device-to-scene matrix.
        """
        return self.show_to_scene.matrix


    # def physical_to_device_length(self, x, y, unitless=1):
    #     """
    #     Converts a physical X,Y vector into device vector (dx, dy).
    #
    #     This natively assumes device coordinate systems are affine. If we convert (0, 1in) as a vector into
    #     machine units we are converting the length of 1in into the equal length in machine units. Positionally this
    #     could be flipped or moved anywhere in the machine. But, the distance should be the same. However, in some cases
    #     due to belt stretching etc. we can have scaled x vs y coord systems so (1in, 0) could be a different length
    #     than (0, 1in).
    #
    #     @param x:
    #     @param y:
    #     @param unitless:
    #     @return:
    #     """
    #     px, py = self.scene_view.physical(x, y)
    #     return self.scene_to_device_position(px, py, vector=True)


    # def device_to_show_position(self, x, y, vector=False):
    #     """
    #     @param x:
    #     @param y:
    #     @param vector:
    #     @return:
    #     """
    #     if vector:
    #         point = self.device_to_show.matrix.transform_vector((x, y))
    #         return point.x, point.y
    #     else:
    #         point = self.device_to_show.matrix.point_in_matrix_space((x, y))
    #         return point.x, point.y
    #
    #
    # def scene_to_show_position(self, x, y, vector=False):
    #     """
    #     @param x:
    #     @param y:
    #     @param vector:
    #     @return:
    #     """
    #     if vector:
    #         point = self.scene_to_show.matrix.transform_vector([x, y])
    #         return point[0], point[1]
    #     else:
    #         point = self.scene_to_show.matrix.point_in_matrix_space((x, y))
    #         return point.x, point.y
    #
    # def show_to_device_position(self, x, y, vector=False):
    #     """
    #     @param x:
    #     @param y:
    #     @param vector:
    #     @return:
    #     """
    #     if vector:
    #         point = self.show_to_device.matrix.transform_vector((x, y))
    #         return point.x, point.y
    #     else:
    #         point = self.show_to_device.matrix.point_in_matrix_space((x, y))
    #         return point.x, point.y
    #
    # def show_to_scene_position(self, x, y, vector=False):
    #     """
    #     @param x:
    #     @param y:
    #     @param vector:
    #     @return:
    #     """
    #     if vector:
    #         point = self.show_to_scene.matrix.transform_vector((x, y))
    #         return point.x, point.y
    #     else:
    #         point = self.show_to_scene.matrix.point_in_matrix_space((x, y))
    #         return point.x, point.y
