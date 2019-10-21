import re
from xml.etree.ElementTree import iterparse

from path import Angle

# SVG STATIC VALUES
SVG_NAME_TAG = 'svg'
SVG_ATTR_VERSION = 'version'
SVG_VALUE_VERSION = '1.1'
SVG_ATTR_XMLNS = 'xmlns'
SVG_VALUE_XMLNS = 'http://www.w3.org/2000/svg'
SVG_ATTR_XMLNS_LINK = 'xmlns:xlink'
SVG_VALUE_XLINK = 'http://www.w3.org/1999/xlink'
SVG_ATTR_XMLNS_EV = 'xmlns:ev'
SVG_VALUE_XMLNS_EV = 'http://www.w3.org/2001/xml-events'

XLINK_HREF = '{http://www.w3.org/1999/xlink}href'
SVG_HREF = "href"
SVG_ATTR_WIDTH = 'width'
SVG_ATTR_HEIGHT = 'height'
SVG_ATTR_VIEWBOX = 'viewBox'
SVG_VIEWBOX_TRANSFORM = 'viewbox_transform'
SVG_TAG_PATH = 'path'
SVG_TAG_GROUP = 'g'
SVG_TAG_RECT = 'rect'
SVG_TAG_CIRCLE = 'circle'
SVG_TAG_ELLIPSE = 'ellipse'
SVG_TAG_LINE = 'line'
SVG_TAG_POLYLINE = 'polyline'
SVG_TAG_POLYGON = 'polygon'
SVG_TAG_TEXT = 'text'
SVG_TAG_IMAGE = 'image'
SVG_TAG_DESC = 'desc'
SVG_ATTR_DATA = 'd'
SVG_ATTR_FILL = 'fill'
SVG_ATTR_STROKE = 'stroke'
SVG_ATTR_STROKE_WIDTH = 'stroke-width'
SVG_ATTR_TRANSFORM = 'transform'
SVG_ATTR_STYLE = 'style'
SVG_ATTR_CENTER_X = 'cx'
SVG_ATTR_CENTER_Y = 'cy'
SVG_ATTR_RADIUS_X = 'rx'
SVG_ATTR_RADIUS_Y = 'ry'
SVG_ATTR_RADIUS = 'r'
SVG_ATTR_POINTS = 'points'
SVG_ATTR_PRESERVEASPECTRATIO = 'preserveAspectRatio'
SVG_ATTR_X = 'x'
SVG_ATTR_Y = 'y'
SVG_ATTR_TAG = 'tag'
SVG_TRANSFORM_MATRIX = 'matrix'
SVG_TRANSFORM_TRANSLATE = 'translate'
SVG_TRANSFORM_SCALE = 'scale'
SVG_TRANSFORM_ROTATE = 'rotate'
SVG_TRANSFORM_SKEW_X = 'skewX'
SVG_TRANSFORM_SKEW_Y = 'skewY'
SVG_VALUE_NONE = 'none'

COORD_PAIR_TMPLT = re.compile(
    r'([\+-]?\d*[\.\d]\d*[eE][\+-]?\d+|[\+-]?\d*[\.\d]\d*)' +
    r'(?:\s*,\s*|\s+|(?=-))' +
    r'([\+-]?\d*[\.\d]\d*[eE][\+-]?\d+|[\+-]?\d*[\.\d]\d*)'
)


# Leaf node to pathd values.


def path2pathd(path):
    return path.get(SVG_ATTR_DATA, '')


def ellipse2pathd(ellipse):
    """converts the parameters from an ellipse or a circle to a string for a
    Path object d-attribute"""

    cx = ellipse.get(SVG_ATTR_CENTER_X, None)
    cy = ellipse.get(SVG_ATTR_CENTER_Y, None)
    rx = ellipse.get(SVG_ATTR_RADIUS_X, None)
    ry = ellipse.get(SVG_ATTR_RADIUS_X, None)
    r = ellipse.get(SVG_ATTR_RADIUS, None)

    if r is not None:
        rx = ry = float(r)
    else:
        rx = float(rx)
        ry = float(ry)

    cx = float(cx)
    cy = float(cy)

    d = ''
    d += 'M' + str(cx - rx) + ',' + str(cy)
    d += 'a' + str(rx) + ',' + str(ry) + ' 0 1,0 ' + str(2 * rx) + ',0'
    d += 'a' + str(rx) + ',' + str(ry) + ' 0 1,0 ' + str(-2 * rx) + ',0'

    return d


