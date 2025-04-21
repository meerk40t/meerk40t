"""
ImageOpNode defines an operation for processing images in the laser cutting application.

This class represents a node of type "op image" and manages the settings and behaviors
associated with image operations, including image processing, classification, and
time estimation for operations. It allows for the manipulation of image attributes,
the application of raster cuts, and the handling of drag-and-drop functionality for
image nodes.

Args:
    settings (dict, optional): Initial settings for the operation.
    **kwargs: Additional keyword arguments for node initialization.

Methods:
    classify(node, fuzzy=False, fuzzydistance=100, usedefault=False): Classifies the given node based on its attributes.
    load(settings, section): Loads settings from a specified section.
    save(settings, section): Saves the current settings to a specified section.
    time_estimate(): Estimates the time required for the operation based on its parameters.
    preprocess(context, matrix, plan): Preprocesses the operation for execution based on the provided context and matrix.
    as_cutobjects(closed_distance=15, passes=1): Generates cut objects for the image operation.
"""
from copy import copy
from math import isnan
from meerk40t.constants import (
    RASTER_T2B,
    RASTER_B2T,
    RASTER_R2L,
    RASTER_L2R,
    RASTER_HATCH,
    RASTER_GREEDY_H,
    RASTER_GREEDY_V,
    RASTER_CROSSOVER,
    RASTER_SPIRAL,
)
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
        self.stopop = True
        self.label = "Image"
        self.overrule_dpi = False
        self._allowed_elements_dnd = ("elem image",)
        self._allowed_elements = ("elem image",)
        self.consider_laserspot = False
        self._spot_in_device_units = 0
        self._instructions = {}

        self.allowed_attributes = []
        super().__init__(type="op image", **kwargs)
        self._formatter = "{enabled}{pass}{element_type}{direction}{speed}mm/s @{power}"
        # They might come from a svg read, but shouldnt be in settings
        for attrib in ("lock", "dangerous", "use_grayscale", "consider_laserspot", "overrule_dpi"):
            if attrib in self.settings:
                del self.settings[attrib]

    def __repr__(self):
        return "ImageOpNode()"

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Image"
        default_map["dpi"] = str(int(self.dpi)) if self.overrule_dpi else ""
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
        if self.raster_direction == RASTER_T2B:
            raster_dir = "T2B"
        elif self.raster_direction == RASTER_B2T:
            raster_dir = "B2T"
        elif self.raster_direction == RASTER_R2L:
            raster_dir = "R2L"
        elif self.raster_direction == RASTER_L2R:
            raster_dir = "L2R"
        elif self.raster_direction == RASTER_HATCH:
            raster_dir = "X"
        elif self.raster_direction == RASTER_CROSSOVER:
            raster_dir = "|-|-"
        elif self.raster_direction == RASTER_GREEDY_H:
            raster_dir = "GR-"
        elif self.raster_direction == RASTER_GREEDY_V:
            raster_dir = "GR|"
        elif self.raster_direction == RASTER_SPIRAL:
            raster_dir = "(.)"
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

    def can_drop(self, drag_node):
        # Default routine for drag + drop for an op node - irrelevant for others...
        if drag_node.has_ancestor("branch reg"):
            # Will be dealt with in elements -
            # we don't implement a more sophisticated routine here
            return False
        if hasattr(drag_node, "as_image"):
            return True
        elif drag_node.type == "reference" and hasattr(drag_node.node, "as_image"):
            return True
        elif drag_node.type in op_nodes:
            # Move operation to a different position.
            return True
        elif drag_node.type in ("file", "group"):
            return not any(e.has_ancestor("branch reg") for e in drag_node.flat(elem_nodes))
        return False

    def drop(self, drag_node, modify=True, flag=False):
        # Default routine for drag + drop for an op node - irrelevant for others...
        if hasattr(drag_node, "as_image"):
            if drag_node.has_ancestor("branch reg"):
                # We do not accept reg nodes.
                return False
            # Dragging element onto operation adds that element to the op.
            if modify:
                self.add_reference(drag_node, pos=None if flag else 0)
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
                if self.overrule_dpi and self.dpi:
                    dpi = self.dpi
                else:
                    dpi = node.dpi
            except AttributeError:
                continue
            min_x, min_y, max_x, max_y = node.bounds
            width_in_inches = (max_x - min_x) / UNITS_PER_INCH
            height_in_inches = (max_y - min_y) / UNITS_PER_INCH
            speed_in_per_s = self.speed / MM_PER_INCH
            if self.raster_direction in (
                RASTER_T2B, RASTER_B2T, RASTER_HATCH, 
                RASTER_GREEDY_H, RASTER_CROSSOVER, RASTER_SPIRAL,
            ):
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
            if self.raster_direction in (RASTER_L2R, RASTER_R2L, RASTER_HATCH, RASTER_GREEDY_V):
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
        self._spot_in_device_units = 0
        self._instructions = {}
        if hasattr(context, "device"):
            if hasattr(context.device, "get_raster_instructions"):
                self._instructions = context.device.get_raster_instructions()

            if self.consider_laserspot:
                try:
                    laserspot = getattr(context.device, "laserspot", "0.3mm")
                    spot = 2 * float(Length(laserspot)) / ( context.device.view.native_scale_x + context.device.view.native_scale_y)
                    # print (f"Laserpot in device units: {spot:.2f} [{laserspot.length_mm}], scale: {context.device.view.native_scale_x + context.device.view.native_scale_y:.2f}")
                except (ValueError, AttributeError):
                    spot = 0
                self._spot_in_device_units = spot

        try:
            overscan = float(Length(self.overscan))
        except ValueError:
            overscan = 0
        transformed_vector = matrix.transform_vector([0, overscan])
        self.overscan = abs(complex(transformed_vector[0], transformed_vector[1]))

        native_mm = abs(complex(*matrix.transform_vector([0, UNITS_PER_MM])))
        self.settings["native_mm"] = native_mm
        self.settings["native_speed"] = self.speed * native_mm
        self.settings["native_rapid_speed"] = self.rapid_speed * native_mm
        for node in self.children:
            if self.overrule_dpi and self.dpi:
                node.dpi = self.dpi

            def actual(image_node):
                def process_images():
                    if hasattr(image_node, "process_image"):
                        if image_node._keyhole_geometry is not None:
                            image_node._keyhole_image = None
                            image_node._cache = None
                            image_node._keyhole_geometry.transform(matrix)
                        image_node._context = context
                        image_node.process_image()

                return process_images

            commands = plan.commands
            commands.append(actual(node))

        msx = matrix.value_scale_x()
        msy = matrix.value_scale_y()
        rotated = False
        negative_scale_x = msx < 0
        negative_scale_y = msy < 0
        if msx == 0 and msy == 0:
            # Rotated view
            rotated = True
            p1a = matrix.point_in_matrix_space((0, 0))
            p2a = matrix.point_in_matrix_space((1, 0))
            dx = p1a.x - p2a.x
            dy = p1a.y - p2a.y
            negative_scale_x = bool(dy < 0) if dx == 0 else bool(dx < 0)
            negative_scale_y = False if dx == 0 else bool(dy < 0)
        if rotated:
            mapping = {
                RASTER_T2B: RASTER_L2R,
                RASTER_B2T: RASTER_R2L,
                RASTER_R2L: RASTER_B2T,
                RASTER_L2R: RASTER_T2B,
                RASTER_GREEDY_H: RASTER_GREEDY_V,
                RASTER_GREEDY_V: RASTER_GREEDY_H,
            }
            if self.raster_direction in mapping:
                self.raster_direction = mapping[self.raster_direction]
        if negative_scale_y:
            # Y is negative scale, flip raster_direction if needed
            self.raster_preference_top = not self.raster_preference_top
            if self.raster_direction == RASTER_T2B:
                self.raster_direction = RASTER_B2T
            elif self.raster_direction == RASTER_B2T:
                self.raster_direction = RASTER_T2B
        if negative_scale_x:
            # X is negative scale, flip raster_direction if needed
            self.raster_preference_left = not self.raster_preference_left
            if self.raster_direction == RASTER_R2L:
                self.raster_direction = RASTER_L2R
            elif self.raster_direction == RASTER_L2R:
                self.raster_direction = RASTER_R2L

        # Look for registered raster (image) preprocessors,
        # these are routines that take one image as parameter
        # and deliver a set of (result image, method (aka raster_direction) )
        # that will be dealt with independently
        # The registered datastructure is (rasterid, description, method)
        def call_me(method):
            def handler():
                method(self)
            return handler

        for key, description, method in context.kernel.lookup_all("raster_preprocessor/.*"):
            if key == self.raster_direction:
                plan.commands.append(call_me(method))
                # print (f"Found {description}")
                break

    def as_cutobjects(self, closed_distance=15, passes=1):
        """
        Generator of cutobjects for the image operation. This takes any image node children
        and converts them into rastercut cutobjects.
        """
        unsupported = self._instructions.get("unsupported_opt", ())
        if self.raster_direction in unsupported:
            self.raster_direction = RASTER_T2B

        for image_node in self.children:
            cutcodes = []
            # Process each child. All settings are different for each child.
            if image_node.type == "reference":
                image_node = image_node.node
            if not hasattr(image_node, "as_image"):
                continue
            if getattr(image_node, "hidden", False):
                continue
            cutsettings = self.derive()
            settings = dict(cutsettings)
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
            bidirectional = self.bidirectional
            start_on_left = self.raster_preference_left
            start_on_top = self.raster_preference_top
            if direction in (RASTER_GREEDY_V, RASTER_L2R, RASTER_R2L):
                horizontal = False
            if direction in (RASTER_B2T, RASTER_T2B, RASTER_HATCH, RASTER_CROSSOVER, RASTER_GREEDY_H):
                horizontal = True
            if direction in (RASTER_T2B, RASTER_CROSSOVER):
                start_on_top = True
            if direction == RASTER_B2T:
                start_on_top = False
            if direction == RASTER_R2L:
                start_on_left = False
            if direction == RASTER_L2R:
                start_on_left = True
            if direction in (RASTER_GREEDY_H, RASTER_GREEDY_V, RASTER_CROSSOVER):
                bidirectional = True

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

            dotwidth = 2 * self._spot_in_device_units / (step_x + step_y)

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
                    rasterimage = copy(cleared_image)
                    cutsettings = dict(settings)
                    cut = RasterCut(
                        image=rasterimage,
                        offset_x=offset_x,
                        offset_y=offset_y,
                        step_x=step_x,
                        step_y=step_y,
                        inverted=inverted,
                        direction=direction,
                        bidirectional=bidirectional,
                        horizontal=horizontal,
                        start_minimum_x=start_on_left,
                        start_minimum_y=start_on_top,
                        overscan=overscan,
                        settings=cutsettings,
                        passes=passes,
                        post_filter=image_filter,
                        label=f"Pass {gray}: cutoff={skip_pixel}",
                        laserspot=dotwidth,
                        special=self._instructions,
                    )
                    cut.path = path
                    cut.original_op = self.type
                    cutcodes.append(cut)

                    if direction == RASTER_HATCH:
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
                        rasterimage = copy(cleared_image)
                        cutsettings = dict(settings)
                        cut = RasterCut(
                            image=rasterimage,
                            offset_x=offset_x,
                            offset_y=offset_y,
                            step_x=step_x,
                            step_y=step_y,
                            inverted=inverted,
                            direction=direction,
                            bidirectional=bidirectional,
                            horizontal=horizontal,
                            start_minimum_x=start_on_left,
                            start_minimum_y=start_on_top,
                            overscan=overscan,
                            settings=cutsettings,
                            passes=passes,
                            post_filter=image_filter,
                            label=f"Pass {gray}.2: cutoff={skip_pixel}",
                            laserspot=dotwidth,
                            special=self._instructions,
                        )
                        cut.path = path
                        cut.original_op = self.type
                        cutcodes.append(cut)
            else:
                # Create Cut Object for regular image
                image_filter = None
                do_optimize = self.raster_direction in (RASTER_GREEDY_H, RASTER_GREEDY_V)
                if do_optimize:
                    # get some image statistics
                    white_pixels = 0
                    used_colors = pil_image.getcolors()
                    for col_count, col in used_colors:
                        if col==255:
                            white_pixels = col_count
                            break
                    white_pixel_ratio = white_pixels / (pil_image.width * pil_image.height)
                    # print (f"white pixels: {white_pixels}, ratio = {white_pixel_ratio:.3f}")
                    if white_pixel_ratio < 0.3:
                        self.raster_direction = RASTER_T2B if self.raster_direction == RASTER_GREEDY_H else RASTER_L2R

                if self.raster_direction in (RASTER_CROSSOVER, RASTER_SPIRAL): # Crossover - need both
                    settings["raster_step_x"] = step_x
                    settings["raster_step_y"] = step_y
                if self.raster_direction == RASTER_CROSSOVER and "split_crossover" in self._instructions:
                    self._instructions["mode_filter"] = "ROW"
                    horizontal=True
                    bidirectional=True
                    start_on_top = True
                    start_on_left = True
                    if horizontal:
                        # Raster step is only along y for horizontal raster
                        settings["raster_step_x"] = 0
                        settings["raster_step_y"] = step_y
                    else:
                        # Raster step is only along x for vertical raster
                        settings["raster_step_x"] = step_x
                        settings["raster_step_y"] = 0
                    # Create Cut Object for horizontal lines
                    # The image may be manipulated inside RasterCut, so let's create a fresh copy
                    rasterimage = copy(pil_image)
                    cutsettings = dict(settings)
                    cut = RasterCut(
                        image=rasterimage,
                        offset_x=offset_x,
                        offset_y=offset_y,
                        step_x=step_x,
                        step_y=step_y,
                        inverted=False,
                        direction=direction,
                        bidirectional=bidirectional,
                        horizontal=horizontal,
                        start_minimum_x=start_on_left,
                        start_minimum_y=start_on_top,
                        overscan=overscan,
                        settings=cutsettings,
                        passes=passes,
                        post_filter=image_filter,
                        laserspot=dotwidth,
                        special=dict(self._instructions),
                    )
                    cut.path = path
                    cut.original_op = self.type
                    cutcodes.append(cut)

                    # Now set it for the next pass
                    horizontal=False
                    if horizontal:
                        # Raster step is only along y for horizontal raster
                        settings["raster_step_x"] = 0
                        settings["raster_step_y"] = step_y
                    else:
                        # Raster step is only along x for vertical raster
                        settings["raster_step_x"] = step_x
                        settings["raster_step_y"] = 0

                    self._instructions["mode_filter"] = "COL"

                # The image may be manipulated inside RasterCut, so let's create a fresh copy
                rasterimage = copy(pil_image)
                cutsettings = dict(settings)
                cut = RasterCut(
                    image=rasterimage,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    step_x=step_x,
                    step_y=step_y,
                    inverted=inverted,
                    bidirectional=bidirectional,
                    direction=direction,
                    horizontal=horizontal,
                    start_minimum_x=start_on_left,
                    start_minimum_y=start_on_top,
                    overscan=overscan,
                    settings=cutsettings,
                    passes=passes,
                    laserspot=dotwidth,
                    special=self._instructions,
                )
                cut.path = path
                cut.original_op = self.type
            cutcodes.append(cut)
            if self.raster_direction == RASTER_HATCH:
                # Create optional crosshatch cut
                direction = RASTER_L2R if start_on_left else RASTER_R2L
                horizontal = False
                settings = dict(settings)
                if horizontal:
                    # Raster step is only along y for horizontal raster
                    settings["raster_step_x"] = 0
                    settings["raster_step_y"] = step_y
                else:
                    # Raster step is only along x for vertical raster
                    settings["raster_step_x"] = step_x
                    settings["raster_step_y"] = 0
                # The image may be manipulated inside RasterCut, so let's create a fresh copy
                rasterimage = copy(pil_image)
                cutsettings = dict(settings)
                cut = RasterCut(
                    image=rasterimage,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    step_x=step_x,
                    step_y=step_y,
                    inverted=inverted,
                    direction=direction,
                    bidirectional=bidirectional,
                    horizontal=horizontal,
                    start_minimum_x=start_on_left,
                    start_minimum_y=start_on_top,
                    overscan=overscan,
                    settings=cutsettings,
                    passes=passes,
                    laserspot=dotwidth,
                    special=self._instructions,
                )
                cut.path = path
                cut.original_op = self.type
                cutcodes.append(cut)
            # Yield all generated cutcodes of this image
            yield from cutcodes

    @property
    def bounds(self):
        if not self._bounds_dirty:
            return self._bounds

        self._bounds = None
        if self.output:
            if self._children:
                self._bounds = Node.union_bounds(self._children, bounds=self._bounds, ignore_locked=False, ignore_hidden=True)
            self._bounds_dirty = False
        return self._bounds
