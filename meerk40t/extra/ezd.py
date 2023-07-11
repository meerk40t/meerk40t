"""
Parser for .ezd files.

These are a working type file produced by EZCad2™. They contain several pens and different settings that were used by
the program when the file was saved. The vector objects consist of a series of laser-ready commands/shapes which refer
to the required pen. Some modification objects like hatch and spiral work like a group containing other sub-elements
and also contain the cached curve/path data. The image objects contain a standard 24 bit bitmap image. All elements
are coordinated relative to the center of the working area and, it is much more common to be given the center point than
a specific corner. Nearly all coordinates are in mm, and denote the deviation from the center point.

"""
import math
import struct
from io import BytesIO

from meerk40t.core.exceptions import BadFileError
from meerk40t.core.units import UNITS_PER_INCH, UNITS_PER_MM
from meerk40t.svgelements import Color, Matrix, Path, Polygon


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
    """
    Provide a specific hint for how to interpret a chunk of bytes. There are cases where 16 bytes could be a point,
    consisting of two floating points, but could also be a string. This is used to force the typing to use the correct
    method.

    @param data:
    @param index:
    @param type:
    @return:
    """
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
    """
    For each element of data (that is a bytes object), interpret them as their most common type.

    @param data:
    @return:
    """
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


def _huffman_decode_python(file, uncompressed_length):
    """
    Python fallback for huffman decoding of the vector table.

    @param file:
    @param uncompressed_length:
    @return:
    """
    huffman_dict = {}
    table_length = struct.unpack("<H", file.read(2))[0]
    for i in range(table_length):
        character, bb, length = struct.unpack("<BIH", file.read(7))
        bits = "{:032b}".format(bb)[-length:]
        huffman_dict[bits] = character
    data = file.read()

    def bit_generator():
        for d in data:
            yield from "{:08b}".format(d)

    q = bytearray()
    c = ""
    for b in bit_generator():
        c += b
        m = huffman_dict.get(c)
        if m is not None:
            q.append(m)
            c = ""
        if len(q) >= uncompressed_length:
            return q
    return q


def _huffman_decode_bitarray(file, uncompressed_length):
    """
    Bitarray decoding of huffman table found in the vector table section.

    @param file:
    @param uncompressed_length:
    @return:
    """
    from bitarray import bitarray

    huffman_dict = {}
    table_length = struct.unpack("<H", file.read(2))[0]
    for i in range(table_length):
        character, bb, length = struct.unpack("<BIH", file.read(7))
        bits = bitarray("{:032b}".format(bb)[-length:])
        huffman_dict[character] = bits
    a = bitarray()
    a.frombytes(file.read())
    while True:
        try:
            return bytearray(a.decode(huffman_dict))
        except ValueError:
            a = a[:-1]


class Pen:
    def __init__(self, file):
        """
        Parse pen with the given file.
        """
        args = _parse_struct(file)
        _interpret(args, 1, str)
        _construct(args)

        self.color = Color(bgr=args[0])
        self.label = args[1]
        self.mark_enable = args[2]
        self.passes = args[4]  # Loop Count
        if self.passes >= 1:
            self.passes_custom = True
        self.speed = args[5]
        self.power = args[6] * 10.0
        self.frequency = args[7] / 1000.0
        self.start_tc = args[9]
        self.end_tc = args[10]
        self.polygon_tc = args[11]
        self.jump_speed = args[12]
        self.jump_min_delay = args[13]
        self.jump_max_delay = args[14]
        self.opt_start_length = args[16]
        self.opt_end_length = args[15]
        self.time_per_point = args[17]
        self.pulse_per_point = args[21]
        self.laser_off_tc = args[23]
        self.wobble_enable = args[26]
        self.wobble_diameter = args[27]
        self.wobble_distance = args[28]

        self.add_endpoints = args[29]
        self.add_endpoint_distance = args[30]
        self.add_endpoint_time_per_point = args[32]
        self.add_endpoint_point_distance = args[31]
        self.add_endpoints_point_cycles = args[33]
        self.opt_enable = args[40] # Apparently crashy for older versions of ezcad.
        self.break_angle = args[41]

        self.jump_min_jump_delay2 = args[37]
        self.jump_max_delay2 = args[38]
        self.jump_speed_max_limit = args[39]


