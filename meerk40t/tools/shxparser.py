from math import tau, cos, sin, atan2, isinf

SHXPARSER_VERSION = "0.0.2"


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
    try:
        bb = bytearray()
        while True:
            b = stream.read(1)
            if b == b"":
                return bb.decode("utf-8")
            if b == b"\r" or b == b"\n" or b == b"\x00":
                return bb.decode("utf-8")
            bb += b
    except UnicodeDecodeError as e:
        raise ShxFontParseError(f"Read string did not capture valid text. {bb}") from e


class ShxPath:
    """
    Example path code. Any class with these functions would work as well. When render is called on the ShxFont class
    the path is given particular useful segments.
    """

    def __init__(self):
        self.path = list()

    def bounds(self):
        """
        Get bounds of paths.
        :return:
        """
        min_x = float("inf")
        min_y = float("inf")
        max_x = -float("inf")
        max_y = -float("inf")
        for p in self.path:
            if p is None:
                continue
            min_x = min(p[0], min_x)
            min_y = min(p[1], min_y)
            max_x = max(p[0], max_x)
            max_y = max(p[1], max_y)

            min_x = min(p[-2], min_x)
            min_y = min(p[-1], min_y)
            max_x = max(p[-2], max_x)
            max_y = max(p[-1], max_y)
        if isinf(min_x):
            return None
        return min_x, min_y, max_x, max_y

    def scale(self, scale_x, scale_y):
        for p in self.path:
            if p is None:
                continue
            if len(p) >= 2:
                p[0] *= scale_x
                p[1] *= scale_y
            if len(p) >= 4:
                p[2] *= scale_x
                p[3] *= scale_y
            if len(p) >= 6:
                p[4] *= scale_x
                p[5] *= scale_y

    def translate(self, translate_x, translate_y):
        for p in self.path:
            if p is None:
                continue
            if len(p) >= 2:
                p[0] += translate_x
                p[1] += translate_y
            if len(p) >= 4:
                p[2] += translate_x
                p[3] += translate_y
            if len(p) >= 6:
                p[4] += translate_x
                p[5] += translate_y

    def new_path(self):
        """
        Start of a new path.
        """
        self.path.append(None)

    def move(self, x, y):
        """
        Move current point to the point specified.
        """
        self.path.append([x, y])

    def line(self, x0, y0, x1, y1):
        """
        Draw a line from the current point to the specified point.
        """
        self.path.append([x0, y0, x1, y1])

    def arc(self, x0, y0, cx, cy, x1, y1):
        """
        Draw an arc from the current point to specified point going through the control point.

        3 Points define a circular arc, there is only one arc which travels from start to end going through a given
        control point. The exceptions are when the arc points are collinear or two arc points are coincident. In some
        cases the start and end points will be equal and the control point will be located the circle diameter away.
        """
        self.path.append([x0, y0, cx, cy, x1, y1])


class ShxFontParseError(Exception):
    """
    Exception thrown if unable to pop a value from the given codes or other suspected parsing errors.
    """


