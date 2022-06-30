import threading
from copy import copy

from PIL.Image import DecompressionBombError

from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_INCH
from meerk40t.image.imagetools import RasterScripts
from meerk40t.svgelements import Matrix


class ImageNode(Node):
    """
    ImageNode is the bootstrapped node type for the 'elem image' type.

    ImageNode contains a main matrix, main image. A processed image and a processed matrix.
    The processed matrix must be concated with the main matrix to be accurate.
    """

    def __init__(
        self,
        image=None,
        matrix=None,
        overscan=None,
        direction=None,
        dpi=500,
        operations=None,
        **kwargs,
    ):
        super(ImageNode, self).__init__(type="elem image", **kwargs)
        if "href" in kwargs:
            self.matrix = Matrix()
            try:
                from PIL import Image as PILImage
                self.image = PILImage.open(kwargs['href'])
                if "x" in kwargs:
                    self.matrix.post_translate_x(kwargs["x"])
                if "y" in kwargs:
                    self.matrix.post_translate_x(kwargs["y"])
                real_width, real_height = self.image.size
                declared_width, declared_height = real_width, real_height
                if "width" in kwargs:
                    declared_width = kwargs["width"]
                if "height" in kwargs:
                    declared_height = kwargs["height"]
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
            self.matrix = matrix
        self.processed_image = None
        self.processed_matrix = None
        self.process_image_failed = False
        self.text = None

        self._needs_update = False
        self._update_thread = None
        self._update_lock = threading.Lock()

        self.settings = kwargs
        self.overscan = overscan
        self.direction = direction
        self.dpi = dpi
        self.step_x = None
        self.step_y = None
        self.lock = False

        self.invert = False
        self.red = 1.0
        self.green = 1.0
        self.blue = 1.0
        self.lightness = 1.0
        self.view_invert = False
        self.dither = True
        self.dither_type = "Floyd-Steinberg"

        if operations is None:
            operations = list()
        self.operations = operations

    def __copy__(self):
        return ImageNode(
            image=self.image,
            matrix=copy(self.matrix),
            overscan=self.overscan,
            direction=self.direction,
            dpi=self.dpi,
            operations=self.operations,
            **self.settings,
        )

    def __repr__(self):
        return "%s('%s', %s, %s)" % (
            self.__class__.__name__,
            self.type,
            str(self.image),
            str(self._parent),
        )

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
        self._bounds_dirty = True
        self.process_image()

    @property
    def bounds(self):
        if self._bounds_dirty:
            image_width, image_height = self.active_image.size
            matrix = self.active_matrix
            x0, y0 = matrix.point_in_matrix_space((0, 0))
            x1, y1 = matrix.point_in_matrix_space((image_width, image_height))
            x2, y2 = matrix.point_in_matrix_space((0, image_height))
            x3, y3 = matrix.point_in_matrix_space((image_width, 0))
            self._bounds_dirty = False
            self._bounds = (
                min(x0, x1, x2, x3),
                min(y0, y1, y2, y3),
                max(x0, x1, x2, x3),
                max(y0, y1, y2, y3),
            )
        return self._bounds

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

    def drop(self, drag_node):
        # Dragging element into element.
        if drag_node.type.startswith("elem"):
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
            self.processed_matrix = None
            self._update_thread = context.threaded(
                self.process_image_thread, result=clear, daemon=True
            )

    def process_image_thread(self):
        while self._needs_update:
            self._needs_update = False
            self.process_image()
            # Unset cache.
            self.wx_bitmap_image = None
            self.cache = None

    def process_image(self):
        if self.step_x is None:
            step = UNITS_PER_INCH / self.dpi
            self.step_x = step
            self.step_y = step

        from PIL import Image, ImageEnhance, ImageFilter, ImageOps

        from meerk40t.image.actualize import actualize
        from meerk40t.image.imagetools import dither

        image = self.image
        main_matrix = self.matrix

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
        if image.mode != "L":
            image = image.convert("RGB")
            image = image.convert("L", matrix=[r, g, b, 1.0])
        if self.invert:
            image = image.point(lambda e: 255 - e)

        # Calculate device real step.
        step_x, step_y = self.step_x, self.step_y
        if (
            main_matrix.a != step_x
            or main_matrix.b != 0.0
            or main_matrix.c != 0.0
            or main_matrix.d != step_y
        ):
            try:
                image, actualized_matrix = actualize(
                    image,
                    main_matrix,
                    step_x=step_x,
                    step_y=step_y,
                    inverted=self.invert,
                )
            except (MemoryError, DecompressionBombError):
                self.process_image_failed = True
                return
        else:
            actualized_matrix = Matrix(main_matrix)

        if self.invert:
            empty_mask = image.convert("L").point(lambda e: 0 if e == 0 else 255)
        else:
            empty_mask = image.convert("L").point(lambda e: 0 if e == 255 else 255)
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

        if empty_mask is not None:
            background = Image.new(image.mode, image.size, "white")
            background.paste(image, mask=empty_mask)
            image = background  # Mask exists use it to remove any pixels that were pure reject.

        if self.dither and self.dither_type is not None:
            if self.dither_type != "Floyd-Steinberg":
                image = dither(image, self.dither_type)
            image = image.convert("1")
        inverted_main_matrix = Matrix(main_matrix).inverse()
        self.processed_matrix = actualized_matrix * inverted_main_matrix
        self.processed_image = image
        # self.matrix = actualized_matrix
        self.altered()
        self.process_image_failed = False

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