class EZCFile:
    """
    Parse the EZCFile given file as a stream.
    """

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
        """
        Parse file header.

        @param file:
        @return:
        """
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
        """
        The second item in the file after the header is the seek table lookup. This provides the location in absolute
        position in the file of the table locations.
        @param file:
        @return:
        """
        self._locations["preview"] = struct.unpack("<I", file.read(4))[0]
        self._locations["v1"] = struct.unpack("<I", file.read(4))[0]
        self._locations["pens"] = struct.unpack("<I", file.read(4))[0]
        self._locations["font"] = struct.unpack("<I", file.read(4))[0]
        self._locations["v4"] = struct.unpack("<I", file.read(4))[0]
        self._locations["vectors"] = struct.unpack("<I", file.read(4))[0]
        self._locations["prevectors"] = struct.unpack("<I", file.read(4))[0]

    def parse_unknown_nontable(self, file):
        """
        This is a non-table section. It could be padding for future seek tables entries or have some unknown meaning.

        @param file:
        @return:
        """
        unknown_table = struct.unpack("<24I", file.read(96))

    def parse_tables(self, file):
        """
        Parses all the different tables found in the file.

        @param file:
        @return:
        """
        self.parse_preview(file)
        self.parse_v1(file)
        self.parse_pens(file)
        self.parse_font(file)
        self.parse_v4(file)
        self.parse_vectors(file)
        self.parse_prevectors(file)

    def parse_v1(self, file):
        """
        Unknown table location. Usually absent.

        @param file:
        @return:
        """
        seek = self._locations.get("v1", 0)
        if seek == 0:
            return
        file.seek(seek, 0)

    def parse_v4(self, file):
        """
        Unknown table location usually contains 96 bytes.

        @param file:
        @return:
        """
        seek = self._locations.get("v4", 0)
        if seek == 0:
            return
        file.seek(seek, 0)
        unknown_table = struct.unpack("<24I", file.read(96))

    def parse_preview(self, file):
        """
        Contains a preview image of the file.

        @param file:
        @return:
        """
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
        """
        Font table. This usually consists of "Arial" with no other data and only exists if a font is used.

        @param file:
        @return:
        """
        seek = self._locations.get("font", 0)
        if seek == 0:
            return
        file.seek(seek, 0)
        font_count = struct.unpack("<I", file.read(4))[0]

        for i in range(font_count):
            f = file.read(100)
            self.fonts.append(f.decode("utf_16").strip("\x00"))

    def parse_pens(self, file):
        """
        Contains all the pens used at the time of the saving of the file. This is 256 pens.

        @param file:
        @return:
        """
        seek = self._locations.get("pens", 0)
        if seek == 0:
            return
        file.seek(seek, 0)

        parameter_count = struct.unpack("<I", file.read(4))[0]
        seek = struct.unpack("<I", file.read(4))[0]
        file.seek(seek, 0)
        for c in range(parameter_count):
            self.pens.append(Pen(file))

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
        """
        Vectors contain the bulk of the files. This is a compressed file of huffman encoded data. The first section
        contains the huffman table, followed by the compressed data.

        @param file:
        @return:
        """
        seek = self._locations.get("vectors", 0)
        if seek == 0:
            return
        file.seek(seek, 0)
        uncompressed_length, unknown2, unknown3, data_start, unknown5 = struct.unpack(
            "<IIIII", file.read(20)
        )
        try:
            q = _huffman_decode_bitarray(file, uncompressed_length)
        except ImportError:
            q = _huffman_decode_python(file, uncompressed_length)
        data = BytesIO(q)
        while parse_object(data, self.objects):
            pass


class EZObject:
    """
    Every object contains the same 15 pieces of data.
    If this object type contains children, the count of children and the children are given exactly following the
    header. Any information specific to the class of object is read after the header and children.
    """

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

        self.label = header[3]
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
    """
    This is a series of related contours.
    """

    def __init__(self, file):
        list.__init__(self)
        EZObject.__init__(self, file)


