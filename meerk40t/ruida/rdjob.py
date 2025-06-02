import threading
import time

from meerk40t.core.cutcode.plotcut import PlotCut
from meerk40t.core.units import UNITS_PER_uM
from meerk40t.svgelements import Color

from .exceptions import RuidaCommandError

INTERFACE_FRAME = b"\xA5\x53\x00"
INTERFACE_PLUS_X_DOWN = b"\xA5\x50\x02"
INTERFACE_PLUS_X_UP = b"\xA5\x51\x02"
INTERFACE_MINUS_X_DOWN = b"\xA5\x50\x01"
INTERFACE_MINUS_X_UP = b"\xA5\x51\x01"
INTERFACE_PLUS_Y_DOWN = b"\xA5\x50\x03"
INTERFACE_PLUS_Y_UP = b"\xA5\x51\x03"
INTERFACE_MINUS_Y_DOWN = b"\xA5\x50\x04"
INTERFACE_MINUS_Y_UP = b"\xA5\x51\x04"
INTERFACE_PLUS_Z_DOWN = b"\xA5\x50\x0A"
INTERFACE_PLUS_Z_UP = b"\xA5\x51\x0A"
INTERFACE_MINUS_Z_DOWN = b"\xA5\x50\x0B"
INTERFACE_MINUS_Z_UP = b"\xA5\x51\x0B"
INTERFACE_PLUS_U_DOWN = b"\xA5\x50\x0C"
INTERFACE_PLUS_U_UP = b"\xA5\x51\x0C"
INTERFACE_MINUS_U_DOWN = b"\xA5\x50\x0D"
INTERFACE_MINUS_U_UP = b"\xA5\x51\x0D"
INTERFACE_PULSE_DOWN = b"\xA5\x50\x05"
INTERFACE_PULSE_UP = b"\xA5\x51\x05"
INTERFACE_SPEED_DOWN = b"\xA5\x50\x11"
INTERFACE_SPEED_UP = b"\xA5\x51\x11"
INTERFACE_PAUSE_DOWN = b"\xA5\x50\x06"
INTERFACE_PAUSE_UP = b"\xA5\x51\x06"
INTERFACE_STOP_DOWN = b"\xA5\x50\x09"
INTERFACE_STOP_UP = b"\xA5\x51\x09"
INTERFACE_RESET_DOWN = b"\xA5\x50\x5A"
INTERFACE_RESET_UP = b"\xA5\x51\x5A"
INTERFACE_TRACE_DOWN = b"\xA5\x50\x0F"
INTERFACE_TRACE_UP = b"\xA5\x51\x0F"
INTERFACE_ESCAPE_DOWN = b"\xA5\x50\x07"
INTERFACE_ESCAPE_UP = b"\xA5\x51\x07"
INTERFACE_LASER_GATE_DOWN = b"\xA5\x50\x12"
INTERFACE_LASER_GATE_UP = b"\xA5\x51\x12"
INTERFACE_ORIGIN_DOWN = b"\xA5\x50\x08"
INTERFACE_ORIGIN_UP = b"\xA5\x51\x08"
AXIS_X_MOVE = b"\x80\x00"  # abscoord(x)
AXIS_Z_MOVE = b"\x80\x01"  # abscoord(z),
MOVE_ABS_XY = b"\x88"  # abscoord(x), abscoord(y)
MOVE_REL_XY = b"\x89"  # relcoord(dx), relcoord(dy)
AXIS_A_MOVE = b"\xA0\x00"  # abscoord(a)
AXIS_U_MOVE = b"\xA0\x08"  # abscoord(u)
MOVE_REL_X = b"\x8A"  # relcoord(dx)
MOVE_REL_Y = b"\x8B"  # relcoord(dy)
CUT_ABS_XY = b"\xA8"  # abscoord(x), abscoord(y)
CUT_REL_XY = b"\xA9"  # relcoord(dx), relcoord(dy)
CUT_REL_X = b"\xAA"  # relcoord(dx)
CUT_REL_Y = b"\xAB"  # relcoord(dy)
IMD_POWER_1 = b"\xC7"  # power(2)
IMD_POWER_2 = b"\xC0"  # power(2)
IMD_POWER_3 = b"\xC2"  # power(2)
IMD_POWER_4 = b"\xC3"  # power(2)
END_POWER_1 = b"\xC8"  # power(2)
END_POWER_2 = b"\xC1"  # power(2)
END_POWER_3 = b"\xC4"  # power(2)
END_POWER_4 = b"\xC5"  # power(2)
MIN_POWER_1 = b"\xC6\x01"  # power(2)
MAX_POWER_1 = b"\xC6\x02"  # power(2)
MIN_POWER_2 = b"\xC6\x21"  # power(2)
MAX_POWER_2 = b"\xC6\x22"  # power(2)
MIN_POWER_3 = b"\xC6\x05"  # power(2)
MAX_POWER_3 = b"\xC6\x06"  # power(2)
MIN_POWER_4 = b"\xC6\x07"  # power(2)
MAX_POWER_4 = b"\xC6\x08"  # power(2)
LASER_INTERVAL = b"\xC6\x10"  # time(5)
ADD_DELAY = b"\xC6\x11"  # time(5)
LASER_ON_DELAY = b"\xC6\x12"  # time(5)
LASER_OFF_DELAY = b"\xC6\x13"  # time(5)
LASER_ON_DELAY2 = b"\xC6\x15"  # time(5)
LASER_OFF_DELAY2 = b"\xC6\x16"  # time(5)
MIN_POWER_1_PART = b"\xC6\x31"  # part(1), power(2)
MAX_POWER_1_PART = b"\xC6\x32"  # part(1), power(2)
MIN_POWER_2_PART = b"\xC6\x41"  # part(1), power(2)
MAX_POWER_2_PART = b"\xC6\x42"  # part(1), power(2)
MIN_POWER_3_PART = b"\xC6\x35"  # part(1), power(2)
MAX_POWER_3_PART = b"\xC6\x36"  # part(1), power(2
MIN_POWER_4_PART = b"\xC6\x37"  # part(1), power(2)
MAX_POWER_4_PART = b"\xC6\x38"  # part(1), power(2)
THROUGH_POWER_1 = b"\xC6\x50"  # power(2)
THROUGH_POWER_2 = b"\xC6\x51"  # power(2)
THROUGH_POWER_3 = b"\xC6\x55"  # power(2)
THROUGH_POWER_4 = b"\xC6\x56"  # power(2)
FREQUENCY_PART = b"\xC6\x60"  # laser(1), part(1), frequency(5)
SPEED_LASER_1 = b"\xC9\x02"  # speed(5)
SPEED_AXIS = b"\xC9\x03"  # speed(5)
SPEED_LASER_1_PART = b"\xC9\x04"  # part(1), speed(5)
FORCE_ENG_SPEED = b"\xC9\x05"  # speed(5)
SPEED_AXIS_MOVE = b"\xC9\x06"  # speed(5)
LAYER_END = b"\xCA\x01\x00"
WORK_MODE_1 = b"\xCA\x01\x01"
WORK_MODE_2 = b"\xCA\x01\x02"
WORK_MODE_3 = b"\xCA\x01\x03"
WORK_MODE_4 = b"\xCA\x01\x04"
WORK_MODE_5 = b"\xCA\x01\x55"
WORK_MODE_6 = b"\xCA\x01\x05"
LASER_DEVICE_0 = b"\xCA\x01\x10"
LASER_DEVICE_1 = b"\xCA\x01\x11"
AIR_ASSIST_OFF = b"\xCA\x01\x12"
AIR_ASSIST_ON = b"\xCA\x01\x13"
DB_HEAD = b"\xCA\x01\x14"
EN_LASER_2_OFFSET_0 = b"\xCA\x01\x30"
EN_LASER_2_OFFSET_1 = b"\xCA\x01\x31"
LAYER_NUMBER_PART = b"\xCA\x02"  # part(1)
EN_LASER_TUBE_START = b"\xCA\x03"  # part(1)
X_SIGN_MAP = b"\xCA\x04"  # value(1)
LAYER_COLOR = b"\xCA\x05"  # color(5)
LAYER_COLOR_PART = b"\xCA\x06"  # part(1), color(5)
EN_EX_IO = b"\xCA\x10"  # value(1)
MAX_LAYER_PART = b"\xCA\x22"  # part(1)
U_FILE_ID = b"\xCA\x30"  # file_number(2)
ZU_MAP = b"\xCA\x40"  # value(1)
WORK_MODE_PART = b"\xCA\x41"  # part(1), mode(1)
ACK = b"\xCC"
ERR = b"\xCD"
KEEP_ALIVE = b"\xCE"
END_OF_FILE = b"\xD7"
START_PROCESS = b"\xD8\x00"
STOP_PROCESS = b"\xD8\x01"
PAUSE_PROCESS = b"\xD8\x02"
RESTORE_PROCESS = b"\xD8\x03"
REF_POINT_2 = b"\xD8\x10"  # MACHINE_ZERO/ABS POSITION
REF_POINT_1 = b"\xD8\x11"  # ANCHOR_POINT
REF_POINT_0 = b"\xD8\x12"  # CURRENT_POSITION
HOME_Z = b"\xD8\x2C"
HOME_U = b"\xD8\x2D"
HOME_XY = b"\xD8\x2A"
FOCUS_Z = b"\xD8\x2E"
KEYDOWN_X_LEFT = b"\xD8\x20"
KEYDOWN_X_RIGHT = b"\xD8\x21"
KEYDOWN_Y_TOP = b"\xD8\x22"
KEYDOWN_Y_BOTTOM = b"\xD8\x23"
KEYDOWN_Z_UP = b"\xD8\x24"
KEYDOWN_Z_DOWN = b"\xD8\x25"
KEYDOWN_U_FORWARD = b"\xD8\x26"
KEYDOWN_U_BACKWARDS = b"\xD8\x27"
KEYUP_X_LEFT = b"\xD8\x30"
KEYUP_X_RIGHT = b"\xD8\x31"
KEYUP_Y_TOP = b"\xD8\x32"
KEYUP_Y_BOTTOM = b"\xD8\x33"
KEYUP_Z_UP = b"\xD8\x34"
KEYUP_Z_DOWN = b"\xD8\x35"
KEYUP_U_FORWARD = b"\xD8\x36"
KEYUP_U_BACKWARDS = b"\xD8\x37"
RAPID_OPTION_LIGHT = b"\x03"
RAPID_OPTION_LIGHTORIGIN = b"\x01"
RAPID_OPTION_ORIGIN = b"\x00"
RAPID_OPTION_NONE = b"\x02"
RAPID_MOVE_X = b"\xD9\x00"  # options(1), abscoord(5)
RAPID_MOVE_Y = b"\xD9\x01"  # options(1), abscoord(5)
RAPID_MOVE_Z = b"\xD9\x02"  # options(1), abscoord(5)
RAPID_MOVE_U = b"\xD9\x03"  # options(1), abscoord(5)
RAPID_FEED_AXIS_MOVE = b"\xD9\x0F"  # options(1)
RAPID_MOVE_XY = b"\xD9\x10"  # options(1), abscoord(5), abscoord(5)
RAPID_MOVE_XYU = b"\xD9\x30"  # options(1), abscoord(5), abscoord(5), abscoord(5)
GET_SETTING = b"\xDA\x00"  # memory(2)
SET_SETTING = b"\xDA\x01"  # memory(2), v0(5), v1(5)
DOCUMENT_FILE_UPLOAD = b"\xE5\x00"  # file_number(2), v0(5), v1(5)
DOCUMENT_FILE_END = b"\xE5\x02"
SET_FILE_SUM = b"\xE5\x05"
SET_ABSOLUTE = b"\xE6\x01"
BLOCK_END = b"\xE7\x00"
SET_FILENAME = b"\xE7\x01"  # filename (null terminated).
PROCESS_TOP_LEFT = b"\xE7\x03"  # abscoord(5), abscoord(5)
PROCESS_REPEAT = b"\xE7\x04"  # v0(2), v1(2), v2(2), v3(2), v4(2), v5(2), v6(2)
ARRAY_DIRECTION = b"\xE7\x05"  # direction(1)
FEED_REPEAT = b"\xE7\x06"  # v0(5), v1(5)
PROCESS_BOTTOM_RIGHT = b"\xE7\x07"  # abscoord(5), abscoord(5)
ARRAY_REPEAT = b"\xE7\x08"  # v0(2), v1(2), v2(2), v3(2), v4(2), v5(2), v6(2)
FEED_LENGTH = b"\xE7\x09"  # value(5)
FEED_INFO = b"\xE7\x0A"
ARRAY_EN_MIRROR_CUT = b"\xE7\x0B"  # value(1)
ARRAY_MIN_POINT = b"\xE7\x13"  # abscoord(5), abscoord(5)
ARRAY_MAX_POINT = b"\xE7\x17"  # abscoord(5), abscoord(5)
ARRAY_ADD = b"\xE7\x23"  # abscoord(5), abscoord(5)
ARRAY_MIRROR = b"\xE7\x24"  # mirror(1)
BLOCK_X_SIZE = b"\xE7\x35"  # abscoord(5), abscoord(5)
BY_TEST = b"\xE7\x35"  # 0x11227766
ARRAY_EVEN_DISTANCE = b"\xE7\x37"
SET_FEED_AUTO_PAUSE = b"\xE7\x38"
UNION_BLOCK_PROPERTY = b"\xE7\x3A"
DOCUMENT_MIN_POINT = b"\xE7\x50"  # abscoord(5), abscoord(5)
DOCUMENT_MAX_POINT = b"\xE7\x51"  # abscoord(5), abscoord(5)
PART_MIN_POINT = b"\xE7\x52"  # part(1), abscoord(5), abscoord(5)
PART_MAX_POINT = b"\xE7\x53"  # part(1), abscoord(5), abscoord(5)
PEN_OFFSET = b"\xE7\x54"  # axis(1), coord(5)
LAYER_OFFSET = b"\xE7\x55"  # axis(1), coord(5)
SET_CURRENT_ELEMENT_INDEX = b"\xE7\x60"  # index(1)
PART_MIN_POINT_EX = b"\xE7\x61"  # part(1), abscoord(5), abscoord(5)
PART_MAX_POINT_EX = b"\xE7\x62"  # part(1), abscoord(5), abscoord(5)
ARRAY_START = b"\xEA"  # index(1)
ARRAY_END = b"\xEB"
REF_POINT_SET = b"\xF0"
ELEMENT_MAX_INDEX = b"\xF1\x00"  # index(1)
ELEMENT_NAME_MAX_INDEX = b"\xF1\x01"  # index(1)
ENABLE_BLOCK_CUTTING = b"\xF1\x02"  # enable(1)
DISPLAY_OFFSET = b"\xF1\x03"  # abscoord(5),  abscoord(5)
FEED_AUTO_CALC = b"\xF1\x04"  # enable(1)
ELEMENT_INDEX = b"\xF2\x00"  # index(1)
ELEMENT_NAME = b"\xF2\x02"  # name(10)
ELEMENT_ARRAY_MIN_POINT = b"\xF2\x03"  # abscoord(5),  abscoord(5)
ELEMENT_ARRAY_MAX_POINT = b"\xF2\x04"  # abscoord(5),  abscoord(5)
ELEMENT_ARRAY = b"\xF2\x05"  # v0(2), v1(2), v2(2), v3(2), v4(2), v5(2), v6(2)
ELEMENT_ARRAY_ADD = b"\xF2\x06"  # abscoord(5), abscoord(5)
ELEMENT_ARRAY_MIRROR = b"\xF2\x07"  # mirror(1)

