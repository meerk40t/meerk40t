from copy import copy

from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_INCH
from meerk40t.svgelements import Matrix


class ImageRasterNode(Node):
    """
    ImageRasterNode is a basic image type. Its information is backed by a raster.
    """

    def __init__(self, **kwargs):
        self.image = None
        self.matrix = None
        super().__init__(type="image raster", **kwargs)
        self._formatter = "{element_type} {id} {width}x{height} @{dpi}"
        if self.matrix is None:
            self.matrix = Matrix()
        self._can_rotate = False
        self._can_skew = False

    def __copy__(self):
        nd = self.node_dict
        nd["matrix"] = copy(self.matrix)
        nd["image"] = copy(self.image)
        return ImageRasterNode(**nd)

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self.image)}, {str(self._parent)})"

    def as_image(self):
        return self.image, self.bbox()

    def preprocess(self, context, matrix, plan):
        """
        Preprocess step during the cut planning stages.

        We require a context to calculate the correct step values relative to the device
        """
        self.matrix *= matrix
        self.set_dirty_bounds()

    def bbox(self, transformed=True, with_stroke=False):
        image_width, image_height = self.image.size
        matrix = self.matrix
        x0, y0 = matrix.point_in_matrix_space((0, 0))
        x1, y1 = matrix.point_in_matrix_space((image_width, image_height))
        x2, y2 = matrix.point_in_matrix_space((0, image_height))
        x3, y3 = matrix.point_in_matrix_space((image_width, 0))
        return (
            min(x0, x1, x2, x3),
            min(y0, y1, y2, y3),
            max(x0, x1, x2, x3),
            max(y0, y1, y2, y3),
        )

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map.update(self.__dict__)
        image = self.image

        pil_image, bounds = self.image, self.bounds

        try:
            default_map["width"] = image.width
            default_map["height"] = image.height
            default_map["offset_x"] = bounds[0]
            default_map["offset_y"] = bounds[1]
        except:
            default_map["width"] = 0
            default_map["height"] = 0
            default_map["offset_x"] = 0
            default_map["offset_y"] = 0
            default_map["step_x"] = 1
            default_map["step_y"] = 1
            default_map["dpi"] = 1
            return default_map

        # Get steps from individual images
        image_width, image_height = pil_image.size
        expected_width = bounds[2] - bounds[0]
        expected_height = bounds[3] - bounds[1]
        step_x = expected_width / image_width
        step_y = expected_height / image_height
        default_map["step_x"] = step_x
        default_map["step_y"] = step_y
        dpi_x = float(UNITS_PER_INCH / step_x)
        dpi_y = float(UNITS_PER_INCH / step_y)
        default_map["dpi"] = round((dpi_x + dpi_y) / 2)
        default_map["element_type"] = "Image"
        return default_map

    def can_drop(self, drag_node):
        if self.is_a_child_of(drag_node):
            return False
        # Dragging element into element.
        return bool(
            hasattr(drag_node, "as_geometry")
            or hasattr(drag_node, "as_image")
            or (drag_node.type.startswith("op ") and drag_node.type != "op dots")
            or drag_node.type in ("file", "group")
        )

    def drop(self, drag_node, modify=True, flag=False):
        # Dragging element into element.
        if not self.can_drop(drag_node):
            return False
        if (
            hasattr(drag_node, "as_geometry")
            or hasattr(drag_node, "as_image")
            or drag_node.type in ("file", "group")
        ):
            if modify:
                self.insert_sibling(drag_node)
            return True
        elif drag_node.type.startswith("op"):
            # If we drag an operation to this node,
            # then we will reverse the game
            return drag_node.drop(self, modify=modify, flag=flag)
        return False

    def notify_scaled(self, *args, **kwargs):
        super().notify_scaled(*args, **kwargs)
        self.notify_update()

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

    @property
    def opaque_image(self):
        from PIL import Image

        img = self.image
        if img is not None:
            if img.mode == "RGBA":
                r, g, b, a = img.split()
                background = Image.new("RGB", img.size, "white")
                background.paste(img, mask=a)
                img = background
        return img
