"""
GRBL Parser.

The grbl parser is intended to be a reusable parser. For commands sent to the write()
function and will update the internal state of the parser as needed and send processed
values to the self.plotter. These commands consist of a command and some number of operands.

"new": asks for a new plot
"start": start of new design
"end": design is ended
"home": Home the device (this is always followed by a move to 0,0).
"move", ox, oy, x, y: move to the position x, y from ox, oy
"line", ox, oy, x, y, power: line to the position, x, y from ox, oy at power `power`.
"arc", ox, oy, cx, cy, x, y, power: arc to the position, x, y from ox, oy via cx,cy (control)
        at power `power`.
"wait", t: Time in seconds to wait
"resume": Resume the laser operation
"pause": Pause the laser operation
"abort": Abort the laser operations
"jog_abort": Abort the current jog action for the laser (usually $J)
"coolant", <boolean>: Turns the coolant on or off.

These commands are called on the `plotter` function which should be passed during the init.

The reply callable is given any responses to these written code commands.
The channel callable is given any additional information about the gcode.
"""

import re

from meerk40t.svgelements import Arc, Color, Path, Move
from meerk40t.core.units import UNITS_PER_PIXEL, UNITS_PER_MM, UNITS_PER_INCH


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


class GRBLPlotter:

    def __init__(self):
        self.paths = list()
        self._path = Path()
        self.operations = {}
        self.paths.append(self._path)
        self.last_x = 0
        self.last_y = 0
        self.power = 0
        self.speed = 0
        self.debugstring = ""

    def setdebug(self, msg):
        self.debugstring = msg

    def plotter(self, command, *args):
        # print (f"{command} - {args}")
        if command == "move":
            x0, y0, x1, y1 = args
            if len(self._path)>0 and isinstance(self._path._segments[-1], Move):
                # The last segment is already a move, so let's update it instead
                self._path._segments[-1].end.x = x1
                self._path._segments[-1].end.y = y1
            else:
                self._path.move((x1, y1))
            self.last_x = x1
            self.last_y = y1
        elif command in "line":
            x0, y0, x1, y1, power = args
            # Initial move?
            if not self._path:
                self._path.move((x0, y0))
            self._path.line((x1, y1))
            self.last_x = x1
            self.last_y = y1
        elif command in "arc":
            x0, y0, cx, cy, x1, y1, power = args
            if (x0 == cx and y0 == cy) or (x1 == cx and x1 == cy):
                self._path.line((x1, x1))
            else:
                arc = Arc(start=(x0, y0), end=(x1, y1), control=(cx, cy))
                self._path.append(arc)
            self.last_x = x1
            self.last_y = y1
        elif command == "new":
            # We break the path here and create a new one
            if len(self._path):
                # Is the trailing segment a move ?
                while len(self._path) > 0 and isinstance(self._path._segments[-1], Move):
                    self._path._segments.pop()
                if len(self._path) == 0:
                    # Degenerate...
                    for op in self.operations:
                        if self._path in self.operations[op]:
                            # Should be the last...
                            self.operations[op].pop()
                    self.paths.pop()
                self._path = Path()
                self.paths.append(self._path)
            if len(args) > 1:
                feed = args[0]
                power = args[1]
                if feed != 0:
                    self.speed = feed
                if power != 0:
                    self.power = power
                if self.speed != 0 and self.power != 0:
                    # Do we have this operation already?!
                    id_string = f"{self.speed}|{self.power}"
                    if id_string not in self.operations:
                        self.operations[id_string] = list()
                    self.operations[id_string].append(self._path)
        elif command == "end":
            if len(self._path):
                # Is the trailing segment a move ?
                while len(self._path) > 0 and isinstance(self._path._segments[-1], Move):
                    self._path._segments.pop()
                if len(self._path) == 0:
                    # Degenerate...
                    for op in self.operations:
                        if self._path in self.operations[op]:
                            # Should be the last...
                            self.operations[op].pop()
                    self.paths.pop()
        elif command == "wait":
            pass
        elif command == "resume":
            pass
        elif command == "pause":
            pass
        elif command == "abort":
            pass
        elif command == "coolant":
            # True or False coolant.
            pass
        elif command == "jog_abort":
            pass