MEM_CARD_ID = 0x02FE


def encode_part(part):
    assert 0 <= part <= 255
    return bytes([part])


def encode_index(index):
    assert 0 <= index <= 255
    return bytes([index])


def encode14(v):
    v = int(v)
    return bytes(
        [
            (v >> 7) & 0x7F,
            v & 0x7F,
        ]
    )


def encode32(v):
    v = int(v)
    return bytes(
        [
            (v >> 28) & 0x7F,
            (v >> 21) & 0x7F,
            (v >> 14) & 0x7F,
            (v >> 7) & 0x7F,
            v & 0x7F,
        ]
    )


def encode_coord(coord):
    return encode32(coord)


def encode_relcoord(coord):
    return encode14(coord)


def encode_color(color):
    # Scewed on RDC 22.01
    # Maybe 16bit color is used?
    return encode32(int(color))


def encode_file_number(file_number):
    return encode14(file_number)


def encode_mem(file_number):
    return encode14(file_number)


def encode_value(value):
    return encode32(value)


def encode_power(power):
    # 16384 / 100%
    return encode14(power * 16383 / 100.0)


def encode_speed(speed):
    # uM/sec
    return encode32(speed * 1000)


def encode_time(time):
    return encode32(time * 1000)


def encode_frequency(freq_hz):
    return encode32(freq_hz)


def signed35(v):
    v = int(v)
    v &= 0x7FFFFFFFF
    if v > 0x3FFFFFFFF:
        return -0x800000000 + v
    else:
        return v


def signed32(v):
    v = int(v)
    v &= 0xFFFFFFFF
    if v > 0x7FFFFFFF:
        return -0x100000000 + v
    else:
        return v


def signed14(v):
    v = int(v)
    v &= 0x7FFF
    if v > 0x1FFF:
        return -0x4000 + v
    else:
        return v


def decode14(data):
    return signed14(decodeu14(data))


def decodeu14(data):
    return (data[0] & 0x7F) << 7 | (data[1] & 0x7F)


def decode35(data):
    return signed35(decodeu35(data))


def decode32(data):
    return signed32(decodeu35(data))


def decodeu35(data):
    return (
        (data[0] & 0x7F) << 28
        | (data[1] & 0x7F) << 21
        | (data[2] & 0x7F) << 14
        | (data[3] & 0x7F) << 7
        | (data[4] & 0x7F)
    )


def abscoord(data):
    return decode32(data)


def relcoord(data):
    return decode14(data)


def parse_mem(data):
    return decode14(data)


def parse_filenumber(data):
    return decode14(data)


def parse_speed(data):
    return decode35(data) / 1000.0


def parse_frequency(data):
    return decodeu35(data)


def parse_power(data):
    return decodeu14(data) / 163.84  # 16384 / 100%


def parse_time(data):
    return decodeu35(data) / 1000.0


def parse_commands(data):
    """
    Parses data blob into command chunk sized pieces.
    @param data:
    @return:
    """
    mark = 0
    for i, b in enumerate(data):
        if b >= 0x80 and mark != i:
            yield data[mark:i]
            mark = i
    if mark != len(data):
        yield data[mark:]


def swizzle_byte(b, magic):
    b ^= (b >> 7) & 0xFF
    b ^= (b << 7) & 0xFF
    b ^= (b >> 7) & 0xFF
    b ^= magic
    b = (b + 1) & 0xFF
    return b


