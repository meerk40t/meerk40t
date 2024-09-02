"""
This module deals with the correction files
"""
import struct

from enum import IntEnum

class CorVersion(IntEnum):
    CORV1 = 0
    CORV2 = 1

class LMC_Correction:
    def __init__(self, filename, *args, **kwargs):
        self.corfile_name = filename
        self.cor_version = CorVersion.CORV1
        self._cor_table = None
        self._cor_scale = None
        if self.corfile_name:
            self.read_correction_file()

    @property
    def cor_table(self):
        if self._cor_table is None:
            self.read_correction_file()
        return self._cor_table

    @property
    def cor_scale(self):
        if self._cor_scale is None:
            self.read_correction_file()
        return self._cor_scale
    
    def read_correction_file(self):
        """
        Reads a standard .cor file and builds a table from that.

        @param filename:
        @return:
        """
        filename = self.corfile_name
        try:
            with open(filename, "rb") as f:
                label = f.read(0x16)
                if label.decode("utf-16") == "LMC1COR_1.0":
                    unk = f.read(2)
                    header = struct.unpack("63d", f.read(0x1F8))
                    self._cor_scale = header[43]
                    self.cor_version = CorVersion.CORV1
                    self._cor_table = self._read_float_correction_file(f)
                else:
                    unk = f.read(6)
                    header = struct.unpack("d", f.read(8))[0]
                    self._cor_scale = header[0]
                    self.cor_version = CorVersion.CORV2
                    self._cor_table = self._read_int_correction_file(f)
        except (OSError, FileNotFoundError, PermissionError):
            self._cor_table = None
            self._cor_scale = None
                
    def _read_float_correction_file(self, f):
        """
        Read table for cor files marked: LMC1COR_1.0
        @param f:
        @return:
        """
        table = []
        for j in range(65):
            for k in range(65):
                dx = int(round(struct.unpack("d", f.read(8))[0]))
                dx = dx if dx >= 0 else -dx + 0x8000
                dy = int(round(struct.unpack("d", f.read(8))[0]))
                dy = dy if dy >= 0 else -dy + 0x8000
                table.append([dx & 0xFFFF, dy & 0xFFFF])
        return table

    def _read_int_correction_file(self, f):
        table = []
        for j in range(65):
            for k in range(65):
                dx = int.from_bytes(f.read(4), "little", signed=True)
                dx = dx if dx >= 0 else -dx + 0x8000
                dy = int.from_bytes(f.read(4), "little", signed=True)
                dy = dy if dy >= 0 else -dy + 0x8000
                table.append([dx & 0xFFFF, dy & 0xFFFF])
        return table

    def write_correction_file(self, filename=None, version=None):
        if filename is None:
            filename = self.corfile_name
        if version is None:
            version = self.cor_version
        with open(filename, "wb") as f:
            if version == CorVersion.CORV1:
                self._write_float_correction_file(f)
            else:
                self._write_int_correction_file(f)
        return

    def _write_float_correction_file(self, f):
        """
        Write table for cor files marked: LMC1COR_1.0
        @param f:
        @return:
        """
        label = "LMC1COR_1.0"
        data = bytes(label.encode("utf-16"))
        f.write(struct.pack("16B", *data))
        data = [0.0] * 63
        data[43] = self._cor_scale
        f.write(struct.pack("2B", [0]*2))
        f.write(struct.pack("63d", data))

        table = self.cor_table
        idx = 0 
        for j in range(65):
            for k in range(65):
                dx, dy = table[idx]
                idx += 1
                # We reverse the original calculation
                # dx = int(round(struct.unpack("d", f.read(8))[0]))
                # dx = dx if dx >= 0 else -dx + 0x8000
                # dy = int(round(struct.unpack("d", f.read(8))[0]))
                # dy = dy if dy >= 0 else -dy + 0x8000
                # table.append([dx & 0xFFFF, dy & 0xFFFF])
                if dx > 0x8000:
                    dx = - (dx - 0x8000) 
                if dy > 0x8000:
                    dy = - (dy - 0x8000) 
                f.write(struct.pack("d", dx))
                f.write(struct.pack("d", dy))


    def _write_int_correction_file(self, f):
        label = "LMC2COR_2.0"
        data = bytes(label.encode("utf-16"))
        f.write(struct.pack("16B", *data))
        # Header are 6 unknown bytes plus the scale (8 byte double)
        unk = struct.pack("6B", [0]*6)
        f.write(unk)
        f.write(struct.pack("d", self._cor_scale))

        table = self.cor_table
        idx = 0
        for j in range(65):
            for k in range(65):
                dx, dy = table[idx]
                idx += 1
                if dx > 0x8000:
                    dx = - (dx - 0x8000) 
                if dy > 0x8000:
                    dy = - (dy - 0x8000) 
                f.write(int(dx).to_bytes(4, byteorder="little", signed=True))
                f.write(int(dy).to_bytes(4, byteorder="little", signed=True))

    