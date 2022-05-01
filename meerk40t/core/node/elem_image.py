from copy import copy

from meerk40t.core.node.node import Node


class ImageNode(Node):
    """
    ImageNode is the bootstrapped node type for the 'elem image' type.
    """

    def __init__(
        self,
        image=None,
        matrix=None,
        overscan=None,
        direction=None,
        dpi=500,
        step_x=None,
        step_y=None,
        **kwargs,
    ):
        super(ImageNode, self).__init__(type="elem image", **kwargs)
        self.image = image
        self.matrix = matrix
        self.settings = kwargs
        self.overscan = overscan
        self.direction = direction
        self.dpi = dpi
        self.step_x = step_x
        self.step_y = step_y
        self.lock = False

    def __copy__(self):
        return ImageNode(
            image=self.image,
            matrix=copy(self.matrix),
            overscan=self.overscan,
            direction=self.direction,
            dpi=self.dpi,
            step_x=self.step_x,
            step_y=self.step_y,
            **self.settings,
        )

    def __repr__(self):
        return "%s('%s', %s, %s)" % (
            self.__class__.__name__,
            self.type,
            str(self.image),
            str(self._parent),
        )

    def preprocess(self, context, matrix, commands):
        self.matrix *= matrix
        self._bounds_dirty = True

    @property
    def bounds(self):
        if self._bounds_dirty:
            image_width, image_height = self.image.size
            x0, y0 = self.matrix.point_in_matrix_space((0, 0))
            x1, y1 = self.matrix.point_in_matrix_space((image_width, image_height))
            x2, y2 = self.matrix.point_in_matrix_space((0, image_height))
            x3, y3 = self.matrix.point_in_matrix_space((image_width, 0))
            self._bounds_dirty = False
            self._bounds = (
                min(x0, x1, x2, x3),
                min(y0, y1, y2, y3),
                max(x0, x1, x2, x3),
                max(y0, y1, y2, y3),
            )
        return self._bounds

    def default_map(self, default_map=None):
        default_map = super(ImageNode, self).default_map(default_map=default_map)
        default_map.update(self.settings)
        default_map["matrix"] = self.matrix
        default_map["dpi"] = self.dpi
        default_map["overscan"] = self.overscan
        default_map["direction"] = self.direction
        return default_map

    def drop(self, drag_node):
        # Dragging element into element.
        if drag_node.type.startswith("elem"):
            self.insert_sibling(drag_node)
            return True
        return False

    def revalidate_points(self):
        bounds = self.bounds
        if bounds is None:
            return
        if len(self._points) < 9:
            self._points.extend([None] * (9 - len(self._points)))
        self._points[0] = [bounds[0], bounds[1], "bounds top_left"]
        self._points[1] = [bounds[2], bounds[1], "bounds top_right"]
        self._points[2] = [bounds[0], bounds[3], "bounds bottom_left"]
        self._points[3] = [bounds[2], bounds[3], "bounds bottom_right"]
        cx = (bounds[0] + bounds[2]) / 2
        cy = (bounds[1] + bounds[3]) / 2
        self._points[4] = [cx, cy, "bounds center_center"]
        self._points[5] = [cx, bounds[1], "bounds top_center"]
        self._points[6] = [cx, bounds[3], "bounds bottom_center"]
        self._points[7] = [bounds[0], cy, "bounds center_left"]
        self._points[8] = [bounds[2], cy, "bounds center_right"]

    def update_point(self, index, point):
        return False

    def add_point(self, point, index=None):
        return False

    def needs_actualization(self):
        """
        Return whether this image node has native sized pixels.

        @param step_x:
        @param step_y:
        @return:
        """
        m = self.matrix
        # Transformation must be uniform to permit native rastering.
        return m.a != self.step_x or m.b != 0.0 or m.c != 0.0 or m.d != self.step_y

    def make_actual(self):
        """
        Makes PIL image actual in that it manipulates the pixels to actually exist
        rather than simply apply the transform on the image to give the resulting image.
        Since our goal is to raster the images real pixels this is required.

        SVG matrices are defined as follows.
        [a c e]
        [b d f]

        Pil requires a, c, e, b, d, f accordingly.
        """
        from meerk40t.image.actualize import actualize

        self.image, self.matrix = actualize(
            self.image, self.matrix, step_x=self.step_x, step_y=self.step_y
        )
        self.altered()
