import os
import re

from ...core.drivers import Driver
from ...kernel import Module
from ..basedevice import (
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

MILS_IN_MM = 39.3701

"""
GRBL device.
"""


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        _ = kernel.translation
        kernel.register("driver/grbl", GRBLDriver)
        kernel.register("emulator/grbl", GRBLEmulator)
        kernel.register("load/GCodeLoader", GCodeLoader)

        @kernel.console_option(
            "grbl", type=int, help=_("run grbl-emulator on given port.")
        )
        @kernel.console_option(
            "flip_x", "X", type=bool, action="store_true", help=_("grbl x-flip")
        )
        @kernel.console_option(
            "flip_y", "Y", type=bool, action="store_true", help=_("grbl y-flip")
        )
        @kernel.console_option(
            "adjust_x", "x", type=int, help=_("adjust grbl home_x position")
        )
        @kernel.console_option(
            "adjust_y", "y", type=int, help=_("adjust grbl home_y position")
        )
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
            help=_("shutdown current grblserver"),
        )
        @kernel.console_command("grblserver", help=_("activate the grblserver."))
        def grblserver(
            command,
            channel,
            _,
            port=23,
            path=None,
            flip_x=False,
            flip_y=False,
            adjust_x=0,
            adjust_y=0,
            silent=False,
            watch=False,
            quit=False,
            **kwargs,
        ):
            ctx = kernel.get_context(path if path is not None else "/")
            if ctx is None:
                return
            _ = kernel.translation
            try:
                server = ctx.open_as("module/TCPServer", "grbl", port=port)
                emulator = ctx.open("emulator/grbl")
                if quit:
                    ctx.close("grbl")
                    ctx.close("emulator/grbl")
                    return
                ctx.channel("grbl/send").greet = "Grbl 1.1e ['$' for help]\r\n"
                channel(_("GRBL Mode."))
                if not silent:
                    console = kernel.channel("console")
                    ctx.channel("grbl").watch(console)
                    server.events_channel.watch(console)
                    if watch:
                        server.events_channel.watch(console)

                emulator.flip_x = flip_x
                emulator.flip_y = flip_y
                emulator.home_adjust = (adjust_x, adjust_y)

                ctx.channel("grbl/recv").watch(emulator.write)
                channel(_("TCP Server for GRBL Emulator on port: %d" % port))
            except OSError:
                channel(_("Server failed on port: %d") % port)
            return


class GRBLDriver(Driver):
    def __init__(self, context, name):
        context = context.get_context("grbl/driver/%s" % name)
        Driver.__init__(self, context=context, name=name)
        self.context.setting(str, "line_end", "\n")
        self.plot = None
        self.scale = 1000.0  # g21 default.
        self.feed_convert = lambda s: s / (self.scale * 60.0)  # G94 default
        self.feed_invert = lambda s: s * (self.scale * 60.0)
        self.power_updated = True
        self.speed_updated = True

    def __repr__(self):
        return "GRBLDriver(%s)" % self.name

    def g20(self):
        self.scale = 1000.0  # g20 is inch mode. 1000 mils in an inch

    def g21(self):
        self.scale = MILS_IN_MM  # g21 is mm mode. 39.3701 mils in a mm

    def g93(self):
        # Feed Rate in Minutes / Unit
        self.feed_convert = lambda s: (self.scale * 60.0) / s
        self.feed_invert = lambda s: (self.scale * 60.0) / s

    def g94(self):
        # Feed Rate in Units / Minute
        self.feed_convert = lambda s: s / (self.scale * 60.0)
        self.feed_invert = lambda s: s * (self.scale * 60.0)

    def g90(self):
        self.set_absolute()

    def g91(self):
        self.set_incremental()

    def set_power(self, power=1000.0):
        Driver.set_power(self, power)
        self.power_updated = True

    def set_speed(self, speed=None):
        Driver.set_speed(self, speed)
        self.speed_updated = True

    def ensure_program_mode(self, *values):
        self.output.write("M3" + self.context.line_end)
        Driver.ensure_program_mode(self, *values)

    def ensure_finished_mode(self, *values):
        self.output.write("M5" + self.context.line_end)
        Driver.ensure_finished_mode(self, *values)

    def move(self, x, y):
        line = []
        if self.laser:
            line.append("G1")
        else:
            line.append("G0")
        line.append("X%f" % (x / self.scale))
        line.append("Y%f" % (y / self.scale))
        if self.power_updated:
            if self.settings.power is not None:
                line.append("S%f" % self.settings.power)
            self.power_updated = False
        if self.settings.speed is None:
            self.settings.speed = 20.0
        if self.speed_updated:
            line.append("F%d" % int(self.feed_convert(self.settings.speed)))
            self.speed_updated = False
        self.output.write(" ".join(line) + self.context.line_end)
        Driver.move(self, x, y)

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
                            p_set.speed != s_set.speed
                            or p_set.raster_step != s_set.raster_step
                        ):
                            self.set_speed(p_set.speed)
                            self.set_step(p_set.raster_step)
                            self.ensure_rapid_mode()
                        self.settings.set_values(p_set)
                    elif on & (
                        PLOT_RAPID | PLOT_JOG
                    ):  # Plot planner requests position change.
                        self.ensure_rapid_mode()
                    continue
                if on == 0:
                    self.laser_on()
                else:
                    self.laser_off()
                self.move(x, y)
            self.plot = None
        return False

    @property
    def type(self):
        return "grbl"


