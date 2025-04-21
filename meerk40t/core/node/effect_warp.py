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
        self.autohide = True
        self.p1 = complex(0, 0)
        self.p2 = complex(0, 0)
        self.p3 = complex(0, 0)
        self.p4 = complex(0, 0)
        self.d1 = complex(0, 0)
        self.d2 = complex(0, 0)
        self.d3 = complex(0, 0)
        self.d4 = complex(0, 0)
        self._interim = False

        Node.__init__(self, type="effect warp", id=id, label=label, lock=lock, **kwargs)
        self._formatter = "{element_type} {id} - ({children})"

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

    def scaled(self, sx, sy, ox, oy, interim=False):
        self.altered()

    def notify_attached(self, node=None, **kwargs):
        Node.notify_attached(self, node=node, **kwargs)
        if node is self:
            return
        if self.autohide and hasattr(node, "hidden"):
            node.hidden = True
        self.altered()
        self.set_bounds_parameters()

    def notify_detached(self, node=None, **kwargs):
        Node.notify_detached(self, node=node, **kwargs)
        if node is self:
            return
        if self.autohide and hasattr(node, "hidden"):
            node.hidden = False
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

    def notify_scaled(self, node=None, sx=1, sy=1, ox=0, oy=0, interim=False, **kwargs):
        Node.notify_scaled(self, node, sx, sy, ox, oy, interim=interim, **kwargs)
        if node is self:
            return
        if interim:
            self.set_interim()
        else:
            self.altered()
            self.set_bounds_parameters()

    def append_child(self, new_child):
        if self.autohide and hasattr(new_child, "hidden"):
            new_child.hidden = True
        return super().append_child(new_child)

    def notify_translated(self, node=None, dx=0, dy=0, interim=False, **kwargs):
        Node.notify_translated(self, node, dx, dy, interim=interim, **kwargs)
        if node is self:
            return
        if interim:
            self.set_interim()
        else:
            self.altered()
            self.set_bounds_parameters()

    def recalculate(self):
        """
        Ensure that the properties for distance, angle and angle_delta are in usable units.
        @return:
        """
        pass

    def preprocess(self, context, matrix, plan):
        """
        We need to adjust the internal warp parameters according to the matrix

        p1 to p4 define the original rectangle - they will be recalculated in as_geometry, so no need to do it here
        n1 to n4 define the skewed rectangle - again recalculated by applying d1 to d4 to p1 to p4
        The problem is that the attribution of d1 to p1 and d2 to p2 etc. could be swapped
        as the bbox might turn the sequence of points around

        So lets have a look at where the old points would fall now
        nx, ny, mx, my = b
        self.p1 = complex(nx, ny)
        self.p2 = complex(mx, ny)
        self.p3 = complex(mx, my)
        self.p4 = complex(nx, my)
        """
        n1 = self.p1 + self.d1
        n2 = self.p2 + self.d2
        n3 = self.p3 + self.d3
        n4 = self.p4 + self.d4
        p1 = matrix.point_in_matrix_space((self.p1.real, self.p1.imag))
        p2 = matrix.point_in_matrix_space((self.p2.real, self.p2.imag))
        p3 = matrix.point_in_matrix_space((self.p3.real, self.p3.imag))
        p4 = matrix.point_in_matrix_space((self.p4.real, self.p4.imag))
        n1 = matrix.point_in_matrix_space((n1.real, n1.imag))
        n2 = matrix.point_in_matrix_space((n2.real, n2.imag))
        n3 = matrix.point_in_matrix_space((n3.real, n3.imag))
        n4 = matrix.point_in_matrix_space((n4.real, n4.imag))
        # We need to establish the top left point of p1 to p4 and swap n1 to n4 accordingly
        nx = min(p1.x, p2.x, p3.x, p4.x)
        mx = max(p1.x, p2.x, p3.x, p4.x)
        ny = min(p1.y, p2.y, p3.y, p4.y)
        my = max(p1.y, p2.y, p3.y, p4.y)
        candidates = [(p1, n1), (p2, n2), (p3, n3), (p4, n4)]

        def find_values(x, y):
            for idx in range(len(candidates)):
                content = candidates[idx]
                if content is None:
                    continue
                p, n = content
                if p.x == x and p.y == y:
                    candidates[idx] = None
                    return p, n
            # This will never happen!
            return None, None

        pp1, nn1 = find_values(nx, ny)
        pp2, nn2 = find_values(mx, ny)
        pp3, nn3 = find_values(mx, my)
        pp4, nn4 = find_values(nx, my)
        self.d1 = complex(nn1.x - pp1.x, nn1.y - pp1.y)
        self.d2 = complex(nn2.x - pp2.x, nn2.y - pp2.y)
        self.d3 = complex(nn3.x - pp3.x, nn3.y - pp3.y)
        self.d4 = complex(nn4.x - pp4.x, nn4.y - pp4.y)


    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Warp"
        default_map["enabled"] = "" if self.output else "(Disabled) "

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

    def as_geometry(self, **kws) -> Geomstr:
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
        if self._interim:
            return outlines

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

    def set_interim(self):
        self.empty_cache()
        self._interim = True

    def altered(self, *args, **kwargs):
        self._interim = False
        super().altered()

    def modified(self):
        self.altered()

    def notify_scaled(self, node=None, sx=1, sy=1, ox=0, oy=0, interim=False, **kwargs):
        Node.notify_scaled(self, node, sx, sy, ox, oy, interim=interim, **kwargs)
        if node is self:
            return
        if interim:
            self.set_interim()
        else:
            self.altered()

    def notify_translated(self, node=None, dx=0, dy=0, interim=False, **kwargs):
        Node.notify_translated(self, node, dx, dy, interim=interim, **kwargs)
        if node is self:
            return
        if interim:
            self.set_interim()
        else:
            self.altered()

    def can_drop(self, drag_node):
        if hasattr(drag_node, "as_geometry") or drag_node.type in ("effect", "file", "group", "reference") or (drag_node.type.startswith("op ") and drag_node.type != "op dots"):
            return True
        return False

    def drop(self, drag_node, modify=True, flag=False):
        # Default routine for drag + drop for an effect node - irrelevant for others...
        if not self.can_drop(drag_node):
            return False
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
            if modify:
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
            old_references = list(self._references)
            result = drag_node.drop(self, modify=modify, flag=flag)
            if result and modify:
                if hasattr(drag_node, "color") and drag_node.color is not None:
                    self.stroke = drag_node.color
                for ref in old_references:
                    ref.remove_node()
            return result
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
