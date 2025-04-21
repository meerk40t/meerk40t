from math import isnan

from meerk40t.core.cutcode.dwellcut import DwellCut
from meerk40t.core.elements.element_types import *
from meerk40t.core.node.node import Node
from meerk40t.core.parameters import Parameters
from meerk40t.core.units import UNITS_PER_MM
from meerk40t.svgelements import Color


class DotsOpNode(Node, Parameters):
    """
    Default object defining any operation done on the laser.

    This is a Node of type "op dots".
    """

    def __init__(self, settings=None, **kwargs):
        if settings is not None:
            settings = dict(settings)
        Parameters.__init__(self, settings, **kwargs)
        self._allowed_elements_dnd = ("elem point",)
        self._allowed_elements = ("elem point",)
        # Is this op out of useful bounds?
        self.dangerous = False
        self.stopop = True
        self.label = "Dots"

        self.allowed_attributes = []
        super().__init__(type="op dots", **kwargs)
        self._formatter = "{enabled}{pass}{element_type} {dwell_time}ms dwell {color}"

    def __repr__(self):
        return "DotsOpNode()"

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
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
            if len(cc) > 0:
                t += cc[0].upper()
                ct += 1
        if ct > 0:
            s = self.color.hex + "-" + t
        default_map["colcode"] = s
        default_map["opstop"] = "(stop)" if self.stopop else ""
        default_map.update(self.settings)
        default_map["color"] = self.color.hexrgb if self.color is not None else ""
        default_map["percent"] = "100%"
        default_map["ppi"] = "default"
        if self.power is not None:
            default_map["percent"] = f"{self.power / 10.0:.0f}%"
            default_map["ppi"] = f"{self.power:.0f}"
        return default_map

    def can_drop(self, drag_node):
        # Default routine for drag + drop for an op node - irrelevant for others...
        if drag_node.has_ancestor("branch reg"):
            # Will be dealt with in elements -
            # we don't implement a more sophisticated routine here
            return False
        if hasattr(drag_node, "as_geometry") and drag_node.type in self._allowed_elements_dnd:
            return True
        elif drag_node.type == "reference" and drag_node.node.type in self._allowed_elements_dnd:
            return True
        elif drag_node.type in op_nodes:
            # Move operation to a different position.
            return True
        elif drag_node.type in ("file", "group"):
            return not any(e.has_ancestor("branch reg") for e in drag_node.flat(elem_nodes))
        return False

    def drop(self, drag_node, modify=True, flag=False):
        # Default routine for drag + drop for an op node - irrelevant for others...
        if hasattr(drag_node, "as_geometry"):
            if (
                drag_node.type not in self._allowed_elements_dnd
                or drag_node.has_ancestor("branch reg")
            ):
                return False
            # Dragging element onto operation adds that element to the op.
            if modify:
                self.add_reference(drag_node, pos=None if flag else 0)
            return True
        elif drag_node.type == "reference":
            # Disallow drop of image refelems onto a Dot op.
            if not drag_node.node.type in self._allowed_elements_dnd:
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
        elif drag_node.type in ("file", "group") and not drag_node.has_ancestor(
            "branch reg"
        ):
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

    def has_attributes(self):
        return "stroke" in self.allowed_attributes or "fill" in self.allowed_attributes

    def is_referenced(self, node):
        for e in self.children:
            if e is node:
                return True
            if hasattr(e, "node") and e.node is node:
                return True
        return False

    def valid_node_for_reference(self, node):
        if node.type in self._allowed_elements_dnd:
            return True
        else:
            return False

    def classify(self, node, fuzzy=False, fuzzydistance=100, usedefault=False):
        def matching_color(col1, col2):
            _result = False
            if col1 is None and col2 is None:
                _result = True
            elif (
                col1 is not None
                and col1.argb is not None
                and col2 is not None
                and col2.argb is not None
            ):
                if fuzzy:
                    distance = Color.distance(col1, col2)
                    _result = distance < fuzzydistance
                else:
                    _result = col1 == col2
            return _result

        if self.is_referenced(node):
            # No need to add it again...
            return False, False, None
        feedback = []
        if node.type in self._allowed_elements:
            if self.default and usedefault:
                # Have classified but more classification might be needed
                if self.valid_node_for_reference(node):
                    self.add_reference(node)
                    feedback.append("stroke")
                    feedback.append("fill")
                    return True, self.stopop, feedback
            else:
                if self.has_attributes():
                    result = False
                    for attribute in self.allowed_attributes:
                        if (
                            hasattr(node, attribute)
                            and getattr(node, attribute) is not None
                        ):
                            plain_color_op = abs(self.color)
                            plain_color_node = abs(getattr(node, attribute))
                            if matching_color(plain_color_op, plain_color_node):
                                if self.valid_node_for_reference(node):
                                    result = True
                                    self.add_reference(node)
                                    # Have classified but more classification might be needed
                                    feedback.append(attribute)
                    if result:
                        return True, self.stopop, feedback
                else:  # empty ? Anything goes
                    if self.valid_node_for_reference(node):
                        self.add_reference(node)
                        # Have classified but more classification might be needed
                        feedback.append("stroke")
                        feedback.append("fill")
                        return True, self.stopop, feedback
        return False, False, None

    def load(self, settings, section):
        settings.read_persistent_attributes(section, self)
        hexa = self.settings.get("hex_color")
        if hexa is not None:
            self.color = Color(hexa)
        self.updated()

    def save(self, settings, section):
        # Sync certain properties with self.settings
        for attr in ("label", "lock", "id"):
            if hasattr(self, attr) and attr in self.settings:
                self.settings[attr] = getattr(self, attr)
        if "hex_color" in self.settings:
            self.settings["hex_color"] = self.color.hexa

        settings.write_persistent_attributes(section, self)
        settings.write_persistent(section, "hex_color", self.color.hexa)
        settings.write_persistent_dict(section, self.settings)

    def time_estimate(self):
        estimate = 0
        for e in self.children:
            if e.type == "reference":
                e = e.node
            if e.type == "elem point":
                estimate += self.dwell_time
        if self.passes_custom and self.passes != 1:
            estimate *= max(self.passes, 1)

        if isnan(estimate):
            estimate = 0

        hours, remainder = divmod(estimate, 3600)
        minutes, seconds = divmod(remainder, 60)

        return f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"

    def preprocess(self, context, matrix, plan):
        """
        Preprocess hatch values

        @param context:
        @param matrix:
        @param plan: Plan value during preprocessor call
        @return:
        """
        if isinstance(self.speed, str):
            try:
                self.speed = float(self.speed)
            except ValueError:
                pass
        native_mm = abs(complex(*matrix.transform_vector([0, UNITS_PER_MM])))
        self.settings["native_mm"] = native_mm
        self.settings["native_speed"] = self.speed * native_mm
        self.settings["native_rapid_speed"] = self.rapid_speed * native_mm

    def as_cutobjects(self, closed_distance=15, passes=1):
        """Generator of cutobjects for a particular operation."""
        settings = self.derive()
        for point_node in self.children:
            if point_node.type == "reference":
                point_node = point_node.node
            if point_node.type != "elem point":
                continue
            if point_node.point is None:
                continue
            if getattr(point_node, "hidden", False):
                continue
            yield DwellCut(
                (point_node.point[0], point_node.point[1]),
                dwell_time=self.dwell_time,
                settings=settings,
                passes=passes,
            )

    @property
    def bounds(self):
        if not self._bounds_dirty:
            return self._bounds

        self._bounds = None
        if self.output:
            if self._children:
                self._bounds = Node.union_bounds(self._children, bounds=self._bounds, ignore_locked=False, ignore_hidden=True)
            self._bounds_dirty = False
        return self._bounds
