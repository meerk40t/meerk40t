"""
Parser for .ezd files.
"""
import struct
from io import BytesIO

import PIL.Image
from bitarray import bitarray


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
    def __init__(self, file):
        """
        Parse pen with given file.

        159 * 4, 636,0x027C bytes total

        @param file:
        """
        self.unknown0 = struct.unpack("<I", file.read(4))[0]  # 61
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.color = struct.unpack("<I", file.read(4))[0]
        label_length = struct.unpack("<I", file.read(4))[0]
        label = file.read(label_length)
        self.label = label.decode("utf_16")

        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown4 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00, 0
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown6 = struct.unpack("<I", file.read(4))[0]  # 01 00 00 00, 1
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown8 = struct.unpack("<I", file.read(4))[0]  # 01 00 00 00, 1
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown10 = struct.unpack("d", file.read(8))[0]  # 500.0
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown13 = struct.unpack("d", file.read(8))[0]  # 50.0, 0
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown16 = struct.unpack("<I", file.read(4))[0]  # 20 4E 00 00, 20000
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown18 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00, 4
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown20 = struct.unpack("<I", file.read(4))[0]  # 2C 01 00 00, 300

        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown22 = struct.unpack("<I", file.read(4))[0]  # 2C 01 00 00, 300
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown24 = struct.unpack("<I", file.read(4))[0]  # 64 00 00 00, 100
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown26 = struct.unpack("d", file.read(8))[0]  # 4000.0

        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown29 = struct.unpack("<I", file.read(4))[0]  # F4 01 00 00, 500

        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown31 = struct.unpack("<I", file.read(4))[0]  # 64 00 00 00

        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown33 = struct.unpack("d", file.read(8))[0]  # 0.0
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown36 = struct.unpack("d", file.read(8))[0]  # 0.0
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown39 = struct.unpack("d", file.read(8))[0]  # 0.1
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown42 = struct.unpack("<2I", file.read(8))
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown45 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown48 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown50 = struct.unpack("<I", file.read(4))[0]  # 01 00 00 00
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown52 = struct.unpack("<I", file.read(4))[0]  # 30 00 00 00
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown54 = struct.unpack("<I", file.read(4))[0]  # 96 00 00 00
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown56 = struct.unpack("<I", file.read(4))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown58 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown61 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown63 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown66 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown69 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown71 = struct.unpack("<I", file.read(4))[0]  # 01 00 00 00
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown73 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown76 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown79 = struct.unpack("<I", file.read(4))[0]  # 01 00 00 00
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown81 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown84 = struct.unpack("<I", file.read(4))[0]  # 64 00 00 00
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown86 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown89 = struct.unpack("<I", file.read(4))[0]  # 96 00 00 00
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown91 = struct.unpack("<I", file.read(4))[0]  # FA 00 00 00
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown93 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown96 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown98 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown101 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown103 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown106 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown109 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown112 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown115 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown118 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown121 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown124 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown127 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown130 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown133 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown136 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown139 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown142 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown145 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.unknown148 = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown152 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown154 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00