def polyline2pathd(polyline, is_polygon=False):
    """converts the string from a polyline parameters to a string for a
    Path object d-attribute"""
    polyline_d = polyline.get(SVG_ATTR_POINTS, None)
    if polyline_d is None:
        return ''
    points = COORD_PAIR_TMPLT.findall(polyline_d)
    closed = (float(points[0][0]) == float(points[-1][0]) and
              float(points[0][1]) == float(points[-1][1]))

    # The `parse_path` call ignores redundant 'z' (closure) commands
    # e.g. `parse_path('M0 0L100 100Z') == parse_path('M0 0L100 100L0 0Z')`
    # This check ensures that an n-point polygon is converted to an n-Line path.
    if is_polygon and closed:
        points.append(points[0])

    d = 'M' + 'L'.join('{0} {1}'.format(x, y) for x, y in points)
    if is_polygon or closed:
        d += 'z'
    return d


def polygon2pathd(polyline):
    """converts the string from a polygon parameters to a string
    for a Path object d-attribute.
    Note:  For a polygon made from n points, the resulting path will be
    composed of n lines (even if some of these lines have length zero).
    """
    return polyline2pathd(polyline, True)


def rect2pathd(rect):
    """Converts an SVG-rect element to a Path d-string.

    The rectangle will start at the (x,y) coordinate specified by the
    rectangle object and proceed counter-clockwise."""
    x0, y0 = float(rect.get(SVG_ATTR_X, 0)), float(rect.get(SVG_ATTR_Y, 0))
    w, h = float(rect.get(SVG_ATTR_WIDTH, 0)), float(rect.get(SVG_ATTR_HEIGHT, 0))
    x1, y1 = x0 + w, y0
    x2, y2 = x0 + w, y0 + h
    x3, y3 = x0, y0 + h

    d = ("M{} {} L {} {} L {} {} L {} {} z"
         "".format(x0, y0, x1, y1, x2, y2, x3, y3))
    return d


def line2pathd(l):
    return 'M' + l['x1'] + ' ' + l['y1'] + 'L' + l['x2'] + ' ' + l['y2']


# PathTokens class.
class PathTokens:
    """Path Tokens is the class for the general outline of how SVG Pathd objects
    are stored. Namely, a single non-'e' character and a collection of floating
    point numbers. While this is explicitly used for SVG pathd objects the method
    for serializing command data in this fashion is also useful as a standalone
    class."""

    def __init__(self, command_elements):
        self.command_elements = command_elements
        commands = ''
        for k in command_elements:
            commands += k
        self.COMMAND_RE = re.compile("([" + commands + "])")
        self.FLOAT_RE = re.compile("[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?")
        self.elements = None
        self.command = None
        self.last_command = None
        self.parser = None

    def _tokenize_path(self, pathdef):
        for x in self.COMMAND_RE.split(pathdef):
            if x in self.command_elements:
                yield x
            for token in self.FLOAT_RE.findall(x):
                yield token

    def get(self):
        """Gets the element from the stack."""
        return self.elements.pop()

    def pre_execute(self):
        """Called before any command element is executed."""
        pass

    def post_execute(self):
        """Called after any command element is executed."""
        pass

    def new_command(self):
        """Called when command element is switched."""
        pass

    def parse(self, pathdef):
        self.elements = list(self._tokenize_path(pathdef))
        # Reverse for easy use of .pop()
        self.elements.reverse()

        while self.elements:
            if self.elements[-1] in self.command_elements:
                self.last_command = self.command
                self.command = self.get()
                self.new_command()
            else:
                if self.command is None:
                    raise ValueError("Invalid command.")  # could be faulty implicit or unaccepted element.
            self.pre_execute()
            self.command_elements[self.command]()
            self.post_execute()


