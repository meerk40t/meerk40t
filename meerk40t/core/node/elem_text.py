import re
from copy import copy
from math import ceil, floor, tau

from PIL import Image

from meerk40t.core.node.mixins import FunctionalParameter, Stroked
from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_INCH, UNITS_PER_POINT, Length
from meerk40t.svgelements import (
    SVG_ATTR_FONT_FAMILY,
    SVG_ATTR_FONT_SIZE,
    SVG_ATTR_FONT_STRETCH,
    SVG_ATTR_FONT_STYLE,
    SVG_ATTR_FONT_VARIANT,
    SVG_ATTR_FONT_WEIGHT,
    Matrix,
)

REGEX_CSS_FONT = re.compile(
    r"^"
    r"(?:"
    r"(?:(normal|italic|oblique)\s)?"
    r"(?:(normal|small-caps)\s)?"
    r"(?:(normal|bold|bolder|lighter|[0-9]{3})\s)?"
    r"(?:(normal|(?:ultra-|extra-|semi-)?condensed|(?:semi-|extra-)?expanded)\s)"
    r"?){0,4}"
    r"(?:"
    r"((?:x-|xx-)?small|medium|(?:x-|xx-)?large|larger|smaller|[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?"
    r"(?:em|pt|pc|px|%)?)"
    r"(?:/"
    r"((?:x-|xx-)?small|medium|(?:x-|xx-)?large|larger|smaller|[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?"
    r"(?:em|pt|pc|px|%)?)"
    r")?\s"
    r")?"
    r"([^;]*);?"
    r"$"
)
REGEX_CSS_FONT_FAMILY = re.compile(
    # r"""(?:([^\s"';,]+|"[^";,]+"|'[^';,]+'|serif|sans-serif|cursive|fantasy|monospace)),?\s*;?"""
    r"\s*'[^']+'|\s*\"[^\"]+\"|[^,\s]+"
)


