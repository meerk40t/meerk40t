import re
import threading
import time

from meerk40t.core.cutcode.plotcut import PlotCut
from meerk40t.core.cutcode.waitcut import WaitCut
from meerk40t.core.units import UNITS_PER_INCH, UNITS_PER_MM
from meerk40t.svgelements import Arc

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


OKAY = 0
# G-code words consist of a letter and a value. Letter was not found.
ERROR_GCODE_LETTER_NOT_FOUND = 1
# Numeric value format is not valid or missing an expected value.
ERROR_NUMERIC_VALUE_INVALID = 2
# Grbl '$' system command was not recognized or supported.
ERROR_REALTIME_NOT_SUPPORTED = 3
# Negative value received for an expected positive value.
ERROR_NEGATIVE_VALUE = 4
# Homing cycle is not enabled via settings.
ERROR_HOMING_CYCLE_DISABLED = 5
# Minimum step pulse time must be greater than 3usec
ERROR_STEP_PULSE_INVALID = 6
# EEPROM read failed. Reset and restored to default values.
ERROR_EEPROM_READ_ERROR = 7
# Grbl '$' command cannot be used unless Grbl is IDLE. Ensures smooth operation during a job.
ERROR_NOT_IDLE = 8
# G-code locked out during alarm or jog state
ERROR_ALARM_OR_JOG = 9
# Soft limits cannot be enabled without homing also enabled.
ERROR_SOFT_LIMITS = 10
# Max characters per line exceeded. Line was not processed and executed.
ERROR_MAX_CHARACTERS = 11
# (Compile Option) Grbl '$' setting value exceeds the maximum step rate supported.
ERROR_EXCEEDED_MAX_STEP = 12
# Safety door detected as opened and door state initiated.
ERROR_SAFETY_DOOR = 13
# (Grbl-Mega Only) Build info or startup line exceeded EEPROM line length limit.
ERROR_EEPROM_LINE_LIMIT = 14
# Jog target exceeds machine travel. Command ignored.
ERROR_JOG_EXCEEDS_MACHINE = 15
# Jog command with no '=' or contains prohibited g-code.
ERROR_JOG_SYNTAX = 16
# Laser mode requires PWM output.
ERROR_REQUIRED_POWER = 17
# Unsupported or invalid g-code command found in block.
ERROR_UNSUPPORTED_GCODE = 20
# More than one g-code command from same modal group found in block.
ERROR_DUPLICATE_COMMAND_MODAL = 21
# Feed rate has not yet been set or is undefined.
ERROR_FEED_RATE_UNSET = 22
# G-code command in block requires an integer value.
ERROR_NUMERIC_VALUE_MISSING = 23
# Two G-code commands that both require the use of the XYZ axis words were detected in the block.
ERROR_OVERLAPPING_GCODE = 24
# A G-code word was repeated in the block.
ERROR_DUPLICATE_COMMAND = 25
# A G-code command implicitly or explicitly requires XYZ axis words in the block, but none were detected.
ERROR_REQUIRES_COORDINATES = 26
# N line number value is not within the valid range of 1 - 9,999,999.
ERROR_INVALID_LINENUMBER = 27
# A G-code command was sent, but is missing some required P or L value words in the line.
ERROR_MISSING_REQUIRED_INFO = 28
# Grbl supports six work coordinate systems G54-G59. G59.1, G59.2, and G59.3 are not supported.
ERROR_UNSUPPORTED_WORK_COORDS = 29
# The G53 G-code command requires either a G0 seek or G1 feed motion mode to be active. A different motion was active.
ERROR_INVALID_MOVE_COMMAND = 30
# There are unused axis words in the block and G80 motion mode cancel is active.
ERROR_UNUSED_AXIS_WORDS = 31
# A G2 or G3 arc was commanded but there are no XYZ axis words in the selected plane to trace the arc.
ERROR_ARC_WITHOUT_WORDS = 32
# The motion command has an invalid target. G2, G3, and G38.2 generates this error, if the arc is impossible to generate or if the probe target is the current position.
ERROR_INVALID_TARGET = 33
# A G2 or G3 arc, traced with the radius definition, had a mathematical error when computing the arc geometry. Try either breaking up the arc into semicircles or quadrants, or redefine them with the arc offset definition.
ERROR_ARC_COMPUTATION = 34
# A G2 or G3 arc, traced with the offset definition, is missing the IJK offset word in the selected plane to trace the arc.
ERROR_ARC_OFFSET_WORDS_MISSING = 35
# There are unused, leftover G-code words that aren't used by any command in the block.
ERROR_UNUSED_WORDS = 36
# The G43.1 dynamic tool length offset command cannot apply an offset to an axis other than its configured axis. The Grbl default axis is the Z-axis.
ERROR_TOOL_LENGTH_INVALID = 37
# Tool number greater than max supported value.
ERROR_EXCEEDED_TOOL_MAX = 38


