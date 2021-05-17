import os
import re

from ...core.drivers import Driver
from ...kernel import Module
from ..basedevice import DRIVER_STATE_PROGRAM
from ..lasercommandconstants import *

MILS_PER_MM = 39.3701

"""
GRBL device is a stub device. Serving as a placeholder.
"""


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("driver/grbl", GRBLDriver)
        kernel.register("emulator/grbl", GRBLEmulator)
        kernel.register("load/GCodeLoader", GCodeLoader)

        @kernel.console_option(
            "grbl", type=int, help="run grbl-emulator on given port."
        )
        @kernel.console_option(
            "flip_x", type=bool, action="store_true", help="grbl x-flip"
        )
        @kernel.console_option(
            "flip_y", type=bool, action="store_true", help="grbl y-flip"
        )
        @kernel.console_option("adjust_x", type=int, help="adjust grbl home_x position")
        @kernel.console_option("adjust_y", type=int, help="adjust grbl home_y position")
        @kernel.console_option(
            "path", "p", type=str, default="/", help="Path of variables to set."
        )
        @kernel.console_command("grblserver", help="activate the grblserver.")
        def grblserver(command, channel, _, path=None, args=tuple(), **kwargs):
            path_context = kernel.get_context(path if path is not None else "/")
            if path_context is None:
                return
            _ = kernel.translation
            port = 23
            try:
                path_context.open_as("module/TCPServer", "grbl", port=port)
                path_context.channel("grbl/send").greet = "Grbl 1.1e ['$' for help]\r\n"
                channel(_("GRBL Mode."))
                chan = "grbl"
                path_context.channel(chan).watch(kernel.channel("console"))
                channel(_("Watching Channel: %s") % chan)
                chan = "server"
                path_context.channel(chan).watch(kernel.channel("console"))
                channel(_("Watching Channel: %s") % chan)
                emulator = path_context.open("emulator/grbl")
                path_context.channel("grbl/recv").watch(emulator.write)
            except OSError:
                channel(_("Server failed on port: %d") % port)
            return


# class GrblDevice:
#     """"""
#
#     def __init__(self, root, uid=""):
#         self.uid = uid
#         self.device_name = "GRBL"
#         self.location_name = "Print"
#
#         # Device specific stuff. Fold into proper kernel commands or delegate to subclass.
#         self._device_log = ""
#         self.current_x = 0
#         self.current_y = 0
#
#         self.hold_condition = lambda e: False
#         self.pipe = None
#         self.interpreter = None
#         self.spooler = None
#
#     def __repr__(self):
#         return "GrblDevice(uid='%s')" % str(self.uid)
#
#     def initialize(self, device, channel=None):
#         """
#         Device initialize.
#
#         :param device:
#         :param name:
#         :return:
#         """
#         self.write = print
#         device.activate("modifier/GRBLDriver")
#
#     def __len__(self):
#         return 0


class GRBLDriver(Driver):
    def __init__(self, pipe):
        Driver.__init__(self, pipe=pipe)
        self.plot = None
        self.speed = 20.0
        self.scale = 1000.0  # g21 default.
        self.feed_convert = lambda s: s / (self.scale * 60.0)  # G94 default
        self.feed_invert = lambda s: s * (self.scale * 60.0)
        self.power_updated = True
        self.speed_updated = True
        self.group_modulation = False

    def g20(self):
        self.scale = 1000.0  # g20 is inch mode. 1000 mils in an inch

    def g21(self):
        self.scale = 39.3701  # g21 is mm mode. 39.3701 mils in a mm

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

    def initialize(self, channel=None):
        self.context.setting(str, "line_end", "\n")

    def ensure_program_mode(self, *values):
        self.pipe.write("M3" + self.context.line_end)
        Driver.ensure_program_mode(self, *values)

    def ensure_finished_mode(self, *values):
        self.pipe.write("M5" + self.context.line_end)
        Driver.ensure_finished_mode(self, *values)

    def plot_path(self, path):
        pass

    def plot_raster(self, raster):
        pass

    def move(self, x, y):
        line = []
        if self.state == DRIVER_STATE_PROGRAM:
            line.append("G1")
        else:
            line.append("G0")
        line.append("X%f" % (x / self.scale))
        line.append("Y%f" % (y / self.scale))
        if self.power_updated:
            line.append("S%f" % self.power)
            self.power_updated = False
        if self.speed_updated:
            line.append("F%d" % int(self.feed_convert(self.speed)))
            self.speed_updated = False
        self.pipe.write(" ".join(line) + self.context.line_end)
        Driver.move(self, x, y)

    def execute_deprecated(self):
        if self.hold():
            return
        while self.plot is not None:
            if self.hold():
                return
            try:
                x, y, on = next(self.plot)
                if on == 0:
                    self.laser_on()
                else:
                    self.laser_off()
                self.move(x, y)
            except StopIteration:
                self.plot = None
                return
            except RuntimeError:
                self.plot = None
                return
        Driver._process_spooled_item(self)

    @property
    def type(self):
        return "grbl"


