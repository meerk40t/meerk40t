"""
Ruida Controller

The balor controller takes low level ruida commands and converts them into hardware control signals for
the hardware controller.
"""

import struct
import time

from meerk40t.ruida.mock_connection import MockConnection
from meerk40t.ruida.rdjob import encode32, encode14

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
WORK_MODE_PART = b"\xCA\x40"  # part(1), mode(1)
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
UNKNOWN_1 = b"\xE7\x0B"  # value(5)
ARRAY_MIN_POINT = b"\xE7\x13"  # abscoord(5), abscoord(5)
ARRAY_MAX_POINT = b"\xE7\x17"  # abscoord(5), abscoord(5)
ARRAY_ADD = b"\xE7\x23"  # abscoord(5), abscoord(5)
ARRAY_MIRROR = b"\xE7\x24"  # mirror(1)
BLOCK_X_SIZE = b"\xE7\x35"  # abscoord(5), abscoord(5)
BY_TEST = b"\xE7\x35"  # 0x11227766
DOCUMENT_MIN_POINT = b"\xE7\x50"  # abscoord(5), abscoord(5)
DOCUMENT_MAX_POINT = b"\xE7\x51"  # abscoord(5), abscoord(5)
PART_MIN_POINT = b"\xE7\x52"  # part(1), abscoord(5), abscoord(5)
PART_MAX_POINT = b"\xE7\x53"  # part(1), abscoord(5), abscoord(5)
PEN_OFFSET = b"\xE7\x54"  # axis(1), coord(5)
LAYER_OFFSET = b"\xE7\x55"  # axis(1), coord(5)
SET_CURRENT_ELEMENT_INDEX = b"\xE7\x55"  # index(1)
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


def encode_part(part):
    assert 0 <= part <= 255
    return part


def encode_index(index):
    assert 0 <= index <= 255
    return index


def encode_coord(coord):
    return encode32(coord)


def encode_color(color):
    return encode32(int(color))


def encode_file_number(file_number):
    return encode14(file_number)


def encode_mem(file_number):
    return encode14(file_number)


def encode_value(value):
    return encode32(value)


def encode_power(power):
    return encode32(power)


def encode_speed(speed):
    return encode32(speed)


