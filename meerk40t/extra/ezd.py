"""
Parser for .ezc files.
"""
import struct

import PIL.Image


def plugin(kernel, lifecycle):
    if lifecycle == "boot":
        context = kernel.root
    elif lifecycle == "register":
        kernel.register("load/EZDLoader", EZDLoader)
        pass
    elif lifecycle == "shutdown":
        pass


class EZDLoader:
    @staticmethod
    def load_types():
        yield "EZCad2 Files", ("ezd",), "application/x-ezd"

    @staticmethod
    def load(context, elements_service, pathname, **kwargs):
        with open(pathname, "br") as file:
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

            # Seek Table
            loc_preview = struct.unpack("<I", file.read(4))[0]
            v1 = struct.unpack("<I", file.read(4))[0]
            loc_parameters = struct.unpack("<I", file.read(4))[0]
            loc_font = struct.unpack("<I", file.read(4))[0]
            v4 = struct.unpack("<I", file.read(4))[0]
            loc_vectors = struct.unpack("<I", file.read(4))[0]
            loc_prevectors = struct.unpack("<I", file.read(4))[0]

            # Unknown table.
            unknown_table = struct.unpack("<24I", file.read(96))

            # Preview Table
            if loc_preview != 0:
                width = struct.unpack("<Q", file.read(8))[0]
                height = struct.unpack("<Q", file.read(8))[0]
                v3 = struct.unpack("<Q", file.read(8))[0]
                v4 = struct.unpack("<Q", file.read(8))[0]
                v5 = struct.unpack("<Q", file.read(8))[0]
                for h in range(height):
                    for w in range(width):
                        rgb0 = struct.unpack("<4B", file.read(4))

            if loc_font == 0:
                unknown = struct.unpack("<I", file.read(4))[0]

            if loc_parameters != 0:
                file.seek(loc_parameters, 1)
                parameter_count = struct.unpack("<I", file.read(4))[0]
                first = struct.unpack("<I", file.read(4))[0]
                for c in range(parameter_count):
                    v0 = struct.unpack("<I", file.read(4))[0]
                    d0 = struct.unpack("<95I", file.read(4))[0]
        return True
