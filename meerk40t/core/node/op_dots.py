from copy import copy

from meerk40t.core.cutcode import DwellCut
from meerk40t.core.element_types import *
from meerk40t.core.node.node import Node
from meerk40t.core.parameters import Parameters
from meerk40t.svgelements import Color


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
        self._formatter = "{enabled}{pass}{element_type} {dwell_time}ms dwell {color}"
        self.settings.update(kwargs)

        if len(args) == 1:
            obj = args[0]
            if hasattr(obj, "settings"):
                self.settings = dict(obj.settings)
            elif isinstance(obj, dict):
                self.settings.update(obj)
        self.allowed_elements_dnd = ("elem point",)
        self.allowed_elements = ("elem point",)
        self.allowed_attributes = []
        # Is this op out of useful bounds?
        self.dangerous = False
        self.settings["stopop"] = True

    def __repr__(self):
        return "DotsOpNode()"

    def __copy__(self):
        return DotsOpNode(self)

    @property
    def bounds(self):
        if self._bounds_dirty:
            self._bounds = Node.union_bounds(self.flat(types=elem_ref_nodes))
            self._bounds_dirty = False
        return self._bounds

    def is_dangerous(self, minpower, maxspeed):
        result = False
        if maxspeed is not None and self.speed > maxspeed:
            result = True
        if minpower is not None and self.power < minpower:
            result = True
        self.dangerous = result

    def default_map(self, default_map=None):
        default_map = super(DotsOpNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Dots"
        default_map["power"] = "default"
        default_map["frequency"] = "default"
        default_map["danger"] = "❌" if self.dangerous else ""
        default_map["defop"] = "✓" if self.default else ""
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["pass"] = (
            f"{self.passes}X " if self.passes_custom and self.passes != 1 else ""
        )
        default_map["penpass"] = f"(p:{self.penbox_pass}) " if self.penbox_pass else ""
        default_map["penvalue"] = (
            f"(v:{self.penbox_value}) " if self.penbox_value else ""
        )
        default_map["dwell_time"] = "default"
        ct = 0
        t = ""
        s = ""
        for cc in self.allowed_attributes:
            if len(cc)>0:
                t += cc[0].upper()
                ct += 1
        if ct>0:
            s = self.color.hex + "-" + t
        default_map["colcode"] = s
        default_map["opstop"] = "❌" if self.stopop else ""
        default_map.update(self.settings)
        default_map["color"] = self.color.hexrgb if self.color is not None else ""
        return default_map

    def drop(self, drag_node, modify=True):
        # Default routine for drag + drop for an op node - irrelevant for others...
        if drag_node.type.startswith("elem"):
            if not drag_node.type in self.allowed_elements_dnd:
                return False
            # Dragging element onto operation adds that element to the op.
            if modify:
                self.add_reference(drag_node, pos=0)
            return True
        elif drag_node.type == "reference":
            # Disallow drop of image refelems onto a Dot op.
            if not drag_node.node.type in self.allowed_elements_dnd:
                return False
            # Move a refelem to end of op.
            if modify:
                self.append_child(drag_node)
            return True
        elif drag_node.type in op_nodes:
            # Move operation to a different position.
            if modify:
                self.insert_sibling(drag_node)
            return True
        elif drag_node.type in ("file", "group"):
            some_nodes = False
            for e in drag_node.flat(elem_nodes):
                # Add element to operation
                if modify:
                    self.add_reference(e)
                some_nodes = True
            return some_nodes
        return False

    def has_color_attribute(self, attribute):
        return attribute in self.allowed_attributes

    def add_color_attribute(self, attribute):
        if not attribute in self.allowed_attributes:
            self.allowed_attributes.append(attribute)

    def remove_color_attribute(self, attribute):
        if attribute in self.allowed_attributes:
            self.allowed_attributes.remove(attribute)

    def valid_node(self, node):
        return True

    def classify(self, node, fuzzy=False, fuzzydistance=100, usedefault=False):
        def matching_color(col1, col2):
            result = False
            if col1 is None and col2 is None:
                result = True
            elif col1 is not None and col1.argb is not None and col2 is not None and col2.argb is not None:
                if fuzzy:
                    distance = Color.distance(col1, col2)
                    result = distance < fuzzydistance
                else:
                    result = col1 == col2
            return result

        if node.type in self.allowed_elements:
            if not self.default:
                if len(self.allowed_attributes)>0:
                    for attribute in self.allowed_attributes:
                        if hasattr(node, attribute) and getattr(node, attribute) is not None:
                            plain_color_op = abs(self.color)
                            plain_color_node = abs(getattr(node, attribute))
                            if matching_color(plain_color_op, plain_color_node):
                                if self.valid_node(node):
                                    self.add_reference(node)
                                # Have classified but more classification might be needed
                                return True, self.stopop
                else: # empty ? Anything goes
                    if self.valid_node(node):
                        self.add_reference(node)
                    # Have classified but more classification might be needed
                    return True, self.stopop
            elif self.default and usedefault:
                # Have classified but more classification might be needed
                if self.valid_node(node):
                    return True, self.stopop
        return False, False

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

    def copy_children_as_real(self, copy_node):
        for node in copy_node.children:
            self.add_node(copy(node.node))

    def time_estimate(self):
        estimate = 0
        for e in self.children:
            if e.type == "reference":
                e = e.node
            if e.type == "elem point":
                estimate += self.dwell_time
        if self.passes_custom and self.passes != 1:
            estimate *= max(self.passes, 1)
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
                (point_node.point[0], point_node.point[1]),
                settings=settings,
                passes=passes,
            )
