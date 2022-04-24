from meerk40t.core.node.node import Node
from copy import copy


class ImageNode(Node):
    """
    ImageNode is the bootstrapped node type for the 'elem image' type.
    """

    def __init__(self, data_object, **kwargs):
        super(ImageNode, self).__init__(data_object)
        self.image = data_object.image
        self.matrix = data_object.transform
        self.dpi = 500
        self.step_x = None
        self.step_y = None
        data_object.node = self

    def __repr__(self):
        return "ImageNode('%s', %s, %s)" % (
            self.type,
            str(self.object),
            str(self._parent),
        )

    def __copy__(self):
        return ImageNode(copy(self.object))

    def default_map(self, default_map=None):
        default_map = super(ImageNode, self).default_map(default_map=default_map)
        if self.object is not None:
            default_map.update(self.object.values)
        if "stroke" not in default_map:
            default_map["stroke"] = "None"
        if "fill" not in default_map:
            default_map["fill"] = "None"
        if "stroke-width" not in default_map:
            default_map["stroke-width"] = "None"
        if "dpi" not in default_map:
            default_map["dpi"] = self.dpi
        return default_map

    def drop(self, drag_node):
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
        obj = self.object
        if hasattr(obj, "point"):
            if len(self._points) <= 11:
                self._points.extend([None] * (11 - len(self._points)))
            start = obj.point(0)
            end = obj.point(1)
            self._points[9] = [start[0], start[1], "endpoint"]
            self._points[10] = [end[0], end[1], "endpoint"]

    def update_point(self, index, point):
        return False

    def add_point(self, point, index=None):
        return False
