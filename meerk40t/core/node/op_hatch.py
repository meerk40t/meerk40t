from copy import copy
from math import isnan

from meerk40t.core.cutcode.plotcut import PlotCut
from meerk40t.core.elements.element_types import *
from meerk40t.core.node.elem_polyline import PolylineNode
from meerk40t.core.node.node import Node
from meerk40t.core.parameters import Parameters
from meerk40t.core.units import UNITS_PER_MM
from meerk40t.svgelements import Color, Path, Polyline


class HatchOpNode(Node, Parameters):
    """
    Default object defining any operation done on the laser.

    This is a Node of type "hatch op".
    """

    def __init__(self, *args, id=None, label=None, lock=False, **kwargs):
        Node.__init__(self, type="op hatch", id=id, label=label, lock=lock)
        Parameters.__init__(self, None, **kwargs)
        self._formatter = (
            "{enabled}{penpass}{pass}{element_type} {speed}mm/s @{power} {color}"
        )
        self._hatch_distance_native = None

        if len(args) == 1:
            obj = args[0]
            if hasattr(obj, "settings"):
                self.settings = dict(obj.settings)
            elif isinstance(obj, dict):
                self.settings.update(obj)
        # Which elements can be added to an operation (manually via DND)?
        self._allowed_elements_dnd = (
            "elem ellipse",
            "elem path",
            "elem polyline",
            "elem rect",
        )
        # Which elements do we consider for automatic classification?
        self._allowed_elements = (
            "elem ellipse",
            "elem path",
            "elem polyline",
            "elem rect",
        )
        # To which attributes does the classification color check respond
        # Can be extended / reduced by add_color_attribute / remove_color_attribute
        self.allowed_attributes = [
            "stroke",
        ]  # comma is relevant
        # Is this op out of useful bounds?
        self.dangerous = False
        self.stopop = True
        if label is None:
            self.label = "Hatch"
        else:
            self.label = label

    def __repr__(self):
        return "HatchOpNode()"

    def __copy__(self):
        return HatchOpNode(self)

    # def is_dangerous(self, minpower, maxspeed):
    #     result = False
    #     if maxspeed is not None and self.speed > maxspeed:
    #         result = True
    #     if minpower is not None and self.power < minpower:
    #         result = True
    #     self.dangerous = result

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Hatch"
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
        default_map["hatch_angle"] = "default"
        default_map["hatch_distance"] = "default"
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
        return default_map

    def drop(self, drag_node, modify=True):
        # Default routine for drag + drop for an op node - irrelevant for others...
        if drag_node.type.startswith("elem"):
            if (
                drag_node.type not in self._allowed_elements_dnd
                or drag_node._parent.type == "branch reg"
            ):
                return False
            # Dragging element onto operation adds that element to the op.
            if modify:
                self.add_reference(drag_node, pos=0)
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
        elif drag_node.type in ("file", "group"):
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

    def valid_node_for_reference(self, node):
        # First check type per se
        if node.type not in self._allowed_elements_dnd:
            return False
        # even then it might not be eligible
        if hasattr(node, "path"):
            # is_valid_closed_path(node.geometry):
            return True
        elif node.type == "elem polyline":
            return node.geometry.is_closed()
        elif node.type in ("elem rect", "elem ellipse"):
            return True
        return False

    def classify(self, node, fuzzy=False, fuzzydistance=100, usedefault=False):
        def matching_color(col1, col2):
            result = False
            if col1 is None and col2 is None:
                result = True
            elif (
                col1 is not None
                and col1.argb is not None
                and col2 is not None
                and col2.argb is not None
            ):
                if fuzzy:
                    distance = Color.distance(col1, col2)
                    result = distance < fuzzydistance
                else:
                    result = col1 == col2
            return result

        feedback = []
        if node.type in self._allowed_elements:
            if not self.default:
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
            elif self.default and usedefault:
                # Have classified but more classification might be needed
                if self.valid_node_for_reference(node):
                    self.add_reference(node)
                    feedback.append("stroke")
                    feedback.append("fill")
                    return True, self.stopop, feedback
        return False, False, None

    def load(self, settings, section):
        settings.read_persistent_attributes(section, self)
        update_dict = settings.read_persistent_string_dict(section, suffix=True)
        self.settings.update(update_dict)
        self.validate()
        hexa = self.settings.get("hex_color")
        if hexa is not None:
            self.color = Color(hexa)
        self.updated()

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
        # TODO: Implement time_estimate.
        if self.passes_custom and self.passes != 1:
            estimate *= max(self.passes, 1)

        if isnan(estimate):
            estimate = 0

        hours, remainder = divmod(estimate, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"

    @staticmethod
    def split(points):
        pos = 0
        for i, pts in enumerate(points):
            if pts is None:
                yield points[pos:i]
                pos = i + 1
        if pos != len(points):
            yield points[pos : len(points)]

    def preprocess(self, context, matrix, plan):
        """
        Preprocess hatch values

        @param context:
        @param matrix:
        @param plan:
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

        def hatch():
            settings = self.settings
            outlines = list()
            for node in self.children:
                try:
                    path = node.as_geometry()
                except AttributeError:
                    continue
                outlines.extend(path.as_interpolated_points(interpolate=100))
                outlines.append(None)
            self.remove_all_children()
            fills = list(context.match("hatch", suffix=True))
            penbox_pass = self.settings.get("penbox_pass")
            if penbox_pass is not None:
                try:
                    penbox_pass = context.penbox.pens[penbox_pass]
                except KeyError:
                    penbox_pass = None
            hatch_cache = dict()
            for p in range(self.implicit_passes):
                chain_settings = dict(settings)
                if "type" in chain_settings:
                    del chain_settings["type"]
                if penbox_pass is not None:
                    try:
                        chain_settings.update(penbox_pass[p])
                    except IndexError:
                        pass

                # Create cache key.
                h_dist = chain_settings.get("hatch_distance", "1mm")
                h_angle = chain_settings.get("hatch_angle", "0deg")
                if isinstance(h_angle, float):
                    h_angle = str(h_angle)
                hatch_type = chain_settings.get("hatch_type")
                if hatch_type not in fills:
                    hatch_type = fills[0]
                key = f"{hatch_type};{h_angle},{h_dist}"

                if key in hatch_cache:
                    hatches = hatch_cache[key]
                else:
                    # Create new hatch.
                    algorithm = context.lookup(f"hatch/{hatch_type}")
                    hatches = list(
                        algorithm(
                            settings=chain_settings, outlines=outlines, matrix=matrix
                        )
                    )
                    hatch_cache[key] = hatches
                if (
                    "line_color" not in chain_settings
                    or chain_settings["line_color"] is None
                    or chain_settings["line_color"].value is None
                ):
                    chain_settings["line_color"] = Color(
                        chain_settings.get("color", "black")
                    )
                for polyline in HatchOpNode.split(hatches):
                    node = PolylineNode(shape=Polyline(*polyline), **chain_settings)
                    node.settings = chain_settings
                    self.add_node(node)

        if self.children:
            commands = plan.commands
            commands.append(hatch)

    def as_cutobjects(self, closed_distance=15, passes=1):
        """Generator of cutobjects for a particular operation."""
        for node in self.children:
            if node.type != "elem polyline":
                continue
            settings = node.settings
            plot = PlotCut(settings=settings, color=node.stroke)
            for p in node.shape:
                x, y = p
                if not plot:
                    plot.plot_init(int(round(x)), int(round(y)))
                plot.plot_append(int(round(x)), int(round(y)), 1)
            yield plot
