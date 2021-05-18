import threading
import time

from meerk40t.tools.zinglplotter import ZinglPlotter

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
)
from ..basedevice import (
    DRIVER_STATE_FINISH,
    DRIVER_STATE_MODECHANGE,
    DRIVER_STATE_PROGRAM,
    DRIVER_STATE_RAPID,
    PLOT_AXIS,
    PLOT_DIRECTION,
    PLOT_FINISH,
    PLOT_JOG,
    PLOT_RAPID,
    PLOT_SETTING,
)
from ..lasercommandconstants import *
from .laserspeed import LaserSpeed
from .lhystudiosemulator import EgvLoader, LhystudiosEmulator


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("driver/lhystudios", LhystudiosDriver)
        kernel.register("output/lhystudios", LhystudiosController)
        kernel.register("emulator/lhystudios", LhystudiosEmulator)
        kernel.register("load/EgvLoader", EgvLoader)
        context = kernel.root

        @context.console_option(
            "idonotlovemyhouse",
            type=bool,
            action="store_true",
            help="override one second laser fire pulse duration",
        )
        @context.console_argument("time", type=float, help="laser fire pulse duration")
        @context.console_command(
            "pulse",
            input_type="lhystudios",
            help="pulse <time>: Pulse the laser in place.",
        )
        def pulse(
            command, channel, _, time=None, idonotlovemyhouse=False, data=None, **kwargs
        ):
            spooler, driver, output = data
            if time is None:
                channel(_("Must specify a pulse time in milliseconds."))
                return
            value = time / 1000.0
            if value > 1.0:
                channel(
                    _('"%s" exceeds 1 second limit to fire a standing laser.') % (value)
                )
                try:
                    if not idonotlovemyhouse:
                        return
                except IndexError:
                    return

            def timed_fire():
                yield COMMAND_WAIT_FINISH
                yield COMMAND_LASER_ON
                yield COMMAND_WAIT, value
                yield COMMAND_LASER_OFF

            if spooler.job_if_idle(timed_fire):
                channel(_("Pulse laser for %f milliseconds") % (value * 1000.0))
            else:
                channel(_("Pulse laser failed: Busy"))
            return

        @context.console_option(
            "difference",
            "d",
            type=bool,
            action="store_true",
            help="Change speed by this amount.",
        )
        @context.console_argument("speed", type=str, help="Set the driver speed.")
        @context.console_command(
            "speed", input_type="lhystudios", help="Set current speed of driver."
        )
        def speed(
            command,
            channel,
            _,
            data=None,
            speed=None,
            increment=False,
            decrement=False,
            **kwargs
        ):
            spooler, driver, output = data
            if speed is None or (increment and decrement):
                channel(_("Speed set at: %f mm/s") % driver.speed)
                return
            if speed.endswith("%"):
                speed = speed[:-1]
                percent = True
            else:
                percent = False
            try:
                s = float(speed)
            except ValueError:
                channel(_("Not a valid speed or percent."))
                return
            if percent and increment:
                s = driver.speed + driver.speed * (s / 100.0)
            elif increment:
                s += driver.speed
            elif percent:
                s = driver.speed * (s / 100.0)
            driver.set_speed(s)
            channel(_("Speed set at: %f mm/s") % driver.speed)

        @context.console_argument("ppi", type=int, help="pulses per inch [0-1000]")
        @context.console_command(
            "power", input_type="lhystudios", help="Set Driver Power"
        )
        def power(command, channel, _, data, ppi=None, args=tuple(), **kwargs):
            spooler, driver, output = data
            if ppi is None:
                channel(_("Power set at: %d pulses per inch") % driver.power)
            else:
                try:
                    driver.set_power(ppi)
                except ValueError:
                    pass

        @context.console_argument("accel", type=int, help="Acceleration amount [1-4]")
        @context.console_command(
            "acceleration",
            input_type="lhystudios",
            help="Set Driver Acceleration [1-4]",
        )
        def acceleration(channel, _, data=None, accel=None, **kwargs):
            """
            Lhymicro-gl speedcodes have a single character of either 1,2,3,4 which indicates
            the acceleration value of the laser. This is typically 1 below 25.4, 2 below 60,
            3 below 127, and 4 at any value greater than that. Manually setting this on the
            fly can be used to check the various properties of that mode.
            """
            spooler, driver, output = data
            if accel is None:
                if driver.acceleration is None:
                    channel(_("Acceleration is set to default."))
                else:
                    channel(_("Acceleration: %d") % driver.acceleration)

            else:
                try:
                    v = accel
                    if v not in (1, 2, 3, 4):
                        driver.set_acceleration(None)
                        channel(_("Acceleration is set to default."))
                        return
                    driver.set_acceleration(v)
                    channel(_("Acceleration: %d") % driver.acceleration)
                except ValueError:
                    channel(_("Invalid Acceleration [1-4]."))
                    return

        @context.console_command(
            "code_update",
            input_type="lhystudios",
            help="update movement codes for the drivers",
        )
        def realtime_pause(data=None, **kwargs):
            spooler, driver, output = data
            driver.update_codes()

        @context.console_command(
            "status",
            input_type="lhystudios",
            help="abort waiting process on the controller.",
        )
        def realtime_pause(channel, _, data=None, **kwargs):
            spooler, driver, output = data
            try:
                output.update_status()
            except ConnectionError:
                channel(_("Could not check status, usb not connected."))

        @context.console_command(
            "continue",
            input_type="lhystudios",
            help="abort waiting process on the controller.",
        )
        def realtime_pause(data=None, **kwargs):
            spooler, driver, output = data
            driver.abort_waiting = True

        @context.console_command(
            "pause",
            input_type="lhystudios",
            help="realtime pause/resume of the machine",
        )
        def realtime_pause(data=None, **kwargs):
            spooler, driver, output = data
            if driver.is_paused:
                driver.resume()
            else:
                driver.pause()

        @context.console_command(
            ("estop", "abort"), input_type="lhystudios", help="Abort Job"
        )
        def pipe_abort(channel, _, data=None, **kwargs):
            spooler, driver, output = data
            driver.reset()
            channel("Lhystudios Channel Aborted.")

        @context.console_argument(
            "rapid_x", type=float, help="limit x speed for rapid."
        )
        @context.console_argument(
            "rapid_y", type=float, help="limit y speed for rapid."
        )
        @context.console_command(
            "rapid_override",
            input_type="lhystudios",
            help="limit speed of typical rapid moves.",
        )
        def rapid_override(channel, _, data=None, rapid_x=None, rapid_y=None, **kwargs):
            spooler, driver, output = data
            if rapid_x is not None:
                if rapid_y is None:
                    rapid_y = rapid_x
                driver.rapid_override = True
                driver.rapid_override_speed_x = rapid_x
                driver.rapid_override_speed_y = rapid_y
                channel(
                    _("Rapid Limit: %f, %f")
                    % (driver.rapid_override_speed_x, driver.rapid_override_speed_y)
                )
            else:
                driver.rapid_override = False
                channel(_("Rapid Limit Off"))

        @context.console_argument("filename", type=str)
        @context.console_command(
            "egv_import", help="Lhystudios Engrave Buffer Import. egv_import <egv_file>"
        )
        def egv_import(filename, data=None, **kwargs):
            spooler, driver, output = data
            if filename is None:
                raise SyntaxError

            def skip(read, byte, count):
                """Skips forward in the file until we find <count> instances of <byte>"""
                pos = read.tell()
                while count > 0:
                    char = read.read(1)
                    if char == byte:
                        count -= 1
                    if char is None or len(char) == 0:
                        read.seek(pos, 0)
                        # If we didn't skip the right stuff, reset the position.
                        break

            def skip_header(file):
                skip(file, "\n", 3)
                skip(file, "%", 5)

            with open(filename, "r") as f:
                skip_header(f)
                while True:
                    data = f.read(1024)
                    if not data:
                        break
                    buffer = bytes(data, "utf8")
                    output.write(buffer)
                output.write(b"\n")

        @context.console_argument("filename", type=str)
        @context.console_command(
            "egv_export",
            input_type="lhystudios",
            help="Lhystudios Engrave Buffer Export. egv_export <egv_file>",
        )
        def egv_export(channel, _, filename, data=None, **kwargs):
            spooler, driver, output = data
            if filename is None:
                raise SyntaxError
            try:
                with open(filename, "w") as f:
                    f.write("Document type : LHYMICRO-GL file\n")
                    f.write("File version: 1.0.01\n")
                    f.write("Copyright: Unknown\n")
                    f.write(
                        "Creator-Software: %s v%s\n"
                        % (output.context._kernel.name, output.context._kernel.version)
                    )
                    f.write("\n")
                    f.write("%0%0%0%0%\n")
                    buffer = bytes(output._buffer)
                    buffer += bytes(output._queue)
                    f.write(buffer.decode("utf-8"))
            except (PermissionError, IOError):
                channel(_("Could not save: %s" % filename))

        @context.console_command(
            "egv",
            input_type="lhystudios",
            help="Lhystudios Engrave Code Sender. egv <lhymicro-gl>",
        )
        def egv(command, channel, _, data=None, args=tuple(), **kwargs):
            spooler, driver, output = data
            if len(args) == 0:
                channel("Lhystudios Engrave Code Sender. egv <lhymicro-gl>")
            else:
                output.write(bytes(args[0].replace("$", "\n"), "utf8"))

        @context.console_command(
            "start", input_type="lhystudios", help="Start Pipe to Controller"
        )
        def pipe_start(command, channel, _, data=None, **kwargs):
            spooler, driver, output = data
            output.update_state(STATE_ACTIVE)
            output.start()
            channel("Lhystudios Channel Started.")

        @context.console_command(
            "hold", input_type="lhystudios", help="Hold Controller"
        )
        def pipe_pause(command, channel, _, data=None, **kwargs):
            spooler, driver, output = data
            output.update_state(STATE_PAUSE)
            output.pause()
            channel("Lhystudios Channel Paused.")

        @context.console_command(
            "resume", input_type="lhystudios", help="Resume Controller"
        )
        def pipe_resume(command, channel, _, data=None, **kwargs):
            spooler, driver, output = data
            output.update_state(STATE_ACTIVE)
            output.start()
            channel("Lhystudios Channel Resumed.")

        @context.console_command(
            "usb_connect", input_type="lhystudios", help="Connects USB"
        )
        def usb_connect(command, channel, _, data=None, **kwargs):
            spooler, driver, output = data
            output.open()
            channel("CH341 Opened.")

        @context.console_command(
            "usb_disconnect", input_type="lhystudios", help="Disconnects USB"
        )
        def usb_disconnect(command, channel, _, data=None, **kwargs):
            spooler, driver, output = data
            output.close()
            channel("CH341 Closed.")

        @kernel.console_option("port", "p", type=int, default=23, help="port to listen on.")
        @kernel.console_command("lhyserver", help="activate the lhyserver.")
        def lhyserver(channel, _, port=23, **kwargs):
            root = kernel.root
            try:
                root.open_as("module/TCPServer", "lhyserver", port=port)
                channel(_("TCP Server for Lhystudios"))
                root.channel("server").watch(kernel.channel("console"))
                channel(_("Watching Channel: %s") % "server")
                spooler, input_driver, output = root.registered["device/%s" % root.active]
                root.channel("lhyserver/recv").watch(output.write)
            except OSError:
                channel(_("Server failed on port: %d") % port)
            return

