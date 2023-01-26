"""
GRBL Interpreter

The GRBL Interpreter converts our parsed Grbl/Gcode data into Driver-like calls.
"""

import re

import numpy as np

from meerk40t.core.cutcode.cutcode import CutCode
from meerk40t.core.cutcode.linecut import LineCut
from meerk40t.core.cutcode.plotcut import PlotCut
from meerk40t.core.units import UNITS_PER_INCH, UNITS_PER_MM
from meerk40t.svgelements import Arc

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


step_pulse_microseconds = 0
step_idle_delay = 25
step_pulse_invert = 2
step_direction_invert = 3
invert_step_enable_pin = 4
invert_limit_pins = 5
invert_probe_pin = 6
status_report_options = 10
junction_deviation = 11
arc_tolerance = 12
report_in_inches = 13
soft_limits_enabled = 20
hard_limits_enabled = 21
homing_cycle_enable = 22
homing_direction_invert = 23
homing_locate_feed_rate = 24
homing_search_seek_rate = 25
homing_switch_debounce_delay = 26
homing_switch_pulloff_distance = 27
maximum_spindle_speed = 30
minimum_spindle_speed = 31
laser_mode_enable = 32
x_axis_steps_per_millimeter = 100
y_axis_steps_per_millimeter = 101
z_axis_steps_per_millimeter = 102
x_axis_max_rate = 110
y_axis_max_rate = 111
z_axis_max_rate = 112
x_axis_acceleration = 120
y_axis_acceleration = 121
z_axis_acceleration = 122
x_axis_max_travel = 130
y_axis_max_travel = 131
z_axis_max_travel = 132

lookup = {
    step_pulse_microseconds: "step_pulse_microseconds",
    step_idle_delay: "step_idle_delay",
    step_pulse_invert: "step_pulse_invert",
    step_direction_invert: "step_direction_invert",
    invert_step_enable_pin: "invert_step_enable_pin",
    invert_limit_pins: "invert_limit_pins",
    invert_probe_pin: "invert_probe_pin",
    status_report_options: "status_report_options",
    junction_deviation: "junction_deviation",
    arc_tolerance: "arc_tolerance",
    report_in_inches: "report_in_inches",
    soft_limits_enabled: "soft_limits_enabled",
    hard_limits_enabled: "hard_limits_enabled",
    homing_cycle_enable: "homing_cycle_enable",
    homing_direction_invert: "homing_direction_invert",
    homing_locate_feed_rate: "homing_locate_feed_rate,",
    homing_search_seek_rate: "homing_search_seek_rate",
    homing_switch_debounce_delay: "homing_switch_debounce_delay,",
    homing_switch_pulloff_distance: "homing_switch_pulloff_distance",
    maximum_spindle_speed: "maximum_spindle_speed,",
    minimum_spindle_speed: "minimum_spindle_speed,",
    laser_mode_enable: "laser_mode_enable,",
    x_axis_steps_per_millimeter: "x_axis_steps_per_millimeter",
    y_axis_steps_per_millimeter: "y_axis_steps_per_millimeter",
    z_axis_steps_per_millimeter: "z_axis_steps_per_millimeter",
    x_axis_max_rate: "x_axis_max_rate",
    y_axis_max_rate: "y_axis_max_rate",
    z_axis_max_rate: "z_axis_max_rate",
    x_axis_acceleration: "x_axis_acceleration",
    y_axis_acceleration: "y_axis_acceleration",
    z_axis_acceleration: "z_axis_acceleration",
    x_axis_max_travel: "x_axis_max_travel",
    y_axis_max_travel: "y_axis_max_travel",
    z_axis_max_travel: "z_axis_max_travel",
}


