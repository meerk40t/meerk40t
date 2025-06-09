"""
ImageNode is the bootstrapped node type for handling image elements within the application.

This class manages the properties and behaviors associated with image nodes, including
image processing, transformations, and keyhole functionalities. It supports various
operations such as cropping, dither effects, and applying raster scripts, while also
maintaining the necessary metadata for rendering and manipulation.

Args:
    **kwargs: Additional keyword arguments for node initialization.

Attributes:
    image: The original image loaded into the node.
    matrix: The transformation matrix applied to the image.
    dpi: The resolution of the image in dots per inch.
    operations: A list of operations to be applied to the image.
    keyhole_reference: Reference for keyhole operations.
    active_image: The processed image ready for rendering.
    active_matrix: The matrix that combines the main matrix with the processed matrix.
    convex_hull: The convex hull of the non-white pixels in the image.

Methods:
    set_keyhole(keyhole_ref, geom=None): Sets the keyhole reference and geometry.
    process_image(step_x=None, step_y=None, crop=True): Processes the image based on the specified steps and cropping options.
    update(context): Initiates the image processing thread and updates the image.
    as_image(): Returns the active image and its bounding box.
    bbox(transformed=True, with_stroke=False): Returns the bounding box of the image.
"""

import threading
import time
from copy import copy
from math import ceil, floor

import numpy as np

from meerk40t.core.node.mixins import LabelDisplay, Suppressable
from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_INCH, UNITS_PER_MM
from meerk40t.image.imagetools import RasterScripts
from meerk40t.svgelements import Matrix, Path, Polygon
from meerk40t.tools.geomstr import Geomstr


