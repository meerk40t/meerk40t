"""
Moshiboard Builder

Builder for Moshiboard command data output information. Allows interactions through simple commands to export the
required data to run a Moshiboard.
"""
import struct

swizzle_table = [
    [
        b"\x00",
        b"\x01",
        b"\x40",
        b"\x03",
        b"\x10",
        b"\x21",
        b"\x50",
        b"\x23",
        b"\x04",
        b"\x09",
        b"\x44",
        b"\x0b",
        b"\x14",
        b"\x29",
        b"\x54",
        b"\x2b",
    ],
    [
        b"\x08",
        b"\x11",
        b"\x48",
        b"\x13",
        b"\x18",
        b"\x31",
        b"\x58",
        b"\x33",
        b"\x0c",
        b"\x19",
        b"\x4c",
        b"\x1b",
        b"\x1c",
        b"\x39",
        b"\x5c",
        b"\x3b",
    ],
    [
        b"\x80",
        b"\x05",
        b"\xc0",
        b"\x07",
        b"\x90",
        b"\x25",
        b"\xd0",
        b"\x27",
        b"\x84",
        b"\x0d",
        b"\xc4",
        b"\x0f",
        b"\x94",
        b"\x2d",
        b"\xd4",
        b"\x2f",
    ],
    [
        b"\x88",
        b"\x15",
        b"\xc8",
        b"\x17",
        b"\x98",
        b"\x35",
        b"\xd8",
        b"\x37",
        b"\x8c",
        b"\x1d",
        b"\xcc",
        b"\x1f",
        b"\x9c",
        b"\x3d",
        b"\xdc",
        b"\x3f",
    ],
    [
        b"\x02",
        b"\x41",
        b"\x42",
        b"\x43",
        b"\x12",
        b"\x61",
        b"\x52",
        b"\x63",
        b"\x06",
        b"\x49",
        b"\x46",
        b"\x4b",
        b"\x16",
        b"\x69",
        b"\x56",
        b"\x6b",
    ],
    [
        b"\x0a",
        b"\x51",
        b"\x4a",
        b"\x53",
        b"\x1a",
        b"\x71",
        b"\x5a",
        b"\x73",
        b"\x0e",
        b"\x59",
        b"\x4e",
        b"\x5b",
        b"\x1e",
        b"\x79",
        b"\x5e",
        b"\x7b",
    ],
    [
        b"\x82",
        b"\x45",
        b"\xc2",
        b"\x47",
        b"\x92",
        b"\x65",
        b"\xd2",
        b"\x67",
        b"\x86",
        b"\x4d",
        b"\xc6",
        b"\x4f",
        b"\x96",
        b"\x6d",
        b"\xd6",
        b"\x6f",
    ],
    [
        b"\x8a",
        b"\x55",
        b"\xca",
        b"\x57",
        b"\x9a",
        b"\x75",
        b"\xda",
        b"\x77",
        b"\x8e",
        b"\x5d",
        b"\xce",
        b"\x5f",
        b"\x9e",
        b"\x7d",
        b"\xde",
        b"\x7f",
    ],
    [
        b"\x20",
        b"\x81",
        b"\x60",
        b"\x83",
        b"\x30",
        b"\xa1",
        b"\x70",
        b"\xa3",
        b"\x24",
        b"\x89",
        b"\x64",
        b"\x8b",
        b"\x34",
        b"\xa9",
        b"\x74",
        b"\xab",
    ],
    [
        b"\x28",
        b"\x91",
        b"\x68",
        b"\x93",
        b"\x38",
        b"\xb1",
        b"\x78",
        b"\xb3",
        b"\x2c",
        b"\x99",
        b"\x6c",
        b"\x9b",
        b"\x3c",
        b"\xb9",
        b"\x7c",
        b"\xbb",
    ],
    [
        b"\xa0",
        b"\x85",
        b"\xe0",
        b"\x87",
        b"\xb0",
        b"\xa5",
        b"\xf0",
        b"\xa7",
        b"\xa4",
        b"\x8d",
        b"\xe4",
        b"\x8f",
        b"\xb4",
        b"\xad",
        b"\xf4",
        b"\xaf",
    ],
    [
        b"\xa8",
        b"\x95",
        b"\xe8",
        b"\x97",
        b"\xb8",
        b"\xb5",
        b"\xf8",
        b"\xb7",
        b"\xac",
        b"\x9d",
        b"\xec",
        b"\x9f",
        b"\xbc",
        b"\xbd",
        b"\xfc",
        b"\xbf",
    ],
    [
        b"\x22",
        b"\xc1",
        b"\x62",
        b"\xc3",
        b"\x32",
        b"\xe1",
        b"\x72",
        b"\xe3",
        b"\x26",
        b"\xc9",
        b"\x66",
        b"\xcb",
        b"\x36",
        b"\xe9",
        b"\x76",
        b"\xeb",
    ],
    [
        b"\x2a",
        b"\xd1",
        b"\x6a",
        b"\xd3",
        b"\x3a",
        b"\xf1",
        b"\x7a",
        b"\xf3",
        b"\x2e",
        b"\xd9",
        b"\x6e",
        b"\xdb",
        b"\x3e",
        b"\xf9",
        b"\x7e",
        b"\xfb",
    ],
    [
        b"\xa2",
        b"\xc5",
        b"\xe2",
        b"\xc7",
        b"\xb2",
        b"\xe5",
        b"\xf2",
        b"\xe7",
        b"\xa6",
        b"\xcd",
        b"\xe6",
        b"\xcf",
        b"\xb6",
        b"\xed",
        b"\xf6",
        b"\xef",
    ],
    [
        b"\xaa",
        b"\xd5",
        b"\xea",
        b"\xd7",
        b"\xba",
        b"\xf5",
        b"\xfa",
        b"\xf7",
        b"\xae",
        b"\xdd",
        b"\xee",
        b"\xdf",
        b"\xbe",
        b"\xfd",
        b"\xfe",
        b"\xff",
    ],
]

