from copy import copy

from meerk40t.core.cutcode import PlotCut
from meerk40t.core.element_types import *
from meerk40t.core.node.elem_polyline import PolylineNode
from meerk40t.core.node.node import Node
from meerk40t.core.parameters import Parameters
from meerk40t.svgelements import Color, Path


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
            self._bounds_dirty = False
        return self._bounds

    def default_map(self, default_map=None):
        default_map = super(HatchOpNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Hatch"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["pass"] = (
            f"{self.passes}X " if self.passes_custom and self.passes != 1 else ""
        )
        default_map["penpass"] = (
            f"(p:{self.penbox_pass}) " if self.penbox_pass else ""
        )
        default_map["penvalue"] = (
            f"(v:{self.penbox_value}) " if self.penbox_value else ""
        )
        default_map["speed"] = "default"
        default_map["power"] = "default"
        default_map["frequency"] = "default"
        default_map["hatch_angle"] = "default"
        default_map["hatch_distance"] = "default"
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

    def classify(self, node):
        if not self.default and hasattr(node, "stroke") and node.stroke is not None:
            plain_color_op = abs(self.color)
            plain_color_node = abs(node.stroke)
            if plain_color_op != plain_color_node:
                return False
        if node.type in (
            "elem path",
        ):
            if node.path[-1].d().lower() == "z":
                self.add_reference(node)
                return True
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

    def copy_children_as_real(self, copy_node):
        for node in copy_node.children:
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

    @staticmethod
    def split(points):
        pos = 0
        for i, pts in enumerate(points):
            if pts is None:
                yield points[pos : i]
                pos = i + 1
        if pos != len(points):
            yield points[pos : len(points)]

    def preprocess(self, context, matrix, commands):
        """
        Preprocess hatch values

        @param context:
        @param matrix:
        @param commands:
        @return:
        """
        def hatch():
            settings = self.settings
            outlines = list()
            for node in self.children:
                path = node.as_path()
                path.approximate_arcs_with_cubics()
                self.settings["line_color"] = path.stroke
                for subpath in path.as_subpaths():
                    if len(subpath) == 0:
                        continue
                    sp = Path(subpath)
                    points = [sp.point(i / 100.0, error=1e-4) for i in range(101)]
                    outlines.append(points)
            self.remove_all_children()
            fills = list(context.match("hatch", suffix=True))
            penbox_pass = self.settings.get("penbox_pass")
            if penbox_pass is not None:
                try:
                    penbox_pass = context.elements.penbox[penbox_pass]
                except KeyError:
                    penbox_pass = None
            hatch_cache = dict()
            for p in range(self.implicit_passes):
                chain_settings = dict(settings)
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
                    hatches = list(algorithm(settings=chain_settings, outlines=outlines, matrix=matrix))
                    hatch_cache[key] = hatches

                for polyline in HatchOpNode.split(hatches):
                    node = PolylineNode(shape=Polyline(*polyline, **chain_settings))
                    node.settings.update(chain_settings)
                    self.add_node(node)

        if self.children:
            commands.append(hatch)

    def as_cutobjects(self, closed_distance=15, passes=1):
        """Generator of cutobjects for a particular operation."""
        for node in self.children:
            if node.type != "elem polyline":
                continue
            settings = node.settings
            plot = PlotCut(settings=settings)
            for p in node.shape:
                x, y = p
                plot.plot_append(int(round(x)), int(round(y)), 1)
            yield plot