class EZGroup(list, EZObject):
    """
    Grouped data appears both when objects are grouped but also in groups within vector file objects like svgs.
    """

    def __init__(self, file):
        list.__init__(self)
        EZObject.__init__(self, file)


class EZVectorFile(list, EZObject):
    """
    Vector file object.
    """

    def __init__(self, file):
        list.__init__(self)
        EZObject.__init__(self, file)
        data1 = _parse_struct(file)
        _interpret(data1, 0, str)
        _construct(data1)

        self.path = data1[0]
        self.args = data1


class EZCurve(EZObject):
    """
    Curves are some number of curve-type (usually 1 or 3) contours.
    """

    def __init__(self, file):
        super().__init__(file)
        pts = []
        (count, closed) = struct.unpack("<2I", file.read(8))
        for i in range(count):
            (unk1, curve_type, unk2, unk3) = struct.unpack("<BB2H", file.read(6))
            # Unk1 is 2 for a weird node. with t equal 0.
            if curve_type == 0:
                d = struct.unpack(f"<5d", file.read(40))
                # print(d)
                continue
            (pt_count,) = struct.unpack("<I", file.read(4))
            # print(unk1, curve_type, unk2, unk2, pt_count)
            pts.append(
                (
                    curve_type,
                    closed,
                    struct.unpack(f"<{pt_count * 2}d", file.read(16 * pt_count)),
                )
            )

        self.points = pts


class EZRect(EZObject):
    """
    Rectangles have optional each corner curved edges.
    """

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
    """
    Circles are center followed by their radius. The angles are given in radians.
    """

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
    """
    Ellipses are a rectangle like structures, the start and end angles create a pie-slice like geometric shape when
    these are set.
    """

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
    """
    Spirals are a modification group of the items contained by the spiral. These also contain a cached-group of the
    output produced by the spiral.
    """

    def __init__(self, file):
        list.__init__(self)
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _construct(args)
        self.spiral_pen = args[0]
        self.spiral_type = args[1]
        self.min_radius = args[5]
        self.min_spiral_pitch = args[2]
        self.max_spiral_pitch = args[3]
        self.max_spiral_increment = args[4]
        self.outer_edge_loops = args[6]
        self.inner_edge_loops = args[7]
        self.spiral_out = args[8]
        self.group = EZGroup(file)


class EZPolygon(EZObject):
    """
    Polygons are either regular or star-like. No control is given over the minor or major phase.
    """

    def __init__(self, file):
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _construct(args)
        self.polygon_type = args[0]
        self.corner_upper_left = args[1]
        self.corner_bottom_right = args[2]
        self.sides = args[7]
        self.matrix = args[9]


class EZTimer(EZObject):
    """
    Timers are wait commands. These are given a time and simply send the wait command to the laser.
    """

    def __init__(self, file):
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _construct(args)
        self.wait_time = args[1]


class EZInput(EZObject):
    """
    Input commands wait on the IO of the laser to trigger to the next item within the operations list.
    """

    def __init__(self, file):
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _interpret(args, 1, str)
        _construct(args)
        self.message_enabled = bool(args[0])
        self.message = args[1]


class EZOutput(EZObject):
    """
    Output list sends IO out to the laser, this is used to trigger things like rotary, GPIO, or light.
    """

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


class EZEncoderDistance(EZObject):
    """
    This is for testing on-the-fly movement.
    """

    def __init__(self, file):
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _construct(args)
        self.distance = args[0]


class EZExtendAxis(EZObject):
    """
    This is for testing on-the-fly movement.
    """

    def __init__(self, file):
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _construct(args)
        self.axis_go_zero = bool(args[0])
        self.only_once_origin = bool(args[1])
        self.relative = bool(args[2])
        self.unit_type = args[3]  # Pulse (0), MM (1), Degree(2).
        self.pulse_per_mm = args[4]
        self.move_pulse = args[5]
        self.max_speed = args[6]
        self.min_speed = args[7]
        self.acceleration_time = args[8]


