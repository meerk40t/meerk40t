from copy import copy

from meerk40t.core.node.mixins import Stroked
from meerk40t.core.node.node import Node
from meerk40t.fill.fills import scanline_fill
from meerk40t.svgelements import Matrix, Color
from meerk40t.tools.geomstr import Geomstr


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
            "{enabled}{element_type} - {distance} {angle}"
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
        self.hatch_algorithm = scanline_fill
        self.settings = kwargs
        self._operands = list()
        self._effect = True

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self._parent)})"

    def __copy__(self):
        nd = self.node_dict
        nd["matrix"] = copy(self.matrix)
        nd["stroke"] = copy(self.stroke)
        nd["fill"] = copy(self.fill)
        return HatchEffectNode(*nd)

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
            self.remove_all_children(destroy=False)
            self.altered()
        else:
            for c in self._operands:
                self.add_node(c)
            self._operands.clear()
            self.altered()

    def as_geometry(self):
        path = Geomstr()
        if not self.effect:
            return path
        outlines = list()
        for node in self._operands:
            if node.type == "reference":
                node = node.node
            path.append(node.as_geometry())
            outlines.extend(path.as_interpolated_points(interpolate=100))
            outlines.append(None)
        if outlines:
            for p in range(self.passes):
                hatches = list(
                    self.hatch_algorithm(
                        settings=self.settings, outlines=outlines, matrix=self.matrix
                    )
                )
                path.append(path.lines(*hatches))
        path.transform(self.matrix)
        return path

    def drop(self, drag_node, modify=True):
        # Default routine for drag + drop for an op node - irrelevant for others...
        if drag_node.type.startswith("elem"):
            # Dragging element onto operation adds that element to the op.
            if modify:
                if self._effect:
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
