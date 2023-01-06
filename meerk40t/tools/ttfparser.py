from io import BytesIO

import struct

ON_CURVE_POINT = 1
ARG_1_AND_2_ARE_WORDS = 1 << 0
ARGS_ARE_XY_VALUES = 1 << 1
ROUND_XY_TO_GRID = 1 << 2
WE_HAVE_A_SCALE = 1 << 3
# obsolete(4)
MORE_COMPONENTS = 1 << 5
WE_HAVE_AN_X_AND_Y_SCALE = 1 << 6
WE_HAVE_A_TWO_BY_TWO = 1 << 7
WE_HAVE_INSTRUCTIONS = 1 << 8
USE_MY_METRICS = 1 << 9
OVERLAP_COMPOUND = 1 << 10


class TrueTypeFont:
    def __init__(self, filename):
        self._raw_tables = {}
        self.version = None
        self.font_revision = None
        self.checksum_adjust = None
        self.magic_number = None
        self.flags = None
        self.units_per_em = None
        self.created = None
        self.modified = None
        self.x_min = None
        self.y_min = None
        self.x_max = None
        self.y_max = None
        self.mac_style = None
        self.lowest_rec_ppem = None
        self.font_direction_hint = None
        self.index_to_loc_format = None
        self.glyph_data_format = None
        self.ascent = None
        self.descent = None
        self.line_gap = None
        self.advance_width_max = None
        self.min_left_bearing = None
        self.min_right_bearing = None
        self.x_max_extent = None
        self.caret_slope_rise = None
        self.caret_slope_run = None
        self.caret_offset = None
        self.metric_data_format = None
        self.number_of_long_hor_metrics = None

        self._character_map = {}
        self._glyph_offsets = None
        self.horizontal_metrics = None
        self.parse_ttf(filename)
        self.parse_head()
        self.parse_hhea()
        self.parse_hmtx()
        self.parse_loca()
        self.parse_cmap()
        self.glyphs = list(self.parse_glyf())

    def render(self, path, text, horizontal=True, font_size=12.0):
        scale = font_size / self.units_per_em
        offset_x = 0
        offset_y = 0
        for c in text:
            index = self._character_map.get(c, 0)
            advance_x = self.horizontal_metrics[index][0]
            advance_y = 0
            glyph = self.glyphs[index]
            path.new_path()
            for contour in glyph:
                if len(contour) == 0:
                    continue
                contour = list(contour)
                curr = contour[-1]
                next = contour[0]
                if curr[2] & ON_CURVE_POINT:
                    path.move((offset_x + curr[0]) * scale, (offset_y + curr[1]) * scale)
                else:
                    if next[2] & ON_CURVE_POINT:
                        path.move((offset_x + next[0]) * scale, (offset_y + next[1]) * scale)
                    else:
                        path.move((offset_x + (curr[0] + next[0]) / 2) * scale, (offset_y + (curr[1] + next[1]) / 2) * scale)
                for i in range(len(contour)):
                    prev = curr
                    curr = next
                    next = contour[(i+1) % len(contour)]
                    if curr[2] & ON_CURVE_POINT:
                        path.line(None, None, (offset_x + curr[0]) * scale, (offset_y + curr[1]) * scale)
                    else:
                        next2 = next
                        if not next[2] & ON_CURVE_POINT:
                            next2 = (curr[0] + next[0]) / 2, (curr[1] + next[1]) / 2
                        path.quad(
                            None,
                            None,
                            (offset_x + curr[0]) * scale,
                            (offset_y + curr[1]) * scale,
                            (offset_x + next2[0]) * scale,
                            (offset_y + next2[1]) * scale,
                        )
                path.close()
            offset_x += advance_x
            offset_y += advance_y

    def parse_ttf(self, font_path, require_checksum=True):
        with open(font_path, "rb") as f:
            header = f.read(12)
            (
                sfnt_version,
                num_tables,
                search_range,
                entry_selector,
                range_shift,
            ) = struct.unpack(">LHHHH", header)
            for i in range(num_tables):
                tag, checksum, offset, length = struct.unpack(">4sLLL", f.read(16))
                p = f.tell()
                f.seek(offset)
                data = f.read(length)
                f.seek(p)
                if require_checksum:
                    for b, byte in enumerate(data):
                        checksum -= byte << 24 - (8 * (b % 4))
                    assert tag == b"head" or checksum % (1 << 32) == 0
                self._raw_tables[tag] = data

    def parse_head(self):
        data = self._raw_tables[b"head"]
        (
            self.version,
            self.font_revision,
            self.checksum_adjust,
            self.magic_number,
            self.flags,
            self.units_per_em,
            self.created,
            self.modified,
            self.x_min,
            self.y_min,
            self.x_max,
            self.y_max,
            self.mac_style,
            self.lowest_rec_ppem,
            self.font_direction_hint,
            self.index_to_loc_format,
            self.glyph_data_format,
        ) = struct.unpack(">IILLHHQQhhhhHHhhh", data)
        self.version /= 1 << 16
        self.font_revision /= 1 << 16
        assert self.magic_number == 0x5F0F3CF5

    def parse_cmap(self):
        data = BytesIO(self._raw_tables[b"cmap"])
        version, subtables = struct.unpack(">HH", data.read(4))
        cmaps = {}
        for platform_id, platform_specific_id, offset in [
            struct.unpack(">HHI", data.read(8)) for _ in range(subtables)
        ]:
            cmaps[(platform_id, platform_specific_id)] = offset
        for p in ((3, 10), (0, 6), (0, 4), (3, 1), (0, 3), (0, 2), (0, 1), (0, 0)):
            if p in cmaps:
                data.seek(cmaps[p])
                self._parse_cmap_table(data)
                return
        raise ValueError("Could not locate an acceptable cmap.")

    def _parse_cmap_table(self, data):
        format = struct.unpack(">H", data.read(2))[0]
        if format == 0:
            self._parse_cmap_format_0(data)
        elif format == 2:
            self._parse_cmap_format_2(data)
        elif format == 4:
            self._parse_cmap_format_4(data)
        elif format == 6:
            self._parse_cmap_format_6(data)
        elif format == 8:
            self._parse_cmap_format_8(data)
        elif format == 10:
            self._parse_cmap_format_10(data)
        elif format == 12:
            self._parse_cmap_format_12(data)
        elif format == 13:
            self._parse_cmap_format_13(data)
        elif format == 14:
            self._parse_cmap_format_14(data)

    def _parse_cmap_format_0(self, data):
        length, language = struct.unpack(">HH", data.read(4))
        for i, c in enumerate(data.read(256)):
            self._character_map[chr(i+1)] = c

    def _parse_cmap_format_2(self, data):
        length, language = struct.unpack(">HH", data.read(4))
        subheader_keys = struct.unpack(">256H", data.read(256 * 2))
        pass

    def _parse_cmap_format_4(self, data):
        (
            length,
            language,
            seg_count_x2,
            search_range,
            entry_selector,
            range_shift,
        ) = struct.unpack(">HHHHHH", data.read(12))
        seg_count = int(seg_count_x2 / 2)
        data = data.read()
        data = struct.unpack(f">{int(len(data)/2)}H", data)
        ends = data[:seg_count]
        starts = data[seg_count+1:seg_count*2+1]
        deltas = data[seg_count*2+1:seg_count*3+1]
        offsets = data[seg_count*3+1:]
        for seg in range(seg_count):
            end = ends[seg]
            start = starts[seg]
            delta = deltas[seg]
            offset = offsets[seg]

            for c in range(start, end + 1):
                if offset == 0:
                    self._character_map[chr(c)] = (c + delta) & 0xFFFF
                else:
                    v = (c - start) + seg + (offset >> 1)
                    glyph_index = offsets[v]
                    if glyph_index != 0:
                        glyph_index = (glyph_index + delta) & 0xFFFF
                    self._character_map[chr(c)] = glyph_index

    def _parse_cmap_format_6(self, data):
        (
            length,
            language,
            first_code,
            entry_count,
        ) = struct.unpack(">HHHHHH", data.read(12))
        for i, c in struct.unpack(f">{entry_count}H", data.read(entry_count * 2)):
            self._character_map[chr(i + 1 + first_code)] = c

    def _parse_cmap_format_8(self, data):
        pass

    def _parse_cmap_format_10(self, data):
        pass

    def _parse_cmap_format_12(self, data):
        pass

    def _parse_cmap_format_13(self, data):
        pass

    def _parse_cmap_format_14(self, data):
        pass

    def parse_hhea(self):
        data = self._raw_tables[b"hhea"]
        (
            self.version,
            self.ascent,
            self.descent,
            self.line_gap,
            self.advance_width_max,
            self.min_left_bearing,
            self.min_right_bearing,
            self.x_max_extent,
            self.caret_slope_rise,
            self.caret_slope_run,
            self.caret_offset,
            reserved0,
            reserved1,
            reserved2,
            reserved3,
            self.metric_data_format,
            self.number_of_long_hor_metrics,
        ) = struct.unpack(">ihhhHhhhhhhhhhhhH", data)

    def parse_hmtx(self):
        data = self._raw_tables[b"hmtx"]
        count = self.number_of_long_hor_metrics
        hm = struct.unpack(f">{'Hh' * count}", data[: count * 4])
        self.horizontal_metrics = [
            (hm[2 * i], hm[2 * i + 1]) for i in range(len(hm) // 2)
        ]
        last_advance = hm[-2]
        if len(data) > count * 4:
            left_bearing = struct.unpack(f">{(len(data) / 4) - count}h")
            self.horizontal_metrics.extend((last_advance, left_bearing))

    def parse_loca(self):
        data = self._raw_tables[b"loca"]
        if self.index_to_loc_format == 0:
            n = int(len(data) / 2)
            self._glyph_offsets = [g * 2 for g in struct.unpack(f">{n}H", data)]
        else:
            n = int(len(data) / 4)
            self._glyph_offsets = struct.unpack(f">{n}I", data)

    def parse_glyf(self):
        for i in range(len(self._glyph_offsets) - 1):
            yield list(self._parse_glyph_index(i))

    def _parse_glyph_index(self, index):
        data = self._raw_tables[b"glyf"]
        start = self._glyph_offsets[index]
        end = self._glyph_offsets[index+1]
        if start == end:
            yield list()
            return
        yield from self._parse_glyph(BytesIO(data[start:end]))

    def _parse_glyph(self, data):
        num_contours, x_min, y_min, x_max, y_max = struct.unpack(
            ">hhhhh", data.read(10)
        )
        if num_contours > 0:
            yield from self._parse_simple_glyph(num_contours, data)
        elif num_contours < 0:
            yield from self._parse_compound_glyph(data)

    def _parse_compound_glyph(self, data):
        flags = MORE_COMPONENTS
        s = 1 << 14
        last_contour = None
        while flags & MORE_COMPONENTS:
            a, b, c, d, e, f = (
                1.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
            )
            dest, src = -1, -1
            flags, glyph_index = struct.unpack(">HH", data.read(4))
            if flags & ARGS_ARE_XY_VALUES:
                if flags & ARG_1_AND_2_ARE_WORDS:
                    args1, args2 = struct.unpack(">hh", data.read(4))
                else:
                    args1, args2 = struct.unpack(">bb", data.read(2))
                e, f = args1 / s, args2 / s
            else:
                if flags & ARG_1_AND_2_ARE_WORDS:
                    args1, args2 = struct.unpack(">HH", data.read(4))
                else:
                    args1, args2 = struct.unpack(">BB", data.read(2))
                dest, src = args1, args2
            if flags & WE_HAVE_A_SCALE:
                a = struct.unpack(">h", data.read(2))[0] / s
                d = a
            elif flags & WE_HAVE_AN_X_AND_Y_SCALE:
                a, d = struct.unpack(">hh", data.read(4))
                a, d = a / s, d / s
            elif flags & WE_HAVE_A_TWO_BY_TWO:
                a, b, c, d = struct.unpack(">hhhh", data.read(8))
                a, b, c, d = a / s, b / s, c / s, d / s
            original = data.tell()
            m = max(abs(a), abs(b))
            if abs(abs(a) - abs(c)) < 33.0 / s:
                m *= 2
            n = max(abs(c), abs(d))
            if abs(abs(b) - abs(c)) < 33.0 / s:
                n *= 2
            contours = list(self._parse_glyph_index(glyph_index))
            if src != -1 and dest != -1:
                pass  # Not properly supported.
            last_contour = contours
            if flags & ROUND_XY_TO_GRID:
                for contour in contours:
                    yield [
                        (
                            round(m * (x * a / m + y * b / m + e)),
                            round(n * (x * c / n + y * d / n + f)),
                            flag,
                        )
                        for x, y, flag in contour
                    ]
            else:
                for contour in contours:
                    yield [
                        (
                            m * (x * a / m + y * b / m + e),
                            n * (x * c / n + y * d / n + f),
                            flag,
                        )
                        for x, y, flag in contour
                    ]
            data.seek(original)

    def _parse_simple_glyph(self, num_contours, data):
        end_pts = struct.unpack(f">{num_contours}H", data.read(2 * num_contours))
        inst_len = struct.unpack(">H", data.read(2))[0]
        instruction = data.read(inst_len)
        num_points = max(end_pts) + 1
        flags = []
        while len(flags) < num_points:
            flag = ord(data.read(1))
            flags.append(flag)
            if flag & 0x8:
                repeat_count = ord(data.read(1))
                flags.extend([flag] * repeat_count)
        x_coords = list(self._read_coords(num_points, 0x2, 0x10, flags, data))
        y_coords = list(self._read_coords(num_points, 0x4, 0x20, flags, data))
        start = 0
        for end in end_pts:
            yield list(zip(x_coords[start:end + 1], y_coords[start:end + 1], flags[start:end + 1]))
            start = end + 1

    def _read_coords(self, num_points, bit_byte, bit_delta, flags, data):
        value = 0
        for i in range(num_points):
            flag = flags[i]
            if flag & bit_byte:
                x = struct.unpack("B", data.read(1))[0]
                if flag & bit_delta:
                    value += x
                else:
                    value -= x
            elif ~flag & bit_delta:
                value += struct.unpack(">h", data.read(2))[0]
            else:
                pass
            yield value