class EZText(EZObject):
    """
    Text objects.
    """

    def __init__(self, file):
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _interpret(args, 10, str)
        _interpret(args, 18, str)
        _interpret(args, 44, str)
        _interpret(args, 54, str)
        _construct(args)
        self.font_angle = args[0]  # Font angle in Text.
        self.height = args[1]  # Height in MM
        self.text_space_setting = args[5]  # 0 auto, 1 between, 2 center
        self.text_space = args[12]
        self.char_space = args[13]
        self.line_space = args[14]
        self.font = args[18]  # Arial, JSF Font, etc
        self.font2 = args[44]
        self.x, self.y = args[7]
        self.text = args[10]
        self.hatch_loop_distance = args[21]
        self.circle_text_enable = args[48]
        self.circle_text_diameter = args[49]
        self.circle_text_base_angle = args[50]
        self.circle_text_range_limit_enable = args[51]
        self.circle_text_range_limit_angle = args[52]
        self.save_options = args[53]  # 3 boolean values
        self.save_filename = args[54]
        self.circle_text_button_flags = args[85]  # 2 is first button, 1 is right to left.
        # extradata = _parse_struct(file)
        # print(extradata)


class EZImage(EZObject):
    """
    Image objects consist of a lot of properties to control the encoding of the image and a 24-bit bitmap.
    """

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
    """
    Hatch is a modification group. All three hatch elements are given properties for each hatch. The hatch contains
    the actual elements that were to be given a hatch. As well as a cache-group of curve items that actually are the
    given hatch properly rendered.
    """

    def __init__(self, file):
        list.__init__(self)
        EZObject.__init__(self, file)
        args = _parse_struct(file)
        _construct(args)
        self.mark_contours = args[0]
        self.mark_contours_type = args[41]

        self.hatch1_enabled = args[1]
        self.hatch1_type = args[3]
        # Includes average distribute line, allcalc, follow edge, crosshatch
        # spiral = 0x50
        self.hatch1_type_all_calc = self.hatch1_type & 0x1
        self.hatch1_type_follow_edge = self.hatch1_type & 0x2
        self.hatch1_type_crosshatch = self.hatch1_type & 0x400
        self.hatch1_angle = args[8]
        self.hatch1_pen = args[2]
        self.hatch1_count = args[42]
        self.hatch1_line_space = args[5]
        self.hatch1_edge_offset = args[4]
        self.hatch1_start_offset = args[6]
        self.hatch1_end_offset = args[7]
        self.hatch1_line_reduction = args[29]
        self.hatch1_number_of_loops = args[32]
        self.hatch1_loop_distance = args[35]
        self.hatch1_angle_inc = args[18]

        self.hatch2_enabled = args[9]
        self.hatch2_type = args[11]
        self.hatch2_angle = args[16]
        self.hatch2_pen = args[10]
        self.hatch2_count = args[43]
        self.hatch2_line_space = args[13]
        self.hatch2_edge_offset = args[12]
        self.hatch2_start_offset = args[14]
        self.hatch2_end_offset = args[15]
        self.hatch2_line_reduction = args[30]
        self.hatch2_number_of_loops = args[33]
        self.hatch2_loop_distance = args[36]
        self.hatch2_angle_inc = args[19]

        self.hatch3_enabled = args[20]
        self.hatch3_type = args[22]
        self.hatch3_angle = args[27]
        self.hatch3_pen = args[21]
        self.hatch3_count = args[44]
        self.hatch3_line_space = args[24]
        self.hatch3_edge_offset = args[23]
        self.hatch3_start_offset = args[25]
        self.hatch3_end_offset = args[26]
        self.hatch3_line_reduction = args[31]
        self.hatch3_number_of_loops = args[34]
        self.hatch3_loop_distance = args[37]
        self.hatch3_angle_inc = args[28]
        tell = file.tell()
        (check,) = struct.unpack("<I", file.read(4))
        file.seek(tell, 0)
        if check == 15:
            self.group = EZGroup(file)
        else:
            self.group = None


