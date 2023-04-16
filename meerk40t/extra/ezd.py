"""
Parser for .ezd files.
"""
import math
import struct
from io import BytesIO

from bitarray import bitarray

from meerk40t.core.exceptions import BadFileError
from meerk40t.core.units import UNITS_PER_MM, UNITS_PER_INCH
from meerk40t.svgelements import (
    Color,
    Rect,
    Matrix,
    Path,
    Circle,
    Ellipse,
    Polygon,
)


def plugin(kernel, lifecycle):
    if lifecycle == "boot":
        context = kernel.root
    elif lifecycle == "register":
        kernel.register("load/EZDLoader", EZDLoader)
        pass
    elif lifecycle == "shutdown":
        pass


def _parse_struct(file):
    """
    Parses a generic structure for ezd files. These are a count of objects. Then for each data entry int32le:length
    followed by data of that length.

    @param file:
    @return:
    """
    p = list()
    count = struct.unpack("<I", file.read(4))[0]
    for i in range(count):
        b = file.read(4)
        if len(b) != 4:
            return p
        (length,) = struct.unpack("<I", b)
        b = file.read(length)
        if len(b) != length:
            return p
        p.append(b)
    return p


def _interpret(data, index, type):
    if type == str:
        data[index] = data[index].decode("utf_16").strip("\x00")
    elif type == "point":
        data[index] = struct.unpack("2d", data[index])
    elif type == "short":
        (data[index],) = struct.unpack("<H", data[index])
    elif type == int:
        (data[index],) = struct.unpack("<I", data[index])
    elif type == float:
        (data[index],) = struct.unpack("d", data[index])
    elif type == "matrix":
        data[index] = struct.unpack("9d", data[index])


def _construct(data):
    for i in range(len(data)):
        b = data[i]
        length = len(b)
        if not isinstance(b, (bytes, bytearray)):
            continue
        if length == 2:
            _interpret(data, i, "short")
        elif length == 4:
            _interpret(data, i, int)
        elif length == 8:
            _interpret(data, i, float)
        elif length == 16:
            _interpret(data, i, "point")
        elif length == 60:
            _interpret(data, i, str)
        elif length == 72:
            _interpret(data, i, "matrix")
        elif length == 0:
            data[i] = None
    return data


class BitList(list):
    def frombytes(self, v):
        for b in v:
            for bit in range(8):
                b >>= 1
                self.append(b & 1)

    def decode(self, huffman):
        pass


class Pen:
    def __init__(
        self,
        color,  # 0
        label,  # 1
        mark_enable,  # 2, 1
        unk2,  # 3, 0
        loop_count,  # 4
        speed,  # 5
        power,  # 6
        frequency_hz,  # 7
        four,  # 8
        start_tc,  # 9
        end_tc,  # 10
        polygon_tc,  # 11
        jump_speed,  # 12
        jump_min_delay,  # 13
        jump_max_delay,  # 14
        opt_end_length,  # 15
        opt_start_length,  # 16
        time_per_point,  # 17
        unk3,  # 18, 0.0
        unk4,  # 19, 1.0
        prob_vector_point_mode,  # 20
        pulse_per_point,  # 21
        unk5,  # 22
        laser_off_tc,  # 23
        unk6,  # 24
        unk7,  # 25
        wobble_enable,  # 26
        wobble_diameter,  # 27
        wobble_distance,  # 28
        add_endpoints,  # 29
        add_endpoint_distance,  # 30
        add_endpoint_point_distance,  # 31
        add_endpoint_time_per_point,  # 32
        add_endpoints_point_cycles,  # 33
        unk8,  # 34, 0.02
        unk9,  # 35, 100
        unk10,  # 36, 0.5
        jump_min_jump_delay2,  # 37
        jump_max_delay2,  # 38
        jump_speed_max_limit,  # 39
        opt_enable,  # 40
        break_angle,  # 41
        *args,
    ):
        """
        Parse pen with given file.

        159 * 4, 636,0x027C bytes total
        """
        self.color = Color(bgr=color)
        self.label = label
        self.loop_count = loop_count
        self.speed = speed
        self.power = power
        self.frequency = frequency_hz / 1000.0
        self.start_tc = start_tc
        self.end_tc = end_tc
        self.polygon_tc = polygon_tc
        self.jump_speed = jump_speed
        self.jump_min_delay = jump_min_delay
        self.jump_max_delay = jump_max_delay
        self.opt_start_length = opt_start_length
        self.opt_end_length = opt_end_length
        self.time_per_point = time_per_point
        # unk3
        # unk4
        self.pulse_per_point = pulse_per_point
        self.laser_off_tc = laser_off_tc
        # unk6
        # unk7
        self.wobble_enable = wobble_enable
        self.wobble_diameter = wobble_diameter
        self.wobble_distance = wobble_distance

        self.add_endpoints = add_endpoints
        self.add_endpoint_distance = add_endpoint_distance
        self.add_endpoint_time_per_point = add_endpoint_time_per_point
        self.add_endpoint_point_distance = add_endpoint_point_distance
        self.add_endpoints_point_cycles = add_endpoints_point_cycles
        # unk8
        # unk9
        # unk10

        unk8,  # 34, 0.02
        unk9,  # 35, 100
        unk10,  # 36, 0.5
        self.opt_enable = opt_enable
        self.break_angle = break_angle