# SVG Path Tokens.
class SVGPathTokens(PathTokens):
    """Utilizes the general PathTokens class to parse SVG pathd strings.
    This class has been updated to account for SVG 2.0 version of the zZ command.
    Points are stored in complex numbers with the real being the x-value and
    the imaginary part being the y-value."""

    def __init__(self):
        PathTokens.__init__(self, {
            'M': self.move_to,
            'm': self.move_to,
            'L': self.line_to,
            'l': self.line_to,
            "H": self.h_to,
            "h": self.h_to,
            "V": self.v_to,
            "v": self.v_to,
            "C": self.cubic_to,
            "c": self.cubic_to,
            "S": self.smooth_cubic_to,
            "s": self.smooth_cubic_to,
            "Q": self.quad_to,
            "q": self.quad_to,
            "T": self.smooth_quad_to,
            "t": self.smooth_quad_to,
            "A": self.arc_to,
            "a": self.arc_to,
            "Z": self.close,
            "z": self.close
        })
        self.parser = None
        self.absolute = False

    def svg_parse(self, parser, pathdef):
        self.parser = parser
        self.absolute = False
        self.parser.start()
        self.parse(pathdef)
        self.parser.end()

    def get_pos(self):
        if self.command == 'Z':
            return "z"  # After Z, all further expected values are also Z.
        coord0 = self.get()
        if coord0 == 'z' or coord0 == 'Z':
            self.command = 'Z'
            return "z"
        coord1 = self.get()
        position = (float(coord0), float(coord1))
        if not self.absolute:
            current_pos = self.parser.current_point
            if current_pos is None:
                return position
            return [position[0] + current_pos[0], position[1] + current_pos[1]]
        return position

    def move_to(self):
        # Moveto command.
        pos = self.get_pos()
        self.parser.move(pos)

        # Implicit moveto commands are treated as lineto commands.
        # So we set command to lineto here, in case there are
        # further implicit commands after this moveto.
        self.command = 'L'

    def line_to(self):
        pos = self.get_pos()
        self.parser.line(pos)

    def h_to(self):
        x = float(self.get())
        if self.absolute:
            self.parser.absolute_h(x)
        else:
            self.parser.relative_h(x)

    def v_to(self):
        y = float(self.get())
        if self.absolute:
            self.parser.absolute_v(y)
        else:
            self.parser.relative_v(y)

    def cubic_to(self):
        control1 = self.get_pos()
        control2 = self.get_pos()
        end = self.get_pos()
        self.parser.cubic(control1, control2, end)

    def smooth_cubic_to(self):
        control2 = self.get_pos()
        end = self.get_pos()
        self.parser.smooth_cubic(control2, end)

    def quad_to(self):
        control = self.get_pos()
        end = self.get_pos()
        self.parser.quad(control, end)

    def smooth_quad_to(self):
        end = self.get_pos()
        self.parser.smooth_quad(end)

    def arc_to(self):
        rx = float(self.get())
        ry = float(self.get())
        rotation = float(self.get())
        arc = float(self.get())
        sweep = float(self.get())
        end = self.get_pos()

        self.parser.arc(rx, ry, rotation, arc, sweep, end)

    def close(self):
        # Close path
        self.parser.closed()
        self.command = None

    def new_command(self):
        self.absolute = self.command.isupper()

    def post_execute(self):
        if self.command == 'Z':  # Z might have been triggered inside commands.
            self.close()


def parse_svg_path(parser, pathdef):
    """Parses the SVG path."""
    tokens = SVGPathTokens()
    tokens.svg_parse(parser, pathdef)


def _tokenize_transform(transform_str):
    """Generator to create transform parse elements.
    Will return tuples(command, list(values))

    TODO: Convert to 2D CSS transforms from SVG 1.1 for SVG 2.0.
    In addition to SVG commands,
    2D CSS has: translateX, translateY, scaleX, scaleY
    2D CSS angles haves units: "deg" tau / 360, "rad" tau/tau, "grad" tau/400, "turn" tau.
    2D CSS distances have length/percentages: "px", "cm", "mm", "in", "pt", etc. (+|-)?d+%
    """

    if not transform_str:
        return
    transform_regex = '(?u)(' \
                      + SVG_TRANSFORM_MATRIX + '|' \
                      + SVG_TRANSFORM_TRANSLATE + '|' \
                      + SVG_TRANSFORM_SCALE + '|' \
                      + SVG_TRANSFORM_ROTATE + '|' \
                      + SVG_TRANSFORM_SKEW_X + '|' \
                      + SVG_TRANSFORM_SKEW_Y + \
                      ')[\s\t\n]*\(([^)]+)\)'
    transform_re = re.compile(transform_regex)
    float_re = re.compile("[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?")
    for sub_element in transform_re.findall(transform_str):
        yield sub_element[0], tuple(map(float, float_re.findall(sub_element[1])))


