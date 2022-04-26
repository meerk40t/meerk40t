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
from meerk40t.svgelements import (
    Angle,
    Color,
    Matrix,
    Path,
)
from meerk40t.tools.pathtools import EulerianFill

MILS_IN_MM = 39.3701


class HatchOpNode(Node, Parameters):
    """
    Default object defining any operation done on the laser.

    This is a Node of type "hatch op".
    """

    def __init__(self, *args, **kwargs):
        if "setting" in kwargs:
            kwargs = kwargs["settings"]
            if "type" in kwargs:
                del kwargs["type"]
        Node.__init__(self, type="op hatch", **kwargs)
        Parameters.__init__(self, None, **kwargs)
        self.settings.update(kwargs)
        self._status_value = "Queued"
        self._hatch_distance_native = None

        if len(args) == 1:
            obj = args[0]
            if hasattr(obj, "settings"):
                self.settings = dict(obj.settings)
            elif isinstance(obj, dict):
                self.settings.update(obj)

    def __repr__(self):
        return "HatchOpNode()"

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        if self.default:
            parts.append("✓")
        if self.passes_custom and self.passes != 1:
            parts.append("%dX" % self.passes)
        parts.append("Hatch")
        if self.speed is not None:
            parts.append("%gmm/s" % float(self.speed))
        if self.frequency is not None:
            parts.append("%gkHz" % float(self.frequency))
        if self.power is not None:
            parts.append("%gppi" % float(self.power))
        parts.append("%s" % self.color.hex)
        return " ".join(parts)

    def __copy__(self):
        return HatchOpNode(self)

    @property
    def bounds(self):
        if self._bounds_dirty:
            self._bounds = Node.union_bounds(self.flat(types=elem_ref_nodes))
        return self._bounds

    def default_map(self, default_map=None):
        default_map = super(HatchOpNode, self).default_map(default_map=default_map)
        default_map['element_type'] = "Hatch"
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
        # TODO: Implement time_estimate.
        hours, remainder = divmod(estimate, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "%s:%s:%s" % (
            int(hours),
            str(int(minutes)).zfill(2),
            str(int(seconds)).zfill(2),
        )

    def scale_native(self, matrix):
        distance_y = float(Length(self.settings.get("hatch_distance", "1mm")))
        transformed_vector = matrix.transform_vector([0, distance_y])
        self._hatch_distance_native = abs(
            complex(transformed_vector[0], transformed_vector[1])
        )

    def as_cutobjects(self, closed_distance=15, passes=1):
        """Generator of cutobjects for a particular operation."""
        settings = self.derive()
        # TODO: This currently applies Eulerian fill when it could just apply scanline fill.
        distance = self._hatch_distance_native
        angle = Angle.parse(settings.get("hatch_angle", "0deg"))
        efill = EulerianFill(distance)
        for node in self.children:
            if node.type == "reference":
                node = node.node
            if node.type == "elem path":
                path = abs(node.path)
                path.approximate_arcs_with_cubics()
            else:
                path = abs(Path(node.shape))
                path.approximate_arcs_with_cubics()
            settings["line_color"] = path.stroke
            for subpath in path.as_subpaths():
                sp = Path(subpath)
                if len(sp) == 0:
                    continue
                if angle is not None:
                    sp *= Matrix.rotate(angle)

                pts = [sp.point(i / 100.0, error=1e-4) for i in range(101)]
                efill += pts
        points = efill.get_fill()
        counter_rotate = Matrix.rotate(-angle)

        def split(points):
            pos = 0
            for i, pts in enumerate(points):
                if pts is None:
                    yield points[pos : i - 1]
                    pos = i + 1
            if pos != len(points):
                yield points[pos : len(points)]

        plot = PlotCut(settings=settings, passes=passes)
        for s in split(points):
            for p in s:
                x, y = counter_rotate.point_in_matrix_space((p.x, p.y))
                if p.value == "RUNG":
                    plot.plot_append(int(round(x)), int(round(y)), 1)
                if p.value == "EDGE":
                    plot.plot_append(int(round(x)), int(round(y)), 0)
        if len(plot):
            yield plot