GRBL_SET_RE = re.compile(r"\$(\d+)=([-+]?[0-9]*\.?[0-9]*)")
CODE_RE = re.compile(r"([A-Za-z])")
FLOAT_RE = re.compile(r"[-+]?[0-9]*\.?[0-9]*")


def _tokenize_code(code_line):
    pos = code_line.find("(")
    while pos != -1:
        end = code_line.find(")")
        yield ["comment", code_line[pos + 1 : end]]
        code_line = code_line[:pos] + code_line[end + 1 :]
        pos = code_line.find("(")
    pos = code_line.find(";")
    if pos != -1:
        yield ["comment", code_line[pos + 1 :]]
        code_line = code_line[:pos]

    code = None
    for x in CODE_RE.split(code_line):
        x = x.strip()
        if len(x) == 0:
            continue
        if len(x) == 1 and x.isalpha():
            if code is not None:
                yield code
            code = [x.lower()]
            continue
        if code is not None:
            code.extend([float(v) for v in FLOAT_RE.findall(x) if len(v) != 0])
            yield code
        code = None
    if code is not None:
        yield code


def get_command_code(lines):
    home_adjust = None
    flip_x = 1  # Assumes the GCode is flip_x, -1 is flip, 1 is normal
    flip_y = 1  # Assumes the Gcode is flip_y,  -1 is flip, 1 is normal
    scale = MILS_IN_MM  # Initially assume mm mode 39.4 mils in an mm. G20 DEFAULT

    def g93_feed_convert(s):
        return (60.0 / s) * scale / MILS_IN_MM

    def g93_feed_invert(s):
        return (60.0 / s) * MILS_IN_MM / scale

    def g94_feed_convert(s):
        return s / ((scale / MILS_IN_MM) * 60.0)

    def g94_feed_invert(s):
        # units to mm, seconds to minutes.
        return s * ((scale / MILS_IN_MM) * 60.0)

    feed_convert, feed_invert = (
        g94_feed_convert,
        g94_feed_invert,
    )  # G94 DEFAULT, mm mode
    move_mode = 0
    home = None
    home2 = None
    on_mode = 1
    power = 0
    speed = 0
    used_speed = 0
    buffer = ""
    settings = {
        0: 10,  # step pulse microseconds
        1: 25,  # step idle delay
        2: 0,  # step pulse invert
        3: 0,  # step direction invert
        4: 0,  # invert step enable pin, boolean
        5: 0,  # invert limit pins, boolean
        6: 0,  # invert probe pin
        10: 255,  # status report options
        11: 0.010,  # Junction deviation, mm
        12: 0.002,  # arc tolerance, mm
        13: 0,  # Report in inches
        20: 0,  # Soft limits enabled.
        21: 0,  # hard limits enabled
        22: 0,  # Homing cycle enable
        23: 0,  # Homing direction invert
        24: 25.000,  # Homing locate feed rate, mm/min
        25: 500.000,  # Homing search seek rate, mm/min
        26: 250,  # Homing switch debounce delay, ms
        27: 1.000,  # Homing switch pull-off distance, mm
        30: 1000,  # Maximum spindle speed, RPM
        31: 0,  # Minimum spindle speed, RPM
        32: 1,  # Laser mode enable, boolean
        100: 250.000,  # X-axis steps per millimeter
        101: 250.000,  # Y-axis steps per millimeter
        102: 250.000,  # Z-axis steps per millimeter
        110: 500.000,  # X-axis max rate mm/min
        111: 500.000,  # Y-axis max rate mm/min
        112: 500.000,  # Z-axis max rate mm/min
        120: 10.000,  # X-axis acceleration, mm/s^2
        121: 10.000,  # Y-axis acceleration, mm/s^2
        122: 10.000,  # Z-axis acceleration, mm/s^2
        130: 200.000,  # X-axis max travel mm.
        131: 200.000,  # Y-axis max travel mm
        132: 200.000,  # Z-axis max travel mm.
    }

    for line in lines:
        gc = {}
        for c in _tokenize_code(line):
            g = c[0]
            if g not in gc:
                gc[g] = []
            if len(c) >= 2:
                gc[g].append(c[1])
            else:
                gc[g].append(None)
        if "m" in gc:
            for v in gc["m"]:
                if v == 0 or v == 1:
                    yield COMMAND_MODE_RAPID
                    yield COMMAND_WAIT_FINISH
                elif v == 2:
                    return 0
                elif v == 30:
                    return 0
                elif v == 3 or v == 4:
                    on_mode = True
                elif v == 5:
                    on_mode = False
                    yield COMMAND_LASER_OFF
                elif v == 7:
                    #  Coolant control.
                    pass
                elif v == 8:
                    yield COMMAND_SIGNAL, ("coolant", True)
                elif v == 9:
                    yield COMMAND_SIGNAL, ("coolant", False)
                elif v == 56:
                    pass  # Parking motion override control.
                elif v == 911:
                    pass  # Set TMC2130 holding currents
                elif v == 912:
                    pass  # M912: Set TMC2130 running currents
                else:
                    return 20
            del gc["m"]
        if "g" in gc:
            for v in gc["g"]:
                if v is None:
                    return 2
                elif v == 0.0:
                    move_mode = 0
                elif v == 1.0:
                    move_mode = 1
                elif v == 2.0:  # CW_ARC
                    move_mode = 2
                elif v == 3.0:  # CCW_ARC
                    move_mode = 3
                elif v == 4.0:  # DWELL
                    t = 0
                    if "p" in gc:
                        t = float(gc["p"].pop()) / 1000.0
                        if len(gc["p"]) == 0:
                            del gc["p"]
                    if "s" in gc:
                        t = float(gc["s"].pop())
                        if len(gc["s"]) == 0:
                            del gc["s"]
                    yield COMMAND_MODE_RAPID
                    yield COMMAND_WAIT, t
                elif v == 10.0:
                    if "l" in gc:
                        l = float(gc["l"].pop(0))
                        if len(gc["l"]) == 0:
                            del gc["l"]
                        if l == 2.0:
                            pass
                        elif l == 20:
                            pass
                elif v == 17:
                    pass  # Set XY coords.
                elif v == 18:
                    return 2  # Set the XZ plane for arc.
                elif v == 19:
                    return 2  # Set the YZ plane for arc.
                elif v == 20.0 or v == 70.0:
                    scale = 1000.0  # g20 is inch mode. 1000 mils in an inch
                elif v == 21.0 or v == 71.0:
                    scale = MILS_IN_MM  # g21 is mm mode. 39.3701 mils in a mm
                elif v == 28.0:
                    yield COMMAND_MODE_RAPID
                    yield COMMAND_HOME
                    if home_adjust is not None:
                        yield COMMAND_MOVE, home_adjust[0], home_adjust[1]
                    if home is not None:
                        yield COMMAND_MOVE, home
                elif v == 28.1:
                    if "x" in gc and "y" in gc:
                        x = gc["x"].pop(0)
                        if len(gc["x"]) == 0:
                            del gc["x"]
                        y = gc["y"].pop(0)
                        if len(gc["y"]) == 0:
                            del gc["y"]
                        if x is None:
                            x = 0
                        if y is None:
                            y = 0
                        home = (x, y)
                elif v == 28.2:
                    # Run homing cycle.
                    yield COMMAND_MODE_RAPID
                    yield COMMAND_HOME
                    if home_adjust is not None:
                        yield COMMAND_MOVE, home_adjust[0], home_adjust[1]
                elif v == 28.3:
                    yield COMMAND_MODE_RAPID
                    yield COMMAND_HOME
                    if home_adjust is not None:
                        yield COMMAND_MOVE, home_adjust[0], home_adjust[1]
                    if "x" in gc:
                        x = gc["x"].pop(0)
                        if len(gc["x"]) == 0:
                            del gc["x"]
                        if x is None:
                            x = 0
                        yield COMMAND_MOVE, x, 0
                    if "y" in gc:
                        y = gc["y"].pop(0)
                        if len(gc["y"]) == 0:
                            del gc["y"]
                        if y is None:
                            y = 0
                        yield COMMAND_MOVE, 0, y
                elif v == 30.0:
                    # Goto predefined position. Return to secondary home position.
                    if "p" in gc:
                        p = float(gc["p"].pop(0))
                        if len(gc["p"]) == 0:
                            del gc["p"]
                    else:
                        p = None
                    yield COMMAND_MODE_RAPID
                    yield COMMAND_HOME
                    if home_adjust is not None:
                        yield COMMAND_MOVE, home_adjust[0], home_adjust[1]
                    if home2 is not None:
                        yield COMMAND_MOVE, home2
                elif v == 30.1:
                    # Stores the current absolute position.
                    if "x" in gc and "y" in gc:
                        x = gc["x"].pop(0)
                        if len(gc["x"]) == 0:
                            del gc["x"]
                        y = gc["y"].pop(0)
                        if len(gc["y"]) == 0:
                            del gc["y"]
                        if x is None:
                            x = 0
                        if y is None:
                            y = 0
                        home2 = (x, y)
                elif v == 38.1:
                    # Touch Plate
                    pass
                elif v == 38.2:
                    # Straight Probe
                    pass
                elif v == 38.3:
                    # Prope towards workpiece
                    pass
                elif v == 38.4:
                    # Probe away from workpiece, signal error
                    pass
                elif v == 38.5:
                    # Probe away from workpiece.
                    pass
                elif v == 40.0:
                    pass  # Compensation Off
                elif v == 43.1:
                    pass  # Dynamic tool Length offsets
                elif v == 49:
                    # Cancel tool offset.
                    pass  # Dynamic tool length offsets
                elif v == 53:
                    pass  # Move in Absolute Coordinates
                elif 54 <= v <= 59:
                    # Fixture offset 1-6, G10 and G92
                    system = v - 54
                    pass  # Work Coordinate Systems
                elif v == 61:
                    # Exact path control mode. GRBL required
                    pass
                elif v == 80:
                    # Motion mode cancel. Canned cycle.
                    pass
                elif v == 90.0:
                    yield COMMAND_SET_ABSOLUTE
                elif v == 91.0:
                    yield COMMAND_SET_INCREMENTAL
                elif v == 91.1:
                    # Offset mode for certain cam. Incremental distance mode for arcs.
                    pass  # ARC IJK Distance Modes # TODO Implement
                elif v == 92:
                    # Change the current coords without moving.
                    pass  # Coordinate Offset TODO: Implement
                elif v == 92.1:
                    # Clear Coordinate offset set by 92.
                    pass  # Clear Coordinate offset TODO: Implement
                elif v == 93.0:
                    feed_convert, feed_invert = g93_feed_convert, g93_feed_invert
                elif v == 94.0:
                    feed_convert, feed_invert = g94_feed_convert, g94_feed_invert
                else:
                    return 20  # Unsupported or invalid g-code command found in block.
            del gc["g"]
        if "comment" in gc:
            del gc["comment"]
        if "f" in gc:  # Feed_rate
            for v in gc["f"]:
                if v is None:
                    return 2  # Numeric value format is not valid or missing an expected value.
                feed_rate = feed_convert(v)
                if speed != feed_rate:
                    speed = feed_rate
            del gc["f"]
        if "s" in gc:
            for v in gc["s"]:
                if v is None:
                    return 2  # Numeric value format is not valid or missing an expected value.
                if 0.0 < v <= 1.0:
                    v *= 1000  # numbers between 0-1 are taken to be in range 0-1.
                power = v
                yield COMMAND_SET_POWER, v

            del gc["s"]
        if "x" in gc or "y" in gc:
            if "x" in gc:
                x = gc["x"].pop(0)
                if x is None:
                    x = 0
                else:
                    x *= scale * flip_x
                if len(gc["x"]) == 0:
                    del gc["x"]
            else:
                x = 0
            if "y" in gc:
                y = gc["y"].pop(0)
                if y is None:
                    y = 0
                else:
                    y *= scale * flip_y
                if len(gc["y"]) == 0:
                    del gc["y"]
            else:
                y = 0
            if move_mode == 0:
                yield COMMAND_MODE_PROGRAM
                yield COMMAND_MOVE, x, y
            elif move_mode >= 1:
                yield COMMAND_MODE_PROGRAM
                if power == 0:
                    yield COMMAND_MOVE, x, y
                else:
                    if used_speed != speed:
                        yield COMMAND_SET_SPEED, speed
                        used_speed = speed
                    yield COMMAND_CUT, x, y
                # TODO: Implement CW_ARC
                # TODO: Implement CCW_ARC


