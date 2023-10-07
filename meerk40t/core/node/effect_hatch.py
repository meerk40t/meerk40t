from copy import copy
from math import sqrt

from meerk40t.core.node.node import Node
from meerk40t.core.units import Angle, Length
from meerk40t.svgelements import Color, Matrix
from meerk40t.tools.geomstr import Geomstr  # ,  Scanbeam


class HatchEffectNode(Node):
    """
    Effect node performing a hatch. Effects are themselves a sort of geometry node that contains other geometry and
    the required data to produce additional geometry.
    """

    def __init__(self, *args, id=None, label=None, lock=False, **kwargs):
        self.fill = None
        self.stroke = Color("Blue")
        self.stroke_width = 1000.0
        self.stroke_scale = False
        self._stroke_zero = None
        self.output = True
        self.hatch_distance = None
        self.hatch_angle = None
        self.hatch_angle_delta = None
        self.hatch_type = None
        self.loops = None
        Node.__init__(
            self, type="effect hatch", id=id, label=label, lock=lock, **kwargs
        )
        self._formatter = "{element_type} - {distance} {angle} ({children})"

        if label is None:
            self.label = "Hatch"
        else:
            self.label = label

        if self.hatch_type is None:
            self.hatch_type = "scanline"
        if self.loops is None:
            self.loops = 1
        if self.hatch_distance is None:
            self.hatch_distance = "1mm"
        if self.hatch_angle is None:
            self.hatch_angle = "0deg"
        if self.hatch_angle_delta is None:
            self.hatch_angle_delta = "0deg"
        self._distance = None
        self._angle = None
        self._angle_delta = 0
        self._effect = True
        self.recalculate()

    @property
    def implied_stroke_width(self):
        return self.stroke_width

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self._parent)})"

    def __copy__(self):
        nd = self.node_dict
        nd["stroke"] = copy(self.stroke)
        nd["fill"] = copy(self.fill)
        return HatchEffectNode(**nd)

    def scaled(self, sx, sy, ox, oy):
        self.altered()

    def notify_attached(self, node=None, **kwargs):
        Node.notify_attached(self, node=node, **kwargs)
        if node is self:
            return
        self.altered()

    def notify_detached(self, node=None, **kwargs):
        Node.notify_detached(self, node=node, **kwargs)
        if node is self:
            return
        self.altered()

    def notify_modified(self, node=None, **kwargs):
        Node.notify_modified(self, node=node, **kwargs)
        if node is self:
            return
        self.altered()

    def notify_altered(self, node=None, **kwargs):
        Node.notify_altered(self, node=node, **kwargs)
        if node is self:
            return
        self.altered()

    def notify_scaled(self, node=None, sx=1, sy=1, ox=0, oy=0, **kwargs):
        Node.notify_scaled(self, node, sx, sy, ox, oy, **kwargs)
        if node is self:
            return
        self.altered()

    def notify_translated(self, node=None, dx=0, dy=0, **kwargs):
        Node.notify_translated(self, node, dx, dy, **kwargs)
        if node is self:
            return
        self.altered()

    @property
    def angle(self):
        return self.hatch_angle

    @angle.setter
    def angle(self, value):
        self.hatch_angle = value
        self.recalculate()

    @property
    def delta(self):
        return self.hatch_angle_delta

    @delta.setter
    def delta(self, value):
        self.hatch_angle_delta = value
        self.recalculate()

    @property
    def distance(self):
        return self.hatch_distance

    @distance.setter
    def distance(self, value):
        self.hatch_distance = value
        self.recalculate()

    def recalculate(self):
        """
        Ensure that the properties for distance, angle and angle_delta are in usable units.
        @return:
        """
        h_dist = self.hatch_distance
        h_angle = self.hatch_angle
        h_angle_delta = self.hatch_angle_delta
        distance_y = float(Length(h_dist))

        if isinstance(h_angle, float):
            self._angle = h_angle
        else:
            self._angle = Angle(h_angle).radians

        if isinstance(h_angle_delta, float):
            self._angle_delta = h_angle_delta
        else:
            self._angle_delta = Angle(h_angle_delta).radians

        # transformed_vector = self.matrix.transform_vector([0, distance_y])
        transformed_vector = [0, distance_y]
        self._distance = abs(complex(transformed_vector[0], transformed_vector[1]))

    def preprocess(self, context, matrix, plan):
        factor = sqrt(abs(matrix.determinant))
        self._distance *= factor
        # for c in self._children:
        #     c.matrix *= matrix

        self.set_dirty_bounds()

    # def bbox(self, transformed=True, with_stroke=False):
    #     geometry = self.as_geometry()
    #     if transformed:
    #         bounds = geometry.bbox(mx=self.matrix)
    #     else:
    #         bounds = geometry.bbox()
    #     xmin, ymin, xmax, ymax = bounds
    #     if with_stroke:
    #         delta = float(self.implied_stroke_width) / 2.0
    #         return (
    #             xmin - delta,
    #             ymin - delta,
    #             xmax + delta,
    #             ymax + delta,
    #         )
    #     return xmin, ymin, xmax, ymax

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Hatch"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["loop"] = (
            f"{self.loops}X " if self.loops and self.loops != 1 else ""
        )
        default_map["angle"] = str(self.hatch_angle)
        default_map["distance"] = str(self.hatch_distance)

        default_map["children"] = str(len(self.children))
        return default_map

    def as_geometry(self, **kws):
        """
        Calculates the hatch effect geometry. The pass index is the number of copies of this geometry whereas the
        internal loops value is rotated each pass by the angle-delta.

        @param kws:
        @return:
        """
        outlines = Geomstr()
        for node in self._children:
            outlines.append(node.as_geometry(**kws))
        # outlines.transform(self.matrix)
        path = Geomstr()
        if self._distance is None:
            self.recalculate()
        for p in range(self.loops):
            path.append(
                Geomstr.hatch(
                    outlines,
                    distance=self._distance,
                    angle=self._angle + p * self._angle_delta,
                )
            )
        return path

    def modified(self):
        self.altered()

    def drop(self, drag_node, modify=True):
        # Default routine for drag + drop for an op node - irrelevant for others...
        if drag_node.type.startswith("elem"):
            # Dragging element onto operation adds that element to the op.
            if not modify:
                if self.parent.type.startswith("op") or self.parent.type.startswith("effect"):
                    self.add_reference(drag_node)
                else:
                    self.append_child(drag_node)
                self.altered()
            return True
        elif drag_node.type == "reference":
            if modify:
                self.append_child(drag_node.node)
            return True
        elif drag_node.type.startswith("op"):
            # If we drag an operation to this node,
            # then we will reverse the game
            return drag_node.drop(self, modify=modify)
        return False
