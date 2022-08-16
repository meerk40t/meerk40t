import re
from copy import copy
from math import sqrt

from meerk40t.core.node.node import Node
from meerk40t.core.units import Length
from meerk40t.svgelements import Matrix

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
    r"""(?:([^\s"';,]+|"[^";,]+"|'[^';,]+'|serif|sans-serif|cursive|fantasy|monospace)),?\s*;?"""
)


class TextNode(Node):
    """
    TextNode is the bootstrapped node type for the 'elem text' type.
    """

    def __init__(
        self,
        text=None,
        x=0,
        y=0,
        font=None,
        anchor=None,
        matrix=None,
        fill=None,
        stroke=None,
        stroke_width=0,
        stroke_scale=True,
        underline=None,
        strikethrough=None,
        overline=None,
        texttransform=None,
        width=None,
        height=None,
        path=None,
        **kwargs,
    ):
        super(TextNode, self).__init__(type="elem text", **kwargs)
        self._formatter = "{element_type} {id}: {text}"
        self.text = text
        self.settings = kwargs
        self.matrix = Matrix() if matrix is None else matrix
        self.fill = fill
        self.stroke = stroke
        self.stroke_width = stroke_width
        self._stroke_scaled = stroke_scale
        if x != 0 or y != 0:
            matrix.pre_translate(x, y)

        self.font_style = "normal"
        self.font_variant = "normal"
        self.font_weight = 400
        self.font_stretch = "normal"
        self.font_size = 16.0  # 16px font 'normal' 12pt font
        self.line_height = 16.0
        self.font_family = "san-serif"
        if font is not None:
            self.parse_font(font)

        self.underline = False if underline is None else underline
        self.strikethrough = False if strikethrough is None else strikethrough

        # For sake of completeness, afaik there is no way to display it with wxpython
        self.overline = False if overline is None else overline
        self.texttransform = "" if texttransform is None else texttransform

        self.anchor = "start" if anchor is None else anchor  # start, middle, end.

        self.width = width
        self.height = height
        self.path = path
        self.lock = False

    def __copy__(self):
        return TextNode(
            text=self.text,
            matrix=copy(self.matrix),
            fill=copy(self.fill),
            stroke=copy(self.stroke),
            stroke_width=self.stroke_width,
            stroke_scale=self._stroke_scaled,
            font=self.font,
            anchor=self.anchor,
            underline=self.underline,
            strikethrough=self.strikethrough,
            overline=self.overline,
            texttransform=self.texttransform,
            width=self.width,
            height=self.height,
            path=self.path,
            **self.settings,
        )

    @property
    def font(self):
        return (
            f"{self.font_style} "
            f"{self.font_variant} "
            f"{self.weight} "
            f"{self.font_size}/{self.line_height} "
            f"{self.font_family};"
        )

    @font.setter
    def font(self, value):
        self.parse_font(value)

    @property
    def stroke_scaled(self):
        return self._stroke_scaled

    @stroke_scaled.setter
    def stroke_scaled(self, v):
        if not v and self._stroke_scaled:
            matrix = self.matrix
            self.stroke_width *= sqrt(abs(matrix.determinant))
        if v and not self._stroke_scaled:
            matrix = self.matrix
            self.stroke_width /= sqrt(abs(matrix.determinant))
        self._stroke_scaled = v

    def implied_stroke_width(self, zoomscale=1.0):
        """If the stroke is not scaled, the matrix scale will scale the stroke, and we
        need to countermand that scaling by dividing by the square root of the absolute
        value of the determinant of the local matrix (1d matrix scaling)"""
        scalefactor = 1.0 if self._stroke_scaled else sqrt(abs(self.matrix.determinant))
        sw = self.stroke_width / scalefactor
        limit = 25 * sqrt(zoomscale) * scalefactor
        if sw < limit:
            sw = limit
        return sw

    @property
    def bounds(self):
        if self._bounds_dirty:
            self._bounds_dirty = False
            self._bounds = self.bbox(with_stroke=True)
        return self._bounds

    def preprocess(self, context, matrix, commands):
        if self.parent.type != "op raster":
            commands.append(self.remove_text)
            return
        self.text = context.elements.mywordlist.translate(self.text)
        self.stroke_scaled = True
        self.matrix *= matrix
        self.stroke_scaled = False
        self._bounds_dirty = True

    def remove_text(self):
        self.remove_node()

    def default_map(self, default_map=None):
        default_map = super(TextNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Text"
        default_map.update(self.settings)
        default_map["text"] = self.text
        default_map["stroke"] = self.stroke
        default_map["fill"] = self.fill
        default_map["stroke-width"] = self.stroke_width
        default_map["matrix"] = self.matrix
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
        if self.font_size:
            size = self.font_size
            try:
                self.font_size = float(Length(self.font_size, unitless=1))
                if self.font_size == 0:
                    self.font_size = size
            except ValueError:
                pass
        if self.line_height:
            height = self.line_height
            try:
                self.line_height = float(
                    Length(self.line_height, relative_length=self.font_size, unitless=1)
                )
                if self.line_height == 0:
                    self.line_height = height
            except ValueError:
                pass

    @property
    def font_list(self):
        return [
            family[1:-1] if family.startswith('"') or family.startswith("'") else family
            for family in REGEX_CSS_FONT_FAMILY.findall(self.font_family)
        ]

    @property
    def weight(self):
        """
        This does not correctly parse weights for bolder or lighter. Those are relative to the previous set
        font-weight and that is generally unknown in this context.
        """
        if self.font_weight == "bold":
            return 700
        if self.font_weight == "normal":
            return 400
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
        if self.path is not None:
            return (self.path * self.matrix).bbox(
                transformed=True,
                with_stroke=with_stroke,
            )

        if self.width:
            width = self.width
        else:
            # Width is undefined, make an educated guess
            width = len(self.text) * self.font_size

        if self.height:
            height = self.height
        else:
            # Height is undefined, make an educated guess
            height = (
                -self.line_height * len(list(self.text.split("\n"))) - self.font_size
            )
        ymin = -height
        ymax = 0
        if self.anchor == "middle":
            xmin = -width / 2
            xmax = width / 2
        elif self.anchor == "end":
            xmin = -width
            xmax = 0
        else:  # "start"
            xmax = width
            xmin = 0

        if transformed:
            p0 = self.matrix.transform_point([xmin, ymin])
            p1 = self.matrix.transform_point([xmin, ymax])
            p2 = self.matrix.transform_point([xmax, ymin])
            p3 = self.matrix.transform_point([xmax, ymax])
            xmin = min(p0[0], p1[0], p2[0], p3[0])
            ymin = min(p0[1], p1[1], p2[1], p3[1])
            xmax = max(p0[0], p1[0], p2[0], p3[0])
            ymax = max(p0[1], p1[1], p2[1], p3[1])

        delta = 0.0
        if (
            with_stroke
            and self.stroke_width is not None
            and not (self.stroke is None or self.stroke.value is None)
        ):
            delta = (
                float(self.implied_stroke_width())
                if transformed
                else float(self.stroke_width)
            ) / 2.0
        return (
            xmin - delta,
            ymin - delta,
            xmax + delta,
            ymax + delta,
        )
