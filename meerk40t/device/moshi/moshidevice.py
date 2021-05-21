import threading
import time

from ...core.drivers import Driver
from ...core.plotplanner import PlotPlanner
from ...kernel import (
    STATE_ACTIVE,
    STATE_BUSY,
    STATE_END,
    STATE_IDLE,
    STATE_INITIALIZE,
    STATE_PAUSE,
    STATE_TERMINATE,
    STATE_UNKNOWN,
    STATE_WAIT,
    Modifier,
    Module,
)
from ..basedevice import (
    DRIVER_STATE_FINISH,
    DRIVER_STATE_MODECHANGE,
    DRIVER_STATE_PROGRAM,
    DRIVER_STATE_RAPID,
    DRIVER_STATE_RASTER,
    PLOT_AXIS,
    PLOT_DIRECTION,
    PLOT_FINISH,
    PLOT_JOG,
    PLOT_RAPID,
    PLOT_SETTING,
)

STATUS_OK = 205  # Seen before file send. And after file send.
STATUS_PROCESSING = 207  # PROCESSING

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


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("driver/moshi", MoshiDriver)
        kernel.register("output/moshi", MoshiController)
        context = kernel.root

        @context.console_command("usb_connect", input_type="moshi", help="Connect USB")
        def usb_connect(command, channel, _, data=None, **kwargs):
            spooler, driver, output = data
            try:
                output.open()
            except ConnectionRefusedError:
                channel("Connection Refused.")

        @context.console_command(
            "usb_disconnect", input_type="moshi", help="Disconnect USB"
        )
        def usb_disconnect(command, channel, _, data=None, args=tuple(), **kwargs):
            spooler, driver, output = data
            if output.connection is not None:
                output.close()
            else:
                channel("Usb is not connected.")

        @context.console_command(
            "start", input_type="moshi", help="Start Pipe to Controller"
        )
        def pipe_start(command, channel, _, data=None, args=tuple(), **kwargs):
            spooler, driver, output = data
            output.update_state(STATE_ACTIVE)
            output.start()
            channel("Moshi Channel Started.")

        @context.console_command("hold", input_type="moshi", help="Hold Controller")
        def pipe_pause(command, channel, _, data=None, args=tuple(), **kwargs):
            spooler, driver, output = data
            output.update_state(STATE_PAUSE)
            output.pause()
            channel("Moshi Channel Paused.")

        @context.console_command("resume", input_type="moshi", help="Resume Controller")
        def pipe_resume(command, channel, _, data=None, args=tuple(), **kwargs):
            spooler, driver, output = data
            output.update_state(STATE_ACTIVE)
            output.start()
            channel("Moshi Channel Resumed.")

        @context.console_command("abort", input_type="moshi", help="Abort Job")
        def pipe_abort(command, channel, _, data=None, args=tuple(), **kwargs):
            spooler, driver, output = data
            output.reset()
            channel("Moshi Channel Aborted.")

        @context.console_command(
            "status",
            input_type="moshi",
            help="abort waiting process on the controller.",
        )
        def realtime_status(channel, _, data=None, **kwargs):
            spooler, driver, output = data
            try:
                output.update_status()
            except ConnectionError:
                channel(_("Could not check status, usb not connected."))

        @context.console_command(
            "continue",
            input_type="moshi",
            help="abort waiting process on the controller.",
        )
        def realtime_pause(data=None, **kwargs):
            spooler, driver, output = data
            output.abort_waiting = True


def get_code_string_from_moshicode(code):
    if code == STATUS_OK:
        return "OK"
    elif code == STATUS_PROCESSING:
        return "Processing"
    elif code == 0:
        return "USB Failed"
    else:
        return "UNK %02x" % code


