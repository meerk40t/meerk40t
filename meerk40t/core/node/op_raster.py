from copy import copy
from math import isnan

from meerk40t.core.cutcode.rastercut import RasterCut
from meerk40t.core.cutplan import CutPlanningFailedError
from meerk40t.core.element_types import *
from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.node.node import Node
from meerk40t.core.parameters import Parameters
from meerk40t.core.units import MM_PER_INCH, UNITS_PER_INCH, UNITS_PER_MM, Length
from meerk40t.svgelements import Color, Matrix, Path, Polygon


class RasterOpNode(Node, Parameters):
    """
    Default object defining any raster operation done on the laser.

    This is a Node of type "op raster".
    """

    def __init__(self, *args, id=None, label=None, lock=False, **kwargs):
        Node.__init__(self, type="op raster", id=id, label=label, lock=lock)
        Parameters.__init__(self, None, **kwargs)
        self._formatter = (
            "{enabled}{pass}{element_type}{direction}{speed}mm/s @{power} {color}"
        )

        if len(args) == 1:
            obj = args[0]
            if hasattr(obj, "settings"):
                self.settings = dict(obj.settings)
            elif isinstance(obj, dict):
                self.settings.update(obj)
        self._allowed_elements_dnd = (
            "elem ellipse",
            "elem path",
            "elem polyline",
            "elem rect",
            "elem line",
            "elem text",
            "elem image",
        )
        # Which elements do we consider for automatic classification?
        self._allowed_elements = (
            "elem ellipse",
            "elem path",
            "elem polyline",
            "elem rect",
            "elem line",
            "elem text",
            #            "elem image",
        )
        # To which attributes do the classification color check respond
        # Can be extended / reduced by add_color_attribute / remove_color_attribute
        # An empty set indicates all nodes will be allowed
        self.allowed_attributes = []
        # self.allowed_attributes.append("fill")
        # Is this op out of useful bounds?
        self.dangerous = False
        self.stopop = False
        if label is None:
            self.label = "Raster"
        else:
            self.label = label

    def __repr__(self):
        return "RasterOp()"

    def __copy__(self):
        return RasterOpNode(self)

    # def is_dangerous(self, minpower, maxspeed):
    #     result = False
    #     if maxspeed is not None and self.speed > maxspeed:
    #         result = True
    #     if minpower is not None and self.power < minpower:
    #         result = True
    #     self.dangerous = result

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Raster"
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
        if self.bidirectional:
            raster_swing = "="
        else:
            raster_swing = "-"
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
        default_map["overscan"] = f"±{self.overscan}"
        return default_map

    def drop(self, drag_node, modify=True):
        count = 0
        existing = 0
        result = False
        if (
            drag_node.type.startswith("elem")
            and not drag_node._parent.type == "branch reg"
        ):
            existing += 1
            # if drag_node.type == "elem image":
            #     return False
            # Dragging element onto operation adds that element to the op.
            if modify:
                count += 1
                self.add_reference(drag_node, pos=0)
            result = True
        elif drag_node.type == "reference":
            # # Disallow drop of image refelems onto a Dot op.
            # if drag_node.type == "elem image":
            #     return False
            # Move a refelem to end of op.
            existing += 1
            if modify:
                count += 1
                self.append_child(drag_node)
            result = True
        elif drag_node.type in op_nodes:
            # Move operation to a different position.
            if modify:
                self.insert_sibling(drag_node)
            result = True
        elif drag_node.type in ("file", "group"):
            some_nodes = False
            for e in drag_node.flat(types=elem_nodes):
                existing += 1
                # Disallow drop of image elems onto a Dot op.
                # if drag_node.type == "elem image":
                #     continue
                # Add element to operation
                if modify:
                    count += 1
                    self.add_reference(e)
                some_nodes = True
            result = some_nodes
        return result

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
        if node.type in self._allowed_elements_dnd:
            return True
        else:
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
                else:  # empty ? Anything with either a solid fill or a plain white stroke goes
                    if self.valid_node_for_reference(node):
                        addit = False
                        if node.type == "elem image":
                            addit = True
                        if hasattr(node, "fill"):
                            if node.fill is not None and node.fill.argb is not None:
                                # if matching_color(node.fill, Color("white")):
                                #     addit = True
                                # if matching_color(node.fill, Color("black")):
                                #     addit = True
                                addit = True
                                feedback.append("fill")
                        if hasattr(node, "stroke"):
                            if node.stroke is not None and node.stroke.argb is not None:
                                if matching_color(node.stroke, Color("white")):
                                    addit = True
                                    feedback.append("stroke")
                                if matching_color(node.stroke, Color("black")):
                                    addit = True
                                    feedback.append("stroke")
                        if addit:
                            self.add_reference(node)
                            # Have classified but more classification might be needed
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
        dpi = self.dpi
        # Get fresh union bounds, may not have been marked dirty on additions or removals.
        min_x, min_y, max_x, max_y = Node.union_bounds(self.flat(types=elem_ref_nodes))
        width_in_inches = (max_x - min_x) / UNITS_PER_INCH
        height_in_inches = (max_y - min_y) / UNITS_PER_INCH
        speed_in_per_s = self.speed / MM_PER_INCH
        if self.raster_direction in (0, 1, 4):
            scanlines = height_in_inches * dpi
            if not self.bidirectional:
                scanlines *= 2
            this_len = scanlines * width_in_inches + height_in_inches
            estimate += this_len / speed_in_per_s
            # print (f"Horizontal scanlines: {scanlines}, Length: {this_len:.1f}")
        if self.raster_direction in (2, 3, 4):
            scanlines = width_in_inches * dpi
            if not self.bidirectional:
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
        Preprocess is called during job planning. This should be called with
        the native matrix.

        @param context:
        @param matrix:
        @param plan:
        @return:
        """
        commands = plan.commands
        native_mm = abs(complex(*matrix.transform_vector([0, UNITS_PER_MM])))
        self.settings["native_mm"] = native_mm
        self.settings["native_speed"] = self.speed * native_mm
        self.settings["native_rapid_speed"] = self.rapid_speed * native_mm

        overscan = float(Length(self.settings.get("overscan", "1mm")))
        transformed_vector = matrix.transform_vector([0, overscan])
        self.overscan = abs(complex(transformed_vector[0], transformed_vector[1]))
        if len(self.children) == 0:
            return

        make_raster = context.lookup("render-op/make_raster")
        if make_raster is None:

            def strip_rasters():
                self.remove_all_children()

            commands.append(strip_rasters)
            return

        def make_image():
            """
            Nested function to be added to commands and to call make_raster on the given elements.
            @return:
            """
            # Calculate raster steps from DPI device context
            step_x, step_y = context.device.dpi_to_steps(self.dpi, matrix=matrix)
            bounds = self.paint_bounds
            img_mx = Matrix.scale(step_x, step_y)
            data = list(self.flat())
            reverse = context.elements.classify_reverse
            if reverse:
                data = list(reversed(data))
            try:
                image = make_raster(data, bounds=bounds, step_x=step_x, step_y=step_y)
                if step_x > 0:
                    img_mx.post_translate(bounds[0], 0)
                else:
                    img_mx.post_translate(bounds[2], 0)
                if step_y > 0:
                    img_mx.post_translate(0, bounds[1])
                else:
                    img_mx.post_translate(0, bounds[3])

            except (AssertionError, MemoryError) as e:
                raise CutPlanningFailedError("Raster too large.") from e
            image = image.convert("L")
            image_node = ImageNode(image=image, matrix=img_mx)
            self.children.clear()
            self.add_node(image_node)
            image_node.step_x = step_x
            image_node.step_y = step_y
            image_node.process_image()

        commands.append(make_image)

    def as_cutobjects(self, closed_distance=15, passes=1):
        """
        Generator of cutobjects for a raster operation. This takes any image node children
        and converts them into rastercut objects. These objects should have already been converted
        from vector shapes.

        The preference for raster shapes is to use the settings set on this operation rather than on the image-node.
        """
        if len(self.children) == 0:
            return
        settings = self.derive()

        # Set overscan
        overscan = self.overscan
        if not isinstance(overscan, float):
            overscan = float(Length(overscan))
        settings["overscan"] = overscan

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
        bidirectional = self.bidirectional

        for image_node in self.children:
            # Process each child. Some core settings are the same for each child.

            if image_node.type != "elem image":
                continue

            step_x = image_node.step_x
            step_y = image_node.step_y

            if horizontal:
                # Raster step is only along y for horizontal raster
                settings["raster_step_x"] = 0
                settings["raster_step_y"] = step_y
            else:
                # Raster step is only along x for vertical raster
                settings["raster_step_x"] = step_x
                settings["raster_step_y"] = 0

            # Perform correct actualization
            image_node.process_image()

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
                horizontal = not horizontal
                settings = dict(settings)
                if horizontal:
                    # Raster step is only along y for horizontal raster
                    settings["raster_step_x"] = 0
                    settings["raster_step_y"] = step_y
                else:
                    # Raster step is only along x for vertical raster
                    settings["raster_step_x"] = step_x
                    settings["raster_step_y"] = 0
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
