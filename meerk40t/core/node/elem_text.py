import re
from copy import copy
from math import sqrt, tau

from meerk40t.core.node.mixins import Stroked
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
    # r"""(?:([^\s"';,]+|"[^";,]+"|'[^';,]+'|serif|sans-serif|cursive|fantasy|monospace)),?\s*;?"""
    r"\s*'[^']+'|\s*\"[^\"]+\"|[^,\s]+"
)


class TextNode(Node, Stroked):
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
        # Offset values to allow to fix the drawing of slanted fonts outside of the GetTextExtentBoundaries
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

    def preprocess(self, context, matrix, plan):
        commands = plan.commands
        if self.parent.type != "op raster":
            commands.append(self.remove_text)
            return
        self.text = context.elements.wordlist_translate(self.text, self)
        self.stroke_scaled = False
        self.stroke_scaled = True
        self.matrix *= matrix
        self.stroke_scaled = False
        self.set_dirty_bounds()

    def remove_text(self):
        self.remove_node()

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
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
        # if (
        #     with_stroke
        #     and self.stroke_width is not None
        #     and not (self.stroke is None or self.stroke.value is None)
        # ):
        #     delta = (
        #         float(self.implied_stroke_width)
        #         if transformed
        #         else float(self.stroke_width)
        #     ) / 2.0
        return (
            xmin - delta,
            ymin - delta,
            xmax + delta,
            ymax + delta,
        )

    """
    A text node has no paint_bounds that is different to bounds,
    so we overload the standard functions to acknowledge that and
    always sync paint_bounds to bounds.
    """

    @property
    def paint_bounds(self):
        # Make sure that bounds is valid
        if self._paint_bounds_dirty:
            self._paint_bounds_dirty = False
            self._paint_bounds = self.bounds
        return self._paint_bounds

    @property
    def bounds(self):
        # Make sure that bounds is valid
        if not self._bounds_dirty:
            if self._paint_bounds_dirty:
                self._paint_bounds_dirty = False
                self._paint_bounds = self._bounds
            return self._bounds

        try:
            self._bounds = self.bbox(with_stroke=False)
        except AttributeError:
            self._bounds = None
        self._paint_bounds = self._bounds
        self._bounds_dirty = False
        self._paint_bounds_dirty = False
        return self._bounds
