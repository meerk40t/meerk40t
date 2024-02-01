from copy import copy

from meerk40t.core.node.mixins import FunctionalParameter
from meerk40t.core.node.node import Node
from meerk40t.svgelements import Color
from meerk40t.tools.geomstr import Geomstr
from meerk40t.tools.pmatrix import PMatrix


class WarpEffectNode(Node, FunctionalParameter):
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
        self.p1 = complex(0, 0)
        self.p2 = complex(0, 0)
        self.p3 = complex(0, 0)
        self.p4 = complex(0, 0)
        self.d1 = complex(0, 0)
        self.d2 = complex(0, 0)
        self.d3 = complex(0, 0)
        self.d4 = complex(0, 0)

        Node.__init__(self, type="effect warp", id=id, label=label, lock=lock, **kwargs)
        self._formatter = "{element_type} - ({children})"

        if label is None:
            self.label = "Warp"
        else:
            self.label = label

        self.recalculate()
        self.perspective_matrix = PMatrix()
        self.set_bounds_parameters()

    def set_bounds_parameters(self):
        b = self.bounds
        if b is None:
            return
        nx, ny, mx, my = b
        self.p1 = complex(nx, ny)
        self.p2 = complex(mx, ny)
        self.p3 = complex(mx, my)
        self.p4 = complex(nx, my)

        n1 = self.p1 + self.d1
        n2 = self.p2 + self.d2
        n3 = self.p3 + self.d3
        n4 = self.p4 + self.d4

        self.functional_parameter = (
            "warp",
            0,
            n1.real,
            n1.imag,
            0,
            n2.real,
            n2.imag,
            0,
            n3.real,
            n3.imag,
            0,
            n4.real,
            n4.imag,
        )

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
        self.set_bounds_parameters()

    def notify_detached(self, node=None, **kwargs):
        Node.notify_detached(self, node=node, **kwargs)
        if node is self:
            return
        self.altered()
        self.set_bounds_parameters()

    def notify_modified(self, node=None, **kwargs):
        Node.notify_modified(self, node=node, **kwargs)
        if node is self:
            return
        self.altered()
        self.set_bounds_parameters()

    def notify_altered(self, node=None, **kwargs):
        Node.notify_altered(self, node=node, **kwargs)
        if node is self:
            return
        self.altered()
        self.set_bounds_parameters()

    def notify_scaled(self, node=None, sx=1, sy=1, ox=0, oy=0, **kwargs):
        Node.notify_scaled(self, node, sx, sy, ox, oy, **kwargs)
        if node is self:
            return
        self.altered()
        self.set_bounds_parameters()

    def notify_translated(self, node=None, dx=0, dy=0, **kwargs):
        Node.notify_translated(self, node, dx, dy, **kwargs)
        if node is self:
            return
        self.altered()
        self.set_bounds_parameters()

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

    def affected_children(self):
        def right_types(start_node):
            res = []
            for e in start_node._children:
                if e.type.startswith("effect"):
                    continue
                if e._children:
                    subs = right_types(e)
                    res.extend(subs)
                elif e.type.startswith("elem"):
                    res.append(e)
            return res

        nodes = right_types(self)
        return nodes

    def as_geometry(self, **kws):
        """
        Calculates the warp effect geometry.

        @param kws:
        @return:
        """
        outlines = Geomstr()
        for node in self.affected_children():
            try:
                outlines.append(node.as_geometry(**kws))
            except AttributeError:
                # If direct children lack as_geometry(), do nothing.
                pass
        self.set_bounds_parameters()

        self.perspective_matrix = PMatrix.map(
            self.p1,
            self.p2,
            self.p3,
            self.p4,
            self.p1 + self.d1,
            self.p2 + self.d2,
            self.p3 + self.d3,
            self.p4 + self.d4,
        )
        outlines.transform3x3(self.perspective_matrix)
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
        elif drag_node.type in ("file", "group"):
            # If we drag a group or a file to this node,
            # then we will do it only if this an element effect
            if modify:
                if self.has_ancestor("branch ops"):
                    return False
                else:
                    self.append_child(drag_node)
                self.altered()
            return True
        return False

    @property
    def functional_parameter(self):
        return self.mkparam

    @functional_parameter.setter
    def functional_parameter(self, value):
        def getit(data, idx, default):
            if idx < len(data):
                return data[idx]
            else:
                return default

        if not isinstance(value, (list, tuple)):
            return
        self.mkparam = value
        if self.mkparam:
            # method = self.mkparam[0]

            n1 = self.p1 + self.d1
            n2 = self.p2 + self.d2
            n3 = self.p3 + self.d3
            n4 = self.p4 + self.d4
            if n1.real != self.mkparam[2] or n1.imag != self.mkparam[3]:
                dn1 = complex(
                    getit(self.mkparam, 2, n1.real), getit(self.mkparam, 3, n1.imag)
                )
                self.d1 = dn1 - self.p1
            elif n2.real != self.mkparam[5] or n2.imag != self.mkparam[6]:
                dn2 = complex(
                    getit(self.mkparam, 5, n2.real), getit(self.mkparam, 6, n2.imag)
                )
                self.d2 = dn2 - self.p2
            elif n3.real != self.mkparam[8] or n3.imag != self.mkparam[9]:
                dn3 = complex(
                    getit(self.mkparam, 8, n3.real), getit(self.mkparam, 9, n3.imag)
                )
                self.d3 = dn3 - self.p3
            elif n4.real != self.mkparam[11] or n4.imag != self.mkparam[12]:
                dn4 = complex(
                    getit(self.mkparam, 11, n4.real), getit(self.mkparam, 12, n4.imag)
                )
                self.d4 = dn4 - self.p4
            self.altered()