class GRBLEmulator(Module):
    def __init__(self, context, path):
        Module.__init__(self, context, path)
        self.cutcode = None

        self.spooler, self.input_driver, self.output = context.registered[
            "device/%s" % context.root.active
        ]

        self.home_adjust = None
        self.flip_x = 1  # Assumes the GCode is flip_x, -1 is flip, 1 is normal
        self.flip_y = 1  # Assumes the Gcode is flip_y,  -1 is flip, 1 is normal
        self.scale = (
            MILS_IN_MM  # Initially assume mm mode 39.4 mils in an mm. G20 DEFAULT
        )
        self.feed_convert = None
        self.feed_invert = None
        self.g94_feedrate()  # G94 DEFAULT, mm mode
        self.move_mode = 0
        self.home = None
        self.home2 = None
        self.on_mode = 1
        self.power = 0
        self.speed = 0
        self.used_speed = 0
        self.buffer = ""
        self.settings = {
            0: 10,  # step pulse microseconds
            1: 25,  # step idle delay
            2: 0,  # step pulse invert
            3: 0,  # step direction invert
            4: 0,  # invert step enable pin, boolean
            5: 0,  # invert limit pins, boolean
            6: 0,  # invert probe pin
            10: 255,  # status report options
            11: 0.010,  # Junction deviation, mm
            12: 0.002,  # arc tolerance, mm
            13: 0,  # Report in inches
            20: 0,  # Soft limits enabled.
            21: 0,  # hard limits enabled
            22: 0,  # Homing cycle enable
            23: 0,  # Homing direction invert
            24: 25.000,  # Homing locate feed rate, mm/min
            25: 500.000,  # Homing search seek rate, mm/min
            26: 250,  # Homing switch debounce delay, ms
            27: 1.000,  # Homing switch pull-off distance, mm
            30: 1000,  # Maximum spindle speed, RPM
            31: 0,  # Minimum spindle speed, RPM
            32: 1,  # Laser mode enable, boolean
            100: 250.000,  # X-axis steps per millimeter
            101: 250.000,  # Y-axis steps per millimeter
            102: 250.000,  # Z-axis steps per millimeter
            110: 500.000,  # X-axis max rate mm/min
            111: 500.000,  # Y-axis max rate mm/min
            112: 500.000,  # Z-axis max rate mm/min
            120: 10.000,  # X-axis acceleration, mm/s^2
            121: 10.000,  # Y-axis acceleration, mm/s^2
            122: 10.000,  # Z-axis acceleration, mm/s^2
            130: 200.000,  # X-axis max travel mm.
            131: 200.000,  # Y-axis max travel mm
            132: 200.000,  # Z-axis max travel mm.
        }
        self.grbl_channel = None
        self.reply = None
        self.channel = None
        self.elements = None

    def initialize(self, *args, **kwargs):
        self.grbl_channel = self.context.channel("grbl")

    def close(self):
        pass

    def open(self):
        pass

    def grbl_write(self, data):
        if self.grbl_channel is not None:
            self.grbl_channel(data)
        if self.reply is not None:
            self.reply(data)

    def realtime_write(self, bytes_to_write):
        driver = self.input_driver
        if bytes_to_write == "?":  # Status report
            # Idle, Run, Hold, Jog, Alarm, Door, Check, Home, Sleep
            if driver.state == 0:
                state = "Idle"
            else:
                state = "Busy"
            x = driver.current_x / self.scale
            y = driver.current_y / self.scale
            z = 0.0
            parts = list()
            parts.append(state)
            parts.append("MPos:%f,%f,%f" % (x, y, z))
            f = self.feed_invert(driver.settings.speed)
            s = driver.settings.power
            parts.append("FS:%f,%d" % (f, s))
            self.grbl_write("<%s>\r\n" % "|".join(parts))
        elif bytes_to_write == "~":  # Resume.
            driver.realtime_command(REALTIME_RESUME)
        elif bytes_to_write == "!":  # Pause.
            driver.realtime_command(REALTIME_PAUSE)
        elif bytes_to_write == "\x18":  # Soft reset.
            driver.realtime_command(REALTIME_RESET)

    def write(self, data, reply=None, channel=None, elements=None):
        self.reply = reply
        self.channel = channel
        self.elements = elements
        if isinstance(data, bytes):
            data = data.decode()
        if "?" in data:
            data = data.replace("?", "")
            self.realtime_write("?")
        if "~" in data:
            data = data.replace("$", "")
            self.realtime_write("~")
        if "!" in data:
            data = data.replace("!", "")
            self.realtime_write("!")
        if "\x18" in data:
            data = data.replace("\x18", "")
            self.realtime_write("\x18")
        self.buffer += data
        while "\b" in self.buffer:
            self.buffer = re.sub(".\b", "", self.buffer, count=1)
            if self.buffer.startswith("\b"):
                self.buffer = re.sub("\b+", "", self.buffer)

        while "\n" in self.buffer:
            pos = self.buffer.find("\n")
            command = self.buffer[0:pos].strip("\r")
            self.buffer = self.buffer[pos + 1 :]
            cmd = self.commandline(command)
            if cmd == 0:  # Execute GCode.
                self.grbl_write("ok\r\n")
            else:
                self.grbl_write("error:%d\r\n" % cmd)

    def commandline(self, data):
        if data.startswith("$"):
            if data == "$":
                self.grbl_write(
                    "[HLP:$$ $# $G $I $N $x=val $Nx=line $J=line $SLP $C $X $H ~ ! ? ctrl-x]\r\n"
                )
                return 0
            elif data == "$$":
                for s in self.settings:
                    v = self.settings[s]
                    if isinstance(v, int):
                        self.grbl_write("$%d=%d\r\n" % (s, v))
                    elif isinstance(v, float):
                        self.grbl_write("$%d=%.3f\r\n" % (s, v))
                return 0
            if GRBL_SET_RE.match(data):
                settings = list(GRBL_SET_RE.findall(data))[0]
                print(settings)
                try:
                    c = self.settings[int(settings[0])]
                except KeyError:
                    return 3
                if isinstance(c, float):
                    self.settings[int(settings[0])] = float(settings[1])
                else:
                    self.settings[int(settings[0])] = int(settings[1])
                return 0
            elif data == "$I":
                pass
            elif data == "$G":
                pass
            elif data == "$N":
                pass
            elif data == "$H":
                self.spooler.job(COMMAND_HOME)
                if self.home_adjust is not None:
                    self.spooler.job(COMMAND_MODE_RAPID)
                    self.spooler.job(
                        COMMAND_MOVE, self.home_adjust[0], self.home_adjust[1]
                    )
                return 0
                # return 5  # Homing cycle not enabled by settings.
            return 3  # GRBL '$' system command was not recognized or supported.
        if data.startswith("cat"):
            return 2
        commands = {}
        for c in _tokenize_code(data):
            g = c[0]
            if g not in commands:
                commands[g] = []
            if len(c) >= 2:
                commands[g].append(c[1])
            else:
                commands[g].append(None)
        return self.command(commands)

    def command(self, gc):
        if "m" in gc:
            for v in gc["m"]:
                if v == 0 or v == 1:
                    self.spooler.job(COMMAND_MODE_RAPID)
                    self.spooler.job(COMMAND_WAIT_FINISH)
                elif v == 2:
                    return 0
                elif v == 30:
                    return 0
                elif v == 3 or v == 4:
                    self.on_mode = True
                elif v == 5:
                    self.on_mode = False
                    self.spooler.job(COMMAND_LASER_OFF)
                elif v == 7:
                    #  Coolant control.
                    pass
                elif v == 8:
                    self.spooler.job(COMMAND_SIGNAL, ("coolant", True))
                elif v == 9:
                    self.spooler.job(COMMAND_SIGNAL, ("coolant", False))
                elif v == 56:
                    pass  # Parking motion override control.
                elif v == 911:
                    pass  # Set TMC2130 holding currents
                elif v == 912:
                    pass  # M912: Set TMC2130 running currents
                else:
                    return 20
            del gc["m"]
        if "g" in gc:
            for v in gc["g"]:
                if v is None:
                    return 2
                elif v == 0.0:
                    self.move_mode = 0
                elif v == 1.0:
                    self.move_mode = 1
                elif v == 2.0:  # CW_ARC
                    self.move_mode = 2
                elif v == 3.0:  # CCW_ARC
                    self.move_mode = 3
                elif v == 4.0:  # DWELL
                    t = 0
                    if "p" in gc:
                        t = float(gc["p"].pop()) / 1000.0
                        if len(gc["p"]) == 0:
                            del gc["p"]
                    if "s" in gc:
                        t = float(gc["s"].pop())
                        if len(gc["s"]) == 0:
                            del gc["s"]
                    self.spooler.job(COMMAND_MODE_RAPID)
                    self.spooler.job(COMMAND_WAIT, t)
                elif v == 10.0:
                    if "l" in gc:
                        l = float(gc["l"].pop(0))
                        if len(gc["l"]) == 0:
                            del gc["l"]
                        if l == 2.0:
                            pass
                        elif l == 20:
                            pass
                elif v == 17:
                    pass  # Set XY coords.
                elif v == 18:
                    return 2  # Set the XZ plane for arc.
                elif v == 19:
                    return 2  # Set the YZ plane for arc.
                elif v == 20.0 or v == 70.0:
                    self.scale = 1000.0  # g20 is inch mode. 1000 mils in an inch
                elif v == 21.0 or v == 71.0:
                    self.scale = MILS_IN_MM  # g21 is mm mode. 39.3701 mils in a mm
                elif v == 28.0:
                    self.spooler.job(COMMAND_MODE_RAPID)
                    self.spooler.job(COMMAND_HOME)
                    if self.home_adjust is not None:
                        self.spooler.job(
                            COMMAND_MOVE, self.home_adjust[0], self.home_adjust[1]
                        )
                    if self.home is not None:
                        self.spooler.job(COMMAND_MOVE, self.home)
                elif v == 28.1:
                    if "x" in gc and "y" in gc:
                        x = gc["x"].pop(0)
                        if len(gc["x"]) == 0:
                            del gc["x"]
                        y = gc["y"].pop(0)
                        if len(gc["y"]) == 0:
                            del gc["y"]
                        if x is None:
                            x = 0
                        if y is None:
                            y = 0
                        self.home = (x, y)
                elif v == 28.2:
                    # Run homing cycle.
                    self.spooler.job(COMMAND_MODE_RAPID)
                    self.spooler.job(COMMAND_HOME)
                    if self.home_adjust is not None:
                        self.spooler.job(
                            COMMAND_MOVE, self.home_adjust[0], self.home_adjust[1]
                        )
                elif v == 28.3:
                    self.spooler.job(COMMAND_MODE_RAPID)
                    self.spooler.job(COMMAND_HOME)
                    if self.home_adjust is not None:
                        self.spooler.job(
                            COMMAND_MOVE, self.home_adjust[0], self.home_adjust[1]
                        )
                    if "x" in gc:
                        x = gc["x"].pop(0)
                        if len(gc["x"]) == 0:
                            del gc["x"]
                        if x is None:
                            x = 0
                        self.spooler.job(COMMAND_MOVE, x, 0)
                    if "y" in gc:
                        y = gc["y"].pop(0)
                        if len(gc["y"]) == 0:
                            del gc["y"]
                        if y is None:
                            y = 0
                        self.spooler.job(COMMAND_MOVE, 0, y)
                elif v == 30.0:
                    # Goto predefined position. Return to secondary home position.
                    if "p" in gc:
                        p = float(gc["p"].pop(0))
                        if len(gc["p"]) == 0:
                            del gc["p"]
                    else:
                        p = None
                    self.spooler.job(COMMAND_MODE_RAPID)
                    self.spooler.job(COMMAND_HOME)
                    if self.home_adjust is not None:
                        self.spooler.job(
                            COMMAND_MOVE, self.home_adjust[0], self.home_adjust[1]
                        )
                    if self.home2 is not None:
                        self.spooler.job(COMMAND_MOVE, self.home2)
                elif v == 30.1:
                    # Stores the current absolute position.
                    if "x" in gc and "y" in gc:
                        x = gc["x"].pop(0)
                        if len(gc["x"]) == 0:
                            del gc["x"]
                        y = gc["y"].pop(0)
                        if len(gc["y"]) == 0:
                            del gc["y"]
                        if x is None:
                            x = 0
                        if y is None:
                            y = 0
                        self.home2 = (x, y)
                elif v == 38.1:
                    # Touch Plate
                    pass
                elif v == 38.2:
                    # Straight Probe
                    pass
                elif v == 38.3:
                    # Prope towards workpiece
                    pass
                elif v == 38.4:
                    # Probe away from workpiece, signal error
                    pass
                elif v == 38.5:
                    # Probe away from workpiece.
                    pass
                elif v == 40.0:
                    pass  # Compensation Off
                elif v == 43.1:
                    pass  # Dynamic tool Length offsets
                elif v == 49:
                    # Cancel tool offset.
                    pass  # Dynamic tool length offsets
                elif v == 53:
                    pass  # Move in Absolute Coordinates
                elif 54 <= v <= 59:
                    # Fixture offset 1-6, G10 and G92
                    system = v - 54
                    pass  # Work Coordinate Systems
                elif v == 61:
                    # Exact path control mode. GRBL required
                    pass
                elif v == 80:
                    # Motion mode cancel. Canned cycle.
                    pass
                elif v == 90.0:
                    self.spooler.job(COMMAND_SET_ABSOLUTE)
                elif v == 91.0:
                    self.spooler.job(COMMAND_SET_INCREMENTAL)
                elif v == 91.1:
                    # Offset mode for certain cam. Incremental distance mode for arcs.
                    pass  # ARC IJK Distance Modes # TODO Implement
                elif v == 92:
                    # Change the current coords without moving.
                    pass  # Coordinate Offset TODO: Implement
                elif v == 92.1:
                    # Clear Coordinate offset set by 92.
                    pass  # Clear Coordinate offset TODO: Implement
                elif v == 93.0:
                    self.g93_feedrate()
                elif v == 94.0:
                    self.g94_feedrate()
                else:
                    return 20  # Unsupported or invalid g-code command found in block.
            del gc["g"]
        if "comment" in gc:
            del gc["comment"]
        if "f" in gc:  # Feed_rate
            for v in gc["f"]:
                if v is None:
                    return 2  # Numeric value format is not valid or missing an expected value.
                feed_rate = self.feed_convert(v)
                if self.speed != feed_rate:
                    self.speed = feed_rate
            del gc["f"]
        if "s" in gc:
            for v in gc["s"]:
                if v is None:
                    return 2  # Numeric value format is not valid or missing an expected value.
                if 0.0 < v <= 1.0:
                    v *= 1000  # numbers between 0-1 are taken to be in range 0-1.
                self.power = v
                self.spooler.job(COMMAND_SET_POWER, v)

            del gc["s"]
        if "x" in gc or "y" in gc:
            if "x" in gc:
                x = gc["x"].pop(0)
                if x is None:
                    x = 0
                else:
                    x *= self.scale * self.flip_x
                if len(gc["x"]) == 0:
                    del gc["x"]
            else:
                x = 0
            if "y" in gc:
                y = gc["y"].pop(0)
                if y is None:
                    y = 0
                else:
                    y *= self.scale * self.flip_y
                if len(gc["y"]) == 0:
                    del gc["y"]
            else:
                y = 0
            if self.move_mode == 0:
                self.spooler.job(COMMAND_MODE_PROGRAM)
                self.spooler.job(COMMAND_MOVE, x, y)
            elif self.move_mode >= 1:
                self.spooler.job(COMMAND_MODE_PROGRAM)
                if self.power == 0:
                    self.spooler.job(COMMAND_MOVE, x, y)
                else:
                    if self.used_speed != self.speed:
                        self.spooler.job(COMMAND_SET_SPEED, self.speed)
                        self.used_speed = self.speed
                    self.spooler.job(COMMAND_CUT, x, y)
                # TODO: Implement CW_ARC
                # TODO: Implement CCW_ARC
        return 0

    def g93_feedrate(self):
        # Feed Rate in Minutes / Unit
        self.feed_convert = lambda s: (60.0 / s) * self.scale / MILS_IN_MM
        self.feed_invert = lambda s: (60.0 / s) * MILS_IN_MM / self.scale

    def g94_feedrate(self):
        # Feed Rate in Units / Minute
        self.feed_convert = lambda s: s / ((self.scale / MILS_IN_MM) * 60.0)
        self.feed_invert = lambda s: s * ((self.scale / MILS_IN_MM) * 60.0)
        # units to mm, seconds to minutes.

    @property
    def type(self):
        return "grbl"


class GcodeBlob(list):
    def __init__(self, cmds, name=None):
        super().__init__(cmds)
        self.name = name

    def __repr__(self):
        return "Gcode(%s, %d lines)" % (self.name, len(self))

    def as_svg(self):
        pass


class GCodeLoader:
    @staticmethod
    def load_types():
        yield "Gcode File", ("gcode", "nc", "gc"), "application/x-gcode"

    @staticmethod
    def load(kernel, elements_modifier, pathname, **kwargs):
        basename = os.path.basename(pathname)
        with open(pathname, "r") as f:
            grblemulator = kernel.root.open_as("emulator/grbl", basename)
            grblemulator.elements = elements_modifier
            commandcode = GcodeBlob(get_command_code(f.readlines()), name=basename)
            elements_modifier.op_branch.add(commandcode, type="lasercode")
            kernel.root.close(basename)
        return True
