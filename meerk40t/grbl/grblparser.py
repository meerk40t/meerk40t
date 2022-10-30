import re

from ..core.cutcode import (
    CutCode,
    HomeCut,
    PlotCut,
    WaitCut,
)
from ..core.parameters import Parameters
from ..core.units import UNITS_PER_INCH, UNITS_PER_MIL, UNITS_PER_MM

MM_PER_MIL = UNITS_PER_MM / UNITS_PER_MIL

STATE_ABORT = -1
STATE_DEFAULT = 0
STATE_CONCAT = 1
STATE_COMPACT = 2

GRBL_SET_RE = re.compile(r"\$(\d+)=([-+]?[0-9]*\.?[0-9]*)")
CODE_RE = re.compile(r"([A-Za-z])")
FLOAT_RE = re.compile(r"[-+]?[0-9]*\.?[0-9]*")


"""
GRBL Emulator
"""


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


class GRBLParser(Parameters):
    def __init__(self):
        Parameters.__init__(self)
        self.design = False
        self.control = False
        self.saving = False

        self.cutcode = CutCode()
        self.plotcut = PlotCut()

        self._use_set = None

        self.spooler = None
        self.device = None

        self.home_adjust = None
        self.scale_x = 1
        self.scale_y = -1

        # Initially assume mm mode 39.4 mils in an mm. G20 DEFAULT
        self.scale = UNITS_PER_MM

        self.compensation = False
        self.feed_convert = None
        self.feed_invert = None
        self.g94_feedrate()  # G94 DEFAULT, mm mode
        self.move_mode = 0
        self.home = None
        self.home2 = None
        self.on_mode = 1
        self.power = 0  # TODO: wrongly duplicates parameters
        self.speed = 0  # TODO: wrongly duplicates parameters
        self.buffer = ""
        self.relative = False  # G90 default.
        self.grbl_settings = {
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
        self.reply = None
        self.position = None
        self.channel = None
        self.x = 0
        self.y = 0

    def __repr__(self):
        return f"GRBL({len(self.cutcode)} cuts)"

    def generate(self):
        for cutobject in self.cutcode:
            yield "plot", cutobject
        yield "plot_start"

    def new_plot_cut(self):
        if len(self.plotcut):
            self.plotcut.settings = self.cutset()
            self.plotcut.check_if_rasterable()
            self.cutcode.append(self.plotcut)
            self.plotcut = PlotCut()

    def cutset(self):
        if self._use_set is None:
            self._use_set = self.derive()
        return self._use_set

    def grbl_write(self, data):
        if self.reply:
            self.reply(data)

    def realtime_write(self, bytes_to_write):
        if bytes_to_write == "?":  # Status report
            # Idle, Run, Hold, Jog, Alarm, Door, Check, Home, Sleep
            device = self if self.device is None else self.device
            if device.state == 0:
                state = "Idle"
            else:
                state = "Busy"
            x, y = device.current
            x /= self.scale
            y /= self.scale
            z = 0.0
            f = self.feed_invert(device.speed)
            s = device.power
            self.grbl_write(f"<{state}|MPos:{x},{y},{z}|FS:{f},{s}>\r\n")
        elif bytes_to_write == "~":  # Resume.
            if self.spooler:
                self.spooler.laserjob("resume", helper=True)
        elif bytes_to_write == "!":  # Pause.
            if self.spooler:
                self.spooler.laserjob("pause", helper=True)
        elif bytes_to_write == "\x18":  # Soft reset.
            if self.spooler:
                self.spooler.laserjob("abort", helper=True)
        elif bytes_to_write == "\x85":
            pass  # Jog Abort.

    def write(self, data):
        if isinstance(data, (bytes, bytearray)):
            if b"?" in data:
                data = data.replace(b"?", b"")
                self.realtime_write("?")
            if b"~" in data:
                data = data.replace(b"~", b"")
                self.realtime_write("~")
            if b"!" in data:
                data = data.replace(b"!", b"")
                self.realtime_write("!")
            if b"\x18" in data:
                data = data.replace(b"\x18", b"")
                self.realtime_write("\x18")
            if b"\x85" in data:
                data = data.replace(b"\x85", b"")
                self.realtime_write("\x85")
            data = data.decode("utf-8")
        self.buffer += data
        while "\b" in self.buffer:
            # Process Backspaces.
            self.buffer = re.sub(".\b", "", self.buffer, count=1)
            if self.buffer.startswith("\b"):
                self.buffer = re.sub("\b+", "", self.buffer)
        while "\r\n" in self.buffer:
            # Process CRLF endlines
            self.buffer = re.sub("\r\n", "\r", self.buffer)
        while "\n" in self.buffer:
            # Process CR endlines
            self.buffer = re.sub("\n", "\r", self.buffer)
        while "\r" in self.buffer:
            # Process normalized lineends.
            pos = self.buffer.find("\r")
            command = self.buffer[0:pos].strip("\r")
            self.buffer = self.buffer[pos + 1 :]
            cmd = self.process(command)
            if cmd == 0:  # Execute GCode.
                self.grbl_write("ok\r\n")
            else:
                self.grbl_write("error:%d\r\n" % cmd)

    def process(self, data):
        if data.startswith("$"):
            if data == "$":
                self.grbl_write(
                    "[HLP:$$ $# $G $I $N $x=val $Nx=line $J=line $SLP $C $X $H ~ ! ? ctrl-x]\r\n"
                )
                return 0
            elif data == "$$":
                for s in self.grbl_settings:
                    v = self.grbl_settings[s]
                    if isinstance(v, int):
                        self.grbl_write("$%d=%d\r\n" % (s, v))
                    elif isinstance(v, float):
                        self.grbl_write("$%d=%.3f\r\n" % (s, v))
                return 0
            if GRBL_SET_RE.match(data):
                settings = list(GRBL_SET_RE.findall(data))[0]
                # print(settings)
                try:
                    c = self.grbl_settings[int(settings[0])]
                except KeyError:
                    return 3
                if isinstance(c, float):
                    self.grbl_settings[int(settings[0])] = float(settings[1])
                else:
                    self.grbl_settings[int(settings[0])] = int(settings[1])
                return 0
            elif data == "$I":
                pass
            elif data == "$G":
                pass
            elif data == "$N":
                pass
            elif data == "$H":

                def realtime_home():
                    yield "home"

                if self.spooler:
                    self.spooler.send(realtime_home)
                return 0
                # return 5  # Homing cycle not enabled by settings.
            elif data.startswith("$"):
                return 3  # GRBL '$' system command was not recognized or supported.
        if data.startswith("cat"):
            # Weird call to cat files for some other grbl boards
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
        return self.process_gcode(commands)

    def process_gcode(self, gc):
        if "m" in gc:
            for v in gc["m"]:
                if v in (0, 1):
                    # Stop or Unconditional Stop
                    self.new_plot_cut()
                elif v == 2:
                    # Program End
                    self.new_plot_cut()
                    return 0
                elif v == 30:
                    # Program Stop
                    self.new_plot_cut()
                    return 0
                elif v in (3, 4):
                    # Spindle On - Clockwise/CCW Laser Mode
                    self.new_plot_cut()
                elif v == 5:
                    # Spindle Off - Laser Mode
                    self.new_plot_cut()
                elif v == 7:
                    #  Mist coolant control.
                    pass
                elif v == 8:
                    # Flood coolant On
                    if self.spooler:
                        self.spooler.laserjob(["signal", ("coolant", True)], helper=True)
                elif v == 9:
                    # Flood coolant Off
                    if self.spooler:
                        self.spooler.laserjob(["signal", ("coolant", False)], helper=True)
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
                elif v == 0:
                    # G0 Rapid Move.
                    self.move_mode = 0
                elif v == 1:
                    # G1 Cut Move.
                    self.move_mode = 1
                elif v == 2:
                    # G2 CW_ARC
                    self.move_mode = 2
                elif v == 3:
                    # G3 CCW_ARC
                    self.move_mode = 3
                elif v == 4:
                    # DWELL
                    t = 0
                    if "p" in gc:
                        t = float(gc["p"].pop()) / 1000.0
                        if len(gc["p"]) == 0:
                            del gc["p"]
                    if "s" in gc:
                        t = float(gc["s"].pop())
                        if len(gc["s"]) == 0:
                            del gc["s"]
                    self.new_plot_cut()
                    self.cutcode.append(WaitCut(t))
                elif v == 17:
                    # Set XY coords.
                    pass
                elif v == 18:
                    # Set the XZ plane for arc.
                    return 2
                elif v == 19:
                    # Set the YZ plane for arc.
                    return 2
                elif v in (20, 70):
                    # g20 is inch mode.
                    self.scale = UNITS_PER_INCH
                elif v in (21, 71):
                    # g21 is mm mode. 39.3701 mils in a mm
                    self.scale = UNITS_PER_MM
                elif v == 28:
                    # Move to Origin (Home)
                    self.cutcode.append(HomeCut())
                elif v == 38.1:
                    # Touch Plate
                    pass
                elif v == 38.2:
                    # Probe towards workpiece, stop on contact. Signal error.
                    pass
                elif v == 38.3:
                    # Probe towards workpiece, stop on contact.
                    pass
                elif v == 38.4:
                    # Probe away from workpiece, signal error
                    pass
                elif v == 38.5:
                    # Probe away from workpiece.
                    pass
                elif v == 40.0:
                    # Compensation Off
                    self.compensation = False
                elif v == 43.1:
                    pass  # Dynamic tool Length offsets
                elif v == 49:
                    # Cancel tool offset.
                    pass  # Dynamic tool length offsets
                elif 53 <= v <= 59:
                    # Coord System Select
                    pass  # Work Coordinate Systems
                elif v == 61:
                    # Exact path control mode. GRBL required
                    pass
                elif v == 80:
                    # Motion mode cancel. Canned cycle.
                    pass
                elif v == 90:
                    # Set to Absolute Positioning
                    self.relative = False
                elif v == 91:
                    # Set to Relative Positioning
                    self.relative = True
                elif v == 92:
                    # Set Position.
                    # Change the current coords without moving.
                    pass  # Coordinate Offset TODO: Implement
                elif v == 92.1:
                    # Clear Coordinate offset set by 92.
                    pass  # Clear Coordinate offset TODO: Implement
                elif v == 93:
                    # Feed Rate Mode (Inverse Time Mode)
                    self.g93_feedrate()
                elif v == 94:
                    # Feed Rate Mode (Units Per Minute)
                    self.g94_feedrate()
                else:
                    return 20  # Unsupported or invalid g-code command found in block.
            del gc["g"]

        if "comment" in gc:
            if self.channel:
                self.channel(f'Comment: {gc["comment"]}')
            del gc["comment"]

        if "f" in gc:  # Feed_rate
            for v in gc["f"]:
                if v is None:
                    return 2  # Numeric value format is not valid or missing an expected value.
                feed_rate = self.feed_convert(v)
                if self.speed != feed_rate:
                    self.speed = feed_rate
                    # On speed change we start a new plot.
                    self.new_plot_cut()
            del gc["f"]
        if "s" in gc:
            for v in gc["s"]:
                if v is None:
                    return 2  # Numeric value format is not valid or missing an expected value.
                if 0.0 < v <= 1.0:
                    v *= 1000  # numbers between 0-1 are taken to be in range 0-1.
                self.power = v

            del gc["s"]
        if "x" in gc or "y" in gc:
            ox = self.x
            oy = self.y
            if "x" in gc:
                x = gc["x"].pop(0)
                if x is None:
                    x = 0
                else:
                    x *= self.scale * self.scale_x
                if len(gc["x"]) == 0:
                    del gc["x"]
            else:
                x = 0
            if "y" in gc:
                y = gc["y"].pop(0)
                if y is None:
                    y = 0
                else:
                    y *= self.scale * self.scale_y
                if len(gc["y"]) == 0:
                    del gc["y"]
            else:
                y = 0
            if self.relative:
                self.x += x
                self.y += y
            else:
                self.x = x
                self.y = y
            if self.move_mode == 0:
                self.plotcut.plot_append(self.x, self.y, 0)
            elif self.move_mode == 1:
                self.plotcut.plot_append(self.x, self.y, self.power / 1000.0)
            elif self.move_mode == 2:
                # TODO: Implement CW_ARC
                self.plotcut.plot_append(self.x, self.y, self.power / 1000.0)
            elif self.move_mode == 3:
                # TODO: Implement CCW_ARC
                self.plotcut.plot_append(self.x, self.y, self.power / 1000.0)
            if self.position:
                self.position((ox, oy, self.x, self.y))
        return 0

    def g93_feedrate(self):
        # Feed Rate in Minutes / Unit
        self.feed_convert = lambda s: (60.0 / s) * self.scale / UNITS_PER_MM
        self.feed_invert = lambda s: (60.0 / s) * UNITS_PER_MM / self.scale

    def g94_feedrate(self):
        # Feed Rate in Units / Minute
        self.feed_convert = lambda s: s / ((self.scale / UNITS_PER_INCH) * 60.0)
        self.feed_invert = lambda s: s * ((self.scale / UNITS_PER_INCH) * 60.0)
        # units to mm, seconds to minutes.

    @property
    def type(self):
        return "grbl"