def parse_viewbox_transform(svg_element, ppi=96.0, viewbox=None):
    """
    SVG 1.1 7.2, SVG 2.0 8.2 equivalent transform of an SVG viewport.
    With regards to https://github.com/w3c/svgwg/issues/215 use 8.2 version.

    It creates a matrix equal to that viewport expected.

    :param svg_element: dict containing the relevant svg entries.
    :return: string of the SVG transform commands to account for the viewbox.
    """
    if viewbox is None:
        if SVG_ATTR_VIEWBOX in svg_element:
            # Let vb-x, vb-y, vb-width, vb-height be the min-x, min-y,
            # width and height values of the viewBox attribute respectively.
            viewbox = svg_element[SVG_ATTR_VIEWBOX]
        else:
            viewbox = "0 0 100 100"
    # Let e-x, e-y, e-width, e-height be the position and size of the element respectively.
    vb = viewbox.split(" ")
    vb_x = float(vb[0])
    vb_y = float(vb[1])
    vb_width = float(vb[2])
    vb_height = float(vb[3])
    if SVG_ATTR_X in svg_element:
        e_x = parse_svg_distance(svg_element[SVG_ATTR_X], ppi)
    else:
        e_x = 0
    if SVG_ATTR_Y in svg_element:
        e_y = parse_svg_distance(svg_element[SVG_ATTR_Y], ppi)
    else:
        e_y = 0
    if SVG_ATTR_WIDTH in svg_element:
        e_width = parse_svg_distance(svg_element[SVG_ATTR_WIDTH], ppi)
    else:
        e_width = 100.0
    if SVG_ATTR_HEIGHT in svg_element:
        e_height = parse_svg_distance(svg_element[SVG_ATTR_HEIGHT], ppi)
    else:
        e_height = e_width

    # Let align be the align value of preserveAspectRatio, or 'xMidYMid' if preserveAspectRatio is not defined.
    # Let meetOrSlice be the meetOrSlice value of preserveAspectRatio, or 'meet' if preserveAspectRatio is not defined
    # or if meetOrSlice is missing from this value.
    if SVG_ATTR_PRESERVEASPECTRATIO in svg_element:
        aspect = svg_element[SVG_ATTR_PRESERVEASPECTRATIO]
        aspect_slice = aspect.split(' ')
        try:
            align = aspect_slice[0]
        except IndexError:
            align = 'xMidYMid'
        try:
            meet_or_slice = aspect_slice[1]
        except IndexError:
            meet_or_slice = 'meet'
    else:
        align = 'xMidYMid'
        meet_or_slice = 'meet'

    # Initialize scale-x to e-width/vb-width.
    scale_x = e_width / vb_width
    # Initialize scale-y to e-height/vb-height.
    scale_y = e_height / vb_height

    # If align is not 'none' and meetOrSlice is 'meet', set the larger of scale-x and scale-y to the smaller.
    if align != SVG_VALUE_NONE and meet_or_slice == 'meet':
        scale_x = max(scale_x, scale_y)
        scale_y = scale_x
    # Otherwise, if align is not 'none' and meetOrSlice is 'slice', set the smaller of scale-x and scale-y to the larger
    elif align != SVG_VALUE_NONE and meet_or_slice == 'slice':
        scale_x = min(scale_x, scale_y)
        scale_y = scale_x
    # Initialize translate-x to e-x - (vb-x * scale-x).
    translate_x = e_x - (vb_x * scale_x)
    # Initialize translate-y to e-y - (vb-y * scale-y)
    translate_y = e_y - (vb_y * scale_y)
    # If align contains 'xMid', add (e-width - vb-width * scale-x) / 2 to translate-x.
    align = align.lower()
    if 'xmid' in align:
        translate_x += (e_width - vb_width * scale_x) / 2.0
    # If align contains 'xMax', add (e-width - vb-width * scale-x) to translate-x.
    if 'xmax' in align:
        translate_x += e_width - vb_width * scale_x
    # If align contains 'yMid', add (e-height - vb-height * scale-y) / 2 to translate-y.
    if 'ymid' in align:
        translate_y += (e_height - vb_height * scale_y) / 2.0
    # If align contains 'yMax', add (e-height - vb-height * scale-y) to translate-y.
    if 'ymax' in align:
        translate_y += (e_height - vb_height * scale_y)

    if translate_x == 0 and translate_y == 0:
        if scale_x == 1 and scale_y == 1:
            return ""  # Nothing happens.
        else:
            return "scale(%f, %f)" % (scale_x, scale_y)
    else:
        if scale_x == 1 and scale_y == 1:
            return "translate(%f, %f)" % (translate_x, translate_y)
        else:
            return "translate(%f, %f) scale(%f, %f)" % (translate_x, translate_y, scale_x, scale_y)
            # return "scale(%f, %f) translate(%f, %f)" % (scale_x, scale_y, translate_x, translate_y)