def unswizzle_byte(b, magic):
    b = (b - 1) & 0xFF
    b ^= magic
    b ^= (b >> 7) & 0xFF
    b ^= (b << 7) & 0xFF
    b ^= (b >> 7) & 0xFF
    return b


def swizzles_lut(magic):
    if magic == -1:
        lut = [s for s in range(256)]
        return lut, lut
    lut_swizzle = [swizzle_byte(s, magic) for s in range(256)]
    lut_unswizzle = [unswizzle_byte(s, magic) for s in range(256)]
    return lut_swizzle, lut_unswizzle


def decode_bytes(data, magic=0x88):
    lut_swizzle, lut_unswizzle = swizzles_lut(magic)
    array = list()
    for b in data:
        array.append(lut_unswizzle[b])
    return bytes(array)


def determine_magic_via_histogram(data):
    """
    Determines magic number via histogram. The number which occurs most in RDWorks files is overwhelmingly 0. It's
    about 50% of all data. The swizzle algorithm means that the swizzle for 0 is magic + 1, so we find the most
    frequent number and subtract one from that and that is *most* likely the magic number.

    @param data:
    @return:
    """
    histogram = [0] * 256
    prev = -1
    for d in data:
        histogram[d] += 5 if prev == d else 1
        prev = d
    m = 0
    magic = None
    for i in range(len(histogram)):
        v = histogram[i]
        if v > m:
            m = v
            magic = i - 1
    return magic


def encode_bytes(data, magic=0x88):
    lut_swizzle, lut_unswizzle = swizzles_lut(magic)
    array = list()
    for b in data:
        array.append(lut_swizzle[b])
    return bytes(array)


def magic_keys():
    mk = dict()
    for g in range(256):
        mk[encode_bytes(b"\xda\x00\x05\x7E", magic=g)] = g
    return mk


