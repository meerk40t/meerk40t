"""
GRBL Emulator

The GRBL Emulator converts our parsed Grbl/Gcode data into Driver-like calls.
"""
import re

from meerk40t.grbl.gcodejob import GcodeJob

GRBL_SET_RE = re.compile(r"\$(\d+)=([-+]?[0-9]*\.?[0-9]*)")

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


class GRBLEmulator:
    def __init__(self, device=None, units_to_device_matrix=None):
        self.device = device
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
        }

        self.speed_scale = 1.0
        self.rapid_scale = 1.0
        self.power_scale = 1.0

        self.reply = None
        self.channel = None

        self._grbl_specific = False

        self._buffer = list()
        self.job = GcodeJob(
            driver=device.driver,
            priority=0,
            channel=self.channel,
            units_to_device_matrix=units_to_device_matrix,
        )

    def __repr__(self):
        return "GRBLInterpreter()"

    def reply_code(self, cmd):
        if cmd == 0:  # Execute GCode.
            if self.reply:
                self.reply("ok\r\n")
        else:
            if self.reply:
                self.reply(f"error:{cmd}\r\n")

    def status_update(self):
        # TODO: This should reference only the driver.status.
        # Idle, Run, Hold, Jog, Alarm, Door, Check, Home, Sleep
        pos, state, minor = self.device.driver.status()
        x, y = self.units_to_device_matrix.point_in_inverse_space(pos)
        x /= self.job.scale
        y /= self.job.scale
        z = 0.0
        if state == "busy":
            state = "Run"
        elif state == "hold":
            state = "Hold"
        else:
            state = "Idle"
        f = self.device.driver.speed
        s = self.device.driver.power
        return f"<{state}|MPos:{x:.3f},{y:.3f},{z:.3f}|FS:{f},{s}>\r\n"

    def write(self, data):
        """
        Process data written to the parser. This is any gcode data realtime commands, grbl-specific commands,
        or gcode itself.

        @param data:
        @return:
        """
        if isinstance(data, str):
            data = data.encode()
        for c in data:
            # Process and extract any realtime grbl commands.
            if c == ord("?"):
                if self.reply:
                    self.reply(self.status_update())
            elif c == ord("~"):
                try:
                    self.device.driver.resume()
                except AttributeError:
                    pass
            elif c == ord("!"):
                try:
                    self.device.driver.pause()
                except AttributeError:
                    pass
            elif c in (ord("\r"), ord("\n")):
                # Process CRLF endlines
                line = "".join(self._buffer)
                if self._grbl_specific:
                    self._grbl_specific = False
                    self.reply_code(self._grbl_special(line))
                else:
                    self.device.spooler.send(self.job, prevent_duplicate=True)
                    self.job.reply = self.reply
                    self.job.write(line)
                self._buffer.clear()
            elif c == 0x08:
                # Process Backspaces.
                if self._buffer:
                    del self._buffer[-1]
            elif c == 0x18:
                try:
                    self.device.driver.reset()
                except AttributeError:
                    pass
            elif c > 0x80:
                if c == 0x84:
                    # Safety Door
                    pass
                elif c == 0x85:
                    try:
                        self.device.driver.jog_abort()
                    except AttributeError:
                        pass
                elif c == 0x90:
                    self.speed_scale = 1.0
                    try:
                        self.device.driver.set("speed_factor", self.speed_scale)
                    except AttributeError:
                        pass
                elif c == 0x91:
                    self.speed_scale *= 1.1
                    try:
                        self.device.driver.set("speed_factor", self.speed_scale)
                    except AttributeError:
                        pass
                elif c == 0x92:
                    self.speed_scale *= 0.9
                    try:
                        self.device.driver.set("speed_factor", self.speed_scale)
                    except AttributeError:
                        pass
                elif c == 0x93:
                    self.speed_scale *= 1.01
                    try:
                        self.device.driver.set("speed_factor", self.speed_scale)
                    except AttributeError:
                        pass
                elif c == 0x94:
                    self.speed_scale *= 0.99
                    try:
                        self.device.driver.set("speed_factor", self.speed_scale)
                    except AttributeError:
                        pass
                elif c == 0x95:
                    self.rapid_scale = 1.0
                    try:
                        self.device.driver.set("rapid_factor", self.rapid_scale)
                    except AttributeError:
                        pass
                elif c == 0x96:
                    self.rapid_scale = 0.5
                    try:
                        self.device.driver.set("rapid_factor", self.rapid_scale)
                    except AttributeError:
                        pass
                elif c == 0x97:
                    self.rapid_scale = 0.25
                    try:
                        self.device.driver.set("rapid_factor", self.rapid_scale)
                    except AttributeError:
                        pass
                elif c == 0x99:
                    self.power_scale = 1.0
                    try:
                        self.device.driver.set("power_factor", self.power_scale)
                    except AttributeError:
                        pass
                elif c == 0x9A:
                    self.power_scale *= 1.1
                    try:
                        self.device.driver.set("power_factor", self.power_scale)
                    except AttributeError:
                        pass
                elif c == 0x9B:
                    self.power_scale *= 0.9
                    try:
                        self.device.driver.set("power_factor", self.power_scale)
                    except AttributeError:
                        pass
                elif c == 0x9C:
                    self.power_scale *= 1.01
                    try:
                        self.device.driver.set("power_factor", self.power_scale)
                    except AttributeError:
                        pass
                elif c == 0x9D:
                    self.power_scale *= 0.99
                    try:
                        self.device.driver.set("power_factor", self.power_scale)
                    except AttributeError:
                        pass
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
            if self.reply:
                self.reply(
                    "[HLP:$$ $# $G $I $N $x=val $Nx=line $J=line $SLP $C $X $H ~ ! ? ctrl-x]\r\n"
                )
            return 0
        elif data == "$$":
            for s in lookup:
                v = self.settings.get(lookup[s], 0)
                if isinstance(v, int):
                    if self.reply:
                        self.reply("$%d=%d\r\n" % (s, v))
                elif isinstance(v, float):
                    if self.reply:
                        self.reply("$%d=%.3f\r\n" % (s, v))
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
            return 0
        elif data == "$G":
            # View GCode Parser state
            return 3
        elif data == "$N":
            # View saved start up code.
            return 3
        elif data == "$H":
            if self.settings["homing_cycle_enable"]:
                try:
                    self.device.driver.physical_home()
                except AttributeError:
                    pass
                try:
                    self.device.driver.move_abs(0, 0)
                except AttributeError:
                    pass
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