class ImageNode(Node, LabelDisplay, Suppressable):
    """
    ImageNode is the bootstrapped node type for the 'elem image' type.

    ImageNode contains a main matrix, main image. A processed image and a processed matrix.
    The processed matrix must be concatenated with the main matrix to be accurate.
    """

    def __init__(self, **kwargs):
        self.image = None
        self.matrix = None
        self.overscan = None
        self.direction = None
        self.dpi = 500
        self.operations = []
        self.invert = None
        self.dither = True
        self.dither_type = "Floyd-Steinberg"
        self.red = 1.0
        self.green = 1.0
        self.blue = 1.0
        self.lightness = 1.0
        self.view_invert = False
        self.prevent_crop = False
        self.is_depthmap = False
        self.depth_resolution = 256
        # Keyhole-Variables
        self._keyhole_reference = None
        self._keyhole_geometry = None
        self._keyhole_image = None
        self._processing = False
        self._convex_hull = None
        self._default_units = UNITS_PER_INCH
        startup = True
        if "comingfromcopy" in kwargs:
            startup = False
            del kwargs["comingfromcopy"]

        self.passthrough = False
        super().__init__(type="elem image", **kwargs)
        if "hidden" in kwargs:
            if isinstance(kwargs["hidden"], str):
                if kwargs["hidden"].lower() == "true":
                    kwargs["hidden"] = True
                else:
                    kwargs["hidden"] = False
            self.hidden = kwargs["hidden"]
        # kwargs can actually reset quite a lot of the properties to none
        # so, we need to revert these changes...
        if self.red is None:
            self.red = 1.0
        if self.green is None:
            self.green = 1.0
        if self.blue is None:
            self.blue = 1.0
        if self.lightness is None:
            self.lightness = 1.0
        if self.operations is None:
            self.operations = list()
        if self.dither_type is None:
            self.dither_type = "Floyd-Steinberg"

        self.__formatter = "{element_type} {id} {width}x{height}"
        if self.matrix is None:
            self.matrix = Matrix()
        if hasattr(self, "href"):
            try:
                from PIL import Image as PILImage

                if not isinstance(self.href, str):
                    # Error caused by href being int value
                    raise ImportError

                self.image = PILImage.open(self.href)
                if hasattr(self, "x"):
                    self.matrix.post_translate_x(self.x)
                    delattr(self, "x")
                if hasattr(self, "y"):
                    self.matrix.post_translate_x(self.y)
                    delattr(self, "y")
                real_width, real_height = self.image.size
                declared_width, declared_height = real_width, real_height
                if hasattr(self, "width"):
                    declared_width = self.width
                    delattr(self, "width")

                if hasattr(self, "height"):
                    declared_height = self.height
                    delattr(self, "height")
                try:
                    sx = declared_width / real_width
                    sy = declared_height / real_height
                    self.matrix.post_scale(sx, sy)
                except ZeroDivisionError:
                    pass
                delattr(self, "href")

            except ImportError:
                self.image = None

        # Step_x/y is the step factor of the image, the reciprocal of the DPI.
        self.step_x = None
        self.step_y = None

        self._needs_update = False
        self._update_thread = None
        self._update_lock = threading.Lock()
        self._processed_image = None
        self._processed_matrix = None
        self._actualized_matrix = None
        self._process_image_failed = False

        self.message = None
        if (
            self.operations
            or self.dither
            or self.prevent_crop
            or self.keyhole_reference
        ) and startup:
            step = self._default_units / self.dpi
            step_x = step
            step_y = step
            self.process_image(step_x, step_y, not self.prevent_crop)

    def __copy__(self):
        nd = self.node_dict
        nd["matrix"] = copy(self.matrix)
        nd["operations"] = copy(self.operations)
        nd["comingfromcopy"] = True
        newnode = ImageNode(**nd)
        if self._processed_image is not None:
            newnode._processed_image = copy(self._processed_image)
            newnode._processed_matrix = copy(self._processed_matrix)
            newnode._actualized_matrix = copy(self._actualized_matrix)
        g = None if self._keyhole_geometry is None else copy(self._keyhole_geometry)
        newnode.set_keyhole(self.keyhole_reference, g)
        return newnode

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self.image)}, {str(self._parent)})"

    @property
    def active_image(self):
        # This may be called too quick, so the image is still processing.
        # This would cause an immediate recalculation which would make
        # things even worse, we wait max 1 second
        counter = 0
        while self._processing and counter < 20:
            time.sleep(0.05)
            counter += 1
        if self._processed_image is None:
            step = self._default_units / self.dpi
            step_x = step
            step_y = step
            self.process_image(step_x, step_y, not self.prevent_crop)
        return self._apply_keyhole()
        # if self._processed_image is not None:
        #     return self._processed_image
        # else:
        #     return self.image

    @property
    def active_matrix(self):
        if self._processed_matrix is None:
            return self.matrix
        return self._processed_matrix * self.matrix

    @property
    def keyhole_reference(self):
        return self._keyhole_reference

    @keyhole_reference.setter
    def keyhole_reference(self, value):
        self._keyhole_reference = value
        self._keyhole_geometry = None
        self._bounds_dirty = True

    def set_keyhole(self, keyhole_ref, geom=None):
        # This is useful if we do want to set it after loading a file
        # or when assigning the reference, as this does not need a context
        # query the complete node tree
        self._cache = None
        self.keyhole_reference = keyhole_ref
        self._keyhole_geometry = geom
        self._keyhole_image = None

    def convex_hull(self) -> Geomstr:
        if self._convex_hull is not None:
            return self._convex_hull
        t0 = time.perf_counter()
        image_np = np.array(self.active_image.convert("L"))
        # print (image_np)
        # Find non-white pixels
        # Iterate over each row in the image
        left_side = []
        right_side = []
        for y in range(image_np.shape[0]):
            row = image_np[y]
            non_white_indices = np.where(row < 255)[0]

            if non_white_indices.size > 0:
                leftmost = non_white_indices[0]
                rightmost = non_white_indices[-1]
                left_side.append((leftmost, y))
                right_side.insert(0, (rightmost, y))
        left_side.extend(right_side)
        non_white_pixels = left_side
        t1 = time.perf_counter()
        # Compute the convex hull
        """
        After the introduction of the quickhull routine in geomstr
        the ConvexHull routine from scipy provides only limited
        advantages over our own routine

        pts = None
        try:
            # The ConvexHull routine from scipy provides less points
            # and is faster (plus it has fewer non-understood artifacts)
            from scipy.spatial import ConvexHull
            c_points = np.array(non_white_pixels)
            hull = ConvexHull(c_points)
            hpts = c_points[hull.vertices]
            pts = list( ( p[0], p[1] ) for p in hpts)
            # print (f"scipy Hull has {len(pts)} pts")
        except ImportError:
            pass
        t1b = time.perf_counter()
        if pts is None:
        """
        pts = list(Geomstr.convex_hull(None, non_white_pixels))
        if pts:
            pts.append(pts[0])
        # print("convex hull done")
        t2 = time.perf_counter()
        # print (f"Hull has {len(pts)} pts")
        self._convex_hull = Geomstr.lines(*pts)
        # print (f"Hull dimension: {self._convex_hull.bbox()} (for reference: image is {self.active_image.width}x{self.active_image.height} pixels)")
        self._convex_hull.transform(self.active_matrix)
        # print (f"Final dimension: {self._convex_hull.bbox()}")
        t3 = time.perf_counter()
        # print (f"Time to get pixels: {t1-t0:.3f}s, geomstr: {t2-t1b:.3f}s, scipy: {t1b-t1:.3f}s, total: {t3-t0:.3f}s")
        return self._convex_hull

    def preprocess(self, context, matrix, plan):
        """
        Preprocess step during the cut planning stages.

        We require a context to calculate the correct step values relative to the device
        """

        dev_x, dev_y = context.device.view.dpi_to_steps(1)
        self._default_units = (dev_x + dev_y) / 2
        self.step_x, self.step_y = context.device.view.dpi_to_steps(self.dpi)
        self.matrix *= matrix
        self.set_dirty_bounds()
        self.process_image(self.step_x, self.step_y, not self.prevent_crop)

    def as_image(self):
        return self.active_image, self.bbox()

    def bbox(self, transformed=True, with_stroke=False):
        image_width, image_height = self.active_image.size
        matrix = self.active_matrix
        x0, y0 = matrix.point_in_matrix_space((0, 0))
        x1, y1 = matrix.point_in_matrix_space((image_width, image_height))
        x2, y2 = matrix.point_in_matrix_space((0, image_height))
        x3, y3 = matrix.point_in_matrix_space((image_width, 0))
        return (
            min(x0, x1, x2, x3),
            min(y0, y1, y2, y3),
            max(x0, x1, x2, x3),
            max(y0, y1, y2, y3),
        )

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map.update(self.__dict__)
        image = self.active_image
        default_map["width"] = image.width
        default_map["height"] = image.height
        default_map["element_type"] = "Image"
        return default_map

    def can_drop(self, drag_node):
        if self.is_a_child_of(drag_node):
            return False
        # Dragging element into element.
        return bool(
            hasattr(drag_node, "as_geometry")
            or hasattr(drag_node, "as_image")
            or drag_node.type in ("op image", "op raster", "file", "group")
        )

    def drop(self, drag_node, modify=True, flag=False):
        # Dragging element into element.
        if not self.can_drop(drag_node):
            return False
        if (
            hasattr(drag_node, "as_geometry")
            or hasattr(drag_node, "as_image")
            or drag_node.type in ("file", "group")
        ):
            if modify:
                self.insert_sibling(drag_node)
            return True
        elif drag_node.type.startswith("op"):
            # If we drag an operation to this node,
            # then we will reverse the game
            old_references = list(self._references)
            result = drag_node.drop(self, modify=modify, flag=flag)
            if result and modify:
                for ref in old_references:
                    ref.remove_node()
            return result
        return False

    def revalidate_points(self):
        bounds = self.bounds
        if bounds is None:
            return
        if len(self._points) < 9:
            self._points.extend([None] * (9 - len(self._points)))
        self._points[0] = [bounds[0], bounds[1], "bounds top_left"]
        self._points[1] = [bounds[2], bounds[1], "bounds top_right"]
        self._points[2] = [bounds[0], bounds[3], "bounds bottom_left"]
        self._points[3] = [bounds[2], bounds[3], "bounds bottom_right"]
        cx = (bounds[0] + bounds[2]) / 2
        cy = (bounds[1] + bounds[3]) / 2
        self._points[4] = [cx, cy, "bounds center_center"]
        self._points[5] = [cx, bounds[1], "bounds top_center"]
        self._points[6] = [cx, bounds[3], "bounds bottom_center"]
        self._points[7] = [bounds[0], cy, "bounds center_left"]
        self._points[8] = [bounds[2], cy, "bounds center_right"]

    def update_point(self, index, point):
        return False

    def add_point(self, point, index=None):
        return False

    def update(self, context):
        """
        Update kicks off the image processing thread, which performs RasterWizard script operations on the image node.

        The text should be displayed in the scene by the renderer. And any additional changes will be processed
        until the new processed image is completed.

        @param context:
        @return:
        """
        self._needs_update = True
        if context is not None:
            self.message = "Processing..."
            context.signal("refresh_scene", "Scene")
        if self._update_thread is None:

            def clear(result):
                self._needs_update = False
                self._update_thread = None
                if context is not None:
                    if self._process_image_failed:
                        self.message = "Process image could not exist in memory."
                    else:
                        self.message = None
                    context.signal("refresh_scene", "Scene")
                    context.signal("image_updated", self)

            def get_keyhole_geometry():
                self._keyhole_geometry = None
                self._keyhole_image = None
                refnode = context.elements.find_node(self.id)
                if refnode is not None and hasattr(refnode, "as_geometry"):
                    self._keyhole_geometry = refnode.as_geometry()

            self._processed_image = None
            self._convex_hull = None
            # self.processed_matrix = None
            if context is None:
                # Direct execution
                self._needs_update = False
                # Calculate scene step_x, step_y values
                step = self._default_units / self.dpi
                step_x = step
                step_y = step
                self.process_image(step_x, step_y, not self.prevent_crop)
                # Unset cache.
                self._cache = None
            else:
                if (
                    self._keyhole_reference is not None
                    and self._keyhole_geometry is None
                ):
                    get_keyhole_geometry()

                # We need to have a thread per image, so we need to provide a node specific thread_name!
                self._update_thread = context.threaded(
                    self._process_image_thread,
                    result=clear,
                    daemon=True,
                    thread_name=f"image_update_{self.id}_{str(time.perf_counter())}",
                )

    def _process_image_thread(self):
        """
        The function deletes the caches and processes the image until it no longer needs updating.

        @return:
        """
        while self._needs_update:
            self._needs_update = False
            # Calculate scene step_x, step_y values
            step = self._default_units / self.dpi
            step_x = step
            step_y = step
            with self._update_lock:
                self.process_image(step_x, step_y, not self.prevent_crop)
                # Unset cache.
                self._cache = None

    def process_image(self, step_x=None, step_y=None, crop=True):
        """
        SVG matrices are defined as follows.
        [a c e]
        [b d f]

        Pil requires a, c, e, b, d, f accordingly.

        As of 0.7.2 this converts the image to "L" as part of the process.

        There is a small amount of slop at the edge of converted images sometimes, so it's essential
        to mark the image as inverted if black should be treated as empty pixels. The scaled down image
        not lose the edge pixels since they could be important, but also dim may not be a multiple
        of step level which requires an introduced empty edge pixel to be added.
        """

        from PIL import Image, ImageDraw

        while self._processing:
            time.sleep(0.05)

        if step_x is None:
            step_x = self.step_x
        if step_y is None:
            step_y = self.step_y
        # print (f"process called with step_x={step_x}, step_y={step_y} (node: {self.step_x}, {self.step_y})")
        try:
            actualized_matrix, image = self._process_image(step_x, step_y, crop=crop)
            inverted_main_matrix = Matrix(self.matrix).inverse()
            self._actualized_matrix = actualized_matrix
            self._processed_matrix = actualized_matrix * inverted_main_matrix
            self._processed_image = image
            self._process_image_failed = False
            bb = self.bbox()
            self._bounds = bb
            self._paint_bounds = bb
        except Exception as e:
            # Memory error if creating requires too much memory.
            # DecompressionBomb if over 272 megapixels.
            # ValueError if bounds are NaN.
            # ZeroDivide if inverting the processed matrix cannot happen because image is a line
            # print (f"Shit, crashed with {e}")
            self._process_image_failed = True
            self._processing = False
        self.updated()

    @property
    def opaque_image(self):
        from PIL import Image

        img = self.image
        if img is not None and img.mode == "RGBA":
            r, g, b, a = img.split()
            background = Image.new("RGB", img.size, "white")
            background.paste(img, mask=a)
            img = background
        return img

    def _convert_image_to_grayscale(self, image):
        # Convert image to L type.
        if image.mode == "I":
            from PIL import Image

            # Load the 32-bit signed grayscale image
            img = np.array(image, dtype=np.int32)

            # No need to reshape the image to its original dimensions
            # img = img.reshape((image.width, image.height))

            # Normalize the image to the range 0-255
            img_normalized = ((img - img.min()) / (img.max() - img.min()) * 255).astype(
                np.uint8
            )

            # Convert the NumPy array to a Pillow Image
            img_pil = Image.fromarray(img_normalized)
            image = img_pil.convert("L")
        elif image.mode != "L":
            # Precalculate RGB for L conversion.
            # if self.red is None:
            #     self.red = 1
            if self.red is None or self.green is None or self.blue is None:
                r = 1
                g = 1
                b = 1
            else:
                r = self.red * 0.299
                g = self.green * 0.587
                b = self.blue * 0.114
                v = self.lightness
                if v == 0:
                    v = 0.000001
                c = r + g + b
                try:
                    c /= v
                    r = r / c
                    g = g / c
                    b = b / c
                except ZeroDivisionError:
                    pass
            image = image.convert("RGB")
            image = image.convert("L", matrix=(r, g, b, 1.0))
        return image

    def _get_transparent_mask(self, image):
        """
        Create Transparency Mask.
        @param image:
        @return:
        """
        if image is None:
            return None
        if "transparency" in image.info:
            image = image.convert("RGBA")
        try:
            return image.getchannel("A").point(lambda e: 255 - e)
        except ValueError:
            return None

    def _apply_mask(self, image, mask, reject_color=None):
        """
        Fill in original image with reject pixels.

        @param image: Image to be masked off.
        @param mask: Mask to apply to image
        @param reject_color: Optional specified reject color override. Reject is usually "white" or black if inverted.
        @return: image with mask pixels filled in with reject pixels
        """
        if not mask:
            return image
        if reject_color is None:
            reject_color = "black" if self.invert else "white"
        from PIL import Image

        background = image.copy()
        reject = Image.new("L", image.size, reject_color)
        background.paste(reject, mask=mask)
        return background

    def _get_crop_box(self, image):
        """
        Get the bbox cutting off the reject edges. The reject edges depend on the image's invert setting.
        @param image: Image to get crop box for.
        @return:
        """
        try:
            if self.invert:
                return image.getbbox()
            else:
                return image.point(lambda e: 255 - e).getbbox()
        except ValueError:
            return None

    def _process_script(self, image):
        """
        Process actual raster script operations. Any required grayscale, inversion, and masking will already have
        occurred. If there were reject pixels before they will be masked off after this process.

        @param image: image to process with self.operation script.

        @return: processed image
        """
        from PIL import ImageEnhance, ImageFilter, ImageOps

        overall_left = 0
        overall_top = 0
        overall_right, overall_bottom = image.size
        for op in self.operations:
            name = op["name"]
            if name == "resample":
                # This is just a reminder, that while this may still appear in the scripts it is intentionally
                # ignored (or needs to be revised with the upcoming appearance of passthrough) as it is not
                # serving the purpose of the past
                continue
            if name == "crop":
                try:
                    # The dimensions of the image could have already be changed,
                    # so we recalculate the edges based on the original image size
                    if op["enable"] and op["bounds"] is not None:
                        crop = op["bounds"]
                        left_gap = int(crop[0])
                        top_gap = int(crop[1])
                        right_gap = self.image.width - int(crop[2])
                        bottom_gap = self.image.height - int(crop[3])

                        w, h = image.size
                        left = left_gap
                        upper = top_gap
                        right = image.width - right_gap
                        lower = image.height - bottom_gap

                        if left >= w:
                            left = w - 1
                        if upper >= h:
                            upper = h
                        if right <= left:
                            right = left + 1
                        if lower <= upper:
                            lower = upper + 1

                        overall_left += left
                        overall_top += upper
                        overall_right -= w - right
                        overall_bottom -= h - lower
                        image = image.crop((left, upper, right, lower))
                except KeyError:
                    pass
            elif name == "edge_enhance":
                try:
                    if op["enable"]:
                        if image.mode == "P":
                            image = image.convert("L")
                        image = image.filter(filter=ImageFilter.EDGE_ENHANCE)
                except KeyError:
                    pass
            elif name == "auto_contrast":
                try:
                    if op["enable"]:
                        if image.mode not in ("RGB", "L"):
                            # Auto-contrast raises NotImplementedError if P
                            # Auto-contrast raises OSError if not RGB, L.
                            image = image.convert("L")
                        image = ImageOps.autocontrast(image, cutoff=op["cutoff"])
                except KeyError:
                    pass
            elif name == "tone":
                try:
                    if op["enable"] and op["values"] is not None and image.mode == "L":
                        image = image.convert("P")
                        tone_values = op["values"]
                        if op["type"] == "spline":
                            spline = ImageNode.spline(tone_values)
                        else:
                            tone_values = [q for q in tone_values if q is not None]
                            spline = ImageNode.line(tone_values)
                        if len(spline) < 256:
                            spline.extend([255] * (256 - len(spline)))
                        if len(spline) > 256:
                            spline = spline[:256]
                        image = image.point(spline)
                        if image.mode != "L":
                            image = image.convert("L")
                except KeyError:
                    pass
            elif name == "contrast":
                try:
                    if op["enable"] and (
                        op["contrast"] is not None and op["brightness"] is not None
                    ):
                        contrast = ImageEnhance.Contrast(image)
                        c = (op["contrast"] + 128.0) / 128.0
                        image = contrast.enhance(c)

                        brightness = ImageEnhance.Brightness(image)
                        b = (op["brightness"] + 128.0) / 128.0
                        image = brightness.enhance(b)
                except KeyError:
                    pass
            elif name == "gamma":
                try:
                    if op["enable"] and op["factor"] is not None:
                        if image.mode == "L":
                            gamma_factor = float(op["factor"])

                            def crimp(px):
                                px = int(round(px))
                                if px < 0:
                                    return 0
                                if px > 255:
                                    return 255
                                return px

                            if gamma_factor == 0:
                                gamma_lut = [0] * 256
                            else:
                                gamma_lut = [
                                    crimp(pow(i / 255, (1.0 / gamma_factor)) * 255)
                                    for i in range(256)
                                ]
                            image = image.point(gamma_lut)
                            if image.mode != "L":
                                image = image.convert("L")
                except KeyError:
                    pass
            elif name == "unsharp_mask":
                try:
                    if (
                        op["enable"]
                        and op["percent"] is not None
                        and op["radius"] is not None
                        and op["threshold"] is not None
                    ):
                        unsharp = ImageFilter.UnsharpMask(
                            radius=op["radius"],
                            percent=op["percent"],
                            threshold=op["threshold"],
                        )
                        image = image.filter(unsharp)
                except (KeyError, ValueError):  # Value error if wrong type of image.
                    pass
            elif name == "halftone":
                try:
                    if op["enable"]:
                        image = RasterScripts.halftone(
                            image,
                            sample=op["sample"],
                            angle=op["angle"],
                            oversample=op["oversample"],
                            black=op["black"],
                        )
                except KeyError:
                    pass
            elif name == "dither":
                # Set dither
                try:
                    if op["enable"] and op["type"] is not None:
                        self.dither_type = op["type"]
                        self.dither = True
                        self.is_depthmap = False
                    else:
                        # Takes precedence
                        self.dither = False
                        # image = self._apply_dither(image)
                except KeyError:
                    pass
            else:
                # print(f"Unknown operation in raster-script: {name}")
                continue
        return image, (overall_left, overall_top, overall_right, overall_bottom)

    def _apply_dither(self, image):
        """
        Dither image to 1 bit. Floyd-Steinberg is performed by Pillow, other dithers require custom code.

        @param image: grayscale image to dither.
        @return: 1 bit dithered image
        """
        from meerk40t.image.imagetools import dither

        if self.dither and self.dither_type is not None:
            if self.dither_type != "Floyd-Steinberg":
                image = dither(image, self.dither_type)
            if image.mode != "1":
                image = image.convert("1")
            self.is_depthmap = False
        return image

    def _process_image(self, step_x, step_y, crop=True):
        """
        This core code replaces the older actualize and rasterwizard functionalities. It should convert the image to
        a post-processed form with resulting post-process matrix.

        @param crop: Should the unneeded edges be cropped as part of this process. The need for the edge is determined
            by the color and the state of the self.invert attribute.
        @return:
        """
        from PIL import Image, ImageOps

        try:
            from PIL.Image import Transform

            AFFINE = Transform.AFFINE
        except ImportError:
            AFFINE = Image.AFFINE

        try:
            from PIL.Image import Resampling

            BICUBIC = Resampling.BICUBIC
        except ImportError:
            BICUBIC = Image.BICUBIC
        self._processing = True
        image = self.image

        transparent_mask = self._get_transparent_mask(image)
        opaque = self.opaque_image
        image = self._convert_image_to_grayscale(opaque)

        image = self._apply_mask(image, transparent_mask)

        # Calculate image box.
        box = None
        if crop:
            box = self._get_crop_box(image)
        if box is None:
            # If box is entirely white, bbox caused value error, or crop not set.
            box = (0, 0, image.width, image.height)
        orgbox = (box[0], box[1], box[2], box[3])

        transform_matrix = copy(self.matrix)  # Prevent Knock-on effect.

        # Find the boundary points of the rotated box edges.
        boundary_points = [
            transform_matrix.point_in_matrix_space([box[0], box[1]]),  # Top-left
            transform_matrix.point_in_matrix_space([box[2], box[1]]),  # Top-right
            transform_matrix.point_in_matrix_space([box[0], box[3]]),  # Bottom-left
            transform_matrix.point_in_matrix_space([box[2], box[3]]),  # Bottom-right
        ]
        xs = [e[0] for e in boundary_points]
        ys = [e[1] for e in boundary_points]

        # bbox here is expanded matrix size of box.
        step_scale_x = 1 / float(step_x)
        step_scale_y = 1 / float(step_y)

        bbox = min(xs), min(ys), max(xs), max(ys)

        image_width = ceil(bbox[2] * step_scale_x) - floor(bbox[0] * step_scale_x)
        image_height = ceil(bbox[3] * step_scale_y) - floor(bbox[1] * step_scale_y)
        tx = bbox[0]
        ty = bbox[1]
        # Caveat: we move the picture backward, so that the non-white
        # image content aligns at 0 , 0 - but we don't crop the image
        transform_matrix.post_translate(-tx, -ty)
        transform_matrix.post_scale(step_scale_x, step_scale_y)
        if step_y < 0:
            # If step_y is negative, translate
            transform_matrix.post_translate(0, image_height)
        if step_x < 0:
            # If step_x is negative, translate
            transform_matrix.post_translate(image_width, 0)

        try:
            transform_matrix.inverse()
        except ZeroDivisionError:
            # malformed matrix, scale=0 or something.
            transform_matrix.reset()

        # Perform image transform if needed.
        if (
            self.matrix.a != step_x
            or self.matrix.b != 0.0
            or self.matrix.c != 0.0
            or self.matrix.d != step_y
        ):
            # print (f"another transform called while {image.width}x{image.height} - requested: {image_width}x{image_height}")
            if image_height <= 0:
                image_height = 1
            if image_width <= 0:
                image_width = 1
            image = image.transform(
                (image_width, image_height),
                AFFINE,
                (
                    transform_matrix.a,
                    transform_matrix.c,
                    transform_matrix.e,
                    transform_matrix.b,
                    transform_matrix.d,
                    transform_matrix.f,
                ),
                resample=BICUBIC,
                fillcolor="black" if self.invert else "white",
            )
            # print (f"after transform {image.width}x{image.height}")
        actualized_matrix = Matrix()

        if step_y < 0:
            # if step_y is negative, translate.
            actualized_matrix.post_translate(0, -image_height)
        if step_x < 0:
            # if step_x is negative, translate.
            actualized_matrix.post_translate(-image_width, 0)

        # If crop applies, apply crop.
        if crop:
            cbox = self._get_crop_box(image)
            if cbox is not None:
                width = cbox[2] - cbox[0]
                height = cbox[3] - cbox[1]
                if width != image.width or height != image.height:
                    image = image.crop(cbox)
                    # TODO:
                    # We did not crop the image so far, but we already applied
                    # the cropped transformation! That may be faulty, and needs to
                    # be corrected at a later stage, but this logic, even if clumsy
                    # is good enough: don't shift things twice!
                    if orgbox[0] == 0 and orgbox[1] == 0:
                        actualized_matrix.post_translate(cbox[0], cbox[1])

        actualized_matrix.post_scale(step_x, step_y)
        actualized_matrix.post_translate(tx, ty)

        # Invert black to white if needed.
        if self.invert:
            try:
                image = ImageOps.invert(image)
            except OSError as e:
                print(
                    f"Image inversion crashed: {e}\nMode: {image.mode}, {image.width}x{image.height} pixel"
                )

        # Find rejection mask of white pixels. (already inverted)
        reject_mask = image.point(lambda e: 0 if e == 255 else 255)
        image, newbounds = self._process_script(image)
        # This may have again changed the size of the image (op crop)
        # so we need to adjust the reject mask...
        reject_mask = reject_mask.crop(newbounds)

        background = Image.new("L", image.size, "white")
        background.paste(image, mask=reject_mask)
        image = background

        image = self._apply_dither(image)

        self._processing = False
        return actualized_matrix, image

    def _apply_keyhole(self):
        from PIL import Image, ImageDraw

        image = self._processed_image
        if image is None:
            image = self.image
        if self._keyhole_geometry is not None:
            # Let's check whether the keyhole dimensions match
            if self._keyhole_image is not None and (
                self._keyhole_image.width != image.width
                or self._keyhole_image.height != image.height
            ):
                self._keyhole_image = None
            if self._keyhole_image is None:
                actualized_matrix = self._actualized_matrix
                # We can't render something with the usual suspects ie laserrender.render
                # as we do not have access to wxpython on the command line, so we stick
                # to the polygon method of ImageDraw instead
                maskimage = Image.new("L", image.size, "black")
                draw = ImageDraw.Draw(maskimage)
                inverted_main_matrix = Matrix(self.matrix).inverse()
                matrix = actualized_matrix * inverted_main_matrix * self.matrix

                x0, y0 = matrix.point_in_matrix_space((0, 0))
                x2, y2 = matrix.point_in_matrix_space((image.width, image.height))
                # print (x0, y0, x2, y2)
                # Let's simplify things, if we don't have any overlap then the image is white...
                i_wd = x2 - x0
                i_ht = y2 - y0
                gidx = 0
                for geom in self._keyhole_geometry.as_subpaths():
                    # Let's simplify things, if we don't have any overlap then we don't need to do something
                    # if x0 > bounds[2] or x2 < bounds [0] or y0 > bounds[3] or y2 < bounds[1]:
                    #     continue
                    geom_points = list(
                        geom.as_interpolated_points(int(UNITS_PER_MM / 10))
                    )
                    points = list()
                    for pt in geom_points:
                        if pt is None:
                            continue
                        gx = pt.real
                        gy = pt.imag
                        x = int(maskimage.width * (gx - x0) / i_wd)
                        y = int(maskimage.height * (gy - y0) / i_ht)
                        points.append((x, y))

                    # print (points)
                    draw.polygon(points, fill="white", outline="white")
                self._keyhole_image = maskimage
                # For debug purposes...
                # maskimage.save("C:\\temp\\maskimage.png")

            background = Image.new("L", image.size, "white")
            background.paste(image, mask=self._keyhole_image)
            image = background
        return image

    @staticmethod
    def line(p):
        N = len(p) - 1
        try:
            m = [(p[i + 1][1] - p[i][1]) / (p[i + 1][0] - p[i][0]) for i in range(0, N)]
        except ZeroDivisionError:
            m = [1] * N
        # b = y - mx
        b = [p[i][1] - (m[i] * p[i][0]) for i in range(N)]
        r = list()
        for i in range(p[0][0]):
            r.append(0)
        for i in range(len(p) - 1):
            x0 = p[i][0]
            x1 = p[i + 1][0]
            range_list = [int(round((m[i] * x) + b[i])) for x in range(x0, x1)]
            r.extend(range_list)
        for i in range(p[-1][0], 256):
            r.append(255)
        r.append(round(int(p[-1][1])))
        return r

    @staticmethod
    def spline(p):
        """
        Spline interpreter.

        Returns all integer locations between different spline interpolation values
        @param p: points to be quad spline interpolated.
        @return: integer y values for given spline points.
        """
        try:
            N = len(p) - 1
            w = [(p[i + 1][0] - p[i][0]) for i in range(N)]
            h = [(p[i + 1][1] - p[i][1]) / w[i] for i in range(N)]
            ftt = (
                [0]
                + [3 * (h[i + 1] - h[i]) / (w[i + 1] + w[i]) for i in range(N - 1)]
                + [0]
            )
            A = [(ftt[i + 1] - ftt[i]) / (6 * w[i]) for i in range(N)]
            B = [ftt[i] / 2 for i in range(N)]
            C = [h[i] - w[i] * (ftt[i + 1] + 2 * ftt[i]) / 6 for i in range(N)]
            D = [p[i][1] for i in range(N)]
        except ZeroDivisionError:
            return list(range(256))
        r = list()
        for i in range(p[0][0]):
            r.append(0)
        for i in range(len(p) - 1):
            a = p[i][0]
            b = p[i + 1][0]
            r.extend(
                int(
                    round(
                        A[i] * (x - a) ** 3
                        + B[i] * (x - a) ** 2
                        + C[i] * (x - a)
                        + D[i]
                    )
                )
                for x in range(a, b)
            )
        for i in range(p[-1][0], 256):
            r.append(255)
        r.append(round(int(p[-1][1])))
        return r

    def as_path(self):
        image_width, image_height = self.active_image.size
        matrix = self.active_matrix
        x0, y0 = matrix.point_in_matrix_space((0, 0))
        x1, y1 = matrix.point_in_matrix_space((0, image_height))
        x2, y2 = matrix.point_in_matrix_space((image_width, image_height))
        x3, y3 = matrix.point_in_matrix_space((image_width, 0))
        return abs(Path(Polygon((x0, y0), (x1, y1), (x2, y2), (x3, y3), (x0, y0))))

    def translated(self, dx, dy, interim=False):
        self._cache = None
        self._keyhole_image = None
        if self._actualized_matrix is not None:
            self._actualized_matrix.post_translate(dx, dy)
        if self._convex_hull is not None:
            self._convex_hull.translate(dx, dy)
        return super().translated(dx, dy)
