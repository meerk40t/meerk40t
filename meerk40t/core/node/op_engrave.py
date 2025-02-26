from math import isnan

from meerk40t.core.elements.element_types import *
from meerk40t.core.node.node import Node
from meerk40t.core.node.nutils import path_to_cutobjects
from meerk40t.core.parameters import Parameters
from meerk40t.core.units import UNITS_PER_MM
from meerk40t.svgelements import Color, Path, Polygon


class EngraveOpNode(Node, Parameters):
    """
    Default object defining any operation done on the laser.

    This is a Node of type "op engrave".
    """

    def __init__(self, settings=None, **kwargs):
        if settings is not None:
            settings = dict(settings)
        Parameters.__init__(self, settings, **kwargs)

        # Is this op out of useful bounds?
        self.dangerous = False

        self.label = "Engrave"
        # We may want to add more advanced logic at a later time
        # to convert text to paths within dnd...
        self._allowed_elements_dnd = (
            "elem ellipse",
            "elem path",
            "elem polyline",
            "elem rect",
            "elem line",
            "effect hatch",
            "effect wobble",
            "effect warp",
        )
        # Which elements do we consider for automatic classification?
        self._allowed_elements = (
            "elem ellipse",
            "elem path",
            "elem polyline",
            "elem rect",
            "elem line",
            "effect hatch",
            "effect wobble",
            "effect warp",
        )

        # To which attributes does the classification color check respond
        # Can be extended / reduced by add_color_attribute / remove_color_attribute
        self.allowed_attributes = [
            "stroke",
        ]  # comma is relevant

        super().__init__(type="op engrave", **kwargs)
        self._formatter = "{enabled}{pass}{element_type} {speed}mm/s @{power} {color}"

    def __repr__(self):
        return "EngraveOpNode()"

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Engrave"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["danger"] = "❌" if self.dangerous else ""
        default_map["defop"] = "✓" if self.default else ""
        default_map["pass"] = (
            f"{self.passes}X " if self.passes_custom and self.passes != 1 else ""
        )
        default_map["penpass"] = f"(p:{self.penbox_pass}) " if self.penbox_pass else ""
        default_map["penvalue"] = (
            f"(v:{self.penbox_value}) " if self.penbox_value else ""
        )
        default_map["speed"] = "default"
        default_map["power"] = "default"
        default_map["frequency"] = "default"
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
        default_map["speed_mm_min"] = (
            "" if self.speed is None else f"{self.speed * 60:.0f}"
        )
        return default_map

    def can_drop(self, drag_node):
        # Default routine for drag + drop for an op node - irrelevant for others...
        if drag_node.has_ancestor("branch reg"):
            # Will be dealt with in elements -
            # we don't implement a more sophisticated routine here
            return False
        if (
            hasattr(drag_node, "as_geometry")
            and drag_node.type in self._allowed_elements_dnd
        ):
            return True
        elif (
            drag_node.type == "reference"
            and drag_node.node.type in self._allowed_elements_dnd
        ):
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
                if e.type in self._allowed_elements_dnd:
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

    def add_reference(self, node=None, pos=None, **kwargs):
        # is the very first child an effect node?
        # if yes then we will put that reference under this one
        if node is None:
            return
        if not self.valid_node_for_reference(node):
            # We could raise a ValueError but that will break things...
            return
        first_is_effect =  (
            len(self._children) > 0 and
            self._children[0].type.startswith("effect ")
        )
        effect = self._children[0] if first_is_effect else None
        ref = self.add(node=node, type="reference", pos=pos, **kwargs)
        node._references.append(ref)
        if first_is_effect:
            effect.append_child(ref)

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
        for node in self.children:
            if node.type == "reference":
                node = node.node
            try:
                path = node.as_path()
            except AttributeError:
                continue
            length = path.length(error=1e-2, min_depth=2)
            try:
                estimate += length / (UNITS_PER_MM * self.speed)
            except ZeroDivisionError:
                estimate = float("inf")
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

        def get_pathlist(node, factor):
            from time import perf_counter

            pathlist = []
            if node.type == "reference":
                node = node.node
            if node.type == "elem image":
                box = node.bbox()
                pathlist.append(
                    (
                        None,
                        Path(
                            Polygon(
                                (box[0], box[1]),
                                (box[0], box[3]),
                                (box[2], box[3]),
                                (box[2], box[1]),
                            )
                        ),
                    )
                )
            elif hasattr(node, "final_geometry"):
                # This will deliver all relevant effects
                # like tabs, dots/dashes applied to the element
                path = node.final_geometry(unitfactor=factor).as_path()
                path.approximate_arcs_with_cubics()
                pathlist.append((None, path))
            elif node.type == "elem path":
                path = abs(node.path)
                path.approximate_arcs_with_cubics()
                pathlist.append((None, path))
            elif node.type.startswith("effect"):
                if hasattr(node, "as_geometries"):
                    time_indicator = f"{perf_counter():.5f}".replace(".", "")
                    pathlist.extend(
                        (f"hatch_{idx}_{time_indicator}", effect_geom.as_path())
                        for idx, effect_geom in enumerate(list(node.as_geometries()))
                    )
                else:
                    pathlist.append((None, node.as_geometry().as_path()))
            else:
                path = abs(Path(node.shape))
                path.approximate_arcs_with_cubics()
                pathlist.append((None, path))
            return pathlist

        settings = self.derive()
        factor = settings["native_mm"] / UNITS_PER_MM if "native_mm" in settings else 1
        for node in self.children:
            if (
                hasattr(node, "hidden")
                and node.hidden
                or node.type not in self._allowed_elements_dnd
            ):
                continue

            pathlist = get_pathlist(node, factor)

            try:
                stroke = node.stroke
            except AttributeError:
                # ImageNode does not have a stroke.
                stroke = None
            for origin, path in pathlist:
                yield from path_to_cutobjects(
                    path,
                    settings=settings,
                    closed_distance=closed_distance,
                    passes=passes,
                    original_op=self.type,
                    color=stroke,
                    origin=origin,
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
