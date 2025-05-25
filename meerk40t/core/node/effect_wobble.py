import math
from copy import copy
from math import sqrt

from meerk40t.core.node.node import Node
from meerk40t.core.node.mixins import Suppressable
from meerk40t.core.units import Length
from meerk40t.svgelements import Color
from meerk40t.tools.geomstr import Geomstr  # ,  Scanbeam


class WobbleEffectNode(Node, Suppressable):
    """
    Effect node performing a wobble. Effects are themselves a sort of geometry node that contains other geometry and
    the required data to produce additional geometry.
    """

    def __init__(self, *args, id=None, label=None, lock=False, **kwargs):
        self.fill = None
        self.stroke = Color("Blue")
        self.stroke_width = 100.0
        self.stroke_scale = False
        self._stroke_zero = None
        self.output = True
        self.autohide = True
        self.wobble_radius = "1.5mm"
        self.wobble_interval = "0.1mm"
        self.wobble_speed = 50
        self.wobble_type = "circle"
        self._interim = False
        super().__init__(
            self, type="effect wobble", id=id, label=label, lock=lock, **kwargs
        )
        if "hidden" in kwargs:
            if isinstance(kwargs["hidden"], str):
                if kwargs["hidden"].lower() == "true":
                    kwargs["hidden"] = True
                else:
                    kwargs["hidden"] = False
            self.hidden = kwargs["hidden"]
        self._formatter = "{element_type} {id} - {type} {radius} ({children})"

        if label is None:
            self.label = "Wobble"
        else:
            self.label = label
        self.recalculate()

        self._total_count = 0
        self._total_distance = 0
        self._remainder = 0
        self.previous_angle = None
        self._last_x = None
        self._last_y = None

    @property
    def implied_stroke_width(self):
        return self.stroke_width

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self._parent)})"

    def __copy__(self):
        nd = self.node_dict
        nd["stroke"] = copy(self.stroke)
        nd["fill"] = copy(self.fill)
        return WobbleEffectNode(**nd)

    def scaled(self, sx, sy, ox, oy, interim=False):
        self.altered()

    def notify_attached(self, node=None, **kwargs):
        Node.notify_attached(self, node=node, **kwargs)
        if node is self:
            return
        if self.autohide and hasattr(node, "hidden"):
            node.hidden = True
        self.altered()

    def notify_detached(self, node=None, **kwargs):
        Node.notify_detached(self, node=node, **kwargs)
        if node is self:
            return
        if self.autohide and hasattr(node, "hidden"):
            node.hidden = False
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

    def append_child(self, new_child):
        if self.autohide and hasattr(new_child, "hidden"):
            new_child.hidden = True
        return super().append_child(new_child)

    @property
    def radius(self):
        return self.wobble_radius

    @radius.setter
    def radius(self, value):
        if self.wobble_radius != value:
            self.wobble_radius = value
            self.recalculate()

    @property
    def interval(self):
        return self.wobble_interval

    @interval.setter
    def interval(self, value):
        if self.wobble_interval != value:
            self.wobble_interval = value
            self.recalculate()

    @property
    def speed(self):
        return self.wobble_speed

    @speed.setter
    def speed(self, value):
        if self.wobble_speed != value:
            self.wobble_speed = value
            self.recalculate()

    def recalculate(self):
        """
        Ensure that the properties for radius, interval and speed are in usable units.
        @return:
        """
        w_radius = self.wobble_radius
        w_interval = self.wobble_interval

        if isinstance(w_radius, float):
            self._radius = w_radius
        else:
            self._radius = float(Length(w_radius))

        if isinstance(w_interval, float):
            self._interval = w_interval
        else:
            self._interval = float(Length(w_interval))

    def preprocess(self, context, matrix, plan):
        factor = sqrt(abs(matrix.determinant))
        self._radius *= factor
        self._interval *= factor
        self.set_dirty_bounds()

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Wobble"
        default_map["type"] = str(self.wobble_type)
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["radius"] = str(self.wobble_radius)
        default_map["interval"] = str(self.wobble_interval)
        default_map["speed"] = str(self.wobble_speed)

        default_map["children"] = str(len(self.children))
        return default_map

    def circle(self, x0, y0, x1, y1):
        if x1 is None or y1 is None:
            yield x0, y0
            return
        for tx, ty in self.wobble(x0, y0, x1, y1):
            t = self._total_distance / (math.tau * self._radius)
            dx = self._radius * math.cos(t * self.speed)
            dy = self._radius * math.sin(t * self.speed)
            yield tx + dx, ty + dy

    def wobble(self, x0, y0, x1, y1):
        distance_change = abs(complex(x0, y0) - complex(x1, y1))
        positions = 1 - self._remainder
        # Circumvent a div by zero error
        try:
            intervals = distance_change / self._interval
        except ZeroDivisionError:
            intervals = 1
        while positions <= intervals:
            amount = positions / intervals
            tx = amount * (x1 - x0) + x0
            ty = amount * (y1 - y0) + y0
            self._total_distance += self._interval
            self._total_count += 1
            yield tx, ty
            positions += 1
        self._remainder += intervals
        self._remainder %= 1

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
        Calculates the hatch effect geometry. The pass index is the number of copies of this geometry whereas the
        internal loops value is rotated each pass by the angle-delta.

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

        path = Geomstr()
        if self._radius is None or self._interval is None:
            self.recalculate()

        if self.wobble_type == "circle":
            path.append(
                Geomstr.wobble_circle(
                    outlines,
                    radius=self._radius,
                    interval=self._interval,
                    speed=self.wobble_speed,
                )
            )
        elif self.wobble_type == "circle_right":
            path.append(
                Geomstr.wobble_circle_right(
                    outlines,
                    radius=self._radius,
                    interval=self._interval,
                    speed=self.wobble_speed,
                )
            )
        elif self.wobble_type == "circle_left":
            path.append(
                Geomstr.wobble_circle_left(
                    outlines,
                    radius=self._radius,
                    interval=self._interval,
                    speed=self.wobble_speed,
                )
            )
        elif self.wobble_type == "sinewave":
            path.append(
                Geomstr.wobble_sinewave(
                    outlines,
                    radius=self._radius,
                    interval=self._interval,
                    speed=self.wobble_speed,
                )
            )
        elif self.wobble_type == "sawtooth":
            path.append(
                Geomstr.wobble_sawtooth(
                    outlines,
                    radius=self._radius,
                    interval=self._interval,
                    speed=self.wobble_speed,
                )
            )
        elif self.wobble_type == "jigsaw":
            path.append(
                Geomstr.wobble_jigsaw(
                    outlines,
                    radius=self._radius,
                    interval=self._interval,
                    speed=self.wobble_speed,
                )
            )
        elif self.wobble_type == "gear":
            path.append(
                Geomstr.wobble_gear(
                    outlines,
                    radius=self._radius,
                    interval=self._interval,
                    speed=self.wobble_speed,
                )
            )
        elif self.wobble_type == "slowtooth":
            path.append(
                Geomstr.wobble_slowtooth(
                    outlines,
                    radius=self._radius,
                    interval=self._interval,
                    speed=self.wobble_speed,
                )
            )
        elif self.wobble_type == "meander_1":
            path.append(
                Geomstr.wobble_meander_1(
                    outlines,
                    radius=self._radius,
                    interval=self._interval,
                    speed=self.wobble_speed,
                )
            )
        elif self.wobble_type == "meander_2":
            path.append(
                Geomstr.wobble_meander_2(
                    outlines,
                    radius=self._radius,
                    interval=self._interval,
                    speed=self.wobble_speed,
                )
            )
        elif self.wobble_type == "meander_3":
            path.append(
                Geomstr.wobble_meander_3(
                    outlines,
                    radius=self._radius,
                    interval=self._interval,
                    speed=self.wobble_speed,
                )
            )
        elif self.wobble_type == "dash":
            path.append(
                Geomstr.wobble_dash(
                    outlines,
                    radius=self._radius,
                    interval=self._interval,
                    speed=self.wobble_speed,
                )
            )
        elif self.wobble_type == "tabs":
            path.append(
                Geomstr.wobble_tab(
                    outlines,
                    radius=self._radius,
                    interval=self._interval,
                    speed=self.wobble_speed,
                )
            )
        return path

    def set_interim(self):
        self.empty_cache()
        self._interim = True

    def altered(self, *args, **kwargs):
        self._interim = False
        super().altered()

    def modified(self):
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
