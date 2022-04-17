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


class ImageOpNode(Node, Parameters):
    """
    Default object defining any operation done on the laser.

    This is a Node of type "op image".
    """

    def __init__(self, *args, **kwargs):
        if "setting" in kwargs:
            kwargs = kwargs["settings"]
            if "type" in kwargs:
                del kwargs["type"]
        Node.__init__(self, *args, type="op image", **kwargs)
        Parameters.__init__(self, None, **kwargs)
        self.settings.update(kwargs)
        self._status_value = "Queued"

        if len(args) == 1:
            obj = args[0]
            if isinstance(obj, SVGElement):
                self.add(obj, type="ref elem")
            elif hasattr(obj, "settings"):
                self.settings = dict(obj.settings)
            elif isinstance(obj, dict):
                self.settings.update(obj)

    def __repr__(self):
        return "ImageOpNode()"

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        if self.default:
            parts.append("✓")
        if self.passes_custom and self.passes != 1:
            parts.append("%dX" % self.passes)
        parts.append("Image")
        if self.speed is not None:
            parts.append("%gmm/s" % float(self.speed))
        if self.frequency is not None:
            parts.append("%gkHz" % float(self.frequency))
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
            raster_dir += "%d" % self.raster_direction
        parts.append(raster_dir)
        if self.power is not None:
            parts.append("%gppi" % float(self.power))
        parts.append("±{overscan}".format(overscan=self.overscan))
        parts.append("%s" % self.color.hex)
        if self.acceleration_custom:
            parts.append("a:%d" % self.acceleration)
        return " ".join(parts)

    def __copy__(self):
        return ImageOpNode(self)

    def drop(self, drag_node):
        if drag_node.type.startswith("elem"):
            if drag_node.type == "elem image":
                return False
            # Dragging element onto operation adds that element to the op.
            self.add(drag_node.object, type="ref elem", pos=0)
            return True
        elif drag_node.type == "ref elem":
            # Disallow drop of image refelems onto a Dot op.
            if drag_node.type == "elem image":
                return False
            # Move an refelem to end of op.
            self.append_child(drag_node)
            return True
        elif drag_node.type in op_nodes:
            # Move operation to a different position.
            self.insert_sibling(drag_node)
            return True
        elif drag_node.type in ("file", "group"):
            some_nodes = False
            for e in drag_node.flat("elem"):
                # Add element to operation
                self.add(e.object, type="ref elem")
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
            self.add(element.object, type="ref elem")

    def deep_copy_children(self, obj):
        for element in obj.children:
            self.add(copy(element.object), type=element.type)

    def time_estimate(self):
        estimate = 0
        for e in self.children:
            e = e.object
            if isinstance(e, SVGImage):
                try:
                    step = e.raster_step
                except AttributeError:
                    try:
                        step = int(e.values["raster_step"])
                    except (KeyError, ValueError):
                        step = 1
                estimate += (e.image_width * e.image_height * step) / (
                    MILS_IN_MM * self.speed
                )
        hours, remainder = divmod(estimate, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "%s:%s:%s" % (
            int(hours),
            str(int(minutes)).zfill(2),
            str(int(seconds)).zfill(2),
        )

    def as_cutobjects(self, closed_distance=15, passes=1):
        """Generator of cutobjects for a particular operation."""
        for svg_image in self.children:
            svg_image = svg_image.object
            if not isinstance(svg_image, SVGImage):
                continue
            settings = self.derive()
            try:
                settings["raster_step"] = int(svg_image.values["raster_step"])
            except KeyError:
                # This overwrites any step that may have been defined in settings.
                settings[
                    "raster_step"
                ] = 1  # If raster_step is not set image defaults to 1.
            if settings["raster_step"] <= 0:
                settings["raster_step"] = 1

            try:
                settings["raster_direction"] = int(svg_image.values["raster_direction"])
            except KeyError:
                pass
            step = settings["raster_step"]
            matrix = svg_image.transform
            pil_image = svg_image.image
            pil_image, matrix = actualize(pil_image, matrix, step)
            box = (
                matrix.value_trans_x(),
                matrix.value_trans_y(),
                matrix.value_trans_x() + pil_image.width * step,
                matrix.value_trans_y() + pil_image.height * step,
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
                pil_image,
                matrix.value_trans_x(),
                matrix.value_trans_y(),
                settings=settings,
                passes=passes,
            )
            cut.path = path
            cut.original_op = self.type
            yield cut
            if settings["raster_direction"] == 4:
                cut = RasterCut(
                    pil_image,
                    matrix.value_trans_x(),
                    matrix.value_trans_y(),
                    crosshatch=True,
                    settings=settings,
                    passes=passes,
                )
                cut.path = path
                cut.original_op = self.type
                yield cut