object_map = {
    1: EZCurve,
    3: EZRect,
    4: EZCircle,
    5: EZEllipse,
    6: EZPolygon,
    0x30: EZCombine,
    0x40: EZImage,
    0x60: EZSpiral,
    0x6000: EZEncoderDistance,
    0x5000: EZExtendAxis,
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
        except (IOError, IndexError) as e:
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
        self.cx = self.width / 2.0
        self.cy = self.height / 2.0
        self.matrix = Matrix.scale(UNITS_PER_MM, -UNITS_PER_MM)
        self.matrix.post_translate(self.cx, self.cy)

    def process(self, ez, pathname):
        self.op_branch.remove_all_children()
        self.elem_branch.remove_all_children()
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
            if len(points) == 0:
                return
            path = Path(stroke="black", transform=self.matrix)
            last_end = None
            for t, closed, contour in points:
                cpt = [
                    complex(contour[i], contour[i + 1])
                    for i in range(0, len(contour), 2)
                ]
                if last_end != cpt[0]:
                    path.move(cpt[0])
                if t == 1:
                    path.line(*cpt[1:])
                elif t == 2:
                    path.quad(*cpt[1:])
                elif t == 3:
                    path.cubic(*cpt[1:])
                last_end = cpt[-1]
            if points[-1][1]:
                # Path is closed.
                path.closed()
            node = elem.add(
                type="elem path",
                path=path,
                stroke_width=self.elements.default_strokewidth,
            )
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
            node = elem.add(
                type="elem polyline",
                shape=polyline,
                stroke_width=self.elements.default_strokewidth,
            )
            p = ez.pens[element.pen]
            op_add = op.add(type="op engrave", **p.__dict__)
            op_add.add_reference(node)
        elif isinstance(element, EZCircle):
            m = element.matrix
            mx = Matrix(m[0], m[1], m[3], m[4], m[6], m[7])
            mx *= self.matrix
            node = elem.add(
                cx=element.center[0],
                cy=element.center[1],
                rx=element.radius,
                ry=element.radius,
                stroke=Color("black"),
                matrix=mx,
                stroke_width=self.elements.default_strokewidth,
                type="elem ellipse",
            )
            p = ez.pens[element.pen]
            op_add = op.add(type="op engrave", **p.__dict__)
            op_add.add_reference(node)
        elif isinstance(element, EZEllipse):
            m = element.matrix
            mx = Matrix(m[0], m[1], m[3], m[4], m[6], m[7])
            mx *= self.matrix
            x0, y0 = element.corner_upper_left
            x1, y1 = element.corner_bottom_right
            node = elem.add(
                cx=(x0 + x1) / 2.0,
                cy=(y0 + y1) / 2.0,
                rx=(x1 - x0) / 2.0,
                ry=(y1 - y0) / 2.0,
                matrix=mx,
                stroke=Color("black"),
                stroke_width=self.elements.default_strokewidth,
                type="elem ellipse",
            )
            p = ez.pens[element.pen]
            op_add = op.add(type="op engrave", **p.__dict__)
            op_add.add_reference(node)
        elif isinstance(element, EZRect):
            m = element.matrix
            mx = Matrix(m[0], m[1], m[3], m[4], m[6], m[7])
            mx *= self.matrix
            x0, y0 = element.corner_upper_left
            x1, y1 = element.corner_bottom_right
            node = elem.add(
                x=x0,
                y=y0,
                width=x1 - x0,
                height=y1 - y0,
                matrix=mx,
                stroke=Color("black"),
                stroke_width=self.elements.default_strokewidth,
                type="elem rect",
            )
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
            elem = elem.add(type="group", label=element.label)
            for child in element:
                # (self, ez, element, elem, op)
                self.parse(ez, child, elem, op)
        elif isinstance(element, EZHatch):
            elem = elem.add(type="group", label=element.label)
            for child in element:
                self.parse(ez, child, elem, op)

            p = ez.pens[element.pen]
            op_add = op.add(type="op hatch", **p.__dict__)
            for e in elem.flat():
                op_add.add_reference(e)

            if element.group:
                for child in element.group:
                    self.parse(ez, child, elem, op)
        elif isinstance(element, (EZGroup, EZCombine)):
            elem = elem.add(type="group", label=element.label)
            # recurse to children
            for child in element:
                self.parse(ez, child, elem, op)
        elif isinstance(element, EZSpiral):
            elem = elem.add(type="group", label=element.label)
            # recurse to children
            for child in element:
                self.parse(ez, child, elem, op)
            for child in element.group:
                self.parse(ez, child, elem, op)
