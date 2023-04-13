import threading
from copy import copy
from math import ceil, floor

from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_INCH
from meerk40t.image.imagetools import RasterScripts
from meerk40t.svgelements import Matrix, Path, Polygon


class ImageNode(Node):
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
        self.operations = list()
        self.invert = None
        self.dither = True
        self.dither_type = "Floyd-Steinberg"
        self.red = 1.0
        self.green = 1.0
        self.blue = 1.0
        self.lightness = 1.0
        self.view_invert = False
        self.prevent_crop = False

        self.passthrough = False
        super().__init__(type="elem image", **kwargs)
        # kwargs can actually reset quite a lot of the properties to none
        # so we need to revert these changes...
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
                    raise ImportError

                self.image = PILImage.open(self.href)
                if hasattr(self, "x"):
                    self.matrix.post_translate_x(self.x)
                if hasattr(self, "y"):
                    self.matrix.post_translate_x(self.y)
                real_width, real_height = self.image.size
                declared_width, declared_height = real_width, real_height
                if hasattr(self, "width"):
                    declared_width = self.width
                if hasattr(self, "height"):
                    declared_height = self.height
                try:
                    sx = declared_width / real_width
                    sy = declared_height / real_height
                    self.matrix.post_scale(sx, sy)
                except ZeroDivisionError:
                    pass
                delattr(self, "href")
                delattr(self, "x")
                delattr(self, "y")
                delattr(self, "height")
                delattr(self, "width")
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
        self._process_image_failed = False
        self._processing_message = None
        if self.operations or self.dither or self.prevent_crop:
            step = UNITS_PER_INCH / self.dpi
            step_x = step
            step_y = step
            self.process_image(step_x, step_y, not self.prevent_crop)

    def __copy__(self):
        nd = self.node_dict
        nd["matrix"] = copy(self.matrix)
        nd["operations"] = copy(self.operations)
        return ImageNode(**nd)

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self.image)}, {str(self._parent)})"

    @property
    def active_image(self):
        if self._processed_image is None and (
            (self.operations is not None and len(self.operations) > 0) or self.dither
        ):
            step = UNITS_PER_INCH / self.dpi
            step_x = step
            step_y = step
            self.process_image(step_x, step_y, not self.prevent_crop)
        if self._processed_image is not None:
            return self._processed_image
        else:
            return self.image

    @property
    def active_matrix(self):
        if self._processed_matrix is None:
            return self.matrix
        return self._processed_matrix * self.matrix

    def preprocess(self, context, matrix, plan):
        """
        Preprocess step during the cut planning stages.

        We require a context to calculate the correct step values relative to the device
        """
        self.step_x, self.step_y = context.device.dpi_to_steps(self.dpi)
        self.matrix *= matrix
        self.set_dirty_bounds()
        self.process_image(self.step_x, self.step_y, not self.prevent_crop)

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

    def drop(self, drag_node, modify=True):
        # Dragging element into element.
        if drag_node.type.startswith("elem"):
            if modify:
                self.insert_sibling(drag_node)
            return True
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
            self._processing_message = "Processing..."
            context.signal("refresh_scene", "Scene")
        if self._update_thread is None:

            def clear(result):
                self._needs_update = False
                self._update_thread = None
                if context is not None:
                    if self._process_image_failed:
                        self._processing_message = (
                            "Process image could not exist in memory."
                        )
                    else:
                        self._processing_message = None
                    context.signal("refresh_scene", "Scene")
                    context.signal("image_updated", self)

            self._processed_image = None
            # self.processed_matrix = None
            if context is None:
                # Direct execution
                self._needs_update = False
                # Calculate scene step_x, step_y values
                step = UNITS_PER_INCH / self.dpi
                step_x = step
                step_y = step
                self.process_image(step_x, step_y, not self.prevent_crop)
                # Unset cache.
                self._cache = None
            else:
                self._update_thread = context.threaded(
                    self._process_image_thread, result=clear, daemon=True
                )

    def _process_image_thread(self):
        """
        The function deletes the caches and processes the image until it no longer needs updating.

        @return:
        """
        while self._needs_update:
            self._needs_update = False
            # Calculate scene step_x, step_y values
            step = UNITS_PER_INCH / self.dpi
            step_x = step
            step_y = step
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
        cannot lose the edge pixels since they could be important, but also dim may not be a multiple
        of step level which requires an introduced empty edge pixel to be added.
        """

        from PIL import Image

        if step_x is None:
            step_x = self.step_x
        if step_y is None:
            step_y = self.step_y
        try:
            actualized_matrix, image = self._process_image(step_x, step_y, crop=crop)
            inverted_main_matrix = Matrix(self.matrix).inverse()
            self._processed_matrix = actualized_matrix * inverted_main_matrix
            self._processed_image = image
            self._process_image_failed = False
            bb = self.bbox()
            self._bounds = bb
            self._paint_bounds = bb
        except (MemoryError, Image.DecompressionBombError):
            self._process_image_failed = True
        self.updated()

    @property
    def opaque_image(self):
        from PIL import Image

        img = self.image
        if img is not None:
            if img.mode == "RGBA":
                r, g, b, a = img.split()
                background = Image.new("RGB", img.size, "white")
                background.paste(img, mask=a)
                img = background
        return img

    def _convert_image_to_grayscale(self, image):
        # Convert image to L type.
        if image.mode != "L":
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
                    if op["enable"] and op["bounds"] is not None:
                        crop = op["bounds"]
                        left = int(crop[0])
                        upper = int(crop[1])
                        right = int(crop[2])
                        lower = int(crop[3])
                        w, h = image.size
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
                    if op["enable"] and op["values"] is not None:
                        if image.mode == "L":
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
                    if op["enable"]:
                        if op["contrast"] is not None and op["brightness"] is not None:
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
            image = image.convert("1")
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

        image = self.image

        transparent_mask = self._get_transparent_mask(image)

        image = self._convert_image_to_grayscale(self.opaque_image)

        image = self._apply_mask(image, transparent_mask)

        # Calculate image box.
        box = None
        if crop:
            box = self._get_crop_box(image)
        if box is None:
            # If box is entirely white, bbox caused value error, or crop not set.
            box = (0, 0, image.width, image.height)

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
            if image_height <= 0:
                image_height = 1
            if image_width <= 0:
                image_width = 1
            image = image.transform(
                (image_width, image_height),
                Image.AFFINE,
                (
                    transform_matrix.a,
                    transform_matrix.c,
                    transform_matrix.e,
                    transform_matrix.b,
                    transform_matrix.d,
                    transform_matrix.f,
                ),
                resample=Image.BICUBIC,
                fillcolor="black" if self.invert else "white",
            )
        actualized_matrix = Matrix()

        # If crop applies, apply crop.
        if crop:
            box = self._get_crop_box(image)
            if box is not None:
                width = box[2] - box[0]
                height = box[3] - box[1]
                if width != image.width or height != image.height:
                    image = image.crop(box)
                    actualized_matrix.post_translate(box[0], box[1])

        if step_y < 0:
            # if step_y is negative, translate.
            actualized_matrix.post_translate(0, -image_height)
        if step_x < 0:
            # if step_x is negative, translate.
            actualized_matrix.post_translate(-image_width, 0)

        actualized_matrix.post_scale(step_x, step_y)
        actualized_matrix.post_translate(tx, ty)

        # Invert black to white if needed.
        if self.invert:
            image = ImageOps.invert(image)

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
        return actualized_matrix, image

    @staticmethod
    def line(p):
        N = len(p) - 1
        try:
            m = [(p[i + 1][1] - p[i][1]) / (p[i + 1][0] - p[i][0]) for i in range(0, N)]
        except ZeroDivisionError:
            m = [1] * N
        # b = y - mx
        b = [p[i][1] - (m[i] * p[i][0]) for i in range(0, N)]
        r = list()
        for i in range(0, p[0][0]):
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
            w = [(p[i + 1][0] - p[i][0]) for i in range(0, N)]
            h = [(p[i + 1][1] - p[i][1]) / w[i] for i in range(0, N)]
            ftt = (
                [0]
                + [3 * (h[i + 1] - h[i]) / (w[i + 1] + w[i]) for i in range(0, N - 1)]
                + [0]
            )
            A = [(ftt[i + 1] - ftt[i]) / (6 * w[i]) for i in range(0, N)]
            B = [ftt[i] / 2 for i in range(0, N)]
            C = [h[i] - w[i] * (ftt[i + 1] + 2 * ftt[i]) / 6 for i in range(0, N)]
            D = [p[i][1] for i in range(0, N)]
        except ZeroDivisionError:
            return list(range(256))
        r = list()
        for i in range(0, p[0][0]):
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
