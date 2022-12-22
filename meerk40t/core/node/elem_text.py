import re
from copy import copy
from math import sqrt

from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_POINT, Length
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
    r"""(?:([^\s"';,]+|"[^";,]+"|'[^';,]+'|serif|sans-serif|cursive|fantasy|monospace)),?\s*;?"""
)


class TextNode(Node):
    """
    TextNode is the bootstrapped node type for the 'elem text' type.
    """

    def __init__(self, **kwargs):
        self.text = None
        self.x = 0
        self.y = 0
        self.anchor = "start"  # start, middle, end.
        self.baseline = "hanging"
        self.matrix = None
        self.fill = None
        self.stroke = None
        self.stroke_width = 0
        self.stroke_scale = True
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
        # Offset values to allow to fix the drawing of slanted fonts outside of the GetTextExtentBoundaries
        self.offset_x = 0
        self.offset_y = 0
        if "font" in kwargs:
            font = kwargs["font"]
            del kwargs["font"]
        else:
            font = None
        super(TextNode, self).__init__(type="elem text", **kwargs)
        self.text = str(self.text)
        self._formatter = "{element_type} {id}: {text}"
        if self.matrix is None:
            self.matrix = Matrix()
        if self.x != 0 or self.y != 0:
            self.matrix.pre_translate(self.x, self.y)
        self.bounds_with_variables_translated = None

        if font is not None:
            self.parse_font(font)
        else:
            self.font_size = getattr(self, SVG_ATTR_FONT_SIZE, None)
            self.font_style = getattr(self, SVG_ATTR_FONT_STYLE, None)
            self.font_variant = getattr(self, SVG_ATTR_FONT_VARIANT, None)
            self.font_weight = getattr(self, SVG_ATTR_FONT_WEIGHT, None)
            self.font_stretch = getattr(self, SVG_ATTR_FONT_STRETCH, None)
            self.font_family = getattr(self, SVG_ATTR_FONT_FAMILY, None)
            self.validate_font()

    def __copy__(self):
        nd = self.node_dict
        nd["matrix"] = copy(self.matrix)
        nd["fill"] = copy(self.fill)
        nd["stroke_width"] = copy(self.stroke_width)
        return TextNode(**nd)

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

    @property
    def stroke_scaled(self):
        return self.stroke_scale

    @stroke_scaled.setter
    def stroke_scaled(self, v):
        if not v and self.stroke_scale:
            matrix = self.matrix
            self.stroke_width *= sqrt(abs(matrix.determinant))
        if v and not self.stroke_scale:
            matrix = self.matrix
            self.stroke_width /= sqrt(abs(matrix.determinant))
        self.stroke_scale = v

    def implied_stroke_width(self, zoomscale=1.0):
        """If the stroke is not scaled, the matrix scale will scale the stroke, and we
        need to countermand that scaling by dividing by the square root of the absolute
        value of the determinant of the local matrix (1d matrix scaling)"""
        scalefactor = sqrt(abs(self.matrix.determinant))
        if self.stroke_scale:
            # Our implied stroke-width is prescaled.
            return self.stroke_width
        else:
            sw = self.stroke_width / scalefactor
            return sw

    def preprocess(self, context, matrix, plan):
        commands = plan.commands
        if self.parent.type != "op raster":
            commands.append(self.remove_text)
            return
        self.text = context.elements.wordlist_translate(self.text, self)
        self.stroke_scaled = True
        self.matrix *= matrix
        self.stroke_scaled = False
        self.set_dirty_bounds()

    def remove_text(self):
        self.remove_node()

    def default_map(self, default_map=None):
        default_map = super(TextNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "Text"
        default_map.update(self.__dict__)
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
        if self.font_family is None:
            return []
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
        if self.path is not None:
            return (self.path * self.matrix).bbox(
                transformed=True,
                with_stroke=with_stroke,
            )
        if self.raw_bbox is None:
            self.raw_bbox = [0, 0, 0, 0]
        left, upper, right, lower = self.raw_bbox
        xmin = left - 2
        ymin = upper - 2
        xmax = right + 2
        ymax = lower + 2
        width = xmax - xmin
        if self.anchor == "middle":
            xmin -= width / 2
            xmax -= width / 2
        elif self.anchor == "end":
            xmin -= width
            xmax -= width
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