class TextNode(Node, Stroked, FunctionalParameter):
    """
    TextNode is the bootstrapped node type for the 'elem text' type.
    """

    def __init__(self, **kwargs):
        self.text = None
        self.anchor = "start"  # start, middle, end.
        self.baseline = "hanging"
        self.matrix = None
        self.fill = None
        self.stroke = None
        self.stroke_width = 0
        self.stroke_scale = True
        self._stroke_zero = None
        self.underline = False
        self.strikethrough = False
        # For sake of completeness, afaik there is no way to display it with wxpython
        self.overline = False
        self.texttransform = ""
        self.width = None
        self.height = None
        self.descent = None
        self.leading = None
        self.raw_bbox = None
        self.path = None
        self.font_style = "normal"
        self.font_variant = "normal"
        self.font_weight = 400
        self.font_stretch = "normal"
        self.font_size = 16.0  # 16px font 'normal' 12pt font
        self.line_height = 16.0
        self.font_family = "sans-serif"
        # We store the bitmap representation of the text
        self._magnification = 2
        self._dpi = 72 * self._magnification
        self._image = None
        self._processed_image = None
        self._processed_matrix = None
        self._process_image_failed = False
        self._generator = None

        # Offset values to allow fixing the drawing of slanted fonts. Without GetTextExtentBoundaries
        self.offset_x = 0
        self.offset_y = 0
        if "font" in kwargs:
            font = kwargs["font"]
            del kwargs["font"]
        else:
            font = None
        super().__init__(type="elem text", **kwargs)

        # We might have relevant forn-information hidden inside settings...
        rotangle = 0
        if "settings" in kwargs:
            kwa = kwargs["settings"]
            # for prop in kwa:
            #     v = getattr(self, prop, None)
            #     print (f"{prop}, kwa={kwargs['settings'][prop]}, v={v}")
            if "font-size" in kwa:
                self.font_size = kwa["font-size"]
            if "font-weight" in kwa:
                self.font_weight = kwa["font-weight"]
            if "font-family" in kwa:
                self.font_family = kwa["font-family"]
            if "rotate" in kwa:
                try:
                    rotangle = float(kwa["rotate"])
                    while rotangle >= 360:
                        rotangle -= 360
                    while rotangle <= -360:
                        rotangle += 360
                except ValueError:
                    rotangle = 0
                # Don't leave it, elsewise it will be reapplied when copying this node
                del kwa["rotate"]
            self.validate_font()
        self.text = str(self.text)
        self._formatter = "{element_type} {id}: {text}"
        if self.matrix is None:
            self.matrix = Matrix()
        try:
            # If there is an x or y this is an SVG pretranslate offset.
            self.matrix.pre_translate(self.x, self.y)
            # It must be deleted to avoid applying it again to copies.
            del self.x
            del self.y
        except AttributeError:
            pass
        if rotangle != 0:
            rotangle = rotangle / 360 * tau
            self.matrix.pre_rotate(rotangle)

        self.bounds_with_variables_translated = None

        if font is not None:
            self.parse_font(font)
        else:
            self.font_size = getattr(self, SVG_ATTR_FONT_SIZE, self.font_size)
            self.font_style = getattr(self, SVG_ATTR_FONT_STYLE, self.font_style)
            self.font_variant = getattr(self, SVG_ATTR_FONT_VARIANT, self.font_variant)
            self.font_weight = getattr(self, SVG_ATTR_FONT_WEIGHT, self.font_weight)
            self.font_stretch = getattr(self, SVG_ATTR_FONT_STRETCH, self.font_stretch)
            self.font_family = getattr(self, SVG_ATTR_FONT_FAMILY, self.font_family)
            self.validate_font()
        if self._stroke_zero is None:
            # This defines the stroke-width zero point scale
            self.stroke_width_zero()

    def __copy__(self):
        nd = self.node_dict
        nd["matrix"] = copy(self.matrix)
        nd["stroke"] = copy(self.stroke)
        nd["stroke_width"] = copy(self.stroke_width)
        nd["fill"] = copy(self.fill)
        newnode = TextNode(**nd)
        newnode._generator = self._generator
        newnode._image = self._image
        return newnode

    @property
    def font(self):
        return (
            f"{self.font_style if self.font_style else 'normal'} "
            f"{self.font_variant if self.font_variant else 'normal'} "
            f"{self.weight} "
            f"{self.font_size}/{self.line_height} "
            f"{self.font_family.strip() if self.font_family else 'san-serif'};"
        )

    @font.setter
    def font(self, value):
        self.parse_font(value)

    def update_image(self, image):
        if image is None:
            s = "None"
        else:
            s = f"{image.width}x{image.height} ({image.mode})"
        # print (f"update image {s}")
        self._image = image
        self._processed_image = None
        self._cache = None
        self.set_dirty_bounds()


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
        Get the bbox cutting off the reject edges.
        @param image: Image to get crop box for.
        @return:
        """
        try:
            return image.point(lambda e: 255 - e).getbbox()
        except ValueError:
            return None


    def _process_image(self, step_x, step_y):
        """
        This core code replaces the older actualize and rasterwizard functionalities. It should convert the image to
        a post-processed form with resulting post-process matrix.

        @param crop: Should the unneeded edges be cropped as part of this process. The need for the edge is determined
            by the color and the state of the self.invert attribute.
        @return:
        """

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

        image = self._image.convert("L")

        transparent_mask = self._get_transparent_mask(image)

        image = self._apply_mask(image, transparent_mask)

        # Calculate image box.
        box = None
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
                fillcolor="white",
            )
        actualized_matrix = Matrix()

        if step_y < 0:
            # if step_y is negative, translate.
            actualized_matrix.post_translate(0, -image_height)
        if step_x < 0:
            # if step_x is negative, translate.
            actualized_matrix.post_translate(-image_width, 0)

        # If crop applies, apply crop.
        cbox = self._get_crop_box(image)
        if cbox is not None:
            width = cbox[2] - cbox[0]
            height = cbox[3] - cbox[1]
            if width != image.width or height != image.height:
                image = image.crop(cbox)
                # We did not crop the image so far, but we already applied
                # the cropped transformation! That may be faulty, and needs to
                # be corrected at a later stage, but this logic, even if clumsy
                # is good enough: don't shift things twice!
                if orgbox[0] == 0 and orgbox[1] == 0:
                    actualized_matrix.post_translate(cbox[0], cbox[1])

        actualized_matrix.post_scale(step_x, step_y)
        actualized_matrix.post_translate(tx, ty)

        # Find rejection mask of white pixels. (already inverted)
        reject_mask = image.point(lambda e: 0 if e == 255 else 255)

        background = Image.new("L", image.size, "white")
        background.paste(image, mask=reject_mask)
        image = background

        return actualized_matrix, image


    def process_image(self, step_x, step_y):
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
            actualized_matrix, image = self._process_image(step_x, step_y)
            inverted_main_matrix = Matrix(self.matrix).inverse()
            self._processed_matrix = actualized_matrix * inverted_main_matrix
            self._processed_image = image
            self._process_image_failed = False
            bb = self.bbox()
            self._bounds = bb
            self._paint_bounds = bb
        except (
            MemoryError,
            Image.DecompressionBombError,
            ValueError,
            ZeroDivisionError,
        ) as e:
            # Memory error if creating requires too much memory.
            # DecompressionBomb if over 272 megapixels.
            # ValueError if bounds are NaN.
            # ZeroDivide if inverting the processed matrix cannot happen because image is a line
            # print (f"Error: {e}")
            self._process_image_failed = True

    @property
    def active_image(self):
        if self._image is None and self._generator is not None:
            # print ("Generation needed")
            # Let's update the image...
            self._generator(self)

        if self._processed_image is None:
            # print ("Processing needed")
            step = UNITS_PER_INCH / self._dpi
            step_x = step
            step_y = step
            self.process_image(step_x, step_y)
        if self._processed_image is not None:
            return self._processed_image
        else:
            return self._image

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
        commands = plan.commands
        if self.parent.type != "op raster":
            commands.append(self.remove_text)
            return
        self.text = context.elements.wordlist_translate(self.text, self)
        step_x, step_y = context.device.view.dpi_to_steps(self._dpi)
        self.matrix *= matrix
        self.set_dirty_bounds()
        self.process_image(step_x, step_y)

    def remove_text(self):
        self.remove_node()

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "Text"
        default_map.update(self.__dict__)
        return default_map

    def drop(self, drag_node, modify=True):
        # Dragging element into element.
        if hasattr(drag_node, "as_geometry") or hasattr(drag_node, "as_image"):
            if modify:
                self.insert_sibling(drag_node)
            return True
        elif drag_node.type.startswith("op"):
            # If we drag an operation to this node,
            # then we will reverse the game
            return drag_node.drop(self, modify=modify)
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

    def parse_font(self, font):
        """
        CSS Fonts 3 has a shorthand font property which serves to provide a single location to define:
        `font-style`, `font-variant`, `font-weight`, `font-stretch`, `font-size`, `line-height`, and `font-family`

        font-style: normal | italic | oblique
        font-variant: normal | small-caps
        font-weight: normal | bold | bolder | lighter | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900
        font-stretch: normal | ultra-condensed | extra-condensed | condensed | semi-condensed | semi-expanded | expanded | extra-expanded | ultra-expanded
        font-size: <absolute-size> | <relative-size> | <length-percentage>
        line-height: '/' <`line-height`>
        font-family: [ <family-name> | <generic-family> ] #
        generic-family:  `serif`, `sans-serif`, `cursive`, `fantasy`, and `monospace`
        """
        # https://www.w3.org/TR/css-fonts-3/#font-prop

        match = REGEX_CSS_FONT.match(font)
        if not match:
            # This is not a qualified shorthand font.
            return
        self.font_style = match.group(1)
        if self.font_style is None:
            self.font_style = "normal"

        self.font_variant = match.group(2)
        if self.font_variant is None:
            self.font_variant = "normal"

        self.font_weight = match.group(3)
        if self.font_weight is None:
            self.font_weight = "normal"

        self.font_stretch = match.group(4)
        if self.font_stretch is None:
            self.font_stretch = "normal"

        self.font_size = match.group(5)
        if self.font_size is None:
            self.font_size = "12pt"
        self.line_height = match.group(6)
        self.font_family = match.group(7)
        self.validate_font()

    def validate_font(self):
        if self.line_height is None:
            self.line_height = "12pt" if self.font_size is None else "100%"
        if self.font_size and isinstance(self.font_size, str):
            size = self.font_size
            try:
                self.font_size = Length(self.font_size, unitless=UNITS_PER_POINT).pt
                if self.font_size == 0:
                    self.font_size = size
            except ValueError:
                pass
        if self.line_height:
            height = self.line_height
            try:
                self.line_height = float(
                    Length(
                        self.line_height,
                        relative_length=f"{self.font_size}pt",
                        unitless=UNITS_PER_POINT,
                    ).pt
                )
                if self.line_height == 0:
                    self.line_height = height
            except ValueError:
                pass

    @property
    def font_list(self):
        result = []
        if self.font_family is not None:
            fonts = re.findall(REGEX_CSS_FONT_FAMILY, self.font_family)
            if len(fonts) == 0:
                result.append(
                    self.font_family[1:-1]
                    if self.font_family.startswith('"')
                    or self.font_family.startswith("'")
                    else self.font_family
                )
            else:
                if not "'" in self.font_family and not '"' in self.font_family:
                    # Just for the sake of checking, add the full string -
                    # this is most of the time the correct choice...
                    result.append(self.font_family)
                for font in fonts:
                    result.append(
                        font[1:-1]
                        if font.startswith('"') or font.startswith("'")
                        else font
                    )
        return result

    @property
    def weight(self):
        """
        This does not correctly parse weights for bolder or lighter. Those are relative to the previous set
        font-weight and that is generally unknown in this context.
        """
        if self.font_weight == "bold":
            return 700
        elif self.font_weight == "normal":
            return 400
        elif self.font_weight == "lighter":
            return 200  # Really this should be lighter than parent font.
        elif self.font_weight == "bolder":
            return 900  # Really this should be bolder than parent font.
        try:
            return int(self.font_weight)
        except (ValueError, TypeError):
            return 400

    def bbox(self, transformed=True, with_stroke=False):
        """
        Get the bounding box for the given text object.
        To perform this action one of two things should be true. Path should exist, or we should have
        defined width, height, offset_x and offset_y values.
        """
        image = self.active_image
        image_width, image_height = image.size
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

    def updated(self):
        self.update_image(None)
        super().updated()

    def modified(self):
        self.update_image(None)
        super().modified()

    def set_generator(self, routine):
        self._generator = routine

    @property
    def paint_bounds(self):
        return self.bounds