class RuidaController:
    """
    Ruida controller is tasked with sending queued data to the controller board and ensuring that the connection to the
    controller board is established to perform these actions.

    This also hides the underlying methods for ruida file types.
    """

    def __init__(
        self,
        service,
        force_mock=False,
    ):
        self.service = service
        self.is_shutdown = False  # Shutdown finished.
        self.force_mock = force_mock

        name = self.service.label
        self.usb_log = service.channel(f"{name}/usb", buffer_size=500)
        self.usb_log.watch(lambda e: service.signal("pipe;usb_status", e))

        self.connection = None
        self.mode = "init"
        self.paused = False
        self._is_opening = False
        self._abort_open = False
        self._disable_connect = False
        self._machine_index = 0
        self._last_x = 0
        self._last_y = 0

    def __call__(self, *args, **kwargs):
        pass

    @property
    def state(self):
        return "idle", "idle"

    def set_disable_connect(self, status):
        self._disable_connect = status

    def added(self):
        pass

    def service_detach(self):
        pass

    def shutdown(self, *args, **kwargs):
        self.is_shutdown = True

    @property
    def connected(self):
        if self.connection is None:
            return False
        return self.connection.is_open(self._machine_index)

    @property
    def is_connecting(self):
        if self.connection is None:
            return False
        return self._is_opening

    def abort_connect(self):
        self._abort_open = True
        self.usb_log("Connect Attempts Aborted")

    def disconnect(self):
        try:
            self.connection.close(self._machine_index)
        except (ConnectionError, ConnectionRefusedError, AttributeError):
            pass
        self.connection = None
        # Reset error to allow another attempt
        self.set_disable_connect(False)

    def connect_if_needed(self):
        if self._disable_connect:
            # After many failures automatic connects are disabled. We require a manual connection.
            self.abort_connect()
            self.connection = None
            raise ConnectionRefusedError(
                "Ruida device was unreachable. Explicit connect required."
            )
        if self.connection is None:
            self.connection = MockConnection(self.usb_log)
            name = self.service.label
            self.connection.send = self.service.channel(f"{name}/send")
            self.connection.recv = self.service.channel(f"{name}/recv")
            # TODO: Needs usbconnection and udp connection.
            # self.connection = USBConnection(self.usb_log)
        self._is_opening = True
        self._abort_open = False
        count = 0
        while not self.connection.is_open(self._machine_index):
            try:
                if self.connection.open(self._machine_index) < 0:
                    raise ConnectionError
                self.init_laser()
            except (ConnectionError, ConnectionRefusedError):
                time.sleep(0.3)
                count += 1
                # self.usb_log(f"Error-Routine pass #{count}")
                if self.is_shutdown or self._abort_open:
                    self._is_opening = False
                    self._abort_open = False
                    return
                if self.connection.is_open(self._machine_index):
                    self.connection.close(self._machine_index)
                if count >= 10:
                    # We have failed too many times.
                    self._is_opening = False
                    self.set_disable_connect(True)
                    self.usb_log("Could not connect to the Ruida controller.")
                    self.usb_log("Automatic connections disabled.")
                    raise ConnectionRefusedError(
                        "Could not connect to the Ruida controller."
                    )
                time.sleep(0.3)
                continue
        self._is_opening = False
        self._abort_open = False

    def send(self, data, read=True):
        if self.is_shutdown:
            return -1, -1, -1, -1
        self.connect_if_needed()
        try:
            self.connection.write(self._machine_index, data)
        except ConnectionError:
            return -1, -1, -1, -1
        if read:
            try:
                r = self.connection.read(self._machine_index)
                return struct.unpack("<4H", r)
            except ConnectionError:
                return -1, -1, -1, -1

    def status(self):
        b0, b1, b2, b3 = self.get_version()
        return b3

    #######################
    # MODE SHIFTS
    #######################

    def rapid_mode(self):
        if self.mode == "rapid":
            return
        self.mode = "rapid"

    def raster_mode(self):
        self.program_mode()

    def program_mode(self):
        if self.mode == "rapid":
            return
        self.mode = "program"

    #######################
    # SETS FOR PLOTLIKES
    #######################

    def set_settings(self, settings):
        """
        Sets the primary settings. Rapid, frequency, speed, and timings.

        @param settings: The current settings dictionary
        @return:
        """
        pass

    #######################
    # PLOTLIKE SHORTCUTS
    #######################

    def mark(self, x, y):
        if x == self._last_x and y == self._last_y:
            return
        self._last_x, self._last_y = x, y

    def goto(self, x, y, long=None, short=None, distance_limit=None):
        if x == self._last_x and y == self._last_y:
            return
        self._last_x, self._last_y = x, y

    def set_xy(self, x, y):
        pass

    def get_last_xy(self):
        return self._last_x, self._last_y

    #######################
    # Command Shortcuts
    #######################

    def wait_finished(self):
        pass

    def wait_ready(self):
        pass

    def wait_idle(self):
        pass

    def abort(self):
        self.mode = "rapid"

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def init_laser(self):
        self.usb_log("Ready")

    #######################
    # Specific Commands
    #######################

    def axis_x_move(self, x):
        self(AXIS_X_MOVE)
        self(encode32(x))

    def axis_z_move(self, z):
        self(AXIS_Z_MOVE)
        self(encode32(z))

    def axis_a_move(self, a):
        self(AXIS_A_MOVE)
        self(encode32(a))

    def axis_u_move(self, u):
        self(AXIS_U_MOVE)
        self(encode32(u))

    def move_abs_xy(self, x, y):
        self(MOVE_ABS_XY)
        self(encode32(x))
        self(encode32(y))

    def move_rel_xy(self, dx, dy):
        self(MOVE_REL_XY)
        self(encode14(dx))
        self(encode14(dy))

    def move_rel_x(self, dx):
        self(MOVE_REL_X)
        self(encode14(dx))

    def move_rel_y(self, dy):
        self(MOVE_REL_Y)
        self(encode14(dy))

    def cut_abs_xy(self, x, y):
        self(CUT_ABS_XY)
        self(encode32(x))
        self(encode32(y))

    def cut_rel_xy(self, dx, dy):
        self(CUT_REL_XY)
        self(encode14(dx))
        self(encode14(dy))

    def cut_rel_x(self, dx):
        self(CUT_REL_X)
        self(encode14(dx))

    def cut_rel_y(self, dy):
        self(CUT_REL_Y)
        self(encode14(dy))

    def imd_power_1(self, power):
        self(IMD_POWER_1)
        self(encode14(power))

    def imd_power_2(self, power):
        self(IMD_POWER_2)
        self(encode14(power))

    def imd_power_3(self, power):
        self(IMD_POWER_3)
        self(encode14(power))

    def imd_power_4(self, power):
        self(IMD_POWER_4)
        self(encode14(power))

    def end_power_1(self, power):
        self(END_POWER_1)
        self(encode14(power))

    def end_power_2(self, power):
        self(END_POWER_2)
        self(encode14(power))

    def end_power_3(self, power):
        self(END_POWER_3)
        self(encode14(power))

    def end_power_4(self, power):
        self(END_POWER_4)
        self(encode14(power))

    def min_power_1(self, power):
        self(MIN_POWER_1)
        self(encode14(power))

    def max_power_1(self, power):
        self(MAX_POWER_1)
        self(encode14(power))

    def min_power_2(self, power):
        self(MIN_POWER_2)
        self(encode14(power))

    def max_power_2(self, power):
        self(MAX_POWER_2)
        self(encode14(power))

    def min_power_3(self, power):
        self(MIN_POWER_3)
        self(encode14(power))

    def max_power_3(self, power):
        self(MAX_POWER_3)
        self(encode14(power))

    def min_power_4(self, power):
        self(MIN_POWER_4)
        self(encode14(power))

    def max_power_4(self, power):
        self(MAX_POWER_4)
        self(encode14(power))

    def laser_interval(self, time):
        self(LASER_INTERVAL)
        self(encode32(time))

    def add_delay(self, time):
        self(ADD_DELAY)
        self(encode32(time))

    def laser_on_delay(self, time):
        self(LASER_ON_DELAY)
        self(encode32(time))

    def laser_off_delay(self, time):
        self(LASER_OFF_DELAY)
        self(encode32(time))

    def laser_on_delay_2(self, time):
        self(LASER_ON_DELAY2)
        self(encode32(time))

    def laser_off_delay_2(self, time):
        self(LASER_OFF_DELAY2)
        self(encode32(time))

    def min_power_1_part(self, part, power):
        self(MIN_POWER_1_PART)
        self(encode_part(part))
        self(encode14(power))

    def max_power_1_part(self, part, power):
        self(MAX_POWER_1_PART)
        self(encode_part(part))
        self(encode14(power))

    def min_power_2_part(self, part, power):
        self(MIN_POWER_2_PART)
        self(encode_part(part))
        self(encode14(power))

    def max_power_2_part(self, part, power):
        self(MAX_POWER_2_PART)
        self(encode_part(part))
        self(encode14(power))

    def min_power_3_part(self, part, power):
        self(MIN_POWER_3_PART)
        self(encode_part(part))
        self(encode14(power))

    def max_power_3_part(self, part, power):
        self(MAX_POWER_3_PART)
        self(encode_part(part))
        self(encode14(power))

    def min_power_4_part(self, part, power):
        self(MIN_POWER_4_PART)
        self(encode_part(part))
        self(encode14(power))

    def max_power_4_part(self, part, power):
        self(MAX_POWER_4_PART)
        self(encode_part(part))
        self(encode14(power))

    def through_power_1(self, power):
        self(THROUGH_POWER_1)
        self(encode14(power))

    def through_power_2(self, power):
        self(THROUGH_POWER_2)
        self(encode14(power))

    def through_power_3(self, power):
        self(THROUGH_POWER_3)
        self(encode14(power))

    def through_power_4(self, power):
        self(THROUGH_POWER_4)
        self(encode14(power))

    def frequency_part(self, laser, part, frequency):
        self(FREQUENCY_PART)
        self(encode_index(laser))
        self(encode_part(part))
        self(encode32(frequency))

    def speed_laser_1(self, speed):
        self(SPEED_LASER_1)
        self(encode32(speed))

    def speed_axis(self, speed):
        self(SPEED_AXIS)
        self(encode32(speed))

    def speed_laser_1_part(self, part, speed):
        self(SPEED_LASER_1_PART)
        self(encode_part(part))
        self(encode32(speed))

    def force_eng_speed(self, speed):
        self(FORCE_ENG_SPEED)
        self(encode32(speed))

    def speed_axis_move(self, speed):
        self(SPEED_AXIS_MOVE)
        self(encode32(speed))

    def layer_end(self):
        self(LAYER_END)

    def work_mode_1(self):
        self(WORK_MODE_1)

    def work_mode_2(self):
        self(WORK_MODE_2)

    def work_mode_3(self):
        self(WORK_MODE_3)

    def work_mode_4(self):
        self(WORK_MODE_4)

    def work_mode_5(self):
        self(WORK_MODE_5)

    def work_mode_6(self):
        self(WORK_MODE_6)

    def laser_device_0(self):
        self(LASER_DEVICE_0)

    def laser_device_1(self):
        self(LASER_DEVICE_1)

    def air_assist_off(self):
        self(AIR_ASSIST_OFF)

    def air_assist_on(self):
        self(AIR_ASSIST_ON)

    def db_head(self):
        self(DB_HEAD)

    def en_laser_2_offset_0(self):
        self(EN_LASER_2_OFFSET_0)

    def en_laser_2_offset_1(self):
        self(EN_LASER_2_OFFSET_1)

    def layer_number_part(self, part):
        self(LAYER_NUMBER_PART)
        self(encode_part(part))

    def en_laser_tube_start(self, part):
        self(EN_LASER_TUBE_START)
        self(encode_part(part))

    def x_sign_map(self, value):
        self(X_SIGN_MAP)
        self(encode_index(value))

    def layer_color(self, color):
        self(LAYER_COLOR)
        self(encode_color(color))

    def layer_color_part(self, part, color):
        self(LAYER_COLOR)
        self(encode_part(part))
        self(encode_color(color))

    def en_ex_io(self, value):
        """
        Enable External IO.

        @param value:
        @return:
        """
        self(EN_EX_IO)
        self(encode_index(value))

    def max_layer_part(self, part):
        self(MAX_LAYER_PART)
        self(encode_part(part))

    def u_file_id(self, file_number):
        self(MAX_LAYER_PART)
        self(encode_file_number(file_number))

    def zu_map(self, value):
        self(ZU_MAP)
        self(encode_index(value))

    def work_mode_part(self, part, mode):
        self(WORK_MODE_PART)
        self(encode_part(part))
        self(encode_index(mode))

    def ack(self):
        self(ACK)

    def err(self):
        self(ERR)

    def keep_alive(self):
        self(KEEP_ALIVE)

    def end_of_file(self):
        self(END_OF_FILE)

    def start_process(self):
        self(START_PROCESS)

    def stop_process(self):
        self(STOP_PROCESS)

    def pause_process(self):
        self(PAUSE_PROCESS)

    def restore_process(self):
        self(RESTORE_PROCESS)

    def ref_point_2(self):
        """
        Machine zero. Absolute position.
        @return:
        """
        self(REF_POINT_2)

    def ref_point_1(self):
        """
        Anchor Point, Origin.
        @return:
        """
        self(REF_POINT_1)

    def ref_point_0(self):
        """
        Current position.

        @return:
        """
        self(REF_POINT_0)

    def home_z(self):
        self(HOME_Z)

    def home_u(self):
        self(HOME_U)

    def home_xy(self):
        self(HOME_XY)

    def focus_z(self):
        self(FOCUS_Z)

    def _rapid_options(self, light=False, origin=False):
        if light and origin:
            return RAPID_OPTION_LIGHTORIGIN
        if light and not origin:
            return RAPID_OPTION_LIGHT
        if origin:
            return RAPID_OPTION_ORIGIN
        return RAPID_OPTION_NONE

    def rapid_move_x(self, x, light=False, origin=False):
        self(RAPID_MOVE_X)
        self(self._rapid_options(light=light, origin=origin))
        self(encode_coord(x))

    def rapid_move_y(self, y, light=False, origin=False):
        self(RAPID_MOVE_Y)
        self(self._rapid_options(light=light, origin=origin))
        self(encode_coord(y))

    def rapid_move_z(self, z, light=False, origin=False):
        self(RAPID_MOVE_Z)
        self(self._rapid_options(light=light, origin=origin))
        self(encode_coord(z))

    def rapid_move_u(self, u, light=False, origin=False):
        self(RAPID_MOVE_U)
        self(self._rapid_options(light=light, origin=origin))
        self(encode_coord(u))

    def rapid_move_xy(self, x, y, light=False, origin=False):
        self(RAPID_MOVE_XY)
        self(self._rapid_options(light=light, origin=origin))
        self(encode_coord(x))
        self(encode_coord(y))

    def rapid_move_xyu(self, x, y, u, light=False, origin=False):
        self(RAPID_MOVE_XYU)
        self(self._rapid_options(light=light, origin=origin))
        self(encode_coord(x))
        self(encode_coord(y))
        self(encode_coord(u))

    def rapid_feed_axis(self, light=False, origin=False):
        self(RAPID_FEED_AXIS_MOVE)
        self(self._rapid_options(light=light, origin=origin))

    def get_setting(self, mem):
        self(GET_SETTING)
        self(encode_mem(mem))

    def set_setting(self, mem, value):
        self(SET_SETTING)
        self(encode_mem(mem))
        self(encode_value(value))
        self(encode_value(value))

    def document_file_upload(self, file_number, value, value1):
        self(DOCUMENT_FILE_UPLOAD)
        self(encode_value(value))
        self(encode_value(value1))

    def document_file_end(self):
        self(DOCUMENT_FILE_END)

    def set_absolute(self):
        self(SET_ABSOLUTE)

    def block_end(self):
        self(BLOCK_END)

    def set_filename(self, filename):
        self(SET_FILENAME)
        self(bytes(filename[:9]), encoding="utf-8")
        self(b"\x00")

    def process_top_left(self, top, left):
        self(PROCESS_TOP_LEFT)
        self(encode_coord(top))
        self(encode_coord(left))

    def process_repeat(self, v0, v1, v2, v3, v4, v5, v6):
        self(PROCESS_REPEAT)
        self(encode14(v0))
        self(encode14(v1))
        self(encode14(v2))
        self(encode14(v3))
        self(encode14(v4))
        self(encode14(v5))
        self(encode14(v6))

    def array_direction(self, direction):
        self(ARRAY_DIRECTION)
        self(encode_index(direction))

    def feed_repeat(self, value, value1):
        self(FEED_REPEAT)
        self(encode32(value))
        self(encode32(value1))

    def process_bottom_right(self, bottom, right):
        self(PROCESS_TOP_LEFT)
        self(encode_coord(bottom))
        self(encode_coord(right))

    def array_repeat(self, v0, v1, v2, v3, v4, v5, v6):
        self(ARRAY_REPEAT)
        self(encode14(v0))
        self(encode14(v1))
        self(encode14(v2))
        self(encode14(v3))
        self(encode14(v4))
        self(encode14(v5))
        self(encode14(v6))

    def feed_length(self, length):
        self(FEED_LENGTH)
        self(encode32(length))

    def array_min_point(self, min_x, min_y):
        self(ARRAY_MIN_POINT)
        self(encode_coord(min_x))
        self(encode_coord(min_y))

    def array_max_point(self, max_x, max_y):
        self(ARRAY_MAX_POINT)
        self(encode_coord(max_x))
        self(encode_coord(max_y))

    def array_add(self, x, y):
        self(ARRAY_ADD)
        self(encode_coord(x))
        self(encode_coord(y))

    def array_mirror(self, mirror):
        self(ARRAY_MIRROR)
        self(encode_index(mirror))

    def block_x_size(self, x0, x1):
        self(BLOCK_X_SIZE)
        self(encode_coord(x0))
        self(encode_coord(x1))

    def by_test(self):
        self(BY_TEST)
        self(encode32(0x11227766))

    def document_min_point(self, min_x, min_y):
        self(DOCUMENT_MIN_POINT)
        self(encode_coord(min_x))
        self(encode_coord(min_y))

    def document_max_point(self, max_x, max_y):
        self(DOCUMENT_MAX_POINT)
        self(encode_coord(max_x))
        self(encode_coord(max_y))

    def part_min_point(self, part, min_x, min_y):
        self(PART_MIN_POINT)
        self(encode_part(part))
        self(encode_coord(min_x))
        self(encode_coord(min_y))

    def part_max_point(self, part, max_x, max_y):
        self(PART_MAX_POINT)
        self(encode_part(part))
        self(encode_coord(max_x))
        self(encode_coord(max_y))

    def pen_offset(self, axis, coord):
        self(PEN_OFFSET)
        self(encode_index(axis))
        self(encode_coord(coord))

    def layer_offset(self, axis, coord):
        self(LAYER_OFFSET)
        self(encode_index(axis))
        self(encode_coord(coord))

    def set_current_element_index(self, index):
        self(SET_CURRENT_ELEMENT_INDEX)
        self(encode_index(index))

    def part_min_point_ex(self, part, min_x, min_y):
        self(PART_MIN_POINT_EX)
        self(encode_part(part))
        self(encode_coord(min_x))
        self(encode_coord(min_y))

    def part_max_point_ex(self, part, max_x, max_y):
        self(PART_MAX_POINT_EX)
        self(encode_part(part))
        self(encode_coord(max_x))
        self(encode_coord(max_y))

    def array_start(self, index):
        self(ARRAY_START)
        self(encode_index(index))

    def array_end(self):
        self(ARRAY_END)

    def ref_point_set(self):
        self(REF_POINT_SET)

    def element_max_index(self, index):
        self(ELEMENT_MAX_INDEX)
        self(encode_index(index))

    def element_name_max_index(self, index):
        self(ELEMENT_NAME_MAX_INDEX)
        self(encode_index(index))

    def enable_block_cutting(self, enable):
        self(ENABLE_BLOCK_CUTTING)
        self(encode_index(enable))

    def display_offset(self, dx, dy):
        self(DISPLAY_OFFSET)
        self(encode_coord(dx))
        self(encode_coord(dy))

    def feed_auto_calc(self, enable):
        self(FEED_AUTO_CALC)
        self(encode_index(enable))

    def element_index(self, index):
        self(ELEMENT_INDEX)
        self(encode_index(index))

    def element_name(self, name):
        self(ELEMENT_NAME)
        self(bytes(name[:9]), encoding="utf-8")
        self(b"\x00")

    def element_array_min_point(self, x, y):
        self(ELEMENT_ARRAY_MIN_POINT)
        self(encode_coord(x))
        self(encode_coord(y))

    def element_array_max_point(self, x, y):
        self(ELEMENT_ARRAY_MAX_POINT)
        self(encode_coord(x))
        self(encode_coord(y))

    def element_array(self, v0, v1, v2, v3, v4, v5, v6):
        self(ELEMENT_ARRAY)
        self(encode14(v0))
        self(encode14(v1))
        self(encode14(v2))
        self(encode14(v3))
        self(encode14(v4))
        self(encode14(v5))
        self(encode14(v6))

    def element_array_add(self, x, y):
        self(ELEMENT_ARRAY_ADD)
        self(encode_coord(x))
        self(encode_coord(y))

    def element_array_mirror(self, mirror):
        self(ELEMENT_ARRAY_MIRROR)
        self(encode_index(mirror))
