from copy import copy

from meerk40t.core.cutcode import RasterCut
from meerk40t.core.element_types import *
from meerk40t.core.node.node import Node
from meerk40t.core.parameters import Parameters
from meerk40t.core.units import Length
from meerk40t.svgelements import Color, Path, Polygon

MILS_IN_MM = 39.3701


class RasterOpNode(Node, Parameters):
    """
    Default object defining any raster operation done on the laser.

    This is a Node of type "op raster".
    """

    def __init__(self, *args, **kwargs):
        if "setting" in kwargs:
            kwargs = kwargs["settings"]
            if "type" in kwargs:
                del kwargs["type"]
        Node.__init__(self, type="op raster", **kwargs)
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
        return "RasterOp()"

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        if self.default:
            parts.append("✓")
        if self.passes_custom and self.passes != 1:
            parts.append("%dX" % self.passes)
        parts.append(f"Raster{self.dpi}")
        if self.speed is not None:
            parts.append(f"{float(self.speed):g}mm/s")
        if self.frequency is not None:
            parts.append(f"{float(self.frequency):g}kHz")
        if self.raster_swing:
            raster_dir = "-"
        else:
            raster_dir = "="
        if self.raster_direction == 0:
            raster_dir += "T2B"
        elif self.raster_direction == 1:
            raster_dir += "B2T"
        elif self.raster_direction == 2:
            raster_dir += "R2L"
        elif self.raster_direction == 3:
            raster_dir += "L2R"
        elif self.raster_direction == 4:
            raster_dir += "X"
        else:
            raster_dir += str(self.raster_direction)
        parts.append(raster_dir)
        if self.power is not None:
            parts.append(f"{float(self.power):g}ppi")
        parts.append(f"±{self.overscan}")
        if self.acceleration_custom:
            parts.append(f"a:{self.acceleration}")
        return " ".join(parts)

    def __copy__(self):
        return RasterOpNode(self)

    @property
    def bounds(self):
        if self._bounds_dirty:
            self._bounds = Node.union_bounds(self.flat(types=elem_ref_nodes))
        return self._bounds

    def default_map(self, default_map=None):
        default_map = super(RasterOpNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Raster"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["speed"] = "default"
        default_map["power"] = "default"
        default_map["frequency"] = "default"
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
        # TODO: Strictly speaking this is wrong. The time estimate is raster of non-svgimage objects.
        estimate = 0
        # for e in self.children:
        #     e = e.object
        #     if isinstance(e, SVGImage):
        #         try:
        #             step = e.raster_step
        #         except AttributeError:
        #             try:
        #                 step = int(e.values["raster_step"])
        #             except (KeyError, ValueError):
        #                 step = 1
        #         estimate += (e.image_width * e.image_height * step) / (
        #             MILS_IN_MM * self.speed
        #         )
        hours, remainder = divmod(estimate, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "%s:%s:%s" % (
            int(hours),
            str(int(minutes)).zfill(2),
            str(int(seconds)).zfill(2),
        )

    def scale_native(self, matrix):
        overscan = float(Length(self.settings.get("overscan", "1mm")))
        transformed_vector = matrix.transform_vector([0, overscan])
        self.overscan = abs(complex(transformed_vector[0], transformed_vector[1]))
        dpi = self.dpi
        oneinch_x = float(Length("1in"))
        oneinch_y = float(Length("1in"))
        transformed_step = matrix.transform_vector([oneinch_x, oneinch_y])
        self.raster_step_x = transformed_step[0] / dpi
        self.raster_step_y = transformed_step[1] / dpi

    def as_cutobjects(self, closed_distance=15, passes=1):
        """
        Generator of cutobjects for a raster operation. This takes any image node children
        and converts them into rastercut objects. These objects should have already been converted
        from vector shapes. However, the preference for raster shapes it to use the settings
        set on the operation rather than on the shape."""
        settings = self.derive()
        overscan = self.overscan
        if not isinstance(overscan, float):
            overscan = float(Length(overscan))
        settings["overscan"] = overscan

        direction = self.raster_direction
        for image_node in self.children:
            if image_node.type != "elem image":
                continue

            # Ensure actualization is done with raster values.
            osx = image_node.step_x
            osy = image_node.step_y
            image_node.step_x = self.raster_step_x
            image_node.step_y = self.raster_step_y
            if image_node.needs_actualization():
                image_node.make_actual()
            image_node.step_x = osx
            image_node.step_y = osy

            image = image_node.image
            matrix = image_node.matrix
            box = (
                matrix.value_trans_x(),
                matrix.value_trans_y(),
                matrix.value_trans_x() + image.width * self.raster_step_x,
                matrix.value_trans_y() + image.height * self.raster_step_y,
            )
            path = Path(
                Polygon(
                    (box[0], box[1]),
                    (box[0], box[3]),
                    (box[2], box[3]),
                    (box[2], box[1]),
                )
            )
            cut = RasterCut(
                image,
                matrix.value_trans_x(),
                matrix.value_trans_y(),
                settings=settings,
                passes=passes,
            )
            cut.path = path
            cut.original_op = self.type
            yield cut
            if direction == 4:
                # Add in optional crosshatch value.
                cut = RasterCut(
                    image,
                    matrix.value_trans_x(),
                    matrix.value_trans_y(),
                    crosshatch=True,
                    settings=settings,
                    passes=passes,
                )
                cut.path = path
                cut.original_op = self.type
                yield cut