MOSHI_SET_OFFSET = 0
MOSHI_TERMINATION = 2
MOSHI_VECTOR_SPEED = 5
MOSHI_RASTER_SPEED = 4
MOSHI_CUT_ABS = 15
MOSHI_CUT_HORIZ = 14
MOSHI_CUT_VERT = 11
MOSHI_MOVE_ABS = 7
MOSHI_MOVE_HORIZ = 6
MOSHI_MOVE_VERT = 3

MOSHI_FREEMOTOR = 1
MOSHI_ESTOP = 1
MOSHI_EPILOGUE = 2
MOSHI_PROLOGUE = 6
# 6 also seen at laser startup.
MOSHI_LASER = 7
MOSHI_READ = 14
# 14 is also sometimes done as a keepalive each 3.4 seconds.


class MoshiBuilder:
    """
    MoshiBuilder builds datablobs of Moshi type. These are series of commands which should be executed as a program
    within the Moshicontroller.
    """

    def __init__(self, channel=None):
        self.data = bytearray()  # Queued additional commands programs.
        self.channel = channel

        self.last_x = 0
        self.last_y = 0

        self.offset_x = 0
        self.offset_y = 0
        self._vector = None
        self._stage = 0

    def __len__(self):
        return len(self.data)

    def clear(self):
        self.data.clear()
        self._stage = 0

    def pipe_int8(self, value):
        """
        Write an 8 bit into to the current program.
        """
        self.write(struct.pack("b", value))

    def pipe_int16le(self, value):
        """
        Write a 16 bit little-endian value to the current program.
        """
        self.write(struct.pack("<h", value))

    def write(self, bytes_to_write):
        """
        Writes data to the queue, this will be moved into the buffer by the thread in a threadsafe manner.

        @param bytes_to_write: data to write to the queue.
        @return:
        """
        self.data += bytes_to_write
        return self

    def vector_speed(self, speed_mms, normal_speed_mms):
        """
        Vector Speed Byte. (0x00 position), followed by 2 int8 values.
        Jog and Normal Speed. These values are limited to integer values which
        are 1 to 256.

        @return:
        """
        assert self._stage == 0
        self._stage = 1
        self._vector = True
        if self.channel:
            self.channel(
                f"Vector Cut Speed: {int(speed_mms)} mm/s Normal Speed: {int(normal_speed_mms)} mm/s"
            )
        self.write(swizzle_table[MOSHI_VECTOR_SPEED][0])
        if speed_mms > 256:
            speed_mms = 256
        if speed_mms < 1:
            speed_mms = 1
        self.pipe_int8(speed_mms - 1)
        self.pipe_int8(normal_speed_mms - 1)

    def raster_speed(self, speed_mms):
        """
        Write speed for raster programs.
        """
        assert self._stage == 0
        self._stage = 1
        if self.channel:
            self.channel(f"Raster Header Speed: {int(speed_mms)} cm/s")
        self.write(swizzle_table[MOSHI_RASTER_SPEED][0])
        speed_cms = int(round(speed_mms / 10))
        if speed_cms == 0:
            speed_cms = 1
        self.pipe_int8(speed_cms - 1)
        self._vector = False

    def set_offset(self, z, x, y):
        """
        2nd Command For Jump. (0x03 position), followed by 3 int16le (2)
        @return:
        """
        assert self._stage == 1
        self._stage = 2
        self.offset_x = x
        self.offset_y = y

        if self.channel:
            self.channel(f"Set Location z: {int(z)}, x: {int(x)}, y: {int(y)}")
        self.write(swizzle_table[MOSHI_SET_OFFSET][0])
        self.pipe_int16le(z)  # Unknown, always zero.
        self.pipe_int16le(x)  # x
        self.pipe_int16le(y)  # y

    def termination(self):
        """
        Terminal Commands for Jump/Program. (last 7 bytes). (4)

        @return:
        """
        # assert self._stage == 3
        self._stage = 4
        if self.channel:
            self.channel("Termination.")
        for i in range(7):
            self.write(swizzle_table[MOSHI_TERMINATION][0])

    def cut_abs(self, x, y):
        """
        Write an absolute position cut value.

        Laser will cut to this position from the current stored head position.
        Head position is stored on the Moshiboard
        """
        assert 2 <= self._stage <= 3
        self._stage = 3
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        self.last_x = x
        self.last_y = y
        x -= self.offset_x
        y -= self.offset_y
        if self.channel:
            self.channel(f"Cut x: {int(x)} y: {int(y)}")
        self.write(swizzle_table[MOSHI_CUT_ABS][1])
        self.pipe_int16le(int(x))
        self.pipe_int16le(int(y))

    def move_abs(self, x, y):
        """
        Write an absolute position move value.

        Laser will move without cutting to this position from the current stored head position.
        Head position is stored on the Moshiboard
        """
        assert 2 <= self._stage <= 3
        self._stage = 3
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        self.last_x = x
        self.last_y = y
        x -= self.offset_x
        y -= self.offset_y
        if self.channel:
            self.channel(f"Move x: {int(x)} y: {int(y)}")
        self.write(swizzle_table[MOSHI_MOVE_ABS][0])
        self.pipe_int16le(int(x))
        self.pipe_int16le(int(y))

    def move_vertical_abs(self, y):
        """
        Write an absolute position vertical move.

        Laser will move the y position without cutting to the new position from the head position
        stored in the Moshiboard.
        """
        assert 2 <= self._stage <= 3
        self._stage = 3

        self.last_y = y
        y -= self.offset_y
        if self.channel:
            self.channel(f"Move Vertical y: {int(y)}")
        self.write(swizzle_table[MOSHI_MOVE_VERT][0])
        self.pipe_int16le(int(y))

    def move_horizontal_abs(self, x):
        """
        Write an absolute position horizontal move.

        Laser will move the x position without cutting to the new position from the head position
        stored in the Moshiboard.
        """
        assert 2 <= self._stage <= 3
        self._stage = 3
        self.last_x = x
        x -= self.offset_x
        if self.channel:
            self.channel(f"Move Horizontal x: {int(x)}")
        self.write(swizzle_table[MOSHI_MOVE_HORIZ][0])
        self.pipe_int16le(int(x))

    def cut_horizontal_abs(self, x):
        """
        Write an absolute position horizontal cut.

        Laser will cut to the x position with laser firing to the new position from the head position
        stored in the Moshiboard.
        """
        assert 2 <= self._stage <= 3
        self._stage = 3
        self.last_x = x
        x -= self.offset_x
        if self.channel:
            self.channel(f"Cut Horizontal x: {int(x)}")
        self.write(swizzle_table[MOSHI_CUT_HORIZ][0])
        self.pipe_int16le(int(x))

    def cut_vertical_abs(self, y):
        """
        Write an absolute position vertical cut.

        Laser will cut to the y position with laser firing to the new position from the head position
        stored in the Moshiboard
        """
        assert 2 <= self._stage <= 3
        self._stage = 3
        self.last_y = y
        y -= self.offset_y
        if self.channel:
            self.channel(f"Cut Vertical y: {int(y)}")
        self.write(swizzle_table[MOSHI_CUT_VERT][0])
        self.pipe_int16le(int(y))

    def debug(self, output=print):
        data = self.data
        convert = MoshiBuilder.convert

        pos = 0
        while pos < len(data):
            cmd = data[pos]
            cmd = convert(cmd)
            cmd >>= 4
            if cmd == 5:
                output(
                    "Vector Cut Speed: %d (%02x) mm/s Normal Speed: %d mm/s (%02x)"
                    % (data[pos + 1] + 1, data[pos + 1], data[pos + 2] + 1, data[pos + 2])
                )
                pos += 3
            elif cmd == 4:
                output(
                    "Raster Header Speed: %d cm/s (%02x)"
                    % (data[pos + 1] + 1, data[pos + 1])
                )
                pos += 2
            elif cmd == 0:
                z = int.from_bytes(data[pos + 1: pos + 3], "little", signed=True)
                x = int.from_bytes(data[pos + 3: pos + 5], "little", signed=True)
                y = int.from_bytes(data[pos + 5: pos + 7], "little", signed=True)
                output(
                    "Set Location unknown: %d, x: %d, y: %d (%02x%02x,%02x%02x,%02x%02x) "
                    % (
                        z,
                        x,
                        y,
                        data[pos + 1],
                        data[pos + 2],
                        data[pos + 3],
                        data[pos + 4],
                        data[pos + 5],
                        data[pos + 6],
                    )
                )
                pos += 7
            elif cmd == 15:
                x = int.from_bytes(data[pos + 1: pos + 3], "little", signed=True)
                y = int.from_bytes(data[pos + 3: pos + 5], "little", signed=True)
                if pos + 5 > len(data):
                    output("Cut Off.")
                    output(data[pos:])
                    return
                output(
                    "cut x: %d, y: %d (%02x%02x,%02x%02x) "
                    % (
                        x,
                        y,
                        data[pos + 1],
                        data[pos + 2],
                        data[pos + 3],
                        data[pos + 4],
                    )
                )
                pos += 5
            elif cmd == 7:
                x = int.from_bytes(data[pos + 1: pos + 3], "little", signed=True)
                y = int.from_bytes(data[pos + 3: pos + 5], "little", signed=True)
                output(
                    "move x: %d, y: %d (%02x%02x,%02x%02x) "
                    % (
                        x,
                        y,
                        data[pos + 1],
                        data[pos + 2],
                        data[pos + 3],
                        data[pos + 4],
                    )
                )
                pos += 5
            elif cmd == 6:
                p = int.from_bytes(data[pos + 1: pos + 3], "little", signed=True)
                output(
                    "move horiz x: %d (%02x%02x) "
                    % (
                        p,
                        data[pos + 1],
                        data[pos + 2],
                    )
                )
                pos += 3
            elif cmd == 3:
                p = int.from_bytes(data[pos + 1: pos + 3], "little", signed=True)
                output(
                    "move vert y: %d (%02x%02x) "
                    % (
                        p,
                        data[pos + 1],
                        data[pos + 2],
                    )
                )
                pos += 3
            elif cmd == 14:
                p = int.from_bytes(data[pos + 1: pos + 3], "little", signed=True)
                output(
                    "cut horiz x: %d (%02x%02x) "
                    % (
                        p,
                        data[pos + 1],
                        data[pos + 2],
                    )
                )
                pos += 3
            elif cmd == 11:
                p = int.from_bytes(data[pos + 1: pos + 3], "little", signed=True)
                output(
                    "cut vert y: %d (%02x%02x) "
                    % (
                        p,
                        data[pos + 1],
                        data[pos + 2],
                    )
                )
                pos += 3
            elif cmd == 2:
                output("Termination. (7 times)")
                pos += 1
            else:
                output("UNKNOWN COMMAND: %d" % cmd)
                raise ValueError
                break

    @staticmethod
    def is_estop(data):
        return data in swizzle_table[MOSHI_ESTOP]

    @staticmethod
    def read(output, channel=None):
        """
        The `a7xx` values used before the AC01 commands. Read preamble.

        Also seen randomly 3.2 seconds apart. Maybe keep-alive.
        @return:
        """
        if channel:
            channel("Realtime: Read...")
        output(swizzle_table[MOSHI_READ][0])

    @staticmethod
    def prologue(output, channel=None):
        """
        Before a jump / program / turned on:
        @return:
        """
        if channel:
            channel("Realtime: Prologue")
        output(swizzle_table[MOSHI_PROLOGUE][0])

    @staticmethod
    def epilogue(output, channel=None):
        """
        Status 205
        After a jump / program
        Status 207
        Status 205 Done.
        @return:
        """
        if channel:
            channel("Realtime: Epilogue")
        output(swizzle_table[MOSHI_EPILOGUE][0])

    @staticmethod
    def laser(output, channel=None):
        """
        Laser Command Toggle.
        @return:
        """
        if channel:
            channel("Realtime: Laser Active")
        output(swizzle_table[MOSHI_LASER][0])

    @staticmethod
    def stop(output, channel=None):
        """
        Estop command.
        @return:
        """
        if channel:
            channel("Realtime: Estop")
        output(swizzle_table[MOSHI_ESTOP][0])

    @staticmethod
    def freemotor(output, channel=None):
        """
        Estop command.
        @return:
        """
        if channel:
            channel("Realtime: Freemotor")
        output(swizzle_table[MOSHI_FREEMOTOR][0])

    @staticmethod
    def _swizzle(b, p7, p6, p5, p4, p3, p2, p1, p0):
        return (
            ((b >> 0) & 1) << p0
            | ((b >> 1) & 1) << p1
            | ((b >> 2) & 1) << p2
            | ((b >> 3) & 1) << p3
            | ((b >> 4) & 1) << p4
            | ((b >> 5) & 1) << p5
            | ((b >> 6) & 1) << p6
            | ((b >> 7) & 1) << p7
        )

    @staticmethod
    def convert(q):
        """
        Translated Moshiboard swizzle into correct Moshi command code.

        Moshiboards command codes have 16 values with 16 different swizzled values. There are
        two different swizzles depending on the parity of the particular code. These codes are used
        randomly by Moshi's native software. The board itself reads these all the same.
        """
        if q & 1:
            return MoshiBuilder._swizzle(q, 7, 6, 2, 4, 3, 5, 1, 0)
        else:
            return MoshiBuilder._swizzle(q, 5, 1, 7, 2, 4, 3, 6, 0)

    @staticmethod
    def reconvert(q):
        """
        Counter-translate a particular command code back into correct values.
        """
        for m in range(5):
            q = MoshiBuilder.convert(q)
        return q
