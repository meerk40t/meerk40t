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
        self.stroke = Color("Blue")
        self.fill = None
        self.stroke_width = 1000.0
        self.stroke_scale = False
        self._stroke_zero = None
        Node.__init__(self, type="effect hatch", id=id, label=label, lock=lock)
        if self.matrix is None:
            self.matrix = Matrix()

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

    def __repr__(self):
        return "HatchEffectNode()"

    def __copy__(self):
        return HatchEffectNode(self)

    def as_geometry(self):
        path = Geomstr()
        outlines = list()
        for node in self.children:
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
        return path

    def drop(self, drag_node, modify=True):
        # Default routine for drag + drop for an op node - irrelevant for others...
        if drag_node.type.startswith("elem"):
            # Dragging element onto operation adds that element to the op.
            if modify:
                self.add_reference(drag_node, pos=0)
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
