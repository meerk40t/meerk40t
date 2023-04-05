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
        self.unknown1 = struct.unpack("<I", file.read(4))[0]  # 4
        self.color = struct.unpack("<I", file.read(4))[0]
        label_length = struct.unpack("<I", file.read(4))[0]
        label = file.read(label_length)
        self.label = label.decode("utf_16")

        self.unknown3 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00, 4
        self.unknown4 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00, 0
        self.unknown5 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00, 4
        self.unknown6 = struct.unpack("<I", file.read(4))[0]  # 01 00 00 00, 1
        self.unknown7 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00, 4
        self.unknown8 = struct.unpack("<I", file.read(4))[0]  # 01 00 00 00, 1
        self.unknown9 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00, 8
        self.unknown10 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00, 0

        self.unknown11 = struct.unpack("<I", file.read(4))[0]  # 00 40 7F 40,
        self.unknown12 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00, 8
        self.unknown13 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00, 0
        self.unknown14 = struct.unpack("<I", file.read(4))[0]  # 00 00 49 40,
        self.unknown15 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00, 4
        self.unknown16 = struct.unpack("<I", file.read(4))[0]  # 20 4E 00 00, 20000
        self.unknown17 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00, 4
        self.unknown18 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00, 4
        self.unknown19 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00, 4
        self.unknown20 = struct.unpack("<I", file.read(4))[0]  # 2C 01 00 00, 300

        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00, 4
        self.unknown22 = struct.unpack("<I", file.read(4))[0]  # 2C 01 00 00, 300
        self.unknown23 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00, 4
        self.unknown24 = struct.unpack("<I", file.read(4))[0]  # 64 00 00 00, 100
        self.unknown25 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00, 8
        self.unknown26 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00, 0
        self.unknown27 = struct.unpack("<I", file.read(4))[0]  # 00 40 AF 40,
        self.unknown28 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00, 4
        self.unknown29 = struct.unpack("<I", file.read(4))[0]  # F4 01 00 00, 500
        self.unknown30 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00, 4

        self.unknown31 = struct.unpack("<I", file.read(4))[0]  # 64 00 00 00
        self.unknown32 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown33 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown34 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown35 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown36 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown37 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown38 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown39 = struct.unpack("<I", file.read(4))[0]  # 9A 99 99 99
        self.unknown40 = struct.unpack("<I", file.read(4))[0]  # 99 99 B9 3F
        self.unknown41 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown42 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown43 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown44 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown45 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown46 = struct.unpack("<I", file.read(4))[0]  # 00 00 F0 3F
        self.unknown47 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown48 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown49 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown50 = struct.unpack("<I", file.read(4))[0]  # 01 00 00 00
        self.unknown51 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown52 = struct.unpack("<I", file.read(4))[0]  # 30 00 00 00
        self.unknown53 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown54 = struct.unpack("<I", file.read(4))[0]  # 96 00 00 00
        self.unknown55 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown56 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown57 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown58 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown59 = struct.unpack("<I", file.read(4))[0]  # 00 00 10 40
        self.unknown60 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown61 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown62 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown63 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown64 = struct.unpack("<I", file.read(4))[0]  # 00 00 F0 3F
        self.unknown65 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown66 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown67 = struct.unpack("<I", file.read(4))[0]  # 00 00 E0 3F
        self.unknown68 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown69 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown70 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown71 = struct.unpack("<I", file.read(4))[0]  # 01 00 00 00
        self.unknown72 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown73 = struct.unpack("<I", file.read(4))[0]  # 7B 14 AE 47
        self.unknown74 = struct.unpack("<I", file.read(4))[0]  # E1 7A 84 3F
        self.unknown75 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown76 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown77 = struct.unpack("<I", file.read(4))[0]  # 00 00 F0 3F
        self.unknown78 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown79 = struct.unpack("<I", file.read(4))[0]  # 01 00 00 00
        self.unknown80 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown81 = struct.unpack("<I", file.read(4))[0]  # 7B 14 AE 47
        self.unknown82 = struct.unpack("<I", file.read(4))[0]  # E1 7A 94 3F
        self.unknown83 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown84 = struct.unpack("<I", file.read(4))[0]  # 64 00 00 00
        self.unknown85 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown86 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown87 = struct.unpack("<I", file.read(4))[0]  # 00 00 E0 3F
        self.unknown88 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown89 = struct.unpack("<I", file.read(4))[0]  # 96 00 00 00
        self.unknown90 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown91 = struct.unpack("<I", file.read(4))[0]  # FA 00 00 00
        self.unknown92 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown93 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown94 = struct.unpack("<I", file.read(4))[0]  # 00 00 24 40
        self.unknown95 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown96 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown97 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown98 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown99 = struct.unpack("<I", file.read(4))[0]  # 00 40 56 40
        self.unknown100 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown101 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown102 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown103 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown104 = struct.unpack("<I", file.read(4))[0]  # 00 00 59 40
        self.unknown105 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown106 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown107 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown108 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown109 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown110 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown111 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown112 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown113 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown114 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown115 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown116 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown117 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown118 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown119 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown120 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown121 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown122 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown123 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown124 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown125 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown126 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown127 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown128 = struct.unpack("<I", file.read(4))[0]  # 00 00 24 40
        self.unknown129 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown130 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown131 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown132 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown133 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown134 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown135 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown136 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown137 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown138 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown139 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown140 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown141 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown142 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown143 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown144 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown145 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown146 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown147 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown148 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown149 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown151 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown152 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown153 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown154 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00