class EZCFile:
    def __init__(self, file):
        self._locations = {}
        self.pens = []
        self.objects = []
        self.fonts = []
        self._preview_bitmap = list()
        self._prevector = None
        self.parse_header(file)
        self.parse_seektable(file)
        self.parse_unknown_nontable(file)
        self.parse_tables(file)

    def parse_header(self, file):
        magic_number = file.read(16)
        header = magic_number.decode("utf_16")
        if header != "EZCADUNI":
            return False
        v0 = struct.unpack("<I", file.read(4))  # 0
        v1 = struct.unpack("<I", file.read(4))  # 2001
        s1 = file.read(60)
        s1 = s1.decode("utf-16")
        s2 = file.read(60)
        s2 = s2.decode("utf-16")
        s3 = file.read(60)
        s3 = s3.decode("utf-16")
        s4 = file.read(140)

    def parse_seektable(self, file):
        # Seek Table
        self._locations["preview"] = struct.unpack("<I", file.read(4))[0]
        self._locations["v1"] = struct.unpack("<I", file.read(4))[0]
        self._locations["pens"] = struct.unpack("<I", file.read(4))[0]
        self._locations["font"] = struct.unpack("<I", file.read(4))[0]
        self._locations["v4"] = struct.unpack("<I", file.read(4))[0]
        self._locations["vectors"] = struct.unpack("<I", file.read(4))[0]
        self._locations["prevectors"] = struct.unpack("<I", file.read(4))[0]

    def parse_unknown_nontable(self, file):
        unknown_table = struct.unpack("<24I", file.read(96))

    def parse_tables(self, file):
        self.parse_preview(file)
        self.parse_v1(file)
        self.parse_pens(file)
        self.parse_font(file)
        self.parse_v4(file)
        self.parse_vectors(file)
        self.parse_prevectors(file)

    def parse_v1(self, file):
        seek = self._locations.get("v1", 0)
        if seek == 0:
            return
        file.seek(seek, 0)

    def parse_v4(self, file):
        seek = self._locations.get("v4", 0)
        if seek == 0:
            return
        file.seek(seek, 0)
        unknown_table = struct.unpack("<24I", file.read(96))

    def parse_preview(self, file):
        seek = self._locations.get("preview", 0)
        if seek == 0:
            return
        file.seek(seek, 0)
        unknown = struct.unpack("<I", file.read(4))[0]
        width = struct.unpack("<I", file.read(4))[0]
        height = struct.unpack("<I", file.read(4))[0]
        v3 = struct.unpack("<3I", file.read(12))
        # 800, 0x200002

        # RGB0
        self._preview_bitmap.extend(
            struct.unpack(f"<{int(width*height)}I", file.read(4 * width * height))
        )

    def parse_font(self, file):
        seek = self._locations.get("font", 0)
        if seek == 0:
            return
        file.seek(seek, 0)
        font_count = struct.unpack("<I", file.read(4))[0]

        for i in range(font_count):
            f = file.read(100)
            self.fonts.append(f.decode("utf_16").strip("\x00"))

    def parse_pens(self, file):
        seek = self._locations.get("pens", 0)
        if seek == 0:
            return
        file.seek(seek, 0)

        parameter_count = struct.unpack("<I", file.read(4))[0]
        seek = struct.unpack("<I", file.read(4))[0]
        file.seek(seek, 0)
        for c in range(parameter_count):
            p = _parse_struct(file)
            _interpret(p, 1, str)
            _construct(p)
            self.pens.append(Pen(*p))

    def parse_prevectors(self, file):
        """
        Pre-vectors are usually 400 bytes with no values.

        @param file:
        @return:
        """
        seek = self._locations.get("prevectors", 0)
        if seek == 0:
            return
        file.seek(seek, 0)

        # 400 bytes of 00, 100 bytes of int
        self._prevector = struct.unpack("<400B", file.read(400))

    def parse_vectors(self, file):
        seek = self._locations.get("vectors", 0)
        if seek == 0:
            return
        file.seek(seek, 0)

        huffman_dict = {}

        uncompressed_length = struct.unpack("<I", file.read(4))[
            0
        ]  # 9C 2E 0B 00, 732828
        unknown2 = struct.unpack("<I", file.read(4))[0]  # DA E8 00 00, 59610
        unknown3 = struct.unpack("<I", file.read(4))[0]  # 23 08 02 00, 133338
        data_start = struct.unpack("<I", file.read(4))[0]  # 9C F0 04 00, 323740
        unknown5 = struct.unpack("<I", file.read(4))[0]  # AD 07 00 00, 1965

        table_length = struct.unpack("<H", file.read(2))[0]  # 00 01, 256
        for i in range(table_length):
            char = file.read(1)
            char = char[0]
            bb = file.read(4)
            bits = bitarray()
            bits.frombytes(bytes(reversed(bb)))
            cc = file.read(2)
            length = struct.unpack("<H", cc)[0]

            bits = bits[-length:]
            huffman_dict[char] = bitarray(bits)
        a = bitarray()
        a.frombytes(file.read())
        while True:
            try:
                q = bytearray(a.decode(huffman_dict))
                break
            except ValueError:
                a = a[:-1]
        self.parse_objects(BytesIO(q))

    def parse_objects(self, file):
        while parse_object(file, self.objects):
            pass