class MoshiDriver(Driver, Modifier):
    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        context = context.get_context("moshi/driver/%s" % name)
        Modifier.__init__(self, context, name, channel)
        Driver.__init__(self, context=context)

        self.next = None
        self.prev = None

        self.plot_planner = PlotPlanner(self.settings)
        self.plot = None

        self.offset_x = 0
        self.offset_y = 0
        self.next_x = None
        self.next_y = None
        self.max_x = None
        self.max_y = None
        self.min_x = None
        self.min_y = None
        self.start_x = None
        self.start_y = None
        self.is_paused = False
        self.context._buffer_size = 0
        self.pipe = self.context.channel("pipe/send")
        self.control = self.context.channel("pipe/control")
        self.thread = None

    def attach(self, *a, **kwargs):
        context = self.context
        root_context = context.root
        kernel = context._kernel
        _ = kernel.translation

        context.driver = self

        context.setting(int, "home_adjust_x", 0)
        context.setting(int, "home_adjust_y", 0)
        context.setting(bool, "home_right", False)
        context.setting(bool, "home_bottom", False)
        root_context.setting(bool, "opt_rapid_between", True)
        root_context.setting(int, "opt_jog_mode", 0)
        root_context.setting(int, "opt_jog_minimum", 127)

    def __repr__(self):
        return "MoshiDriver(%s)" % self.name

    def swizzle(self, b, p7, p6, p5, p4, p3, p2, p1, p0):
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

    def convert(self, q):
        if q & 1:
            return self.swizzle(q, 7, 6, 2, 4, 3, 5, 1, 0)
        else:
            return self.swizzle(q, 5, 1, 7, 2, 4, 3, 6, 0)

    def reconvert(self, q):
        for m in range(5):
            q = self.convert(q)
        return q

    def pipe_int8(self, value):
        v = bytes(
            bytearray(
                [
                    value & 0xFF,
                ]
            )
        )
        self.pipe(v)

    def pipe_int16le(self, value):
        v = bytes(
            bytearray(
                [
                    (value >> 0) & 0xFF,
                    (value >> 8) & 0xFF,
                ]
            )
        )
        self.pipe(v)

    def write_vector_speed(self, speed_mms, normal_speed_mms):
        """
        Vector Speed Byte. (0x00 position), followed by 2 int8 values.
        Speed and Normal Speed.
        :return:
        """
        self.pipe(swizzle_table[5][0])
        if speed_mms > 256:
            speed_mms = 256
        if speed_mms < 1:
            speed_mms = 1
        self.pipe_int8(speed_mms - 1)
        self.pipe_int8(normal_speed_mms - 1)  # Unknown

    def write_raster_speed(self, speed_mms):
        self.pipe(swizzle_table[4][0])
        speed_cms = int(round(speed_mms / 10))
        if speed_cms == 0:
            speed_cms = 1
        self.pipe_int8(speed_cms - 1)

    def write_set_offset(self, z, x, y):
        """
        2nd Command For Jump. (0x03 position), followed by 3 int16le (2)
        :return:
        """
        self.pipe(swizzle_table[0][0])
        self.pipe_int16le(z)  # Unknown, always zero.
        self.pipe_int16le(x)  # x
        self.pipe_int16le(y)  # y

    def write_termination(self):
        """
        Terminal Commands for Jump/Program. (last 7 bytes). (4)
        :return:
        """
        for i in range(7):
            self.pipe(swizzle_table[2][0])

    def write_cut_abs(self, x, y):
        self.pipe(swizzle_table[15][1])
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        self.current_x = x
        self.current_y = y
        x -= self.offset_x
        y -= self.offset_y
        self.pipe_int16le(int(x))
        self.pipe_int16le(int(y))

    def write_move_abs(self, x, y):
        self.pipe(swizzle_table[7][0])
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        self.current_x = x
        self.current_y = y
        x -= self.offset_x
        y -= self.offset_y
        self.pipe_int16le(int(x))
        self.pipe_int16le(int(y))

    def write_move_vertical_abs(self, y):
        self.current_y = y
        y -= self.offset_y
        self.pipe(swizzle_table[3][0])
        self.pipe_int16le(int(y))

    def write_move_horizontal_abs(self, x):
        self.current_x = x
        x -= self.offset_x
        self.pipe(swizzle_table[6][0])
        self.pipe_int16le(int(x))

    def write_cut_horizontal_abs(self, x):
        self.current_x = x
        x -= self.offset_x
        self.pipe(swizzle_table[14][0])
        self.pipe_int16le(int(x))

    def write_cut_vertical_abs(self, y):
        self.current_y = y
        y -= self.offset_y
        self.pipe(swizzle_table[11][0])
        self.pipe_int16le(int(y))

    def ensure_program_mode(self):
        if self.state == DRIVER_STATE_PROGRAM:
            return
        if self.state == DRIVER_STATE_RASTER:
            self.ensure_rapid_mode()
        speed = int(self.settings.speed)
        # Normal speed is rapid. Passing same speed so PPI isn't crazy.
        self.write_vector_speed(speed, speed)
        x, y = self.calc_home_position()
        self.offset_x = x
        self.offset_y = y
        self.write_set_offset(0, x, y)
        self.state = DRIVER_STATE_PROGRAM
        self.context.signal("driver;mode", self.state)

    def ensure_raster_mode(self):
        if self.state == DRIVER_STATE_RASTER:
            return
        if self.state == DRIVER_STATE_PROGRAM:
            self.ensure_rapid_mode()
        speed = int(self.settings.speed)
        self.write_raster_speed(speed)
        x, y = self.calc_home_position()
        self.offset_x = x
        self.offset_y = y
        self.write_set_offset(0, x, y)
        self.state = DRIVER_STATE_RASTER
        self.context.signal("driver;mode", self.state)
        self.write_move_abs(0, 0)

    def ensure_rapid_mode(self):
        if self.state == DRIVER_STATE_RAPID:
            return
        if self.state == DRIVER_STATE_FINISH:
            self.state = DRIVER_STATE_RAPID
        elif (
            self.state == DRIVER_STATE_PROGRAM
            or self.state == DRIVER_STATE_MODECHANGE
            or self.state == DRIVER_STATE_RASTER
        ):
            self.write_termination()
            self.control("execute\n")
        self.state = DRIVER_STATE_RAPID
        self.context.signal("driver;mode", self.state)

    def ensure_finished_mode(self):
        if self.state == DRIVER_STATE_FINISH:
            return
        if (
            self.state == DRIVER_STATE_PROGRAM
            or self.state == DRIVER_STATE_MODECHANGE
            or self.state == DRIVER_STATE_RASTER
        ):
            self.ensure_rapid_mode()
            self.state = DRIVER_STATE_FINISH

    def plotplanner_process(self):
        """
        Processes any data in the plot planner. Getting all relevant (x,y,on) plot values and performing the cardinal
        movements. Or updating the laser state based on the settings of the cutcode.

        :return:
        """
        if self.plot is not None:
            while True:
                try:
                    if self.hold():
                        return True
                    x, y, on = next(self.plot)
                except StopIteration:
                    break
                except TypeError:
                    break
                on = int(on)
                if on & PLOT_FINISH:  # Plot planner is ending.
                    self.ensure_rapid_mode()
                    continue
                if on & PLOT_SETTING:  # Plot planner settings have changed.
                    p_set = self.plot_planner.settings
                    s_set = self.settings
                    if p_set.power != s_set.power:
                        self.set_power(p_set.power)
                    if (
                        p_set.speed != s_set.speed
                        or p_set.raster_step != s_set.raster_step
                    ):
                        self.set_speed(p_set.speed)
                        self.set_step(p_set.raster_step)
                        self.ensure_rapid_mode()
                    self.settings.set_values(p_set)
                    continue
                if on & PLOT_AXIS:  # Major Axis.
                    continue
                if on & PLOT_DIRECTION:
                    continue
                if on & (
                    PLOT_RAPID | PLOT_JOG
                ):  # Plot planner requests position change.
                    self.ensure_rapid_mode()
                    self.move_absolute(x, y)
                    continue
                self.goto_absolute(x, y, on & 1)
            self.plot = None
        return False

    def goto_absolute(self, x, y, cut):
        if self.settings.raster_step == 0:
            self.ensure_program_mode()
        else:
            self.ensure_program_mode()
            # self.ensure_raster_mode() # Rastermode is not functional.
        if self.state == DRIVER_STATE_PROGRAM:
            if cut:
                self.write_cut_abs(x, y)
            else:
                self.write_move_abs(x, y)
        else:
            if x == self.current_x and y == self.current_y:
                return
            if cut:
                if x == self.current_x:
                    self.write_cut_vertical_abs(y=y)
                if y == self.current_y:
                    self.write_cut_horizontal_abs(x=x)
            else:
                if x == self.current_x:
                    self.write_move_vertical_abs(y=y)
                if y == self.current_y:
                    self.write_move_horizontal_abs(x=x)
        oldx = self.current_x
        oldy = self.current_y
        self.current_x = x
        self.current_y = y
        self.context.signal("driver;position", (x, y, oldx, oldy))

    def cut(self, x, y):
        if self.is_relative:
            self.cut_relative(x, y)
        else:
            self.cut_absolute(x, y)
        self.ensure_rapid_mode()
        self.control("execute\n")

    def cut_absolute(self, x, y):
        self.ensure_program_mode()
        self.write_cut_abs(x, y)

        oldx = self.current_x
        oldy = self.current_y
        self.current_x = x
        self.current_y = y
        self.context.signal("driver;position", (x, y, oldx, oldy))

    def cut_relative(self, dx, dy):
        x = dx + self.current_x
        y = dy + self.current_y
        self.cut_absolute(x, y)

    def jog(self, x, y, **kwargs):
        self.move(x, y)

    def move(self, x, y):
        if self.is_relative:
            self.move_relative(x, y)
        else:
            self.move_absolute(x, y)
        self.ensure_rapid_mode()
        self.control("execute\n")

    def move_absolute(self, x, y):
        self.ensure_program_mode()
        oldx = self.current_x
        oldy = self.current_y
        self.write_move_abs(x, y)
        x = self.current_x
        y = self.current_y
        self.context.signal("driver;position", (x, y, oldx, oldy))

    def move_relative(self, dx, dy):
        x = dx + self.current_x
        y = dy + self.current_y
        self.move_absolute(x, y)

    def set_speed(self, speed=None):
        if self.settings.speed != speed:
            self.settings.speed = speed
            if self.state == DRIVER_STATE_PROGRAM or self.state == DRIVER_STATE_RASTER:
                self.state = DRIVER_STATE_MODECHANGE

    def set_step(self, step=None):
        if self.settings.raster_step != step:
            self.settings.raster_step = step
            if self.state == DRIVER_STATE_PROGRAM or self.state == DRIVER_STATE_RASTER:
                self.state = DRIVER_STATE_MODECHANGE

    def calc_home_position(self):
        x = self.context.home_adjust_x
        y = self.context.home_adjust_y
        bed_dim = self.context.root
        bed_dim.setting(int, "bed_width", 310)
        bed_dim.setting(int, "bed_height", 210)
        if self.context.home_right:
            x += int(bed_dim.bed_width * 39.3701)
        if self.context.home_bottom:
            y += int(bed_dim.bed_height * 39.3701)
        return x, y

    def home(self, *values):
        self.offset_x = 0
        self.offset_y = 0

        x, y = self.calc_home_position()
        try:
            x = int(values[0])
        except (ValueError, IndexError):
            pass
        try:
            y = int(values[1])
        except (ValueError, IndexError):
            pass
        self.ensure_rapid_mode()
        self.is_relative = False
        self.move(x, y)

    def lock_rail(self):
        pass

    def unlock_rail(self, abort=False):
        self.ensure_rapid_mode()
        self.control("unlock\n")

    def abort(self):
        self.control("stop\n")

    @property
    def type(self):
        return "moshi"


