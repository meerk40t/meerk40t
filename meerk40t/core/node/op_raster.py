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
from meerk40t.core.cutplan import CutPlanningFailedError
from meerk40t.core.elements.element_types import *
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

    def __init__(self, settings=None, **kwargs):
        if settings is not None:
            settings = dict(settings)
        Parameters.__init__(self, settings, **kwargs)

        self._allowed_elements_dnd = (
            "elem ellipse",
            "elem path",
            "elem polyline",
            "elem rect",
            "elem line",
            "elem text",
            "elem image",
            "image raster",
        )
        # Which elements do we consider for automatic classification?
        self._allowed_elements = (
            "elem ellipse",
            "elem path",
            "elem polyline",
            "elem rect",
            "elem line",
            "elem text",
        )

        # self.allowed_attributes.append("fill")
        # Is this op out of useful bounds?
        self.dangerous = False
        self.stopop = False
        self.label = "Raster"
        self.use_grayscale = True
        self.consider_laserspot = False
        self._spot_in_device_units = 0
        self._instructions = {}

        # To which attributes do the classification color check respond
        # Can be extended / reduced by add_color_attribute / remove_color_attribute
        # An empty set indicates all nodes will be allowed
        self.allowed_attributes = []
        super().__init__(type="op raster", **kwargs)
        self._formatter = (
            "{enabled}{pass}{element_type}{direction}{speed}mm/s @{power} {color}"
        )
        if isinstance(self.use_grayscale, str):
            s = self.use_grayscale.lower()
            self.use_grayscale = s in ("true", "1")
        if self.use_grayscale is None:
            self.use_grayscale = True
        # They might come from a svg read, but shouldnt be in settings
        for attrib in ("lock", "dangerous", "use_grayscale", "consider_laserspot"):
            if attrib in self.settings:
                del self.settings[attrib]


    def __repr__(self):
        return "RasterOp()"

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Raster"
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
        default_map["percent"] = "100%"
        default_map["ppi"] = "default"
        default_map["grayscale"] = "GS" if self.use_grayscale else "BW"
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
        if drag_node.type.startswith("elem ") and drag_node.type in self._allowed_elements_dnd:
            return True
        elif drag_node.type == "reference" and drag_node.node.type in self._allowed_elements_dnd:
            return True
        elif drag_node.type in op_nodes:
            # Move operation to a different position.
            return True
        elif drag_node.type in ("file", "group"):
            return not any(e.has_ancestor("branch reg") for e in drag_node.flat(elem_nodes))
        return False

    def drop(self, drag_node, modify=True, flag=False):
        count = 0
        existing = 0
        result = False
        if drag_node.type.startswith("elem") and not drag_node.has_ancestor(
            "branch reg"
        ):
            existing += 1
            # if drag_node.type == "elem image":
            #     return False
            # Dragging element onto operation adds that element to the op.
            if modify:
                count += 1
                self.add_reference(drag_node, pos=None if flag else 0)
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
        elif drag_node.type in ("file", "group") and not drag_node.has_ancestor(
            "branch reg"
        ):
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

    def is_referenced(self, node):
        for e in self.children:
            if e is node:
                return True
            if hasattr(e, "node") and e.node is node:
                return True
        return False

    def valid_node_for_reference(self, node):
        if node.type in self._allowed_elements_dnd:
            return True
        else:
            return False

    def classify(self, node, fuzzy=False, fuzzydistance=100, usedefault=False):
        def matching_color(col1, col2):
            _result = False
            if col1 is None and col2 is None:
                _result = True
            elif (
                col1 is not None
                and col1.argb is not None
                and col2 is not None
                and col2.argb is not None
            ):
                if fuzzy:
                    distance = Color.distance(col1, col2)
                    _result = distance < fuzzydistance
                else:
                    _result = col1 == col2
            return _result

        if self.is_referenced(node):
            # No need to add it again...
            return False, False, None

        feedback = []
        if node.type in self._allowed_elements:
            if self.default and usedefault:
                # Have classified but more classification might be needed
                if self.valid_node_for_reference(node):
                    self.add_reference(node)
                    feedback.append("stroke")
                    feedback.append("fill")
                    return True, self.stopop, feedback
            else:
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
                        if node.type in ("elem image", "elem text"):
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
        estimate = 0
        dpi = self.dpi
        # Get fresh union bounds, may not have been marked dirty on additions or removals.
        min_x, min_y, max_x, max_y = Node.union_bounds(self.flat(types=elem_ref_nodes))
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
        Preprocess is called during job planning. This should be called with
        the native matrix.

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

        if isinstance(self.speed, str):
            try:
                self.speed = float(self.speed)
            except ValueError:
                pass
        commands = plan.commands
        native_mm = abs(complex(*matrix.transform_vector([0, UNITS_PER_MM])))
        self.settings["native_mm"] = native_mm
        self.settings["native_speed"] = self.speed * native_mm
        self.settings["native_rapid_speed"] = self.rapid_speed * native_mm
        try:
            overscan = float(Length(self.overscan))
        except ValueError:
            overscan = 0
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
            self.set_dirty_bounds()

            step_x, step_y = context.device.view.dpi_to_steps(self.dpi)
            img_mx = Matrix.scale(step_x, step_y)
            data = []
            for node in self.flat():
                if node.type not in self._allowed_elements_dnd:
                    continue
                if node.type == "reference":
                    node = node.node
                if getattr(node, 'hidden', False):
                    continue
                data.append(node)
            if not data:
                self.children.clear()
                return
            bounds = Node.union_bounds(data, attr="paint_bounds")
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

        commands.append(make_image)
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
        Generator of cutobjects for a raster operation. This takes any image node children
        and converts them into rastercut objects. These objects should have already been converted
        from vector shapes.

        The preference for raster shapes is to use the settings set on this operation rather than on the image-node.
        """
        if len(self.children) == 0:
            return
        settings = self.derive()
        # make an independent copy
        unsupported = self._instructions.get("unsupported_opt", ())
        if self.raster_direction in unsupported:
            self.raster_direction = RASTER_T2B

        # Set overscan
        overscan = self.overscan
        if not isinstance(overscan, float):
            overscan = float(Length(overscan))
        settings["overscan"] = overscan

        for image_node in self.children:
            if hasattr(image_node, "direction") and image_node.direction is not None:
                direction = image_node.direction
            else:
                direction = self.raster_direction
            horizontal = False
            bidirectional = self.bidirectional
            start_on_left = self.raster_preference_left
            start_on_top = self.raster_preference_top
            # Set variables by direction
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

            cutcodes = []
            # Process each child. Some core settings are the same for each child.

            if image_node.type == "reference":
                image_node = image_node.node
            if getattr(image_node, "hidden", False):
                continue
            if image_node.type != "elem image":
                continue

            step_x = image_node.step_x
            step_y = image_node.step_y

            dotwidth = 2 * self._spot_in_device_units / (step_x + step_y)
            # print (f"Laserspot in device units: {self._spot_in_device_units:.2f}, step: {step_x:.2f} + {step_y:.2f} -> {dotwidth:.2f}")

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
            image_filter = None
            if not self.use_grayscale: # By default a bw picture
                threshold = 200
                pil_image = pil_image.point(lambda x: 255 if x > threshold else 0, mode="1")
                # pil_image = pil_image.convert("1")
            if self.raster_direction in (RASTER_GREEDY_H, RASTER_GREEDY_V): # Greedy nearest neighbour
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
                horizontal = True
                start_on_top = True
                start_on_left = True
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
                    bidirectional=bidirectional,
                    direction=direction,
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

            # Create Cut Object
            cut = RasterCut(
                image=rasterimage,
                offset_x=offset_x,
                offset_y=offset_y,
                step_x=step_x,
                step_y=step_y,
                inverted=False,
                bidirectional=bidirectional,
                direction=direction,
                horizontal=horizontal,
                start_minimum_x=start_on_left,
                start_minimum_y=start_on_top,
                overscan=overscan,
                settings=cutsettings,
                passes=passes,
                post_filter=image_filter,
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
                    inverted=False,
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
