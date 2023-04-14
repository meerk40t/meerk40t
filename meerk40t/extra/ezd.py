"""
Parser for .ezd files.
"""
import struct
from io import BytesIO

from bitarray import bitarray

from meerk40t.core.exceptions import BadFileError
from meerk40t.svgelements import Color, Rect, Matrix


def plugin(kernel, lifecycle):
    if lifecycle == "boot":
        context = kernel.root
    elif lifecycle == "register":
        kernel.register("load/EZDLoader", EZDLoader)
        pass
    elif lifecycle == "shutdown":
        pass


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
        self.color = Color(rgb=color)
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
        self._preview_bitmap = list()
        self._prevector = None
        self.parse_header(file)
        self.parse_seektable(file)
        self.parse_unknown_nontable(file)
        self.parse_tables(file)

    def _parse_struct(self, file):
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

    def _interpret(self, data, index, type):
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

    def _construct(self, data):
        for i in range(len(data)):
            b = data[i]
            length = len(b)
            if not isinstance(b, (bytes, bytearray)):
                continue
            if length == 2:
                self._interpret(data, i, "short")
            elif length == 4:
                self._interpret(data, i, int)
            elif length == 8:
                self._interpret(data, i, float)
            elif length == 16:
                self._interpret(data, i, "point")
            elif length == 60:
                self._interpret(data, i, str)
            elif length == 72:
                self._interpret(data, i, "matrix")
            elif length == 0:
                data[i] = None
        return data

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
        print(file.tell())
        unknown = struct.unpack("<I", file.read(4))[0]
        print(file.tell())

    def parse_pens(self, file):
        seek = self._locations.get("pens", 0)
        if seek == 0:
            return
        file.seek(seek, 0)

        parameter_count = struct.unpack("<I", file.read(4))[0]
        seek = struct.unpack("<I", file.read(4))[0]
        file.seek(seek, 0)
        for c in range(parameter_count):
            p = self._parse_struct(file)
            self._interpret(p, 1, str)
            self._construct(p)
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
                self.parse_objects(BytesIO(q))
                return
            except ValueError:
                a = a[:-1]

    def parse_objects(self, file):
        while self.parse_object(file, self.objects):
            pass

    def parse_object(self, file, objects):
        object_type = struct.unpack("<I", file.read(4))[0]  # 0
        if object_type == 0:
            return False
        header = self._parse_struct(file)
        self._interpret(header, 3, str)
        self._construct(header)

        if object_type == 1:
            # curve
            secondary = self._parse_struct(file)
            self._construct(secondary)
            objects.append(EZCurve(*header, *secondary))
            return True
        elif object_type == 3:
            # rect
            secondary = self._parse_struct(file)
            self._construct(secondary)
            objects.append(EZRect(*header, *secondary))
            return True
        elif object_type == 4:
            # circle
            secondary = self._parse_struct(file)
            self._construct(secondary)
            objects.append(EZCircle(*header, *secondary))
            return True
        elif object_type == 5:
            # ellipse
            secondary = self._parse_struct(file)
            self._construct(secondary)
            objects.append(EZEllipse(*header, *secondary))
            return True
        elif object_type == 6:
            # polygon
            secondary = self._parse_struct(file)
            self._construct(secondary)
            objects.append(EZPolygon(*header, *secondary))
            return True
        elif object_type == 0x40:
            # bitmap
            secondary = self._parse_struct(file)
            self._construct(secondary)
            objects.append(EZImage(*header, *secondary))
            return True
        elif object_type == 0x3000:
            # input
            secondary = self._parse_struct(file)
            self._interpret(secondary, 1, str)
            self._construct(secondary)
            objects.append(EZInput(*header, *secondary))
            return True
        elif object_type == 0x2000:
            # timer
            secondary = self._parse_struct(file)
            self._construct(secondary)
            objects.append(EZTimer(*header, *secondary))
            return True
        elif object_type == 0x800:
            # text
            secondary = self._parse_struct(file)
            self._construct(secondary)
            objects.append(EZText(*header, *secondary))
            return True
        elif object_type == 0x10:
            (count,) = struct.unpack("<I", file.read(4))
            group = EZGroup(*header)
            objects.append(group)
            for c in range(count):
                self.parse_object(file, group)
            return True
        elif object_type == 0x50:
            # Vector File
            (count,) = struct.unpack("<I", file.read(4))
            group = EZVFile(*header)
            objects.append(group)
            for c in range(count):
                self.parse_object(file, group)
            data1 = self._parse_struct(file)
            self._interpret(data1, 0, str)
            self._construct(data1)
            group.secondary(*data1)
            print(data1)
            return True
        elif object_type == 0x20:
            # hatch-rect / hatch-curve
            secondary = self._parse_struct(file)
            self._construct(secondary)
            objects.append(EZHatch(*header, *secondary))
            return True
        elif object_type == 0x400:
            # hatch-curve
            secondary = self._parse_struct(file)
            self._construct(secondary)
            objects.append(EZHatch(*header, *secondary))
            return True
        # print(object_type)
        # d = file.read()
        # print(d)
        return False


