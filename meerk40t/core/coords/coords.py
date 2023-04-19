"""
This is a giant list of console commands that deal with and often implement the elements system in the program.
"""
from meerk40t.core.viewmap import ViewMap
from meerk40t.kernel import Service
from meerk40t.core.units import UNITS_PER_MM, NATIVE_UNIT_PER_INCH, UNITS_PER_INCH, Length
from meerk40t.core.view import View


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "register":
        kernel.add_service("space", CoordinateSystem(kernel))


class CoordinateSystem(Service):
    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "space")
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

        self.width = "100mm"
        self.height = "100mm"
        self.display = View(self.width, self.height, dpi_x=UNITS_PER_MM, dpi_y=UNITS_PER_MM)
        self.scene = View(self.width, self.height, dpi=NATIVE_UNIT_PER_INCH)
        self.update_dims(self.width, self.height)

    def update_dims(self, width, height):
        self.width = width
        self.height = height
        self.display.set_dims(self.width, self.height)
        self.scene.set_dims(self.width, self.height)
        self.display.transform(
            origin_x=self.origin_x,
            origin_y=self.origin_y,
            flip_x=self.right_positive,
            flip_y=self.bottom_positive,
            swap_xy=self.swap_xy,
        )

    def get_view(self, view):
        if view == "scene":
            return self.scene
        if view == "device":
            return self.device.view
        if view == "display":
            return self.display

    def map(self, source, dest):
        view_map = ViewMap(self.get_view(source), self.get_view(dest))
        return view_map.matrix

    def length(self, v):
        return float(Length(v))

    def length_x(self, v):
        return float(Length(v, relative_length=self.width))

    def length_y(self, v):
        return float(Length(v, relative_length=self.height))

    def bounds(self, x0, y0, x1, y1):
        return (
            float(Length(x0, relative_length=self.width)),
            float(Length(y0, relative_length=self.height)),
            float(Length(x1, relative_length=self.width)),
            float(Length(y1, relative_length=self.height)),
        )

    def area(self, v):
        llx = Length(v, relative_length=self.width)
        lx = float(llx)
        if "%" in v:
            lly = Length(v, relative_length=self.height)
        else:
            lly = Length(f"1{llx._preferred_units}")
        ly = float(lly)
        return lx * ly

    def display_origin_in_scene_units(self):
        m = self.map("display", "scene")
        return m.point_in_matrix_space((0,0))

    def set_centered(self):
        self.origin_x = 0.5
        self.origin_y = 0.5
        # self.validate()

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

    def device_to_scene_position(self, x, y, vector=False):
        """
        Converts a device position x, y into a scene position of native units (1/65535) inches.
        @param x:
        @param y:
        @param vector:
        @return:
        """
        if self.device_to_scene is None:
            return x, y
        if vector:
            point = self.device_to_scene.matrix.transform_vector((x, y))
            return point.x, point.y
        else:
            point = self.device_to_scene.matrix.point_in_matrix_space((x, y))
            return point.x, point.y

    def scene_to_device_position(self, x, y, vector=False):
        """
        Converts scene to a device position (or vector). Converts x, y from scene units (1/65535) inches into
        device specific units. Optionally allows the calculation of a vector distance.

        @param x:
        @param y:
        @param vector:
        @return:
        """
        if vector:
            point = self.scene_to_device.matrix.transform_vector([x, y])
            return point[0], point[1]
        else:
            point = self.scene_to_device.matrix.point_in_matrix_space((x, y))
            return point.x, point.y

    def device_position(self, x, y):
        m = self.scene_to_device.matrix
        return m.point_in_matrix_space((x, y))

    def device_to_scene_matrix(self):
        """
        Returns the device-to-scene matrix.
        """
        return self.device_to_scene.matrix

    def scene_to_device_matrix(self):
        """
        Returns the scene-to-device matrix.
        """
        self.scene_to_device = ViewMap(self.scene, self.device.view)
        return self.scene_to_device.matrix

    def native_mm(self):
        return self.laser_view.mm

    def length(
        self,
        value,
        axis=None,
        new_units=None,
        relative_length=None,
        as_float=False,
        unitless=1,
        digits=None,
        scale=None,
    ):
        """
        Axis 0 is X
        Axis 1 is Y

        Axis -1 is 1D in x, y space. e.g. a line width.

        Convert a length of distance {value} to new native values.

        @param value:
        @param axis:
        @param new_units:
        @param relative_length:
        @param as_float:
        @param unitless: factor for units with no units sets.
        @param scale: scale length by given factor.
        @return:
        """
        if axis == 0:
            if relative_length is None:
                relative_length = self.width
        else:
            if relative_length is None:
                relative_length = self.height
        length = Length(
            value, relative_length=relative_length, unitless=unitless, digits=digits
        )
        if scale is not None:
            length *= scale

        if new_units == "mm":
            if as_float:
                return length.mm
            else:
                return length.length_mm
        elif new_units == "inch":
            if as_float:
                return length.inches
            else:
                return length.length_inches
        elif new_units == "cm":
            if as_float:
                return length.cm
            else:
                return length.length_cm
        elif new_units == "px":
            if as_float:
                return length.pixels
            else:
                return length.length_pixels
        elif new_units == "mil":
            if as_float:
                return length.mil
            else:
                return length.length_mil
        else:
            return length.units

    def contains(self, x, y):
        return self.laser_view.contains(x, y)

    def bbox(self):
        return self.scene_view.bbox()

    def dpi_to_steps(self, dpi, matrix=None):
        """
        Converts a DPI to a given step amount within the device length values. So M2 Nano will have 1 step per mil,
        the DPI of 500 therefore is step_x 2, step_y 2. A Galvo laser with a 200mm lens will have steps equal to
        200mm/65536 ~= 0.12 mils. So a DPI of 500 needs a step size of ~16.65 for x and y. Since 500 DPI is one dot
        per 2 mils.

        Note, steps size can be negative if our driver is x or y flipped.

        @param dpi:
        @param matrix: matrix to use rather than the scene to device matrix if supplied.
        @return:
        """
        # We require vectors so any positional offsets are non-contributing.
        unit_x = UNITS_PER_INCH
        unit_y = UNITS_PER_INCH
        if matrix is None:
            matrix = self.scene_to_device_matrix()
        oneinch_x = abs(complex(*matrix.transform_vector([unit_x, 0])))
        oneinch_y = abs(complex(*matrix.transform_vector([0, unit_y])))
        step_x = float(oneinch_x / dpi)
        step_y = float(oneinch_y / dpi)
        return step_x, step_y

    @property
    def length_width(self):
        return Length(self.width)

    @property
    def length_height(self):
        return Length(self.height)

    @property
    def unit_width(self):
        return float(Length(self.width))

    @property
    def unit_height(self):
        return float(Length(self.height))

    @staticmethod
    def conversion(units, amount=1):
        return Length(f"{amount}{units}").preferred


    def physical_to_device_length(self, x, y, unitless=1):
        """
        Converts a physical X,Y vector into device vector (dx, dy).

        This natively assumes device coordinate systems are affine. If we convert (0, 1in) as a vector into
        machine units we are converting the length of 1in into the equal length in machine units. Positionally this
        could be flipped or moved anywhere in the machine. But, the distance should be the same. However, in some cases
        due to belt stretching etc. we can have scaled x vs y coord systems so (1in, 0) could be a different length
        than (0, 1in).

        @param x:
        @param y:
        @param unitless:
        @return:
        """
        px, py = self.scene_view.physical(x, y)
        return self.scene_to_device_position(px, py, vector=True)


    def device_to_show_position(self, x, y, vector=False):
        """
        @param x:
        @param y:
        @param vector:
        @return:
        """
        if vector:
            point = self.device_to_show.matrix.transform_vector((x, y))
            return point.x, point.y
        else:
            point = self.device_to_show.matrix.point_in_matrix_space((x, y))
            return point.x, point.y


    def scene_to_show_position(self, x, y, vector=False):
        """
        @param x:
        @param y:
        @param vector:
        @return:
        """
        if vector:
            point = self.scene_to_show.matrix.transform_vector([x, y])
            return point[0], point[1]
        else:
            point = self.scene_to_show.matrix.point_in_matrix_space((x, y))
            return point.x, point.y

    def show_to_device_position(self, x, y, vector=False):
        """
        @param x:
        @param y:
        @param vector:
        @return:
        """
        if vector:
            point = self.show_to_device.matrix.transform_vector((x, y))
            return point.x, point.y
        else:
            point = self.show_to_device.matrix.point_in_matrix_space((x, y))
            return point.x, point.y

    def show_to_scene_position(self, x, y, vector=False):
        """
        @param x:
        @param y:
        @param vector:
        @return:
        """
        if vector:
            point = self.show_to_scene.matrix.transform_vector((x, y))
            return point.x, point.y
        else:
            point = self.show_to_scene.matrix.point_in_matrix_space((x, y))
            return point.x, point.y