def parse_svg_distance(distance_str, ppi=96.0):
    """Convert svg length to set distances.
    96 is the typical pixels per inch.
    Other values have been used."""
    if distance_str.endswith('mm'):
        return float(distance_str[:-2]) * ppi * 0.0393701
    if distance_str.endswith('cm'):
        return float(distance_str[:-2]) * ppi * 0.393701
    if distance_str.endswith('in'):
        return float(distance_str[:-2]) * ppi
    if distance_str.endswith('px'):
        return float(distance_str[:-2])
    if distance_str.endswith('pt'):
        return float(distance_str[:-2]) * 1.3333
    if distance_str.endswith('pc'):
        return float(distance_str[:-2]) * 16
    return float(distance_str)


def parse_svg_transform(transform_str, obj):
    """Parses the svg transform tag. Currently parses SVG 1.1 transformations.
    With regard to SVG 2.0 would be CSS transformations, and require a superset.

    For typical usecase these will be given a path.Matrix."""
    if not transform_str:
        return
    if not isinstance(transform_str, str):
        raise TypeError('Must provide a string to parse')

    for name, params in _tokenize_transform(transform_str):
        if SVG_TRANSFORM_MATRIX == name:
            obj.pre_cat(*params)
        elif SVG_TRANSFORM_TRANSLATE == name:
            obj.pre_translate(*params)
        elif SVG_TRANSFORM_SCALE == name:
            obj.pre_scale(*params)
        elif SVG_TRANSFORM_ROTATE == name:
            obj.pre_rotate(Angle.degrees(params[0]), *params[1:])
        elif SVG_TRANSFORM_SKEW_X == name:
            obj.pre_skew_x(Angle.degrees(params[0]), *params[1:])
        elif SVG_TRANSFORM_SKEW_Y == name:
            obj.pre_skew_y(Angle.degrees(params[0]), *params[1:])


