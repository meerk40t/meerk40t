from copy import copy

from meerk40t.core.cutcode import RasterCut
from meerk40t.core.element_types import *
from meerk40t.core.node.node import Node
from meerk40t.core.parameters import Parameters
from meerk40t.core.units import Length
from meerk40t.image.actualize import actualize
from meerk40t.svgelements import Color, Path, Polygon

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
        Node.__init__(self, type="op image", **kwargs)
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

    @property
    def bounds(self):
        if self._bounds_dirty:
            self._bounds = Node.union_bounds(self.flat(types=elem_ref_nodes))
            self._bounds_dirty = False
        return self._bounds

    def default_map(self, default_map=None):
        default_map = super(ImageOpNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Image"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["pass"] = (
            f"{self.passes}X " if self.passes_custom and self.passes != 1 else ""
        )
        if self.raster_swing:
            raster_swing = "-"
        else:
            raster_swing = "="
        if self.raster_direction == 0:
            raster_dir = "T2B"
        elif self.raster_direction == 1:
            raster_dir = "B2T"
        elif self.raster_direction == 2:
            raster_dir = "R2L"
        elif self.raster_direction == 3:
            raster_dir = "L2R"
        elif self.raster_direction == 4:
            raster_dir = "X"
        else:
            raster_dir = str(self.raster_direction)
        default_map["direction"] = f"{raster_swing}{raster_dir} "
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

    def copy_children_as_real(self, copy_node):
        for node in copy_node.children:
            self.add_node(copy(node.node))

    def time_estimate(self):
        estimate = 0
        for node in self.children:
            if node.type == "reference":
                node = node.node
            try:
                e = node.image
            except AttributeError:
                continue
            step = node.step_x
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

    def preprocess(self, context, matrix, commands):
        """
        Process the scale to native resolution done with the given matrix. In the case of image ops we are scaling
        the overscan length into usable native units.

        @param matrix:
        @return:
        """
        overscan = float(Length(self.settings.get("overscan", "1mm")))
        transformed_vector = matrix.transform_vector([0, overscan])
        self.overscan = abs(complex(transformed_vector[0], transformed_vector[1]))

        for node in self.children:
            dpi = node.dpi
            oneinch_x = context.device.physical_to_device_length("1in", 0)[0]
            oneinch_y = context.device.physical_to_device_length(0, "1in")[1]
            step_x = float(oneinch_x / dpi)
            step_y = float(oneinch_y / dpi)
            node.step_x = step_x
            node.step_y = step_y
            m1 = node.matrix
            # Transformation must be uniform to permit native rastering.
            if m1.a != step_x or m1.b != 0.0 or m1.c != 0.0 or m1.d != step_y:

                def actual(image_node, s_x, s_y):
                    def actualize_images():
                        image_node.image, image_node.matrix = actualize(
                            image_node.image, image_node.matrix, step_x=s_x, step_y=s_y
                        )
                        image_node.cache = None

                    return actualize_images

                commands.append(actual(node, step_x, step_y))
                break

    def as_cutobjects(self, closed_distance=15, passes=1):
        """
        Generator of cutobjects for the image operation. This takes any image node children
        and converts them into rastercut cutobjects.
        """
        for image_node in self.children:
            # Process each child. All settings are different for each child.

            if image_node.type != "elem image":
                continue
            settings = self.derive()

            # Set overscan
            overscan = self.overscan
            if not isinstance(overscan, float):
                overscan = float(Length(overscan))

            # Set steps
            step_x = image_node.step_x
            step_y = image_node.step_y

            # Set variables by direction
            if image_node.direction is not None:
                direction = image_node.direction
            else:
                direction = self.raster_direction
            horizontal = False
            start_on_left = False
            start_on_top = False
            if direction == 0 or direction == 4:
                horizontal = True
                start_on_top = True
            elif direction == 1:
                horizontal = True
                start_on_top = False
            elif direction == 2:
                horizontal = False
                start_on_left = False
            elif direction == 3:
                horizontal = False
                start_on_left = True
            bidirectional = bool(self.raster_swing)

            # Perform correct actualization
            if image_node.needs_actualization():
                image_node.make_actual()

            # Set variables
            matrix = image_node.matrix
            pil_image = image_node.image
            offset_x = matrix.value_trans_x()
            offset_y = matrix.value_trans_y()

            # Establish path
            min_x = offset_x
            min_y = offset_y
            max_x = offset_x + pil_image.width * step_x
            max_y = offset_y + pil_image.height * step_y
            path = Path(
                Polygon(
                    (min_x, min_y),
                    (min_x, max_y),
                    (max_x, max_y),
                    (max_x, min_y),
                )
            )

            # Create Cut Object
            cut = RasterCut(
                image=pil_image,
                offset_x=offset_x,
                offset_y=offset_y,
                step_x=step_x,
                step_y=step_y,
                inverted=False,
                bidirectional=bidirectional,
                horizontal=horizontal,
                start_on_top=start_on_top,
                start_on_left=start_on_left,
                overscan=overscan,
                settings=settings,
                passes=passes,
            )
            cut.path = path
            cut.original_op = self.type
            yield cut
            if direction == 4:
                # Create optional crosshatch cut
                horizontal = False
                start_on_left = False
                cut = RasterCut(
                    image=pil_image,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    step_x=step_x,
                    step_y=step_y,
                    inverted=False,
                    bidirectional=bidirectional,
                    horizontal=horizontal,
                    start_on_top=start_on_top,
                    start_on_left=start_on_left,
                    overscan=overscan,
                    settings=settings,
                    passes=passes,
                )
                cut.path = path
                cut.original_op = self.type
                yield cut
