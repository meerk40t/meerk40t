import numpy as np
from copy import copy

from meerk40t.core.node.mixins import FunctionalParameter
from meerk40t.core.node.node import Node
from meerk40t.svgelements import Color
from meerk40t.tools.geomstr import Geomstr


class PMatrix:
    def __init__(self, a=1.0, b=0.0, c=0.0, d=0.0, e=1.0, f=0, g=0.0, h=0.0, i=1.0):
        if isinstance(a, PMatrix):
            self.mx = copy(a.mx)
            return
        if isinstance(a, np.ndarray):
            self.mx = a
            return
        self.mx = np.array([[a, b, c], [d, e, f], [g, h, i]])

    def __invert__(self):
        self.mx = np.linalg.inv(self.mx)
        return self

    @classmethod
    def map(cls, p1, p2, p3, p4, r1, r2, r3, r4):
        p = PMatrix.perspective(p1, p2, p3, p4)
        r = PMatrix.perspective(r1, r2, r3, r4)
        mx = np.dot(p.mx, np.linalg.inv(r.mx))
        return cls(mx)

    @classmethod
    def perspective(cls, p1, p2, p3, p4):
        """
        Create a matrix which transforms these four ordered points to the clockwise points of the unit-square.

        If G and H are very close to 0, this is an affine transformation. If they are not, then the perspective
        transform requires g and h,

        @param p1:
        @param p2:
        @param p3:
        @param p4:
        @return:
        """
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4

        i = 1
        try:
            j = (y1 - y2 + y3 - y4) / (y2 - y3)
            k = (x1 - x2 + x3 - x4) / (x4 - x3)
            m = (y4 - y3) / (y2 - y3)
            n = (x2 - x3) / (x4 - x3)

            h = i * (j - k * m) / (1 - m * n)
            g = i * (k - j * n) / (1 - m * n)
        except ZeroDivisionError:
            h = 0.0
            g = 0.0

        c = x1 * i
        f = y1 * i
        a = x4 * (g + i) - x1 * i
        b = x2 * (h + i) - x1 * i
        d = y4 * (g + i) - y1 * i
        e = y2 * (h + i) - y1 * i

        m = cls()
        m.mx[0, 0] = a
        m.mx[0, 1] = d
        m.mx[0, 2] = g

        m.mx[1, 0] = b
        m.mx[1, 1] = e
        m.mx[1, 2] = h

        m.mx[2, 0] = c
        m.mx[2, 1] = f
        m.mx[2, 2] = i
        return m


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
        self.x1 = 0
        self.y1 = 0
        self.x2 = 0
        self.y2 = 0
        self.x3 = 0
        self.y3 = 0
        self.x4 = 0
        self.y4 = 0

        Node.__init__(self, type="effect warp", id=id, label=label, lock=lock, **kwargs)
        self._formatter = "{element_type} - {type} {radius} ({children})"

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
        self.x1 = nx
        self.y1 = ny
        self.x2 = mx
        self.y2 = ny
        self.x3 = mx
        self.y3 = my
        self.x4 = nx
        self.y4 = my

        self.functional_parameter = (
            "warp",
            0,
            self.x1,
            self.y1,
            0,
            self.x2,
            self.y2,
            0,
            self.x3,
            self.y3,
            0,
            self.x4,
            self.y4,
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
        self.perspective_matrix = PMatrix.perspective((0.1,0.2), (0.01,1.1), (2.3,1.04), (1.3,0.02))
        outlines.transform3x3(self.perspective_matrix.mx)
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

        if isinstance(value, (list, tuple)):
            self.mkparam = value
            if self.mkparam:
                method = self.mkparam[0]

                if self.x1 != self.mkparam[2] or self.y1 != self.mkparam[3]:
                    # P1 changed.
                    self.x1 = getit(self.mkparam, 2, self.x1)
                    self.y1 = getit(self.mkparam, 3, self.y1)
                elif self.x2 != self.mkparam[5] or self.y2 != self.mkparam[6]:
                    # P2 changed
                    self.x2 = getit(self.mkparam, 5, self.x2)
                    self.y2 = getit(self.mkparam, 6, self.y2)
                elif self.x3 != self.mkparam[8] or self.y3 != self.mkparam[9]:
                    # P3 changed
                    self.x3 = getit(self.mkparam, 8, self.x2)
                    self.y3 = getit(self.mkparam, 9, self.y2)
                elif self.x4 != self.mkparam[11] or self.y4 != self.mkparam[12]:
                    # P3 changed
                    self.x4 = getit(self.mkparam, 11, self.x2)
                    self.y4 = getit(self.mkparam, 12, self.y2)
                self.altered()