class EZObject:
    def __init__(self):
        """
        Parse uncompressed object.
        # 01-02 : Item type. 0001 Curve. 0003 Rect, 0004 Circle, 0005 Ellipse, 0006 Polygon, 3000 Input, 2000 Timer, 4000 Output, 8000 Text.
        # 0c-0d : Pen Used.
        # 1a-1b : Selected 0x02, Hidden 0x01, Locked 0x10
        # 1C-1D : Length of title. - Extends Title. 02 00 is min, 1E 1F are 00 in that case.
        # 40-21 : 02 00 if right array, 03 00 if up array 0x01 - Up, 0x02 - Bidirectional
        # 46-47 : X-array
        # 4E-4F : Y-array
        # 6E- of header for shape.

        # Polygon
        # F2-F3 : Number of sides.
        # 92-93 : Star Shaped bool. (also changed 6E from 0D to 0C)

        # Image
        # 8E-8F : Original Path

        # Units 24 40 = 10mm, 34 40 = 20mm, 3E 40 = 30mm (maybe 08 00 after)
        """
        pass

    def _parse_pen(self, file):
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.pen = struct.unpack("<I", file.read(4))[0]

    def _parse_type(self, file):
        data_len = struct.unpack("<I", file.read(4))[0]  # 2
        assert (data_len == 2)
        object_type = struct.unpack("<H", file.read(2))[0]
        self.type = None
        if object_type == 1:
            self.type = "curve"
        elif object_type == 3:
            self.type = "rect"
        elif object_type == 4:
            self.type = "circle"
        elif object_type == 5:
            self.type = "ellipse"
        elif object_type == 6:
            self.type = "polygon"
        elif object_type == 0x3000:
            self.type = "input"
        elif object_type == 0x2000:
            self.type = "timer"
        elif object_type == 0x800:
            self.type = "text"

    def _parse_state(self, file):
        data_len = struct.unpack("<I", file.read(4))[0]  # 2
        assert (data_len == 2)
        self.state = struct.unpack("<H", file.read(2))[0]
        # Selected 0x02, Hidden 0x01, Locked 0x10
        self.selected = bool(self.state & 0x02)
        self.hidden = bool(self.state & 0x01)
        self.locked = bool(self.state & 0x10)

    def _parse_array(self, file):
        array_state = struct.unpack("<H", file.read(2))[0]
        self.array_bidirectional = bool(array_state & 0x2)
        self.array_vertical = bool(array_state & 0x1)

        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.array_count_x = struct.unpack("<I", file.read(4))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.array_count_y = struct.unpack("<I", file.read(4))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.array_step_x = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.array_step_y = struct.unpack("d", file.read(8))[0]

    def _parse_position(self, file):
        data_len = struct.unpack("<I", file.read(4))[0]  # 16
        assert (data_len == 16)
        self.x_pos = struct.unpack("d", file.read(8))[0]
        self.y_pos = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.z_pos = struct.unpack("d", file.read(8))[0]

    def _parse_input_port(self, file):
        self.input_port_bits = struct.unpack("<H", file.read(2))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 2
        assert (data_len == 2)

    def parse(self, data):
        file = BytesIO(data)
        obj_type = struct.unpack("<I", file.read(4))[0]  # 0
        self.unknown1 = struct.unpack("<I", file.read(4))[0]  # 15
        self._parse_pen(file)
        self._parse_type(file)
        self._parse_state(file)

        data_len = struct.unpack("<I", file.read(4))[0]  # 2
        assert (data_len == 2)
        self.unknown14 = struct.unpack("<H", file.read(2))[0]  # 0
        data_len = struct.unpack("<I", file.read(4))[0]  # 2
        assert (data_len == 4)
        self.unknown17 = struct.unpack("<I", file.read(4))[0]  # 1
        data_len = struct.unpack("<I", file.read(4))[0]  # 2
        assert (data_len == 2)
        self.unknown21 = struct.unpack("<H", file.read(2))[0]  # 0
        data_len = struct.unpack("<I", file.read(4))[0]  # 2
        assert (data_len == 2)
        self.unknown24 = struct.unpack("<H", file.read(2))[0]  # 0
        data_len = struct.unpack("<I", file.read(4))[0]  # 2
        assert (data_len == 2)

        self._parse_input_port(file)

        self._parse_array(file)
        self._parse_position(file)

        end_structure = struct.unpack("<I", file.read(4))[0]  # 8
        if self.type == "rect":
            self.parse_rect(file)
        elif self.type == "text":
            self.parse_text(file)
        elif self.type == "polygon":
            self.parse_polygon(file)

        data = file.read()
        print(data)
        return data

    def _general_parse(self, file):
        while file:
            length = struct.unpack("<I", file.read(4))[0]
            if length == 2:
                yield struct.unpack("<I", file.read(2))[0]
            elif length == 4:
                yield struct.unpack("<I", file.read(4))[0]
            elif length == 8:
                yield struct.unpack("d", file.read(8))[0]
            else:
                yield file.read(length)


    def parse_polygon(self, file):
        parsed = list(self._general_parse(file))
        print(parsed)
        print(parsed)

    def parse_text(self, file):
        self.font_angle = struct.unpack("d", file.read(8))  # Font angle in Text.

    def parse_rect(self, file):
        data_len = struct.unpack("<I", file.read(4))[0]  # 16
        assert (data_len == 16)
        self.min_x = struct.unpack("d", file.read(8))[0]
        self.max_x = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 16
        assert (data_len == 16)
        self.max_y = struct.unpack("d", file.read(8))[0]
        self.min_y = struct.unpack("d", file.read(8))[0]

        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.corner_bottom_left = struct.unpack("d", file.read(8))
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.corner_bottom_right = struct.unpack("d", file.read(8))
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.corner_upper_right = struct.unpack("d", file.read(8))
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        assert (data_len == 8)
        self.corner_upper_left = struct.unpack("d", file.read(8))
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        assert (data_len == 4)
        self.unknown106 = struct.unpack("<I", file.read(4))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 72
        assert (data_len == 72)
        self.matrix_0 = struct.unpack("d", file.read(8))
        self.matrix_1 = struct.unpack("d", file.read(8))
        self.matrix_2 = struct.unpack("d", file.read(8))
        self.matrix_4 = struct.unpack("d", file.read(8))
        self.matrix_5 = struct.unpack("d", file.read(8))
        self.matrix_6 = struct.unpack("d", file.read(8))
        self.matrix_7 = struct.unpack("d", file.read(8))
        self.matrix_8 = struct.unpack("d", file.read(8))
        self.matrix_9 = struct.unpack("d", file.read(8))