class EZObject:
    def __init__(
        self,
        pen,
        type,
        state,
        v1,
        v2,
        v3,
        v4,
        input_bits,
        array_state,
        array_count_x,
        array_count_y,
        array_step_x,
        array_step_y,
        position,
        z_pos,
        *args,
    ):
        self.pen = pen
        self.type = type
        self.state = state

        # Selected 0x02, Hidden 0x01, Locked 0x10
        self.selected = bool(self.state & 0x02)
        self.hidden = bool(self.state & 0x01)
        self.locked = bool(self.state & 0x10)

        self.unknown1 = v1
        self.unknown2 = v2
        self.unknown3 = v3
        self.unknown4 = v4
        self.input_port_bits = input_bits
        self.array_state = array_state
        self.array_bidirectional = bool(array_state & 0x2)
        self.array_vertical = bool(array_state & 0x1)
        self.array_count_x = array_count_x
        self.array_count_y = array_count_y
        self.array_step_x = array_step_x
        self.array_step_y = array_step_y
        self.position = position
        self.z_pos = z_pos


class EZGroup(list):
    def __init__(
        self,
        pen,
        type,
        state,
        v1,
        v2,
        v3,
        v4,
        input_bits,
        array_state,
        array_count_x,
        array_count_y,
        array_step_x,
        array_step_y,
        position,
        z_pos=None,
        *args,
    ):
        super().__init__()
        self.pen = pen
        self.type = type
        self.state = state

        # Selected 0x02, Hidden 0x01, Locked 0x10
        self.selected = bool(self.state & 0x02)
        self.hidden = bool(self.state & 0x01)
        self.locked = bool(self.state & 0x10)

        self.unknown1 = v1
        self.unknown2 = v2
        self.unknown3 = v3
        self.unknown4 = v4
        self.input_port_bits = input_bits
        self.array_state = array_state
        self.array_bidirectional = bool(array_state & 0x2)
        self.array_vertical = bool(array_state & 0x1)
        self.array_count_x = array_count_x
        self.array_count_y = array_count_y
        self.array_step_x = array_step_x
        self.array_step_y = array_step_y
        self.position = position
        self.z_pos = z_pos
        print(args)
        print(self.__dict__)


class EZVFile(list):
    def __init__(
        self,
        pen,
        type,
        state,
        v1,
        v2,
        v3,
        v4,
        input_bits,
        array_state,
        array_count_x,
        array_count_y,
        array_step_x,
        array_step_y,
        position,
        z_pos=None,
        *args,
    ):
        super().__init__()
        self.pen = pen
        self.type = type
        self.state = state

        # Selected 0x02, Hidden 0x01, Locked 0x10
        self.selected = bool(self.state & 0x02)
        self.hidden = bool(self.state & 0x01)
        self.locked = bool(self.state & 0x10)

        self.unknown1 = v1
        self.unknown2 = v2
        self.unknown3 = v3
        self.unknown4 = v4
        self.input_port_bits = input_bits
        self.array_state = array_state
        self.array_bidirectional = bool(array_state & 0x2)
        self.array_vertical = bool(array_state & 0x1)
        self.array_count_x = array_count_x
        self.array_count_y = array_count_y
        self.array_step_x = array_step_x
        self.array_step_y = array_step_y
        self.position = position
        self.z_pos = z_pos
        self.path = None
        self.args = None
        print(args)
        print(self.__dict__)

    def secondary(
        self,
        path,
        unknown,
        unknown2,
        unknown_f,
        unknown_f2,
        unknown3,
        unknown_f3,
        unknown_f4,
    ):
        self.path = path
        self.args = (
            unknown,
            unknown2,
            unknown_f,
            unknown_f2,
            unknown3,
            unknown_f3,
            unknown_f4,
        )