class EZObject:
    def __init__(self, file):
        header = _parse_struct(file)
        _interpret(header, 3, str)
        _construct(header)

        self.pen = header[0]
        self.type = header[1]
        self.state = header[2]

        # Selected 0x02, Hidden 0x01, Locked 0x10
        self.selected = bool(self.state & 0x02)
        self.hidden = bool(self.state & 0x01)
        self.locked = bool(self.state & 0x10)

        self.unknown1 = header[3]
        self.unknown2 = header[4]
        self.unknown3 = header[5]
        self.unknown4 = header[6]
        self.input_port_bits = header[7]
        self.array_state = header[8]
        self.array_bidirectional = bool(self.array_state & 0x2)
        self.array_vertical = bool(self.array_state & 0x1)
        self.array_count_x = header[9]
        self.array_count_y = header[10]
        self.array_step_x = header[11]
        self.array_step_y = header[12]
        self.position = header[13]
        self.z_pos = header[14]
        if isinstance(self, list):
            (count,) = struct.unpack("<I", file.read(4))
            for c in range(count):
                parse_object(file, self)


class EZCombine(list, EZObject):
    def __init__(self, file):
        list.__init__(self)
        EZObject.__init__(self, file)


class EZGroup(list, EZObject):
    def __init__(self, file):
        list.__init__(self)
        EZObject.__init__(self, file)