class EZObject:
    def __init__(self, file):
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

        @param file:
        """
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
        self.unknown1 = struct.unpack("<H", file.read(2))[0]
        self.unknown2 = struct.unpack("<H", file.read(2))[0]
        self.unknown3 = struct.unpack("<H", file.read(2))[0]
        self.unknown4 = struct.unpack("<H", file.read(2))[0]
        self.unknown5 = struct.unpack("<H", file.read(2))[0]
        self.pen = struct.unpack("<H", file.read(2))[0]
        self.unknown7 = struct.unpack("<H", file.read(2))[0]
        self.unknown8 = struct.unpack("<H", file.read(2))[0]
        self.unknown9 = struct.unpack("<H", file.read(2))[0]
        self.object_type_2 = struct.unpack("<H", file.read(2))[0]
        self.unknown11 = struct.unpack("<H", file.read(2))[0]
        self.unknown12 = struct.unpack("<H", file.read(2))[0]
        self.state = struct.unpack("<H", file.read(2))[0]
        # Selected 0x02, Hidden 0x01, Locked 0x10
        self.selected = bool(self.state & 0x02)
        self.hidden = bool(self.state & 0x01)
        self.locked = bool(self.state & 0x10)

        self.unknown14 = struct.unpack("<H", file.read(2))[0]
        self.unknown15 = struct.unpack("<H", file.read(2))[0]
        self.unknown16 = struct.unpack("<H", file.read(2))[0]
        self.unknown17 = struct.unpack("<H", file.read(2))[0]
        self.unknown18 = struct.unpack("<H", file.read(2))[0]
        self.unknown19 = struct.unpack("<H", file.read(2))[0]
        self.unknown20 = struct.unpack("<H", file.read(2))[0]
        self.unknown21 = struct.unpack("<H", file.read(2))[0]
        self.unknown22 = struct.unpack("<H", file.read(2))[0]
        self.unknown23 = struct.unpack("<H", file.read(2))[0]
        self.unknown24 = struct.unpack("<H", file.read(2))[0]
        self.unknown25 = struct.unpack("<H", file.read(2))[0]
        self.unknown26 = struct.unpack("<H", file.read(2))[0]
        self.unknown27 = struct.unpack("<H", file.read(2))[0]
        self.unknown28 = struct.unpack("<H", file.read(2))[0]
        self.input_port_bits = struct.unpack("<H", file.read(2))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 2
        array_state = struct.unpack("<H", file.read(2))[0]
        self.array_bidirectional = bool(array_state & 0x2)
        self.array_vertical = bool(array_state & 0x1)

        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        self.array_count_x = struct.unpack("<I", file.read(4))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        self.array_count_y = struct.unpack("<I", file.read(4))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        self.array_step_x = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        self.array_step_y = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 16
        self.x_pos = struct.unpack("d", file.read(8))[0]
        self.y_pos = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        self.z_pos = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        # self.unknownzz = struct.unpack("<I", file.read(4))[0]
        self.unknownzz = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 16
        self.min_x = struct.unpack("d", file.read(8))[0]
        self.max_x = struct.unpack("d", file.read(8))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 16
        self.max_y = struct.unpack("d", file.read(8))[0]
        self.min_y = struct.unpack("d", file.read(8))[0]
        if self.type == "rect":
            self.parse_rect(file)
        elif self.type == "text":
            self.parse_text(file)

    def parse_text(self, file):
        self.font_angle = struct.unpack("d", file.read(8))  # Font angle in Text.

    def parse_rect(self, file):
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        self.corner_bottom_left = struct.unpack("d", file.read(8))
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        self.corner_bottom_right = struct.unpack("d", file.read(8))
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        self.corner_upper_right = struct.unpack("d", file.read(8))
        data_len = struct.unpack("<I", file.read(4))[0]  # 8
        self.corner_upper_left = struct.unpack("d", file.read(8))
        data_len = struct.unpack("<I", file.read(4))[0]  # 4
        self.unknown106 = struct.unpack("<I", file.read(4))[0]
        data_len = struct.unpack("<I", file.read(4))[0]  # 72
        self.matrix_0 = struct.unpack("d", file.read(8))
        self.matrix_1 = struct.unpack("d", file.read(8))
        self.matrix_2 = struct.unpack("d", file.read(8))
        self.matrix_4 = struct.unpack("d", file.read(8))
        self.matrix_5 = struct.unpack("d", file.read(8))
        self.matrix_6 = struct.unpack("d", file.read(8))
        self.matrix_7 = struct.unpack("d", file.read(8))
        self.matrix_8 = struct.unpack("d", file.read(8))
        self.matrix_9 = struct.unpack("d", file.read(8))
        data_len = struct.unpack("<I", file.read(4))[0]  # 0
        data = file.read()
        print(data)


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
                q = bytes(a.decode(huffman_dict))
                byte_io = BytesIO(q)
                self._objects.append(EZObject(byte_io))
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
