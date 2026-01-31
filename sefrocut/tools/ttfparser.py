import struct
from io import BytesIO

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

_FLAG_NAMES = {
    ON_CURVE_POINT: "ON_CURVE_POINT",
    ARG_1_AND_2_ARE_WORDS: "ARG_1_AND_2_ARE_WORDS",
    ARGS_ARE_XY_VALUES: "ARGS_ARE_XY_VALUES",
    ROUND_XY_TO_GRID: "ROUND_XY_TO_GRID",
    WE_HAVE_A_SCALE: "WE_HAVE_A_SCALE",
    MORE_COMPONENTS: "MORE_COMPONENTS",
    WE_HAVE_AN_X_AND_Y_SCALE: "WE_HAVE_AN_X_AND_Y_SCALE",
    WE_HAVE_A_TWO_BY_TWO: "WE_HAVE_A_TWO_BY_TWO",
    WE_HAVE_INSTRUCTIONS: "WE_HAVE_INSTRUCTIONS",
    USE_MY_METRICS: "USE_MY_METRICS",
    OVERLAP_COMPOUND: "OVERLAP_COMPOUND",
}


def flagname(flag):
    """Return all active flag names for the given flag value."""
    names = [name for bit, name in _FLAG_NAMES.items() if flag & bit]
    return " | ".join(names) if names else f"UNKNOWN_FLAG_{flag}"


class TTFParsingError(ValueError):
    """Parsing error"""


