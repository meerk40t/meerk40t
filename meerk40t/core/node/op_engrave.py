from copy import copy

from meerk40t.core.cutcode import (
    CubicCut,
    CutGroup,
    DwellCut,
    LineCut,
    PlotCut,
    QuadCut,
    RasterCut,
)
from meerk40t.core.element_types import *
from meerk40t.core.node.node import Node
from meerk40t.core.parameters import Parameters
from meerk40t.core.units import Length
from meerk40t.image.actualize import actualize
from meerk40t.svgelements import (
    Angle,
    Close,
    Color,
    CubicBezier,
    Line,
    Matrix,
    Move,
    Path,
    Polygon,
    QuadraticBezier,
    Shape,
    SVGElement,
    SVGImage,
)
from meerk40t.tools.pathtools import EulerianFill, VectorMontonizer

MILS_IN_MM = 39.3701


class EngraveOpNode(Node, Parameters):
    """
    Default object defining any operation done on the laser.

    This is a Node of type "op engrave".
    """

    def __init__(self, *args, **kwargs):
        if "setting" in kwargs:
            kwargs = kwargs["settings"]
            if "type" in kwargs:
                del kwargs["type"]
        Node.__init__(self, *args, type="op engrave", **kwargs)
        Parameters.__init__(self, None, **kwargs)
        self.settings.update(kwargs)
        self._status_value = "Queued"

        if len(args) == 1:
            obj = args[0]
            if isinstance(obj, Node):
                self.add_reference(obj)
            elif isinstance(obj, SVGElement):
                self.add_reference(obj.node)
            elif hasattr(obj, "settings"):
                self.settings = dict(obj.settings)
            elif isinstance(obj, dict):
                self.settings.update(obj)

    def __repr__(self):
        return "EngraveOpNode()"

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        if self.default:
            parts.append("✓")
        if self.passes_custom and self.passes != 1:
            parts.append("%dX" % self.passes)
        parts.append("Engrave")
        if self.speed is not None:
            parts.append("%gmm/s" % float(self.speed))
        if self.power is not None:
            parts.append("%gppi" % float(self.power))
        if self.frequency is not None:
            parts.append("%gkHz" % float(self.frequency))
        parts.append("%s" % self.color.hex)
        if self.dratio_custom:
            parts.append("d:%g" % self.dratio)
        if self.acceleration_custom:
            parts.append("a:%d" % self.acceleration)
        if self.dot_length_custom:
            parts.append("dot: %d" % self.dot_length)
        return " ".join(parts)

    def __copy__(self):
        return EngraveOpNode(self)

    def default_map(self, default_map=None):
        default_map = super(EngraveOpNode, self).default_map(default_map=default_map)
        default_map['element_type'] = "Engrave"
        default_map['enabled'] = "(Disabled) " if not self.output else ""
        default_map['speed'] = "default"
        default_map['power'] = "default"
        default_map['frequency'] = "default"
        default_map.update(self.settings)
        return default_map

    def drop(self, drag_node):
        if drag_node.type.startswith("elem"):
            if drag_node.type == "elem image":
                return False
            # Dragging element onto operation adds that element to the op.
            self.add_reference(drag_node, pos=0)
            return True
        elif drag_node.type == "reference":
            # Disallow drop of image refelems onto a Dot op.
            if drag_node.type == "elem image":
                return False
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
                # Add element to operation
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

    def save(self, settings, section):
        settings.write_persistent_attributes(section, self)
        settings.write_persistent(section, "hex_color", self.color.hexa)
        settings.write_persistent_dict(section, self.settings)

    def copy_children(self, obj):
        for element in obj.children:
            self.add_reference(element)

    def deep_copy_children(self, obj):
        for node in obj.children:
            self.add(copy(node.node), type=node.node.type)

    def time_estimate(self):
        estimate = 0
        for e in self.children:
            e = e.object
            if isinstance(e, Shape):
                try:
                    length = e.length(error=1e-2, min_depth=2)
                except AttributeError:
                    length = 0
                try:
                    estimate += length / (MILS_IN_MM * self.speed)
                except ZeroDivisionError:
                    estimate = float("inf")
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
        for element in self.children:
            object_path = element.object
            if isinstance(object_path, SVGImage):
                box = object_path.bbox()
                path = Path(
                    Polygon(
                        (box[0], box[1]),
                        (box[0], box[3]),
                        (box[2], box[3]),
                        (box[2], box[1]),
                    )
                )
            else:
                # Is a shape or path.
                if not isinstance(object_path, Path):
                    path = abs(Path(object_path))
                else:
                    path = abs(object_path)
                path.approximate_arcs_with_cubics()
            settings["line_color"] = path.stroke
            for subpath in path.as_subpaths():
                sp = Path(subpath)
                if len(sp) == 0:
                    continue
                closed = (
                    isinstance(sp[-1], Close)
                    or abs(sp.z_point - sp.current_point) <= closed_distance
                )
                group = CutGroup(
                    None,
                    closed=closed,
                    settings=settings,
                    passes=passes,
                )
                group.path = Path(subpath)
                group.original_op = self.type
                for seg in subpath:
                    if isinstance(seg, Move):
                        pass  # Move operations are ignored.
                    elif isinstance(seg, Close):
                        if seg.start != seg.end:
                            group.append(
                                LineCut(
                                    seg.start,
                                    seg.end,
                                    settings=settings,
                                    passes=passes,
                                    parent=group,
                                )
                            )
                    elif isinstance(seg, Line):
                        if seg.start != seg.end:
                            group.append(
                                LineCut(
                                    seg.start,
                                    seg.end,
                                    settings=settings,
                                    passes=passes,
                                    parent=group,
                                )
                            )
                    elif isinstance(seg, QuadraticBezier):
                        group.append(
                            QuadCut(
                                seg.start,
                                seg.control,
                                seg.end,
                                settings=settings,
                                passes=passes,
                                parent=group,
                            )
                        )
                    elif isinstance(seg, CubicBezier):
                        group.append(
                            CubicCut(
                                seg.start,
                                seg.control1,
                                seg.control2,
                                seg.end,
                                settings=settings,
                                passes=passes,
                                parent=group,
                            )
                        )
                if len(group) > 0:
                    group[0].first = True
                for i, cut_obj in enumerate(group):
                    cut_obj.closed = closed
                    try:
                        cut_obj.next = group[i + 1]
                    except IndexError:
                        cut_obj.last = True
                        cut_obj.next = group[0]
                    cut_obj.previous = group[i - 1]
                yield group
