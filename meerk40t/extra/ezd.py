"""
Parser for .ezd files.

EZD (EZCad2) files are proprietary binary files produced by EZCad2 laser engraving software.
These files contain complete laser cutting/engraving projects with vector graphics, text, images,
hatch patterns, and all associated processing parameters.

FILE FORMAT OVERVIEW:
====================

EZD files use a complex binary structure with the following main sections:

1. HEADER (176 bytes total):
   - Magic number: "EZCADUNI" (16 bytes, UTF-16)
   - Version info: Two int32 values (typically 0, 2001)
   - Metadata strings: Three 60-byte UTF-16 strings (user info, software version, etc.)
   - Additional header data: 140 bytes (purpose unknown)

2. SEEK TABLE (28 bytes):
   - Contains 7 int32 offsets pointing to different data sections:
     * Preview bitmap location
     * V1 table (usually unused)
     * Pen definitions
     * Font table
     * V4 table (unknown purpose)
     * Vector objects (main content)
     * Pre-vector data (usually empty)

3. UNKNOWN SECTION (96 bytes):
   - Padding or reserved space between seek table and content

4. DATA TABLES (parsed via seek table offsets):
   - Preview: RGB bitmap of the design
   - Pens: Up to 256 laser parameter sets (power, speed, frequency, etc.)
   - Fonts: Font names used in text objects
   - Vectors: Huffman-compressed main content containing all design elements

VECTOR DATA STRUCTURE:
=====================

The main vector section contains Huffman-compressed binary data that expands to a stream
of EZ objects. Each object follows this structure:

- Object Type (int32): Identifies the object class (1=Curve, 3=Rect, 4=Circle, etc.)
- Object Header (15 fields): Common properties for all objects
  * pen: Laser parameter set index (0-255)
  * type/state: Object flags (selected, hidden, locked)
  * label: Object name/description
  * position: X,Y coordinates (relative to design center)
  * z_pos: Z-axis position
  * Various other properties (array settings, input/output bits, etc.)
- Object-specific data: Variable-length data depending on object type
- Child count (int32): Number of child objects (for groups/containers)
- Child objects: Recursively nested EZ objects

OBJECT TYPES:
============

Primitive Shapes:
- EZCurve (1): Multi-contour paths with line/quadratic/cubic segments
- EZRect (3): Rectangles with optional corner rounding
- EZCircle (4): Circles/ellipses with center/radius
- EZEllipse (5): Ellipses with bounding box and rotation
- EZPolygon (6): Regular polygons (triangle, square, etc.)

Text and Images:
- EZText (0x800): Text objects with font, size, position
- EZImage (0x40): Bitmap images with processing parameters

Groups and Modifications:
- EZGroup (0x10): Object collections/groups
- EZCombine (0x30): Combined path operations
- EZHatch (0x20): Hatch patterns applied to child objects
- EZSpiral (0x60): Spiral distortions of child objects

Control Objects:
- EZTimer (0x2000): Wait/delay commands
- EZInput (0x3000): Wait for external input signals
- EZOutput (0x4000): Send output signals
- EZEncoderDistance (0x6000): Rotary encoder movements
- EZExtendAxis (0x5000): Extended axis control

Special Objects:
- EZVectorFile (0x50): Imported vector files (SVG, DXF, etc.)

HATCH OBJECTS:
=============

Hatch objects are complex containers that apply laser fill patterns to child geometry.
They support up to 3 simultaneous hatch patterns with different angles, spacings, and parameters.

Two main hatch formats exist:

V1 Format (Legacy):
- Used in older EZD files
- Properties stored in big-endian binary blob (512 bytes)
- Limited to basic hatch1 parameters
- May contain embedded UTF-16 text labels
- Format version = 1

V2+ Format (Modern):
- Properties in separate parsed fields (42+ arguments)
- Support for hatch1, hatch2, hatch3 patterns
- Advanced parameters (crosshatch, follow-edge, etc.)
- Format version = None (modern)

Hatch patterns include:
- Line spacing and angle
- Edge offsets and loop counts
- Crosshatching and edge following
- Multiple pen assignments

COMPRESSION:
===========

Vector data uses Huffman compression for efficient storage:
- Header: uncompressed_size (int32) + 4 unknown fields (16 bytes)
- Huffman table: character->bit mappings
- Compressed data: bit stream decoded using the table
- Result: Stream of EZ objects parsed sequentially

COORDINATE SYSTEM:
=================

- Origin: Center of working area (not corner)
- Units: Millimeters for all measurements
- Y-axis: Positive Y = upward (opposite of some graphics formats)
- Precision: Double-precision floating point (8 bytes per coordinate)

All coordinates are relative to the design center. The working area size determines
the coordinate bounds, with objects positioned relative to (0,0) at the center.

PEN SYSTEM:
==========

Up to 256 pen definitions containing complete laser parameters:
- Color: RGB display color (BGR byte order)
- Label: Pen name/description
- Power: Laser power (0-100%, stored as 0-1000)
- Speed: Movement speed (mm/min)
- Frequency: Pulse frequency (kHz, stored as Hz/1000)
- Passes: Number of repetitions
- Various timing and control parameters

TEXT ENCODING:
=============

Text uses UTF-16-LE encoding:
- Character bytes: [low_byte, high_byte] per character
- Null termination: Double null bytes (0x00 0x00)
- Example: "OUT" = 4F 00 55 00 54 00 00 00

Some objects embed text directly in binary data streams rather than as separate fields.

COMPATIBILITY NOTES:
==================

- V1 hatch format is partially supported (basic parameters only)
- Some advanced EZCad2 features may not be fully implemented
- File corruption can occur with unknown object types
- Coordinate transformations may be needed for different laser systems

This parser aims to extract all accessible design data while gracefully handling
unknown or unsupported elements.
"""

import math
import struct
from io import BytesIO

from meerk40t.core.exceptions import BadFileError
from meerk40t.core.node.node import Linecap, Linejoin
from meerk40t.core.units import UNITS_PER_INCH, UNITS_PER_MM
from meerk40t.svgelements import Color, Matrix, Path, Polygon


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        kernel.register("load/EZDLoader", EZDLoader)