class EZVectorFile(list, EZObject):
    def __init__(self, file):
        list.__init__(self)
        EZObject.__init__(self, file)
        data1 = _parse_struct(file)
        _interpret(data1, 0, str)
        _construct(data1)

        self.path = data1[0]
        self.args = data1


class EZCurve(EZObject):
    def __init__(self, file):
        super().__init__(file)
        pts = []
        (count, unknown) = struct.unpack("<2I", file.read(8))
        for i in range(count):
            (curve_type, unk2, unk3) = struct.unpack("<3H", file.read(6))
            (pt_count,) = struct.unpack("<I", file.read(4))
            pts.append((curve_type, struct.unpack(f"<{pt_count * 2}d", file.read(16 * pt_count))))
        self.points = pts


class EZRect(EZObject):
    def __init__(self, file):
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _construct(args)
        self.min_pos = args[0]
        self.max_pos = args[1]
        self.corner_upper_left = args[0]
        self.corner_bottom_right = args[1]
        self.round_c1 = args[2]
        self.round_c2 = args[3]
        self.round_c3 = args[4]
        self.round_c4 = args[5]
        self.unknown5 = args[6]
        self.matrix = args[7]


class EZCircle(EZObject):
    def __init__(self, file):
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _construct(args)
        self.center = args[0]
        self.radius = args[1]
        self.start_angle = args[2]
        self.cw = args[3]
        self.circle_prop0 = args[4]
        self.matrix = args[5]


class EZEllipse(EZObject):
    def __init__(self, file):
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _construct(args)
        self.corner_upper_left = args[1]
        self.corner_bottom_right = args[2]
        self.start_angle = args[3]
        self.end_angle = args[4]
        self.matrix = args[6]


class EZSpiral(list, EZObject):
    def __init__(self, file):
        list.__init__(self)
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _construct(args)
        print(args)
        print(self.__dict__)


class EZPolygon(EZObject):
    def __init__(self, file):
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _construct(args)
        self.corner_upper_left = args[1]
        self.corner_bottom_right = args[2]
        self.sides = args[7]
        self.matrix = args[9]


class EZTimer(EZObject):
    def __init__(self, file):
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _construct(args)
        self.wait_time = args[1]


class EZInput(EZObject):
    def __init__(self, file):
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _interpret(args, 1, str)
        _construct(args)
        self.message_enabled = bool(args[0])
        self.message = args[1]


class EZOutput(EZObject):
    def __init__(self, file):
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _construct(args)
        self.output_bit = args[0]
        self.low_to_high = bool(args[1])  # 1
        self.timed_high = bool(args[2])  # 0
        self.wait_time = args[4]  # args[18] is int value
        self.all_out_mode = bool(args[5])
        self.all_out_bits = args[6]


class EZText(EZObject):
    def __init__(self, file):
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _interpret(args, 10, str)
        _interpret(args, 18, str)
        _interpret(args, 44, str)
        _construct(args)
        self.font_angle = args[0]  # Font angle in Text.
        self.text = args[10]


class EZImage(EZObject):
    def __init__(self, file):
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _construct(args)

        image_bytes = bytearray(file.read(2))  # BM
        image_length = file.read(4)  # int32le
        (size,) = struct.unpack("<I", image_length)
        image_bytes += image_length
        image_bytes += file.read(size - 6)

        from PIL import Image

        image = Image.open(BytesIO(image_bytes))

        self.image_path = args[0]
        self.width = args[5]
        self.height = args[4]
        self.fixed_dpi_x = args[9]
        self.fixed_dpi_y = args[333 - 15]
        self.image = image
        self.powermap = args[74 - 15 : 330 - 15]
        self.scan_line_increment = args[29 - 15]
        self.scan_line_increment_value = args[30 - 15]
        self.disable_mark_low_gray_point = args[31 - 15]
        self.disable_mark_low_gray_point_value = args[32 - 15]
        self.acc_distance_mm = args[331 - 15]
        self.dec_distance_mm = args[332 - 15]
        self.all_offset_mm = args[334 - 15]
        self.bidirectional_offset = args[330 - 15]
        self.status_bits = args[25 - 15]
        self.mirror_x = bool(self.status_bits & 0x20)
        self.mirror_y = bool(self.status_bits & 0x40)


