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

    def __init__(
        self,
        image=None,
        matrix=None,
        overscan=None,
        direction=None,
        dpi=500,
        operations=None,
        invert=None,
        dither=None,
        dither_type=None,
        red=None,
        green=None,
        blue=None,
        lightness=None,
        label=None,
        settings=None,
        **kwargs,
    ):
        if settings is None:
            settings = dict()
        settings.update(kwargs)
        super(ImageNode, self).__init__(type="elem image", **settings)
        self.__formatter = "{element_type} {id} {width}x{height}"
        if matrix is None:
            matrix = Matrix()

        self.matrix = matrix
        if "href" in settings:
            try:
                from PIL import Image as PILImage

                self.image = PILImage.open(settings["href"])
                if "x" in settings:
                    self.matrix.post_translate_x(settings["x"])
                if "y" in settings:
                    self.matrix.post_translate_x(settings["y"])
                real_width, real_height = self.image.size
                declared_width, declared_height = real_width, real_height
                if "width" in settings:
                    declared_width = settings["width"]
                if "height" in settings:
                    declared_height = settings["height"]
                try:
                    sx = declared_width / real_width
                    sy = declared_height / real_height
                    self.matrix.post_scale(sx, sy)
                except ZeroDivisionError:
                    pass
            except ImportError:
                self.image = None
        else:
            self.image = image

        self.settings = settings
        self.overscan = overscan
        self.direction = direction
        self.dpi = dpi
        self.step_x = None
        self.step_y = None
        self.label = label
        self.lock = False

        self.invert = False if invert is None else invert
        self.red = 1.0 if red is None else red
        self.green = 1.0 if green is None else green
        self.blue = 1.0 if blue is None else blue
        self.lightness = 1.0 if lightness is None else lightness
        self.dither = True if dither is None else dither
        self.dither_type = "Floyd-Steinberg" if dither_type is None else dither_type

        if operations is None:
            operations = list()
        self.operations = operations

        self._needs_update = False
        self._update_thread = None
        self._update_lock = threading.Lock()
        self.processed_image = None
        self.processed_matrix = None
        self.process_image_failed = False
        self.view_invert = False
        self.text = None

    def __copy__(self):
        return ImageNode(
            image=self.image,
            matrix=copy(self.matrix),
            overscan=self.overscan,
            direction=self.direction,
            dpi=self.dpi,
            operations=self.operations,
            invert=self.invert,
            dither=self.dither,
            dither_type=self.dither_type,
            red=self.red,
            green=self.green,
            blue=self.blue,
            lightness=self.lightness,
            settings=self.settings,
        )

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.type}', {str(self.image)}, {str(self._parent)})"

    @property
    def active_image(self):
        if self.processed_image is not None:
            return self.processed_image
        else:
            return self.image

    @property
    def active_matrix(self):
        if self.processed_matrix is None:
            return self.matrix
        return self.processed_matrix * self.matrix

    def preprocess(self, context, matrix, commands):
        """
        Preprocess step during the cut planning stages.

        We require a context to calculate the correct step values relative to the device
        """
        self.step_x, self.step_y = context.device.dpi_to_steps(self.dpi)
        self.matrix *= matrix
        self.set_dirty_bounds()
        self.process_image()

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
        default_map = super(ImageNode, self).default_map(default_map=default_map)
        default_map.update(self.settings)
        image = self.active_image
        default_map["width"] = image.width
        default_map["height"] = image.height
        default_map["element_type"] = "Image"
        default_map["matrix"] = self.matrix
        default_map["dpi"] = self.dpi
        default_map["overscan"] = self.overscan
        default_map["direction"] = self.direction
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
        self.text = "Processing..."
        context.signal("refresh_scene", "Scene")
        if self._update_thread is None:

            def clear(result):
                if self.process_image_failed:
                    self.text = "Process image could not exist in memory."
                else:
                    self.text = None
                self._needs_update = False
                self._update_thread = None
                context.signal("refresh_scene", "Scene")
                context.signal("image updated", self)

            self.processed_image = None
            # self.processed_matrix = None
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
            self.process_image()
            # Unset cache.
            self.wx_bitmap_image = None
            self.cache = None

    def process_image(self, crop=True):
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

        try:
            self._process_image(crop=crop)
            self.process_image_failed = False
        except (MemoryError, Image.DecompressionBombError):
            self.process_image_failed = True
        self.altered()

    def _process_image(self, crop=True):
        """
        This core code replaces the older actualize and rasterwizard functionalities. It should convert the image to
        a post-processed form with resulting post-process matrix. Which should be combined with the main matrix to get
        the relevant combined matrix values.

        @param crop: Should the unneeded edges be cropped as part of this process. The need for the edge is determined
            by the color and the state of the self.invert attribute.
        @return:
        """
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps

        from meerk40t.image.imagetools import dither

        # Calculate device real step.
        if self.step_x is None:
            step = UNITS_PER_INCH / self.dpi
            self.step_x = step
            self.step_y = step
        step_x, step_y = self.step_x, self.step_y
        assert step_x != 0
        assert step_y != 0

        image = self.image
        main_matrix = self.matrix

        # Precalculate RGB for L conversion.
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

        transform_is_needed = (
            main_matrix.a != step_x
            or main_matrix.b != 0.0
            or main_matrix.c != 0.0
            or main_matrix.d != step_y
        )

        # Create Transparency Mask.
        if "transparency" in image.info:
            image = image.convert("RGBA")
        try:
            transparent_mask = image.getchannel("A").point(lambda e: 255 - e)
        except ValueError:
            transparent_mask = None

        matrix = copy(main_matrix)  # Prevent Knock-on effect.

        # Convert image to L type.
        if image.mode != "L":
            image = image.convert("RGB")
            image = image.convert("L", matrix=(r, g, b, 1.0))

        # Paste Transparency mask.
        if transparent_mask:
            # Fill in original transparent values with reject pixels
            background = image.copy()
            reject = Image.new("L", image.size, "black" if self.invert else "white")
            background.paste(reject, mask=transparent_mask)
            image = background

        # Calculate image box.
        box = None
        if crop:
            try:
                # Get the bbox cutting off the white edges.
                if self.invert:
                    box = image.getbbox()
                else:
                    box = image.point(lambda e: 255 - e).getbbox()
            except ValueError:
                pass
        if box is None:
            # If box is entirely white, bbox caused value error, or crop not set.
            box = (0, 0, image.width, image.height)

        # Find the boundary points of the rotated box edges.
        boundary_points = [
            matrix.point_in_matrix_space([box[0], box[1]]),  # Top-left
            matrix.point_in_matrix_space([box[2], box[1]]),  # Top-right
            matrix.point_in_matrix_space([box[0], box[3]]),  # Bottom-left
            matrix.point_in_matrix_space([box[2], box[3]]),  # Bottom-right
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
        matrix.post_translate(-tx, -ty)
        matrix.post_scale(step_scale_x, step_scale_y)
        if step_y < 0:
            # If step_y is negative, translate
            matrix.post_translate(0, image_height)
        if step_x < 0:
            # If step_x is negative, translate
            matrix.post_translate(image_width, 0)
        try:
            matrix.inverse()
        except ZeroDivisionError:
            # Rare crash if matrix is malformed and cannot invert.
            matrix.reset()
            matrix.post_translate(-tx, -ty)
            matrix.post_scale(step_scale_x, step_scale_y)

        # Perform image transform if needed.
        if transform_is_needed:
            if image_height <= 0:
                image_height = 1
            if image_width <= 0:
                image_width = 1
            image = image.transform(
                (image_width, image_height),
                Image.AFFINE,
                (matrix.a, matrix.c, matrix.e, matrix.b, matrix.d, matrix.f),
                resample=Image.BICUBIC,
                fillcolor="black" if self.invert else "white",
            )
            matrix.reset()
        else:
            matrix = copy(main_matrix)

        # If crop applies, apply crop.
        if crop:
            box = None
            try:
                if self.invert:
                    box = image.getbbox()
                else:
                    box = image.point(lambda e: 255 - e).getbbox()
            except ValueError:
                pass
            if box is not None:
                width = box[2] - box[0]
                height = box[3] - box[1]
                if width != image_width or height != image_height:
                    image = image.crop(box)
                    matrix.post_translate(box[0], box[1])

        if step_y < 0:
            # if step_y is negative, translate.
            matrix.post_translate(0, -image_height)
        if step_x < 0:
            # if step_x is negative, translate.
            matrix.post_translate(-image_width, 0)

        matrix.post_scale(step_x, step_y)
        matrix.post_translate(tx, ty)
        actualized_matrix = matrix

        # Invert black to white if needed.
        if self.invert:
            image = ImageOps.invert(image)

        # Find rejection mask of white pixels.
        reject_mask = image.point(lambda e: 0 if e == 255 else 255)

        # Process operations.
        for op in self.operations:
            name = op["name"]
            if name == "crop":
                try:
                    if op["enable"] and op["bounds"] is not None:
                        crop = op["bounds"]
                        left = int(crop[0])
                        upper = int(crop[1])
                        right = int(crop[2])
                        lower = int(crop[3])
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

        # Remask image removing pixels that were white before operations were processed.
        background = Image.new("L", image.size, "white")
        background.paste(image, mask=reject_mask)
        image = background

        # Dither image to 1 bit.
        if self.dither and self.dither_type is not None:
            if self.dither_type != "Floyd-Steinberg":
                image = dither(image, self.dither_type)
            image = image.convert("1")

        # Set final values.
        inverted_main_matrix = Matrix(main_matrix).inverse()
        self.processed_matrix = actualized_matrix * inverted_main_matrix
        self.processed_image = image

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