distance_lookup = [
    b"",
    b"a",
    b"b",
    b"c",
    b"d",
    b"e",
    b"f",
    b"g",
    b"h",
    b"i",
    b"j",
    b"k",
    b"l",
    b"m",
    b"n",
    b"o",
    b"p",
    b"q",
    b"r",
    b"s",
    b"t",
    b"u",
    b"v",
    b"w",
    b"x",
    b"y",
    b"|a",
    b"|b",
    b"|c",
    b"|d",
    b"|e",
    b"|f",
    b"|g",
    b"|h",
    b"|i",
    b"|j",
    b"|k",
    b"|l",
    b"|m",
    b"|n",
    b"|o",
    b"|p",
    b"|q",
    b"|r",
    b"|s",
    b"|t",
    b"|u",
    b"|v",
    b"|w",
    b"|x",
    b"|y",
    b"|z",
]


def lhymicro_distance(v):
    dist = b""
    if v >= 255:
        zs = int(v / 255)
        v %= 255
        dist += b"z" * zs
    if v >= 52:
        return dist + b"%03d" % v
    return dist + distance_lookup[v]


def convert_to_list_bytes(data):
    if isinstance(data, str):  # python 2
        packet = [0] * 30
        for i in range(0, 30):
            packet[i] = ord(data[i])
        return packet
    else:
        packet = [0] * 30
        for i in range(0, 30):
            packet[i] = data[i]
        return packet


STATUS_BAD_STATE = 204
# 0xCC, 11001100
STATUS_OK = 206
# 0xCE, 11001110
STATUS_ERROR = 207
# 0xCF, 11001111
STATUS_FINISH = 236
# 0xEC, 11101100
STATUS_BUSY = 238
# 0xEE, 11101110
STATUS_POWER = 239


def get_code_string_from_code(code):
    if code == STATUS_OK:
        return "OK"
    elif code == STATUS_BUSY:
        return "Busy"
    elif code == STATUS_ERROR:
        return "Rejected"
    elif code == STATUS_FINISH:
        return "Finish"
    elif code == STATUS_POWER:
        return "Low Power"
    elif code == STATUS_BAD_STATE:
        return "Bad State"
    elif code == 0:
        return "USB Failed"
    else:
        return "UNK %02x" % code


crc_table = [
    0x00,
    0x5E,
    0xBC,
    0xE2,
    0x61,
    0x3F,
    0xDD,
    0x83,
    0xC2,
    0x9C,
    0x7E,
    0x20,
    0xA3,
    0xFD,
    0x1F,
    0x41,
    0x00,
    0x9D,
    0x23,
    0xBE,
    0x46,
    0xDB,
    0x65,
    0xF8,
    0x8C,
    0x11,
    0xAF,
    0x32,
    0xCA,
    0x57,
    0xE9,
    0x74,
]


def onewire_crc_lookup(line):
    """
    License: 2-clause "simplified" BSD license
    Copyright (C) 1992-2017 Arjen Lentz
    https://lentz.com.au/blog/calculating-crc-with-a-tiny-32-entry-lookup-table

    :param line: line to be CRC'd
    :return: 8 bit crc of line.
    """
    crc = 0
    for i in range(0, 30):
        crc = line[i] ^ crc
        crc = crc_table[crc & 0x0F] ^ crc_table[16 + ((crc >> 4) & 0x0F)]
    return crc


