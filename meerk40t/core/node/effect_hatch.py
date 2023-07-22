from copy import copy
from math import sqrt

from meerk40t.core.node.mixins import Stroked
from meerk40t.core.node.node import Node
from meerk40t.core.units import Length, Angle
from meerk40t.svgelements import Matrix, Color
from meerk40t.tools.geomstr import Geomstr, Scanbeam


class HatchEffectNode(Node, Stroked):
    """
    Default object defining any operation done on the laser.

    This is a Node of type "hatch op".
    """

    def __init__(self, *args, id=None, label=None, lock=False, **kwargs):
        self.matrix = None
        self.fill = None
        self.stroke = Color("Blue")
        self.stroke_width = 1000.0
        self.stroke_scale = False
        self._stroke_zero = None
        self.output = True
        self.hatch_distance = None
        self.hatch_angle = None
        self.hatch_type = None
        Node.__init__(self, type="effect hatch", id=id, label=label, lock=lock, **kwargs)
        self._formatter = "{effect}{element_type} - {distance} {angle}"
        if self.matrix is None:
            self.matrix = Matrix()

        if self._stroke_zero is None:
            # This defines the stroke-width zero point scale
            self.stroke_width_zero()

        if label is None:
            self.label = "Hatch"
        else:
            self.label = label
        if self.hatch_type is None:
            self.hatch_type = "scanline"
        self.passes = 1
        if self.hatch_distance is None:
            self.hatch_distance = "1mm"
        if self.hatch_angle is None:
            self.hatch_angle = "0deg"
        self.settings = kwargs
        self._operands = list()
        self._distance = None
        self._angle = None
        self._effect = True
        self.recalculate()
        for c in kwargs.get("operands", []):
            self._operands.append(copy(c))

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self._parent)})"

    def __copy__(self):
        nd = self.node_dict
        nd["matrix"] = copy(self.matrix)
        nd["stroke"] = copy(self.stroke)
        nd["fill"] = copy(self.fill)
        nd["operands"] = copy(self._operands)
        return HatchEffectNode(**nd)

    def scaled(self, sx, sy, ox, oy):
        self.altered()

    @property
    def angle(self):
        return self.hatch_angle

    @angle.setter
    def angle(self, value):
        self.hatch_angle = value
        self.recalculate()

    @property
    def distance(self):
        return self.hatch_angle

    @distance.setter
    def distance(self, angle):
        self.hatch_distance = angle
        self.recalculate()

    def recalculate(self):
        h_dist = self.hatch_distance
        h_angle = self.hatch_angle
        distance_y = float(Length(h_dist))
        if isinstance(h_angle, float):
            self._angle = h_angle
        else:
            self._angle = Angle(h_angle).radians
        transformed_vector = self.matrix.transform_vector([0, distance_y])
        self._distance = abs(complex(transformed_vector[0], transformed_vector[1]))

    def preprocess(self, context, matrix, plan):
        self.stroke_scaled = False
        self.stroke_scaled = True
        factor = sqrt(abs(matrix.determinant))
        self._distance *= factor
        for c in self._operands:
            c.matrix *= matrix

        self.stroke_scaled = False
        self.set_dirty_bounds()

    def bbox(self, transformed=True, with_stroke=False):
        if not self.effect:
            return None
        geometry = self.as_geometry()
        if transformed:
            bounds = geometry.bbox(mx=self.matrix)
        else:
            bounds = geometry.bbox()
        xmin, ymin, xmax, ymax = bounds
        if with_stroke:
            delta = float(self.implied_stroke_width) / 2.0
            return (
                xmin - delta,
                ymin - delta,
                xmax + delta,
                ymax + delta,
            )
        return xmin, ymin, xmax, ymax

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Hatch"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["effect"] = "+" if self.effect else "-"
        default_map["pass"] = (
            f"{self.passes}X " if self.passes and self.passes != 1 else ""
        )
        default_map["angle"] = str(self.hatch_angle)
        default_map["distance"] = str(self.hatch_distance)
        return default_map

    @property
    def effect(self):
        return self._effect

    @effect.setter
    def effect(self, value):
        self._effect = value
        if self._effect:
            self._operands.extend(self._children)
            for c in self._children:
                c.set_dirty_bounds()
                c.matrix *= ~self.matrix
            self.remove_all_children(destroy=False)
            self.set_dirty_bounds()
            self.altered()
        else:
            for c in self._operands:
                c.matrix *= self.matrix
                self.set_dirty_bounds()
                self.add_node(c)
            self._operands.clear()
            self.set_dirty_bounds()
            self.altered()

    def as_geometry(self):
        outlines = Geomstr()
        if not self.effect:
            return outlines
        for node in self._operands:
            outlines.append(node.as_geometry())
        outlines.transform(self.matrix)
        path = Geomstr()
        if self._distance is None:
            self.recalculate()
        for p in range(self.passes):
            path.append(Geomstr.hatch(outlines, distance=self._distance, angle=self._angle))
        return path

    def modified(self):
        self.altered()

    def drop(self, drag_node, modify=True):
        # Default routine for drag + drop for an op node - irrelevant for others...
        if drag_node.type.startswith("elem"):
            # Dragging element onto operation adds that element to the op.
            if modify:
                if self._effect:
                    drag_node.matrix *= ~self.matrix
                    self._operands.append(drag_node)
                    drag_node.remove_node()
                else:
                    self.append_child(drag_node)
                self.altered()
            return True
        elif drag_node.type == "reference":
            if modify:
                self.append_child(drag_node.node)
            return True
        return False

    def copy_children(self, obj):
        for element in obj.children:
            self.add_reference(element)

    def copy_children_as_real(self, copy_node):
        for node in copy_node.children:
            self.add_node(copy(node.node))
