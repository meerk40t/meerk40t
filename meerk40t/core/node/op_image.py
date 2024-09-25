from math import isnan

from meerk40t.core.cutcode.rastercut import RasterCut
from meerk40t.core.elements.element_types import *
from meerk40t.core.node.node import Node
from meerk40t.core.parameters import Parameters
from meerk40t.core.units import MM_PER_INCH, UNITS_PER_INCH, UNITS_PER_MM, Length
from meerk40t.svgelements import Color, Path, Polygon


class ImageOpNode(Node, Parameters):
    """
    Default object defining any operation done on the laser.

    This is a Node of type "op image".
    """

    def __init__(self, settings=None, **kwargs):
        if settings is not None:
            settings = dict(settings)
        Parameters.__init__(self, settings, **kwargs)

        # Is this op out of useful bounds?
        self.dangerous = False
        self.coolant = 0  # Nothing to do (0/None = keep, 1=turn on, 2=turn off)
        self.stopop = True
        self.label = "Image"

        self.allowed_attributes = []
        super().__init__(type="op image", **kwargs)
        self._formatter = "{enabled}{pass}{element_type}{direction}{speed}mm/s @{power}"

    def __repr__(self):
        return "ImageOpNode()"

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Image"
        default_map["dpi"] = str(int(self.dpi))
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
        default_map["opstop"] = "<stop>" if self.stopop else ""
        default_map.update(self.settings)
        default_map["color"] = self.color.hexrgb if self.color is not None else ""
        default_map["colcode"] = self.color.hexrgb if self.color is not None else ""
        default_map["overscan"] = f"±{self.overscan}"
        # print(self.dangerous, self.stopop, self.raster_direction)
        default_map["percent"] = "100%"
        default_map["ppi"] = "default"
        if self.power is not None:
            default_map["percent"] = f"{self.power / 10.0:.0f}%"
            default_map["ppi"] = f"{self.power:.0f}"
        default_map["speed_mm_min"] = (
            "" if self.speed is None else f"{self.speed * 60:.0f}"
        )
        return default_map

    def drop(self, drag_node, modify=True):
        # Default routine for drag + drop for an op node - irrelevant for others...
        if hasattr(drag_node, "as_image"):
            if drag_node.has_ancestor("branch reg"):
                # We do not accept reg nodes.
                return False
            # Dragging element onto operation adds that element to the op.
            if modify:
                self.add_reference(drag_node, pos=0)
            return True
        elif drag_node.type == "reference":
            # Disallow drop of image refelems onto a Dot op.
            if not hasattr(drag_node.node, "as_image"):
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
        elif drag_node.type in ("file", "group") and not drag_node.has_ancestor(
            "branch reg"
        ):
            some_nodes = False
            for e in drag_node.flat(elem_nodes):
                # Add element to operation
                if hasattr(e, "as_image"):
                    if modify:
                        self.add_reference(e)
                    some_nodes = True
            return some_nodes
        return False

    def is_referenced(self, node):
        for e in self.children:
            if e is node:
                return True
            if hasattr(e, "node") and e.node is node:
                return True
        return False

    def valid_node_for_reference(self, node):
        if hasattr(node, "as_image"):
            return True
        else:
            return False

    def classify(self, node, fuzzy=False, fuzzydistance=100, usedefault=False):
        if self.is_referenced(node):
            # No need to add it again...
            return False, False, None

        feedback = []
        if hasattr(node, "as_image"):
            self.add_reference(node)
            # Have classified and no more classification are needed
            feedback.append("stroke")
            feedback.append("fill")
            return True, self.stopop, feedback
        return False, False, None

    def load(self, settings, section):
        settings.read_persistent_attributes(section, self)
        hexa = self.settings.get("hex_color")
        if hexa is not None:
            self.color = Color(hexa)
        self.updated()

    def save(self, settings, section):
        # Sync certain properties with self.settings
        for attr in ("label", "lock", "id"):
            if hasattr(self, attr) and attr in self.settings:
                self.settings[attr] = getattr(self, attr)
        if "hex_color" in self.settings:
            self.settings["hex_color"] = self.color.hexa

        settings.write_persistent_attributes(section, self)
        settings.write_persistent(section, "hex_color", self.color.hexa)
        settings.write_persistent_dict(section, self.settings)

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
                if not self.bidirectional:
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

        native_mm = abs(complex(*matrix.transform_vector([0, UNITS_PER_MM])))
        self.settings["native_mm"] = native_mm
        self.settings["native_speed"] = self.speed * native_mm
        self.settings["native_rapid_speed"] = self.rapid_speed * native_mm

        for node in self.children:

            def actual(image_node):
                def process_images():
                    if hasattr(image_node, "process_image"):
                        image_node._context = context
                        image_node.process_image()

                return process_images

            commands = plan.commands
            commands.append(actual(node))
        if matrix.value_scale_y() < 0:
            # Y is negative scale, flip raster_direction if needed
            if self.raster_direction == 0:
                self.raster_direction = 1
            elif self.raster_direction == 1:
                self.raster_direction = 0
        if matrix.value_scale_x() < 0:
            # X is negative scale, flip raster_direction if needed
            if self.raster_direction == 2:
                self.raster_direction = 3
            elif self.raster_direction == 3:
                self.raster_direction = 2

    def as_cutobjects(self, closed_distance=15, passes=1):
        """
        Generator of cutobjects for the image operation. This takes any image node children
        and converts them into rastercut cutobjects.
        """
        for image_node in self.children:
            cutcodes = []
            # Process each child. All settings are different for each child.
            if image_node.type == "reference":
                image_node = image_node.node
            if not hasattr(image_node, "as_image"):
                continue
            if getattr(image_node, "hidden", False):
                continue
            settings = self.derive()

            # Set overscan
            overscan = self.overscan
            if not isinstance(overscan, float):
                overscan = float(Length(overscan))

            # Set variables by direction
            if hasattr(image_node, "direction") and image_node.direction is not None:
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
            bidirectional = self.bidirectional

            # Set variables
            pil_image, bounds = image_node.as_image()
            offset_x = bounds[0]
            offset_y = bounds[1]

            # Get steps from individual images
            image_width, image_height = pil_image.size
            expected_width = bounds[2] - bounds[0]
            expected_height = bounds[3] - bounds[1]
            step_x = expected_width / image_width
            step_y = expected_height / image_height

            if horizontal:
                # Raster step is only along y for horizontal raster
                settings["raster_step_x"] = 0
                settings["raster_step_y"] = step_y
            else:
                # Raster step is only along x for vertical raster
                settings["raster_step_x"] = step_x
                settings["raster_step_y"] = 0

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
            inverted = False
            # Not used!
            if image_node.is_depthmap:
                # Make sure it's grayscale...
                if pil_image.mode != "L":
                    pil_image = pil_image.convert("L")

                gres = image_node.depth_resolution
                if gres < 0:
                    gres = 0
                if gres > 255:
                    gres = 255
                stepsize = 255 /  gres

                # no need for the filter as we have already moved every
                # pixel during preprocessing to either 255 or 0
                # def image_filter(pixel):
                #     # We ignore grayscale and move it into black-white = always on
                #     # The filter takes a pixel value between 0=black and 255=white
                #     # provides and creates a power value of 1.0 for black
                #     # and 0.0 for white
                #     if pixel == 255:
                #         return 0.0
                #     else:
                #         return 1.0
                image_filter = None

                if inverted:
                    delta = +1
                    start_pixel = 0
                else:
                    delta = -1
                    start_pixel = 255
                for gray in range(image_node.depth_resolution):
                    skip_pixel = int(start_pixel + gray * delta * stepsize)
                    if skip_pixel < 0:
                        skip_pixel = 0
                    if skip_pixel > 255:
                        skip_pixel = 255

                    def threshold_filter(pixel):
                        # This threshold filter function is defined to set pixels to white (255) if they are above
                        # or equal to the threshold, and to black (0) if they are below the threshold.
                        return 255 if pixel >= skip_pixel else 0

                    cleared_image = pil_image.point(threshold_filter)
                    extrema = cleared_image.getextrema()
                    # print (f"{skip_pixel}: extrema={extrema}")
                    if extrema == (0, 0):
                        # all black
                        # We will burn this
                        pass
                    elif extrema == (255, 255):
                        # all white
                        # we can skip this
                        # print (f"Skipping from {skip_pixel} as image is fully white")
                        continue

                    # Create Cut Object
                    cut = RasterCut(
                        image=cleared_image,
                        offset_x=offset_x,
                        offset_y=offset_y,
                        step_x=step_x,
                        step_y=step_y,
                        inverted=inverted,
                        bidirectional=bidirectional,
                        horizontal=horizontal,
                        start_minimum_y=start_on_top,
                        start_minimum_x=start_on_left,
                        overscan=overscan,
                        settings=settings,
                        passes=passes,
                        post_filter=image_filter,
                        label=f"Pass {gray}: cutoff={skip_pixel}"
                    )
                    cut.path = path
                    cut.original_op = self.type
                    cutcodes.append(cut)

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
                            image=cleared_image,
                            offset_x=offset_x,
                            offset_y=offset_y,
                            step_x=step_x,
                            step_y=step_y,
                            inverted=inverted,
                            bidirectional=bidirectional,
                            horizontal=horizontal,
                            start_minimum_y=start_on_top,
                            start_minimum_x=start_on_left,
                            overscan=overscan,
                            settings=settings,
                            passes=passes,
                            post_filter=image_filter,
                            label=f"Pass {gray}.2: cutoff={skip_pixel}"
                        )
                        cut.path = path
                        cut.original_op = self.type
                        cutcodes.append(cut)
            else:
                # Create Cut Object for regular image
                cut = RasterCut(
                    image=pil_image,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    step_x=step_x,
                    step_y=step_y,
                    inverted=inverted,
                    bidirectional=bidirectional,
                    horizontal=horizontal,
                    start_minimum_y=start_on_top,
                    start_minimum_x=start_on_left,
                    overscan=overscan,
                    settings=settings,
                    passes=passes,
                )
                cut.path = path
                cut.original_op = self.type
            cutcodes.append(cut)
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
                    inverted=inverted,
                    bidirectional=bidirectional,
                    horizontal=horizontal,
                    start_minimum_y=start_on_top,
                    start_minimum_x=start_on_left,
                    overscan=overscan,
                    settings=settings,
                    passes=passes,
                )
                cut.path = path
                cut.original_op = self.type
                cutcodes.append(cut)
            # Yield all generated cutcodes of this image
            for cut in cutcodes:
                yield cut