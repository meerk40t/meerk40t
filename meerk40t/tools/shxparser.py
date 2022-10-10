from math import atan2, cos, sin, tau

SHXPARSER_VERSION = "0.0.1"


END_OF_SHAPE = 0
PEN_DOWN = 1
PEN_UP = 2
DIVIDE_VECTOR = 3
MULTIPLY_VECTOR = 4
PUSH_STACK = 5
POP_STACK = 6
DRAW_SUBSHAPE = 7
XY_DISPLACEMENT = 8
POLY_XY_DISPLACEMENT = 9  # 0,0 terminated
OCTANT_ARC = 0xA
FRACTIONAL_ARC = 0xB  # 5 bytes, start, end, high radius, radius, ±0SC
BULGE_ARC = 0xC  # dx, dy, bulge
POLY_BULGE_ARC = 0xD  # 0,0 terminated BULGE_ARC
COND_MODE_2 = 0x0E  # PROCESS this command *only if mode=2*


def signed8(b):
    if b > 127:
        return -256 + b
    else:
        return b


def int_16le(byte):
    return (byte[0] & 0xFF) + ((byte[1] & 0xFF) << 8)


def int_32le(b):
    return (
        (b[0] & 0xFF)
        + ((b[1] & 0xFF) << 8)
        + ((b[2] & 0xFF) << 16)
        + ((b[3] & 0xFF) << 24)
    )


def read_int_8(stream):
    byte = bytearray(stream.read(1))
    if len(byte) == 1:
        return byte[0]
    return None


def read_int_16le(stream):
    byte = bytearray(stream.read(2))
    if len(byte) == 2:
        return int_16le(byte)
    return None


def read_int_32le(stream):
    b = bytearray(stream.read(4))
    if len(b) == 4:
        return int_32le(b)
    return None


def read_string(stream):
    bb = bytearray()
    while True:
        b = stream.read(1)
        if b == b"":
            try:
                result = bb.decode("utf-8")
            except UnicodeDecodeError:
                result = ""
            return result
        if b == b"\r" or b == b"\n" or b == b"\x00":
            try:
                result = bb.decode("utf-8")
            except UnicodeDecodeError:
                result = ""
            return result
        bb += b


class ShxPath:
    """
    Example path code. Any class with these functions would work as well. When render is called on the ShxFont class
    the path is given particular useful segments.
    """

    def __init__(self):
        self.path = list()

    def new_path(self):
        """
        Start of a new path.
        """
        self.path.append(None)

    def move(self, x, y):
        """
        Move current point to the point specified.
        """
        self.path.append((x, y))

    def line(self, x0, y0, x1, y1):
        """
        Draw a line from the current point to the specified point.
        """
        self.path.append((x0, y0, x1, y1))

    def arc(self, x0, y0, cx, cy, x1, y1):
        """
        Draw an arc from the current point to specified point going through the control point.

        3 Points define a circular arc, there is only one arc which travels from start to end going through a given
        control point. The exceptions are when the arc points are colinear or two arc points are coincident. In some
        cases the start and end points will be equal and the control point will be located the circle diameter away.
        """
        self.path.append((x0, y0, cx, cy, x1, y1))