STATE_X_FORWARD_LEFT = (
    0b0000000000000001  # Direction is flagged left rather than right.
)
STATE_Y_FORWARD_TOP = 0b0000000000000010  # Direction is flagged top rather than bottom.
STATE_X_STEPPER_ENABLE = 0b0000000000000100  # X-stepper motor is engaged.
STATE_Y_STEPPER_ENABLE = 0b0000000000001000  # Y-stepper motor is engaged.
STATE_HORIZONTAL_MAJOR = 0b0000000000010000
REQUEST_X = 0b0000000000100000
REQUEST_X_FORWARD_LEFT = 0b0000000001000000  # Requested direction towards the left.
REQUEST_Y = 0b0000000010000000
REQUEST_Y_FORWARD_TOP = 0b0000000100000000  # Requested direction towards the top.
REQUEST_AXIS = 0b0000001000000000
REQUEST_HORIZONTAL_MAJOR = 0b0000010000000000  # Requested horizontal major axis.


class LhystudiosDriver(Driver):
    """
    LhystudiosDriver provides Lhystudios specific coding for elements and sends it to the backend
    to write to the usb.

    The interpret() ticks to process additional data.
    """

    def __init__(self, context, name, *args, **kwargs):
        context = context.get_context("lhystudios/driver/%s" % name)
        Driver.__init__(self, context=context, name=name)

        kernel = context._kernel
        _ = kernel.translation
        root_context = context.root
        root_context.setting(bool, "opt_rapid_between", True)
        root_context.setting(int, "opt_jog_mode", 0)
        root_context.setting(int, "opt_jog_minimum", 127)

        context.driver = self

        context.setting(bool, "strict", False)
        context.setting(bool, "swap_xy", False)
        context.setting(bool, "flip_x", False)
        context.setting(bool, "flip_y", False)
        context.setting(bool, "home_right", False)
        context.setting(bool, "home_bottom", False)
        context.setting(int, "home_adjust_x", 0)
        context.setting(int, "home_adjust_y", 0)
        context.setting(int, "buffer_max", 900)
        context.setting(bool, "buffer_limit", True)
        context.setting(int, "current_x", 0)
        context.setting(int, "current_y", 0)

        context.setting(bool, "autolock", True)

        context.setting(str, "board", "M2")
        context.setting(bool, "fix_speeds", False)

        self.CODE_RIGHT = b"B"
        self.CODE_LEFT = b"T"
        self.CODE_TOP = b"L"
        self.CODE_BOTTOM = b"R"
        self.CODE_ANGLE = b"M"
        self.CODE_LASER_ON = b"D"
        self.CODE_LASER_OFF = b"U"

        self.plot_planner = PlotPlanner(self.settings)

        self.plot = None
        self.plot_gen = None

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

        def primary_hold():
            if self.output is None:
                return True

            buffer = len(self.output)
            if buffer is None:
                return False
            return self.context.buffer_limit and buffer > self.context.buffer_max

        self.holds.append(primary_hold)

        self.update_codes()

        current_x = context.current_x
        current_y = context.current_y

        self.next_x = current_x
        self.next_y = current_y
        self.max_x = current_x
        self.max_y = current_y
        self.min_x = current_x
        self.min_y = current_y
        self.start_x = current_x
        self.start_y = current_y

        context.root.listen("lifecycle;ready", self.on_driver_ready)

    def detach(self, *args, **kwargs):
        self.context.root.unlisten("lifecycle;ready", self.on_driver_ready)
        self.thread = None

    def on_driver_ready(self, origin, *args):
        self.start_driver()

    def __repr__(self):
        return "LhystudiosDriver(%s)" % self.name

    def update_codes(self):
        if not self.context.swap_xy:
            self.CODE_RIGHT = b"B"
            self.CODE_LEFT = b"T"
            self.CODE_TOP = b"L"
            self.CODE_BOTTOM = b"R"
        else:
            self.CODE_RIGHT = b"R"
            self.CODE_LEFT = b"L"
            self.CODE_TOP = b"T"
            self.CODE_BOTTOM = b"B"
        if self.context.flip_x:
            q = self.CODE_LEFT
            self.CODE_LEFT = self.CODE_RIGHT
            self.CODE_RIGHT = q
        if self.context.flip_y:
            q = self.CODE_TOP
            self.CODE_TOP = self.CODE_BOTTOM
            self.CODE_BOTTOM = q

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
                sx = self.context.current_x
                sy = self.context.current_y
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
                        p_set.raster_step != s_set.raster_step
                        or p_set.speed != s_set.speed
                        or s_set.implicit_d_ratio != p_set.implicit_d_ratio
                        or s_set.implicit_accel != p_set.implicit_accel
                    ):
                        self.set_speed(p_set.speed)
                        self.set_step(p_set.raster_step)
                        self.set_acceleration(p_set.implicit_accel)
                        self.set_d_ratio(p_set.implicit_d_ratio)
                    self.settings.set_values(p_set)
                    continue
                if on & PLOT_AXIS:  # Major Axis.
                    self.set_prop(REQUEST_AXIS)
                    if x == 0:  # X Major / Horizontal.
                        self.set_prop(REQUEST_HORIZONTAL_MAJOR)
                    else:  # Y Major / Vertical
                        self.unset_prop(REQUEST_HORIZONTAL_MAJOR)
                    continue
                if on & PLOT_DIRECTION:
                    self.set_prop(REQUEST_X)
                    self.set_prop(REQUEST_Y)
                    if x == 1:  # Moving Right. +x
                        self.unset_prop(REQUEST_X_FORWARD_LEFT)
                    else:  # Moving Left -x
                        self.set_prop(REQUEST_X_FORWARD_LEFT)
                    if y == 1:  # Moving Bottom +y
                        self.unset_prop(REQUEST_Y_FORWARD_TOP)
                    else:  # Moving Top. -y
                        self.set_prop(REQUEST_Y_FORWARD_TOP)
                    continue
                if on & (
                    PLOT_RAPID | PLOT_JOG
                ):  # Plot planner requests position change.
                    if (
                        on & PLOT_RAPID
                        or self.state != DRIVER_STATE_PROGRAM
                        or self.settings.raster_step != 0
                    ):
                        # Perform a rapid position change. Always perform this for raster moves.
                        self.ensure_rapid_mode()
                        self.move_absolute(x, y)
                        continue
                    # Jog is performable and requested. # We have not flagged our direction or state.
                    self.jog_absolute(x, y, mode=self.root_context.opt_jog_mode)
                    continue
                else:
                    self.ensure_program_mode()
                dx = x - sx
                dy = y - sy
                if self.settings.raster_step != 0:
                    if self.is_prop(STATE_X_STEPPER_ENABLE):
                        if dy != 0:
                            if self.is_prop(STATE_Y_FORWARD_TOP):
                                if abs(dy) > self.settings.raster_step:
                                    self.ensure_finished_mode()
                                    self.move_relative(
                                        0, dy + self.settings.raster_step
                                    )
                                    self.set_prop(STATE_X_STEPPER_ENABLE)
                                    self.unset_prop(STATE_Y_STEPPER_ENABLE)
                                    self.ensure_program_mode()
                                self.h_switch()
                            else:
                                if abs(dy) > self.settings.raster_step:
                                    self.ensure_finished_mode()
                                    self.move_relative(
                                        0, dy - self.settings.raster_step
                                    )
                                    self.set_prop(STATE_X_STEPPER_ENABLE)
                                    self.unset_prop(STATE_Y_STEPPER_ENABLE)
                                    self.ensure_program_mode()
                                self.h_switch()
                    elif self.is_prop(STATE_Y_STEPPER_ENABLE):
                        if dx != 0:
                            if self.is_prop(STATE_X_FORWARD_LEFT):
                                if abs(dx) > self.settings.raster_step:
                                    self.ensure_finished_mode()
                                    self.move_relative(
                                        dx + self.settings.raster_step, 0
                                    )
                                    self.set_prop(STATE_Y_STEPPER_ENABLE)
                                    self.unset_prop(STATE_X_STEPPER_ENABLE)
                                    self.ensure_program_mode()
                                self.v_switch()
                            else:
                                if abs(dx) > self.settings.raster_step:
                                    self.ensure_finished_mode()
                                    self.move_relative(
                                        dx - self.settings.raster_step, 0
                                    )
                                    self.set_prop(STATE_Y_STEPPER_ENABLE)
                                    self.unset_prop(STATE_X_STEPPER_ENABLE)
                                    self.ensure_program_mode()
                                self.v_switch()
                self.goto_octent_abs(x, y, on & 1)
            self.plot = None
        return False

    def plot_plot(self, plot):
        """
        :param plot:
        :return:
        """
        self.plot_planner.push(plot)

    def plot_start(self):
        if self.plot is None:
            self.plot = self.plot_planner.gen()

    def pause(self, *values):
        self.realtime_data_output(b"PN!\n")
        self.is_paused = True

    def resume(self, *values):
        self.realtime_data_output(b"PN&\n")
        self.is_paused = False

    def reset(self):
        Driver.reset(self)
        self.context.signal("pipe;buffer", 0)
        self.plot = None
        self.plot_planner.clear()
        self.realtime_data_output(b"I*\n")
        self.laser = False
        self.properties = 0
        self.state = DRIVER_STATE_RAPID
        self.context.signal("driver;mode", self.state)
        self.is_paused = False

    def cut(self, x, y):
        self.goto(x, y, True)

    def cut_absolute(self, x, y):
        self.goto_absolute(x, y, True)

    def cut_relative(self, x, y):
        self.goto_relative(x, y, True)

    def jog(self, x, y, **kwargs):
        if self.is_relative:
            self.jog_relative(x, y, **kwargs)
        else:
            self.jog_absolute(x, y, **kwargs)

    def jog_absolute(self, x, y, **kwargs):
        self.jog_relative(
            x - self.context.current_x, y - self.context.current_y, **kwargs
        )

    def jog_relative(self, dx, dy, mode=0):
        self.laser_off()
        dx = int(round(dx))
        dy = int(round(dy))
        if mode == 0:
            self._program_mode_jog_event(dx, dy)
        elif mode == 1:
            self.fly_switch_speed(dx, dy)
        else:
            self.ensure_rapid_mode()
            self.move_relative(dx, dy)
            self.ensure_program_mode()

    def _program_mode_jog_event(self, dx=0, dy=0):
        dx = int(round(dx))
        dy = int(round(dy))
        self.state = DRIVER_STATE_RAPID
        self.laser = False
        if self.is_prop(STATE_HORIZONTAL_MAJOR):
            if not self.is_left and dx >= 0:
                self.data_output(self.CODE_LEFT)
            if not self.is_right and dx <= 0:
                self.data_output(self.CODE_RIGHT)
        else:
            if not self.is_top and dy >= 0:
                self.data_output(self.CODE_TOP)
            if not self.is_bottom and dy <= 0:
                self.data_output(self.CODE_BOTTOM)
        self.data_output(b"N")
        if dy != 0:
            self.goto_y(dy)
        if dx != 0:
            self.goto_x(dx)
        self.data_output(b"SE")
        self.declare_directions()
        self.state = DRIVER_STATE_PROGRAM

    def move(self, x, y):
        self.goto(x, y, False)

    def move_absolute(self, x, y):
        self.goto_absolute(x, y, False)

    def move_relative(self, x, y):
        self.goto_relative(x, y, False)

    def goto(self, x, y, cut):
        """
        Goto a position within a cut.

        This depends on whether is_relative is set.

        :param x:
        :param y:
        :param cut:
        :return:
        """
        if self.is_relative:
            self.goto_relative(x, y, cut)
        else:
            self.goto_absolute(x, y, cut)

    def goto_absolute(self, x, y, cut):
        """
        Goto absolute x and y. With cut set or not set.

        :param x:
        :param y:
        :param cut:
        :return:
        """
        self.goto_relative(x - self.context.current_x, y - self.context.current_y, cut)

    def goto_relative(self, dx, dy, cut):
        """
        Goto relative dx, dy. With cut set or not set.

        :param dx:
        :param dy:
        :param cut:
        :return:
        """
        if abs(dx) == 0 and abs(dy) == 0:
            return
        dx = int(round(dx))
        dy = int(round(dy))
        if self.state == DRIVER_STATE_RAPID:
            if self.rapid_override and (dx != 0 or dy != 0):
                self.set_acceleration(None)
                self.set_step(0)
                if dx != 0:
                    self.ensure_rapid_mode()
                    self.set_speed(self.rapid_override_speed_x)
                    self.ensure_program_mode()
                    self.goto_octent(dx, 0, cut)
                if dy != 0:
                    if self.rapid_override_speed_x != self.rapid_override_speed_y:
                        self.ensure_rapid_mode()
                        self.set_speed(self.rapid_override_speed_y)
                        self.ensure_program_mode()
                    self.goto_octent(0, dy, cut)
                self.ensure_rapid_mode()
            else:
                self.data_output(b"I")
                if dx != 0:
                    self.goto_x(dx)
                if dy != 0:
                    self.goto_y(dy)
                self.data_output(b"S1P\n")
                if not self.context.autolock:
                    self.data_output(b"IS2P\n")
        elif self.state == DRIVER_STATE_PROGRAM:
            mx = 0
            my = 0
            for x, y in ZinglPlotter.plot_line(0, 0, dx, dy):
                self.goto_octent(x - mx, y - my, cut)
                mx = x
                my = y
        elif self.state == DRIVER_STATE_FINISH:
            if dx != 0:
                self.goto_x(dx)
            if dy != 0:
                self.goto_y(dy)
            self.data_output(b"N")
        elif self.state == DRIVER_STATE_MODECHANGE:
            self.fly_switch_speed(dx, dy)
        self.check_bounds()
        # self.context.signal('driver;position', (self.context.current_x, self.context.current_y,
        #                                              self.context.current_x - dx, self.context.current_y - dy))

    def goto_octent_abs(self, x, y, on):
        dx = x - self.context.current_x
        dy = y - self.context.current_y
        self.goto_octent(dx, dy, on)

    def goto_octent(self, dx, dy, on):
        if dx == 0 and dy == 0:
            return
        if on:
            self.laser_on()
        else:
            self.laser_off()
        if abs(dx) == abs(dy):
            if dx != 0:
                self.goto_angle(dx, dy)
        elif dx != 0:
            self.goto_x(dx)
            if dy != 0:
                raise ValueError(
                    "Not a valid diagonal or orthogonal movement. (dx=%s, dy=%s)"
                    % (str(dx), str(dy))
                )
        else:
            self.goto_y(dy)
            if dx != 0:
                raise ValueError(
                    "Not a valid diagonal or orthogonal movement. (dx=%s, dy=%s)"
                    % (str(dx), str(dy))
                )
        # self.context.signal('driver;position', (self.context.current_x, self.context.current_y,
        #                                              self.context.current_x - dx, self.context.current_y - dy))

    def set_speed(self, speed=None):
        if self.settings.speed != speed:
            self.settings.speed = speed
            if self.state == DRIVER_STATE_PROGRAM:
                self.state = DRIVER_STATE_MODECHANGE

    def set_d_ratio(self, dratio=None):
        if self.settings.dratio != dratio:
            self.settings.dratio = dratio
            if self.state == DRIVER_STATE_PROGRAM:
                self.state = DRIVER_STATE_MODECHANGE

    def set_acceleration(self, accel=None):
        if self.settings.acceleration != accel:
            self.settings.acceleration = accel
            if self.state == DRIVER_STATE_PROGRAM:
                self.state = DRIVER_STATE_MODECHANGE

    def set_step(self, step=None):
        if self.settings.raster_step != step:
            self.settings.raster_step = step
            if self.state == DRIVER_STATE_PROGRAM:
                self.state = DRIVER_STATE_MODECHANGE

    def laser_off(self):
        if not self.laser:
            return False
        if self.state == DRIVER_STATE_RAPID:
            self.data_output(b"I")
            self.data_output(self.CODE_LASER_OFF)
            self.data_output(b"S1P\n")
            if not self.context.autolock:
                self.data_output(b"IS2P\n")
        elif self.state == DRIVER_STATE_PROGRAM:
            self.data_output(self.CODE_LASER_OFF)
        elif self.state == DRIVER_STATE_FINISH:
            self.data_output(self.CODE_LASER_OFF)
            self.data_output(b"N")
        self.laser = False
        return True

    def laser_on(self):
        if self.laser:
            return False
        if self.state == DRIVER_STATE_RAPID:
            self.data_output(b"I")
            self.data_output(self.CODE_LASER_ON)
            self.data_output(b"S1P\n")
            if not self.context.autolock:
                self.data_output(b"IS2P\n")
        elif self.state == DRIVER_STATE_PROGRAM:
            self.data_output(self.CODE_LASER_ON)
        elif self.state == DRIVER_STATE_FINISH:
            self.data_output(self.CODE_LASER_ON)
            self.data_output(b"N")
        self.laser = True
        return True

    def ensure_rapid_mode(self):
        if self.state == DRIVER_STATE_RAPID:
            return
        if self.state == DRIVER_STATE_FINISH:
            self.data_output(b"S1P\n")
            if not self.context.autolock:
                self.data_output(b"IS2P\n")
        elif (
            self.state == DRIVER_STATE_PROGRAM or self.state == DRIVER_STATE_MODECHANGE
        ):
            self.data_output(b"FNSE-\n")
            self.laser = False
        self.state = DRIVER_STATE_RAPID
        self.context.signal("driver;mode", self.state)

    def fly_switch_speed(self, dx=0, dy=0):
        dx = int(round(dx))
        dy = int(round(dy))
        self.data_output(b"@NSE")
        self.state = DRIVER_STATE_RAPID
        speed_code = LaserSpeed(
            self.context.board,
            self.settings.speed,
            self.settings.raster_step,
            d_ratio=self.settings.implicit_d_ratio,
            acceleration=self.settings.implicit_accel,
            fix_limit=True,
            fix_lows=True,
            fix_speeds=self.context.fix_speeds,
            raster_horizontal=True,
        ).speedcode
        try:
            speed_code = bytes(speed_code)
        except TypeError:
            speed_code = bytes(speed_code, "utf8")
        self.data_output(speed_code)
        if dx != 0:
            self.goto_x(dx)
        if dy != 0:
            self.goto_y(dy)
        self.data_output(b"N")
        self.set_requested_directions()
        self.data_output(self.code_declare_directions())
        self.data_output(b"S1E")
        self.state = DRIVER_STATE_PROGRAM

    def ensure_finished_mode(self):
        if self.state == DRIVER_STATE_FINISH:
            return
        if self.state == DRIVER_STATE_PROGRAM or self.state == DRIVER_STATE_MODECHANGE:
            self.data_output(b"@NSE")
            self.laser = False
        elif self.state == DRIVER_STATE_RAPID:
            self.data_output(b"I")
        self.state = DRIVER_STATE_FINISH
        self.context.signal("driver;mode", self.state)

    def ensure_program_mode(self):
        if self.state == DRIVER_STATE_PROGRAM:
            return
        self.ensure_finished_mode()

        speed_code = LaserSpeed(
            self.context.board,
            self.settings.speed,
            self.settings.raster_step,
            d_ratio=self.settings.implicit_d_ratio,
            acceleration=self.settings.implicit_accel,
            fix_limit=True,
            fix_lows=True,
            fix_speeds=self.context.fix_speeds,
            raster_horizontal=True,
        ).speedcode
        try:
            speed_code = bytes(speed_code)
        except TypeError:
            speed_code = bytes(speed_code, "utf8")
        self.data_output(speed_code)
        self.data_output(b"N")
        self.set_requested_directions()
        self.declare_directions()
        self.data_output(b"S1E")
        self.state = DRIVER_STATE_PROGRAM
        self.context.signal("driver;mode", self.state)

    def h_switch(self):
        if self.is_prop(STATE_X_FORWARD_LEFT):
            self.data_output(self.CODE_RIGHT)
            self.unset_prop(STATE_X_FORWARD_LEFT)
        else:
            self.data_output(self.CODE_LEFT)
            self.set_prop(STATE_X_FORWARD_LEFT)
        if self.is_prop(STATE_Y_FORWARD_TOP):
            self.context.current_y -= self.settings.raster_step
        else:
            self.context.current_y += self.settings.raster_step
        self.laser = False

    def v_switch(self):
        if self.is_prop(STATE_Y_FORWARD_TOP):
            self.data_output(self.CODE_BOTTOM)
            self.unset_prop(STATE_Y_FORWARD_TOP)
        else:
            self.data_output(self.CODE_TOP)
            self.set_prop(STATE_Y_FORWARD_TOP)
        if self.is_prop(STATE_X_FORWARD_LEFT):
            self.context.current_x -= self.settings.raster_step
        else:
            self.context.current_x += self.settings.raster_step
        self.laser = False

    def calc_home_position(self):
        x = 0
        y = 0
        bed_dim = self.context.get_context("/")
        bed_dim.setting(int, "bed_width", 310)
        bed_dim.setting(int, "bed_height", 210)
        if self.context.home_right:
            x = int(bed_dim.bed_width * 39.3701)
        if self.context.home_bottom:
            y = int(bed_dim.bed_height * 39.3701)
        return x, y

    def home(self, *values):
        x, y = self.calc_home_position()
        self.ensure_rapid_mode()
        self.data_output(b"IPP\n")
        # old_x = self.context.current_x
        # old_y = self.context.current_y
        self.context.current_x = x
        self.context.current_y = y
        self.reset_modes()
        self.state = DRIVER_STATE_RAPID
        adjust_x = self.context.home_adjust_x
        adjust_y = self.context.home_adjust_y
        try:
            adjust_x = int(values[0])
        except (ValueError, IndexError):
            pass
        try:
            adjust_y = int(values[1])
        except (ValueError, IndexError):
            pass
        if adjust_x != 0 or adjust_y != 0:
            # Perform post home adjustment.
            self.move_relative(adjust_x, adjust_y)
            # Erase adjustment
            self.context.current_x = x
            self.context.current_y = y

        self.context.signal("driver;mode", self.state)
        # self.context.signal('driver;position', (self.context.current_x, self.context.current_y, old_x, old_y))

    def lock_rail(self):
        self.ensure_rapid_mode()
        self.data_output(b"IS1P\n")

    def unlock_rail(self, abort=False):
        self.ensure_rapid_mode()
        self.data_output(b"IS2P\n")

    def abort(self):
        self.data_output(b"I\n")

    def check_bounds(self):
        self.min_x = min(self.min_x, self.context.current_x)
        self.min_y = min(self.min_y, self.context.current_y)
        self.max_x = max(self.max_x, self.context.current_x)
        self.max_y = max(self.max_y, self.context.current_y)

    def reset_modes(self):
        self.laser = False
        self.properties = 0

    def goto_x(self, dx):
        if dx > 0:
            self.move_right(dx)
        else:
            self.move_left(dx)

    def goto_y(self, dy):
        if dy > 0:
            self.move_bottom(dy)
        else:
            self.move_top(dy)

    def goto_angle(self, dx, dy):
        if abs(dx) != abs(dy):
            raise ValueError("abs(dx) must equal abs(dy)")
        self.set_prop(STATE_X_STEPPER_ENABLE)  # Set both on
        self.set_prop(STATE_Y_STEPPER_ENABLE)
        if dx > 0:  # Moving right
            if self.is_prop(STATE_X_FORWARD_LEFT):
                self.data_output(self.CODE_RIGHT)
                self.unset_prop(STATE_X_FORWARD_LEFT)
        else:  # Moving left
            if not self.is_prop(STATE_X_FORWARD_LEFT):
                self.data_output(self.CODE_LEFT)
                self.set_prop(STATE_X_FORWARD_LEFT)
        if dy > 0:  # Moving bottom
            if self.is_prop(STATE_Y_FORWARD_TOP):
                self.data_output(self.CODE_BOTTOM)
                self.unset_prop(STATE_Y_FORWARD_TOP)
        else:  # Moving top
            if not self.is_prop(STATE_Y_FORWARD_TOP):
                self.data_output(self.CODE_TOP)
                self.set_prop(STATE_Y_FORWARD_TOP)
        self.context.current_x += dx
        self.context.current_y += dy
        self.check_bounds()
        self.data_output(self.CODE_ANGLE + lhymicro_distance(abs(dy)))

    def set_requested_directions(self):
        if self.context.strict:
            self.unset_prop(STATE_X_FORWARD_LEFT)
            self.unset_prop(STATE_Y_FORWARD_TOP)
            self.unset_prop(STATE_HORIZONTAL_MAJOR)
        else:
            if self.is_prop(REQUEST_X):
                if self.is_prop(REQUEST_X_FORWARD_LEFT):
                    self.set_prop(STATE_X_FORWARD_LEFT)
                else:
                    self.unset_prop(STATE_X_FORWARD_LEFT)
                self.unset_prop(REQUEST_X)
            if self.is_prop(REQUEST_Y):
                if self.is_prop(REQUEST_Y_FORWARD_TOP):
                    self.set_prop(STATE_Y_FORWARD_TOP)
                else:
                    self.unset_prop(STATE_Y_FORWARD_TOP)
                self.unset_prop(REQUEST_Y)
            if self.is_prop(REQUEST_AXIS):
                if self.is_prop(REQUEST_HORIZONTAL_MAJOR):
                    self.set_prop(STATE_HORIZONTAL_MAJOR)
                else:
                    self.unset_prop(STATE_HORIZONTAL_MAJOR)
                self.unset_prop(REQUEST_AXIS)

    def declare_directions(self):
        """Declare direction declares raster directions of left, top, with the primary momentum direction going last.
        You cannot declare a diagonal direction."""
        self.data_output(self.code_declare_directions())

    def code_declare_directions(self):
        x_dir = (
            self.CODE_LEFT if self.is_prop(STATE_X_FORWARD_LEFT) else self.CODE_RIGHT
        )
        y_dir = self.CODE_TOP if self.is_prop(STATE_Y_FORWARD_TOP) else self.CODE_BOTTOM
        if self.is_prop(STATE_HORIZONTAL_MAJOR):
            self.set_prop(STATE_X_STEPPER_ENABLE)
            self.unset_prop(STATE_Y_STEPPER_ENABLE)
            return y_dir + x_dir
        else:
            self.unset_prop(STATE_X_STEPPER_ENABLE)
            self.set_prop(STATE_Y_STEPPER_ENABLE)
            return x_dir + y_dir

    @property
    def is_left(self):
        return (
            self.is_prop(STATE_X_STEPPER_ENABLE)
            and not self.is_prop(STATE_Y_STEPPER_ENABLE)
            and self.is_prop(STATE_X_FORWARD_LEFT)
        )

    @property
    def is_right(self):
        return (
            self.is_prop(STATE_X_STEPPER_ENABLE)
            and not self.is_prop(STATE_Y_STEPPER_ENABLE)
            and not self.is_prop(STATE_X_FORWARD_LEFT)
        )

    @property
    def is_top(self):
        return (
            not self.is_prop(STATE_X_STEPPER_ENABLE)
            and self.is_prop(STATE_Y_STEPPER_ENABLE)
            and self.is_prop(STATE_Y_FORWARD_TOP)
        )

    @property
    def is_bottom(self):
        return (
            not self.is_prop(STATE_X_STEPPER_ENABLE)
            and self.is_prop(STATE_Y_STEPPER_ENABLE)
            and not self.is_prop(STATE_Y_FORWARD_TOP)
        )

    @property
    def is_angle(self):
        return self.is_prop(STATE_Y_STEPPER_ENABLE) and self.is_prop(
            STATE_X_STEPPER_ENABLE
        )

    def set_left(self):
        self.set_prop(STATE_X_STEPPER_ENABLE)
        self.unset_prop(STATE_Y_STEPPER_ENABLE)
        self.set_prop(STATE_X_FORWARD_LEFT)

    def set_right(self):
        self.set_prop(STATE_X_STEPPER_ENABLE)
        self.unset_prop(STATE_Y_STEPPER_ENABLE)
        self.unset_prop(STATE_X_FORWARD_LEFT)

    def set_top(self):
        self.unset_prop(STATE_X_STEPPER_ENABLE)
        self.set_prop(STATE_Y_STEPPER_ENABLE)
        self.set_prop(STATE_Y_FORWARD_TOP)

    def set_bottom(self):
        self.unset_prop(STATE_X_STEPPER_ENABLE)
        self.set_prop(STATE_Y_STEPPER_ENABLE)
        self.unset_prop(STATE_Y_FORWARD_TOP)

    def move_right(self, dx=0):
        self.context.current_x += dx
        if not self.is_right or self.state != DRIVER_STATE_PROGRAM:
            self.data_output(self.CODE_RIGHT)
            self.set_right()
        if dx != 0:
            self.data_output(lhymicro_distance(abs(dx)))
            self.check_bounds()

    def move_left(self, dx=0):
        self.context.current_x -= abs(dx)
        if not self.is_left or self.state != DRIVER_STATE_PROGRAM:
            self.data_output(self.CODE_LEFT)
            self.set_left()
        if dx != 0:
            self.data_output(lhymicro_distance(abs(dx)))
            self.check_bounds()

    def move_bottom(self, dy=0):
        self.context.current_y += dy
        if not self.is_bottom or self.state != DRIVER_STATE_PROGRAM:
            self.data_output(self.CODE_BOTTOM)
            self.set_bottom()
        if dy != 0:
            self.data_output(lhymicro_distance(abs(dy)))
            self.check_bounds()

    def move_top(self, dy=0):
        self.context.current_y -= abs(dy)
        if not self.is_top or self.state != DRIVER_STATE_PROGRAM:
            self.data_output(self.CODE_TOP)
            self.set_top()
        if dy != 0:
            self.data_output(lhymicro_distance(abs(dy)))
            self.check_bounds()

    @property
    def type(self):
        return "lhystudios"