def parse_svg_file(f, viewport_transform=False):
    """Parses the SVG file.
    Style elements are split into their proper values.
    Transform elements are concatenated and unparsed.
    Leaf node elements are turned into pathd values."""

    stack = []
    values = {}
    for event, elem in iterparse(f, events=('start', 'end')):
        if event == 'start':
            stack.append(values)
            current_values = values
            values = {}
            values.update(current_values)  # copy of dictionary

            attributes = elem.attrib
            if SVG_ATTR_STYLE in attributes:
                for equate in attributes[SVG_ATTR_STYLE].split(";"):
                    equal_item = equate.split(":")
                    if len(equal_item) == 2:
                        attributes[equal_item[0]] = equal_item[1]
            if SVG_ATTR_TRANSFORM in attributes:
                new_transform = attributes[SVG_ATTR_TRANSFORM]
                if SVG_ATTR_TRANSFORM in values:
                    current_transform = values[SVG_ATTR_TRANSFORM]
                    attributes[SVG_ATTR_TRANSFORM] = current_transform + " " + new_transform
                else:
                    attributes[SVG_ATTR_TRANSFORM] = new_transform
                # will be used to update values.
            values.update(attributes)
            tag = elem.tag
            if tag.startswith('{'):
                tag = tag[28:]  # Removing namespace. http://www.w3.org/2000/svg:
            if SVG_NAME_TAG == tag:
                if viewport_transform:
                    new_transform = parse_viewbox_transform(values)
                    values[SVG_VIEWBOX_TRANSFORM] = new_transform
                    if SVG_ATTR_TRANSFORM in attributes:
                        values[SVG_ATTR_TRANSFORM] += " " + new_transform
                    else:
                        values[SVG_ATTR_TRANSFORM] = new_transform
                yield values
                continue
            elif SVG_TAG_GROUP == tag:
                continue
            elif SVG_TAG_PATH == tag:
                values[SVG_ATTR_DATA] = path2pathd(values)
            elif SVG_TAG_CIRCLE == tag:
                values[SVG_ATTR_DATA] = ellipse2pathd(values)
            elif SVG_TAG_ELLIPSE == tag:
                values[SVG_ATTR_DATA] = ellipse2pathd(values)
            elif SVG_TAG_LINE == tag:
                values[SVG_ATTR_DATA] = line2pathd(values)
            elif SVG_TAG_POLYLINE == tag:
                values[SVG_ATTR_DATA] = polyline2pathd(values)
            elif SVG_TAG_POLYGON == tag:
                values[SVG_ATTR_DATA] = polygon2pathd(values)
            elif SVG_TAG_RECT == tag:
                values[SVG_ATTR_DATA] = rect2pathd(values)
            elif SVG_TAG_IMAGE == tag:  # Has no pathd data, but yields as element.
                if XLINK_HREF in values:
                    image = values[XLINK_HREF]
                elif SVG_HREF in values:
                    image = values[SVG_HREF]
                else:
                    continue
                values[SVG_TAG_IMAGE] = image
            else:
                continue
            values[SVG_ATTR_TAG] = tag
            yield values
        else:  # End event.
            # The iterparse spec makes it clear that internal text data is undefined except at the end.
            tag = elem.tag
            if tag.startswith('{'):
                tag = tag[28:]  # Removing namespace. http://www.w3.org/2000/svg:
            if SVG_TAG_TEXT == tag:
                values[SVG_ATTR_TAG] = tag
                values[SVG_TAG_TEXT] = elem.text
                yield values
            elif SVG_TAG_DESC == tag:
                values[SVG_ATTR_TAG] = tag
                values[SVG_TAG_DESC] = elem.text
                yield values
            values = stack.pop()


# SVG Color Parsing

def color_rgb(r, g, b):
    return int(0xFF000000 |
               ((r & 255) << 16) |
               ((g & 255) << 8) |
               (b & 255))