class EZCurve(EZObject):
    def __init__(self, *args):
        super().__init__(*args)
        print(args)
        print(self.__dict__)


class EZRect(EZObject):
    def __init__(self, *args):
        super().__init__(*args)
        self.min_pos = args[15]
        self.max_pos = args[16]
        self.corner_upper_left = args[15]
        self.corner_bottom_right = args[16]
        self.round_c1 = args[17]
        self.round_c2 = args[18]
        self.round_c3 = args[19]
        self.round_c4 = args[20]
        self.unknown5 = args[21]
        self.matrix = args[22]


class EZCircle(EZObject):
    def __init__(self, *args):
        super().__init__(*args)
        print(args)
        print(self.__dict__)


class EZEllipse(EZObject):
    def __init__(self, *args):
        super().__init__(*args)
        print(args)
        print(self.__dict__)


class EZPolygon(EZObject):
    def __init__(self, *args):
        super().__init__(*args)
        print(args)
        print(self.__dict__)


class EZTimer(EZObject):
    def __init__(self, *args):
        super().__init__(*args)
        print(args)
        print(self.__dict__)


class EZInput(EZObject):
    def __init__(self, *args):
        super().__init__(*args)
        self.message_enabled = bool(args[15])
        self.message = args[16]


class EZText(EZObject):
    def __init__(self, *args):
        super().__init__(*args)
        self.font_angle = args[15]  # Font angle in Text.
        print(args)
        print(self.__dict__)


class EZImage(EZObject):
    def __init__(self, *args):
        super().__init__(*args)
        print(args)
        print(self.__dict__)


class EZHatch(EZObject):
    def __init__(self, *args):
        super().__init__(*args)
        print(args)
        print(self.__dict__)


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

        op_branch = elements_service.op_branch
        op_branch.remove_all_children()
        for p in ezfile.pens:
            op_branch.add(type="op engrave", **p.__dict__)
        context_node = elements_service.elem_branch
        context_node.remove_all_children()
        ez_processor = EZProcessor(elements_service)
        ez_processor.process(ezfile, pathname)
        return True


class EZProcessor:
    def __init__(self, elements):
        self.elements = elements
        self.element_list = list()
        self.regmark_list = list()
        self.pathname = None
        self.regmark = None

    def process(self, ez, pathname):
        self.pathname = pathname
        context_node = self.elements.get(type="branch elems")
        file_node = context_node.add(type="file", filepath=pathname)
        self.regmark = self.elements.reg_branch
        file_node.focus()
        for f in ez.objects:
            self.parse(f, file_node, self.element_list)

    def parse(self, element, context_node, e_list):
        node = None
        if isinstance(element, EZText):
            node = context_node.add(type="elem text")
            e_list.append(node)
        elif isinstance(element, EZCurve):
            node = context_node.add(type="elem path")
            e_list.append(node)
        elif isinstance(element, EZPolygon):
            node = context_node.add(
                type="elem polyline",
            )
            e_list.append(node)
        elif isinstance(element, (EZCircle, EZEllipse)):
            node = context_node.add(
                type="elem ellipse",
            )
            e_list.append(node)
        elif isinstance(element, EZRect):
            e = element.pen
            m = element.matrix
            mx = Matrix(m[0], m[1], m[3], m[4], m[6], m[7])
            mx.post_scale_y(-1)
            x0, y0 = element.corner_upper_left
            x1, y1 = element.corner_bottom_right
            rect = Rect(x0, y0, x1 - x0, y1 - y0, transform=mx, stroke="black")
            node = context_node.add(type="elem rect", shape=rect)
            e_list.append(node)
        elif isinstance(element, EZTimer):
            node = context_node.add(type="util wait")
            e_list.append(node)
        elif isinstance(element, EZImage):
            node = context_node.add(type="elem image")
            e_list.append(node)
        elif isinstance(element, EZVFile):
            for child in element:
                self.parse(child, context_node, e_list)
        elif isinstance(element, EZGroup):
            context_node = context_node.add(type="group")
            # recurse to children
            for child in element:
                self.parse(child, context_node, e_list)
        else:
            return
        if node is None:
            return
        try:
            op_add = self.elements.op_branch.children[element.pen]
            op_add.add_reference(node)
        except IndexError:
            pass