class GRBLEmulator(Module):
    def __init__(self, context, path):
        Module.__init__(self, context, path)
        self.home_adjust = None
        self.flip_x = 1  # Assumes the GCode is flip_x, -1 is flip, 1 is normal
        self.flip_y = 1  # Assumes the Gcode is flip_y,  -1 is flip, 1 is normal
        self.scale = (
            MILS_PER_MM  # Initially assume mm mode 39.4 mils in an mm. G20 DEFAULT
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
        self.grbl_set_re = re.compile(r"\$(\d+)=([-+]?[0-9]*\.?[0-9]*)")
        self.code_re = re.compile(r"([A-Za-z])")
        self.float_re = re.compile(r"[-+]?[0-9]*\.?[0-9]*")
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
        driver = self.context.driver
        if bytes_to_write == "?":  # Status report
            # Idle, Run, Hold, Jog, Alarm, Door, Check, Home, Sleep
            if driver.state == 0:
                state = "Idle"
            else:
                state = "Busy"
            x = self.context.current_x / self.scale
            y = self.context.current_y / self.scale
            z = 0.0
            parts = list()
            parts.append(state)
            parts.append("MPos:%f,%f,%f" % (x, y, z))
            f = self.feed_invert(self.context.driver.speed)
            s = self.context.driver.power
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

    def _tokenize_code(self, code_line):
        code = None
        for x in self.code_re.split(code_line):
            x = x.strip()
            if len(x) == 0:
                continue
            if len(x) == 1 and x.isalpha():
                if code is not None:
                    yield code
                code = [x.lower()]
                continue
            if code is not None:
                code.extend([float(v) for v in self.float_re.findall(x) if len(v) != 0])
                yield code
            code = None
        if code is not None:
            yield code

    def commandline(self, data):
        active = self.context.active
        spooler, input_device, output = self.context.registered['device/%s' % active]
        pos = data.find("(")
        commands = {}
        while pos != -1:
            end = data.find(")")
            if "comment" not in commands:
                commands["comment"] = []
            commands["comment"].append(data[pos + 1 : end])
            data = data[:pos] + data[end + 1 :]
            pos = data.find("(")
        pos = data.find(";")
        if pos != -1:
            if "comment" not in commands:
                commands["comment"] = []
            commands["comment"].append(data[pos + 1 :])
            data = data[:pos]
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
            if self.grbl_set_re.match(data):
                settings = list(self.grbl_set_re.findall(data))[0]
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
                spooler.job(COMMAND_HOME)
                if self.home_adjust is not None:
                    spooler.job(COMMAND_MODE_RAPID)
                    spooler.job(COMMAND_MOVE, self.home_adjust[0], self.home_adjust[1])
                return 0
                # return 5  # Homing cycle not enabled by settings.
            return 3  # GRBL '$' system command was not recognized or supported.
        if data.startswith("cat"):
            return 2
        for c in self._tokenize_code(data):
            g = c[0]
            if g not in commands:
                commands[g] = []
            if len(c) >= 2:
                commands[g].append(c[1])
            else:
                commands[g].append(None)
        return self.command(commands)

    def command(self, gc):
        active = self.context.active
        spooler, input_device, output = self.context.registered['device/%s' % active]
        if "m" in gc:
            for v in gc["m"]:
                if v == 0 or v == 1:
                    spooler.job(COMMAND_MODE_RAPID)
                    spooler.job(COMMAND_WAIT_FINISH)
                elif v == 2:
                    return 0
                elif v == 30:
                    return 0
                elif v == 3 or v == 4:
                    self.on_mode = True
                elif v == 5:
                    self.on_mode = False
                    spooler.job(COMMAND_LASER_OFF)
                elif v == 7:
                    #  Coolant control.
                    pass
                elif v == 8:
                    spooler.job(COMMAND_SIGNAL, ("coolant", True))
                elif v == 9:
                    spooler.job(COMMAND_SIGNAL, ("coolant", False))
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
                    spooler.job(COMMAND_MODE_RAPID)
                    spooler.job(COMMAND_WAIT, t)
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
                    self.scale = 39.3701  # g21 is mm mode. 39.3701 mils in a mm
                elif v == 28.0:
                    spooler.job(COMMAND_MODE_RAPID)
                    spooler.job(COMMAND_HOME)
                    if self.home_adjust is not None:
                        spooler.job(
                            COMMAND_MOVE, self.home_adjust[0], self.home_adjust[1]
                        )
                    if self.home is not None:
                        spooler.job(COMMAND_MOVE, self.home)
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
                    spooler.job(COMMAND_MODE_RAPID)
                    spooler.job(COMMAND_HOME)
                    if self.home_adjust is not None:
                        spooler.job(
                            COMMAND_MOVE, self.home_adjust[0], self.home_adjust[1]
                        )
                elif v == 28.3:
                    spooler.job(COMMAND_MODE_RAPID)
                    spooler.job(COMMAND_HOME)
                    if self.home_adjust is not None:
                        spooler.job(
                            COMMAND_MOVE, self.home_adjust[0], self.home_adjust[1]
                        )
                    if "x" in gc:
                        x = gc["x"].pop(0)
                        if len(gc["x"]) == 0:
                            del gc["x"]
                        if x is None:
                            x = 0
                        spooler.job(COMMAND_MOVE, x, 0)
                    if "y" in gc:
                        y = gc["y"].pop(0)
                        if len(gc["y"]) == 0:
                            del gc["y"]
                        if y is None:
                            y = 0
                        spooler.job(COMMAND_MOVE, 0, y)
                elif v == 30.0:
                    # Goto predefined position. Return to secondary home position.
                    if "p" in gc:
                        p = float(gc["p"].pop(0))
                        if len(gc["p"]) == 0:
                            del gc["p"]
                    else:
                        p = None
                    spooler.job(COMMAND_MODE_RAPID)
                    spooler.job(COMMAND_HOME)
                    if self.home_adjust is not None:
                        spooler.job(
                            COMMAND_MOVE, self.home_adjust[0], self.home_adjust[1]
                        )
                    if self.home2 is not None:
                        spooler.job(COMMAND_MOVE, self.home2)
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
                    # Fixure offset 1-6, G10 and G92
                    system = v - 54
                    pass  # Work Coordinate Systems
                elif v == 61:
                    # Exact path control mode. GRBL required
                    pass
                elif v == 80:
                    # Motion mode cancel. Canned cycle.
                    pass
                elif v == 90.0:
                    spooler.job(COMMAND_SET_ABSOLUTE)
                elif v == 91.0:
                    spooler.job(COMMAND_SET_INCREMENTAL)
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
                spooler.job(COMMAND_SET_POWER, v)

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
                spooler.job(COMMAND_MODE_PROGRAM)
                spooler.job(COMMAND_MOVE, x, y)
            elif self.move_mode >= 1:
                spooler.job(COMMAND_MODE_PROGRAM)
                if self.power == 0:
                    spooler.job(COMMAND_MOVE, x, y)
                else:
                    if self.used_speed != self.speed:
                        spooler.job(COMMAND_SET_SPEED, self.speed)
                        self.used_speed = self.speed
                    spooler.job(COMMAND_CUT, x, y)
                # TODO: Implement CW_ARC
                # TODO: Implement CCW_ARC
        return 0

    def g93_feedrate(self):
        # Feed Rate in Minutes / Unit
        self.feed_convert = lambda s: (60.0 / s) * self.scale / MILS_PER_MM
        self.feed_invert = lambda s: (60.0 / s) * MILS_PER_MM / self.scale

    def g94_feedrate(self):
        # Feed Rate in Units / Minute
        self.feed_convert = lambda s: s / ((self.scale / MILS_PER_MM) * 60.0)
        self.feed_invert = lambda s: s * ((self.scale / MILS_PER_MM) * 60.0)
        # units to mm, seconds to minutes.

    @property
    def type(self):
        return "grbl"


class GcodeBlob:
    def __init__(self, name, b=None):
        if b is None:
            b = list()
        self.name = name
        self.data = b
        self.output = True
        self.operation = "GcodeBlob"

    def __repr__(self):
        return "GcodeBlob(%s, %d lines)" % (self.name, len(self.data))

    def as_svg(self):
        pass

    def __len__(self):
        return len(self.data)

    def generate(self):
        grblemulator = GRBLEmulator(None, None)
        for line in self.data:
            grblemulator.write(line)


class GCodeLoader:
    @staticmethod
    def load_types():
        yield "Gcode File", ("gcode", "nc", "gc"), "application/x-gcode"

    @staticmethod
    def load(kernel, pathname, channel=None, **kwargs):
        basename = os.path.basename(pathname)
        with open(pathname, "r") as f:
            blob = GcodeBlob(basename, f.readlines())
        return [blob], None, None, pathname, basename
