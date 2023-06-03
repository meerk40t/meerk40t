from copy import copy

import numpy as np

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

    def __init__(self, *args, id=None, label=None, lock=False,  **kwargs):
        self.matrix = None
        self.fill = None
        self.stroke = Color("Blue")
        self.stroke_width = 1000.0
        self.stroke_scale = False
        self._stroke_zero = None
        self.output = True
        Node.__init__(self, type="effect hatch", id=id, label=label, lock=lock)
        self._formatter = (
            "{effect}{element_type} - {distance} {angle}"
        )
        if self.matrix is None:
            self.matrix = Matrix()

        if self._stroke_zero is None:
            # This defines the stroke-width zero point scale
            self.stroke_width_zero()

        if label is None:
            self.label = "Hatch"
        else:
            self.label = label
        self.hatch_type = "scanline"
        self.passes = 1
        self.hatch_distance = "1mm"
        self.hatch_angle = "0deg"
        self.settings = kwargs
        self._operands = list()
        self._effect = True
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

    def preprocess(self, context, matrix, plan):
        self.stroke_scaled = False
        self.stroke_scaled = True
        for oper in self._operands:
            oper.matrix *= matrix
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
            if node.type == "reference":
                node = node.node
            outlines.append(node.as_geometry())
        path = Geomstr()
        for p in range(self.passes):
            path.append(self.scanline_fill(outlines=outlines))
        path.transform(self.matrix)
        return path

    def scanline_fill(self, outlines):
        """
        Applies optimized scanline fill
        @return:
        """
        h_dist = self.hatch_distance
        h_angle = self.hatch_angle
        distance_y = float(Length(h_dist))
        if isinstance(h_angle, float):
            angle = h_angle
        else:
            angle = Angle(h_angle).radians
        transformed_vector = self.matrix.transform_vector([0, distance_y])
        distance = abs(complex(transformed_vector[0], transformed_vector[1]))

        path = outlines
        path.rotate(angle)
        vm = Scanbeam(path)
        y_min, y_max = vm.event_range()
        vm.valid_low = y_min - distance
        vm.valid_high = y_max + distance
        vm.scanline_to(vm.valid_low)

        forward = True
        geometry = Geomstr()
        if np.isinf(y_max):
            return geometry
        while vm.current_is_valid_range():
            vm.scanline_to(vm.scanline + distance)
            y = vm.scanline
            actives = vm.actives()
            r = range(1, len(actives), 2) if forward else range(len(actives) - 1, 0, -2)
            for i in r:
                left_segment = actives[i - 1]
                right_segment = actives[i]
                left_segment_x = vm.x_intercept(left_segment)
                right_segment_x = vm.x_intercept(right_segment)
                if forward:
                    geometry.line(complex(left_segment_x, y), complex(right_segment_x, y))
                else:
                    geometry.line(complex(right_segment_x, y), complex(left_segment_x, y))
                geometry.end()
            forward = not forward
        geometry.rotate(-angle)
        return geometry

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
                self.append_child(drag_node)
            return True
        return False

    def copy_children(self, obj):
        for element in obj.children:
            self.add_reference(element)

    def copy_children_as_real(self, copy_node):
        for node in copy_node.children:
            self.add_node(copy(node.node))