class TrueTypeFont:
    def __init__(self, filename, require_checksum=False):
        self._raw_tables = {}
        self.version = None
        self.font_revision = None
        self.checksum_adjust = None
        self.magic_number = None
        self.flags = None
        self.units_per_em = 1000  # Default value, will be overwritten during parsing
        self.created = None
        self.modified = None
        self.active = True
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
        self.number_of_long_hor_metrics = (
            0  # Default value, will be overwritten during parsing
        )

        self.font_family = None
        self.font_subfamily = None
        self.font_name = None
        self._character_map = {}
        self._variation_sequences = {}  # Unicode variation sequences mapping
        self._glyph_offsets = []
        self.horizontal_metrics = []

        self.is_okay = False
        self.cmap_version = -1
        self.parse_ttf(filename, require_checksum=require_checksum)
        if (
            b"CFF " in self._raw_tables
            and b"glyf" not in self._raw_tables
            and b"loca" not in self._raw_tables
        ):
            error_msg = "Format CFF font file is not supported."
            self._logger(error_msg)
            raise TTFParsingError(error_msg)
        try:
            self.parse_head()
            self.parse_hhea()
            self.parse_hmtx()
            self.parse_loca()
            self.parse_cmap()
            self.parse_name()
        except Exception as e:
            error_msg = f"TTF init for {filename} crashed: {e}"
            self._logger(error_msg)
            raise TTFParsingError(error_msg) from e
        self.glyph_data = list(self.parse_glyf())
        self._line_information = []

    def _logger(self, message):
        DEBUG = True
        # This can be replaced with an actual logging implementation
        if DEBUG:
            print(message)

    def line_information(self):
        return self._line_information

    @property
    def glyphs(self):
        return list(self._character_map.keys())

    @staticmethod
    def query_name(filename):
        def get_string(f, off, length, platform_id, platform_specific_id, filename):
            string = None
            try:
                location = f.tell()
                f.seek(off)
                string = f.read(length)
                f.seek(location)
                if string is None:
                    return ""
                
                # Handle platform-specific encodings
                if platform_id == 0:  # Unicode
                    return string.decode("UTF-16BE")
                elif platform_id == 1:  # Macintosh
                    if platform_specific_id == 0:  # MacRoman
                        try:
                            return string.decode("mac_roman")
                        except UnicodeDecodeError:
                            # Fall back to UTF-8 for some Mac fonts
                            return string.decode("UTF-8")
                    else:
                        # Other Macintosh encodings, try UTF-8
                        return string.decode("UTF-8")
                elif platform_id == 3:  # Windows
                    return string.decode("UTF-16BE")
                else:
                    # Unknown platform, try UTF-16BE first
                    return string.decode("UTF-16BE")
            except UnicodeDecodeError:
                try:
                    decoded = string.decode("UTF8") if string is not None else ""
                    # Check if the decoded string looks like binary garbage
                    # If it contains non-printable characters or looks like raw bytes, use fallback
                    # Heuristic for detecting binary garbage, but allow valid non-Latin scripts
                    # Only reject if we have clear signs of corrupted data:
                    # - Contains null bytes
                    # - Majority of characters are control characters (excluding common whitespace)
                    # - String is suspiciously short with only control characters
                    if len(decoded) > 0:
                        control_char_count = sum(1 for c in decoded if ord(c) < 32 and c not in '\t\n\r')
                        null_byte_count = decoded.count('\x00')
                        
                        # Reject if:
                        # 1. Contains null bytes (clear sign of corruption)
                        # 2. More than 50% control characters (excluding tabs/newlines)
                        # 3. Very short string (< 3 chars) that's all control characters
                        if (null_byte_count > 0 or
                            (len(decoded) > 0 and control_char_count / len(decoded) > 0.5) or
                            (len(decoded) < 3 and control_char_count == len(decoded))):
                            # Return file basename as fallback to help identify problematic files
                            import os
                            return f"<{os.path.basename(filename)}>"
                    return decoded
                except UnicodeDecodeError:
                    # Return file basename as fallback to help identify problematic files
                    import os
                    return f"<{os.path.basename(filename)}>"

        try:
            with open(filename, "rb") as f:
                (
                    sfnt_version,
                    num_tables,
                    search_range,
                    entry_selector,
                    range_shift,
                ) = struct.unpack(">LHHHH", f.read(12))

                name_table = False
                for i in range(num_tables):
                    tag, checksum, offset, length = struct.unpack(">4sLLL", f.read(16))
                    if tag == b"name":
                        f.seek(offset)
                        name_table = True
                        break
                if not name_table:
                    return None, None, None

                # We are now at the name table.
                table_start = f.tell()
                (
                    fmt,
                    count,
                    strings_offset,
                ) = struct.unpack(">HHH", f.read(6))
                if fmt == 1:
                    (langtag_count,) = struct.unpack(">H", f.read(2))
                    for langtag_record in range(langtag_count):
                        (langtag_len, langtag_offset) = struct.unpack(">HH", f.read(4))

                font_family = None
                font_subfamily = None
                font_name = None
                for record_index in range(count):
                    (
                        platform_id,
                        platform_specific_id,
                        language_id,
                        name_id,
                        length,
                        record_offset,
                    ) = struct.unpack(">HHHHHH", f.read(2 * 6))
                    pos = table_start + strings_offset + record_offset
                    if name_id == 1:
                        font_family = get_string(f, pos, length, platform_id, platform_specific_id, filename)
                    elif name_id == 2:
                        font_subfamily = get_string(f, pos, length, platform_id, platform_specific_id, filename)
                    elif name_id == 4:
                        font_name = get_string(f, pos, length, platform_id, platform_specific_id, filename)
                    if font_family and font_subfamily and font_name:
                        break
                return font_family, font_subfamily, font_name
        except Exception:
            # Anything fishy
            return None

    def render(
        self,
        path,
        vtext,
        horizontal=True,
        font_size=12.0,
        h_spacing=1.0,
        v_spacing=1.1,
        align="start",
    ):
        def _do_render(to_render, offsets):
            # Letter spacing
            scale = font_size / self.units_per_em
            offset_y = 0
            lines = to_render.split("\n")
            if offsets is None:
                offsets = [0] * len(lines)
            self._line_information.clear()
            for text, offs in zip(lines, offsets):
                line_start_x = offs * scale
                line_start_y = offset_y * scale
                offset_x = offs
                # print (f"{offset_x}, {offset_y}: '{text}', fs={font_size}, em:{self.units_per_em}")
                for (
                    base_char_code,
                    variation_selector,
                ) in self.parse_text_with_variation_sequences(text):
                    index = self.lookup_glyph_with_variation(
                        base_char_code, variation_selector
                    )
                    if index >= len(self.glyph_data):
                        continue
                    if index >= len(self.horizontal_metrics):
                        # print (f"Horizontal metrics has {len(self.horizontal_metrics)} elements, requested index {index}")
                        advance_x = self.units_per_em * h_spacing
                    else:
                        hm = self.horizontal_metrics[index]
                        if isinstance(hm, (list, tuple)):
                            advance_x = hm[0] * h_spacing
                        else:
                            advance_x = hm * h_spacing
                    advance_y = 0
                    glyph = self.glyph_data[index]
                    if self.active:
                        path.new_path()
                    for contour in glyph:
                        if len(contour) == 0:
                            continue
                        contour = list(contour)
                        curr = contour[-1]
                        next = contour[0]
                        if curr[2] & ON_CURVE_POINT:
                            start_x = (offset_x + curr[0]) * scale
                            start_y = (offset_y + curr[1]) * scale
                        elif next[2] & ON_CURVE_POINT:
                            start_x = (offset_x + next[0]) * scale
                            start_y = (offset_y + next[1]) * scale
                        else:
                            start_x = (offset_x + (curr[0] + next[0]) / 2) * scale
                            start_y = (offset_y + (curr[1] + next[1]) / 2) * scale
                        if self.active:
                            path.move(start_x, start_y)
                        for i in range(len(contour)):
                            curr = next
                            next = contour[(i + 1) % len(contour)]
                            if curr[2] & ON_CURVE_POINT:
                                if self.active:
                                    path.line(
                                        None,
                                        None,
                                        (offset_x + curr[0]) * scale,
                                        (offset_y + curr[1]) * scale,
                                    )
                            else:
                                next2 = next
                                if not next[2] & ON_CURVE_POINT:
                                    next2 = (
                                        (curr[0] + next[0]) / 2,
                                        (curr[1] + next[1]) / 2,
                                    )
                                if self.active:
                                    path.quad(
                                        None,
                                        None,
                                        (offset_x + curr[0]) * scale,
                                        (offset_y + curr[1]) * scale,
                                        (offset_x + next2[0]) * scale,
                                        (offset_y + next2[1]) * scale,
                                    )
                        if self.active:
                            path.close()
                    offset_x += advance_x
                    offset_y += advance_y
                    if self.active:
                        path.character_end()
                # Store start point, nonscaled width plus scaled width and height of line
                self._line_information.append(
                    (
                        line_start_x,
                        line_start_y,
                        offset_x,
                        offset_x * scale - line_start_x,
                        self.units_per_em * scale,
                    )
                )
                offset_y -= v_spacing * self.units_per_em
            line_lens = [e[2] for e in self._line_information]
            return line_lens

        if not self.is_okay:
            return
        self.active = False
        line_lengths = _do_render(vtext, None)
        max_len = max(line_lengths)
        offsets = []
        for ll in line_lengths:
            # NB anchor not only defines the alignment of the individual
            # lines to another but as well of the whole block relative
            # to the origin
            if align == "middle":
                offs = -max_len / 2 + (max_len - ll) / 2
            elif align == "end":
                offs = -ll
            else:
                offs = 0
            offsets.append(offs)
        self.active = True
        line_lengths = _do_render(vtext, offsets)

    def parse_ttf(self, font_path, require_checksum=True):
        with open(font_path, "rb") as f:
            try:
                header = f.read(12)
                (
                    sfnt_version,
                    num_tables,
                    search_range,
                    entry_selector,
                    range_shift,
                ) = struct.unpack(">LHHHH", header)
                for _ in range(num_tables):
                    tag, checksum, offset, length = struct.unpack(">4sLLL", f.read(16))
                    p = f.tell()
                    f.seek(offset)
                    data = f.read(length)
                    f.seek(p)
                    if require_checksum:
                        for b, byte in enumerate(data):
                            checksum -= byte << 24 - (8 * (b % 4))
                        if tag == b"head" and checksum % (1 << 32) != 0:
                            error_msg = f"Invalid checksum for table {tag.decode('ascii')}: {checksum % (1 << 32)} != 0"
                            self._logger(error_msg)
                            raise TTFParsingError(error_msg)
                    self._raw_tables[tag] = data
            except Exception as e:
                error_msg = f"Error parsing TTF file {font_path}: {e}"
                self._logger(error_msg)
                raise TTFParsingError(error_msg) from e

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
        for p in (
            (3, 10),
            (0, 6),
            (0, 4),
            (3, 1),
            (0, 3),
            (0, 2),
            (0, 1),
            (0, 0),
            (3, 0),
        ):
            if p in cmaps:
                data.seek(cmaps[p])
                parsed = self._parse_cmap_table(data)
                if parsed:
                    self.is_okay = True
                    return
        self.is_okay = False
        # raise ValueError("Could not locate an acceptable cmap.")

    def _parse_cmap_table(self, data):
        _fmt = struct.unpack(">H", data.read(2))[0]
        self.cmap_version = _fmt
        if _fmt == 0:
            return self._parse_cmap_format_0(data)
        elif _fmt == 2:
            return self._parse_cmap_format_2(data)
        elif _fmt == 4:
            return self._parse_cmap_format_4(data)
        elif _fmt == 6:
            return self._parse_cmap_format_6(data)
        elif _fmt == 8:
            return self._parse_cmap_format_8(data)
        elif _fmt == 10:
            return self._parse_cmap_format_10(data)
        elif _fmt == 12:
            return self._parse_cmap_format_12(data)
        elif _fmt == 13:
            return self._parse_cmap_format_13(data)
        elif _fmt == 14:
            return self._parse_cmap_format_14(data)
        self.cmap_version = -1
        return False

    def _parse_cmap_format_0(self, data):
        length, language = struct.unpack(">HH", data.read(4))
        for i, c in enumerate(data.read(256)):
            self._character_map[chr(i + 1)] = c
        return True

    def _parse_cmap_format_2(self, data):
        """
        Format 2: high-byte mapping through table
        Used for mixed 8/16-bit encoding (primarily for CJK fonts)
        This is a complex format - implementing basic support
        """
        try:
            length, language = struct.unpack(">HH", data.read(4))

            # Read subheader keys (256 entries, each 2 bytes)
            subheader_keys = struct.unpack(">256H", data.read(256 * 2))

            # Find the maximum subheader index to determine how many subheaders we have
            max_subheader_index = max(subheader_keys)
            num_subheaders = (max_subheader_index // 8) + 1  # Each subheader is 8 bytes

            # Calculate remaining data size for validation
            remaining_data_size = len(data.getvalue()) - data.tell()
            expected_subheader_size = num_subheaders * 8

            if remaining_data_size < expected_subheader_size:
                error_msg = f"Insufficient data for subheaders in cmap format 2: expected {expected_subheader_size} bytes, got {remaining_data_size} bytes"
                self._logger(error_msg)
                raise TTFParsingError(error_msg)

            # Read subheaders
            subheaders = []
            for _ in range(num_subheaders):
                first_code, entry_count, id_delta, id_range_offset = struct.unpack(
                    ">HHHH", data.read(8)
                )
                subheaders.append((first_code, entry_count, id_delta, id_range_offset))

            # For format 2, character mapping is complex and depends on:
            # - High byte determining which subheader to use
            # - Low byte being processed through that subheader
            #
            # This is primarily used for CJK encodings and requires careful handling
            # For now, we'll implement basic single-byte mapping (subheader 0)

            if subheaders:
                first_code, entry_count, id_delta, id_range_offset = subheaders[0]

                # For single-byte characters (using subheader 0)
                for byte_val in range(256):
                    if (
                        subheader_keys[byte_val] == 0
                        and byte_val >= first_code
                        and byte_val < first_code + entry_count
                    ):
                        # This character has a mapping in subheader 0
                        try:
                            char_code = byte_val
                            if 0 <= char_code <= 0x10FFFF:
                                # Simple mapping for basic characters
                                glyph_id = (char_code + id_delta) & 0xFFFF
                                if glyph_id != 0:  # 0 means missing glyph
                                    self._character_map[chr(char_code)] = glyph_id
                        except ValueError:
                            continue

            return True
        except struct.error as e:
            error_msg = f"Struct unpacking error in cmap format 2: {e}"
            self._logger(error_msg)
            raise TTFParsingError(error_msg) from e
        except Exception as e:
            error_msg = f"Error parsing cmap format 2: {e}"
            self._logger(error_msg)
            raise TTFParsingError(error_msg) from e

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
        # We need to have an even amount of bytes for unpack
        if len(data) % 2 == 1:
            data = data[:-1]
        data = struct.unpack(f">{len(data)//2}H", data)
        ends = data[:seg_count]
        starts = data[seg_count + 1 : seg_count * 2 + 1]
        deltas = data[seg_count * 2 + 1 : seg_count * 3 + 1]
        offsets = data[seg_count * 3 + 1 :]
        for seg in range(seg_count):
            end = ends[seg]
            start = starts[seg]
            delta = deltas[seg]
            offset = offsets[seg]
            if start == end == 0xFFFF:
                break

            for c in range(start, end + 1):
                if offset == 0:
                    self._character_map[chr(c)] = (c + delta) & 0xFFFF
                else:
                    v = (c - start) + seg + (offset >> 1)
                    glyph_index = offsets[v]
                    if glyph_index != 0:
                        glyph_index = (glyph_index + delta) & 0xFFFF
                    self._character_map[chr(c)] = glyph_index
        return True

    def _parse_cmap_format_6(self, data):
        (
            length,
            language,
            first_code,
            entry_count,
        ) = struct.unpack(">HHHH", data.read(8))
        glyph_indices = struct.unpack(f">{entry_count}H", data.read(entry_count * 2))
        for i, glyph_index in enumerate(glyph_indices):
            try:
                char_code = i + first_code
                if 0 <= char_code <= 0x10FFFF:  # Valid Unicode range
                    self._character_map[chr(char_code)] = glyph_index
            except ValueError:
                # Invalid Unicode character, skip
                continue
        return True

    def _parse_cmap_format_8(self, data):
        """
        Format 8: mixed 16-bit and 32-bit coverage
        Used for Unicode variation sequences and supplementary characters
        """
        try:
            # Read header
            reserved, length, language = struct.unpack(">HII", data.read(10))

            # Read is32 array (8192 bytes = 65536 bits, one bit per 16-bit code)
            is32_data = data.read(8192)
            if len(is32_data) < 8192:
                error_msg = "Insufficient data for is32 array in cmap format 8"
                self._logger(error_msg)
                raise TTFParsingError(error_msg)

            # Read number of groups
            n_groups = struct.unpack(">I", data.read(4))[0]

            # Process each group
            for group_idx in range(n_groups):
                if len(data.getvalue()) - data.tell() < 12:
                    error_msg = (
                        f"Insufficient data for group {group_idx} in cmap format 8"
                    )
                    self._logger(error_msg)
                    raise TTFParsingError(error_msg)

                start_char_code, end_char_code, start_glyph_id = struct.unpack(
                    ">III", data.read(12)
                )

                # Validate group
                if start_char_code > end_char_code:
                    continue  # Skip invalid group

                # Map characters in this group
                for char_code in range(start_char_code, end_char_code + 1):
                    try:
                        if 0 <= char_code <= 0x10FFFF:  # Valid Unicode range
                            glyph_id = start_glyph_id + (char_code - start_char_code)
                            self._character_map[chr(char_code)] = glyph_id
                    except ValueError:
                        # Invalid Unicode character, skip
                        continue

            return True
        except struct.error as e:
            error_msg = f"Struct unpacking error in cmap format 8: {e}"
            self._logger(error_msg)
            raise TTFParsingError(error_msg) from e
        except Exception as e:
            error_msg = f"Error parsing cmap format 8: {e}"
            self._logger(error_msg)
            raise TTFParsingError(error_msg) from e

    def _parse_cmap_format_10(self, data):
        """
        Format 10: trimmed table
        Similar to format 6 but uses 32-bit character codes and glyph IDs
        """
        try:
            # Read header (reserved, length, language, startCharCode, numChars)
            reserved, length, language, start_char_code, num_chars = struct.unpack(
                ">HIIII", data.read(18)
            )

            # Validate parameters
            if num_chars == 0:
                return True  # Empty table is valid

            if start_char_code > 0x10FFFF:
                error_msg = (
                    f"Invalid start character code in cmap format 10: {start_char_code}"
                )
                self._logger(error_msg)
                raise TTFParsingError(error_msg)

            # Check we have enough data for the glyph array
            expected_data_size = num_chars * 2  # 2 bytes per glyph ID
            if len(data.getvalue()) - data.tell() < expected_data_size:
                error_msg = f"Insufficient data for glyph array in cmap format 10: expected {expected_data_size} bytes"
                self._logger(error_msg)
                raise TTFParsingError(error_msg)

            # Read glyph IDs
            glyph_ids = struct.unpack(f">{num_chars}H", data.read(expected_data_size))

            # Map characters to glyphs
            for i, glyph_id in enumerate(glyph_ids):
                char_code = start_char_code + i
                try:
                    if 0 <= char_code <= 0x10FFFF:  # Valid Unicode range
                        self._character_map[chr(char_code)] = glyph_id
                except ValueError:
                    # Invalid Unicode character, skip
                    continue

            return True
        except struct.error as e:
            error_msg = f"Struct unpacking error in cmap format 10: {e}"
            self._logger(error_msg)
            raise TTFParsingError(error_msg) from e
        except Exception as e:
            error_msg = f"Error parsing cmap format 10: {e}"
            self._logger(error_msg)
            raise TTFParsingError(error_msg) from e

    def _parse_cmap_format_12(self, data):
        (
            reserved,
            length,
            language,
            n_groups,
        ) = struct.unpack(">HIII", data.read(14))
        for _ in range(n_groups):
            (start_char_code, end_char_code, start_glyph_code) = struct.unpack(
                ">III", data.read(12)
            )

            for char_code in range(start_char_code, end_char_code + 1):
                try:
                    if 0 <= char_code <= 0x10FFFF:  # Valid Unicode range
                        glyph_index = start_glyph_code + (char_code - start_char_code)
                        self._character_map[chr(char_code)] = glyph_index
                except ValueError:
                    # Invalid Unicode character, skip
                    continue
        return True

    def _parse_cmap_format_13(self, data):
        (
            reserved,
            length,
            language,
            n_groups,
        ) = struct.unpack(">HIII", data.read(14))
        for _ in range(n_groups):
            (start_char_code, end_char_code, glyph_code) = struct.unpack(
                ">III", data.read(12)
            )

            for char_code in range(start_char_code, end_char_code + 1):
                try:
                    if 0 <= char_code <= 0x10FFFF:  # Valid Unicode range
                        self._character_map[chr(char_code)] = glyph_code
                except ValueError:
                    # Invalid Unicode character, skip
                    continue
        return True

    def _parse_cmap_format_14(self, data):
        """
        Format 14: Unicode variation sequences
        Maps variation selector sequences to glyphs
        This format handles Unicode Variation Sequences (UVS) where a base character
        combined with a variation selector can map to a specific glyph variant.

        Performance optimized version to handle large ranges efficiently.
        """
        try:
            # Store current position to calculate relative offsets
            subtable_start = (
                data.tell() - 6
            )  # Subtract 6 for format and length already read

            # Read header
            length, num_var_selector_records = struct.unpack(">IH", data.read(6))

            # Limit processing to avoid infinite loops on malformed fonts
            MAX_VAR_SELECTOR_RECORDS = 100
            MAX_UNICODE_RANGES = 1000
            MAX_UVS_MAPPINGS = 10000
            MAX_RANGE_SIZE = 10000  # Limit individual range processing

            if num_var_selector_records > MAX_VAR_SELECTOR_RECORDS:
                warning_msg = f"Warning: Too many variation selector records ({num_var_selector_records}), limiting to {MAX_VAR_SELECTOR_RECORDS}"
                self._logger(warning_msg)
                num_var_selector_records = MAX_VAR_SELECTOR_RECORDS

            # Each variation selector record is 11 bytes
            for record_idx in range(num_var_selector_records):
                if len(data.getvalue()) - data.tell() < 11:
                    error_msg = (
                        f"Insufficient data for variation selector record {record_idx}"
                    )
                    self._logger(error_msg)
                    break  # Skip remaining records instead of crashing

                # Read variation selector record (24-bit variation selector + 2 offsets)
                vs_bytes = data.read(3)
                variation_selector = struct.unpack(">I", vs_bytes + b"\x00")[
                    0
                ]  # Convert 24-bit to 32-bit
                default_uvs_offset, non_default_uvs_offset = struct.unpack(
                    ">II", data.read(8)
                )

                # Save current position to return to after processing tables
                current_pos = data.tell()

                # Process Default UVS Table (if present) - OPTIMIZED
                if default_uvs_offset != 0:
                    try:
                        # Seek to default UVS table (offset is from start of cmap subtable)
                        data.seek(subtable_start + default_uvs_offset)

                        # Read number of Unicode ranges
                        num_unicode_ranges = struct.unpack(">I", data.read(4))[0]

                        if num_unicode_ranges > MAX_UNICODE_RANGES:
                            warning_msg = f"Warning: Too many Unicode ranges ({num_unicode_ranges}), limiting to {MAX_UNICODE_RANGES}"
                            self._logger(warning_msg)
                            num_unicode_ranges = MAX_UNICODE_RANGES

                        # Process each Unicode range - WITH LIMITS
                        for _ in range(num_unicode_ranges):
                            if len(data.getvalue()) - data.tell() < 4:
                                break  # Not enough data for this range

                            # Each range is 4 bytes: 3-byte start code + 1-byte additional count
                            range_data = data.read(4)
                            start_unicode_value = struct.unpack(
                                ">I", range_data[:3] + b"\x00"
                            )[0]
                            additional_count = range_data[3]

                            # Limit range size to prevent infinite loops
                            if additional_count > MAX_RANGE_SIZE:
                                warning_msg = f"Warning: Large range size ({additional_count}), limiting to {MAX_RANGE_SIZE}"
                                self._logger(warning_msg)
                                additional_count = MAX_RANGE_SIZE

                            # Pre-build character map for efficient lookup
                            char_map_keys = set(
                                ord(c) for c in self._character_map.keys()
                            )

                            # Map all characters in this range - OPTIMIZED
                            for offset in range(additional_count + 1):
                                base_char = start_unicode_value + offset
                                if (
                                    0 <= base_char <= 0x10FFFF
                                    and base_char in char_map_keys
                                ):
                                    try:
                                        # For default UVS, use the default glyph mapping
                                        base_char_obj = chr(base_char)
                                        # Store variation sequence mapping
                                        vs_key = (base_char, variation_selector)
                                        self._variation_sequences[
                                            vs_key
                                        ] = self._character_map[base_char_obj]
                                    except (ValueError, KeyError):
                                        continue
                    except (struct.error, IndexError) as e:
                        error_msg = f"Error processing default UVS table: {e}"
                        self._logger(error_msg)

                # Process Non-Default UVS Table (if present) - OPTIMIZED
                if non_default_uvs_offset != 0:
                    try:
                        # Seek to non-default UVS table
                        data.seek(subtable_start + non_default_uvs_offset)

                        # Read number of UVS mappings
                        num_uvs_mappings = struct.unpack(">I", data.read(4))[0]

                        if num_uvs_mappings > MAX_UVS_MAPPINGS:
                            warning_msg = f"Warning: Too many UVS mappings ({num_uvs_mappings}), limiting to {MAX_UVS_MAPPINGS}"
                            self._logger(warning_msg)
                            num_uvs_mappings = MAX_UVS_MAPPINGS

                        # Process each UVS mapping
                        for _ in range(num_uvs_mappings):
                            if len(data.getvalue()) - data.tell() < 5:
                                break  # Not enough data for this mapping

                            # Each mapping is 5 bytes: 3-byte Unicode value + 2-byte glyph ID
                            mapping_data = data.read(5)
                            unicode_value = struct.unpack(
                                ">I", mapping_data[:3] + b"\x00"
                            )[0]
                            glyph_id = struct.unpack(">H", mapping_data[3:5])[0]

                            if 0 <= unicode_value <= 0x10FFFF:
                                # Store non-default variation sequence mapping
                                vs_key = (unicode_value, variation_selector)
                                self._variation_sequences[vs_key] = glyph_id
                    except (struct.error, IndexError) as e:
                        error_msg = f"Error processing non-default UVS table: {e}"
                        self._logger(error_msg)

                # Return to position after variation selector record
                data.seek(current_pos)

            return True
        except struct.error as e:
            error_msg = f"Struct unpacking error in cmap format 14: {e}"
            self._logger(error_msg)
            return False  # Don't crash, just return False
        except Exception as e:
            error_msg = f"Error parsing cmap format 14: {e}"
            self._logger(error_msg)
            return False  # Don't crash, just return False

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

        # Check if we have enough data for the long horizontal metrics
        if len(data) < count * 4:
            error_msg = f"Insufficient data in hmtx table: expected {count * 4} bytes, got {len(data)}"
            self._logger(error_msg)
            raise TTFParsingError(error_msg)

        hm = struct.unpack(f">{'Hh' * count}", data[: count * 4])
        self.horizontal_metrics = [
            (hm[2 * i], hm[2 * i + 1]) for i in range(len(hm) // 2)
        ]

        # Handle additional left side bearings for remaining glyphs
        last_advance = hm[-2] if hm else 0
        table_start = count * 4
        if len(data) > table_start:
            remaining = (len(data) - table_start) // 2
            if remaining > 0:
                left_bearings = struct.unpack(
                    f">{remaining}h", data[table_start : table_start + remaining * 2]
                )
                # Extend with tuples of (last_advance, left_bearing)
                self.horizontal_metrics.extend(
                    [(last_advance, lb) for lb in left_bearings]
                )

    def parse_loca(self):
        try:
            data = self._raw_tables[b"loca"]
        except KeyError:
            self._glyph_offsets = []
            return
        if self.index_to_loc_format == 0:
            n = len(data) // 2
            self._glyph_offsets = [g * 2 for g in struct.unpack(f">{n}H", data)]
        else:
            n = len(data) // 4
            self._glyph_offsets = struct.unpack(f">{n}I", data)

    def parse_glyf(self):
        for i in range(len(self._glyph_offsets) - 1):
            yield list(self._parse_glyph_index(i))

    def _parse_glyph_index(self, index):
        data = self._raw_tables[b"glyf"]
        start = self._glyph_offsets[index]
        end = self._glyph_offsets[index + 1]
        if start == end:
            yield []
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
        """
        Parses a compound glyph, which can consist of multiple components.
        Each component can have its own transformation matrix applied to it.
        The transformation matrix can include scaling, translation, and rotation.
        The flags indicate how the arguments are interpreted, whether they are
        absolute coordinates or relative offsets, and whether the glyph is
        transformed by a scale, x and y scale, or a two-by-two matrix.
        The glyphs are returned as a list of contours, where each contour is a
        list of points. Each point is a tuple of (x, y, flag), where
        x and y are the coordinates of the point, and flag indicates whether
        the point is an on-curve point or a control point.

        The flags used in the compound glyphs are defined as follows:
        - ON_CURVE_POINT: Indicates that the point is an on-curve point.
        - ARG_1_AND_2_ARE_WORDS: Indicates that the first two arguments are
          16-bit signed integers instead of 8-bit unsigned integers.
        - ARGS_ARE_XY_VALUES: Indicates that the arguments are interpreted as
          x and y coordinates instead of relative offsets.
        - ROUND_XY_TO_GRID: Indicates that the x and y coordinates should be
          rounded to the nearest grid point.
        - WE_HAVE_A_SCALE: Indicates that the glyph is transformed by a single
          scale factor applied to both x and y coordinates.
        - MORE_COMPONENTS: Indicates that there are more components in the
          compound glyph. This flag is used to indicate that the glyph has
          additional components that need to be processed.
        - WE_HAVE_AN_X_AND_Y_SCALE: Indicates that the glyph is transformed by
          separate scale factors for x and y coordinates.
        - WE_HAVE_A_TWO_BY_TWO: Indicates that the glyph is transformed by a
          two-by-two matrix, which allows for more complex transformations
          including rotation and shearing.
        - WE_HAVE_INSTRUCTIONS: Indicates that the glyph has instructions that
          modify the rendering of the glyph. These instructions can include
          additional transformations or adjustments to the glyph's shape.
        - USE_MY_METRICS: Indicates that the glyph should use its own metrics
          instead of the metrics defined in the font's horizontal metrics table.
        - OVERLAP_COMPOUND: Indicates that the components of the compound glyph
          may overlap. This flag is used to indicate that the components of the
          compound glyph may overlap, which can affect how the glyph is rendered.

        """
        flags = MORE_COMPONENTS
        scale_factor = 1 << 14  # Fixed point scale factor (16384)

        # Collect all contours from all components
        all_contours = []

        while flags & MORE_COMPONENTS:
            # Initialize transformation matrix as identity
            # Matrix format: [xx, xy, yx, yy, dx, dy]
            # Represents: [x'] = [xx xy] [x] + [dx]
            #             [y']   [yx yy] [y]   [dy]
            transform_xx, transform_xy, transform_yx, transform_yy = 1.0, 0.0, 0.0, 1.0
            transform_dx, transform_dy = 0.0, 0.0

            # Read component header
            flags, glyph_index = struct.unpack(">HH", data.read(4))

            # Read arguments (either offsets or point indices)
            if flags & ARG_1_AND_2_ARE_WORDS:
                # 16-bit arguments
                arg1, arg2 = struct.unpack(">hh", data.read(4))
            else:
                # 8-bit arguments
                if flags & ARGS_ARE_XY_VALUES:
                    # Signed bytes for offsets
                    arg1, arg2 = struct.unpack(">bb", data.read(2))
                else:
                    # Unsigned bytes for point indices
                    arg1, arg2 = struct.unpack(">BB", data.read(2))

            # Interpret arguments
            if flags & ARGS_ARE_XY_VALUES:
                # Arguments are x,y offsets
                transform_dx, transform_dy = float(arg1), float(arg2)
            else:
                # Arguments are point indices for point matching
                # Point matching not fully implemented - would need to find
                # matching points in already processed contours and source glyph
                transform_dx, transform_dy = 0.0, 0.0

            # Read transformation matrix components
            if flags & WE_HAVE_A_SCALE:
                # Single scale factor for both x and y
                scale = struct.unpack(">h", data.read(2))[0] / scale_factor
                transform_xx = transform_yy = scale
            elif flags & WE_HAVE_AN_X_AND_Y_SCALE:
                # Separate scale factors for x and y
                scale_x, scale_y = struct.unpack(">hh", data.read(4))
                transform_xx = scale_x / scale_factor
                transform_yy = scale_y / scale_factor
            elif flags & WE_HAVE_A_TWO_BY_TWO:
                # Full 2x2 transformation matrix
                xx, xy, yx, yy = struct.unpack(">hhhh", data.read(8))
                transform_xx = xx / scale_factor
                transform_xy = xy / scale_factor
                transform_yx = yx / scale_factor
                transform_yy = yy / scale_factor

            # Get the component glyph's contours
            component_contours = list(self._parse_glyph_index(glyph_index))

            # Apply transformation to each contour
            for contour in component_contours:
                transformed_contour = []
                for x, y, flag in contour:
                    # Apply 2D transformation matrix
                    new_x = transform_xx * x + transform_xy * y + transform_dx
                    new_y = transform_yx * x + transform_yy * y + transform_dy

                    # Round to grid if requested
                    if flags & ROUND_XY_TO_GRID:
                        new_x = round(new_x)
                        new_y = round(new_y)

                    transformed_contour.append((new_x, new_y, flag))

                # Add transformed contour to our collection
                all_contours.append(transformed_contour)
        # Yield all collected contours
        yield from all_contours

    def _parse_simple_glyph(self, num_contours, data):
        try:
            # Check we have enough data for contour endpoints
            if len(data.getvalue()) - data.tell() < num_contours * 2:
                error_msg = "Insufficient data for contour endpoints"
                self._logger(error_msg)
                raise TTFParsingError(error_msg)

            end_pts = struct.unpack(f">{num_contours}H", data.read(2 * num_contours))

            # Check we have enough data for instruction length
            if len(data.getvalue()) - data.tell() < 2:
                error_msg = "Insufficient data for instruction length"
                self._logger(error_msg)
                raise TTFParsingError(error_msg)

            inst_len = struct.unpack(">H", data.read(2))[0]

            # Check we have enough data for instructions
            if len(data.getvalue()) - data.tell() < inst_len:
                error_msg = "Insufficient data for instructions"
                self._logger(error_msg)
                raise TTFParsingError(error_msg)

            _ = data.read(inst_len)  # Read instructions but don't store unused variable

            if not end_pts:
                return

            num_points = max(end_pts) + 1
            if num_points <= 0:
                return

            # Read flags with bounds checking
            flags = []
            while len(flags) < num_points:
                if len(data.getvalue()) - data.tell() < 1:
                    error_msg = "Insufficient data for flags"
                    self._logger(error_msg)
                    raise TTFParsingError(error_msg)

                flag = ord(data.read(1))
                flags.append(flag)
                if flag & 0x8:  # Repeat flag
                    if len(data.getvalue()) - data.tell() < 1:
                        error_msg = "Insufficient data for repeat count"
                        self._logger(error_msg)
                        raise TTFParsingError(error_msg)
                    repeat_count = ord(data.read(1))
                    flags.extend([flag] * repeat_count)

            # Truncate flags if we read too many
            flags = flags[:num_points]

            x_coords = list(self._read_coords(num_points, 0x2, 0x10, flags, data))
            y_coords = list(self._read_coords(num_points, 0x4, 0x20, flags, data))

            start = 0
            for end in end_pts:
                if end >= num_points:
                    error_msg = f"Invalid contour endpoint: {end} >= {num_points}"
                    self._logger(error_msg)
                    raise TTFParsingError(error_msg)
                yield list(
                    zip(
                        x_coords[start : end + 1],
                        y_coords[start : end + 1],
                        flags[start : end + 1],
                    )
                )
                start = end + 1
        except struct.error as e:
            error_msg = f"Struct unpacking error in simple glyph: {e}"
            self._logger(error_msg)
            raise TTFParsingError(error_msg) from e
        except (IndexError, ValueError) as e:
            error_msg = f"Error parsing simple glyph: {e}"
            self._logger(error_msg)
            raise TTFParsingError(error_msg) from e

    def _read_coords(self, num_points, bit_byte, bit_delta, flags, data):
        value = 0
        for i in range(num_points):
            if i >= len(flags):
                error_msg = f"Flag index {i} out of range (flags length: {len(flags)})"
                self._logger(error_msg)
                raise TTFParsingError(error_msg)

            flag = flags[i]
            try:
                if flag & bit_byte:
                    # Single byte coordinate
                    if len(data.getvalue()) - data.tell() < 1:
                        error_msg = "Insufficient data for single byte coordinate"
                        self._logger(error_msg)
                        raise TTFParsingError(
                            "Insufficient data for single byte coordinate"
                        )
                    x = struct.unpack("B", data.read(1))[0]
                    if flag & bit_delta:
                        value += x
                    else:
                        value -= x
                elif ~flag & bit_delta:
                    # Two byte coordinate
                    if len(data.getvalue()) - data.tell() < 2:
                        error_msg = "Insufficient data for two byte coordinate"
                        self._logger(error_msg)
                        raise TTFParsingError(
                            "Insufficient data for two byte coordinate"
                        )
                    value += struct.unpack(">h", data.read(2))[0]
                # Coordinate unchanged from previous
                yield value
            except struct.error as e:
                error_msg = f"Struct unpacking error in coordinates: {e}"
                self._logger(error_msg)
                raise TTFParsingError(error_msg) from e

    def parse_name(self):
        def decode(string):
            try:
                return string.decode("UTF-16BE")
            except UnicodeDecodeError:
                try:
                    return string.decode("UTF8")
                except UnicodeDecodeError:
                    # Return a safe fallback instead of raw bytes
                    return "< undecodable font name >"

        data = self._raw_tables[b"name"]
        b = BytesIO(data)
        (
            format,
            count,
            offset,
        ) = struct.unpack(">HHH", b.read(6))
        if format == 1:
            (langtag_count,) = struct.unpack(">H", b.read(2))
            for langtag_record in range(langtag_count):
                (langtag_len, langtag_offset) = struct.unpack(">HH", b.read(4))

        records = [struct.unpack(">HHHHHH", b.read(2 * 6)) for _ in range(count)]
        strings = b.read()
        for (
            platform_id,
            platform_specific_id,
            language_id,
            name_id,
            length,
            str_offset,
        ) in records:
            try:
                if name_id == 1:
                    self.font_family = decode(strings[str_offset : str_offset + length])
                elif name_id == 2:
                    self.font_subfamily = decode(
                        strings[str_offset : str_offset + length]
                    )
                elif name_id == 3:
                    # Unique Subfamily Name
                    pass
                elif name_id == 4:
                    self.font_name = decode(strings[str_offset : str_offset + length])
            except (IndexError, UnicodeDecodeError) as e:
                # Log error but continue parsing other name records
                warning_msg = f"Warning: Error decoding name record {name_id}: {e}"
                self._logger(warning_msg)
                continue

    def get_variation_sequences(self):
        """
        Get Unicode variation sequences mapping.

        Returns:
            dict: Dictionary mapping (base_char, variation_selector) tuples to glyph IDs.
                  For example: {(0x4E00, 0xFE00): 1234} means base character U+4E00
                  with variation selector U+FE00 maps to glyph ID 1234.
        """
        return getattr(self, "_variation_sequences", {})

    def has_variation_sequences(self):
        """
        Check if this font contains Unicode variation sequences (cmap format 14).

        Returns:
            bool: True if the font has variation sequence mappings, False otherwise.
        """
        return bool(getattr(self, "_variation_sequences", {}))

    def get_glyph_index(self, char, variation_selector=None):
        """
        Get the glyph index for a character, optionally with a variation selector.

        Args:
            char (str): The base character
            variation_selector (int, optional): Unicode variation selector code point (e.g., 0xFE00-0xFE0F)

        Returns:
            int: Glyph index, or 0 if not found
        """
        if variation_selector is not None:
            # Try to find variation sequence first
            char_code = ord(char) if isinstance(char, str) else char
            vs_key = (char_code, variation_selector)
            if vs_key in self._variation_sequences:
                return self._variation_sequences[vs_key]

        # Fall back to regular character mapping
        if isinstance(char, str):
            return self._character_map.get(char, 0)

        # Handle numeric character codes
        try:
            return self._character_map.get(chr(char), 0)
        except ValueError:
            return 0

    def has_variation_selector(self, char, variation_selector):
        """
        Check if a character has a specific variation selector mapping.

        Args:
            char (str or int): The base character (string) or character code (int)
            variation_selector (int): Unicode variation selector code point

        Returns:
            bool: True if the variation sequence exists, False otherwise
        """
        char_code = ord(char) if isinstance(char, str) else char
        vs_key = (char_code, variation_selector)
        return vs_key in self._variation_sequences

    def get_available_variation_selectors(self, char):
        """
        Get all variation selectors available for a given character.

        Args:
            char (str or int): The base character (string) or character code (int)

        Returns:
            list: List of variation selector code points available for this character
        """
        char_code = ord(char) if isinstance(char, str) else char
        return [
            vs
            for (base_char, vs) in self._variation_sequences.keys()
            if base_char == char_code
        ]

    def lookup_glyph_with_variation(self, base_char, variation_selector=None):
        """
        Look up a glyph ID for a character, optionally with a variation selector.

        Args:
            base_char (str or int): The base character (string) or Unicode code point (int)
            variation_selector (int, optional): Unicode code point of variation selector

        Returns:
            int: Glyph ID for the character/variation sequence, or 0 if not found
        """
        # Convert base_char to Unicode code point if it's a string
        base_char_code = ord(base_char) if isinstance(base_char, str) else base_char

        if variation_selector is not None:
            # Check for variation sequence first
            vs_key = (base_char_code, variation_selector)
            if vs_key in self._variation_sequences:
                return self._variation_sequences[vs_key]

        # Fall back to regular character map - convert code point back to character for lookup
        try:
            base_char_str = chr(base_char_code)
            return self._character_map.get(base_char_str, 0)
        except (ValueError, OverflowError):
            # Invalid Unicode code point
            return 0

    def parse_text_with_variation_sequences(self, text):
        """
        Parse text and extract base characters with their variation selectors.

        This method correctly handles Unicode code points, including surrogate pairs
        and non-BMP characters, ensuring that variation selectors are properly
        detected even for astral-plane base characters.

        Args:
            text (str): Input text that may contain variation sequences

        Yields:
            tuple: (base_char_code, variation_selector) where variation_selector is None
                   for regular characters or the Unicode code point for variation sequences
        """
        # Convert string to list of Unicode code points to handle surrogate pairs correctly
        code_points = []
        i = 0
        while i < len(text):
            char = text[i]
            char_code = ord(char)

            # Check if this is the start of a surrogate pair (high surrogate)
            if 0xD800 <= char_code <= 0xDBFF and i + 1 < len(text):
                next_char = text[i + 1]
                next_char_code = ord(next_char)

                # Check if next character is low surrogate
                if 0xDC00 <= next_char_code <= 0xDFFF:
                    # Combine surrogate pair into single code point
                    combined_code_point = (
                        0x10000
                        + ((char_code - 0xD800) << 10)
                        + (next_char_code - 0xDC00)
                    )
                    code_points.append(combined_code_point)
                    i += 2  # Skip both surrogate characters
                else:
                    # High surrogate without low surrogate - treat as individual character
                    code_points.append(char_code)
                    i += 1
            else:
                # Regular BMP character or unpaired low surrogate
                code_points.append(char_code)
                i += 1

        # Now iterate over Unicode code points
        i = 0
        while i < len(code_points):
            base_char_code = code_points[i]

            # Check if the next code point is a variation selector
            variation_selector = None
            if i + 1 < len(code_points):
                next_code_point = code_points[i + 1]
                # Check for standardized variation selectors (U+FE00-U+FE0F)
                # or additional variation selectors (U+E0100-U+E01EF)
                if (
                    0xFE00 <= next_code_point <= 0xFE0F
                    or 0xE0100 <= next_code_point <= 0xE01EF
                ):
                    variation_selector = next_code_point
                    i += 1  # Skip the variation selector in next iteration

            yield (base_char_code, variation_selector)
            i += 1

    def debug_variation_sequences(self):
        """
        Debug method to print information about parsed variation sequences.

        Returns:
            str: Debug information about variation sequences
        """
        if not self._variation_sequences:
            return "No variation sequences found in font"

        debug_info = [f"Found {len(self._variation_sequences)} variation sequences:"]
        for (base_char, vs), glyph_id in self._variation_sequences.items():
            try:
                base_char_str = (
                    chr(base_char) if isinstance(base_char, int) else str(base_char)
                )
                vs_str = f"U+{vs:04X}" if vs else "None"
                debug_info.append(
                    f"  {base_char_str} (U+{base_char:04X}) + {vs_str} -> glyph {glyph_id}"
                )
            except (ValueError, TypeError):
                debug_info.append(f"  {base_char} + {vs} -> glyph {glyph_id}")

        return "\n".join(debug_info)

    def test_variation_sequence_lookup(self, base_char, variation_selector):
        """
        Test method to check if a specific variation sequence is supported.

        Args:
            base_char (str): The base character
            variation_selector (int): Unicode code point of variation selector

        Returns:
            dict: Information about the lookup result
        """
        base_char_code = ord(base_char) if isinstance(base_char, str) else base_char
        vs_key = (base_char_code, variation_selector)

        regular_glyph = self._character_map.get(base_char, 0)
        variation_glyph = self.lookup_glyph_with_variation(
            base_char, variation_selector
        )

        return {
            "base_char": base_char,
            "base_char_code": f"U+{base_char_code:04X}",
            "variation_selector": f"U+{variation_selector:04X}",
            "regular_glyph_id": regular_glyph,
            "variation_glyph_id": variation_glyph,
            "has_variation": vs_key in self._variation_sequences,
            "uses_different_glyph": regular_glyph != variation_glyph,
        }
