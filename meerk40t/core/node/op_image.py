from copy import copy
from math import isnan

from meerk40t.core.cutcode.rastercut import RasterCut
from meerk40t.core.element_types import *
from meerk40t.core.node.node import Node
from meerk40t.core.parameters import Parameters
from meerk40t.core.units import MM_PER_INCH, UNITS_PER_INCH, Length
from meerk40t.svgelements import Color, Path, Polygon


class ImageOpNode(Node, Parameters):
    """
    Default object defining any operation done on the laser.

    This is a Node of type "op image".
    """

    def __init__(self, *args, id=None, label=None, lock=False, **kwargs):
        Node.__init__(self, type="op image", id=id, label=label, lock=lock)
        Parameters.__init__(self, None, **kwargs)
        self._formatter = "{enabled}{pass}{element_type}{direction}{speed}mm/s @{power}"

        if len(args) == 1:
            obj = args[0]
            if hasattr(obj, "settings"):
                self.settings = dict(obj.settings)
            elif isinstance(obj, dict):
                self.settings.update(obj)
        # Which elements can be added to an operation (manually via DND)?
        self._allowed_elements_dnd = ("elem image",)
        # Which elements do we consider for automatic classification?
        self._allowed_elements = ("elem image",)

        # Is this op out of useful bounds?
        self.dangerous = False
        self.stopop = True
        self.allowed_attributes = []

    def __repr__(self):
        return "ImageOpNode()"

    def __copy__(self):
        return ImageOpNode(self)

    # def is_dangerous(self, minpower, maxspeed):
    #     result = False
    #     if maxspeed is not None and self.speed > maxspeed:
    #         result = True
    #     if minpower is not None and self.power < minpower:
    #         result = True
    #     self.dangerous = result

    def default_map(self, default_map=None):
        default_map = super(ImageOpNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Image"
        default_map["dpi"] = str(self.dpi)
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
        default_map["opstop"] = "<stop>" if self.stopop else ""
        default_map.update(self.settings)
        default_map["color"] = self.color.hexrgb if self.color is not None else ""
        default_map["colcode"] = self.color.hexrgb if self.color is not None else ""
        default_map["overscan"] = f"±{self.overscan}"
        # print(self.dangerous, self.stopop, self.raster_direction)
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

    def valid_node_for_reference(self, node):
        if node.type in self._allowed_elements_dnd:
            return True
        else:
            return False

    def classify(self, node, fuzzy=False, fuzzydistance=100, usedefault=False):
        feedback = []
        if node.type in self._allowed_elements:
            self.add_reference(node)
            # Have classified and no more classification are needed
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
        """
        The scanlines would equal "(e.height * 1000) / dpi" but our images are pre-actualized.

        @return:
        """
        estimate = 0
        for node in self.children:
            if node.type == "reference":
                node = node.node
            try:
                e = node.image
                dpi = node.dpi
            except AttributeError:
                continue
            min_x, min_y, max_x, max_y = node.bounds
            width_in_inches = (max_x - min_x) / UNITS_PER_INCH
            height_in_inches = (max_y - min_y) / UNITS_PER_INCH
            speed_in_per_s = self.speed / MM_PER_INCH
            if self.raster_direction in (0, 1, 4):
                scanlines = height_in_inches * dpi
                if self.raster_swing:
                    scanlines *= 2
                estimate += (
                    scanlines * width_in_inches / speed_in_per_s
                    + height_in_inches / speed_in_per_s
                )
                this_len = scanlines * width_in_inches + height_in_inches
                estimate += this_len / speed_in_per_s
                # print (f"Horizontal scanlines: {scanlines}, Length: {this_len:.1f}")
            if self.raster_direction in (2, 3, 4):
                scanlines = width_in_inches * dpi
                if self.raster_swing:
                    scanlines *= 2
                this_len = scanlines * height_in_inches + width_in_inches
                estimate += this_len / speed_in_per_s
                # print (f"Vertical scanlines: {scanlines}, Length: {this_len:.1f}")

        if self.passes_custom and self.passes != 1:
            estimate *= max(self.passes, 1)

        if isnan(estimate):
            estimate = 0

        hours, remainder = divmod(estimate, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"

    def preprocess(self, context, matrix, plan):
        """
        Process the scale to native resolution done with the given matrix. In the case of image ops we are scaling
        the overscan length into usable native units.

        @param context:
        @param matrix:
        @param plan:
        @return:
        """
        overscan = float(Length(self.settings.get("overscan", "1mm")))
        transformed_vector = matrix.transform_vector([0, overscan])
        self.overscan = abs(complex(transformed_vector[0], transformed_vector[1]))

        for node in self.children:

            def actual(image_node):
                def process_images():
                   if hasattr(image_node, "process_image"):
                        image_node._context = context
                        image_node.process_image()

                return process_images

            commands = plan.commands
            commands.append(actual(node))

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

            # Get steps from individual images
            step_x = image_node.step_x
            step_y = image_node.step_y

            settings["raster_step_x"] = step_x
            settings["raster_step_x"] = step_y

            # Set variables
            matrix = image_node.active_matrix
            pil_image = image_node.active_image
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