class EZHatch(list, EZObject):
    def __init__(self, file):
        list.__init__(self)
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _construct(args)
        print(args)
        self.group = EZGroup(file)
        print(self.group)


object_map = {
    1: EZCurve,
    3: EZRect,
    4: EZCircle,
    5: EZEllipse,
    6: EZPolygon,
    0x30: EZCombine,
    0x40: EZImage,
    0x60: EZSpiral,
    0x4000: EZOutput,
    0x3000: EZInput,
    0x2000: EZTimer,
    0x800: EZText,
    0x10: EZGroup,
    0x50: EZVectorFile,
    0x20: EZHatch,
}


def parse_object(file, objects):
    object_type = struct.unpack("<I", file.read(4))[0]  # 0
    if object_type == 0:
        return False
    ez_class = object_map.get(object_type)
    assert ez_class
    objects.append(ez_class(file))
    return True


class EZDLoader:
    @staticmethod
    def load_types():
        yield "EZCad2 Files", ("ezd",), "application/x-ezd"

    @staticmethod
    def load(context, elements_service, pathname, **kwargs):
        try:
            with open(pathname, "br") as file:
                ezfile = EZCFile(file)
        except IOError as e:
            raise BadFileError(str(e)) from e

        ez_processor = EZProcessor(elements_service)
        ez_processor.process(ezfile, pathname)
        return True