class GRBLInterpreter:
    def __init__(self, driver, units_to_device_matrix):
        self.driver = driver
        self.units_to_device_matrix = units_to_device_matrix
        self.settings = {
            "step_pulse_microseconds": 10,  # step pulse microseconds
            "step_idle_delay": 25,  # step idle delay
            "step_pulse_invert": 0,  # step pulse invert
            "step_direction_invert": 0,  # step direction invert
            "invert_step_enable_pin": 0,  # invert step enable pin, boolean
            "invert_limit_pins": 0,  # invert limit pins, boolean
            "invert_probe_pin": 0,  # invert probe pin
            "status_report_options": 255,  # status report options
            "junction_deviation": 0.010,  # Junction deviation, mm
            "arc_tolerance": 0.002,  # arc tolerance, mm
            "report_in_inches": 0,  # Report in inches
            "soft_limits_enabled": 0,  # Soft limits enabled.
            "hard_limits_enabled": 0,  # hard limits enabled
            "homing_cycle_enable": 1,  # Homing cycle enable
            "homing_direction_invert": 0,  # Homing direction invert
            "homing_locate_feed_rate": 25.000,  # Homing locate feed rate, mm/min
            "homing_search_seek_rate": 500.000,  # Homing search seek rate, mm/min
            "homing_switch_debounce_delay": 250,  # Homing switch debounce delay, ms
            "homing_switch_pulloff_distance": 1.000,  # Homing switch pull-off distance, mm
            "maximum_spindle_speed": 1000,  # Maximum spindle speed, RPM
            "minimum_spindle_speed": 0,  # Minimum spindle speed, RPM
            "laser_mode_enable": 1,  # Laser mode enable, boolean
            "x_axis_steps_per_millimeter": 250.000,  # X-axis steps per millimeter
            "y_axis_steps_per_millimeter": 250.000,  # Y-axis steps per millimeter
            "z_axis_steps_per_millimeter": 250.000,  # Z-axis steps per millimeter
            "x_axis_max_rate": 500.000,  # X-axis max rate mm/min
            "y_axis_max_rate": 500.000,  # Y-axis max rate mm/min
            "z_axis_max_rate": 500.000,  # Z-axis max rate mm/min
            "x_axis_acceleration": 10.000,  # X-axis acceleration, mm/s^2
            "y_axis_acceleration": 10.000,  # Y-axis acceleration, mm/s^2
            "z_axis_acceleration": 10.000,  # Z-axis acceleration, mm/s^2
            "x_axis_max_travel": 200.000,  # X-axis max travel mm.
            "y_axis_max_travel": 200.000,  # Y-axis max travel mm
            "z_axis_max_travel": 200.000,  # Z-axis max travel mm.
            "speed": 0,
            "power": 0,
        }

        self.compensation = False
        self.feed_convert = None
        self.feed_invert = None

        self.speed_scale = 1.0
        self.rapid_scale = 1.0
        self.power_scale = 1.0
        self.move_mode = 0
        self.x = 0
        self.y = 0
        self.z = 0

        # Initially assume mm mode. G21 mm DEFAULT
        self.scale = UNITS_PER_MM

        # G94 feedrate default, mm mode
        self.g94_feedrate()

        # G90 default.
        self.relative = False

        self.reply = None
        self.channel = None

        self._buffer = list()
        self._grbl_specific = False
        self._interpolate = 50
        self.program_mode = False

    def __repr__(self):
        return "GRBLInterpreter()"

    def grbl_write(self, data):
        if self.reply:
            self.reply(data)

    @property
    def current(self):
        return self.x, self.y

    @property
    def state(self):
        return 0

    def status_update(self):
        # Idle, Run, Hold, Jog, Alarm, Door, Check, Home, Sleep
        if self.state == 0:
            state = "Idle"
        else:
            state = "Busy"
        x, y = self.current
        x /= self.scale
        y /= self.scale
        z = 0.0
        f = self.feed_invert(self.settings.get("speed", 0))
        s = self.settings.get("power", 0)
        return f"<{state}|MPos:{x},{y},{z}|FS:{f},{s}>\r\n"

    def write(self, data):
        """
        Process data written to the parser. This is any gcode data realtime commands, grbl-specific commands,
        or gcode itself.

        @param data:
        @return:
        """
        for c in data:
            # Process and extract any realtime grbl commands.
            if c == ord("?"):
                self.grbl_write(self.status_update())
            elif c == ord("~"):
                self.driver.resume()
            elif c == ord("!"):
                self.driver.pause()
            elif c in (ord("\r"), ord("\n")):
                # Process CRLF endlines
                line = ''.join(self._buffer)
                if self._grbl_specific:
                    self._grbl_specific = False
                    cmd = self._grbl_special(line)
                else:
                    cmd = self._process_gcode(line)
                self._buffer.clear()
                if cmd == 0:  # Execute GCode.
                    self.grbl_write("ok\r\n")
                else:
                    self.grbl_write("error:%d\r\n" % cmd)
            elif c == 0x08:
                # Process Backspaces.
                if self._buffer:
                    del self._buffer[-1]
            elif c == 0x18:
                self.driver.reset()
            elif c == 0x84:
                # Safety Door
                pass
            elif c == 0x85:
                try:
                    self.driver.jog_abort()
                except AttributeError:
                    pass
            elif c == 0x90:
                self.speed_scale = 1.0
                self.driver.set("speed_factor", self.speed_scale)
            elif c == 0x91:
                self.speed_scale *= 1.1
                self.driver.set("speed_factor", self.speed_scale)
            elif c == 0x92:
                self.speed_scale *= 0.9
                self.driver.set("speed_factor", self.speed_scale)
            elif c == 0x93:
                self.speed_scale *= 1.01
                self.driver.set("speed_factor", self.speed_scale)
            elif c == 0x94:
                self.speed_scale *= 0.99
                self.driver.set("speed_factor", self.speed_scale)
            elif c == 0x95:
                self.rapid_scale = 1.0
                self.driver.set("rapid_factor", self.rapid_scale)
            elif c == 0x96:
                self.rapid_scale = 0.5
                self.driver.set("rapid_factor", self.rapid_scale)
            elif c == 0x97:
                self.rapid_scale = 0.25
                self.driver.set("rapid_factor", self.rapid_scale)
            elif c == 0x99:
                self.power_scale = 1.0
                self.driver.set("power_factor", self.power_scale)
            elif c == 0x9A:
                self.power_scale *= 1.1
                self.driver.set("power_factor", self.power_scale)
            elif c == 0x9B:
                self.power_scale *= 0.9
                self.driver.set("power_factor", self.power_scale)
            elif c == 0x9C:
                self.power_scale *= 1.01
                self.driver.set("power_factor", self.power_scale)
            elif c == 0x9D:
                self.power_scale *= 0.99
                self.driver.set("power_factor", self.power_scale)
            elif c == 0x9E:
                # Toggle Spindle Stop
                pass
            elif c == 0xA0:
                # Toggle Flood Coolant
                pass
            elif c == 0xA1:
                # Toggle Mist Coolant
                pass
            elif c == ord("$"):
                if not self._buffer:
                    # First character is "$" this is special grbl.
                    self._grbl_specific = True
                self._buffer.append(chr(c))
            else:
                self._buffer.append(chr(c))

    def _grbl_special(self, data):
        """
        GRBL special commands are commands beginning with $ that do purely grbl specific things.

        @param data:
        @return:
        """
        if data == "$":
            self.grbl_write(
                "[HLP:$$ $# $G $I $N $x=val $Nx=line $J=line $SLP $C $X $H ~ ! ? ctrl-x]\r\n"
            )
            return 0
        elif data == "$$":
            for s in lookup:
                v = self.settings.get(lookup[s], 0)
                if isinstance(v, int):
                    self.grbl_write("$%d=%d\r\n" % (s, v))
                elif isinstance(v, float):
                    self.grbl_write("$%d=%.3f\r\n" % (s, v))
            return 0
        if GRBL_SET_RE.match(data):
            settings = list(GRBL_SET_RE.findall(data))[0]
            index = settings[0]
            value = settings[1]
            try:
                name = lookup[index]
                c = self.settings[name]
            except KeyError:
                return 3
            if isinstance(c, float):
                self.settings[name] = float(value)
            else:
                self.settings[name] = int(value)
            return 0
        elif data == "$I":
            # View Build Info
            pass
        elif data == "$G":
            # View GCode Parser state
            pass
        elif data == "$N":
            # View saved start up code.
            pass
        elif data == "$H":
            if self.settings["homing_cycle_enable"]:
                self.driver.physical_home()
                self.driver.move_abs(0, 0)
                self.x = 0
                self.y = 0
                return 0
            else:
                return 5  # Homing cycle not enabled by settings.
        elif data.startswith("$J="):
            """
            $Jx=line - Run jogging motion

            New to Grbl v1.1, this command will execute a special jogging motion. There are three main
            differences between a jogging motion and a motion commanded by a g-code line.

                Like normal g-code commands, several jog motions may be queued into the planner buffer,
                but the jogging can be easily canceled by a jog-cancel or feed-hold real-time command.
                Grbl will immediately hold the current jog and then automatically purge the buffers
                of any remaining commands.
                Jog commands are completely independent of the g-code parser state. It will not change
                any modes like G91 incremental distance mode. So, you no longer have to make sure
                that you change it back to G90 absolute distance mode afterwards. This helps reduce
                the chance of starting with the wrong g-code modes enabled.
                If soft-limits are enabled, any jog command that exceeds a soft-limit will simply
                return an error. It will not throw an alarm as it would with a normal g-code command.
                This allows for a much more enjoyable and fluid GUI or joystick interaction.

            Executing a jog requires a specific command structure, as described below:

                The first three characters must be '$J=' to indicate the jog.

                The jog command follows immediate after the '=' and works like a normal G1 command.

                Feed rate is only interpreted in G94 units per minute. A prior G93 state is
                ignored during jog.

                Required words:
                    XYZ: One or more axis words with target value.
                    F - Feed rate value. NOTE: Each jog requires this value and is not treated as modal.

                Optional words: Jog executes based on current G20/G21 and G90/G91 g-code parser state.
                If one of the following optional words is passed, that state is overridden for one command only.
                    G20 or G21 - Inch and millimeter mode
                    G90 or G91 - Absolute and incremental distances
                    G53 - Move in machine coordinates

                All other g-codes, m-codes, and value words are not accepted in the jog command.

                Spaces and comments are allowed in the command. These are removed by the pre-parser.

                Example: G21 and G90 are active modal states prior to jogging. These are sequential commands.
                    $J=X10.0 Y-1.5 will move to X=10.0mm and Y=-1.5mm in work coordinate frame (WPos).
                    $J=G91 G20 X0.5 will move +0.5 inches (12.7mm) to X=22.7mm (WPos).
                    Note that G91 and G20 are only applied to this jog command.
                    $J=G53 Y5.0 will move the machine to Y=5.0mm in the machine coordinate frame (MPos).
                    If the work coordinate offset for the y-axis is 2.0mm, then Y is 3.0mm in (WPos).

            Jog commands behave almost identically to normal g-code streaming. Every jog command
            will return an 'ok' when the jogging motion has been parsed and is setup for execution.
            If a command is not valid or exceeds a soft-limit, Grbl will return an 'error:'.
            Multiple jogging commands may be queued in sequence.
            """
            data = data[3:]
            # self._process_gcode(data, jog=True)
            return 3  # not yet supported
        else:
            return 3  # GRBL '$' system command was not recognized or supported.

    def _process_gcode(self, data, jog=False):
        """
        Processes the gcode commands which are parsed into different dictionary objects.

        @param data: gcode line to process
        @param jog: indicate this gcode line is operated as a jog.
        @return:
        """
        gc = {}
        for c in _tokenize_code(data):
            g = c[0]
            if g not in gc:
                gc[g] = []
            if len(c) >= 2:
                gc[g].append(c[1])
            else:
                gc[g].append(None)
        if "m" in gc:
            for v in gc["m"]:
                if v in (0, 1):
                    # Stop or Unconditional Stop
                    self.driver.rapid_mode()
                elif v == 2:
                    # Program End
                    self.driver.plot_start()
                    self.driver.rapid_mode()
                    return 0
                elif v == 30:
                    # Program Stop
                    self.driver.rapid_mode()
                    return 0
                elif v in (3, 4):
                    # Spindle On - Clockwise/CCW Laser Mode
                    self.driver.program_mode()
                    self.program_mode = True
                elif v == 5:
                    # Spindle Off - Laser Mode
                    if self.program_mode:
                        self.driver.plot_start()
                    self.driver.rapid_mode()
                    self.program_mode = False
                elif v == 7:
                    #  Mist coolant control.
                    pass
                elif v == 8:
                    # Flood coolant On
                    self.driver.signal("coolant", True)
                elif v == 9:
                    # Flood coolant Off
                    self.driver.signal("coolant", False)
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
                    self.driver.rapid_mode()
                    self.driver.wait(t)
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
                    self.driver.home()
                    self.driver.move_abs(0, 0)
                    self.x = 0
                    self.y = 0
                    self.z = 0
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
                if self.settings.get("speed", 0) != feed_rate:
                    self.settings["speed"] = feed_rate
                    self.driver.set("speed", v)
            del gc["f"]
        if "s" in gc:
            for v in gc["s"]:
                if v is None:
                    return 2  # Numeric value format is not valid or missing an expected value.
                if 0.0 < v <= 1.0:
                    v *= 1000  # numbers between 0-1 are taken to be in range 0-1.
                if self.settings["power"] != v:
                    self.driver.set("power", v)
                    self.settings["power"] = v
            del gc["s"]
        if "z" in gc:
            oz = self.z
            v = gc["z"].pop(0)
            if v is None:
                z = 0
            else:
                z = self.scale * v
            if len(gc["z"]) == 0:
                del gc["z"]
            self.z = z
            if oz != self.z:
                try:
                    self.driver.axis("z", self.z)
                except AttributeError:
                    pass

        if (
            "x" in gc
            or "y" in gc
            or ("i" in gc or "j" in gc and self.move_mode in (2, 3))
        ):
            ox = self.x
            oy = self.y
            if "x" in gc:
                x = gc["x"].pop(0)
                if x is None:
                    x = 0
                else:
                    x *= self.scale
                if len(gc["x"]) == 0:
                    del gc["x"]
            else:
                if self.relative:
                    x = 0
                else:
                    x = self.x
            if "y" in gc:
                y = gc["y"].pop(0)
                if y is None:
                    y = 0
                else:
                    y *= self.scale
                if len(gc["y"]) == 0:
                    del gc["y"]
            else:
                if self.relative:
                    y = 0
                else:
                    y = self.y
            if self.relative:
                self.x += x
                self.y += y
            else:
                self.x = x
                self.y = y
            if self.move_mode == 0:
                self.driver.move_abs(self.x, self.y)
            elif self.move_mode == 1:
                plotcut = PlotCut(settings=dict(self.settings))
                power = self.settings["power"]
                plotcut.plot_append(ox , oy, power)
                plotcut.plot_append(self.x, self.y, power)
                self.plot(plotcut)
            elif self.move_mode in (2, 3):
                # 2 = CW ARC
                # 3 = CCW ARC
                cx = ox
                cy = oy
                if "i" in gc:
                    ix = gc["i"].pop(0)  # * self.scale
                    cx += ix
                if "j" in gc:
                    jy = gc["j"].pop(0)  # * self.scale
                    cy += jy
                if "r" in gc:
                    # Strictly speaking this uses the R parameter, but that wasn't coded.
                    arc = Arc(
                        start=(ox, oy),
                        center=(cx, cy),
                        end=(self.x, self.y),
                        ccw=self.move_mode == 3,
                    )
                    power = self.settings["power"]
                    plotcut = PlotCut(settings=dict(self.settings))
                    for p in range(self._interpolate + 1):
                        x, y = arc.point(p / self._interpolate)
                        plotcut.plot_append(x, y, power)
                    self.plot(plotcut)
                else:
                    arc = Arc(
                        start=(ox, oy),
                        center=(cx, cy),
                        end=(self.x, self.y),
                        ccw=self.move_mode == 3,
                    )
                    power = self.settings["power"]
                    plotcut = PlotCut(settings=self.settings)
                    for p in range(self._interpolate + 1):
                        x, y = arc.point(p / self._interpolate)
                        plotcut.plot_append(x, y, power)
                    self.plot(plotcut)
        return 0

    def plot(self, plot):
        if isinstance(plot, PlotCut):
            matrix = self.units_to_device_matrix
            for i in range(len(plot.plot)):
                x, y, laser = plot.plot[i]
                x, y = matrix.transform_point([x, y])
                plot.plot[i] = int(x), int(y), laser
        self.driver.plot(plot)
        if not self.program_mode:
            # If we plotted this and we aren't in program mode execute all of these commands right away
            self.driver.plot_start()

    def g93_feedrate(self):
        """
        Feed Rate in Minutes / Unit
        G93 - is Inverse Time Mode. In inverse time feed rate mode, an F word means the move
        should be completed in [one divided by the F number] minutes. For example, if the
        F number is 2.0, the move should be completed in half a minute.
        When the inverse time feed rate mode is active, an F word must appear on every line
        which has a G1, G2, or G3 motion, and an F word on a line that does not have
        G1, G2, or G3 is ignored. Being in inverse time feed rate mode does not
        affect G0 (rapid move) motions.
        @return:
        """

        if self.scale == UNITS_PER_INCH:
            self.feed_convert = lambda s: (60.0 * self.scale / UNITS_PER_INCH) / s
            self.feed_invert = lambda s: (60.0 * UNITS_PER_INCH / self.scale) / s
        else:
            self.feed_convert = lambda s: (60.0 * self.scale / UNITS_PER_MM) / s
            self.feed_invert = lambda s: (60.0 * UNITS_PER_MM / self.scale) / s

    def g94_feedrate(self):
        """
        Feed Rate in Units / Minute
        G94 - is Units per Minute Mode. In units per minute feed mode, an F word is interpreted
        to mean the controlled point should move at a certain number of inches per minute,
        millimeters per minute, or degrees per minute, depending upon what length units
        are being used and which axis or axes are moving.
        @return:
        """

        if self.scale == UNITS_PER_INCH:
            self.feed_convert = lambda s: s / ((self.scale / UNITS_PER_INCH) * 60.0)
            self.feed_invert = lambda s: s * ((self.scale / UNITS_PER_INCH) * 60.0)
        else:
            self.feed_convert = lambda s: s / ((self.scale / UNITS_PER_MM) * 60.0)
            self.feed_invert = lambda s: s * ((self.scale / UNITS_PER_MM) * 60.0)