class GcodeJob:
    def __init__(
        self, driver=None, units_to_device_matrix=None, priority=0, channel=None
    ):
        self.units_to_device_matrix = units_to_device_matrix
        self._driver = driver
        self.channel = channel
        self.reply = None
        self.buffer = list()

        self.priority = priority

        self.time_submitted = time.time()
        self.time_started = None
        self.runtime = 0

        self._stopped = True
        self._estimate = 0

        # Initially assume mm mode. G21 mm DEFAULT
        self.scale = UNITS_PER_MM

        self.compensation = False
        self.feed_convert = None
        self.feed_invert = None
        self._interpolate = 50
        self.program_mode = False
        self.plotcut = None

        self.speed = None
        self.power = None

        self.move_mode = 0
        self.x = 0
        self.y = 0
        self.z = 0

        self.lock = threading.Lock()

        # G90 default.
        self.relative = False

        # G94 feedrate default, mm mode
        self.g94_feedrate()

    def __str__(self):
        return f"{self.__class__.__name__}({len(self.buffer)} lines)"

    @property
    def status(self):
        if self.is_running and self.time_started is not None:
            return "Running"
        elif not self.is_running:
            return "Disabled"
        else:
            return "Queued"

    def reply_code(self, cmd):
        if cmd == 0:  # Execute GCode.
            if self.reply:
                self.reply("ok\r\n")
        else:
            if self.reply:
                self.reply(f"error:{cmd}\r\n")

    def write(self, line):
        with self.lock:
            self.buffer.append(line)

    def write_all(self, lines):
        with self.lock:
            self.buffer.extend(lines)

    def write_blob(self, data):
        self.write_all(
            [r for r in re.split("[\n|\r]", data.decode("utf-8")) if r.strip()]
        )

    def execute(self, driver=None):
        """
        Execute calls each item in the list of items in order. This is intended to be called by the spooler thread. And
        hold the spooler while these items are executing.
        @return:
        """
        self._stopped = False
        if self.time_started is None:
            self.time_started = time.time()
        try:
            with self.lock:
                line = self.buffer.pop(0)
            cmd = self._process_gcode(line)
            self.reply_code(cmd)
        except IndexError:
            # Could not pop, list is empty. Job is done.
            pass
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
        result = 0
        if self.is_running():
            result = time.time() - self.time_started
        else:
            result = self.runtime
        return result

    def estimate_time(self):
        """
        Give laser job time estimate.
        @return:
        """
        return self._estimate

    def _process_gcode(self, data, jog=False):
        """
        Processes the gcode commands which are parsed into different dictionary objects.
        List of Supported G-Codes in Grbl v1.1:
          - Non-Modal Commands: G4, G10L2, G10L20, G28, G30, G28.1, G30.1, G53, G92, G92.1
          - Motion Modes: G0, G1, G2, G3, G38.2, G38.3, G38.4, G38.5, G80
          - Feed Rate Modes: G93, G94
          - Unit Modes: G20, G21
          - Distance Modes: G90, G91
          - Arc IJK Distance Modes: G91.1
          - Plane Select Modes: G17, G18, G19
          - Tool Length Offset Modes: G43.1, G49
          - Cutter Compensation Modes: G40
          - Coordinate System Modes: G54, G55, G56, G57, G58, G59
          - Control Modes: G61
          - Program Flow: M0, M1, M2, M30*
          - Coolant Control: M7*, M8, M9
          - Spindle Control: M3, M4, M5
          - Valid Non-Command Words: F, I, J, K, L, N, P, R, S, T, X, Y, Z

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
                    # Program Flow: Stop or Unconditional Stop
                    try:
                        self._driver.rapid_mode()
                    except AttributeError:
                        pass
                elif v == 2:
                    # Program Flow: Program End
                    try:
                        self._driver.plot_start()
                    except AttributeError:
                        pass
                    try:
                        self._driver.rapid_mode()
                    except AttributeError:
                        pass
                    return OKAY
                elif v == 30:
                    # Program Flow: Program Stop
                    try:
                        self._driver.rapid_mode()
                    except AttributeError:
                        pass
                    return OKAY
                elif v in (3, 4):
                    # Spindle Control - Spindle On - Clockwise/CCW Laser Mode
                    self.program_mode = True
                elif v == 5:
                    # Spindle Control - Spindle Off - Laser Mode
                    if self.program_mode:
                        try:
                            self.plot_commit()
                            self._driver.plot_start()
                        except AttributeError:
                            pass
                    try:
                        self._driver.rapid_mode()
                    except AttributeError:
                        pass
                    self.program_mode = False
                elif v == 7:
                    #  Coolant Control: Mist coolant control.
                    pass
                elif v == 8:
                    # Coolant Control: Flood coolant On
                    try:
                        self._driver.signal("coolant", True)
                    except AttributeError:
                        pass
                elif v == 9:
                    # Coolant Control: Flood coolant Off
                    try:
                        self._driver.signal("coolant", False)
                    except AttributeError:
                        pass
                elif v == 56:
                    # Parking motion override control.
                    pass
                else:
                    # Unsupported or invalid g-code command found in block.
                    return ERROR_UNSUPPORTED_GCODE
            del gc["m"]
        if "g" in gc:
            for v in gc["g"]:
                if v is None:
                    # G but no number given.
                    # Numeric value format is not valid or missing an expected value.
                    return ERROR_NUMERIC_VALUE_INVALID
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
                    if self.program_mode:
                        self.plot_commit()
                        self.plot(WaitCut(t))
                    else:
                        try:
                            self._driver.wait(t)
                        except AttributeError:
                            pass
                elif v == 10:
                    l_value = gc["l"].pop(0)
                    if l_value is None:
                        # A G-code command was sent, but is missing some required P or L value words in the line.
                        return ERROR_MISSING_REQUIRED_INFO
                    elif l_value == 2:
                        # Set Work Coordinate Offsets
                        pass
                    elif l_value == 20:
                        # Set Work Coordinate Offsets
                        # Sets the offset values for the coordinate system. P1 = G54
                        p_value = gc["p"].pop(0)
                        if p_value is None:
                            # A G-code command was sent, but is missing some required P or L value words in the line.
                            return ERROR_MISSING_REQUIRED_INFO
                    else:
                        # Unsupported or invalid g-code command found in block.
                        return ERROR_UNSUPPORTED_GCODE
                elif v == 17:
                    # Set XY coords.
                    pass
                elif v == 18:
                    # Set the XZ plane for arc.
                    # Unsupported or invalid g-code command found in block.
                    return ERROR_UNSUPPORTED_GCODE
                elif v == 19:
                    # Set the YZ plane for arc.
                    # Unsupported or invalid g-code command found in block.
                    return ERROR_UNSUPPORTED_GCODE
                elif v in (20, 70):
                    # g20 is inch mode.
                    self.scale = UNITS_PER_INCH
                elif v in (21, 71):
                    # g21 is mm mode. 39.3701 mils in a mm
                    self.scale = UNITS_PER_MM
                elif v == 28:
                    # Move to Origin (Home)
                    try:
                        self._driver.home()
                    except AttributeError:
                        pass
                    try:
                        self._driver.move_abs(0, 0)
                    except AttributeError:
                        pass
                    self.x = 0
                    self.y = 0
                    self.z = 0
                elif v == 28.1:
                    # Set Pre-defined Location
                    pass
                elif v == 30:
                    # Goto Pre-defined Position
                    pass
                elif v == 30.1:
                    # Set Pre-defined Position
                    pass
                elif v == 38.2:
                    # Probe towards workpiece, stop on contact. Signal error.
                    # Unsupported or invalid g-code command found in block.
                    return ERROR_UNSUPPORTED_GCODE
                elif v == 38.3:
                    # Probe towards workpiece, stop on contact.
                    # Unsupported or invalid g-code command found in block.
                    return ERROR_UNSUPPORTED_GCODE
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
                elif v == 53:
                    # Absolute movement non-modal command.
                    pass
                elif 54 <= v <= 59:
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
                    # Unsupported or invalid g-code command found in block.
                    return ERROR_UNSUPPORTED_GCODE
            del gc["g"]

        if "comment" in gc:
            if self.channel:
                self.channel(f'Comment: {gc["comment"]}')
            del gc["comment"]

        if "f" in gc:  # Feed_rate
            for v in gc["f"]:
                if v is None:
                    # Numeric value format is not valid or missing an expected value.
                    return ERROR_NUMERIC_VALUE_INVALID
                feed_rate = self.feed_convert(v)
                if self.speed != feed_rate:
                    self.speed = feed_rate
                    try:
                        self._driver.set("speed", v)
                    except AttributeError:
                        pass
                    self.plot_commit()  # Speed change means plot change
            del gc["f"]
        if "s" in gc:
            for v in gc["s"]:
                if v is None:
                    # Numeric value format is not valid or missing an expected value.
                    return ERROR_NUMERIC_VALUE_INVALID
                if 0.0 < v <= 1.0:
                    v *= 1000  # numbers between 0-1 are taken to be in range 0-1.
                if self.power != v:
                    try:
                        self._driver.set("power", v)
                    except AttributeError:
                        pass
                    self.power = v
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
                    self.plot_commit()  # We plot commit on z level change
                    self._driver.axis("z", self.z)
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
                nx = self.x + x
                ny = self.y + y
            else:
                nx = x
                ny = y
            if self.move_mode == 0:
                self.plot_commit()
                if self.program_mode:
                    self.plot_location(nx, ny, 0)
                else:
                    try:
                        self._driver.move_abs(nx, ny)
                        self.x = nx
                        self.y = ny
                    except AttributeError:
                        pass
            elif self.move_mode == 1:
                self.plot_location(nx, ny, self.power)
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
                        end=(nx, ny),
                        ccw=self.move_mode == 3,
                    )
                    power = self.power
                    for p in range(self._interpolate + 1):
                        x, y = arc.point(p / self._interpolate)
                        self.plot_location(x, y, power)
                else:
                    arc = Arc(
                        start=(ox, oy),
                        center=(cx, cy),
                        end=(nx, ny),
                        ccw=self.move_mode == 3,
                    )
                    power = self.power
                    for p in range(self._interpolate + 1):
                        x, y = arc.point(p / self._interpolate)
                        self.plot_location(x, y, power)
        return OKAY

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
            ox, oy = matrix.transform_point([self.x, self.y])
            self.plotcut = PlotCut(settings={"speed": self.speed, "power": self.power})
            self.plotcut.plot_init(int(round(ox)), int(round(oy)))
        tx, ty = matrix.transform_point([x, y])
        self.plotcut.plot_append(
            int(round(tx)), int(round(ty)), power * (self.power / 1000.0)
        )
        if not self.program_mode:
            self.plot_commit()
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
        if not self.program_mode:
            # If we plotted this, and we aren't in program mode execute all of these commands right away
            try:
                self._driver.plot_start()
            except AttributeError:
                pass

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