class LhystudiosController:
    """
    K40 Controller controls the Lhystudios boards sending any queued data to the USB when the signal is not busy.

    This is registered in the kernel as a module. Saving a few persistent settings like packet_count and registering
    a couple controls like Connect_USB.

    This is also a Pipe. Elements written to the Controller are sent to the USB to the matched device. Opening and
    closing of the pipe are dealt with internally. There are three primary monitor data channels. 'send', 'recv' and
    'usb'. They display the reading and writing of information to/from the USB and the USB connection log, providing
    information about the connecting and error status of the USB device.
    """

    def __init__(self, context, name, channel=None, *args, **kwargs):
        context = context.get_context("lhystudios/output/%s" % name)
        self.context = context
        self.name = name
        self.state = STATE_UNKNOWN
        self.is_shutdown = False

        self.next = None
        self.prev = None

        self._thread = None
        self._buffer = (
            bytearray()
        )  # Threadsafe buffered commands to be sent to controller.
        self._realtime_buffer = (
            bytearray()  # Threadsafe realtime buffered commands to be sent to the controller.
        )
        self._queue = bytearray()  # Thread-unsafe additional commands to append.
        self._preempt = (
            bytearray()
        )  # Thread-unsafe preempt commands to prepend to the buffer.
        self.context._buffer_size = 0
        self._queue_lock = threading.Lock()
        self._preempt_lock = threading.Lock()
        self._main_lock = threading.Lock()

        self._status = [0] * 6
        self._usb_state = -1

        self.ch341 = self.context.open("module/ch341")
        self.connection = None
        self.max_attempts = 5
        self.refuse_counts = 0
        self.connection_errors = 0
        self.count = 0
        self.pre_ok = False

        self.abort_waiting = False
        self.pipe_channel = context.channel("%s/events" % name)
        self.usb_log = context.channel("%s/usb" % name, buffer_size=20)
        self.usb_send_channel = context.channel("%s/usb_send" % name)
        self.recv_channel = context.channel("%s/recv" % name)
        self.usb_log.watch(lambda e: context.signal("pipe;usb_status", e))

        context = self.context

        context.setting(int, "usb_index", -1)
        context.setting(int, "usb_bus", -1)
        context.setting(int, "usb_address", -1)
        context.setting(int, "usb_version", -1)
        context.setting(bool, "mock", False)
        context.setting(int, "packet_count", 0)
        context.setting(int, "rejected_count", 0)

        self.reset()

        self.context.root.listen("lifecycle;ready", self.on_controller_ready)

    def viewbuffer(self):
        buffer = bytes(self._realtime_buffer) + bytes(self._buffer) + bytes(self._queue)
        try:
            buffer_str = buffer.decode()
        except ValueError:
            try:
                buffer_str = buffer.decode("utf8")
            except UnicodeDecodeError:
                buffer_str = str(buffer)
        except AttributeError:
            buffer_str = buffer
        return buffer_str

    def on_controller_ready(self, origin, *args):
        self.start()

    def finalize(self, *args, **kwargs):
        self.context.get_context("/").unlisten(
            "lifecycle;ready", self.on_controller_ready
        )
        if self._thread is not None:
            self.write(b"\x18\n")

    def __repr__(self):
        return "LhystudiosController(%s)" % self.name

    def __len__(self):
        """Provides the length of the buffer of this device."""
        return len(self._buffer) + len(self._queue) + len(self._preempt)

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
        else:
            self.connection.open()

        if self.connection is None:
            raise ConnectionRefusedError

    def close(self):
        self.pipe_channel("close()")
        if self.connection is not None:
            self.connection.close()
            self.connection = None

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
        self.start()
        self.update_buffer()
        return self

    def realtime_write(self, bytes_to_write):
        """
        Writes data to the preempting commands, this will be moved to the front of the buffer by the thread
        in a threadsafe manner.

        :param bytes_to_write: data to write to the front of the queue.
        :return:
        """
        self.pipe_channel("realtime_write(%s)" % str(bytes_to_write))
        self._preempt_lock.acquire(True)
        self._preempt = bytearray(bytes_to_write) + self._preempt
        self._preempt_lock.release()
        self.start()
        self.update_buffer()
        return self

    def start(self):
        """
        Controller state change to Started.
        :return:
        """
        if self._thread is None or not self._thread.is_alive():
            self._thread = self.context.threaded(
                self._thread_data_send, thread_name="LhyPipe(%s)" % (self.context._path)
            )
            self._thread.stop = self.stop
            self.update_state(STATE_INITIALIZE)

    def _pause_busy(self):
        """
        BUSY can be called in a paused state to packet halt the controller.

        This can only be done from PAUSE..
        """
        if self.state != STATE_PAUSE:
            self.pause()
        if self.state == STATE_PAUSE:
            self.update_state(STATE_BUSY)

    def _resume_busy(self):
        """
        Resumes from a BUSY to restore the controller. This will return to a paused state.

        This can only be done from BUSY.
        """
        if self.state == STATE_BUSY:
            self.update_state(STATE_PAUSE)
            self.resume()

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
        self._buffer = bytearray()
        self._queue = bytearray()
        self.context.signal("pipe;buffer", 0)
        self.update_state(STATE_TERMINATE)

    def reset(self):
        self.update_state(STATE_INITIALIZE)

    def stop(self):
        self.abort()
        self._thread.join()  # Wait until stop completes before continuing.

    def update_state(self, state):
        if state == self.state:
            return
        self.state = state
        if self.context is not None:
            self.context.signal("pipe;thread", self.state)

    def update_buffer(self):
        if self.context is not None:
            self.context._buffer_size = (
                len(self._realtime_buffer) + len(self._buffer) + len(self._queue)
            )
            self.context.signal("pipe;buffer", len(self))

    def update_packet(self, packet):
        if self.context is not None:
            self.context.signal("pipe;packet", convert_to_list_bytes(packet))
            self.context.signal("pipe;packet_text", packet)
            self.usb_send_channel(packet)

    def _thread_data_send(self):
        """
        Main threaded function to send data. While the controller is working the thread
        will be doing work in this function.
        """
        self._main_lock.acquire(True)
        self.count = 0
        self.pre_ok = False
        self.is_shutdown = False
        while self.state != STATE_END and self.state != STATE_TERMINATE:
            if self.state == STATE_INITIALIZE:
                # If we are initialized. Change that to active since we're running.
                self.update_state(STATE_ACTIVE)
            if self.state == STATE_PAUSE or self.state == STATE_BUSY:
                # If we are paused just keep sleeping until the state changes.
                if len(self._realtime_buffer) == 0 and len(self._preempt) == 0:
                    # Only pause if there are no realtime commands to queue.
                    time.sleep(0.25)
                    continue
            try:
                # We try to process the queue.
                queue_processed = self.process_queue()
                self.refuse_counts = 0
                if self.is_shutdown:
                    break  # Sometimes it could reset this and escape.
            except ConnectionRefusedError:
                # The attempt refused the connection.
                self.refuse_counts += 1
                self.pre_ok = False
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
                self.pre_ok = False
                time.sleep(0.5)
                self.close()
                continue
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
                continue
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
        self._thread = None
        self.is_shutdown = False
        self.update_state(STATE_END)
        self.pre_ok = False
        self._main_lock.release()

    def process_queue(self):
        """
        Attempts to process the buffer/queue
        Will fail on ConnectionRefusedError at open, 'process_queue_pause = True' (anytime before packet sent),
        self._buffer is empty, or a failure to produce packet.

        Buffer will not be changed unless packet is successfully sent, or pipe commands are processed.

        - : tells the system to require wait finish at the end of the queue processing.
        * : tells the system to clear the buffers, and abort the thread.
        ! : tells the system to pause.
        & : tells the system to resume.
        \x18 : tells the system to quit.

        :return: queue process success.
        """
        if len(self._queue):  # check for and append queue
            self._queue_lock.acquire(True)
            self._buffer += self._queue
            self._queue = bytearray()
            self._queue_lock.release()
            self.update_buffer()

        if len(self._preempt):  # check for and prepend preempt
            self._preempt_lock.acquire(True)
            self._realtime_buffer += self._preempt
            self._preempt = bytearray()
            self._preempt_lock.release()
            self.update_buffer()

        if len(self._realtime_buffer) > 0:
            buffer = self._realtime_buffer
            realtime = True
        else:
            if len(self._buffer) > 0:
                buffer = self._buffer
                realtime = False
            else:
                # The buffer and realtime buffers are empty. No packet creation possible.
                return False

        # Find buffer of 30 or containing '\n'.
        find = buffer.find(b"\n", 0, 30)
        if find == -1:  # No end found.
            length = min(30, len(buffer))
        else:  # Line end found.
            length = min(30, len(buffer), find + 1)
        packet = bytes(buffer[:length])

        # edge condition of catching only pipe command without '\n'
        if packet.endswith((b"-", b"*", b"&", b"!", b"#", b"\x18")):
            packet += buffer[length : length + 1]
            length += 1
        post_send_command = None

        # find pipe commands.
        if packet.endswith(b"\n"):
            packet = packet[:-1]
            if packet.endswith(b"-"):  # wait finish
                packet = packet[:-1]
                post_send_command = self.wait_finished
            elif packet.endswith(b"*"):  # abort
                post_send_command = self.abort
                packet = packet[:-1]
            elif packet.endswith(b"&"):  # resume
                self._resume_busy()
                packet = packet[:-1]
            elif packet.endswith(b"!"):  # pause
                self._pause_busy()
                packet = packet[:-1]
            elif packet.endswith(b"\x18"):
                self.state = STATE_TERMINATE
                self.is_shutdown = True
                packet = packet[:-1]
            if len(packet) != 0:
                if packet.endswith(b"#"):
                    packet = packet[:-1]
                    try:
                        c = packet[-1]
                    except IndexError:
                        c = b"F"  # Packet was simply #. We can do nothing.
                    packet += bytes([c]) * (30 - len(packet))  # Padding. '\n'
                else:
                    packet += b"F" * (30 - len(packet))  # Padding. '\n'
        if not realtime and self.state in (STATE_PAUSE, STATE_BUSY):
            return False  # Processing normal queue, PAUSE and BUSY apply.

        # Packet is prepared and ready to send. Open Channel.
        self.open()

        if len(packet) == 30:
            # We have a sendable packet.
            if not self.pre_ok:
                self.wait_until_accepting_packets()
            self.send_packet(packet)

            # Packet is sent, trying to confirm.
            status = 0
            flawless = True
            for attempts in range(300):
                # We'll try to confirm this at 300 times.
                try:
                    self.update_status()
                    status = self._status[1]
                except ConnectionError:
                    # Errors are ignored, must confirm packet.
                    flawless = False
                    continue
                if status == 0:
                    # We did not read a status.
                    continue
                elif status == STATUS_OK:
                    # Packet was fine.
                    self.pre_ok = True
                    break
                elif status == STATUS_BUSY:
                    # Busy. We still do not have our confirmation. BUSY comes before ERROR or OK.
                    continue
                elif status == STATUS_ERROR:
                    self.context.rejected_count += 1
                    if flawless:  # Packet was rejected. The CRC failed.
                        return False
                    else:
                        # The channel had the error, assuming packet was actually good.
                        break
                elif status == STATUS_FINISH:
                    # We finished. If we were going to wait for that, we no longer need to.
                    if post_send_command == self.wait_finished:
                        post_send_command = None
                    continue  # This is not a confirmation.
            if status == 0:  # After 300 attempts we could only get status = 0.
                raise ConnectionError  # Broken pipe. 300 attempts. Could not confirm packet.
            self.context.packet_count += (
                1  # Our packet is confirmed or assumed confirmed.
            )
        else:
            if len(packet) != 0:
                # We could only generate a partial packet, throw it back
                return False
            # We have an empty packet of only commands. Continue work.

        # Packet was processed. Remove that data.
        if realtime:
            self._realtime_buffer = self._realtime_buffer[length:]
        else:
            self._buffer = self._buffer[length:]
        self.update_buffer()

        if post_send_command is not None:
            # Post send command could be wait_finished, and might have a broken pipe.
            try:
                post_send_command()
            except ConnectionError:
                # We should have already sent the packet. So this should be fine.
                pass
        return True  # A packet was prepped and sent correctly.

    def send_packet(self, packet):
        packet = b"\x00" + packet + bytes([onewire_crc_lookup(packet)])
        self.connection.write(packet)
        self.update_packet(packet)
        self.pre_ok = False

    def update_status(self):
        try:
            self._status = self.connection.get_status()
        except AttributeError:
            # self.connection was closed by something.
            raise ConnectionError
        if self.context is not None:
            self.context.signal(
                "pipe;status", self._status, get_code_string_from_code(self._status[1])
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
                self.pre_ok = False
                break
            if status == STATUS_ERROR:
                break
            time.sleep(0.05)
            if self.context is not None:
                self.context.signal("pipe;wait", STATUS_OK, i)
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
                raise ConnectionError
            if status == STATUS_ERROR:
                self.context.rejected_count += 1
            if status & 0x02 == 0:
                # StateBitPEMP = 0x00000200, Finished = 0xEC, 11101100
                break
            if self.context is not None:
                self.context.signal("pipe;wait", status, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.
        self.update_state(original_state)

    @property
    def type(self):
        return "lhystudios"
