import math
import threading
import time

from meerk40t.tools.zinglplotter import ZinglPlotter

from ...core.drivers import Driver
from ...core.plotplanner import grouped
from ...kernel import (
    STATE_ACTIVE,
    STATE_BUSY,
    STATE_END,
    STATE_IDLE,
    STATE_INITIALIZE,
    STATE_PAUSE,
    STATE_SUSPEND,
    STATE_TERMINATE,
    STATE_UNKNOWN,
    STATE_WAIT,
)
from ...svgelements import Length
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
    PLOT_LEFT_UPPER,
    PLOT_RAPID,
    PLOT_RIGHT_LOWER,
    PLOT_SETTING,
    PLOT_START,
)
from ..lasercommandconstants import *
from .laserspeed import LaserSpeed
from .lhystudiosemulator import EgvLoader, LhystudiosEmulator

MILS_IN_MM = 39.3701


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        _ = kernel.translation
        kernel.register("driver/lhystudios", LhystudiosDriver)
        kernel.register("output/lhystudios", LhystudiosController)
        kernel.register("emulator/lhystudios", LhystudiosEmulator)
        kernel.register("load/EgvLoader", EgvLoader)
        context = kernel.root

        @context.console_option(
            "idonotlovemyhouse",
            type=bool,
            action="store_true",
            help=_("override one second laser fire pulse duration"),
        )
        @context.console_argument(
            "time", type=float, help=_("laser fire pulse duration")
        )
        @context.console_command(
            "pulse",
            input_type="lhystudios",
            help=_("pulse <time>: Pulse the laser in place."),
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
                    _('"%s" exceeds 1 second limit to fire a standing laser.') % value
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

        @context.console_argument("speed", type=float, help=_("Set the movement speed"))
        @context.console_argument("dx", type=Length, help=_("change in x"))
        @context.console_argument("dy", type=Length, help=_("change in y"))
        @context.console_command(
            "move_at_speed",
            input_type="lhystudios",
            help=_("move_at_speed <speed> <dx> <dy>"),
        )
        def move_speed(channel, _, speed, dx, dy, data=None, **kwgs):
            spooler, driver, output = data
            dx = Length(dx).value(ppi=1000.0)
            dy = Length(dy).value(ppi=1000.0)

            def move_at_speed():
                yield COMMAND_SET_SPEED, speed
                yield COMMAND_MODE_PROGRAM
                x = driver.current_x
                y = driver.current_y
                yield COMMAND_MOVE, x + dx, y + dy
                yield COMMAND_MODE_RAPID

            if not spooler.job_if_idle(move_at_speed):
                channel(_("Busy"))
            return

        @context.console_option(
            "difference",
            "d",
            type=bool,
            action="store_true",
            help=_("Change speed by this amount."),
        )
        @context.console_argument("speed", type=str, help=_("Set the driver speed."))
        @context.console_command(
            "speed", input_type="lhystudios", help=_("Set current speed of driver.")
        )
        def speed(
            command, channel, _, data=None, speed=None, difference=False, **kwargs
        ):
            spooler, driver, output = data
            if speed is None:
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
            if percent and difference:
                s = driver.speed + driver.speed * (s / 100.0)
            elif difference:
                s += driver.speed
            elif percent:
                s = driver.speed * (s / 100.0)
            driver.set_speed(s)
            channel(_("Speed set at: %f mm/s") % driver.speed)

        @context.console_argument("ppi", type=int, help=_("pulses per inch [0-1000]"))
        @context.console_command(
            "power", input_type="lhystudios", help=_("Set Driver Power")
        )
        def power(command, channel, _, data, ppi=None, **kwargs):
            spooler, driver, output = data
            if ppi is None:
                channel(_("Power set at: %d pulses per inch") % driver.power)
            else:
                try:
                    driver.set_power(ppi)
                except ValueError:
                    pass

        @context.console_argument(
            "accel", type=int, help=_("Acceleration amount [1-4]")
        )
        @context.console_command(
            "acceleration",
            input_type="lhystudios",
            help=_("Set Driver Acceleration [1-4]"),
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
            help=_("update movement codes for the drivers"),
        )
        def code_update(data=None, **kwargs):
            spooler, driver, output = data
            driver.update_codes()

        @context.console_command(
            "status",
            input_type="lhystudios",
            help=_("abort waiting process on the controller."),
        )
        def realtime_status(channel, _, data=None, **kwargs):
            spooler, driver, output = data
            try:
                output.update_status()
            except ConnectionError:
                channel(_("Could not check status, usb not connected."))

        @context.console_command(
            "continue",
            input_type="lhystudios",
            help=_("abort waiting process on the controller."),
        )
        def realtime_continue(data=None, **kwargs):
            spooler, driver, output = data
            output.abort_waiting = True

        @context.console_command(
            "pause",
            input_type="lhystudios",
            help=_("realtime pause/resume of the machine"),
        )
        def realtime_pause(data=None, **kwargs):
            spooler, driver, output = data
            if driver.is_paused:
                driver.resume()
            else:
                driver.pause()

        @context.console_command(
            ("estop", "abort"), input_type="lhystudios", help=_("Abort Job")
        )
        def pipe_abort(channel, _, data=None, **kwargs):
            spooler, driver, output = data
            driver.reset()
            channel(_("Lhystudios Channel Aborted."))

        @context.console_argument(
            "rapid_x", type=float, help=_("limit x speed for rapid.")
        )
        @context.console_argument(
            "rapid_y", type=float, help=_("limit y speed for rapid.")
        )
        @context.console_command(
            "rapid_override",
            input_type="lhystudios",
            help=_("limit speed of typical rapid moves."),
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
            "egv_import",
            input_type="lhystudios",
            help=_("Lhystudios Engrave Buffer Import. egv_import <egv_file>"),
        )
        def egv_import(channel, _, filename, data=None, **kwargs):
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

            try:
                with open(filename, "r") as f:
                    skip_header(f)
                    while True:
                        data = f.read(1024)
                        if not data:
                            break
                        buffer = bytes(data, "utf8")
                        output.write(buffer)
                    output.write(b"\n")
            except (PermissionError, IOError, FileNotFoundError):
                channel(_("Could not load: %s" % filename))

        @context.console_argument("filename", type=str)
        @context.console_command(
            "egv_export",
            input_type="lhystudios",
            help=_("Lhystudios Engrave Buffer Export. egv_export <egv_file>"),
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
                        % (output.context.kernel.name, output.context.kernel.version)
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
            help=_("Lhystudios Engrave Code Sender. egv <lhymicro-gl>"),
        )
        def egv(command, channel, _, data=None, remainder=None, **kwargs):
            spooler, driver, output = data
            if remainder is None or len(remainder) == 0:
                channel("Lhystudios Engrave Code Sender. egv <lhymicro-gl>")
            else:
                output.write(
                    bytes(remainder.replace("$", "\n").replace(" ", "\n"), "utf8")
                )

        @context.console_command(
            "start", input_type="lhystudios", help=_("Start Pipe to Controller")
        )
        def pipe_start(command, channel, _, data=None, **kwargs):
            spooler, driver, output = data
            output.update_state(STATE_ACTIVE)
            output.start()
            channel(_("Lhystudios Channel Started."))

        @context.console_command(
            "hold", input_type="lhystudios", help=_("Hold Controller")
        )
        def pipe_pause(command, channel, _, data=None, **kwargs):
            spooler, driver, output = data
            output.update_state(STATE_PAUSE)
            output.pause()
            channel("Lhystudios Channel Paused.")

        @context.console_command(
            "resume", input_type="lhystudios", help=_("Resume Controller")
        )
        def pipe_resume(command, channel, _, data=None, **kwargs):
            spooler, driver, output = data
            output.update_state(STATE_ACTIVE)
            output.start()
            channel(_("Lhystudios Channel Resumed."))

        @context.console_command(
            "usb_connect", input_type="lhystudios", help=_("Connects USB")
        )
        def usb_connect(command, channel, _, data=None, **kwargs):
            spooler, driver, output = data
            output.open()
            channel(_("CH341 Opened."))

        @context.console_command(
            "usb_disconnect", input_type="lhystudios", help=_("Disconnects USB")
        )
        def usb_disconnect(command, channel, _, data=None, **kwargs):
            spooler, driver, output = data
            output.close()
            channel(_("CH341 Closed."))

        @context.console_command(
            "usb_reset", input_type="lhystudios", help=_("Reset USB device")
        )
        def usb_reset(command, channel, _, data=None, **kwargs):
            spooler, driver, output = data
            output.usb_reset()

        @context.console_command(
            "usb_release", input_type="lhystudios", help=_("Release USB device")
        )
        def usb_release(command, channel, _, data=None, **kwargs):
            spooler, driver, output = data
            output.usb_release()

        @context.console_command(
            "usb_abort", input_type="lhystudios", help=_("Stops USB retries")
        )
        def usb_abort(command, channel, _, data=None, **kwargs):
            spooler, driver, output = data
            output.abort_retry()

        @context.console_command(
            "usb_continue", input_type="lhystudios", help=_("Continues USB retries")
        )
        def usb_continue(command, channel, _, data=None, **kwargs):
            spooler, driver, output = data
            output.continue_retry()

        @kernel.console_option(
            "port", "p", type=int, default=23, help=_("port to listen on.")
        )
        @kernel.console_option(
            "silent",
            "s",
            type=bool,
            action="store_true",
            help=_("do not watch server channels"),
        )
        @kernel.console_option(
            "watch", "w", type=bool, action="store_true", help=_("watch send/recv data")
        )
        @kernel.console_option(
            "quit",
            "q",
            type=bool,
            action="store_true",
            help=_("shutdown current lhyserver"),
        )
        @kernel.console_command("lhyserver", help=_("activate the lhyserver."))
        def lhyserver(
            channel, _, port=23, silent=False, watch=False, quit=False, **kwargs
        ):
            root = kernel.root
            try:
                spooler, input_driver, output = root.registered[
                    "device/%s" % root.active
                ]
                if output is None:
                    channel(
                        _(
                            "Output for device %s does not exist. Lhyserver cannot attach."
                        )
                        % root.active
                    )
                    return
                if output.type != "lhystudios":
                    channel(_("Lhyserver cannot attach to non-Lhystudios controllers."))
                    return
                server = root.open_as("module/TCPServer", "lhyserver", port=port)
                if quit:
                    root.close("lhyserver")
                    return
                channel(_("TCP Server for Lhystudios on port: %d" % port))
                if not silent:
                    console = kernel.channel("console")
                    server.events_channel.watch(console)
                    if watch:
                        server.data_channel.watch(console)
                channel(_("Watching Channel: %s") % "server")
                root.channel("lhyserver/recv").watch(output.write)
                channel(_("Attached: %s" % repr(output)))

            except OSError:
                channel(_("Server failed on port: %d") % port)
            except KeyError:
                channel(_("Server cannot be attached to any device."))
            return

        @kernel.console_command("lhyemulator", help=_("activate the lhyemulator."))
        def lhyemulator(channel, _, **kwargs):
            root = kernel.root
            name = root.active
            driver_context = kernel.get_context("lhystudios/driver/%s" % name)
            try:
                driver_context.open_as("emulator/lhystudios", "lhyemulator%s" % name)
                channel(_("Lhystudios Emulator attached to %s" % str(driver_context)))
            except KeyError:
                channel(_("Emulator cannot be attached to any device."))
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
    if v < 0:
        raise ValueError("Cannot permit negative values.")
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


class LhystudiosDriver(Driver):
    """
    LhystudiosDriver provides Lhystudios specific coding for elements and sends it to the backend
    to write to the usb.

    The interpret() ticks to process additional data.
    """

    def __init__(self, context, name, *args, **kwargs):
        context = context.get_context("lhystudios/driver/%s" % name)
        Driver.__init__(self, context=context, name=name)
        self._topward = False
        self._leftward = False
        self._x_engaged = False
        self._y_engaged = False
        self._horizontal_major = False

        self._request_leftward = None
        self._request_topward = None
        self._request_horizontal_major = None

        kernel = context._kernel
        _ = kernel.translation
        root_context = context.root
        root_context.setting(bool, "opt_rapid_between", True)
        root_context.setting(int, "opt_jog_mode", 0)
        root_context.setting(int, "opt_jog_minimum", 256)

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

        context.setting(bool, "autolock", True)

        context.setting(str, "board", "M2")
        context.setting(bool, "twitchfull", False)
        context.setting(bool, "nse_raster", False)
        context.setting(bool, "nse_stepraster", False)
        context.setting(bool, "fix_speeds", False)

        self.CODE_RIGHT = b"B"
        self.CODE_LEFT = b"T"
        self.CODE_TOP = b"L"
        self.CODE_BOTTOM = b"R"
        self.CODE_ANGLE = b"M"
        self.CODE_LASER_ON = b"D"
        self.CODE_LASER_OFF = b"U"
        self.update_codes()

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

        # Step amount expected of the current operation
        self.step = 0

        # Step amount is the current correctly set step amount in the controller.
        self.step_value_set = 0

        # Step index of the current step taken for unidirectional
        self.step_index = 0

        # Step total the count for fractional step amounts
        self.step_total = 0.0

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
        if self.plot is None:
            return False
        if self.hold():
            return True
        for x, y, on in self.plot:
            sx = self.current_x
            sy = self.current_y
            on = int(on)
            if on > 1:
                # Special Command.
                if on & PLOT_FINISH:  # Plot planner is ending.
                    self.ensure_rapid_mode()
                    break
                elif on & PLOT_SETTING:  # Plot planner settings have changed.
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
                elif on & PLOT_AXIS:  # Major Axis.
                    # 0 means X Major / Horizontal.
                    # 1 means Y Major / Vertical
                    self._request_horizontal_major = bool(x == 0)
                elif on & PLOT_DIRECTION:
                    # -1: Moving Left -x
                    # 1: Moving Right. +x
                    self._request_leftward = bool(x != 1)
                    # -1: Moving Bottom +y
                    # 1: Moving Top. -y
                    self._request_topward = bool(y != 1)
                elif on & (
                    PLOT_RAPID | PLOT_JOG
                ):  # Plot planner requests position change.
                    if on & PLOT_RAPID or self.state != DRIVER_STATE_PROGRAM:
                        # Perform a rapid position change. Always perform this for raster moves.
                        # DRIVER_STATE_RASTER should call this code as well.
                        self.ensure_rapid_mode()
                        self.move_absolute(x, y)
                    else:
                        # Jog is performable and requested. # We have not flagged our direction or state.
                        self.jog_absolute(x, y, mode=self.root_context.opt_jog_mode)
                continue
            dx = x - sx
            dy = y - sy
            step = self.settings.raster_step
            if step == 0:
                # vector mode
                self.ensure_program_mode()
            else:
                # program mode
                self.ensure_raster_mode()
                if self._horizontal_major:
                    # Horizontal Rastering.
                    if self.context.nse_raster or self.settings.raster_alt:
                        # Alt-Style Raster
                        if (dx > 0 and self._leftward) or (
                            dx < 0 and not self._leftward
                        ):
                            self.h_switch(dy)
                    else:
                        # Default Raster
                        if dy != 0:
                            self.h_switch_g(dy)
                else:
                    # Vertical Rastering.
                    if self.context.nse_raster or self.settings.raster_alt:
                        # Alt-Style Raster
                        if (dy > 0 and self._topward) or (dy < 0 and not self._topward):
                            self.v_switch(dx)
                    else:
                        # Default Raster
                        if dx != 0:
                            self.v_switch_g(dx)
                # Update dx, dy (if changed by switches)
                dx = x - self.current_x
                dy = y - self.current_y
            self.goto_octent(dx, dy, on & 1)
            if self.hold():
                return True
        self.plot = None
        return False

    def pause(self, *values):
        self.data_output(b"~PN!\n~")
        self.is_paused = True

    def resume(self, *values):
        self.data_output(b"~PN&\n~")
        self.is_paused = False

    def reset(self):
        Driver.reset(self)
        self.context.signal("pipe;buffer", 0)
        self.data_output(b"~I*\n~")
        self.reset_modes()
        self.state = DRIVER_STATE_RAPID
        self.context.signal("driver;mode", self.state)
        self.is_paused = False

    def send_blob(self, blob_type, data):
        if blob_type == "egv":
            self.data_output(data)

    def cut(self, x, y):
        self.goto(x, y, True)

    def jog(self, x, y, **kwargs):
        if self.is_relative:
            self.jog_relative(x, y, **kwargs)
        else:
            self.jog_absolute(x, y, **kwargs)

    def jog_absolute(self, x, y, **kwargs):
        self.jog_relative(x - self.current_x, y - self.current_y, **kwargs)

    def jog_relative(self, dx, dy, mode=0):
        self.laser_off()
        dx = int(round(dx))
        dy = int(round(dy))
        if mode == 0:
            self._nse_jog_event(dx, dy)
        elif mode == 1:
            self.mode_shift_on_the_fly(dx, dy)
        else:
            # Finish-out Jog
            self.ensure_rapid_mode()
            self.move_relative(dx, dy)
            self.ensure_program_mode()

    def _nse_jog_event(self, dx=0, dy=0):
        """
        NSE Jog events are performed from program or raster mode and skip out to rapid mode to perform
        a single jog command. This jog effect varies based on the horizontal vertical major setting and
        needs to counteract the jogged head according to those settings.

        NSE jogs will not change the underlying mode even though they temporarily switch into
        rapid mode. nse jogs are not done in raster mode.
        """
        dx = int(round(dx))
        dy = int(round(dy))
        original_state = self.state
        self.state = DRIVER_STATE_RAPID
        self.laser = False
        if self._horizontal_major:
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
        self.goto_xy(dx, dy)
        self.data_output(b"SE")
        self.data_output(self.code_declare_directions())
        self.state = original_state

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
        self.goto_relative(x - self.current_x, y - self.current_y, cut)

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
                # Rapid movement override. Should make programmed jogs.
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
                self.goto_xy(dx, dy)
                self.data_output(b"S1P\n")
                if not self.context.autolock:
                    self.data_output(b"IS2P\n")
        elif self.state == DRIVER_STATE_RASTER:
            # goto in raster, switches to program to recall this function.
            self.ensure_program_mode()
            self.goto_relative(dx, dy, cut)
            return
        elif self.state == DRIVER_STATE_PROGRAM:
            mx = 0
            my = 0
            line = list(grouped(ZinglPlotter.plot_line(0, 0, dx, dy)))
            for x, y in line:
                self.goto_octent(x - mx, y - my, cut)
                mx = x
                my = y
        elif self.state == DRIVER_STATE_FINISH:
            self.goto_xy(dx, dy)
            self.data_output(b"N")
        elif self.state == DRIVER_STATE_MODECHANGE:
            self.mode_shift_on_the_fly(dx, dy)
        self.context.signal(
            "driver;position",
            (self.current_x - dx, self.current_y - dy, self.current_x, self.current_y),
        )

    def set_speed(self, speed=None):
        if self.settings.speed != speed:
            self.settings.speed = speed
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def set_d_ratio(self, d_ratio=None):
        if self.settings.dratio != d_ratio:
            self.settings.dratio = d_ratio
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def set_acceleration(self, accel=None):
        if self.settings.acceleration != accel:
            self.settings.acceleration = accel
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def set_step(self, step=None):
        if self.settings.raster_step != step:
            self.settings.raster_step = step
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
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
        elif self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
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
        elif self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
            self.data_output(self.CODE_LASER_ON)
        elif self.state == DRIVER_STATE_FINISH:
            self.data_output(self.CODE_LASER_ON)
            self.data_output(b"N")
        self.laser = True
        return True

    def ensure_rapid_mode(self, *values):
        if self.state == DRIVER_STATE_RAPID:
            return
        if self.state == DRIVER_STATE_FINISH:
            self.data_output(b"S1P\n")
            if not self.context.autolock:
                self.data_output(b"IS2P\n")
        elif self.state in (
            DRIVER_STATE_PROGRAM,
            DRIVER_STATE_RASTER,
            DRIVER_STATE_MODECHANGE,
        ):
            self.data_output(b"FNSE-\n")
            self.laser = False
        self.state = DRIVER_STATE_RAPID
        self.context.signal("driver;mode", self.state)

    def mode_shift_on_the_fly(self, dx=0, dy=0):
        """
        Mode shift on the fly changes the current modes while in programmed or raster mode
        this exits with a @ command that resets the modes. A movement operation can be added after
        the speed code and before the return to into programmed or raster mode.

        This switch is often avoided because testing revealed some chance of a runaway during reset
        switching.

        If the raster step has been changed from zero this can result in shifting from program to raster mode
        """
        dx = int(round(dx))
        dy = int(round(dy))
        self.data_output(b"@NSE")
        self.laser = False
        self.state = DRIVER_STATE_RAPID
        self.ensure_program_mode(dx, dy)

    def ensure_finished_mode(self, *values):
        if self.state == DRIVER_STATE_FINISH:
            return
        if self.state in (
            DRIVER_STATE_PROGRAM,
            DRIVER_STATE_RASTER,
            DRIVER_STATE_MODECHANGE,
        ):
            self.data_output(b"@NSE")
            self.laser = False
        elif self.state == DRIVER_STATE_RAPID:
            self.data_output(b"I")
        self.state = DRIVER_STATE_FINISH
        self.context.signal("driver;mode", self.state)

    def ensure_raster_mode(self, *values):
        """
        Raster mode runs in either G0xx stepping mode or NSE stepping but is only intended to move horizontal or
        vertical rastering, usually at a high speed. Accel twitches are required for this mode.

        @param values:
        @return:
        """
        if self.state == DRIVER_STATE_RASTER:
            return
        self.ensure_finished_mode()
        self.ensure_program_mode()

    def ensure_program_mode(self, *values, dx=0, dy=0):
        """
        Vector Mode implies but doesn't discount rastering. Twitches are used if twitchfull is set to True.

        @param values: passed information from the driver command
        @param dx: change in dx that should be made while switching to program mode.
        @param dy: change in dy that should be made while switching to program mode.
        @return:
        """
        if self.state == DRIVER_STATE_PROGRAM:
            return
        self.ensure_finished_mode()

        instance_step = 0
        self.step_index = 0
        self.step = self.settings.raster_step
        self.step_value_set = 0
        if self.settings.raster_alt:
            pass
        elif self.context.nse_raster and not self.context.nse_stepraster:
            pass
        else:
            self.step_value_set = self.step
            instance_step = self.step_value_set

        suffix_c = None
        if (
            not self.context.twitchfull or self.settings.force_twitchless
        ) and not self.step:
            suffix_c = True
        if self._request_leftward is not None:
            self._leftward = self._request_leftward
            self._request_leftward = None
        if self._request_topward is not None:
            self._topward = self._request_topward
            self._request_topward = None
        if self._request_horizontal_major is not None:
            self._horizontal_major = self._request_horizontal_major
            self._request_horizontal_major = None
        if self.context.strict:
            # Override requested or current values only use core initial values.
            self._leftward = False
            self._topward = False
            self._horizontal_major = False

        speed_code = LaserSpeed(
            self.context.board,
            self.settings.speed,
            instance_step,
            d_ratio=self.settings.implicit_d_ratio,
            acceleration=self.settings.implicit_accel,
            fix_limit=True,
            fix_lows=True,
            suffix_c=suffix_c,
            fix_speeds=self.context.fix_speeds,
            raster_horizontal=self._horizontal_major,
        ).speedcode
        speed_code = bytes(speed_code, "utf8")
        self.data_output(speed_code)
        self.goto_xy(dx, dy)
        self.data_output(b"N")
        self.data_output(self.code_declare_directions())
        self.data_output(b"S1E")
        if self.step:
            self.state = DRIVER_STATE_RASTER
        else:
            self.state = DRIVER_STATE_PROGRAM
        self.context.signal("driver;mode", self.state)

    def h_switch(self, dy: float):
        """
        NSE h_switches replace the mere reversal of direction with N<v><distance>SE

        If a G-value is set we should subtract that from the step for our movement. Since triggering NSE will cause
        that step to occur.

        @param dy: The amount along the directional axis we should move during this step.

        @return:
        """
        set_step = self.step_value_set
        if isinstance(set_step, tuple):
            set_step = set_step[self.step_index % len(set_step)]

        # correct for fractional stepping
        self.step_total += dy
        delta = math.trunc(self.step_total)
        self.step_total -= delta

        step_amount = -set_step if self._topward else set_step
        delta = delta - step_amount

        # We force reenforce directional move.
        if self._leftward:
            self.data_output(self.CODE_LEFT)
        else:
            self.data_output(self.CODE_RIGHT)
        self.data_output(b"N")
        if delta != 0:
            if delta < 0:
                self.data_output(self.CODE_TOP)
                self._topward = True
            else:
                self.data_output(self.CODE_BOTTOM)
                self._topward = False
            self.data_output(lhymicro_distance(abs(delta)))
            self.current_y += delta
        self.data_output(b"SE")
        self.current_y += step_amount

        self._leftward = not self._leftward
        self._x_engaged = True
        self._y_engaged = False
        self.laser = False
        self.step_index += 1

    def v_switch(self, dx: float):
        """
        NSE v_switches replace the mere reversal of direction with N<h><distance>SE

        @param dx: The amount along the directional axis we should move during this step.

        @return:
        """
        set_step = self.step_value_set
        if isinstance(set_step, tuple):
            set_step = set_step[self.step_index % len(set_step)]

        # correct for fractional stepping
        self.step_total += dx
        delta = math.trunc(self.step_total)
        self.step_total -= delta

        step_amount = -set_step if self._leftward else set_step
        delta = delta - step_amount

        # We force reenforce directional move.
        if self._topward:
            self.data_output(self.CODE_TOP)
        else:
            self.data_output(self.CODE_BOTTOM)
        self.data_output(b"N")
        if delta != 0:
            if delta < 0:
                self.data_output(self.CODE_LEFT)
                self._leftward = True
            else:
                self.data_output(self.CODE_RIGHT)
                self._leftward = False
            self.data_output(lhymicro_distance(abs(delta)))
            self.current_x += delta
        self.data_output(b"SE")
        self.current_x += step_amount
        self._topward = not self._topward
        self._x_engaged = False
        self._y_engaged = True
        self.laser = False
        self.step_index += 1

    def h_switch_g(self, dy: float):
        """
        Horizontal switch with a Gvalue set. The board will automatically step according to the step_value_set.

        @return:
        """
        set_step = self.step_value_set
        if isinstance(set_step, tuple):
            set_step = set_step[self.step_index % len(set_step)]

        # correct for fractional stepping
        self.step_total += dy
        delta = math.trunc(self.step_total)
        self.step_total -= delta

        step_amount = -set_step if self._topward else set_step
        delta = delta - step_amount
        if delta != 0:
            # Movement exceeds the standard raster step amount. Rapid relocate.
            self.ensure_finished_mode()
            self.move_relative(0, delta)
            self._x_engaged = True
            self._y_engaged = False
            self.ensure_raster_mode()

        # We reverse direction and step.
        if self._leftward:
            self.data_output(self.CODE_RIGHT)
            self._leftward = False
        else:
            self.data_output(self.CODE_LEFT)
            self._leftward = True
        self.current_y += step_amount
        self.laser = False
        self.step_index += 1

    def v_switch_g(self, dx: float):
        """
        Vertical switch with a Gvalue set. The board will automatically step according to the step_value_set.

        @return:
        """
        set_step = self.step_value_set
        if isinstance(set_step, tuple):
            set_step = set_step[self.step_index % len(set_step)]

        # correct for fractional stepping
        self.step_total += dx
        delta = math.trunc(self.step_total)
        self.step_total -= delta

        step_amount = -set_step if self._leftward else set_step
        delta = delta - step_amount
        if delta != 0:
            # Movement exceeds the standard raster step amount. Rapid relocate.
            self.ensure_finished_mode()
            self.move_relative(delta, 0)
            self._y_engaged = True
            self._x_engaged = False
            self.ensure_raster_mode()

        # We reverse direction and step.
        if self._topward:
            self.data_output(self.CODE_BOTTOM)
            self._topward = False
        else:
            self.data_output(self.CODE_TOP)
            self._topward = True
        self.current_x += step_amount
        self.laser = False
        self.step_index += 1

    def calc_home_position(self):
        x = 0
        y = 0
        bed_dim = self.context.root
        bed_dim.setting(int, "bed_width", 310)
        bed_dim.setting(int, "bed_height", 210)
        if self.context.home_right:
            x = int(bed_dim.bed_width * MILS_IN_MM)
        if self.context.home_bottom:
            y = int(bed_dim.bed_height * MILS_IN_MM)
        return x, y

    def home(self, *values):
        x, y = self.calc_home_position()
        self.ensure_rapid_mode()
        self.data_output(b"IPP\n")
        old_x = self.current_x
        old_y = self.current_y
        self.current_x = x
        self.current_y = y
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
            self.current_x = x
            self.current_y = y

        self.context.signal("driver;mode", self.state)
        self.context.signal(
            "driver;position", (old_x, old_y, self.current_x, self.current_y)
        )

    def lock_rail(self):
        self.ensure_rapid_mode()
        self.data_output(b"IS1P\n")

    def unlock_rail(self, abort=False):
        self.ensure_rapid_mode()
        self.data_output(b"IS2P\n")

    def abort(self):
        self.data_output(b"I\n")

    def reset_modes(self):
        self.laser = False
        self._request_leftward = None
        self._request_topward = None
        self._request_horizontal_major = None
        self._topward = False
        self._leftward = False
        self._x_engaged = False
        self._y_engaged = False
        self._horizontal_major = False

    def goto_xy(self, dx, dy):
        rapid = self.state not in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER)
        if dx != 0:
            self.current_x += dx
            if dx > 0:  # Moving right
                if not self.is_right or rapid:
                    self.data_output(self.CODE_RIGHT)
                    self._leftward = False
            else:  # Moving left
                if not self.is_left or rapid:
                    self.data_output(self.CODE_LEFT)
                    self._leftward = True
            self._x_engaged = True
            self._y_engaged = False
            self.data_output(lhymicro_distance(abs(dx)))
        if dy != 0:
            self.current_y += dy
            if dy > 0:  # Moving bottom
                if not self.is_bottom or rapid:
                    self.data_output(self.CODE_BOTTOM)
                    self._topward = False
            else:  # Moving top
                if not self.is_top or rapid:
                    self.data_output(self.CODE_TOP)
                    self._topward = True
            self._x_engaged = False
            self._y_engaged = True
            self.data_output(lhymicro_distance(abs(dy)))

    def goto_octent(self, dx, dy, on):
        if dx == 0 and dy == 0:
            return
        if on:
            self.laser_on()
        else:
            self.laser_off()
        if abs(dx) == abs(dy):
            self._x_engaged = True  # Set both on
            self._y_engaged = True
            if dx > 0:  # Moving right
                if self._leftward:
                    self.data_output(self.CODE_RIGHT)
                    self._leftward = False
            else:  # Moving left
                if not self._leftward:
                    self.data_output(self.CODE_LEFT)
                    self._leftward = True
            if dy > 0:  # Moving bottom
                if self._topward:
                    self.data_output(self.CODE_BOTTOM)
                    self._topward = False
            else:  # Moving top
                if not self._topward:
                    self.data_output(self.CODE_TOP)
                    self._topward = True
            self.current_x += dx
            self.current_y += dy
            self.data_output(self.CODE_ANGLE)
            self.data_output(lhymicro_distance(abs(dy)))
        else:
            self.goto_xy(dx, dy)
        self.context.signal(
            "driver;position",
            (self.current_x - dx, self.current_y - dy, self.current_x, self.current_y),
        )

    def code_declare_directions(self):
        x_dir = self.CODE_LEFT if self._leftward else self.CODE_RIGHT
        y_dir = self.CODE_TOP if self._topward else self.CODE_BOTTOM
        if self._horizontal_major:
            self._x_engaged = True
            self._y_engaged = False
            return y_dir + x_dir
        else:
            self._x_engaged = False
            self._y_engaged = True
            return x_dir + y_dir

    @property
    def is_left(self):
        return self._x_engaged and not self._y_engaged and self._leftward

    @property
    def is_right(self):
        return self._x_engaged and not self._y_engaged and not self._leftward

    @property
    def is_top(self):
        return not self._x_engaged and self._y_engaged and self._topward

    @property
    def is_bottom(self):
        return not self._x_engaged and self._y_engaged and not self._topward

    @property
    def is_angle(self):
        return self._y_engaged and self._x_engaged

    @property
    def type(self):
        return "lhystudios"