class EZCFile:
    def __init__(self, file):
        self._locations = {}
        self._pens = []
        self._objects = []
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
        self._locations['preview'] = struct.unpack("<I", file.read(4))[0]
        self._locations['v1'] = struct.unpack("<I", file.read(4))[0]
        self._locations['pens'] = struct.unpack("<I", file.read(4))[0]
        self._locations['font'] = struct.unpack("<I", file.read(4))[0]
        self._locations['v4'] = struct.unpack("<I", file.read(4))[0]
        self._locations['vectors'] = struct.unpack("<I", file.read(4))[0]
        self._locations['prevectors'] = struct.unpack("<I", file.read(4))[0]

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
        seek = self._locations.get('v1', 0)
        if seek == 0:
            return
        file.seek(seek, 0)

    def parse_v4(self, file):
        seek = self._locations.get('v4', 0)
        if seek == 0:
            return
        file.seek(seek, 0)
        unknown_table = struct.unpack("<24I", file.read(96))

    def parse_preview(self, file):
        seek = self._locations.get('preview', 0)
        if seek == 0:
            return
        file.seek(seek, 0)
        unknown = struct.unpack("<I", file.read(4))[0]
        width = struct.unpack("<I", file.read(4))[0]
        height = struct.unpack("<I", file.read(4))[0]
        v3 = struct.unpack("<3I", file.read(12))
        # 800, 0x200002

        # RGB0
        self._preview_bitmap.extend(struct.unpack(f"<{int(width*height)}I", file.read(4 * width * height)))

    def parse_font(self, file):
        seek = self._locations.get('font', 0)
        if seek == 0:
            return
        file.seek(seek, 0)
        print(file.tell())
        unknown = struct.unpack("<I", file.read(4))[0]
        print(file.tell())

    def parse_pens(self, file):
        seek = self._locations.get('pens', 0)
        if seek == 0:
            return
        file.seek(seek, 0)

        parameter_count = struct.unpack("<I", file.read(4))[0]
        seek = struct.unpack("<I", file.read(4))[0]
        file.seek(seek, 0)
        for c in range(parameter_count):
            self._pens.append(Pen(file))

    def parse_prevectors(self, file):
        """
        Pre-vectors are usually 400 bytes with no values.

        @param file:
        @return:
        """
        seek = self._locations.get('prevectors', 0)
        if seek == 0:
            return
        file.seek(seek, 0)

        # 400 bytes of 00, 100 bytes of int
        self._prevector = struct.unpack("<400B", file.read(400))

    def parse_vectors(self, file):
        seek = self._locations.get('vectors', 0)
        if seek == 0:
            return
        file.seek(seek, 0)

        huffman_dict = {}

        uncompressed_length = struct.unpack("<I", file.read(4))[0]  # 9C 2E 0B 00, 732828
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
                try:
                    while True:
                        obj = EZObject()
                        q = obj.parse(q)
                        self._objects.append(obj)
                except struct.error:
                    pass
                return
            except ValueError:
                a = a[:-1]


class EZDLoader:
    @staticmethod
    def load_types():
        yield "EZCad2 Files", ("ezd",), "application/x-ezd"

    @staticmethod
    def load(context, elements_service, pathname, **kwargs):
        with open(pathname, "br") as file:
            file = EZCFile(file)
        return True
