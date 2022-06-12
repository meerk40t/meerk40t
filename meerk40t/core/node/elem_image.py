import threading
from copy import copy

from meerk40t.core.node.layernode import LayerNode
from meerk40t.core.node.node import Node
from meerk40t.image.imagetools import RasterScripts
from meerk40t.svgelements import Matrix


class ImageNode(Node):
    """
    ImageNode is the bootstrapped node type for the 'elem image' type.

    ImageNode contains a main matrix and some number of images with matrix offsets. The main matrix and the image
    matrix are concatted to find the current image
    """

    def __init__(
        self,
        image=None,
        matrix=None,
        overscan=None,
        direction=None,
        dpi=500,
        step_x=None,
        step_y=None,
        **kwargs,
    ):
        super(ImageNode, self).__init__(type="elem image", **kwargs)
        self.images = {"default": [image, Matrix()]}
        self.active = "default"
        self.matrix = matrix  # global matrix.
        self.text = None

        self.settings = kwargs
        self.overscan = overscan
        self.direction = direction
        self.dpi = dpi
        self.step_x = step_x
        self.step_y = step_y
        self.lock = False

        self.invert = False
        self.red = 1.0
        self.green = 1.0
        self.blue = 1.0
        self.lightness = 1.0
        self.view_invert = False
        self.dither = True
        self.dither_type = "Floyd-Steinberg"

        self.operations = list()

        self._needs_update = False
        self._context = None
        self._update_thread = None
        self._update_lock = threading.Lock()

    @property
    def image(self):
        return self.get_image(self.active)

    @property
    def active_matrix(self):
        return self.get_combined_matrix(self.active)

    def __copy__(self):
        return ImageNode(
            image=self.image,
            matrix=copy(self.active_matrix),
            overscan=self.overscan,
            direction=self.direction,
            dpi=self.dpi,
            step_x=self.step_x,
            step_y=self.step_y,
            **self.settings,
        )

    def __repr__(self):
        return "%s('%s', %s, %s)" % (
            self.__class__.__name__,
            self.type,
            str(self.image),
            str(self._parent),
        )

    def get_image(self, name):
        return self.images.get(name)[0]

    def get_matrix(self, name):
        return self.images.get(name)[1]

    def get_combined_matrix(self, name):
        return self.get_matrix(name) * self.matrix

    def preprocess(self, context, matrix, commands):
        self._context = context
        self.process_image()
        self._context = None
        self.active = "processed"
        self.matrix *= matrix
        self._bounds_dirty = True

    @property
    def bounds(self):
        if self._bounds_dirty:
            image_width, image_height = self.image.size
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
        default_map["width"] = self.image.width
        default_map["height"] = self.image.height
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
        self._context = context
        self._needs_update = True
        self.text = "Processing..."
        self._context.signal("refresh_scene", "Scene")
        if self._update_thread is None:

            def clear(result):
                self.text = None
                self._needs_update = False
                self._update_thread = None
                self._context.signal("refresh_scene", "Scene")
                self._context = None

            self._update_thread = context.threaded(
                self.process_image_thread, result=clear, daemon=True
            )

    def process_image_thread(self):
        if self._context is None:
            return  # Requires temporary context.
        while self._needs_update:
            self._needs_update = False
            self.process_image()
            # Unset cache.
            self.wx_bitmap_image = None
            self.cache = None
            self._context.signal("image updated", self)

    def process_image(self):
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
        from meerk40t.image.actualize import actualize
        from meerk40t.image.imagetools import dither

        try:
            image, matrix = self.images["default"]
        except KeyError:
            return

        matrix = matrix * self.matrix

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

        dpi = self.dpi
        step_x, step_y = self._context.device.dpi_to_steps(dpi)
        self.step_x, self.step_y = step_x, step_y

        m = matrix
        if m.a != step_x or m.b != 0.0 or m.c != 0.0 or m.d != step_y:
            image, amatrix = actualize(
                image, matrix, step_x=step_x, step_y=step_y, inverted=self.invert
            )
        else:
            amatrix = Matrix(matrix)

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
        m = Matrix(matrix).inverse()
        self.images["processed"] = (image, amatrix * m)
        self.images["default"][1] = Matrix()
        self.active = "processed"
        self.layers_changed()
        self.altered()

    def layers_changed(self):
        self.remove_all_children()
        for name in self.images:
            node = LayerNode(layer_name=name)
            self.add_node(node)

    def activate(self, layer):
        self.active = layer
        self.altered()

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