class ShxFont:
    """
    This class performs the parsing of the three major types of .SHX fonts. Composing them into specific glyphs which
    consist of commands in a vector-shape language. When .render() is called on some text, vector actions are performed
    on the font which create the vector path.
    """

    def __init__(self, filename, debug=False):
        self.format = None  # format (usually AutoCAD-86)
        self.type = None  # Font type: shapes, bigfont, unifont
        self.version = None  # Font file version (usually 1.0).
        self.glyphs = dict()  # Glyph dictionary
        self.font_name = None  # Parsed font name.
        self.above = None  # Distance above baseline for capital letters.
        self.below = None  # Distance below baseline for lowercase letters
        self.modes = None  # 0 Horizontal Only, 2 Dual mode (Horizontal or Vertical)
        self.encoding = False  # 0 unicode, 1 packed multibyte, 2 shape file
        self.embedded = False  # 0 font can be embedded, 1 font cannot be embedded, 2 embedding is read-only

        self._debug = debug
        self._code = None
        self._path = None
        self._skip = False
        self._pen = False
        self._horizontal = True
        self._letter = None
        self._x = 0
        self._y = 0
        self._last_x = 0
        self._last_y = 0
        self._scale = 1
        self._stack = []

        self._parse(filename)

    def __str__(self):
        return f'{self.type}("{self.font_name}", {self.version}, glyphs: {len(self.glyphs)})'

    def _parse(self, filename):
        with open(filename, "br") as f:
            self._parse_header(f)
            if self._debug:
                print(f"Font header indicates font type is {self.type}")
            if self.type == "shapes":
                self._parse_shapes(f)
            elif self.type == "bigfont":
                self._parse_bigfont(f)
            elif self.type == "unifont":
                self._parse_unifont(f)
            else:
                raise ShxFontParseError(f"{self.type} is not a valid shx file type.")

    def _parse_header(self, f):
        header = read_string(f)
        parts = header.split(" ")
        if len(parts) != 3:
            raise ShxFontParseError(f"Header information invalid: {header}")
        self.format = parts[0]
        self.type = parts[1]
        self.version = parts[2]
        f.read(2)

    def _parse_shapes(self, f):
        start = read_int_16le(f)
        end = read_int_16le(f)
        count = read_int_16le(f)
        if self._debug:
            print(f"Parsing shape: start={start}, end={end}, count={count}")
        glyph_ref = list()
        for i in range(count):
            index = read_int_16le(f)
            length = read_int_16le(f)
            glyph_ref.append((index, length))

        for index, length in glyph_ref:
            if index == 0:
                if self.font_name is not None:
                    raise ShxFontParseError("Double-initializing glyph data detected")
                self.font_name = read_string(f)
                self.above = read_int_8(f)  # vector lengths above baseline
                self.below = read_int_8(f)  # vector lengths below baseline
                # 0 - Horizontal, 2 - dual. 0x0E command only when mode=2
                self.modes = read_int_8(f)
                # end = read_int_16le(f)
            else:
                read = f.read(length)
                data = read
                if len(data) != length:
                    raise ShxFontParseError("Glyph length did not exist in file.")
                if data[0] == 0 and data[1] == 0:
                    data = data[2:]
                elif data[0] == 0:
                    data = data[1:]
                    find = data.find(b"\x00")
                    if find != -1:
                        name = data[:find]

                        for c in name:
                            if ord("A") <= c <= ord("Z") or ord("0") <= c <= ord("9") or c == ord(" ") or c == ord("&"):
                                continue
                            name = None
                            break
                        if name is not None:
                            data = data[find+1:]
                            name = name.decode()
                            self.glyphs[name] = data
                        else:
                            if self._debug:
                                print(f"{data} did not contain a name.")
                self.glyphs[index] = data

    def _parse_bigfont(self, f):
        count = read_int_16le(f)
        length = read_int_16le(f)
        changes = list()
        change_count = read_int_16le(f)
        if self._debug:
            print(f"Parsing bigfont: count={count}, length={length}, change_count={change_count}")
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
        if self._debug:
            print(f"Parsing unifont: name={self.font_name}, count={count}, length={length}")
        for i in range(count - 1):
            index = read_int_16le(f)
            length = read_int_16le(f)
            self.glyphs[index] = f.read(length)

    def pop(self):
        try:
            return self._code.pop()
        except IndexError as e:
            raise ShxFontParseError("No codes to pop()") from e

    def render(self, path, text, horizontal=True, font_size=12.0):
        if self.above is None:
            self.above = 1
        self._scale = font_size / self.above
        self._horizontal = horizontal
        self._path = path
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
            self._letter = letter
            try:
                self._code = bytearray(reversed(self.glyphs[ord(letter)]))
            except KeyError:
                # Letter is not found.
                continue
            self._pen = True
            while self._code:
                try:
                    self._parse_code()
                except IndexError as e:
                    raise ShxFontParseError("Stack Error during render.") from e
            self._skip = False
        if self._debug:
            print(f"Render Complete.\n\n\n")

    def _parse_code(self):
        b = self.pop()
        direction = b & 0x0F
        length = (b & 0xF0) >> 4
        if length == 0:
            self._parse_code_special(direction)
        else:
            self._parse_code_length(direction, length)

    def _parse_code_length(self, direction, length):
        """
        Length direction codes. If length is 0 then direction is special otherwise the
        command is a move in one of 16 different directions moving in 22.5° increments for
        a distance of 1 to 15 units lengths.

        :param direction:
        :param length:
        :return:
        """
        if self._debug:
            print(f"MOVE DIRECTION {direction} for {length}  {'(Skipped)' if self._skip else ''}")
        if self._skip:
            self._skip = False
            return
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
        self._x += dx * length * self._scale
        self._y += dy * length * self._scale
        if self._pen:
            self._path.line(self._last_x, self._last_y, self._x, self._y)
        else:
            self._path.move(self._x, self._y)
        self._last_x, self._last_y = self._x, self._y

    def _parse_code_special(self, special):
        if special == END_OF_SHAPE:
            self._end_of_shape()
        elif special == PEN_DOWN:
            self._pen_down()
        elif special == PEN_UP:
            self._pen_up()
        elif special == DIVIDE_VECTOR:
            self._divide_vector()
        elif special == MULTIPLY_VECTOR:
            self._multiply_vector()
        elif special == PUSH_STACK:
            self._push_stack()
        elif special == POP_STACK:
            self._pop_stack()
        elif special == DRAW_SUBSHAPE:
            self._draw_subshape()
        elif special == XY_DISPLACEMENT:
            self._xy_displacement()
        elif special == POLY_XY_DISPLACEMENT:
            self._poly_xy_displacement()
        elif special == OCTANT_ARC:
            self._octant_arc()
        elif special == FRACTIONAL_ARC:
            self._fractional_arc()
        elif special == BULGE_ARC:
            self._bulge_arc()
        elif special == POLY_BULGE_ARC:
            self._poly_bulge_arc()
        elif special == COND_MODE_2:
            self._cond_mode_2()

    def _end_of_shape(self):
        """
        End of shape definition.
        :return:
        """
        try:
            while self.pop() != 0:
                pass
        except ShxFontParseError:
            pass
        if self._debug:
            print("END_OF_SHAPE")
        if self._skip:
            self._skip = False
            return
        self._path.new_path()

    def _pen_down(self):
        """
        Activates draw mode. Pen is down. Draw is activated for each shape.
        :return:
        """
        if self._debug:
            print(f"PEN_DOWN: {self._x}, {self._y} {'(Skipped)' if self._skip else ''}")
        if self._skip:
            self._skip = False
            return
        self._pen = True
        self._path.move(self._x, self._y)

    def _pen_up(self):
        """
        Deactivates draw mode. Subsequent draws are moves to new locations.
        :return:
        """
        if self._debug:
            print(f"PEN_UP {'(Skipped)' if self._skip else ''}")
        if self._skip:
            self._skip = False
            return
        self._pen = False

    def _divide_vector(self):
        """
        Height is specified with shape command. Initially considered the length of a single vector.
        Divides the scale factor by the next byte.

        :return:
        """
        factor = self.pop()
        if self._debug:
            print(f"DIVIDE_VECTOR {self._scale}/{factor} {'(Skipped)' if self._skip else ''}")
        if factor == 0:
            raise ShxFontParseError("Divide Vector is not permitted to be 0.")
        if self._skip:
            self._skip = False
            return
        self._scale /= factor

    def _multiply_vector(self):
        """
        Multiplies the scale factor by the next byte.

        :return:
        """
        factor = self.pop()
        if self._debug:
            print(f"MULTIPLY_VECTOR {self._scale}*{factor} {'(Skipped)' if self._skip else ''}")
        if factor == 0:
            raise ShxFontParseError("Multiply Vector is not permitted to be 0.")
        if self._skip:
            self._skip = False
            return
        self._scale *= factor

    def _push_stack(self):
        """
        Stack is considered four units deep. Everything pushed on the stack must be
        popped from the stack. Overflows respond with an error message.

        :return:
        """
        if self._debug:
            print(f"PUSH_STACK {self._x}, {self._y} {'(Skipped)' if self._skip else ''}")
        if self._skip:
            self._skip = False
            return
        self._stack.append((self._x, self._y))
        if len(self._stack) == 4:
            raise IndexError(
                f"Position stack overflow in shape {self._letter}"
            )

    def _pop_stack(self):
        """
        Stack is considered four units deep. You may not pop more locations than have
        been pushed onto the stack. Attempts to do so will respond with a error message.
        :return:
        """
        if self._debug:
            print(f"POP_STACK {self._x}, {self._y}  {'(Skipped)' if self._skip else ''}")

        if self._skip:
            self._skip = False
            return
        try:
            self._x, self._y = self._stack.pop()
        except IndexError:
            raise IndexError(
                f"Position stack underflow in shape {self._letter}"
            )
        self._path.move(self._x, self._y)
        self._last_x, self._last_y = self._x, self._y

    def _draw_subshape_shapes(self):
        subshape = self.pop()
        if self._debug:
            print(f"Appending glyph {subshape} (Type={self.type}). {'(Skipped)' if self._skip else ''}")
        if self._skip:
            self._skip = False
            return
        try:
            shape = self.glyphs[subshape]
        except KeyError as e:
            raise ShxFontParseError("Referenced subshape does not exist.") from e
        self._code += bytearray(reversed(shape))

    def _draw_subshape_bigfont(self):
        subshape = self.pop()
        if self._debug:
            print(f"Appending glyph {subshape} (Type={self.type}). {'(Skipped)' if self._skip else ''}")
        if subshape == 0:
            subshape = int_16le([self.pop(), self.pop()])
            origin_x = self.pop() * self._scale
            origin_y = self.pop() * self._scale
            width = self.pop() * self._scale
            height = self.pop() * self._scale
            if self._debug:
                print(f"Extended Bigfont Glyph: {subshape}, origin_x = {origin_x}, origin_y = {origin_y}. {width}x{height}")
        if self._skip:
            self._skip = False
            return
        try:
            shape = self.glyphs[subshape]
        except KeyError as e:
            raise ShxFontParseError("Referenced subshape does not exist.") from e
        self._code += bytearray(reversed(shape))

    def _draw_subshape_unifont(self):
        subshape = int_16le([self.pop(), self.pop()])
        if self._debug:
            print(f"Appending glyph {subshape} (Type={self.type}). {'(Skipped)' if self._skip else ''}")
        if self._skip:
            self._skip = False
            return
        try:
            shape = self.glyphs[subshape]
        except KeyError as e:
            raise ShxFontParseError("Referenced subshape does not exist.") from e
        self._code += bytearray(reversed(shape))

    def _draw_subshape(self):
        """
        Subshape is given in next byte, for non-unicode fonts one byte is used for
        unicode fonts two bytes are used and shapes are numbered from 1 to 65535.

        Drawmode is not reset for the subshape. When complete the current shape
        continues.
        :return:
        """
        if self.type == "shapes":
            self._draw_subshape_shapes()
        elif self.type == "bigfont":
            self._draw_subshape_bigfont()
        elif self.type == "unifont":
            self._draw_subshape_unifont()

    def _xy_displacement(self):
        """
        X,Y displacement given in next two bytes 1 byte-x, 1 byte-y. The displacement
        ranges from -128 to +127.
        :return:
        """
        dx = signed8(self.pop()) * self._scale
        dy = signed8(self.pop()) * self._scale
        if self._debug:
            print(f"XY_DISPLACEMENT {dx} {dy} {'(Skipped)' if self._skip else ''}")
        if self._skip:
            self._skip = False
            return
        self._x += dx
        self._y += dy
        if self._pen:
            self._path.line(self._last_x, self._last_y, self._x, self._y)
        else:
            self._path.move(self._x, self._y)
        self._last_x, self._last_y = self._x, self._y

    def _poly_xy_displacement(self):
        """
        XY displacement in a series terminated with (0,0)
        :return:
        """
        while True:
            dx = signed8(self.pop()) * self._scale
            dy = signed8(self.pop()) * self._scale
            if self._debug:
                print(f"POLY_XY_DISPLACEMENT {dx} {dy} {'(Skipped)' if self._skip else ''}")
            if dx == 0 and dy == 0:
                if self._debug:
                    print("POLY_XY_DISPLACEMENT (Terminated)")
                break
            if self._skip:
                continue
            self._x += dx
            self._y += dy
            if self._pen:
                self._path.line(self._last_x, self._last_y, self._x, self._y)
            else:
                self._path.move(self._x, self._y)
            self._last_x, self._last_y = self._x, self._y
        if self._skip:
            self._skip = False

    def _octant_arc(self):
        """
        Octant arc spans one or more 45° octants starting and ending at a boundary.
        Octants are numbered ccw starting from 0° at the 3 o'clock position.

        3 2 1
         \ /
        4-O-0
         / \
        5 6 7

        First byte specifies the radius as a value from 1 to 255. The second is the
        direction of the arc. Each nibble of the second byte defines s and c the start
        and the span.
        :return:
        """
        radius = self.pop() * self._scale
        sc = signed8(self.pop())
        s = (sc >> 4) & 0x7
        c = sc & 0x7
        if self._debug:
            print(f"OCTANT_ARC, {radius}, {s}, {c} {'(Skipped)' if self._skip else ''}")
        if self._skip:
            self._skip = False
            return
        octant = tau / 8.0
        ccw = (sc >> 7) & 1
        if c == 0:
            c = 8
        if ccw:
            s = -s
        start_angle = s * octant
        end_angle = (c + s) * octant
        mid_angle = (start_angle + end_angle) / 2
        # negative radius in the direction of start_octent finds center.
        cx = self._x - radius * cos(start_angle)
        cy = self._y - radius * sin(start_angle)
        mx = cx + radius * cos(mid_angle)
        my = cy + radius * sin(mid_angle)
        self._x = cx + radius * cos(end_angle)
        self._y = cy + radius * sin(end_angle)
        if self._pen:
            self._path.arc(self._last_x, self._last_y, mx, my, self._x, self._y)
        else:
            self._path.move(self._x, self._y)
        self._last_x, self._last_y = self._x, self._y

    def _fractional_arc(self):
        """
        Fractional Arc.
        Octant Arc plus fractional bits 0-255 parts of 45°
        55° -> (55 - 45) * (256 / 45) = 56 (octent 1)
        45° + (56/256 * 45°) = 55°
        95° -> (95 - 90) * (256 / 45) = 28 (octent 2)
        90° + (28/256 * 45°) = 95°
        """
        octant = tau / 8.0
        start_offset = octant * self.pop() / 256.0
        end_offset = octant * self.pop() / 256.0
        radius = (256 * self.pop() + self.pop()) * self._scale
        sc = signed8(self.pop())
        s = (sc >> 4) & 0x7
        c = sc & 0x7

        if self._debug:
            print(f"FRACTION_ARC {start_offset}, {end_offset}, {radius}, {s}, {c} {'(Skipped)' if self._skip else ''}")
        if self._skip:
            self._skip = False
            return
        ccw = (sc >> 7) & 1

        if c == 0:
            c = 8
        if ccw:
            s = -s
        start_angle = start_offset + (s * octant)
        end_angle = (c + s) * octant + end_offset
        mid_angle = (start_angle + end_angle) / 2
        cx = self._x - radius * cos(start_angle)
        cy = self._y - radius * sin(start_angle)
        mx = cx + radius * cos(mid_angle)
        my = cy + radius * sin(mid_angle)
        self._x = cx + radius * cos(end_angle)
        self._y = cy + radius * sin(end_angle)
        if self._pen:
            self._path.arc(self._last_x, self._last_y, mx, my, self._x, self._y)
        else:
            self._path.move(self._x, self._y)
        self._last_x, self._last_y = self._x, self._y

    def _bulge_arc(self):
        """
        Arc defined by xy and displacement bulge. 1-byte-X, 1-byte-Y, 1-byte-bulge.

        This gives us X from -127 to +127 and Y from -127 to +127. The bulge height
        is given as 127  * 2 * H / D If the sign is negative the location is clockwise.

        :return:
        """

        dx = signed8(self.pop()) * self._scale
        dy = signed8(self.pop()) * self._scale
        h = signed8(self.pop())

        if self._debug:
            print(f"BULGE_ARC {dx}, {dy}, {h} {'(Skipped)' if self._skip else ''}")
        if self._skip:
            self._skip = False
            return
        r = abs(complex(dx, dy)) / 2
        bulge = h / 127.0
        bx = self._x + (dx / 2)
        by = self._y + (dy / 2)
        bulge_angle = atan2(dy, dx) - tau / 4
        mx = bx + r * bulge * cos(bulge_angle)
        my = by + r * bulge * sin(bulge_angle)
        self._x += dx
        self._y += dy
        if self._pen:
            if bulge == 0:
                self._path.line(self._last_x, self._last_y, self._x, self._y)
            else:
                self._path.arc(self._last_x, self._last_y, mx, my, self._x, self._y)
        else:
            self._path.move(self._x, self._y)
        self._last_x, self._last_y = self._x, self._y

    def _poly_bulge_arc(self):
        """
        Similar to bulge but repeated, until X and Y are (0,0).
        :return:
        """
        h = 0
        while True:
            dx = signed8(self.pop()) * self._scale
            dy = signed8(self.pop()) * self._scale
            if self._debug:
                print(f"POLY_BULGE_ARC {dx}, {dy}, {h} {'(Skipped)' if self._skip else ''}")
            if dx == 0 and dy == 0:
                if self._debug:
                    print(f"POLY_BULGE_ARC (TERMINATED)")
                break
            h = signed8(self.pop())
            if self._skip:
                continue
            r = abs(complex(dx, dy)) / 2
            bulge = h / 127.0
            bx = self._x + (dx / 2)
            by = self._y + (dy / 2)
            bulge_angle = atan2(dy, dx) - tau / 4
            mx = bx + r * bulge * cos(bulge_angle)
            my = by + r * bulge * sin(bulge_angle)
            self._x += dx
            self._y += dy
            if self._pen:
                if bulge == 0:
                    self._path.line(self._last_x, self._last_y, self._x, self._y)
                else:
                    self._path.arc(self._last_x, self._last_y, mx, my, self._x, self._y)
            else:
                self._path.move(self._x, self._y)
            self._last_x, self._last_y = self._x, self._y
        if self._skip:
            self._skip = False

    def _cond_mode_2(self):
        """
        Process the next command only in vertical text.

        :return:
        """
        if self._debug:
            print("COND_MODE_2")
        if self.modes == 2 and self._horizontal:
            if self._debug:
                print("SKIP NEXT")
            self._skip = True
