from copy import copy

from meerk40t.core.cutcode import RasterCut
from meerk40t.core.cutplan import CutPlanningFailedError
from meerk40t.core.element_types import *
from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.node.node import Node
from meerk40t.core.parameters import Parameters
from meerk40t.core.units import Length
from meerk40t.image.actualize import actualize
from meerk40t.svgelements import Color, Matrix, Path, Polygon

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
            self._bounds_dirty = False
        return self._bounds

    def default_map(self, default_map=None):
        default_map = super(RasterOpNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Raster"
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

    def copy_children_as_real(self, copy_node):
        for node in copy_node.children:
            self.add_node(copy(node.node))

    def time_estimate(self):
        estimate = 0
        for node in self.children:
            if node.type != "elem image":
                continue
            step_y = node.step_x
            step_x = node.step_y
            estimate += (
                node.image.width * node.image.height * step_x / MILS_IN_MM * self.speed
            )
            estimate += node.image.height * step_y / MILS_IN_MM * self.speed
        hours, remainder = divmod(estimate, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "%s:%s:%s" % (
            int(hours),
            str(int(minutes)).zfill(2),
            str(int(seconds)).zfill(2),
        )

    def preprocess(self, context, matrix, commands):
        """
        Preprocess is called during job planning. This should be called with
        the native matrix.

        @param context:
        @param matrix:
        @param commands:
        @return:
        """
        overscan = float(Length(self.settings.get("overscan", "1mm")))
        transformed_vector = matrix.transform_vector([0, overscan])
        self.overscan = abs(complex(transformed_vector[0], transformed_vector[1]))
        dpi = self.dpi
        oneinch_x = float(Length("1in"))
        oneinch_y = float(Length("1in"))
        transformed_step = matrix.transform_vector([oneinch_x, oneinch_y])
        self.raster_step_x = transformed_step[0] / dpi
        self.raster_step_y = transformed_step[1] / dpi

        if len(self.children) == 0:
            return
        if len(self.children) == 1 and self.children[0].type == "elem image":
            dpi = float(self.settings.get("dpi", 500))
            oneinch_x = context.device.physical_to_device_length("1in", 0)[0]
            oneinch_y = context.device.physical_to_device_length(0, "1in")[1]
            step_x = float(oneinch_x / dpi)
            step_y = float(oneinch_y / dpi)
            self.settings["raster_step_x"] = step_x
            self.settings["raster_step_y"] = step_y
            node = self.children[0]
            node.step_x = step_x
            node.step_y = step_y
            m = node.matrix
            # Transformation must be uniform to permit native rastering.
            if m.a != step_x or m.b != 0.0 or m.c != 0.0 or m.d != step_y:

                def actualize_raster_image(image_node, s_x, s_y):
                    def actualize_raster_image_node():
                        image_node.image, image_node.matrix = actualize(
                            image_node.image, image_node.matrix, step_x=s_x, step_y=s_y
                        )
                        image_node.cache = None

                    return actualize_raster_image_node

                commands.append(actualize_raster_image(node, step_x, step_y))
            return

        make_raster = context.lookup("render-op/make_raster")
        if make_raster is None:

            def strip_rasters():
                self.remove_node()

            commands.append(strip_rasters)
            return

        def make_image():
            step_x = self.raster_step_x
            step_y = self.raster_step_y
            bounds = self.bounds
            try:
                image = make_raster(
                    list(self.flat()), bounds=bounds, step_x=step_x, step_y=step_y
                )
            except AssertionError:
                raise CutPlanningFailedError("Raster too large.")
            if image.width == 1 and image.height == 1:
                # TODO: Solve this is a less kludgy manner. The call to make the image can fail the first time
                #  around because the renderer is what sets the size of the text. If the size hasn't already
                #  been set, the initial bounds are wrong.
                bounds = self.bounds
                try:
                    image = make_raster(
                        list(self.flat()), bounds=bounds, step_x=step_x, step_y=step_y
                    )
                except AssertionError:
                    raise CutPlanningFailedError("Raster too large.")
            image = image.convert("L")
            matrix = Matrix.scale(step_x, step_y)
            matrix.post_translate(bounds[0], bounds[1])
            image_node = ImageNode(
                image=image, matrix=matrix, step_x=step_x, step_y=step_y
            )
            self.children.clear()
            self.add_node(image_node)

        commands.append(make_image)

    def as_cutobjects(self, closed_distance=15, passes=1):
        """
        Generator of cutobjects for a raster operation. This takes any image node children
        and converts them into rastercut objects. These objects should have already been converted
        from vector shapes.

        The preference for raster shapes is to use the settings set on this operation rather than on the image-node.
        """
        settings = self.derive()

        # Set overscan
        overscan = self.overscan
        if not isinstance(overscan, float):
            overscan = float(Length(overscan))
        settings["overscan"] = overscan

        # Set steps
        step_x = self.raster_step_x
        step_y = self.raster_step_y

        # Set variables by direction
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

        for image_node in self.children:
            # Process each child. Some core settings are the same for each child.

            if image_node.type != "elem image":
                continue

            # Perform correct actualization
            osx = image_node.step_x
            osy = image_node.step_y
            image_node.step_x = step_x
            image_node.step_y = step_y
            if image_node.needs_actualization():
                image_node.make_actual()
            image_node.step_x = osx
            image_node.step_y = osy

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