class GRBLParser:
    def __init__(self, plotter=None):
        self.plotter = plotter
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
            "homing_cycle_enable": 0,  # Homing cycle enable
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

        self.move_mode = 0
        self.x = 0
        self.y = 0
        self.home = None
        self.home2 = None

        # Initially assume mm mode. G21 mm DEFAULT
        self.scale = UNITS_PER_MM

        # G94 feedrate default, mm mode
        self.g94_feedrate()

        # G90 default.
        self.relative = False

        self.reply = None
        self.channel = None

        self._buffer = ""

    def __repr__(self):
        return "GRBLParser()"

    def parse(self, data, elements):
        plotclass = GRBLPlotter()
        self.plotter = plotclass.plotter
        for d in data:
            if isinstance(d, (bytes, bytearray)):
                d = d.decode("utf-8")
            # Lets split lines...
            splitted_lines = d.splitlines()
            for singleline in splitted_lines:
                self.process(singleline)
        # Terminate
        self.plotter("end")
        # We need to add a matrix to scale grbl coordinates ?!
        op_nodes = {}
        for path in plotclass.paths:
            if path is None or len(path) == 0:
                continue
            node = elements.elem_branch.add(
                type="elem path", path=abs(path), stroke=Color("blue"), stroke_width=UNITS_PER_PIXEL,
            )
            for op in plotclass.operations:
                values = op.split("|")
                if len(values) > 1:
                    speed = float(values[0])
                    power = float(values[1])
                else:
                    # Should not happen...
                    continue
                if path in plotclass.operations[op]:
                    if op in op_nodes:
                        opnode = op_nodes[op]
                    else:
                        from meerk40t.core.node.op_engrave import EngraveOpNode
                        opnode = EngraveOpNode(label=f"Grbl - P={power}, S={speed}")
                        opnode.speed = speed
                        opnode.power = power
                        opnode.color = Color("blue")
                        node.stroke = opnode.color
                        elements.op_branch.add_node(opnode)
                        op_nodes[op] = opnode
                    opnode.add_reference(node)

        elements.signal("tree_changed")

    def grbl_write(self, data):
        if self.reply:
            self.reply(data)

    @property
    def current(self):
        return self.x, self.y

    @property
    def state(self):
        return 0

    def realtime_write(self, bytes_to_write):
        if bytes_to_write == "?":  # Status report
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
            self.grbl_write(f"<{state}|MPos:{x},{y},{z}|FS:{f},{s}>\r\n")
        elif bytes_to_write == "~":  # Resume.
            self.plotter("resume")
        elif bytes_to_write == "!":  # Pause.
            self.plotter("pause")
        elif bytes_to_write == "\x18":  # Soft reset.
            self.plotter("abort")
        elif bytes_to_write == "\x85":
            self.plotter("jog_abort")

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
        self._buffer += data
        while "\b" in self._buffer:
            # Process Backspaces.
            self._buffer = re.sub(".\b", "", self._buffer, count=1)
            if self._buffer.startswith("\b"):
                self._buffer = re.sub("\b+", "", self._buffer)
        while "\r\n" in self._buffer:
            # Process CRLF endlines
            self._buffer = re.sub("\r\n", "\r", self._buffer)
        while "\n" in self._buffer:
            # Process CR endlines
            self._buffer = re.sub("\n", "\r", self._buffer)
        while "\r" in self._buffer:
            # Process normalized lineends.
            pos = self._buffer.find("\r")
            command = self._buffer[0:pos].strip("\r")
            self._buffer = self._buffer[pos + 1 :]
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
                pass
            elif data == "$G":
                pass
            elif data == "$N":
                pass
            elif data == "$H":
                if self.settings["homing_cycle_enable"]:
                    self.plotter("home")
                    self.plotter("move", self.x, self.y, 0, 0)
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
                commands = {}
                for c in _tokenize_code(data):
                    g = c[0]
                    if g not in commands:
                        commands[g] = []
                    if len(c) >= 2:
                        commands[g].append(c[1])
                    else:
                        commands[g].append(None)
                return 3  # not yet supported
            elif data.startswith("$"):
                return 3  # GRBL '$' system command was not recognized or supported.

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
                    self.plotter("new")
                elif v == 2:
                    # Program End
                    self.plotter("new")
                    return 0
                elif v == 30:
                    # Program Stop
                    self.plotter("new")
                    return 0
                elif v in (3, 4):
                    # Spindle On - Clockwise/CCW Laser Mode
                    self.plotter("start")
                elif v == 5:
                    # Spindle Off - Laser Mode
                    self.plotter("end")
                elif v == 7:
                    #  Mist coolant control.
                    pass
                elif v == 8:
                    # Flood coolant On
                    self.plotter("coolant", True)
                elif v == 9:
                    # Flood coolant Off
                    self.plotter("coolant", False)
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
                    self.plotter("new")
                    self.plotter("wait", t)
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
                    self.plotter("home")
                    self.plotter("move", self.x, self.y, 0, 0)
                    self.x = 0
                    self.y = 0
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
                    # On speed change we start a new plot.
                    self.plotter("new", v, 0)
            del gc["f"]
        if "s" in gc:
            for v in gc["s"]:
                if v is None:
                    return 2  # Numeric value format is not valid or missing an expected value.
                if 0.0 < v <= 1.0:
                    v *= 1000  # numbers between 0-1 are taken to be in range 0-1.
                if self.settings["power"] != v:
                    self.plotter("new", 0, v)
                self.settings["power"] = v
            del gc["s"]
        if "x" in gc or "y" in gc:
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
            power = self.settings.get("power", 0)
            if self.move_mode == 0:
                self.plotter("move", ox, oy, self.x, self.y)
            elif self.move_mode == 1:
                self.plotter("line", ox, oy, self.x, self.y, power / 1000.0)
            elif self.move_mode == 2:
                # CW ARC
                cx = ox
                cy = oy
                self.plotter("arc", ox, oy, cx, cy, self.x, self.y, power / 1000.0)
            elif self.move_mode == 3:
                # CCW ARC
                cx = ox
                cy = oy
                self.plotter("arc", ox, oy, cx, cy, self.x, self.y, power / 1000.0)
        return 0

    ### THE CODE FOR G93 / G94 NEEDS A THOROUGH REVIEW
    # According to my understanding they have to be given in the context of the active unit
    # (mm or inch)

    def g93_feedrate(self):
        # Feed Rate in Minutes / Unit
        # G93 - is Inverse Time Mode. In inverse time feed rate mode, an F word means the move
        # should be completed in [one divided by the F number] minutes. For example, if the
        # F number is 2.0, the move should be completed in half a minute.
        # When the inverse time feed rate mode is active, an F word must appear on every line
        # which has a G1, G2, or G3 motion, and an F word on a line that does not have
        # G1, G2, or G3 is ignored. Being in inverse time feed rate mode does not
        # affect G0 (rapid move) motions.
        if self.scale == UNITS_PER_INCH:
            self.feed_convert = lambda s: (60.0 * self.scale / UNITS_PER_INCH) / s
            self.feed_invert = lambda s: (60.0 * UNITS_PER_INCH / self.scale) / s
        else:
            self.feed_convert = lambda s: (60.0 * self.scale / UNITS_PER_MM) / s
            self.feed_invert = lambda s: (60.0 * UNITS_PER_MM / self.scale) / s

        # Original code:
        # MM_PER_INCH = 25.4
        # MIL_PER_INCH = 1000.0
        # MIL_PER_MM = MIL_PER_INCH / MM_PER_INCH
        # self.feed_convert = lambda s: (60.0 / s) * self.scale / MIL_PER_MM
        # self.feed_invert = lambda s: (60.0 / s) * MIL_PER_MM / self.scale

    def g94_feedrate(self):
        # Feed Rate in Units / Minute
        # G94 - is Units per Minute Mode. In units per minute feed mode, an F word is interpreted
        # to mean the controlled point should move at a certain number of inches per minute,
        # millimeters per minute, or degrees per minute, depending upon what length units
        # are being used and which axis or axes are moving.
        if self.scale == UNITS_PER_INCH:
            self.feed_convert = lambda s: s / ((self.scale / UNITS_PER_INCH) * 60.0)
            self.feed_invert = lambda s: s * ((self.scale / UNITS_PER_INCH) * 60.0)
        else:
            self.feed_convert = lambda s: s / ((self.scale / UNITS_PER_MM) * 60.0)
            self.feed_invert = lambda s: s * ((self.scale / UNITS_PER_MM) * 60.0)
        # units to mm, seconds to minutes.

        # Original code:
        # MIL_PER_INCH = 1000.0
        # self.feed_convert = lambda s: s / ((self.scale / MIL_PER_INCH) * 60.0)
        # self.feed_invert = lambda s: s * ((self.scale / MIL_PER_INCH) * 60.0)
        # units to mm, seconds to minutes.

    @property
    def type(self):
        return "grbl"