class LhystudiosController:
    """
    K40 Controller controls the Lhystudios boards sending any queued data to the USB when the signal is not busy.

    Opening and closing of the pipe are dealt with internally. There are three primary monitor data channels.
    'send', 'recv' and 'usb'. They display the reading and writing of information to/from the USB and the USB connection
    log, providing information about the connecting and error status of the USB device.
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

        self.connection = None
        self.max_attempts = 5
        self.refuse_counts = 0
        self.connection_errors = 0
        self.count = 0
        self.aborted_retries = False
        self.pre_ok = False
        self.realtime = False

        self.abort_waiting = False
        self.pipe_channel = context.channel("%s/events" % name)
        self.usb_log = context.channel("%s/usb" % name, buffer_size=500)
        self.usb_send_channel = context.channel("%s/usb_send" % name)
        self.recv_channel = context.channel("%s/recv" % name)
        self.usb_log.watch(lambda e: context.signal("pipe;usb_status", e))

        self.ch341 = self.context.open("module/ch341", log=self.usb_log)

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
        self.context.root.listen("lifecycle;shutdown", self.finalize)

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
        self.context.root.unlisten("lifecycle;ready", self.on_controller_ready)
        self.start()

    def finalize(self, *args, **kwargs):
        if self._thread is not None:
            self.write(b"\x18\n")
        self.context.root.unlisten("lifecycle;shutdown", self.finalize)

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
            try:
                self.connection.open()
            except AttributeError:
                raise ConnectionRefusedError("Mock Driver cannot connect with USB")

        if self.connection is None:
            raise ConnectionRefusedError("ch341 connect did not return a connection.")

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
        f = bytes_to_write.find(b"~")
        if f != -1:
            # ~ was found in bytes. We are in a realtime exception.
            self.realtime = True

            # All code prior to ~ is sent to normal write.
            queue_bytes = bytes_to_write[:f]
            if queue_bytes:
                self.write(queue_bytes)

            # All code after ~ is sent to realtime write.
            preempt_bytes = bytes_to_write[f + 1 :]
            if preempt_bytes:
                self.realtime_write(preempt_bytes)
            return self
        if self.realtime:
            # We are in a realtime exception that has not been terminated.
            self.realtime_write(bytes_to_write)
            return self

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
        f = bytes_to_write.find(b"~")
        if f != -1:
            # ~ was found in bytes. We are leaving realtime exception.
            self.realtime = False

            # All date prior to the ~ is sent to realtime write.
            preempt_bytes = bytes_to_write[:f]
            if preempt_bytes:
                self.realtime_write(preempt_bytes)

            # All data after ~ is sent back to normal write.
            queue_bytes = bytes_to_write[f + 1 :]
            if queue_bytes:
                self.write(queue_bytes)
            return self
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
                self._thread_data_send,
                thread_name="LhyPipe(%s)" % self.context.path,
                result=self.stop,
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

    def stop(self, *args):
        self.abort()
        try:
            if self._thread is not None:
                self._thread.join()  # Wait until stop completes before continuing.
            self._thread = None
        except RuntimeError:
            pass  # Stop called by current thread.

    def abort_retry(self):
        self.aborted_retries = True
        self.context.signal("pipe;state", "STATE_FAILED_SUSPENDED")

    def continue_retry(self):
        self.aborted_retries = False
        self.context.signal("pipe;state", "STATE_FAILED_RETRYING")

    def usb_release(self):
        self.connection.release()

    def usb_reset(self):
        self.connection.reset()

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
        self.context.signal("pipe;packet", convert_to_list_bytes(packet))
        self.context.signal("pipe;packet_text", packet)
        if self.usb_send_channel:
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
            if self.state in (STATE_PAUSE, STATE_BUSY, STATE_SUSPEND):
                # If we are paused just keep sleeping until the state changes.
                if len(self._realtime_buffer) == 0 and len(self._preempt) == 0:
                    # Only pause if there are no realtime commands to queue.
                    self.context.signal("pipe;running", False)
                    time.sleep(0.25)
                    continue
            if self.aborted_retries:
                self.context.signal("pipe;running", False)
                time.sleep(0.25)
                continue
            try:
                # We try to process the queue.
                queue_processed = self.process_queue()
                if self.refuse_counts:
                    self.context.signal("pipe;failing", 0)
                self.refuse_counts = 0
                if self.is_shutdown:
                    break  # Sometimes it could reset this and escape.
            except ConnectionRefusedError:
                # The attempt refused the connection.
                self.refuse_counts += 1
                self.pre_ok = False
                if self.refuse_counts >= 5:
                    self.context.signal("pipe;state", "STATE_FAILED_RETRYING")
                self.context.signal("pipe;failing", self.refuse_counts)
                self.context.signal("pipe;running", False)
                time.sleep(3)  # 3 second sleep on failed connection attempt.
                continue
            except ConnectionError:
                # There was an error with the connection, close it and try again.
                self.connection_errors += 1
                self.pre_ok = False

                self.context.signal("pipe;running", False)
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
            self.context.signal("pipe;running", queue_processed)
        self._thread = None
        self.is_shutdown = False
        self.update_state(STATE_END)
        self.pre_ok = False
        self.context.signal("pipe;running", False)
        self._main_lock.release()

    def process_queue(self):
        """
        Attempts to process the buffer/queue
        Will fail on ConnectionRefusedError at open, 'process_queue_pause = True' (anytime before packet sent),
        self._buffer is empty, or a failure to produce packet.

        Buffer will not be changed unless packet is successfully sent, or pipe commands are processed.

        The following are meta commands for the controller
        - : require wait finish at the end of the queue processing.
        * : clear the buffers, and abort the thread.
        ! : pause.
        & : resume.
        % : fail checksum, do not resend
        ~ : begin/end realtime exception (Note, these characters would be consumed during
                the write process and should not exist in the queue)
        \x18 : quit.

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
        if packet.endswith((b"-", b"*", b"&", b"!", b"#", b"%", b"\x18")):
            packet += buffer[length : length + 1]
            length += 1
        post_send_command = None
        default_checksum = True

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
            elif packet.endswith(b"%"):  # alt-checksum
                default_checksum = False
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
            if default_checksum:
                packet = b"\x00" + packet + bytes([onewire_crc_lookup(packet)])
            else:
                packet = b"\x00" + packet + bytes([onewire_crc_lookup(packet) ^ 0xFF])
            self.connection.write(packet)
            self.pre_ok = False

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
                    if not default_checksum:
                        break
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
            del self._realtime_buffer[:length]
        else:
            del self._buffer[:length]
        if len(packet) != 0:
            # Packet was completed and sent. Only then update the channel.
            self.update_packet(packet)
        self.update_buffer()

        if post_send_command is not None:
            # Post send command could be wait_finished, and might have a broken pipe.
            try:
                post_send_command()
            except ConnectionError:
                # We should have already sent the packet. So this should be fine.
                pass
        return True  # A packet was prepped and sent correctly.

    def update_status(self):
        try:
            self._status = self.connection.get_status()
        except AttributeError:
            # self.connection was closed by something.
            raise ConnectionError
        if self.context is not None:
            try:
                self.context.signal(
                    "pipe;status",
                    self._status,
                    get_code_string_from_code(self._status[1]),
                )
            except IndexError:
                pass
            if self.recv_channel:
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
