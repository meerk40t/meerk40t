import math
from copy import copy
from math import sqrt

from meerk40t.core.node.node import Node
from meerk40t.core.units import Angle, Length
from meerk40t.svgelements import Color, Matrix
from meerk40t.tools.geomstr import Geomstr  # ,  Scanbeam


class PMatrix:
    def __init__(self):
        self.a = 1
        self.b = 0
        self.c = 0
        self.d = 0
        self.e = 1
        self.f = 0
        self.g = 0
        self.h = 0
        self.i = 1


class WarpEffectNode(Node):
    """
    Effect node performing a warp. Effects are themselves a sort of geometry node that contains other geometry and
    the required data to produce additional geometry.
    """

    def __init__(self, *args, id=None, label=None, lock=False, **kwargs):
        self.fill = None
        self.stroke = Color("Blue")
        self.stroke_width = 1000.0
        self.stroke_scale = False
        self._stroke_zero = None
        self.output = True

        Node.__init__(
            self, type="effect warp", id=id, label=label, lock=lock, **kwargs
        )
        self._formatter = "{element_type} - {type} {radius} ({children})"

        if label is None:
            self.label = "Warp"
        else:
            self.label = label

        self.recalculate()
        self.perspective_matrix = PMatrix()
        self.p1 = complex(0,0)
        self.p2 = complex(0,1)
        self.p3 = complex(1,1)
        self.p4 = complex(0,1)

    @property
    def implied_stroke_width(self):
        return self.stroke_width

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self._parent)})"

    def __copy__(self):
        nd = self.node_dict
        nd["stroke"] = copy(self.stroke)
        nd["fill"] = copy(self.fill)
        return WarpEffectNode(**nd)

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

    def recalculate(self):
        """
        Ensure that the properties for distance, angle and angle_delta are in usable units.
        @return:
        """
        pass

    def preprocess(self, context, matrix, plan):
        pass

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Warp"
        default_map["enabled"] = "(Disabled) " if not self.output else ""

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
            try:
                outlines.append(node.as_geometry(**kws))
            except AttributeError:
                # If direct children lack as_geometry(), do nothing.
                pass
        # outlines.perspective_warp(self.perspective_matrix)
        return outlines

    def modified(self):
        self.altered()

    def drop(self, drag_node, modify=True):
        # Default routine for drag + drop for an op node - irrelevant for others...
        if drag_node.type.startswith("effect"):
            if modify:
                if drag_node.parent is self.parent:
                    self.append_child(drag_node)
                else:
                    self.swap_node(drag_node)
                drag_node.altered()
                self.altered()
            return True
        if hasattr(drag_node, "as_geometry"):
            # Dragging element onto operation adds that element to the op.
            if not modify:
                if self.has_ancestor("branch ops"):
                    self.add_reference(drag_node)
                else:
                    self.append_child(drag_node)
                self.altered()
            return True
        elif drag_node.type == "reference":
            if modify:
                if self.has_ancestor("branch ops"):
                    self.append_child(drag_node)
                else:
                    self.append_child(drag_node.node)
            return True
        elif drag_node.type.startswith("op"):
            # If we drag an operation to this node,
            # then we will reverse the game
            return drag_node.drop(self, modify=modify)
        return False