class RDJob:
    def __init__(
        self,
        driver=None,
        units_to_device_matrix=None,
        priority=0,
        channel=None,
        magic=0x11,
    ):
        self.units_to_device_matrix = units_to_device_matrix
        self._driver = driver
        self.channel = channel
        self.reply = None
        self.buffer = list()
        self.plotcut = None

        self.priority = priority

        self.time_submitted = time.time()
        self.time_started = None
        self.runtime = 0

        self._stopped = True
        self.enabled = True
        self._estimate = 0
        self.offset = 0

        self.scale = UNITS_PER_uM

        self.speed = None
        self.power = None
        self.frequency = None
        self.power1_max = None
        self.power1_min = None
        self.power2_max = None
        self.power2_min = None

        self.color = None
        # 0x11 for the 634XG
        self.magic = magic
        self.lut_swizzle, self.lut_unswizzle = swizzles_lut(self.magic)

        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.u = 0.0

        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.d = 0.0

        self.lock = threading.Lock()

    def __str__(self):
        return f"{self.__class__.__name__}({len(self.buffer)} lines)"

    def __call__(self, *args, output=None, swizzle=True):
        e = b"".join(args)
        if output is None:
            self.write_command(e)
        else:
            if swizzle:
                e = bytes([self.lut_swizzle[b] for b in e])
            output(e)

    @property
    def status(self):
        if self.is_running():
            if self.time_started:
                return "Running"
            else:
                return "Queued"
        else:
            if self.enabled:
                return "Waiting"
            else:
                return "Disabled"

    def clear(self):
        self.buffer.clear()

    def set_magic(self, magic):
        """
        Sets the magic number for blob decoding.

        @param magic: magic number to unswizzling.
        @return:
        """
        if magic is not None and magic != self.magic:
            self.magic = magic
            self.lut_swizzle, self.lut_unswizzle = swizzles_lut(self.magic)

    def write_blob(self, data, magic=None):
        """
        Procedural commands sent in large data chunks. This can be through USB or UDP or a loaded file. These are
        expected to be unswizzled with the swizzle_mode set for the reply. Write will parse out the individual commands
        and send those to the command routine.

        @param data:
        @param magic: magic number for unswizzling
        @return:
        """
        if magic is None:
            magic = determine_magic_via_histogram(data)
        self.set_magic(magic)
        data = self.unswizzle(data)
        with self.lock:
            self.buffer.extend(parse_commands(data))

    def write_command(self, command):
        with self.lock:
            self.buffer.append(command)

    def file_sum(self):
        return sum([sum(list(g)) for g in self.buffer])

    def get_contents(self, first=None, last=None, swizzled=True):
        data = b"".join(self.buffer[first:last])
        if swizzled:
            return self.swizzle(data)
        return data

    def execute(self, driver=None):
        """
        Execute calls each item in the list of items in order. This is intended to be called by the spooler thread. And
        hold the spooler while these items are executing.
        @return:
        """
        self._stopped = False
        if self.time_started is None:
            self.time_started = time.time()
        with self.lock:
            command = self.buffer.pop(0)
        try:
            array = list(command)
            self.process(array, offset=self.offset)
            self.offset += len(command)
        except IndexError as e:
            raise RuidaCommandError(
                f"Could not process Ruida buffer, {self.buffer[:25]} with magic: {self.magic:02}"
            ) from e
        if not self.buffer:
            # Buffer is empty now. Job is complete
            self.runtime += time.time() - self.time_started
            self._stopped = True
            return True  # All steps were executed.
        return False

    def stop(self):
        """
        Stop this current laser-job, cannot be called from the spooler thread.
        @return:
        """
        if not self._stopped:
            self.runtime += time.time() - self.time_started
        self._stopped = True

    def is_running(self):
        return not self._stopped

    def elapsed_time(self):
        """
        How long is this job already running...
        """
        if self.is_running():
            return time.time() - self.time_started
        else:
            return self.runtime

    def estimate_time(self):
        """
        Give laser job time estimate.
        @return:
        """
        return self._estimate

    def plot_location(self, x, y, power):
        """
        Adds this particular location to the current plotcut.

        Or, starts a new plotcut if one is not already started.

        First plotcut is a 0-power move to the current position. X and Y are set to plotted location

        @param x:
        @param y:
        @param power:
        @return:
        """
        matrix = self.units_to_device_matrix
        if matrix is None:
            # Using job for something other than point plotting
            return
        if self.plotcut is None:
            self.x = x
            self.y = y
            ox, oy = matrix.transform_point([self.x, self.y])
            self.plotcut = PlotCut(
                settings={
                    "speed": self.speed,
                    "power": self.power,
                    "frequency": self.frequency,
                }
            )
            self.plotcut.plot_init(int(round(ox)), int(round(oy)))
        tx, ty = matrix.transform_point([x, y])
        self.plotcut.plot_append(
            int(round(tx)), int(round(ty)), power * (self.power / 1000.0)
        )
        self.x = x
        self.y = y

    def plot_commit(self):
        """
        Force commits the old plotcut and unsets the current plotcut.

        @return:
        """
        if self.plotcut is None:
            return
        self.plot(self.plotcut)
        self.plotcut = None

    def plot(self, plot):
        try:
            self._driver.plot(plot)
        except AttributeError:
            pass

    def __repr__(self):
        return f"RuidaEmulator(@{hex(id(self))})"

    @property
    def current(self):
        return self.x, self.y

    def set_color(self, color):
        self.color = color

    def process(self, array, offset=None):
        """
        Parses an individual unswizzled ruida command, updating the emulator state.

        These commands can change the position, settings, speed, color, power, create elements.
        @param array:
        @return:
        """
        desc = ""
        if array[0] < 0x80:
            if self.channel:
                self.channel(f"NOT A COMMAND: {array[0]}")
            raise RuidaCommandError("Not a command.")
        elif array[0] == 0x80:
            value = abscoord(array[2:7])
            if array[1] == 0x00:
                desc = f"Axis X Move {value}"
                self.x += value
            elif array[1] == 0x08:
                desc = f"Axis Z Move {value}"
                self.z += value
        elif array[0] == 0x88:  # 0b10001000 11 characters.
            x = abscoord(array[1:6])
            y = abscoord(array[6:11])
            self.plot_location(x * self.scale, y * self.scale, 0)
            desc = f"Move Absolute ({x}μm, {y}μm)"
        elif array[0] == 0x89:  # 0b10001001 5 characters
            if len(array) > 1:
                dx = relcoord(array[1:3])
                dy = relcoord(array[3:5])
                self.plot_location(
                    self.x + dx * self.scale, self.y + dy * self.scale, 0
                )
                desc = f"Move Relative ({dx:+}μm, {dy:+}μm)"
            else:
                desc = "Move Relative (no coords)"
        elif array[0] == 0x8A:  # 0b10101010 3 characters
            dx = relcoord(array[1:3])
            self.plot_location(self.x + dx * self.scale, self.y, 0)
            desc = f"Move Horizontal Relative ({dx:+}μm)"
        elif array[0] == 0x8B:  # 0b10101011 3 characters
            dy = relcoord(array[1:3])
            self.plot_location(self.x, self.y + dy * self.scale, 0)
            desc = f"Move Vertical Relative ({dy:+}μm)"
        elif array[0] == 0xA0:
            value = abscoord(array[2:7])
            if array[1] == 0x00:
                desc = f"Axis Y Move {value}"
            elif array[1] == 0x08:
                desc = f"Axis U Move {value}"
        elif array[0] == 0xA8:  # 0b10101000 11 characters.
            x = abscoord(array[1:6])
            y = abscoord(array[6:11])
            self.plot_location(x * self.scale, y * self.scale, 1)
            desc = f"Cut Absolute ({x}μm, {y}μm)"
        elif array[0] == 0xA9:  # 0b10101001 5 characters
            dx = relcoord(array[1:3])
            dy = relcoord(array[3:5])
            self.plot_location(self.x + dx * self.scale, self.y + dy * self.scale, 1)
            desc = f"Cut Relative ({dx:+}μm, {dy:+}μm)"
        elif array[0] == 0xAA:  # 0b10101010 3 characters
            dx = relcoord(array[1:3])
            self.plot_location(self.x + dx * self.scale, self.y, 1)
            desc = f"Cut Horizontal Relative ({dx:+}μm)"
        elif array[0] == 0xAB:  # 0b10101011 3 characters
            dy = relcoord(array[1:3])
            self.plot_location(self.x, self.y + dy * self.scale, 1)
            desc = f"Cut Vertical Relative ({dy:+}μm)"
        elif array[0] == 0xC7:
            try:
                v0 = parse_power(array[1:3])
            except IndexError:
                v0 = 0
            desc = f"Imd Power 1 ({v0})"
        elif array[0] == 0xC2:
            v0 = parse_power(array[1:3])
            desc = f"Imd Power 3 ({v0})"
        elif array[0] == 0xC0:
            v0 = parse_power(array[1:3])
            desc = f"Imd Power 2 ({v0})"
        elif array[0] == 0xC3:
            v0 = parse_power(array[1:3])
            desc = f"Imd Power 4 ({v0})"
        elif array[0] == 0xC8:
            v0 = parse_power(array[1:3])
            desc = f"End Power 1 ({v0})"
        elif array[0] == 0xC4:
            v0 = parse_power(array[1:3])
            desc = f"End Power 3 ({v0})"
        elif array[0] == 0xC1:
            v0 = parse_power(array[1:3])
            desc = f"End Power 2 ({v0})"
        elif array[0] == 0xC5:
            v0 = parse_power(array[1:3])
            desc = f"End Power 4 ({v0})"
        elif array[0] == 0xC6:
            if array[1] == 0x01:
                power = parse_power(array[2:4])
                self.power1_min = power
                power = self.power1_min
                desc = f"Power 1 min={power}"
                self.power = power * 10  # 1000 / 100
            elif array[1] == 0x02:
                power = parse_power(array[2:4])
                self.power1_max = power
                power = self.power1_max
                desc = f"Power 1 max={power}"
                self.power = power * 10  # 1000 / 100
            elif array[1] == 0x05:
                power = parse_power(array[2:4])
                desc = f"Power 3 min={power}"
            elif array[1] == 0x06:
                power = parse_power(array[2:4])
                desc = f"Power 3 max={power}"
            elif array[1] == 0x07:
                power = parse_power(array[2:4])
                desc = f"Power 4 min={power}"
            elif array[1] == 0x08:
                power = parse_power(array[2:4])
                desc = f"Power 4 max={power}"
            elif array[1] == 0x10:
                interval = parse_time(array[2:7])
                desc = f"Laser Interval {interval}ms"
            elif array[1] == 0x11:
                interval = parse_time(array[2:7])
                desc = f"Add Delay {interval}ms"
            elif array[1] == 0x12:
                interval = parse_time(array[2:7])
                desc = f"Laser On Delay {interval}ms"
            elif array[1] == 0x13:
                interval = parse_time(array[2:7])
                desc = f"Laser Off Delay {interval}ms"
            elif array[1] == 0x15:
                interval = parse_time(array[2:7])
                desc = f"Laser On2 {interval}ms"
            elif array[1] == 0x16:
                interval = parse_time(array[2:7])
                desc = f"Laser Off2 {interval}ms"
            elif array[1] == 0x21:
                power = parse_power(array[2:4])
                desc = f"Power 2 min={power}"
                self.power2_min = power
            elif array[1] == 0x22:
                power = parse_power(array[2:4])
                desc = f"Power 2 max={power}"
                self.power2_max = power
            elif array[1] == 0x31:
                part = array[2]
                self.power1_min = parse_power(array[3:5])
                desc = f"{part}, Power 1 Min=({self.power1_min})"
            elif array[1] == 0x32:
                part = array[2]
                self.power1_max = parse_power(array[3:5])
                desc = f"{part}, Power 1 Max=({self.power1_max})"
            elif array[1] == 0x35:
                part = array[2]
                power = parse_power(array[3:5])
                desc = f"{part}, Power 3 Min ({power})"
            elif array[1] == 0x36:
                part = array[2]
                power = parse_power(array[3:5])
                desc = f"{part}, Power 3 Max ({power})"
            elif array[1] == 0x37:
                part = array[2]
                power = parse_power(array[3:5])
                desc = f"{part}, Power 4 Min ({power})"
            elif array[1] == 0x38:
                part = array[2]
                power = parse_power(array[3:5])
                desc = f"{part}, Power 4 Max ({power})"
            elif array[1] == 0x41:
                part = array[2]
                power = parse_power(array[3:5])
                desc = f"{part}, Power 2 Min ({power})"
            elif array[1] == 0x42:
                part = array[2]
                power = parse_power(array[3:5])
                desc = f"{part}, Power 2 Max ({power})"
            elif array[1] == 0x50:
                power = parse_power(array[2:4])
                desc = f"Through Power 1 ({power})"
            elif array[1] == 0x51:
                power = parse_power(array[2:4])
                desc = f"Through Power 2 ({power})"
            elif array[1] == 0x55:
                power = parse_power(array[2:4])
                desc = f"Through Power 3 ({power})"
            elif array[1] == 0x56:
                power = parse_power(array[2:4])
                desc = f"Through Power 4 ({power})"
            elif array[1] == 0x60:
                laser = array[2]
                part = array[3]
                frequency = parse_frequency(array[4:9])
                desc = f"{part}, Laser {laser}, Frequency ({frequency})"
                if frequency != self.frequency:
                    self.frequency = frequency
        elif array[0] == 0xC9:
            if array[1] == 0x02:
                self.plot_commit()
                speed = parse_speed(array[2:7])
                if speed != self.speed:
                    self.speed = speed
                desc = f"Speed Laser 1 {speed}mm/s"
            elif array[1] == 0x03:
                speed = parse_speed(array[2:7])
                desc = f"Axis Speed {speed}mm/s"
            elif array[1] == 0x04:
                self.plot_commit()
                part = array[2]
                speed = parse_speed(array[3:8])
                if speed != self.speed:
                    self.speed = speed
                desc = f"{part}, Speed {speed}mm/s"
            elif array[1] == 0x05:
                speed = parse_speed(array[2:7]) / 1000.0
                desc = f"Force Eng Speed {speed}mm/s"
            elif array[1] == 0x06:
                speed = parse_speed(array[2:7]) / 1000.0
                desc = f"Axis Move Speed {speed}mm/s"
        elif array[0] == 0xCA:
            if array[1] == 0x01:
                if array[2] == 0x00:
                    desc = "End Layer"
                elif array[2] == 0x01:
                    desc = "Work Mode 1"
                elif array[2] == 0x02:
                    desc = "Work Mode 2"
                elif array[2] == 0x03:
                    desc = "Work Mode 3"
                elif array[2] == 0x04:
                    desc = "Work Mode 4"
                elif array[2] == 0x55:
                    desc = "Work Mode 5"
                elif array[2] == 0x05:
                    desc = "Work Mode 6"
                elif array[2] == 0x10:
                    desc = "Layer Device 0"
                elif array[2] == 0x11:
                    desc = "Layer Device 1"
                elif array[2] == 0x12:
                    desc = "Air Assist Off"
                elif array[2] == 0x13:
                    desc = "Air Assist On"
                elif array[2] == 0x14:
                    desc = "DbHead"
                elif array[2] == 0x30:
                    desc = "EnLaser2Offset 0"
                elif array[2] == 0x31:
                    desc = "EnLaser2Offset 1"
            elif array[1] == 0x02:
                part = array[2]
                desc = f"{part}, Layer Number"
            elif array[1] == 0x03:
                desc = "EnLaserTube Start"
            elif array[1] == 0x04:
                value = array[2]
                desc = f"X Sign Map {value}"
            elif array[1] == 0x05:
                self.plot_commit()
                c = decodeu35(array[2:7])
                r = c & 0xFF
                g = (c >> 8) & 0xFF
                b = (c >> 16) & 0xFF
                c = Color(red=r, blue=b, green=g)
                self.set_color(c.hex)
                desc = f"Layer Color {str(self.color)}"
            elif array[1] == 0x06:
                part = array[2]
                c = decodeu35(array[3:8])
                r = c & 0xFF
                g = (c >> 8) & 0xFF
                b = (c >> 16) & 0xFF
                c = Color(red=r, blue=b, green=g)
                self.set_color(c.hex)
                desc = f"Color Part {part}, {self.color}"
            elif array[1] == 0x10:
                value = array[2]
                desc = f"EnExIO Start {value}"
            elif array[1] == 0x22:
                part = array[2]
                desc = f"{part}, Max Layer"
            elif array[1] == 0x30:
                filenumber = parse_filenumber(array[2:4])
                desc = f"U File ID {filenumber}"
            elif array[1] == 0x40:
                value = array[2]
                desc = f"ZU Map {value}"
            elif array[1] == 0x41:
                part = array[2]
                mode = array[3]
                desc = f"{part}, Work Mode {mode}"
        elif array[0] == 0xCC:
            desc = "ACK from machine"
        elif array[0] == 0xCD:
            desc = "ERR from machine"
        elif array[0] == 0xCE:
            desc = "Keep Alive"
        elif array[0] == 0xD0:
            zone = array[1]
            desc = f"Set Inhale Zone {zone}"
        elif array[0] == 0xD7:
            self.plot_commit()
            try:
                self._driver.plot_start()
            except AttributeError:
                pass
            desc = "End Of File"
        elif array[0] == 0xD8:
            if array[1] == 0x00:
                desc = "Start Process"
            elif array[1] == 0x10:
                desc = "Ref Point Mode 2, Machine Zero/Absolute Position"
            elif array[1] == 0x11:
                desc = "Ref Point Mode 1, Anchor Point"
            elif array[1] == 0x12:
                desc = "Ref Point Mode 0, Current Position"
        elif array[0] == 0xD9:
            if array[1] == 0x00:
                opts = array[2]
                value = abscoord(array[3:8])
                desc = f"Rapid move X ({value}μm)"
            elif array[1] == 0x01:
                opts = array[2]
                value = abscoord(array[3:8])
                desc = f"Rapid move Y ({value}μm)"
            elif array[1] == 0x02:
                opts = array[2]
                value = abscoord(array[3:8])
                desc = f"Rapid move Z ({value}μm)"
            elif array[1] == 0x03:
                opts = array[2]
                value = abscoord(array[3:8])
                desc = f"Rapid move U ({value}μm)"
            elif array[1] == 0x0F:
                opts = array[2]
                value = abscoord(array[3:8])
                desc = f"Rapid move Feed ({value}μm)"
            elif array[1] == 0x10:
                opts = array[2]
                x = abscoord(array[3:8])
                y = abscoord(array[8:13])
                desc = f"Rapid move XY ({x}μm, {y}μm)"
            elif array[1] == 0x30:
                opts = array[2]
                x = abscoord(array[3:7])
                y = abscoord(array[8:13])
                u = abscoord(array[13:18])
                desc = f"Rapid move XYU ({x}μm, {y}μm, {u}μm)"
        elif array[0] == 0xDA:
            mem = parse_mem(array[2:4])
            if array[1] == 0x01:
                value0 = array[4:9]
                value1 = array[9:14]
                v0 = decodeu35(value0)
                v1 = decodeu35(value1)
                desc = f"Set {array[2]:02x} {array[3]:02x} (mem: {mem:04x})= {v0} (0x{v0:08x}) {v1} (0x{v1:08x})"
        elif array[0] == 0xE5:  # 0xE502
            if array[1] == 0x00:
                # RDWorks File Upload
                filenumber = array[2]
                desc = f"Document Page Number {filenumber}"
                # TODO: Requires Response.
            if array[1] == 0x02:
                # len 3
                desc = "Document Data End"
            elif array[1] == 0x05:
                _sum = decodeu35(array[2:7])
                desc = f"Set File Sum {_sum}"

        elif array[0] == 0xE6:
            if array[1] == 0x01:
                desc = "Set Absolute"
                # Only seen in Absolute Coords. MachineZero is Ref2 but does not Set Absolute.
        elif array[0] == 0xE7:
            if array[1] == 0x00:
                self.plot_commit()
                desc = "Block End"
            elif array[1] == 0x01:
                pass  # Set filename for job (only realtime, see emulator)
            elif array[1] == 0x03:
                c_x = abscoord(array[2:7])
                c_y = abscoord(array[7:12])
                desc = f"Process TopLeft ({c_x}μm, {c_y}μm)"
            elif array[1] == 0x04:
                v0 = decode14(array[2:4])
                v1 = decode14(array[4:6])
                v2 = decode14(array[6:8])
                v3 = decode14(array[8:10])
                v4 = decode14(array[10:12])
                v5 = decode14(array[12:14])
                v6 = decode14(array[14:16])
                desc = f"Process Repeat ({v0}, {v1}, {v2}, {v3}, {v4}, {v5}, {v6})"
            elif array[1] == 0x05:
                direction = array[2]
                desc = f"Array Direction ({direction})"
            elif array[1] == 0x06:
                v1 = decodeu35(array[2:7])
                v2 = decodeu35(array[7:12])
                desc = f"Feed Repeat ({v1}, {v2})"
            elif array[1] == 0x07:
                c_x = abscoord(array[2:7])
                c_y = abscoord(array[7:12])
                desc = f"Process BottomRight({c_x}μm, {c_y}μm)"
            elif array[1] == 0x08:  # Same value given to F2 04
                v0 = decode14(array[2:4])
                v1 = decode14(array[4:6])
                v2 = decode14(array[6:8])
                v3 = decode14(array[8:10])
                v4 = decode14(array[10:12])
                v5 = decode14(array[12:14])
                v6 = decode14(array[14:16])
                desc = f"Array Repeat ({v0}, {v1}, {v2}, {v3}, {v4}, {v5}, {v6})"
            elif array[1] == 0x09:
                v1 = decodeu35(array[2:7])
                desc = f"Feed Length {v1}"
            elif array[1] == 0x0A:
                desc = f"Feed Info"
            elif array[1] == 0x0B:
                v1 = array[2]
                desc = f"Array En Mirror Cut {v1}"
            elif array[1] == 0x0C:
                v1 = array[2]
                desc = f"Array Mirror Cut Distance {v1}"
            elif array[1] == 0x0C:
                v1 = array[2]
                desc = f"Set File Head Distance {v1}"
            elif array[1] == 0x13:
                c_x = abscoord(array[2:7])
                c_y = abscoord(array[7:12])
                desc = f"Array Min Point ({c_x}μm, {c_y}μm)"
            elif array[1] == 0x17:
                c_x = abscoord(array[2:7])
                c_y = abscoord(array[7:12])
                desc = f"Array Max Point ({c_x}μm, {c_y}μm)"
            elif array[1] == 0x23:
                c_x = abscoord(array[2:7])
                c_y = abscoord(array[7:12])
                desc = f"Array Add ({c_x}μm, {c_y}μm)"
            elif array[1] == 0x24:
                v1 = array[2]
                desc = f"Array Mirror {v1}"
            elif array[1] == 0x32:
                v1 = decodeu35(array[2:7])
                desc = f"Set Tick Count {v1}"
            elif array[1] == 0x35:
                v1 = decodeu35(array[2:7])
                v2 = decodeu35(array[7:12])
                desc = f"Block X Size {v1} {v2}"
            elif array[1] == 0x32:
                desc = f"Set File Empty"
            elif array[1] == 0x37:
                v1 = abscoord(array[2:7])
                v2 = abscoord(array[7:12])
                desc = f"Array Even Distance {v1} {v2}"
            elif array[1] == 0x38:
                v1 = array[2]
                desc = f"Set Feed Auto Pause {v1}"
            elif array[1] == 0x3A:
                desc = f"Union Block Property"
            elif array[1] == 0x3B:
                v1 = array[2]
                desc = f"Set File Property {v1}"
            elif array[1] == 0x46:
                desc = "BY Test 0x11227766"
            elif array[1] == 0x50:
                c_x = abscoord(array[1:6])
                c_y = abscoord(array[6:11])
                desc = f"Document Min Point({c_x}μm, {c_y}μm)"
            elif array[1] == 0x51:
                c_x = abscoord(array[2:7])
                c_y = abscoord(array[7:12])
                desc = f"Document Max Point({c_x}μm, {c_y}μm)"
            elif array[1] == 0x52:
                part = array[2]
                c_x = abscoord(array[3:8])
                c_y = abscoord(array[8:13])
                desc = f"{part}, Min Point({c_x}μm, {c_y}μm)"
            elif array[1] == 0x53:
                part = array[2]
                c_x = abscoord(array[3:8])
                c_y = abscoord(array[8:13])
                desc = f"{part}, MaxPoint({c_x}μm, {c_y}μm)"
            elif array[1] == 0x54:
                axis = array[2]
                c_x = abscoord(array[3:8])
                desc = f"Pen Offset {axis}: {c_x}μm"
            elif array[1] == 0x55:
                axis = array[2]
                c_x = abscoord(array[3:8])
                desc = f"Layer Offset {axis}: {c_x}μm"
            elif array[1] == 0x57:
                desc = f"PList Feed"
            elif array[1] == 0x60:
                desc = f"Set Current Element Index ({array[2]})"
            elif array[1] == 0x61:
                part = array[2]
                c_x = abscoord(array[3:8])
                c_y = abscoord(array[8:13])
                desc = f"{part}, MinPointEx({c_x}μm, {c_y}μm)"
            elif array[1] == 0x62:
                part = array[2]
                c_x = abscoord(array[3:8])
                c_y = abscoord(array[8:13])
                desc = f"{part}, MaxPointEx({c_x}μm, {c_y}μm)"
        elif array[0] == 0xE8:
            # Realtime command.
            pass
        elif array[0] == 0xEA:
            index = array[1]
            desc = f"Array Start ({index})"
        elif array[0] == 0xEB:
            desc = "Array End"
        elif array[0] == 0xF0:
            desc = "Ref Point Set"
        elif array[0] == 0xF1:
            if array[1] == 0x00:
                index = array[2]
                desc = f"Element Max Index ({index})"
            elif array[1] == 0x01:
                index = array[2]
                desc = f"Element Name Max Index({index})"
            elif array[1] == 0x02:
                enable = array[2]
                desc = f"Enable Block Cutting ({enable})"
            elif array[1] == 0x03:
                c_x = abscoord(array[2:7])
                c_y = abscoord(array[7:12])
                desc = f"Display Offset ({c_x}μm, {c_y}μm)"
            elif array[1] == 0x04:
                enable = array[2]
                desc = f"Feed Auto Calc ({enable})"
            elif array[1] == 0x20:
                desc = f"Unknown ({array[2]},{array[3]})"
        elif array[0] == 0xF2:
            if array[1] == 0x00:
                index = array[2]
                desc = f"Element Index ({index})"
            if array[1] == 0x01:
                index = array[2]
                desc = f"Element Name Index ({index})"
            if array[1] == 0x02:
                name = bytes(array[2:12])
                desc = f"Element Name ({str(name)})"
            if array[1] == 0x03:
                c_x = abscoord(array[2:7])
                c_y = abscoord(array[7:12])
                desc = f"Element Array Min Point ({c_x}μm, {c_y}μm)"
            if array[1] == 0x04:
                c_x = abscoord(array[2:7])
                c_y = abscoord(array[7:12])
                desc = f"Element Array Max Point ({c_x}μm, {c_y}μm)"
            if array[1] == 0x05:
                v0 = decode14(array[2:4])
                v1 = decode14(array[4:6])
                v2 = decode14(array[6:8])
                v3 = decode14(array[8:10])
                v4 = decode14(array[10:12])
                v5 = decode14(array[12:14])
                v6 = decode14(array[14:16])
                desc = f"Element Array ({v0}, {v1}, {v2}, {v3}, {v4}, {v5}, {v6})"
            if array[1] == 0x06:
                c_x = abscoord(array[2:7])
                c_y = abscoord(array[7:12])
                desc = f"Element Array Add ({c_x}μm, {c_y}μm)"
            if array[1] == 0x07:
                index = array[2]
                desc = f"Element Array Mirror ({index})"
        else:
            desc = "Unknown Command!"
        if self.channel:
            prefix = f"{offset:06x}" if offset is not None else ''
            self.channel(f"{prefix}-**-> {str(bytes(array).hex())}\t({desc})")

    def unswizzle(self, data):
        return bytes([self.lut_unswizzle[b] for b in data])

    def swizzle(self, data):
        return bytes([self.lut_swizzle[b] for b in data])

    def _calculate_layer_bounds(self, layer):
        max_x = float("-inf")
        max_y = float("-inf")
        min_x = float("inf")
        min_y = float("inf")
        for item in layer:
            try:
                ny = item.upper()
                nx = item.left()

                my = item.lower()
                mx = item.right()
            except AttributeError:
                continue

            if mx > max_x:
                max_x = mx
            if my > max_y:
                max_y = my
            if nx < min_x:
                min_x = nx
            if ny < min_y:
                min_y = ny
        return min_x, min_y, max_x, max_y

    def write_header(self, data):
        if not data:
            return
        # Optional: Set Tick count.
        self.ref_point_2()  # abs_pos
        self.set_absolute()
        self.ref_point_set()
        self.enable_block_cutting(0)
        # Optional: Set File Property 1
        self.start_process()
        self.feed_repeat(0, 0)
        self.set_feed_auto_pause(0)
        b = self._calculate_layer_bounds(data)
        min_x, min_y, max_x, max_y = b
        self.process_top_left(min_x, min_y)
        self.process_bottom_right(max_x, max_y)
        self.document_min_point(0, 0)  # Unknown
        self.document_max_point(max_x, max_y)
        self.process_repeat(1, 1, 0, 0, 0, 0, 0)
        self.array_direction(0)
        last_settings = None
        layers = list()

        # Sort out data by layers.
        for item in data:
            if not hasattr(item, "settings"):
                continue
            current_settings = item.settings
            if last_settings is not current_settings:
                if "part" not in current_settings:
                    current_settings["part"] = len(layers)
                    layers.append(list())
            layers[current_settings["part"]].append(item)

        part = 0
        # Write layer Information
        for layer in layers:
            (
                layer_min_x,
                layer_min_y,
                layer_max_x,
                layer_max_y,
            ) = self._calculate_layer_bounds(layer)
            current_settings = layer[0].settings

            # Current Settings is New.
            part = current_settings.get("part", 0)
            speed = current_settings.get("speed", 10)
            power = current_settings.get("power", 1000) / 10.0
            color = current_settings.get("line_color", 0)
            frequency = current_settings.get("frequency")

            if color == 0:
                color = current_settings.get("color", color)

            self.speed_laser_1_part(part, speed)
            if frequency:
                self.frequency_part(0, part, frequency)
            self.min_power_1_part(part, power)
            self.max_power_1_part(part, power)
            self.min_power_2_part(part, power)
            self.max_power_2_part(part, power)
            self.layer_color_part(part, color)
            self.work_mode_part(part, 0)
            self.part_min_point(part, layer_min_x, layer_min_y)
            self.part_max_point(part, layer_max_x, layer_max_y)
            self.part_min_point_ex(part, layer_min_x, layer_min_y)
            self.part_max_point_ex(part, layer_max_x, layer_max_y)
        self.max_layer_part(part)
        self.pen_offset(0, 0)
        self.pen_offset(1, 0)
        self.layer_offset(0, 0)
        self.layer_offset(1, 0)
        self.display_offset(0, 0)

        # Element Info
        # self.encoder.element_max_index(0)
        # self.encoder.element_name_max_index(0)
        # self.encoder.element_index(0)
        # self.encoder.element_name_max_index(0)
        # self.encoder.element_name('\x05*9\x1cA\x04j\x15\x08 ')
        # self.encoder.element_array_min_point(min_x, min_y)
        # self.encoder.element_array_max_point(max_x, max_y)
        # self.encoder.element_array(1, 1, 0, 257, -3072, 2, 5232)
        # self.encoder.element_array_add(0,0)
        # self.encoder.element_array_mirror(0)

        self.feed_info(0)

        # Array Info
        array_index = 0
        self.array_start(array_index)
        self.set_current_element_index(array_index)
        self.array_en_mirror_cut(array_index)
        self.array_min_point(min_x, min_y)
        self.array_max_point(max_x, max_y)
        self.array_add(0, 0)
        self.array_mirror(0)
        # self.encoder.array_even_distance(0)  # Unknown.
        self.array_repeat(1, 1, 0, 1123, -3328, 4, 3480)  # Unknown.
        # Layer and cut information.

    def write_settings(self, current_settings):
        part = current_settings.get("part", 0)
        speed = current_settings.get("speed", 0)
        power = current_settings.get("power", 0) / 10.0
        air = current_settings.get("coolant", 0)
        self.layer_end()
        self.layer_number_part(part)
        self.laser_device_0()
        if air == 1:
            self.air_assist_on()
        elif air==2:
            self.air_assist_off()
        self.speed_laser_1(speed)
        self.laser_on_delay(0)
        self.laser_off_delay(0)
        self.min_power_1(power)
        self.max_power_1(power)
        self.min_power_2(power)
        self.max_power_2(power)
        self.en_laser_tube_start()
        self.en_ex_io(0)

    def write_tail(self):
        # End layer and cut information.
        self.array_end()
        self.block_end()
        # self.encoder.set_setting(0x320, 142, 142)
        self.set_file_sum(self.file_sum())
        self.end_of_file()

    def jump(self, x, y, dx, dy):
        if dx == 0 and dy == 0:
            # We are not moving.
            return

        if abs(dx) > 8192 or abs(dy) > 8192:
            # Exceeds encoding limit, use abs.
            self.move_abs_xy(x, y)
            return

        if dx == 0:
            # Y-relative.
            self.move_rel_y(dy)
            return
        if dy == 0:
            # X-relative.
            self.move_rel_x(dx)
            return
        self.move_rel_xy(dx, dy)

    def mark(self, x, y, dx, dy):
        if dx == 0 and dy == 0:
            # We are not moving.
            return

        if abs(dx) > 8192 or abs(dy) > 8192:
            # Exceeds encoding limit, use abs.
            self.cut_abs_xy(x, y)
            return

        if dx == 0:
            # Y-relative.
            self.cut_rel_y(dy)
            return
        if dy == 0:
            # X-relative.
            self.cut_rel_x(dx)
            return
        self.cut_rel_xy(dx, dy)

    #######################
    # Specific Commands
    #######################

    def axis_x_move(self, x, output=None):
        self(AXIS_X_MOVE, encode32(x), output=output)

    def axis_z_move(self, z, output=None):
        self(AXIS_Z_MOVE, encode32(z), output=output)

    def axis_a_move(self, a, output=None):
        self(AXIS_A_MOVE, encode32(a), output=output)

    def axis_u_move(self, u, output=None):
        self(AXIS_U_MOVE, encode32(u), output=output)

    def move_abs_xy(self, x, y, output=None):
        self(MOVE_ABS_XY, encode_coord(x), encode_coord(y), output=output)

    def move_rel_xy(self, dx, dy, output=None):
        self(MOVE_REL_XY, encode_relcoord(dx), encode_relcoord(dy), output=output)

    def move_rel_x(self, dx, output=None):
        self(MOVE_REL_X, encode_relcoord(dx), output=output)

    def move_rel_y(self, dy, output=None):
        self(MOVE_REL_Y, encode_relcoord(dy), output=output)

    def cut_abs_xy(self, x, y, output=None):
        self(CUT_ABS_XY, encode_coord(x), encode_coord(y), output=output)

    def cut_rel_xy(self, dx, dy, output=None):
        self(CUT_REL_XY, encode_relcoord(dx), encode_relcoord(dy), output=output)

    def cut_rel_x(self, dx, output=None):
        self(CUT_REL_X, encode_relcoord(dx), output=output)

    def cut_rel_y(self, dy, output=None):
        self(CUT_REL_Y, encode_relcoord(dy), output=output)

    def imd_power_1(self, power, output=None):
        self(IMD_POWER_1, encode_power(power), output=output)

    def imd_power_2(self, power, output=None):
        self(IMD_POWER_2, encode_power(power), output=output)

    def imd_power_3(self, power, output=None):
        self(IMD_POWER_3, encode_power(power), output=output)

    def imd_power_4(self, power, output=None):
        self(IMD_POWER_4, encode_power(power), output=output)

    def end_power_1(self, power, output=None):
        self(END_POWER_1, encode_power(power), output=output)

    def end_power_2(self, power, output=None):
        self(END_POWER_2, encode_power(power), output=output)

    def end_power_3(self, power, output=None):
        self(END_POWER_3, encode_power(power), output=output)

    def end_power_4(self, power, output=None):
        self(END_POWER_4, encode_power(power), output=output)

    def min_power_1(self, power, output=None):
        self(MIN_POWER_1, encode_power(power), output=output)

    def max_power_1(self, power, output=None):
        self(MAX_POWER_1, encode_power(power), output=output)

    def min_power_2(self, power, output=None):
        self(MIN_POWER_2, encode_power(power), output=output)

    def max_power_2(self, power, output=None):
        self(MAX_POWER_2, encode_power(power), output=output)

    def min_power_3(self, power, output=None):
        self(MIN_POWER_3, encode_power(power), output=output)

    def max_power_3(self, power, output=None):
        self(MAX_POWER_3, encode_power(power), output=output)

    def min_power_4(self, power, output=None):
        self(MIN_POWER_4, encode_power(power), output=output)

    def max_power_4(self, power, output=None):
        self(MAX_POWER_4, encode_power(power), output=output)

    def laser_interval(self, time, output=None):
        self(LASER_INTERVAL, encode_time(time), output=output)

    def add_delay(self, time, output=None):
        self(ADD_DELAY, encode_time(time), output=output)

    def laser_on_delay(self, time, output=None):
        self(LASER_ON_DELAY, encode_time(time), output=output)

    def laser_off_delay(self, time, output=None):
        self(LASER_OFF_DELAY, encode_time(time), output=output)

    def laser_on_delay_2(self, time, output=None):
        self(LASER_ON_DELAY2, encode_time(time), output=output)

    def laser_off_delay_2(self, time, output=None):
        self(LASER_OFF_DELAY2, encode_time(time), output=output)

    def min_power_1_part(self, part, power, output=None):
        self(MIN_POWER_1_PART, encode_part(part), encode_power(power), output=output)

    def max_power_1_part(self, part, power, output=None):
        self(MAX_POWER_1_PART, encode_part(part), encode_power(power), output=output)

    def min_power_2_part(self, part, power, output=None):
        self(MIN_POWER_2_PART, encode_part(part), encode_power(power), output=output)

    def max_power_2_part(self, part, power, output=None):
        self(MAX_POWER_2_PART, encode_part(part), encode_power(power), output=output)

    def min_power_3_part(self, part, power, output=None):
        self(MIN_POWER_3_PART, encode_part(part), encode_power(power), output=output)

    def max_power_3_part(self, part, power, output=None):
        self(MAX_POWER_3_PART, encode_part(part), encode_power(power), output=output)

    def min_power_4_part(self, part, power, output=None):
        self(MIN_POWER_4_PART, encode_part(part), encode_power(power), output=output)

    def max_power_4_part(self, part, power, output=None):
        self(MAX_POWER_4_PART, encode_part(part), encode_power(power), output=output)

    def through_power_1(self, power, output=None):
        """
        This is the power used for the Laser On / Laser Off Delay.

        @param power:
        @param output:
        @return:
        """
        self(THROUGH_POWER_1, encode_power(power), output=output)

    def through_power_2(self, power, output=None):
        self(THROUGH_POWER_2, encode_power(power), output=output)

    def through_power_3(self, power, output=None):
        self(THROUGH_POWER_3, encode_power(power), output=output)

    def through_power_4(self, power, output=None):
        self(THROUGH_POWER_4, encode_power(power), output=output)

    def frequency_part(self, laser, part, frequency, output=None):
        self(
            FREQUENCY_PART,
            encode_index(laser),
            encode_part(part),
            encode_frequency(frequency),
            output=output,
        )

    def speed_laser_1(self, speed, output=None):
        self(SPEED_LASER_1, encode_speed(speed), output=output)

    def speed_axis(self, speed, output=None):
        self(SPEED_AXIS, encode_speed(speed), output=output)

    def speed_laser_1_part(self, part, speed, output=None):
        self(SPEED_LASER_1_PART, encode_part(part), encode_speed(speed), output=output)

    def force_eng_speed(self, speed, output=None):
        self(FORCE_ENG_SPEED, encode_speed(speed), output=output)

    def speed_axis_move(self, speed, output=None):
        self(SPEED_AXIS_MOVE, encode_speed(speed), output=output)

    def layer_end(self, output=None):
        self(LAYER_END, output=output)

    def work_mode_1(self, output=None):
        self(WORK_MODE_1, output=output)

    def work_mode_2(self, output=None):
        self(WORK_MODE_2, output=output)

    def work_mode_3(self, output=None):
        self(WORK_MODE_3, output=output)

    def work_mode_4(self, output=None):
        self(WORK_MODE_4, output=output)

    def work_mode_5(self, output=None):
        self(WORK_MODE_5, output=output)

    def work_mode_6(self, output=None):
        self(WORK_MODE_6, output=output)

    def laser_device_0(self, output=None):
        self(LASER_DEVICE_0, output=output)

    def laser_device_1(self, output=None):
        self(LASER_DEVICE_1, output=output)

    def air_assist_off(self, output=None):
        self(AIR_ASSIST_OFF, output=output)

    def air_assist_on(self, output=None):
        self(AIR_ASSIST_ON, output=output)

    def db_head(self, output=None):
        self(DB_HEAD, output=output)

    def en_laser_2_offset_0(self, output=None):
        self(EN_LASER_2_OFFSET_0, output=output)

    def en_laser_2_offset_1(self, output=None):
        self(EN_LASER_2_OFFSET_1, output=output)

    def layer_number_part(self, part, output=None):
        self(LAYER_NUMBER_PART, encode_part(part), output=output)

    def en_laser_tube_start(self, output=None):
        self(EN_LASER_TUBE_START, output=output)

    def x_sign_map(self, value, output=None):
        self(X_SIGN_MAP, encode_index(value), output=output)

    def layer_color(self, color, output=None):
        self(LAYER_COLOR, encode_color(color), output=output)

    def layer_color_part(self, part, color, output=None):
        self(LAYER_COLOR_PART, encode_part(part), encode_color(color), output=output)

    def en_ex_io(self, value, output=None):
        """
        Enable External IO.

        @param value:
        @param output:
        @return:
        """
        self(EN_EX_IO, encode_index(value), output=output)

    def max_layer_part(self, part, output=None):
        self(MAX_LAYER_PART, encode_part(part), output=output)

    def u_file_id(self, file_number, output=None):
        self(MAX_LAYER_PART, encode_file_number(file_number), output=output)

    def zu_map(self, value, output=None):
        self(ZU_MAP, encode_index(value), output=output)

    def work_mode_part(self, part, mode, output=None):
        self(WORK_MODE_PART, encode_part(part), encode_index(mode), output=output)

    def ack(self, output=None):
        self(ACK, output=output)

    def err(self, output=None):
        self(ERR, output=output)

    def keep_alive(self, output=None):
        self(KEEP_ALIVE, output=output)

    def end_of_file(self, output=None):
        self(END_OF_FILE, output=output)

    def start_process(self, output=None):
        self(START_PROCESS, output=output)

    def stop_process(self, output=None):
        self(STOP_PROCESS, output=output)

    def pause_process(self, output=None):
        self(PAUSE_PROCESS, output=output)

    def restore_process(self, output=None):
        self(RESTORE_PROCESS, output=output)

    def ref_point_2(self, output=None):
        """
        Machine zero. Absolute position.
        @return:
        """
        self(REF_POINT_2, output=output)

    def ref_point_1(self, output=None):
        """
        Anchor Point, Origin.
        @return:
        """
        self(REF_POINT_1, output=output)

    def ref_point_0(self, output=None):
        """
        Current position.

        @return:
        """
        self(REF_POINT_0, output=output)

    def home_z(self, output=None):
        self(HOME_Z, output=output)

    def home_u(self, output=None):
        self(HOME_U, output=output)

    def home_xy(self, output=None):
        self(HOME_XY, output=output)

    def focus_z(self, output=None):
        self(FOCUS_Z, output=output)

    def keydown_x_left(self, output=None):
        self(KEYDOWN_X_LEFT, output=output)

    def keyup_x_left(self, output=None):
        self(KEYUP_X_LEFT, output=output)

    def keydown_x_right(self, output=None):
        self(KEYDOWN_X_RIGHT, output=output)

    def keyup_x_right(self, output=None):
        self(KEYUP_X_RIGHT, output=output)

    def keydown_y_top(self, output=None):
        self(KEYDOWN_Y_TOP, output=output)

    def keyup_y_top(self, output=None):
        self(KEYUP_Y_TOP, output=output)

    def keydown_y_bottom(self, output=None):
        self(KEYDOWN_Y_BOTTOM, output=output)

    def keyup_y_bottom(self, output=None):
        self(KEYUP_Y_BOTTOM, output=output)

    def keydown_z_up(self, output=None):
        self(KEYDOWN_Z_UP, output=output)

    def keyup_z_up(self, output=None):
        self(KEYUP_Z_UP, output=output)

    def keydown_z_down(self, output=None):
        self(KEYDOWN_Z_DOWN, output=output)

    def keyup_z_down(self, output=None):
        self(KEYUP_Z_DOWN, output=output)

    def _rapid_options(self, light=False, origin=False):
        if light and origin:
            return RAPID_OPTION_LIGHTORIGIN
        if light and not origin:
            return RAPID_OPTION_LIGHT
        if origin:
            return RAPID_OPTION_ORIGIN
        return RAPID_OPTION_NONE

    def rapid_move_x(self, x, light=False, origin=False, output=None):
        self(
            RAPID_MOVE_X,
            self._rapid_options(light=light, origin=origin),
            encode_coord(x),
            output=output,
        )

    def rapid_move_y(self, y, light=False, origin=False, output=None):
        self(
            RAPID_MOVE_Y,
            self._rapid_options(light=light, origin=origin),
            encode_coord(y),
            output=output,
        )

    def rapid_move_z(self, z, light=False, origin=False, output=None):
        self(
            RAPID_MOVE_Z,
            self._rapid_options(light=light, origin=origin),
            encode_coord(z),
            output=output,
        )

    def rapid_move_u(self, u, light=False, origin=False, output=None):
        self(
            RAPID_MOVE_U,
            self._rapid_options(light=light, origin=origin),
            encode_coord(u),
            output=output,
        )

    def rapid_move_xy(self, x, y, light=False, origin=False, output=None):
        self(
            RAPID_MOVE_XY,
            self._rapid_options(light=light, origin=origin),
            encode_coord(x),
            encode_coord(y),
            output=output,
        )

    def rapid_move_xyu(self, x, y, u, light=False, origin=False, output=None):
        self(
            RAPID_MOVE_XYU,
            self._rapid_options(light=light, origin=origin),
            encode_coord(x),
            encode_coord(y),
            encode_coord(u),
            output=output,
        )

    def rapid_feed_axis(self, light=False, origin=False, output=None):
        self(
            RAPID_FEED_AXIS_MOVE,
            self._rapid_options(light=light, origin=origin),
            output=output,
        )

    def get_setting(self, mem, output=None):
        self(GET_SETTING, encode_mem(mem), output=output)

    def set_setting(self, mem, value, output=None):
        self(
            SET_SETTING,
            encode_mem(mem),
            encode_value(value),
            encode_value(value),
            output=output,
        )

    def document_file_upload(self, file_number, value, value1, output=None):
        self(
            DOCUMENT_FILE_UPLOAD,
            encode_value(value),
            encode_value(value1),
            output=output,
        )

    def document_file_end(self, output=None):
        self(DOCUMENT_FILE_END, output=output)

    def set_file_sum(self, value, output=None):
        self(SET_FILE_SUM, encode_value(value), output=output)

    def set_absolute(self, output=None):
        self(SET_ABSOLUTE, output=output)

    def block_end(self, output=None):
        self(BLOCK_END, output=output)

    def set_filename(self, filename, output=None):
        self(
            SET_FILENAME, bytes(filename[:9], encoding="utf-8"), b"\x00", output=output
        )

    def process_top_left(self, top, left, output=None):
        self(PROCESS_TOP_LEFT, encode_coord(top), encode_coord(left), output=output)

    def process_repeat(self, v0, v1, v2, v3, v4, v5, v6, output=None):
        self(
            PROCESS_REPEAT,
            encode14(v0),
            encode14(v1),
            encode14(v2),
            encode14(v3),
            encode14(v4),
            encode14(v5),
            encode14(v6),
            output=output,
        )

    def array_direction(self, direction, output=None):
        self(ARRAY_DIRECTION, encode_index(direction), output=output)

    def feed_repeat(self, value, value1, output=None):
        self(FEED_REPEAT, encode32(value), encode32(value1), output=output)

    def process_bottom_right(self, bottom, right, output=None):
        self(
            PROCESS_BOTTOM_RIGHT,
            encode_coord(bottom),
            encode_coord(right),
            output=output,
        )

    def array_repeat(self, v0, v1, v2, v3, v4, v5, v6, output=None):
        self(
            ARRAY_REPEAT,
            encode14(v0),
            encode14(v1),
            encode14(v2),
            encode14(v3),
            encode14(v4),
            encode14(v5),
            encode14(v6),
            output=output,
        )

    def feed_length(self, length, output=None):
        self(FEED_LENGTH, encode32(length), output=output)

    def feed_info(self, value, output=None):
        self(FEED_INFO, encode_value(value), output=output)

    def array_en_mirror_cut(self, index, output=None):
        self(ARRAY_EN_MIRROR_CUT, encode_index(index), output=output)

    def array_min_point(self, min_x, min_y, output=None):
        self(ARRAY_MIN_POINT, encode_coord(min_x), encode_coord(min_y), output=output)

    def array_max_point(self, max_x, max_y, output=None):
        self(ARRAY_MAX_POINT, encode_coord(max_x), encode_coord(max_y), output=output)

    def array_add(self, x, y, output=None):
        self(ARRAY_ADD, encode_coord(x), encode_coord(y), output=output)

    def array_mirror(self, mirror, output=None):
        self(ARRAY_MIRROR, encode_index(mirror), output=output)

    def block_x_size(self, x0, x1, output=None):
        self(BLOCK_X_SIZE, encode_coord(x0), encode_coord(x1), output=output)

    def by_test(self, output=None):
        self(BY_TEST, encode32(0x11227766), output=output)

    def array_even_distance(self, max_x, max_y, output=None):
        self(
            ARRAY_EVEN_DISTANCE, encode_coord(max_x), encode_coord(max_y), output=output
        )

    def set_feed_auto_pause(self, index, output=None):
        self(SET_FEED_AUTO_PAUSE, encode_index(index), output=output)

    def union_block_property(self, output=None):
        self(UNION_BLOCK_PROPERTY, output=output)

    def document_min_point(self, min_x, min_y, output=None):
        self(
            DOCUMENT_MIN_POINT, encode_coord(min_x), encode_coord(min_y), output=output
        )

    def document_max_point(self, max_x, max_y, output=None):
        self(
            DOCUMENT_MAX_POINT, encode_coord(max_x), encode_coord(max_y), output=output
        )

    def part_min_point(self, part, min_x, min_y, output=None):
        self(
            PART_MIN_POINT,
            encode_part(part),
            encode_coord(min_x),
            encode_coord(min_y),
            output=output,
        )

    def part_max_point(self, part, max_x, max_y, output=None):
        self(
            PART_MAX_POINT,
            encode_part(part),
            encode_coord(max_x),
            encode_coord(max_y),
            output=output,
        )

    def pen_offset(self, axis, coord, output=None):
        self(PEN_OFFSET, encode_index(axis), encode_coord(coord), output=output)

    def layer_offset(self, axis, coord, output=None):
        self(LAYER_OFFSET, encode_index(axis), encode_coord(coord), output=output)

    def set_current_element_index(self, index, output=None):
        self(SET_CURRENT_ELEMENT_INDEX, encode_index(index), output=output)

    def part_min_point_ex(self, part, min_x, min_y, output=None):
        self(
            PART_MIN_POINT_EX,
            encode_part(part),
            encode_coord(min_x),
            encode_coord(min_y),
            output=output,
        )

    def part_max_point_ex(self, part, max_x, max_y, output=None):
        self(
            PART_MAX_POINT_EX,
            encode_part(part),
            encode_coord(max_x),
            encode_coord(max_y),
            output=output,
        )

    def array_start(self, index, output=None):
        self(ARRAY_START, encode_index(index), output=output)

    def array_end(self, output=None):
        self(ARRAY_END, output=output)

    def ref_point_set(self, output=None):
        self(REF_POINT_SET, output=output)

    def element_max_index(self, index, output=None):
        self(ELEMENT_MAX_INDEX, encode_index(index), output=output)

    def element_name_max_index(self, index, output=None):
        self(ELEMENT_NAME_MAX_INDEX, encode_index(index), output=output)

    def enable_block_cutting(self, enable, output=None):
        self(ENABLE_BLOCK_CUTTING, encode_index(enable), output=output)

    def display_offset(self, dx, dy, output=None):
        self(DISPLAY_OFFSET, encode_coord(dx), encode_coord(dy), output=output)

    def feed_auto_calc(self, enable, output=None):
        self(FEED_AUTO_CALC, encode_index(enable), output=output)

    def element_index(self, index, output=None):
        self(ELEMENT_INDEX, encode_index(index), output=output)

    def element_name(self, name, output=None):
        self(ELEMENT_NAME, bytes(name[:9], encoding="utf-8"), b"\x00", output=output)

    def element_array_min_point(self, x, y, output=None):
        self(ELEMENT_ARRAY_MIN_POINT, encode_coord(x), encode_coord(y), output=output)

    def element_array_max_point(self, x, y, output=None):
        self(ELEMENT_ARRAY_MAX_POINT, encode_coord(x), encode_coord(y), output=output)

    def element_array(self, v0, v1, v2, v3, v4, v5, v6, output=None):
        self(
            ELEMENT_ARRAY,
            encode14(v0),
            encode14(v1),
            encode14(v2),
            encode14(v3),
            encode14(v4),
            encode14(v5),
            encode14(v6),
            output=output,
        )

    def element_array_add(self, x, y, output=None):
        self(ELEMENT_ARRAY_ADD, encode_coord(x), encode_coord(y), output=output)

    def element_array_mirror(self, mirror, output=None):
        self(ELEMENT_ARRAY_MIRROR, encode_index(mirror), output=output)
