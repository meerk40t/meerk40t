from copy import copy

from meerk40t.core.node.node import Fillrule, Linecap, Linejoin, Node
from meerk40t.core.parameters import Parameters
from meerk40t.svgelements import Matrix


class NumpathNode(Node, Parameters):
    """
    NumpathNode is the bootstrapped node type for the 'elem numpath' type.
    """

    def __init__(
        self,
        path=None,
        matrix=None,
        fill=None,
        stroke=None,
        stroke_width=None,
        linecap=Linecap.CAP_BUTT,
        linejoin=Linejoin.JOIN_MITER,
        fillrule=Fillrule.FILLRULE_NONZERO,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.settings.update(kwargs)
        self.path = path
        if matrix is None:
            matrix = Matrix()
        self.matrix = matrix
        self.fill = fill
        self.stroke = stroke
        self.stroke_width = stroke_width
        self.linecap = linecap
        self.linejoin = linejoin
        self.fillrule = fillrule
        self.lock = False

    def __copy__(self):
        return NumpathNode(
            path=copy(self.path),
            matrix=copy(self.matrix),
            fill=copy(self.fill),
            stroke=copy(self.stroke),
            stroke_width=self.stroke_width,
            linecap=self.linecap,
            linejoin=self.linejoin,
            fillrule=self.fillrule,
            **self.settings,
        )

    def __repr__(self):
        return "%s('%s', %s, %s)" % (
            self.__class__.__name__,
            self.type,
            str(len(self.path)),
            str(self._parent),
        )

    @property
    def bounds(self):
        if self._bounds_dirty:
            self._bounds = self.path.bbox(self.matrix)
            self._bounds_dirty = False
        return self._bounds

    def preprocess(self, context, matrix, commands):
        self.path.transform(self.matrix)
        self.path.transform(matrix)
        self._bounds_dirty = True

    def default_map(self, default_map=None):
        default_map = super(NumpathNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Numpath"
        default_map.update(self.settings)
        default_map["stroke"] = self.stroke
        default_map["fill"] = self.fill
        default_map["stroke-width"] = self.stroke_width
        default_map["matrix"] = self.matrix
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

    def as_path(self):
        return None