# defining predefined colors permitted by svg: https://www.w3.org/TR/SVG11/types.html#ColorKeywords
svg_color_dict = {
    "aliceblue": color_rgb(240, 248, 255),
    "antiquewhite": color_rgb(250, 235, 215),
    "aqua": color_rgb(0, 255, 255),
    "aquamarine": color_rgb(127, 255, 212),
    "azure": color_rgb(240, 255, 255),
    "beige": color_rgb(245, 245, 220),
    "bisque": color_rgb(255, 228, 196),
    "black": color_rgb(0, 0, 0),
    "blanchedalmond": color_rgb(255, 235, 205),
    "blue": color_rgb(0, 0, 255),
    "blueviolet": color_rgb(138, 43, 226),
    "brown": color_rgb(165, 42, 42),
    "burlywood": color_rgb(222, 184, 135),
    "cadetblue": color_rgb(95, 158, 160),
    "chartreuse": color_rgb(127, 255, 0),
    "chocolate": color_rgb(210, 105, 30),
    "coral": color_rgb(255, 127, 80),
    "cornflowerblue": color_rgb(100, 149, 237),
    "cornsilk": color_rgb(255, 248, 220),
    "crimson": color_rgb(220, 20, 60),
    "cyan": color_rgb(0, 255, 255),
    "darkblue": color_rgb(0, 0, 139),
    "darkcyan": color_rgb(0, 139, 139),
    "darkgoldenrod": color_rgb(184, 134, 11),
    "darkgray": color_rgb(169, 169, 169),
    "darkgreen": color_rgb(0, 100, 0),
    "darkgrey": color_rgb(169, 169, 169),
    "darkkhaki": color_rgb(189, 183, 107),
    "darkmagenta": color_rgb(139, 0, 139),
    "darkolivegreen": color_rgb(85, 107, 47),
    "darkorange": color_rgb(255, 140, 0),
    "darkorchid": color_rgb(153, 50, 204),
    "darkred": color_rgb(139, 0, 0),
    "darksalmon": color_rgb(233, 150, 122),
    "darkseagreen": color_rgb(143, 188, 143),
    "darkslateblue": color_rgb(72, 61, 139),
    "darkslategray": color_rgb(47, 79, 79),
    "darkslategrey": color_rgb(47, 79, 79),
    "darkturquoise": color_rgb(0, 206, 209),
    "darkviolet": color_rgb(148, 0, 211),
    "deeppink": color_rgb(255, 20, 147),
    "deepskyblue": color_rgb(0, 191, 255),
    "dimgray": color_rgb(105, 105, 105),
    "dimgrey": color_rgb(105, 105, 105),
    "dodgerblue": color_rgb(30, 144, 255),
    "firebrick": color_rgb(178, 34, 34),
    "floralwhite": color_rgb(255, 250, 240),
    "forestgreen": color_rgb(34, 139, 34),
    "fuchsia": color_rgb(255, 0, 255),
    "gainsboro": color_rgb(220, 220, 220),
    "ghostwhite": color_rgb(248, 248, 255),
    "gold": color_rgb(255, 215, 0),
    "goldenrod": color_rgb(218, 165, 32),
    "gray": color_rgb(128, 128, 128),
    "grey": color_rgb(128, 128, 128),
    "green": color_rgb(0, 128, 0),
    "greenyellow": color_rgb(173, 255, 47),
    "honeydew": color_rgb(240, 255, 240),
    "hotpink": color_rgb(255, 105, 180),
    "indianred": color_rgb(205, 92, 92),
    "indigo": color_rgb(75, 0, 130),
    "ivory": color_rgb(255, 255, 240),
    "khaki": color_rgb(240, 230, 140),
    "lavender": color_rgb(230, 230, 250),
    "lavenderblush": color_rgb(255, 240, 245),
    "lawngreen": color_rgb(124, 252, 0),
    "lemonchiffon": color_rgb(255, 250, 205),
    "lightblue": color_rgb(173, 216, 230),
    "lightcoral": color_rgb(240, 128, 128),
    "lightcyan": color_rgb(224, 255, 255),
    "lightgoldenrodyellow": color_rgb(250, 250, 210),
    "lightgray": color_rgb(211, 211, 211),
    "lightgreen": color_rgb(144, 238, 144),
    "lightgrey": color_rgb(211, 211, 211),
    "lightpink": color_rgb(255, 182, 193),
    "lightsalmon": color_rgb(255, 160, 122),
    "lightseagreen": color_rgb(32, 178, 170),
    "lightskyblue": color_rgb(135, 206, 250),
    "lightslategray": color_rgb(119, 136, 153),
    "lightslategrey": color_rgb(119, 136, 153),
    "lightsteelblue": color_rgb(176, 196, 222),
    "lightyellow": color_rgb(255, 255, 224),
    "lime": color_rgb(0, 255, 0),
    "limegreen": color_rgb(50, 205, 50),
    "linen": color_rgb(250, 240, 230),
    "magenta": color_rgb(255, 0, 255),
    "maroon": color_rgb(128, 0, 0),
    "mediumaquamarine": color_rgb(102, 205, 170),
    "mediumblue": color_rgb(0, 0, 205),
    "mediumorchid": color_rgb(186, 85, 211),
    "mediumpurple": color_rgb(147, 112, 219),
    "mediumseagreen": color_rgb(60, 179, 113),
    "mediumslateblue": color_rgb(123, 104, 238),
    "mediumspringgreen": color_rgb(0, 250, 154),
    "mediumturquoise": color_rgb(72, 209, 204),
    "mediumvioletred": color_rgb(199, 21, 133),
    "midnightblue": color_rgb(25, 25, 112),
    "mintcream": color_rgb(245, 255, 250),
    "mistyrose": color_rgb(255, 228, 225),
    "moccasin": color_rgb(255, 228, 181),
    "navajowhite": color_rgb(255, 222, 173),
    "navy": color_rgb(0, 0, 128),
    "oldlace": color_rgb(253, 245, 230),
    "olive": color_rgb(128, 128, 0),
    "olivedrab": color_rgb(107, 142, 35),
    "orange": color_rgb(255, 165, 0),
    "orangered": color_rgb(255, 69, 0),
    "orchid": color_rgb(218, 112, 214),
    "palegoldenrod": color_rgb(238, 232, 170),
    "palegreen": color_rgb(152, 251, 152),
    "paleturquoise": color_rgb(175, 238, 238),
    "palevioletred": color_rgb(219, 112, 147),
    "papayawhip": color_rgb(255, 239, 213),
    "peachpuff": color_rgb(255, 218, 185),
    "peru": color_rgb(205, 133, 63),
    "pink": color_rgb(255, 192, 203),
    "plum": color_rgb(221, 160, 221),
    "powderblue": color_rgb(176, 224, 230),
    "purple": color_rgb(128, 0, 128),
    "red": color_rgb(255, 0, 0),
    "rosybrown": color_rgb(188, 143, 143),
    "royalblue": color_rgb(65, 105, 225),
    "saddlebrown": color_rgb(139, 69, 19),
    "salmon": color_rgb(250, 128, 114),
    "sandybrown": color_rgb(244, 164, 96),
    "seagreen": color_rgb(46, 139, 87),
    "seashell": color_rgb(255, 245, 238),
    "sienna": color_rgb(160, 82, 45),
    "silver": color_rgb(192, 192, 192),
    "skyblue": color_rgb(135, 206, 235),
    "slateblue": color_rgb(106, 90, 205),
    "slategray": color_rgb(112, 128, 144),
    "slategrey": color_rgb(112, 128, 144),
    "snow": color_rgb(255, 250, 250),
    "springgreen": color_rgb(0, 255, 127),
    "steelblue": color_rgb(70, 130, 180),
    "tan": color_rgb(210, 180, 140),
    "teal": color_rgb(0, 128, 128),
    "thistle": color_rgb(216, 191, 216),
    "tomato": color_rgb(255, 99, 71),
    "turquoise": color_rgb(64, 224, 208),
    "violet": color_rgb(238, 130, 238),
    "wheat": color_rgb(245, 222, 179),
    "white": color_rgb(255, 255, 255),
    "whitesmoke": color_rgb(245, 245, 245),
    "yellow": color_rgb(255, 255, 0),
    "yellowgreen": color_rgb(154, 205, 50)
}