class ShxFont:
    """
    This class performs the parsing of the three major types of .SHX fonts. Composing them into specific glyphs which
    consist of commands in a vector-shape language. When .render() is called on some text, vector actions are performed
    on the font which create the vector path.
    """

    def __init__(self, filename):
        self.format = None  # format (usually AutoCAD-86)
        self.type = None  # Font type: shapes, bigfont, unifont
        self.version = None  # Font file version (usually 1.0).
        self.glyphs = dict()  # Glyph dictionary
        self.font_name = "unknown"  # Parsed font name.
        self.above = None  # Distance above baseline for capital letters.
        self.below = None  # Distance below baseline for lowercase letters
        self.modes = None  # 0 Horizontal Only, 2 Dual mode (Horizontal or Vertical)
        self.encoding = False  # 0 unicode, 1 packed multibyte, 2 shape file
        self.embedded = False  # 0 font can be embedded, 1 font cannot be embedded, 2 embedding is read-only
        self._parse(filename)

    def __str__(self):
        return f'{self.type}("{self.font_name}", {self.version}, glyphs: {len(self.glyphs)})'

    def _parse(self, filename):
        with open(filename, "br") as f:
            self._parse_header(f)
            if self.type == "shapes":
                self._parse_shapes(f)
            elif self.type == "bigfont":
                self._parse_bigfont(f)
            elif self.type == "unifont":
                self._parse_unifont(f)

    def _parse_header(self, f):
        header = read_string(f)
        parts = header.split(" ")
        self.format = parts[0]
        self.type = parts[1]
        self.version = parts[2]
        f.read(2)

    def _parse_shapes(self, f):
        start = read_int_16le(f)
        end = read_int_16le(f)
        count = read_int_16le(f)
        glyph_ref = list()
        for i in range(count):
            index = read_int_16le(f)
            length = read_int_16le(f)
            glyph_ref.append((index, length))

        for index, length in glyph_ref:
            if index == 0:
                self.font_name = read_string(f)
                self.above = read_int_8(f)  # vector lengths above baseline
                self.below = read_int_8(f)  # vector lengths below baseline
                # 0 - Horizontal, 2 - dual. 0x0E command only when mode=2
                self.modes = read_int_8(f)
                # end = read_int_16le(f)
            else:
                self.glyphs[index] = f.read(length)

    def _parse_bigfont(self, f):
        count = read_int_16le(f)
        length = read_int_16le(f)
        changes = list()
        change_count = read_int_16le(f)
        for i in range(change_count):
            start = read_int_16le(f)
            end = read_int_16le(f)
            changes.append((start, end))

        glyph_ref = list()
        for i in range(count):
            index = read_int_16le(f)
            length = read_int_16le(f)
            offset = read_int_32le(f)
            glyph_ref.append((index, length, offset))

        for index, length, offset in glyph_ref:
            f.seek(offset, 0)
            if index == 0:
                # self.font_name = read_string(f)
                self.above = read_int_8(f)  # vector lengths above baseline
                self.below = read_int_8(f)  # vector lengths below baseline
                # 0 - Horizontal, 2 - dual. 0x0E command only when mode=2
                self.modes = read_int_8(f)

            else:
                self.glyphs[index] = f.read(length)

    def _parse_unifont(self, f):
        count = read_int_32le(f)
        length = read_int_16le(f)
        f.seek(5)
        self.font_name = read_string(f)
        self.above = read_int_8(f)
        self.below = read_int_8(f)
        self.mode = read_int_8(f)
        self.encoding = read_int_8(f)
        self.embedded = read_int_8(f)
        ignore = read_int_8(f)
        for i in range(count - 1):
            index = read_int_16le(f)
            length = read_int_16le(f)
            self.glyphs[index] = f.read(length)

    def render(self, path, text, horizontal=True, font_size=12.0):
        skip = False
        x = 0
        y = 0
        last_x = 0
        last_y = 0
        if self.above == 0:
            # Invalid font!
            return
        scale = font_size / self.above
        stack = []
        replacer = []
        for tchar in text:
            to_replace = None
            # Yes, I am German :-)
            if ord(tchar) not in self.glyphs:
                if tchar == "ä":
                    to_replace = (tchar, "ae")
                elif tchar == "ö":
                    to_replace = (tchar, "ue")
                elif tchar == "ü":
                    to_replace = (tchar, "ue")
                elif tchar == "Ä":
                    to_replace = (tchar, "Ae")
                elif tchar == "Ö":
                    to_replace = (tchar, "Oe")
                elif tchar == "Ü":
                    to_replace = (tchar, "Ue")
                elif tchar == "ß":
                    to_replace = (tchar, "ss")
            if to_replace is not None and to_replace not in replacer:
                replacer.append(to_replace)
        for to_replace in replacer:
            # print (f"Replace all '{to_replace[0]}' with '{to_replace[1]}'")
            text = text.replace(to_replace[0], to_replace[1])
        for letter in text:
            try:
                code = bytearray(reversed(self.glyphs[ord(letter)]))
            except KeyError:
                # Letter is not found.
                continue
            pen = True
            while code:
                b = code.pop()
                direction = b & 0x0F
                length = (b & 0xF0) >> 4
                if length == 0:
                    if direction == END_OF_SHAPE:
                        path.new_path()
                    elif direction == PEN_DOWN:
                        if not skip:
                            pen = True
                            path.move(x, y)
                    elif direction == PEN_UP:
                        if not skip:
                            pen = False
                    elif direction == DIVIDE_VECTOR:
                        factor = code.pop()
                        if not skip:
                            scale /= factor
                    elif direction == MULTIPLY_VECTOR:
                        factor = code.pop()
                        if not skip:
                            scale *= factor
                    elif direction == PUSH_STACK:
                        if not skip:
                            stack.append((x, y))
                            if len(stack) == 4:
                                raise IndexError(
                                    f"Position stack overflow in shape {letter}"
                                )
                    elif direction == POP_STACK:
                        if not skip:
                            try:
                                x, y = stack.pop()
                            except IndexError:
                                raise IndexError(
                                    f"Position stack underflow in shape {letter}"
                                )
                            path.move(x, y)
                            last_x, last_y = x, y
                    elif direction == DRAW_SUBSHAPE:
                        if self.type == "shapes":
                            subshape = code.pop()
                            if not skip:
                                code = code + bytearray(reversed(self.glyphs[subshape]))
                        elif self.type == "bigfont":
                            subshape = code.pop()
                            if subshape == 0:
                                subshape = int_16le([code.pop(), code.pop()])
                                origin_x = code.pop() * scale
                                origin_y = code.pop() * scale
                                width = code.pop() * scale
                                height = code.pop() * scale
                            if not skip:
                                try:
                                    code = code + bytearray(
                                        reversed(self.glyphs[subshape])
                                    )
                                except KeyError:
                                    pass  # TODO: Likely some bug here.
                        elif self.type == "unifont":
                            subshape = int_16le([code.pop(), code.pop()])
                            if not skip:
                                code = code + bytearray(reversed(self.glyphs[subshape]))
                    elif direction == XY_DISPLACEMENT:
                        dx = signed8(code.pop()) * scale
                        dy = signed8(code.pop()) * scale
                        if not skip:
                            x += dx
                            y += dy
                            if pen:
                                path.line(last_x, last_y, x, y)
                            else:
                                path.move(x, y)
                            last_x, last_y = x, y
                    elif direction == POLY_XY_DISPLACEMENT:
                        while True:
                            dx = signed8(code.pop()) * scale
                            dy = signed8(code.pop()) * scale
                            if dx == 0 and dy == 0:
                                break
                            if not skip:
                                x += dx
                                y += dy
                                if pen:
                                    path.line(last_x, last_y, x, y)
                                else:
                                    path.move(x, y)
                                last_x, last_y = x, y
                    elif direction == OCTANT_ARC:
                        radius = code.pop() * scale
                        sc = signed8(code.pop())
                        if not skip:
                            octant = tau / 8.0
                            ccw = (sc >> 7) & 1
                            s = (sc >> 4) & 0x7
                            c = sc & 0x7
                            if c == 0:
                                c = 8
                            if ccw:
                                s = -s
                            start_angle = s * octant
                            end_angle = (c + s) * octant
                            mid_angle = (start_angle + end_angle) / 2
                            # negative radius in the direction of start_octent finds center.
                            cx = x - radius * cos(start_angle)
                            cy = y - radius * sin(start_angle)
                            mx = cx + radius * cos(mid_angle)
                            my = cy + radius * sin(mid_angle)
                            x = cx + radius * cos(end_angle)
                            y = cy + radius * sin(end_angle)
                            if pen:
                                path.arc(last_x, last_y, mx, my, x, y)
                            else:
                                path.move(x, y)
                            last_x, last_y = x, y
                    elif direction == FRACTIONAL_ARC:
                        """
                        Fractional Arc.
                        Octant Arc plus fractional bits 0-255 parts of 45°
                        55° -> (55 - 45) * (256 / 45) = 56 (octent 1)
                        45° + (56/256 * 45°) = 55°
                        95° -> (95 - 90) * (256 / 45) = 28 (octent 2)
                        90° + (28/256 * 45°) = 95°
                        """
                        octant = tau / 8.0
                        start_offset = octant * code.pop() / 256.0
                        end_offset = octant * code.pop() / 256.0
                        radius = (256 * code.pop() + code.pop()) * scale
                        sc = signed8(code.pop())
                        if not skip:
                            ccw = (sc >> 7) & 1
                            s = (sc >> 4) & 0x7
                            c = sc & 0x7
                            if c == 0:
                                c = 8
                            if ccw:
                                s = -s
                            start_angle = start_offset + (s * octant)
                            end_angle = (c + s) * octant + end_offset
                            mid_angle = (start_angle + end_angle) / 2
                            cx = x - radius * cos(start_angle)
                            cy = y - radius * sin(start_angle)
                            mx = cx + radius * cos(mid_angle)
                            my = cy + radius * sin(mid_angle)
                            x = cx + radius * cos(end_angle)
                            y = cy + radius * sin(end_angle)
                            if pen:
                                path.arc(last_x, last_y, mx, my, x, y)
                            else:
                                path.move(x, y)
                            last_x, last_y = x, y
                    elif direction == BULGE_ARC:
                        dx = signed8(code.pop()) * scale
                        dy = signed8(code.pop()) * scale
                        h = signed8(code.pop())
                        if not skip:
                            r = abs(complex(dx, dy)) / 2
                            bulge = h / 127.0
                            bx = x + (dx / 2)
                            by = y + (dy / 2)
                            bulge_angle = atan2(dy, dx) - tau / 4
                            mx = bx + r * bulge * cos(bulge_angle)
                            my = by + r * bulge * sin(bulge_angle)
                            x += dx
                            y += dy
                            if pen:
                                if bulge == 0:
                                    path.line(x, y)
                                else:
                                    path.arc(last_x, last_y, mx, my, x, y)
                            else:
                                path.move(x, y)
                            last_x, last_y = x, y
                    elif direction == POLY_BULGE_ARC:
                        while True:
                            dx = signed8(code.pop()) * scale
                            dy = signed8(code.pop()) * scale
                            if dx == 0 and dy == 0:
                                break
                            h = signed8(code.pop())
                            if not skip:
                                r = abs(complex(dx, dy)) / 2
                                bulge = h / 127.0
                                bx = x + (dx / 2)
                                by = y + (dy / 2)
                                bulge_angle = atan2(dy, dx) - tau / 4
                                mx = bx + r * bulge * cos(bulge_angle)
                                my = by + r * bulge * sin(bulge_angle)
                                x += dx
                                y += dy
                                if pen:
                                    if bulge == 0:
                                        path.line(last_x, last_y, x, y)
                                    else:
                                        path.arc(last_x, last_y, mx, my, x, y)
                                else:
                                    path.move(x, y)
                                last_x, last_y = x, y
                    elif direction == COND_MODE_2:
                        if self.modes == 2 and horizontal:
                            skip = True
                            continue
                else:
                    if not skip:
                        if direction in (2, 1, 0, 0xF, 0xE):
                            dx = 1.0
                        elif direction in (3, 0xD):
                            dx = 0.5
                        elif direction in (4, 0xC):
                            dx = 0.0
                        elif direction in (5, 0xB):
                            dx = -0.5
                        else:  # (6, 7, 8, 9, 0xa):
                            dx = -1.0
                        if direction in (6, 5, 4, 3, 2):
                            dy = 1.0
                        elif direction in (7, 1):
                            dy = 0.5
                        elif direction in (8, 0):
                            dy = 0.0
                        elif direction in (9, 0xF):
                            dy = -0.5
                        else:  # (0xa, 0xb, 0xc, 0xd, 0xe, 0xf):
                            dy = -1.0
                        x += dx * length * scale
                        y += dy * length * scale
                        if pen:
                            path.line(last_x, last_y, x, y)
                        else:
                            path.move(x, y)
                        last_x, last_y = x, y
                skip = False