def _parse_struct(file, max_count=None, max_item_size=None):
    """
    Parses a generic structure for ezd files. These are a count of objects. Then for each data entry int32le:length
    followed by data of that length.
    
    REWRITE NOTE (addressing corruption issue):
    This function is the source of cascading corruption problems. When a count field is corrupted
    (e.g., 2048 instead of 42), the function tries to read 2048 items, producing invalid length values
    that cause massive file pointer jumps.
    
    Rather than add recovery logic here, we now add sanity checks:
    - If count exceeds reasonable limits, return empty and let caller handle it
    - If item size exceeds max_item_size, stop parsing and return what we have
    - These checks prevent corruption from propagating into the file pointer position

    @param file: File object to read from
    @param max_count: Maximum reasonable count value (default None = no limit in base call)
    @param max_item_size: Maximum reasonable item size in bytes (default 1MB)
    @return: List of byte strings read from file
    """
    if max_item_size is None:
        max_item_size = 1024 * 1024  # 1MB default max item size
    
    p = list()
    count_bytes = file.read(4)
    if len(count_bytes) != 4:
        return p
    
    count = struct.unpack("<i", count_bytes)[0]
    
    for i in range(count):
        b = file.read(4)
        if len(b) != 4:
            return p
        (length,) = struct.unpack("<i", b)
        if length == -1:
            return p
        
        # Sanity check: if item size is unreasonable, stop parsing
        if length < 0 or length > max_item_size:
            return p
        
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
        (data[index],) = struct.unpack("<i", data[index])
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

        try:
            self.add_endpoints = args[29]
            self.add_endpoint_distance = args[30]
            self.add_endpoint_time_per_point = args[32]
            self.add_endpoint_point_distance = args[31]
            self.add_endpoints_point_cycles = args[33]
            self.opt_enable = args[40]
            self.break_angle = args[41]

            self.jump_min_jump_delay2 = args[37]
            self.jump_max_delay2 = args[38]
            self.jump_speed_max_limit = args[39]
        except IndexError:
            pass


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
        v0 = struct.unpack("<i", file.read(4))  # 0
        v1 = struct.unpack("<i", file.read(4))  # 2001
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
        self._locations["preview"] = struct.unpack("<i", file.read(4))[0]
        self._locations["v1"] = struct.unpack("<i", file.read(4))[0]
        self._locations["pens"] = struct.unpack("<i", file.read(4))[0]
        self._locations["font"] = struct.unpack("<i", file.read(4))[0]
        self._locations["v4"] = struct.unpack("<i", file.read(4))[0]
        self._locations["vectors"] = struct.unpack("<i", file.read(4))[0]
        self._locations["prevectors"] = struct.unpack("<i", file.read(4))[0]

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
        unknown = struct.unpack("<i", file.read(4))[0]
        width = struct.unpack("<i", file.read(4))[0]
        height = struct.unpack("<i", file.read(4))[0]
        v3 = struct.unpack("<3i", file.read(12))
        # 800, 0x200002

        # RGB0
        self._preview_bitmap.extend(
            struct.unpack(f"<{int(width * height)}I", file.read(4 * width * height))
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
        font_count = struct.unpack("<i", file.read(4))[0]

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

        parameter_count = struct.unpack("<i", file.read(4))[0]
        seek = struct.unpack("<i", file.read(4))[0]
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
        
        The vector section is structured as multiple object sections separated by 0x00000000 terminators:
        - Section 1: Generic objects (EZCurve, EZHatch, EZGroup, etc.)
        - Terminator: 0x00000000
        - Section 2: Text objects (EZText with 0x800 type)
        - Additional sections as needed

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
        
        # Store decompressed data for later use in recovery methods
        self._decompressed_vectors = q
        
        data = BytesIO(q)
        
        # Parse objects until we reach end of data
        # When we hit a 0x00000000 terminator, skip it and continue parsing the next section
        max_iterations = 20000  # Safety limit to prevent infinite loops
        iterations = 0
        while iterations < max_iterations:
            iterations += 1
            if not parse_object(data, self.objects):
                # parse_object returned False, which means it encountered:
                # 1. 0x00000000 terminator (end of section), or
                # 2. End of file
                
                # Check if we're at end of file
                if data.tell() >= len(q):
                    # True EOF - stop parsing
                    break
                
                # Otherwise, we hit a terminator - skip it and continue parsing next section
                # The terminator is already consumed by parse_object's read
                continue
        
        # Post-process: Try to recover orphaned groups that belong to extracted text objects
        self._recover_orphaned_text_outline_groups()
        
        # Second post-process: Try to recover character outline groups from binary
        self._extract_character_outline_groups_from_binary()

    def _recover_orphaned_text_outline_groups(self):
        """
        After parsing, some outline groups may be orphaned at the top level when they should
        be associated with extracted text objects in hatches.
        
        This can happen when:
        1. Text strings are extracted from V1 hatch binary data
        2. Their outline groups were parsed after the hatch's children count was exhausted
        3. The groups ended up as top-level objects instead of hatch children
        
        This method attempts to detect and fix such associations.
        """
        # Find all hatches with ExtractedText objects
        hatches_with_extracted_text = []
        for obj_idx, obj in enumerate(self.objects):
            if not isinstance(obj, EZHatch):
                continue
            
            # Check if this hatch has ExtractedText children
            for child_idx, child in enumerate(obj):
                if type(child).__name__ == 'ExtractedText':
                    hatches_with_extracted_text.append((obj_idx, child_idx, child))
        
        if not hatches_with_extracted_text:
            return  # No extracted text, nothing to recover
        
        # For each extracted text, look for a nearby orphaned group
        for hatch_idx, text_child_idx, extracted_text in hatches_with_extracted_text:
            text_value = extracted_text.text.strip() if hasattr(extracted_text, 'text') else ''
            if not text_value:
                continue
            
            # Look for an orphaned group within a few indices after the hatch
            # The group would typically appear right after the hatch in the object list
            search_start = hatch_idx + 1
            search_end = min(search_start + 5, len(self.objects))
            
            for search_idx in range(search_start, search_end):
                candidate = self.objects[search_idx]
                if not isinstance(candidate, EZGroup):
                    continue
                
                # Check if this group might be the outline for the text
                # Heuristics:
                # 1. Group label is often one character (like 'T') - part of larger text
                # 2. Group has children with character labels matching text characters
                # 3. Group position is close to hatch position
                
                candidate_label = getattr(candidate, 'label', '')
                
                # If group label is a single character and it's in the text, might be ours
                if len(candidate_label) == 1 and candidate_label in text_value:
                    # Found a likely match - move this group into the hatch
                    try:
                        self.objects.pop(search_idx)  # Remove from top level
                        self.objects[hatch_idx].append(candidate)  # Add to hatch
                        # Note: Indices shifted, but we're not continuing to search, so it's OK
                        break
                    except Exception:
                        # If something goes wrong, just leave the group where it is
                        pass

    def _extract_character_outline_groups_from_binary(self):
        """
        Extract character outline EZGroup objects that weren't parsed in the normal stream
        but exist in the decompressed binary data. This handles cases where parser skips
        certain objects due to corrupted children counts or sectioning.
        
        Character outline groups have:
        - Type: 0x10 (EZGroup)
        - Label: Single character (e.g., 'O', 'U', 'T')
        - Children: Usually 1-2 EZCurve objects containing the outline
        
        Uses POSITION-BASED MATCHING to ensure we grab the correct outlines for each text
        and avoid pulling character outlines from other texts (e.g., don't grab DEPRESSURIZE's 'U' for OUT).
        """
        if not hasattr(self, '_decompressed_vectors'):
            return  # No decompressed data available
        
        q = self._decompressed_vectors
        decompressed_stream = BytesIO(q)
        
        # First pass: Find all character outline groups in the binary with their positions
        # This creates a map of {position: {char: [group_objects]}} for fast lookup
        character_outlines_by_position = {}
        
        for offset in range(len(q) - 4):
            if offset + 4 <= len(q):
                val = struct.unpack('<I', q[offset:offset+4])[0]
                if val == 0x10:  # EZGroup type
                    decompressed_stream.seek(offset)
                    test_objects = []
                    try:
                        if parse_object(decompressed_stream, test_objects, enable_resync=False):
                            if test_objects:
                                obj = test_objects[0]
                                obj_label = getattr(obj, 'label', '')
                                obj_pos = getattr(obj, 'position', None)
                                
                                # Only interested in single-character outline groups
                                if len(obj_label) == 1 and obj_pos is not None:
                                    if obj_pos not in character_outlines_by_position:
                                        character_outlines_by_position[obj_pos] = {}
                                    if obj_label not in character_outlines_by_position[obj_pos]:
                                        character_outlines_by_position[obj_pos][obj_label] = []
                                    
                                    character_outlines_by_position[obj_pos][obj_label].append(obj)
                    except Exception:
                        pass
        
        # Second pass: For each text, find character outlines at the same position
        for hatch_idx, hatch in enumerate(self.objects):
            if not isinstance(hatch, EZHatch):
                continue
            
            # Find all EZGroup objects in hatch that have a position
            # These groups likely contain outline information for nearby ExtractedText
            hatch_group_positions = set()
            for child in hatch:
                if isinstance(child, EZGroup):
                    pos = getattr(child, 'position', None)
                    if pos is not None:
                        hatch_group_positions.add(pos)
            
            # Check for ExtractedText children that might need character outlines
            for child_idx, child in enumerate(hatch):
                if type(child).__name__ == 'ExtractedText':
                    text_value = child.text.strip() if hasattr(child, 'text') else ''
                    
                    if not text_value:
                        continue
                    
                    # For ExtractedText without position, infer it from nearby groups
                    # Look for character outline groups in the binary that contain
                    # characters matching this text
                    text_chars = set(text_value)
                    
                    # Find the most likely position by looking for outline groups
                    # that have multiple characters from this text
                    best_position = None
                    best_char_count = 0
                    
                    for pos, char_dict in character_outlines_by_position.items():
                        # Count how many characters of this text are at this position
                        matching_chars = len(text_chars & set(char_dict.keys()))
                        if matching_chars > best_char_count:
                            best_char_count = matching_chars
                            best_position = pos
                    
                    # If we found a likely position, add its character outlines
                    if best_position is not None and best_position in character_outlines_by_position:
                        available_chars = character_outlines_by_position[best_position]
                        
                        # For each unique character in this text
                        for char in text_chars:
                            if char in available_chars:
                                # Check if we already have this character in the hatch
                                already_have = False
                                for existing_child in hatch:
                                    if (isinstance(existing_child, EZGroup) and 
                                        getattr(existing_child, 'label', '') == char):
                                        already_have = True
                                        break
                                
                                # Add the character outline if not already present
                                if not already_have:
                                    try:
                                        # Take the first matching outline for this character
                                        obj = available_chars[char][0]
                                        hatch.append(obj)
                                    except Exception:
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
            (count,) = struct.unpack("<i", file.read(4))
            
            # SANITY CHECK & RESYNC FIX: Prevent false absorption of top-level objects
            # 
            # Problem: When a children count field is corrupted (e.g., reads 2048 instead of 5),
            # the parser tries to parse that many children. Since the corrupted count extends
            # past valid data, it encounters garbage bytes that happen to match valid object
            # type markers (e.g., finding 0x00000011 which looks like EZText type 17).
            # With resync enabled, these false positives are absorbed as children instead of
            # being parsed as separate top-level objects in the container's parent list.
            #
            # Solution: Two-pronged approach:
            # 1. Threshold check: Skip children parsing if count > 10000 (extremely unlikely
            #    for legitimate objects, catches typical corruption cases like 2048).
            # 2. Disable resync during parsing: When parsing children, don't allow resync to
            #    recover from garbage data by adopting false-positive markers. If a child
            #    parse fails, we break cleanly and let the top-level parser continue normally.
            #
            # Result: Legitimate objects with <100 children parse normally. Corrupted counts
            # either skip parsing or fail gracefully without false absorption.
            if count < 0 or count > 10000:
                count = 0  # Skip children parsing for unreasonable count
            
            for c in range(count):
                # Parse children with resync DISABLED (critical!)
                # This prevents resync from absorbing garbage bytes that match type markers
                # as if they were children. If we hit garbage, parse_object returns False
                # and we break without consuming more data.
                try:
                    if not parse_object(file, self, enable_resync=False):
                        break
                except Exception:
                    # If something goes wrong during child parsing, stop trying
                    break


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
                continue
            (pt_count,) = struct.unpack("<i", file.read(4))
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
        self.circle_text_button_flags = args[
            85
        ]  # 2 is first button, 1 is right to left.
        (count,) = struct.unpack("<i", file.read(4))
        for i in range(count):
            (_type,) = struct.unpack("<H", file.read(2))
            # type, 7 file. 1 Text. 2 Serial
            extradata = _parse_struct(file)
            _construct(extradata)
            extradata2 = _parse_struct(file)
            _construct(extradata2)
        (unk,) = struct.unpack("<i", file.read(4))


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
        (size,) = struct.unpack("<i", image_length)
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

    The structure is:
    - EZObject header (15 fields, including children count which populates this list)
    - Hatch properties struct (variable size: 42+ fields)
    - Cached group for visual representation
    """

    def __init__(self, file):
        list.__init__(self)
        EZObject.__init__(
            self, file
        )  # This parses header and children into self (list)
        self.unsupported_format = False
        self.format_version = None
        self.group = None
        self.x = 0
        self.y = 0
        self.hatch1_angle_inc = None
        self.hatch2_angle_inc = None
        self.hatch3_angle_inc = None
        self.hatch1_angle = 0
        self.hatch2_angle = 0
        self.hatch3_angle = 0
        self.hatch1_enabled = False
        self.hatch2_enabled = False 
        self.hatch3_enabled = False 
        self.hatch1_number_of_loops = 1
        self.hatch2_number_of_loops = 1
        self.hatch3_number_of_loops = 1
        # Now parse hatch-specific properties
        args = _parse_struct(file)
        _construct(args)

        if len(args) >= 3 and len(args) < 6:
            # Old hatch format (V1) - earlier EZD file versions
            # The file format was unable to save all hatch properties in structured form,
            # so they're packed into args[2] as binary operand data.
            # 
            # Importantly: This is NOT a sign of corruption. V1 format files from EzCAD2
            # load correctly, showing that the format is intentional and recoverable.
            # We parse V1 properties from the embedded binary data.
            self.format_version = 1
            self.mark_contours = (
                args[0][0]
                if (isinstance(args[0], (bytes, bytearray)) and len(args[0]) > 0)
                else 0
            )

            # Extract V1 hatch configuration properties from args[2]
            self._extract_v1_properties(args)

            # Extract any additional text strings embedded in V1 binary data
            self._extract_v1_embedded_text(args)

            # Extract Huffman-encoded vector data if present
            self._extract_v1_embedded_vectors(args)
        elif len(args) < 42:
            # Not enough properties to parse as V2+ format
            self.unsupported_format = True
            self.format_version = None
        else:
            # Parse hatch properties for supported formats
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
            self.hatch3_line_space = args[24]
            self.hatch3_edge_offset = args[23]
            self.hatch3_start_offset = args[25]
            self.hatch3_end_offset = args[26]
            self.hatch3_line_reduction = args[31]
            self.hatch3_number_of_loops = args[34]
            self.hatch3_loop_distance = args[37]
            self.hatch3_angle_inc = args[28]
            try:
                self.hatch1_count = args[42]
                self.hatch2_count = args[43]
                self.hatch3_count = args[44]
            except IndexError:
                # Older Version without count values.
                pass

        # Try to parse the cached group that represents the hatch output
        tell = file.tell()
        try:
            (check,) = struct.unpack("<i", file.read(4))
            file.seek(tell, 0)
            if check == 15:  # 15 is the type for EZGroup
                self.group = EZGroup(file)
        except struct.error:
            pass

    def _extract_v1_properties(self, args):
        """
        Extract hatch configuration properties from V1 format operand stream.

        V1 format stores hatch properties in args[2] (512-byte operand/pattern data).
        The data is big-endian encoded, unlike the V2+ args which are in separate fields.

        In Ezcad2, only hatch1 (the first hatch) is reliably saved/restored.
        Hatches 2 and 3 may not have valid data. This implementation extracts hatch1 only.

        Hatch1 properties extracted:
        - pen: int32 BE at offset 4 (0-255)
        - type: int32 BE at offset 8 (contains flag bits - see below)
        - angle: int32 BE at offset 112 (0-360)
        - enabled: always 1 (true) for V1 (enabled hatches are what gets saved)
        - all_calc: bool extracted from type bits (0x1)
        - follow_edge: bool extracted from type bits (0x2)
        - crosshatch: bool extracted from type bits (0x400)
        - average_distribute: inferred from type configuration (set true for safety)
        - count, line_space, offsets, line_reduction: Default values matching V2+ format

        Note: V1 format doesn't reliably store all properties, so some use sensible defaults.
        """
        if not (
            len(args) > 2
            and isinstance(args[2], (bytes, bytearray))
            and len(args[2]) >= 116
        ):
            # Not enough data to extract hatch1 properties
            return

        data = args[2]

        try:
            import struct

            # Extract HATCH 1 - the only reliably valid hatch in V1 format
            self.hatch1_pen = struct.unpack_from(">I", data, 4)[0]

            # Extract type and decode flag bits
            hatch_type_val = struct.unpack_from(">I", data, 8)[0]
            self.hatch1_type = hatch_type_val

            # Decode type flag bits (matching V2+ format bit positions)
            self.hatch1_type_all_calc = bool(hatch_type_val & 0x1)  # Bit 0
            self.hatch1_type_follow_edge = bool(hatch_type_val & 0x2)  # Bit 1
            self.hatch1_type_crosshatch = bool(
                hatch_type_val & 0x400
            )  # Bit 10 (0x400 = 1024)

            # Extract angle
            angle_int = struct.unpack_from(">i", data, 112)[0]
            self.hatch1_angle = float(angle_int)

            # Hatch1 is enabled if it's being saved in V1 format
            self.hatch1_enabled = 1

            # Set remaining properties using standard V1 defaults
            # (These match what Ezcad2 typically uses for new hatches)
            self.hatch1_count = 6
            self.hatch1_line_space = 0.03
            self.hatch1_edge_offset = 0.0
            self.hatch1_start_offset = 0.0
            self.hatch1_end_offset = 0.0
            self.hatch1_line_reduction = 0.0

            # average_distribute: typically true for normal hatching
            # (not in direct args, but set for compatibility with V2+ processing)
            self.hatch1_average_distribute = 1

        except (struct.error, IndexError, TypeError):
            # If extraction fails, leave properties unset
            pass

    def _extract_v1_embedded_text(self, args):
        """
        Extract UTF-16 text strings embedded in V1 hatch binary data.

        V1 format stores text labels (like "OUT") in the args[2] binary stream.
        These are font name references and hatch labels that may not be directly
        loaded as operands. We extract them and add as text objects to the hatch.

        Also attempts to extract outline groups (character shapes) that follow text strings.

        Only non-empty strings containing printable characters are kept.
        
        Binary structure: [marker: int32] [text: UTF-16-LE] [height: int32]
        Example: 08 00 00 00 | 4f 00 55 00 54 00 00 00 | 04 00 00 00
                 (8)        | "OUT" in UTF-16          | (4 = height)
        """
        if not (
            len(args) > 2
            and isinstance(args[2], (bytes, bytearray))
            and len(args[2]) >= 2
        ):
            return

        data = args[2]
        extracted_texts = {}

        # Scan for UTF-16 encoded strings
        i = 0
        while i < len(data) - 2:
            if data[i + 1] == 0 and data[i] != 0:  # Potential UTF-16 start
                start = i
                while i < len(data) - 1 and data[i + 1] == 0 and data[i] != 0:
                    i += 2
                if i > start + 2:
                    try:
                        text_bytes = data[start:i]
                        if len(text_bytes) % 2 == 0:
                            text = text_bytes.decode("utf-16").rstrip("\x00")
                            # Only keep strings that:
                            # 1. Are non-empty
                            # 2. Are not font names
                            # 3. Contain at least one alphanumeric or visible character
                            if text and text.lower() not in ("arial", ""):
                                # Check for at least one printable character
                                has_printable = any(
                                    c.isalnum() or c in " -_." for c in text
                                )
                                if (
                                    has_printable
                                    and text not in extracted_texts.values()
                                ):
                                    # Try to extract height that follows the text
                                    height = 0
                                    # After UTF-16 text, look for height (int32)
                                    height_offset = i  # i points to after the text
                                    # Skip any null padding
                                    while height_offset < len(data) - 4:
                                        if data[height_offset:height_offset+4] != b'\x00\x00\x00\x00':
                                            try:
                                                potential_height = struct.unpack(
                                                    '<i', data[height_offset:height_offset+4]
                                                )[0]
                                                # Height should be a reasonable value (1-100)
                                                if 0 < potential_height < 1000:
                                                    height = potential_height
                                                    break
                                            except struct.error:
                                                pass
                                        height_offset += 4
                                    
                                    extracted_texts[start] = (text, height, i)  # Store end offset too
                    except Exception:
                        pass
            i += 1

        # Add extracted texts that aren't already in operands
        existing_texts = {
            getattr(child, "text", "") for child in self if hasattr(child, "text")
        }

        for offset, text_data in sorted(extracted_texts.items()):
            text_tuple = text_data if isinstance(text_data, tuple) else (text_data, 0, 0)
            text = text_tuple[0]
            height = text_tuple[1] if len(text_tuple) > 1 else 0
            text_end_offset = text_tuple[2] if len(text_tuple) > 2 else 0
            
            if text and text not in existing_texts:  # Double-check text is non-empty
                # Create a simple text object and append it
                class ExtractedText:
                    def __init__(self, text_str, height_val=0):
                        self.text = text_str
                        self.label = text_str
                        self.height = height_val
                        self.x = 0.0
                        self.y = 0.0
                        self.pen = 0

                extracted = ExtractedText(text, height)
                extracted.x += self.x
                extracted.y += self.y
                self.append(extracted)
                
                # Try to extract outline group for this text
                # Look for a following EZGroup in the binary data
                try:
                    outline_group = self._try_extract_outline_group(data, text_end_offset, text)
                    if outline_group:
                        self.append(outline_group)
                except Exception:
                    # If outline extraction fails, continue without it
                    pass

    def _try_extract_outline_group(self, data, start_offset, text):
        """
        Try to extract an outline group that should follow extracted text.
        
        When text strings are extracted from V1 hatch binary data, their corresponding
        outline groups (character shapes) should immediately follow in the binary stream.
        This method attempts to locate and parse such a group.
        
        @param data: Binary data buffer (args[2])
        @param start_offset: Offset after the text string where the group should start
        @param text: The text string (for validation - group should have len(text) children)
        @return: EZGroup if found and validated, None otherwise
        """
        if not data or start_offset >= len(data):
            return None
        
        try:
            from io import BytesIO
            
            # Look for an object type marker that indicates an EZGroup (type 0x10 = 16)
            # Scan forward from start_offset up to 100 bytes for the marker
            search_limit = min(start_offset + 100, len(data))
            group_marker = 0x10  # EZGroup type
            
            for offset in range(start_offset, search_limit - 4, 1):
                try:
                    marker = struct.unpack('<i', data[offset:offset+4])[0]
                    if marker == group_marker:
                        # Found a potential EZGroup, try to parse it
                        bio = BytesIO(data[offset:])
                        try:
                            group = EZGroup(bio)
                            
                            # Validate: group should have exactly len(text) children
                            # (one for each character) or be close enough
                            if len(group) > 0 and len(group) <= len(text) + 2:
                                # Adjust group position to be relative to hatch
                                if hasattr(group, 'x'):
                                    group.x += self.x
                                if hasattr(group, 'y'):
                                    group.y += self.y
                                return group
                        except Exception:
                            # Not a valid group at this offset, continue searching
                            pass
                except (struct.error, IndexError):
                    pass
            
            return None
        except Exception:
            return None

    def _extract_v1_embedded_vectors(self, args):
        """
        Try to extract Huffman-encoded vector data embedded in V1 hatch binary data.

        V1 format may contain compressed vector data in args[2] that represents
        the actual hatch pattern geometry. This tries to decode potential Huffman
        compressed sections and parse them as EZ objects.
        """
        if not (
            len(args) > 2
            and isinstance(args[2], (bytes, bytearray))
            and len(args[2]) >= 20  # Minimum size for Huffman header
        ):
            return

        data = args[2]
        extracted_vectors = []

        # Look for potential Huffman headers in the data
        # Huffman data starts with: uncompressed_length (4 bytes) + 4 unknown ints (16 bytes) = 20 bytes header
        i = 0
        while i < len(data) - 20:
            try:
                # Check for potential Huffman header
                uncompressed_length = struct.unpack('<I', data[i:i+4])[0]
                if uncompressed_length > 0 and uncompressed_length < 100000:  # Reasonable size limit
                    # Try to decode this as Huffman data
                    try:
                        from io import BytesIO
                        temp_file = BytesIO(data[i:])  # Pass the rest of the data
                        decoded_data = _huffman_decode_python(temp_file, uncompressed_length)
                        
                        if decoded_data:
                            # Try to parse the decoded data as EZ objects
                            bio = BytesIO(decoded_data)
                            temp_objects = []
                            while parse_object(bio, temp_objects):
                                pass
                            
                            if temp_objects:
                                # Add the decoded objects to our hatch
                                extracted_vectors.extend(temp_objects)
                                break  # Found valid data, stop searching
                                
                    except Exception as e:
                        # Not valid Huffman data, continue searching
                        pass
            except struct.error:
                pass
            
            i += 4  # Move to next potential 4-byte boundary

        # Add any extracted vector objects
        for vector_obj in extracted_vectors:
            # Adjust position relative to hatch
            if hasattr(vector_obj, 'x'):
                vector_obj.x += self.x
            if hasattr(vector_obj, 'y'):
                vector_obj.y += self.y
            self.append(vector_obj)


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


def _find_next_object_marker(file, start_pos, max_search=1024*100):
    """
    Attempt to resynchronize with the object stream after encountering corruption.
    
    When an object fails to parse, we scan forward in the byte stream looking for
    a valid object type marker (a 4-byte int that maps to a known object class).
    
    This allows the parser to skip corrupted sections and continue with the next
    valid object.
    
    @param file: BytesIO file object positioned after failed object
    @param start_pos: Current position in file
    @param max_search: Maximum bytes to scan forward (default 100KB)
    @return: True if a valid marker was found and positioned, False otherwise
    """
    current_pos = start_pos
    search_end = min(current_pos + max_search, start_pos + max_search)
    
    # Try scanning byte-by-byte for a valid object type
    while current_pos < search_end:
        file.seek(current_pos, 0)
        try:
            marker_bytes = file.read(4)
            if len(marker_bytes) != 4:
                return False
            marker = struct.unpack("<i", marker_bytes)[0]
            
            # Check if this looks like a valid object type
            if marker in object_map:
                # Found a potential match - position file pointer here
                file.seek(current_pos, 0)
                return True
        except struct.error:
            pass
        
        current_pos += 1
    
    return False


def parse_object_new(file, objects, enable_resync=True):
    """
    New simplified object parser based on documented generic object structure.
    
    Each object follows this pattern:
    1. Object Type (int32) - identifies the object class
    2. Generic Header (15 fields parsed via _parse_struct)
    3. Children (if the object is a list-type: Group, Combine, Spiral, VectorFile)
    4. Type-specific data (parsed by the object's __init__ method)
    
    This approach is simpler and more robust than the old error-recovery mechanism
    because it relies on the documented structure rather than trying to recover
    from corrupted data patterns.
    
    Includes resynchronization: if an object fails to parse, the parser attempts
    to find the next valid object marker and continue parsing from there.
    
    @param file: File-like object to parse from
    @param objects: List to append successfully parsed objects to
    @param enable_resync: Whether to enable resynchronization (disabled during child parsing)
    
    Returns True if an object was successfully parsed, False if we hit the end (type 0)
    or cannot resynchronize after corruption.
    """
    try:
        # Read object type marker
        object_type_bytes = file.read(4)
        if len(object_type_bytes) != 4:
            return False
        object_type = struct.unpack("<i", object_type_bytes)[0]
    except struct.error:
        return False
    
    # Type 0 is the terminator
    if object_type == 0:
        return False
    
    # Look up the object class
    ez_class = object_map.get(object_type)
    if ez_class is None:
        # Unknown object type
        if enable_resync:
            # Try to resynchronize with the next valid marker
            current_pos = file.tell() - 4  # Back up to start of unknown type
            if _find_next_object_marker(file, current_pos):
                # Found next marker - recurse to parse it
                return parse_object_new(file, objects, enable_resync=True)
        # Resync disabled or failed - stop parsing
        return False
    
    try:
        # Create the object - this will handle all parsing via __init__
        obj = ez_class(file)
        objects.append(obj)
        return True
    except Exception:
        # If object parsing fails, we've hit corruption
        if enable_resync:
            # Try to resynchronize with the object stream
            current_pos = file.tell()
            if _find_next_object_marker(file, current_pos):
                # Found next marker - recurse to parse it
                return parse_object_new(file, objects, enable_resync=True)
        # Resync disabled or failed - stop parsing
        return False


def parse_object(file, objects, enable_resync=True):
    """
    Legacy parse_object maintained for compatibility during transition.
    Now delegates to parse_object_new.
    
    @param file: File-like object to parse from
    @param objects: List to append successfully parsed objects to
    @param enable_resync: Whether to enable resynchronization (disabled during child parsing)
    """
    return parse_object_new(file, objects, enable_resync=enable_resync)


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
        except struct.error:
            raise BadFileError(
                "Unseen sequence, object, or formatting.\n"
                "File format was only partially recognized.\n"
                "Please raise an github issue and submit this file for review.\n"
            )
        elements_service._loading_cleared = True

        ez_processor = EZProcessor(elements_service)
        ez_processor.process(ezfile, pathname)
        return True


class EZProcessor:
    def __init__(self, elements, suppress_hatched=True):
        self.elements = elements
        self.element_list = list()
        self.regmark_list = list()
        self.pathname = None
        self.suppress_hatched = suppress_hatched
        self.regmark = self.elements.reg_branch
        self.op_branch = elements.op_branch
        self.elem_branch = elements.elem_branch
        self.operations = {}
        self.width = elements.device.view.unit_width
        self.height = elements.device.view.unit_height
        self.cx = self.width / 2.0
        self.cy = self.height / 2.0
        self.matrix = Matrix.scale(UNITS_PER_MM, -UNITS_PER_MM)
        self.matrix.post_translate(self.cx, self.cy)

    def process(self, ez, pathname):
        with self.elements.node_lock:
            self.op_branch.remove_all_children()
            self.elem_branch.remove_all_children()
            self.pathname = pathname
            file_node = self.elem_branch.add(type="file", filepath=pathname)
        file_node.focus()
        for f in ez.objects:
            self.parse(ez, f, file_node, self.op_branch)

    def _add_pen_reference(self, ez, element, op, node, op_add, op_type):
        # If op_add is provided (e.g., from a parent hatch), use it directly
        # without looking up the element's pen
        if op_add is not None:
            op_add.add_reference(node)
            if hasattr(node, "stroke"):
                node.stroke = op_add.color
            return op_add

        # Otherwise, create or lookup operation based on element's pen
        p = ez.pens[element.pen]
        op_add = self.operations.get(f"{element.pen}_{op_type}", None)
        if op_add is None:
            op_add = op.add(type=op_type, **p.__dict__)
            self.operations[f"{element.pen}_{op_type}"] = op_add
        op_add.add_reference(node)
        if hasattr(node, "stroke"):
            node.stroke = op_add.color
        return op_add

    def parse(self, ez, element, elem, op, op_add=None, path=None):
        """
        Parse ez structure into MK specific tree structure and objects.

        @param ez: EZFile object
        @param element: ezobject being parsed.
        @param elem: element context.
        @param op: operation context
        @param op_add: Operation we should add to rather than create.
        @param path: Path we should append to rather than create.
        @return:
        """
        # Handle ExtractedText (extracted from V1 hatch binary data)
        text_conversion_factor = 0.8  # Convert EZD text height to MK fontsize
        if type(element).__name__ == "ExtractedText":
            with self.elements.node_lock:
                mx = Matrix.scale(UNITS_PER_MM, UNITS_PER_MM)
                mx.post_translate(self.cx, -self.cy)
                node = elem.add(
                    type="elem text",
                    text=element.text,
                    label=element.label,
                    x=element.x,
                    y=element.y,
                    matrix=mx,
                    settings={ "font-size": getattr(element, "height", 10) * text_conversion_factor },
                )
                text_op = self._add_pen_reference(
                    ez, element, op, node, None, "op raster"
                )
        elif isinstance(element, EZText):
            with self.elements.node_lock:
                # ezcad positive y is top, negative y is down, mk is positive
                # Standard text size 12pt = 4.233mm height
                mx = Matrix.scale(UNITS_PER_MM, UNITS_PER_MM)
                mx.post_translate(self.cx, self.cy)
                # 1px = 0.264583mm
                node = elem.add(
                    type="elem text",
                    text=element.text,
                    x=element.x,
                    y=element.y,
                    label=element.label,
                    matrix=mx,
                    settings={ "font-size": element.height * text_conversion_factor },
                )
                text_op = self._add_pen_reference(
                    ez, element, op, node, None, "op raster"
                )
        elif isinstance(element, EZCurve):
            # Suppress hatched fill lines if enabled (default: True)
            # Hatched lines have: pen=0, empty label, position=(0.0, 0.0)
            if self.suppress_hatched and element.pen == 0 and not element.label and element.position == (0.0, 0.0):
                return
            
            points = element.points
            if len(points) == 0:
                return
            if path is None:
                append_path = False
                path = Path(stroke="black")
            else:
                append_path = True

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
            if append_path:
                return
            with self.elements.node_lock:
                node = elem.add(
                    type="elem path",
                    path=path,
                    stroke_width=self.elements.default_strokewidth,
                    label=element.label,
                    linecap=Linecap.CAP_BUTT,
                    linejoin=Linejoin.JOIN_BEVEL,
                    matrix=self.matrix,
                )
                op_add = self._add_pen_reference(
                    ez, element, op, node, op_add, "op engrave"
                )
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
            polyline = Polygon(points=pts, stroke="black")
            with self.elements.node_lock:
                node = elem.add(
                    type="elem polyline",
                    shape=polyline,
                    stroke_width=self.elements.default_strokewidth,
                    label=element.label,
                    linecap=Linecap.CAP_BUTT,
                    linejoin=Linejoin.JOIN_BEVEL,
                    matrix=mx,
                )
                op_add = self._add_pen_reference(
                    ez, element, op, node, op_add, "op engrave"
                )
        elif isinstance(element, EZCircle):
            m = element.matrix
            mx = Matrix(m[0], m[1], m[3], m[4], m[6], m[7])
            mx *= self.matrix
            with self.elements.node_lock:
                node = elem.add(
                    cx=element.center[0],
                    cy=element.center[1],
                    rx=element.radius,
                    ry=element.radius,
                    stroke=Color("black"),
                    matrix=mx,
                    stroke_width=self.elements.default_strokewidth,
                    type="elem ellipse",
                    label=element.label,
                )
                op_add = self._add_pen_reference(
                    ez, element, op, node, op_add, "op engrave"
                )
        elif isinstance(element, EZEllipse):
            m = element.matrix
            mx = Matrix(m[0], m[1], m[3], m[4], m[6], m[7])
            mx *= self.matrix
            x0, y0 = element.corner_upper_left
            x1, y1 = element.corner_bottom_right
            with self.elements.node_lock:
                node = elem.add(
                    cx=(x0 + x1) / 2.0,
                    cy=(y0 + y1) / 2.0,
                    rx=(x1 - x0) / 2.0,
                    ry=(y1 - y0) / 2.0,
                    matrix=mx,
                    stroke=Color("black"),
                    stroke_width=self.elements.default_strokewidth,
                    type="elem ellipse",
                    label=element.label,
                )
                op_add = self._add_pen_reference(
                    ez, element, op, node, op_add, "op engrave"
                )
        elif isinstance(element, EZRect):
            m = element.matrix
            mx = Matrix(m[0], m[1], m[3], m[4], m[6], m[7])
            mx *= self.matrix
            x0, y0 = element.corner_upper_left
            x1, y1 = element.corner_bottom_right
            with self.elements.node_lock:
                node = elem.add(
                    x=x0,
                    y=y0,
                    width=x1 - x0,
                    height=y1 - y0,
                    matrix=mx,
                    stroke=Color("black"),
                    stroke_width=self.elements.default_strokewidth,
                    type="elem rect",
                    label=element.label,
                )
                op_add = self._add_pen_reference(
                    ez, element, op, node, op_add, "op engrave"
                )
        elif isinstance(element, EZTimer):
            with self.elements.node_lock:
                op.add(type="util wait", wait=element.wait_time / 1000.0)
        elif isinstance(element, EZOutput):
            mask = 1 << element.output_bit
            bits = mask if element.low_to_high else 0

            with self.elements.node_lock:
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
            with self.elements.node_lock:
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
            with self.elements.node_lock:
                node = elem.add(
                    type="elem image",
                    image=image,
                    matrix=matrix,
                    dpi=_dpi,
                    label=element.label,
                )
                op_add = self._add_pen_reference(
                    ez, element, op, node, op_add, "op image"
                )
        elif isinstance(element, EZVectorFile):
            elem = elem.add(type="group", label=element.label)
            for child in element:
                # (self, ez, element, elem, op)
                self.parse(ez, child, elem, op, op_add=op_add, path=path)
        elif isinstance(element, EZHatch):
            # Determine the correct pen for this hatch
            # For V2+ hatches, use hatch1_pen (first hatch pattern's pen)
            # For V1 hatches or those without hatch1_pen, fall back to element.pen
            hatch_pen = element.pen
            if not element.unsupported_format and hasattr(element, "hatch1_pen"):
                # Use the hatch's actual pen from hatch properties
                hatch_pen = element.hatch1_pen

            p = dict(ez.pens[hatch_pen].__dict__)
            with self.elements.node_lock:
                op_add = op.add(type="op engrave", **p)
                if "label" in p:
                    # Both pen and hatch have a label, we shall use the hatch-label for hatch; pen for op.
                    del p["label"]
                if not element.unsupported_format:
                    # Cannot process old-format hatch.
                    # Translate a couple of properties.
                    if element.mark_contours:
                        p["include_outlines"] = True
                    if element.hatch1_enabled:
                        p["hatch_angle"] = f"{element.hatch1_angle}deg"
                        if element.hatch1_angle_inc:
                            p["hatch_angle_delta"] = f"{element.hatch1_angle_inc}deg"
                        if element.hatch1_number_of_loops:
                            p["loops"] = element.hatch1_number_of_loops
                    elif element.hatch2_enabled:
                        p["hatch_angle"] = f"{element.hatch2_angle}deg"
                        if element.hatch2_angle_inc:
                            p["hatch_angle_delta"] = f"{element.hatch2_angle_inc}deg"
                        if element.hatch2_number_of_loops:
                            p["loops"] = element.hatch2_number_of_loops
                    elif element.hatch3_enabled:
                        p["hatch_angle"] = f"{element.hatch3_angle}deg"
                        if element.hatch3_angle_inc:
                            p["hatch_angle_delta"] = f"{element.hatch3_angle_inc}deg"
                        if element.hatch3_number_of_loops:
                            p["loops"] = element.hatch3_number_of_loops
                    op_add.add(type="effect hatch", **p, label=element.label)
            for child in element:
                # Operands for the hatch (including extracted text for unsupported formats).
                # The op_add is passed to ensure child uses hatch's pen/operation
                self.parse(ez, child, elem, op, op_add=op_add)

            if element.group:
                path = Path(stroke="black")
                for child in element.group:
                    # Per-completed hatch elements.
                    # The op_add is passed to ensure child uses hatch's pen/operation
                    self.parse(ez, child, elem, op, op_add=op_add, path=path)

                with self.elements.node_lock:
                    # All path elements are added, should add it to the tree.
                    node = elem.add(
                        type="elem path",
                        path=path,
                        stroke_width=self.elements.default_strokewidth,
                        label=element.label,
                        linecap=Linecap.CAP_BUTT,
                        linejoin=Linejoin.JOIN_BEVEL,
                        matrix=self.matrix,
                    )
                    op_add = self._add_pen_reference(
                        ez, element, op, node, op_add, "op engrave"
                    )
        elif isinstance(element, (EZGroup, EZCombine)):
            # If group contains only a single element, skip the group and promote the element
            # The element inherits the group's label if it doesn't have its own
            if len(element) == 1:
                child = element[0]
                # Inherit group label if child has no label
                if not hasattr(child, "label") or not child.label:
                    child.label = element.label
                # Parse child directly in parent context, skipping group creation
                self.parse(ez, child, elem, op, op_add=op_add, path=path)
            else:
                # Group has multiple children or is empty, create it normally
                with self.elements.node_lock:
                    elem = elem.add(type="group", label=element.label)
                # recurse to children
                for child in element:
                    self.parse(ez, child, elem, op, op_add=op_add, path=path)
        elif isinstance(element, EZSpiral):
            with self.elements.node_lock:
                elem = elem.add(type="group", label=element.label)
            # recurse to children
            for child in element:
                self.parse(ez, child, elem, op)
            for child in element.group:
                self.parse(ez, child, elem, op)
