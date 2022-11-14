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
        *args,
        path=None,
        matrix=None,
        fill=None,
        stroke=None,
        stroke_width=None,
        linecap=Linecap.CAP_BUTT,
        linejoin=Linejoin.JOIN_MITER,
        fillrule=Fillrule.FILLRULE_EVENODD,
        id=None,
        label=None,
        lock=False,
        settings=None,
        **kwargs,
    ):
        if settings is None:
            settings = dict()
        settings.update(kwargs)
        if "type" in settings:
            del settings["type"]
        super().__init__(
            type="numpath", id=id, label=label, lock=lock, *args, **settings
        )
        self._formatter = "{element_type} {id} {stroke}"
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
            id=self.id,
            label=self.label,
            lock=self.lock,
            settings=self.settings,
        )

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(len(self.path))}, {str(self._parent)})"

    def bbox(self, transformed=True, with_stroke=False):
        return self.path.bbox(self.matrix)

    def preprocess(self, context, matrix, plan):
        self.path.transform(self.matrix)
        self.path.transform(matrix)
        self.set_dirty_bounds()

    def default_map(self, default_map=None):
        default_map = super(NumpathNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Numpath"
        default_map.update(self.settings)
        default_map["stroke"] = self.stroke
        default_map["fill"] = self.fill
        default_map["stroke-width"] = self.stroke_width
        default_map["matrix"] = self.matrix
        return default_map

    def drop(self, drag_node, modify=True):
        # Dragging element into element.
        if drag_node.type.startswith("elem"):
            if modify:
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
