"""
Parser for .ezd files.
"""
import struct

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

        @param file:
        """
        # 159 * 4, 636,0x027C bytes total
        self.unknown0 = struct.unpack("<I", file.read(4))[0]  # 61
        self.unknown1 = struct.unpack("<I", file.read(4))[0]  # 4
        self.unknown2 = struct.unpack("<I", file.read(4))[0]  # 0
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

        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 64 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 9A 99 99 99
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 99 99 B9 3F
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 F0 3F
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 01 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 30 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 96 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 10 40
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 F0 3F
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 E0 3F
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 01 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 7B 14 AE 47
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # E1 7A 84 3F
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 F0 3F
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 01 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 7B 14 AE 47
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # E1 7A 94 3F
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 64 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 E0 3F
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 96 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # FA 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 24 40
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 40 56 40
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 59 40
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 24 40
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 08 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 04 00 00 00
        self.unknown21 = struct.unpack("<I", file.read(4))[0]  # 00 00 00 00



class EZCFile:
    def __init__(self, file):
        self._locations = {}
        self._pens = []
        self._preview_bitmap = list()
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
        print(file.tell())
        self.parse_preview(file)
        print(file.tell())
        self.parse_v1(file)
        print(file.tell())
        self.parse_pens(file)
        print(file.tell())
        self.parse_font(file)
        print(file.tell())
        self.parse_v4(file)
        print(file.tell())
        self.parse_vectors(file)
        print(file.tell())
        self.parse_prevectors(file)
        print(file.tell())

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
        seek = self._locations.get('prevectors', 0)
        if seek == 0:
            return
        file.seek(seek, 0)
        # 400 bytes of 00
        d0 = struct.unpack("<400b", file.read(400))[0]

    def parse_vectors(self, file):
        seek = self._locations.get('vectors', 0)
        if seek == 0:
            return
        file.seek(seek, 0)

        huffman_dict = {}

        table_length = struct.unpack("<H", file.read(2))[0]
        # dunno = b.read(1)
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
                print(q.hex())
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