def parse_svg_color_lookup(color_string):
    """Parse SVG Color by Keyword on dictionary lookup"""
    return svg_color_dict.get(color_string, 0xFF000000)


def parse_svg_color_hex(hex_string):
    """Parse SVG Color by Hex String"""
    h = hex_string.lstrip('#')
    size = len(h)
    if size == 8:
        return int(h[:8], 16)
    elif size == 6:
        return int(h[:6], 16)
    elif size == 4:
        return int(h[3] + h[3] + h[2] + h[2] + h[1] + h[1] + h[0] + h[0], 16)
    elif size == 3:
        return int(h[2] + h[2] + h[1] + h[1] + h[0] + h[0], 16)
    return 0xFF000000


def parse_svg_color_rgb(values):
    """Parse SVG Color, RGB value declarations """
    int_values = list(map(int, values))
    return color_rgb(int_values[0], int_values[1], int_values[2])


def parse_svg_color_rgbp(values):
    """Parse SVG color, RGB percent value declarations"""
    ratio = 255.0 / 100.0
    values = list(map(float, values))
    return color_rgb(int(values[0] * ratio), int(values[1] * ratio), int(values[2] * ratio))


def parse_svg_color(color_string):
    """Parse SVG color, will return a set value."""
    hex_re = re.compile(r'^#?([0-9A-Fa-f]{3,8})$')
    match = hex_re.match(color_string)
    if match:
        return parse_svg_color_hex(color_string)
    rgb_re = re.compile(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)')
    match = rgb_re.match(color_string)
    if match:
        return parse_svg_color_rgb(match.groups())

    rgbp_re = re.compile(r'rgb\(\s*(\d+)%\s*,\s*(\d+)%\s*,\s*(\d+)%\s*\)')
    match = rgbp_re.match(color_string)
    if match:
        return parse_svg_color_rgbp(match.groups())
    return parse_svg_color_lookup(color_string)