class EZProcessor:
    def __init__(self, elements):
        self.elements = elements
        self.element_list = list()
        self.regmark_list = list()
        self.pathname = None
        self.regmark = self.elements.reg_branch
        self.op_branch = elements.op_branch
        self.elem_branch = elements.elem_branch

        self.width = elements.device.unit_width
        self.height = elements.device.unit_height
        self.matrix = Matrix.map(
            (-50, 50),
            (50, 50),
            (50, -50),
            (-50, -50),
            (0, 0),
            (self.width, 0),
            (self.width, self.height),
            (0, self.height),
        )

    def process(self, ez, pathname):

        self.op_branch.remove_all_children()
        self.elem_branch.remove_all_children()
        # for p in ez.pens:
        #     self.op_branch.add(type="op engrave", **p.__dict__)
        self.pathname = pathname
        file_node = self.elem_branch.add(type="file", filepath=pathname)
        file_node.focus()
        for f in ez.objects:
            self.parse(ez, f, file_node, self.op_branch)

    def parse(self, ez, element, elem, op):
        if isinstance(element, EZText):
            node = elem.add(type="elem text", text=element.text, transform=self.matrix)
            p = ez.pens[element.pen]
            op_add = op.add(type="op engrave", **p.__dict__)
            op_add.add_reference(node)

        elif isinstance(element, EZCurve):
            points = element.points

            path = Path(stroke="black", transform=self.matrix)
            for pt in points:
                if len(path) == 0:
                    path.move(pt[0:2])
                if len(pt) == 4:
                    path.line(pt[2:4])
                elif len(pt) == 6:
                    path.quad(pt[2:4], pt[4:6])
                elif len(pt) == 8:
                    path.cubic(pt[2:4], pt[4:6], pt[6:8])
            node = elem.add(type="elem path", path=path)
            p = ez.pens[element.pen]
            op_add = op.add(type="op engrave", **p.__dict__)
            op_add.add_reference(node)

        elif isinstance(element, EZPolygon):
            m = element.matrix
            mx = Matrix(m[0], m[1], m[3], m[4], m[6], m[7])
            mx *= self.matrix
            x0, y0 = element.corner_upper_left
            x1, y1 = element.corner_bottom_right
            step = math.tau / element.sides
            cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            rx = (x1 - x0) / 2.0
            ry = (y1 - y0) / 2.0
            pts = []
            theta = step / 2.0
            for i in range(element.sides):
                pts.append((cx + math.cos(theta) * rx, cy + math.sin(theta) * ry))
                theta += step
            polyline = Polygon(points=pts, transform=mx, stroke="black")
            node = elem.add(type="elem polyline", shape=polyline)
            p = ez.pens[element.pen]
            op_add = op.add(type="op engrave", **p.__dict__)
            op_add.add_reference(node)

        elif isinstance(element, EZCircle):
            m = element.matrix
            mx = Matrix(m[0], m[1], m[3], m[4], m[6], m[7])
            mx *= self.matrix
            shape = Circle(
                center=element.center, r=element.radius, transform=mx, stroke="black"
            )
            node = elem.add(type="elem ellipse", shape=shape)
            p = ez.pens[element.pen]
            op_add = op.add(type="op engrave", **p.__dict__)
            op_add.add_reference(node)

        elif isinstance(element, EZEllipse):
            m = element.matrix
            mx = Matrix(m[0], m[1], m[3], m[4], m[6], m[7])
            mx *= self.matrix
            x0, y0 = element.corner_upper_left
            x1, y1 = element.corner_bottom_right
            shape = Ellipse(
                center=((x0 + x1) / 2.0, (y0 + y1) / 2.0),
                rx=(x1 - x0) / 2.0,
                ry=(y1 - y0) / 2.0,
                transform=mx,
                stroke="black",
            )
            node = elem.add(type="elem ellipse", shape=shape)
            p = ez.pens[element.pen]
            op_add = op.add(type="op engrave", **p.__dict__)
            op_add.add_reference(node)

        elif isinstance(element, EZRect):
            m = element.matrix
            mx = Matrix(m[0], m[1], m[3], m[4], m[6], m[7])
            mx *= self.matrix
            x0, y0 = element.corner_upper_left
            x1, y1 = element.corner_bottom_right
            rect = Rect(x0, y0, x1 - x0, y1 - y0, transform=mx, stroke="black")
            node = elem.add(type="elem rect", shape=rect)
            p = ez.pens[element.pen]
            op_add = op.add(type="op engrave", **p.__dict__)
            op_add.add_reference(node)

        elif isinstance(element, EZTimer):
            op.add(type="util wait", wait=element.wait_time / 1000.0)
        elif isinstance(element, EZOutput):
            mask = 1 << element.output_bit
            bits = mask if element.low_to_high else 0

            op.add(
                type="util output",
                output_value=bits,
                output_mask=mask,
            )
            if element.timed_high:
                op.add(type="util wait", wait=element.wait_time / 1000.0)
                op.add(
                    type="util output",
                    output_value=~bits,
                    output_mask=mask,
                )

        elif isinstance(element, EZInput):
            op.add(
                type="util input",
                input_message=element.message,
                input_value=element.input_port_bits,
                input_mask=element.input_port_bits,
            )
        elif isinstance(element, EZImage):
            image = element.image
            left, top = self.matrix.point_in_matrix_space(
                (
                    element.position[0] - (element.width / 2.0),
                    element.position[1] + element.height / 2.0,
                )
            )
            w, h = image.size
            unit_width = element.width * UNITS_PER_MM
            unit_height = element.height * UNITS_PER_MM
            matrix = Matrix.scale(
                (unit_width / w),
                (unit_height / h),
            )
            _dpi = int(
                round(
                    (
                        float((w * UNITS_PER_INCH) / unit_width)
                        + float((h * UNITS_PER_INCH) / unit_height)
                    )
                    / 2.0,
                )
            )
            matrix.post_translate(left, top)
            node = elem.add(type="elem image", image=image, matrix=matrix, dpi=_dpi)
            p = ez.pens[element.pen]
            op_add = op.add(type="op image", **p.__dict__)
            op_add.add_reference(node)
        elif isinstance(element, EZVectorFile):
            for child in element:
                # (self, ez, element, elem, op)
                self.parse(ez, child, elem, op)
        elif isinstance(element, EZGroup):
            elem = elem.add(type="group")
            # recurse to children
            for child in element:
                self.parse(ez, child, elem, op)