class MoshiController(Module):
    def __init__(self, context, name, channel=None, *args, **kwargs):
        context = context.get_context("moshi/output/%s" % name)
        Module.__init__(self, context, name, channel)
        self.state = STATE_UNKNOWN

        self.next = None
        self.prev = None

        self.is_shutdown = False

        self._thread = None
        self._buffer = b""  # Threadsafe buffered commands to be sent to controller.
        self._queue = bytearray()  # Queued additional commands programs.
        self._programs = []  # Programs to execute.

        self.context._buffer_size = 0
        self._queue_lock = threading.Lock()
        self._main_lock = threading.Lock()

        self._status = [0] * 6
        self._usb_state = -1

        self.ch341 = self.context.open("module/ch341")
        self.connection = None

        self.max_attempts = 5
        self.refuse_counts = 0
        self.connection_errors = 0
        self.count = 0
        self.abort_waiting = False

        self.pipe_channel = context.channel("%s/events" % name)
        self.usb_log = context.channel("%s/usb" % name, buffer_size=20)
        self.usb_send_channel = context.channel("%s/usb_send" % name)
        self.recv_channel = context.channel("%s/recv" % name)
        self.usb_log.watch(lambda e: context.signal("pipe;usb_status", e))

        control = context.channel("%s/control" % name)
        control.watch(self.control)

    def initialize(self, *args, **kwargs):
        context = self.context

        context.setting(int, "packet_count", 0)
        context.setting(int, "rejected_count", 0)

        self.reset()

    def finalize(self, *args, **kwargs):
        if self._thread is not None:
            self.is_shutdown = True

    def viewbuffer(self):
        buffer = "Current Working Buffer: %s\n" % str(self._buffer)
        for p in self._programs:
            buffer += "%s\n" % str(p)
        buffer += "Building Buffer: %s\n" % str(self._queue)
        return buffer

    def __repr__(self):
        return "MoshiController()"

    def __len__(self):
        """Provides the length of the buffer of this device."""
        return len(self._buffer) + sum(map(len, self._programs)) + len(self._queue)

    def realtime_read(self):
        """
        The a7xx values used before the AC01 commands. Read preamble.
        :return:
        """
        self.realtime_pipe(swizzle_table[14][0])

    def realtime_prologue(self):
        """
        Before a jump / program / turned on:
        :return:
        """
        self.realtime_pipe(swizzle_table[6][0])

    def realtime_epilogue(self):
        """
        Status 205
        After a jump / program
        Status 207
        Status 205 Done.
        :return:
        """
        self.realtime_pipe(swizzle_table[2][0])

    def realtime_freemotor(self):
        """
        Freemotor command
        :return:
        """
        self.realtime_pipe(swizzle_table[1][0])

    def realtime_laser(self):
        """
        Laser Command Toggle.
        :return:
        """
        self.realtime_pipe(swizzle_table[7][0])

    def realtime_stop(self):
        """
        Stop command (likely same as freemotor):
        :return:
        """
        self.realtime_pipe(swizzle_table[1][0])

    def realtime_pipe(self, data):
        self.connection.write_addr(data)

    realtime_write = realtime_pipe

    def open(self):
        self.pipe_channel("open()")
        if self.connection is None:
            self.connection = self.ch341.connect(
                driver_index=self.context.usb_index,
                chipv=self.context.usb_version,
                bus=self.context.usb_bus,
                address=self.context.usb_address,
                mock=self.context.mock,
            )
            if self.context.mock:
                self.connection.mock_status = 205
                self.connection.mock_finish = 207
        else:
            self.connection.open()
        if self.connection is None:
            raise ConnectionRefusedError

    def close(self):
        self.pipe_channel("close()")
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def control(self, command):
        if command == "execute\n":
            if len(self._queue) == 0:
                return
            self._queue_lock.acquire(True)
            program = self._queue
            self._queue = bytearray()
            self._queue_lock.release()
            self._programs.append(program)
            self.start()
        elif command == "stop\n":
            self.realtime_stop()
        elif command == "unlock\n":
            if self._main_lock.locked():
                return
            else:
                self.realtime_freemotor()

    def write(self, bytes_to_write):
        """
        Writes data to the queue, this will be moved into the buffer by the thread in a threadsafe manner.

        :param bytes_to_write: data to write to the queue.
        :return:
        """
        self.pipe_channel("write(%s)" % str(bytes_to_write))
        self._queue_lock.acquire(True)
        self._queue += bytes_to_write
        self._queue_lock.release()
        self.update_buffer()
        return self

    def start(self):
        """
        Controller state change to Started.
        :return:
        """
        if self._thread is None or not self._thread.is_alive():
            self._thread = self.context.threaded(
                self._thread_data_send,
                thread_name="MoshiPipe(%s)" % (self.context._path),
                result=self.stop
            )
            self.update_state(STATE_INITIALIZE)

    def pause(self):
        """
        Pause simply holds the controller from sending any additional packets.

        If this state change is done from INITIALIZE it will start the processing.
        Otherwise it must be done from ACTIVE or IDLE.
        """
        if self.state == STATE_INITIALIZE:
            self.start()
            self.update_state(STATE_PAUSE)
        if self.state == STATE_ACTIVE or self.state == STATE_IDLE:
            self.update_state(STATE_PAUSE)

    def resume(self):
        """
        Resume can only be called from PAUSE.
        """
        if self.state == STATE_PAUSE:
            self.update_state(STATE_ACTIVE)

    def abort(self):
        self._buffer = b""
        self._queue = bytearray()
        self.context.signal("pipe;buffer", 0)
        self.update_state(STATE_TERMINATE)

    def reset(self):
        self.update_state(STATE_INITIALIZE)

    def stop(self, *args):
        self.abort()
        if self._thread is not None:
            self._thread.join()  # Wait until stop completes before continuing.
        self._thread = None

    def update_state(self, state):
        if state == self.state:
            return
        self.state = state
        if self.context is not None:
            self.context.signal("pipe;thread", self.state)

    def update_buffer(self):
        if self.context is not None:
            self.context._buffer_size = len(self._buffer)
            self.context.signal("pipe;buffer", self.context._buffer_size)

    def update_packet(self, packet):
        if self.context is not None:
            self.context.signal("pipe;packet_text", packet)
            self.usb_send_channel(packet)

    def _new_program(self):
        if len(self._buffer) == 0:
            if len(self._programs) == 0:
                return  # There is nothing to run.
            self.wait_until_accepting_packets()
            self.realtime_prologue()
            self._buffer = self._programs.pop(0)

    def _send_buffer(self):
        while len(self._buffer) != 0:
            queue_processed = self.process_buffer()
            self.refuse_counts = 0

            if queue_processed:
                # Packet was sent.
                if self.state not in (
                    STATE_PAUSE,
                    STATE_BUSY,
                    STATE_ACTIVE,
                    STATE_TERMINATE,
                ):
                    self.update_state(STATE_ACTIVE)
                self.count = 0
            else:
                # No packet could be sent.
                if self.state not in (
                    STATE_PAUSE,
                    STATE_BUSY,
                    STATE_BUSY,
                    STATE_TERMINATE,
                ):
                    self.update_state(STATE_IDLE)
                if self.count > 50:
                    self.count = 50
                time.sleep(0.02 * self.count)
                # will tick up to 1 second waits if there's never a queue.
                self.count += 1

    def _wait_cycle(self):
        if len(self._buffer) == 0:
            self.realtime_epilogue()
            self.wait_finished()

    def _thread_data_send(self):
        """
        Main threaded function to send data. While the controller is working the thread
        will be doing work in this function.
        """

        with self._main_lock:
            self.count = 0
            self.is_shutdown = False
            stage = 0
            while self.state != STATE_END and self.state != STATE_TERMINATE:
                try:
                    self.open()
                    if self.state == STATE_INITIALIZE:
                        # If we are initialized. Change that to active since we're running.
                        self.update_state(STATE_ACTIVE)
                    if stage == 0:
                        self._new_program()
                        stage = 1
                    if len(self._buffer) == 0:
                        break
                    # We try to process the queue.
                    if stage == 1:
                        self._send_buffer()
                        stage = 2
                    if self.is_shutdown:
                        break
                    if stage == 2:
                        self._wait_cycle()
                        stage = 0
                except ConnectionRefusedError:
                    # The attempt refused the connection.
                    self.refuse_counts += 1
                    time.sleep(3)  # 3 second sleep on failed connection attempt.
                    if self.refuse_counts >= self.max_attempts:
                        # We were refused too many times, kill the thread.
                        self.update_state(STATE_TERMINATE)
                        self.context.signal("pipe;error", self.refuse_counts)
                        break
                    continue
                except ConnectionError:
                    # There was an error with the connection, close it and try again.
                    self.connection_errors += 1
                    time.sleep(0.5)
                    self.close()
                    continue
            self._thread = None
            self.is_shutdown = False
            self.update_state(STATE_END)

    def process_buffer(self):
        """
        :return: queue process success.
        """
        if len(self._buffer) > 0:
            buffer = self._buffer
        else:
            return False

        length = min(32, len(buffer))
        packet = bytes(buffer[:length])

        # Packet is prepared and ready to send. Open Channel.

        self.send_packet(packet)
        self.context.packet_count += 1

        # Packet was processed. Remove that data.
        self._buffer = self._buffer[length:]
        self.update_buffer()
        return True  # A packet was prepped and sent correctly.

    def send_packet(self, packet):
        self.connection.write(packet)
        self.update_packet(packet)

    def update_status(self):
        if self.connection is None:
            raise ConnectionError
        self._status = self.connection.get_status()
        if self.context is not None:
            self.context.signal(
                "pipe;status",
                self._status,
                get_code_string_from_moshicode(self._status[1]),
            )
            self.recv_channel(str(self._status))

    def wait_until_accepting_packets(self):
        i = 0
        while self.state != STATE_TERMINATE:
            self.update_status()
            status = self._status[1]
            if status == 0:
                raise ConnectionError
            if status == STATUS_OK:
                return
            time.sleep(0.05)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.

    def wait_finished(self):
        i = 0
        original_state = self.state
        if self.state != STATE_PAUSE:
            self.pause()

        while True:
            if self.state != STATE_WAIT:
                self.update_state(STATE_WAIT)
            self.update_status()
            status = self._status[1]
            if status == 0:
                self.close()
                self.open()
                continue
            if status == STATUS_OK:
                break
            if self.context is not None:
                self.context.signal("pipe;wait", status, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.
            if status == STATUS_PROCESSING:
                time.sleep(0.5)  # Half a second between requests.
        self.update_state(original_state)

    @property
    def type(self):
        return "moshi"
