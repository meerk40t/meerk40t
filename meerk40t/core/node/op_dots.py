from copy import copy

from meerk40t.core.cutcode import DwellCut
from meerk40t.core.element_types import *
from meerk40t.core.node.node import Node
from meerk40t.core.parameters import Parameters
from meerk40t.svgelements import Color

MILS_IN_MM = 39.3701


class DotsOpNode(Node, Parameters):
    """
    Default object defining any operation done on the laser.

    This is a Node of type "op dots".
    """

    def __init__(self, *args, **kwargs):
        if "setting" in kwargs:
            kwargs = kwargs["settings"]
            if "type" in kwargs:
                del kwargs["type"]
        Node.__init__(self, type="op dots", **kwargs)
        Parameters.__init__(self, None, **kwargs)
        self.settings.update(kwargs)
        self._status_value = "Queued"

        if len(args) == 1:
            obj = args[0]
            if hasattr(obj, "settings"):
                self.settings = dict(obj.settings)
            elif isinstance(obj, dict):
                self.settings.update(obj)

    def __repr__(self):
        return "DotsOpNode()"

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        if self.default:
            parts.append("✓")
        if self.passes_custom and self.passes != 1:
            parts.append("%dX" % self.passes)
        if self.frequency is not None:
            parts.append("%gkHz" % float(self.frequency))
        parts.append("Dots")
        parts.append("%gms dwell" % self.dwell_time)
        return " ".join(parts)

    def __copy__(self):
        return DotsOpNode(self)

    @property
    def bounds(self):
        if self._bounds_dirty:
            self._bounds = Node.union_bounds(self.flat(types=elem_ref_nodes))
        return self._bounds

    def default_map(self, default_map=None):
        default_map = super(DotsOpNode, self).default_map(default_map=default_map)
        default_map['element_type'] = "Dots"
        default_map['enabled'] = "(Disabled) " if not self.output else ""
        default_map['dwell_time'] = "default"
        default_map.update(self.settings)
        return default_map

    def drop(self, drag_node):
        if drag_node.type.startswith("elem"):
            if drag_node.type == "elem image":
                return False
            # Dragging element onto operation adds a reference of that elem to the op.
            self.add_reference(drag_node, pos=0)
            return True
        elif drag_node.type == "reference":
            # Move a refelem to end of op.
            self.append_child(drag_node)
            return True
        elif drag_node.type in op_nodes:
            # Move operation to a different position.
            self.insert_sibling(drag_node)
            return True
        elif drag_node.type in ("file", "group"):
            some_nodes = False
            for e in drag_node.flat("elem"):
                # Disallow drop of image elems onto a Dot op.
                if drag_node.type == "elem image":
                    continue
                # Add reference to element to operation
                self.add_reference(e)
                some_nodes = True
            return some_nodes
        return False

    def load(self, settings, section):
        settings.read_persistent_attributes(section, self)
        update_dict = settings.read_persistent_string_dict(section, suffix=True)
        self.settings.update(update_dict)
        self.validate()
        hexa = self.settings.get("hex_color")
        if hexa is not None:
            self.color = Color(hexa)
        self.notify_update()

    def save(self, settings, section):
        settings.write_persistent_attributes(section, self)
        settings.write_persistent(section, "hex_color", self.color.hexa)
        settings.write_persistent_dict(section, self.settings)

    def copy_children(self, obj):
        for element in obj.children:
            self.add_reference(element)

    def deep_copy_children(self, obj):
        for node in obj.children:
            self.add_node(copy(node.node))

    def time_estimate(self):
        estimate = 0
        for e in self.children:
            if e.type == "reference":
                e = e.node
            if e.type == "elem point":
                estimate += self.dwell_time
        hours, remainder = divmod(estimate, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "%s:%s:%s" % (
            int(hours),
            str(int(minutes)).zfill(2),
            str(int(seconds)).zfill(2),
        )

    def as_cutobjects(self, closed_distance=15, passes=1):
        """Generator of cutobjects for a particular operation."""
        settings = self.derive()
        for point_node in self.children:
            if point_node.type != "elem point":
                continue
            yield DwellCut(
                (point_node.point[0], point_node[1]),
                settings=settings,
                passes=passes,
            )
