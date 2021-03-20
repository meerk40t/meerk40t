from ...core.plotplanner import PlotPlanner
from ...core.zinglplotter import ZinglPlotter
from ...kernel import Modifier
from ..basedevice import (INTERPRETER_STATE_FINISH,
                          INTERPRETER_STATE_MODECHANGE,
                          INTERPRETER_STATE_PROGRAM, INTERPRETER_STATE_RAPID,
                          PLOT_AXIS, PLOT_DIRECTION, PLOT_FINISH, PLOT_JOG,
                          PLOT_RAPID, PLOT_SETTING, Interpreter)
from ..lasercommandconstants import *
from .laserspeed import LaserSpeed

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


class LhymicroInterpreter(Interpreter, Modifier):
    """
    LhymicroInterpreter provides Lhystudio specific coding for elements and sends it to the backend
    to write to the usb.

    The interpret() ticks to process additional data.
    """

    def __init__(self, context, job_name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, job_name, channel)
        Interpreter.__init__(self, context=context)

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

        self.pipe = self.context.channel("pipe/send")
        self.realtime_pipe = self.context.channel("pipe/send_realtime")

        def primary_hold():
            buffer = self.context._buffer_size
            if buffer is None:
                return False
            return self.context.buffer_limit and buffer > self.context.buffer_max

        self.holds.append(primary_hold)

    def attach(self, *a, **kwargs):
        context = self.context
        kernel = context._kernel
        _ = kernel.translation
        root_context = context.get_context('/')

        @context.console_command(
            "pulse", help="pulse <time>: Pulse the laser in place."
        )
        def pulse(command, channel, _, args=tuple(), **kwargs):
            if len(args) == 0:
                channel(_("Must specify a pulse time in milliseconds."))
                return
            try:
                value = float(args[0]) / 1000.0
            except ValueError:
                channel(_('"%s" not a valid pulse time in milliseconds') % (args[0]))
                return
            if value > 1.0:
                channel(
                    _('"%s" exceeds 1 second limit to fire a standing laser.')
                    % (args[0])
                )
                try:
                    if args[1] != "idonotlovemyhouse":
                        return
                except IndexError:
                    return

            def timed_fire():
                yield COMMAND_WAIT_FINISH
                yield COMMAND_LASER_ON
                yield COMMAND_WAIT, value
                yield COMMAND_LASER_OFF

            if self.context.spooler.job_if_idle(timed_fire):
                channel(_("Pulse laser for %f milliseconds") % (value * 1000.0))
            else:
                channel(_("Pulse laser failed: Busy"))
            return

        @context.console_command("speed", help="Set Speed in Interpreter.")
        def speed(command, channel, _, args=tuple(), **kwargs):
            if len(args) == 0:
                channel(_("Speed set at: %f mm/s") % self.speed)
                return
            inc = False
            percent = False
            speed = args[0]
            if speed == "inc":
                speed = args[1]
                inc = True
            if speed.endswith("%"):
                speed = speed[:-1]
                percent = True
            try:
                s = float(speed)
            except ValueError:
                channel(_("Not a valid speed or percent."))
                return
            if percent and inc:
                s = self.speed + self.speed * (s / 100.0)
            elif inc:
                s += self.speed
            elif percent:
                s = self.speed * (s / 100.0)
            self.set_speed(s)
            channel(_("Speed set at: %f mm/s") % self.speed)

        @context.console_command("power", help="Set Interpreter Power")
        def power(command, channel, _, args=tuple(), **kwargs):
            if len(args) == 0:
                channel(_("Power set at: %d pulses per inch") % self.power)
            else:
                try:
                    self.set_power(int(args[0]))
                except ValueError:
                    pass

        @context.console_command(
            "acceleration", help="Set Interpreter Acceleration [1-4]"
        )
        def acceleration(command, channel, _, args=tuple(), **kwargs):
            if len(args) == 0:
                if self.acceleration is None:
                    channel(_("Acceleration is set to default."))
                else:
                    channel(_("Acceleration: %d") % self.acceleration)

            else:
                try:
                    v = int(args[0])
                    if v not in (1, 2, 3, 4):
                        self.set_acceleration(None)
                        channel(_("Acceleration is set to default."))
                        return
                    self.set_acceleration(v)
                    channel(_("Acceleration: %d") % self.acceleration)
                except ValueError:
                    channel(_("Invalid Acceleration [1-4]."))
                    return

        @context.console_command("pause", help="realtime pause/resume of the machine")
        def realtime_pause(command, channel, _, args=tuple(), **kwargs):
            if self.is_paused:
                self.resume()
            else:
                self.pause()

        @self.context.console_command("abort", help="Abort Job")
        def pipe_abort(command, channel, _, args=tuple(), **kwargs):
            self.reset()
            channel("Lhystudios Channel Aborted.")

        @self.context.console_argument("rapid_x", type=float, help="limit x speed for rapid.")
        @self.context.console_argument("rapid_y", type=float, help="limit y speed for rapid.")
        @self.context.console_command("rapid_override", help="limit speed of typical rapid moves.")
        def rapid_override(command, channel, _, rapid_x=None, rapid_y=None, **kwargs):
            if rapid_x is not None:
                if rapid_y is None:
                    rapid_y = rapid_x
                self.rapid_override = True
                self.rapid_override_speed_x = rapid_x
                self.rapid_override_speed_y = rapid_y
                channel(_("Rapid Limit: %f, %f") % (self.rapid_override_speed_x,self.rapid_override_speed_y))
            else:
                self.rapid_override = False
                channel(_("Rapid Limit Off"))

        context.interpreter = self

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
        root_context.setting(bool, "opt_rapid_between", True)
        root_context.setting(int, "opt_jog_mode", 0)
        root_context.setting(int, "opt_jog_minimum", 127)

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

        context.register("control/Realtime Pause", self.pause)
        context.register("control/Realtime Resume", self.resume)
        context.register("control/Update Codes", self.update_codes)

        context.get_context("/").listen("lifecycle;ready", self.on_interpreter_ready)

    def detach(self, *args, **kwargs):
        self.context.get_context("/").unlisten(
            "lifecycle;ready", self.on_interpreter_ready
        )
        self.thread = None

    def on_interpreter_ready(self, *args):
        self.start_interpreter()

    def __repr__(self):
        return "LhymicroInterpreter()"

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
                        or self.state != INTERPRETER_STATE_PROGRAM
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
        self.realtime_pipe(b"PN!\n")
        self.is_paused = True

    def resume(self, *values):
        self.realtime_pipe(b"PN&\n")
        self.is_paused = False

    def reset(self):
        Interpreter.reset(self)
        self.context.signal("pipe;buffer", 0)
        self.plot = None
        self.plot_planner.clear()
        self.realtime_pipe(b"I*\n")
        self.laser = False
        self.properties = 0
        self.state = INTERPRETER_STATE_RAPID
        self.context.signal("interpreter;mode", self.state)
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
        self.state = INTERPRETER_STATE_RAPID
        self.laser = False
        if self.is_prop(STATE_HORIZONTAL_MAJOR):
            if not self.is_left and dx >= 0:
                self.pipe(self.CODE_LEFT)
            if not self.is_right and dx <= 0:
                self.pipe(self.CODE_RIGHT)
        else:
            if not self.is_top and dy >= 0:
                self.pipe(self.CODE_TOP)
            if not self.is_bottom and dy <= 0:
                self.pipe(self.CODE_BOTTOM)
        self.pipe(b"N")
        if dy != 0:
            self.goto_y(dy)
        if dx != 0:
            self.goto_x(dx)
        self.pipe(b"SE")
        self.declare_directions()
        self.state = INTERPRETER_STATE_PROGRAM

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
        if self.state == INTERPRETER_STATE_RAPID:
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
                self.pipe(b"I")
                if dx != 0:
                    self.goto_x(dx)
                if dy != 0:
                    self.goto_y(dy)
                self.pipe(b"S1P\n")
                if not self.context.autolock:
                    self.pipe(b"IS2P\n")
        elif self.state == INTERPRETER_STATE_PROGRAM:
            mx = 0
            my = 0
            for x, y in ZinglPlotter.plot_line(0, 0, dx, dy):
                self.goto_octent(x - mx, y - my, cut)
                mx = x
                my = y
        elif self.state == INTERPRETER_STATE_FINISH:
            if dx != 0:
                self.goto_x(dx)
            if dy != 0:
                self.goto_y(dy)
            self.pipe(b"N")
        elif self.state == INTERPRETER_STATE_MODECHANGE:
            self.fly_switch_speed(dx, dy)
        self.check_bounds()
        # self.context.signal('interpreter;position', (self.context.current_x, self.context.current_y,
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
        # self.context.signal('interpreter;position', (self.context.current_x, self.context.current_y,
        #                                              self.context.current_x - dx, self.context.current_y - dy))

    def set_speed(self, speed=None):
        if self.settings.speed != speed:
            self.settings.speed = speed
            if self.state == INTERPRETER_STATE_PROGRAM:
                self.state = INTERPRETER_STATE_MODECHANGE

    def set_d_ratio(self, dratio=None):
        if self.settings.dratio != dratio:
            self.settings.dratio = dratio
            if self.state == INTERPRETER_STATE_PROGRAM:
                self.state = INTERPRETER_STATE_MODECHANGE

    def set_acceleration(self, accel=None):
        if self.settings.acceleration != accel:
            self.settings.acceleration = accel
            if self.state == INTERPRETER_STATE_PROGRAM:
                self.state = INTERPRETER_STATE_MODECHANGE

    def set_step(self, step=None):
        if self.settings.raster_step != step:
            self.settings.raster_step = step
            if self.state == INTERPRETER_STATE_PROGRAM:
                self.state = INTERPRETER_STATE_MODECHANGE

    def laser_off(self):
        if not self.laser:
            return False
        if self.state == INTERPRETER_STATE_RAPID:
            self.pipe(b"I")
            self.pipe(self.CODE_LASER_OFF)
            self.pipe(b"S1P\n")
            if not self.context.autolock:
                self.pipe(b"IS2P\n")
        elif self.state == INTERPRETER_STATE_PROGRAM:
            self.pipe(self.CODE_LASER_OFF)
        elif self.state == INTERPRETER_STATE_FINISH:
            self.pipe(self.CODE_LASER_OFF)
            self.pipe(b"N")
        self.laser = False
        return True

    def laser_on(self):
        if self.laser:
            return False
        if self.state == INTERPRETER_STATE_RAPID:
            self.pipe(b"I")
            self.pipe(self.CODE_LASER_ON)
            self.pipe(b"S1P\n")
            if not self.context.autolock:
                self.pipe(b"IS2P\n")
        elif self.state == INTERPRETER_STATE_PROGRAM:
            self.pipe(self.CODE_LASER_ON)
        elif self.state == INTERPRETER_STATE_FINISH:
            self.pipe(self.CODE_LASER_ON)
            self.pipe(b"N")
        self.laser = True
        return True

    def ensure_rapid_mode(self):
        if self.state == INTERPRETER_STATE_RAPID:
            return
        if self.state == INTERPRETER_STATE_FINISH:
            self.pipe(b"S1P\n")
            if not self.context.autolock:
                self.pipe(b"IS2P\n")
        elif (
            self.state == INTERPRETER_STATE_PROGRAM
            or self.state == INTERPRETER_STATE_MODECHANGE
        ):
            self.pipe(b"FNSE-\n")
            self.laser = False
        self.state = INTERPRETER_STATE_RAPID
        self.context.signal("interpreter;mode", self.state)

    def fly_switch_speed(self, dx=0, dy=0):
        dx = int(round(dx))
        dy = int(round(dy))
        self.pipe(b"@NSE")
        self.state = INTERPRETER_STATE_RAPID
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
        self.pipe(speed_code)
        if dx != 0:
            self.goto_x(dx)
        if dy != 0:
            self.goto_y(dy)
        self.pipe(b"N")
        self.set_requested_directions()
        self.pipe(self.code_declare_directions())
        self.pipe(b"S1E")
        self.state = INTERPRETER_STATE_PROGRAM

    def ensure_finished_mode(self):
        if self.state == INTERPRETER_STATE_FINISH:
            return
        if (
            self.state == INTERPRETER_STATE_PROGRAM
            or self.state == INTERPRETER_STATE_MODECHANGE
        ):
            self.pipe(b"@NSE")
            self.laser = False
        elif self.state == INTERPRETER_STATE_RAPID:
            self.pipe(b"I")
        self.state = INTERPRETER_STATE_FINISH
        self.context.signal("interpreter;mode", self.state)

    def ensure_program_mode(self):
        if self.state == INTERPRETER_STATE_PROGRAM:
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
        self.pipe(speed_code)
        self.pipe(b"N")
        self.set_requested_directions()
        self.declare_directions()
        self.pipe(b"S1E")
        self.state = INTERPRETER_STATE_PROGRAM
        self.context.signal("interpreter;mode", self.state)

    def h_switch(self):
        if self.is_prop(STATE_X_FORWARD_LEFT):
            self.pipe(self.CODE_RIGHT)
            self.unset_prop(STATE_X_FORWARD_LEFT)
        else:
            self.pipe(self.CODE_LEFT)
            self.set_prop(STATE_X_FORWARD_LEFT)
        if self.is_prop(STATE_Y_FORWARD_TOP):
            self.context.current_y -= self.settings.raster_step
        else:
            self.context.current_y += self.settings.raster_step
        self.laser = False

    def v_switch(self):
        if self.is_prop(STATE_Y_FORWARD_TOP):
            self.pipe(self.CODE_BOTTOM)
            self.unset_prop(STATE_Y_FORWARD_TOP)
        else:
            self.pipe(self.CODE_TOP)
            self.set_prop(STATE_Y_FORWARD_TOP)
        if self.is_prop(STATE_X_FORWARD_LEFT):
            self.context.current_x -= self.settings.raster_step
        else:
            self.context.current_x += self.settings.raster_step
        self.laser = False

    def calc_home_position(self):
        x = 0
        y = 0
        bed_dim = self.context.get_context('/')
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
        self.pipe(b"IPP\n")
        old_x = self.context.current_x
        old_y = self.context.current_y
        self.context.current_x = x
        self.context.current_y = y
        self.reset_modes()
        self.state = INTERPRETER_STATE_RAPID
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

        self.context.signal("interpreter;mode", self.state)
        # self.context.signal('interpreter;position', (self.context.current_x, self.context.current_y, old_x, old_y))

    def lock_rail(self):
        self.ensure_rapid_mode()
        self.pipe(b"IS1P\n")

    def unlock_rail(self, abort=False):
        self.ensure_rapid_mode()
        self.pipe(b"IS2P\n")

    def abort(self):
        self.pipe(b"I\n")

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
                self.pipe(self.CODE_RIGHT)
                self.unset_prop(STATE_X_FORWARD_LEFT)
        else:  # Moving left
            if not self.is_prop(STATE_X_FORWARD_LEFT):
                self.pipe(self.CODE_LEFT)
                self.set_prop(STATE_X_FORWARD_LEFT)
        if dy > 0:  # Moving bottom
            if self.is_prop(STATE_Y_FORWARD_TOP):
                self.pipe(self.CODE_BOTTOM)
                self.unset_prop(STATE_Y_FORWARD_TOP)
        else:  # Moving top
            if not self.is_prop(STATE_Y_FORWARD_TOP):
                self.pipe(self.CODE_TOP)
                self.set_prop(STATE_Y_FORWARD_TOP)
        self.context.current_x += dx
        self.context.current_y += dy
        self.check_bounds()
        self.pipe(self.CODE_ANGLE + lhymicro_distance(abs(dy)))

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
        self.pipe(self.code_declare_directions())

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
        if not self.is_right or self.state != INTERPRETER_STATE_PROGRAM:
            self.pipe(self.CODE_RIGHT)
            self.set_right()
        if dx != 0:
            self.pipe(lhymicro_distance(abs(dx)))
            self.check_bounds()

    def move_left(self, dx=0):
        self.context.current_x -= abs(dx)
        if not self.is_left or self.state != INTERPRETER_STATE_PROGRAM:
            self.pipe(self.CODE_LEFT)
            self.set_left()
        if dx != 0:
            self.pipe(lhymicro_distance(abs(dx)))
            self.check_bounds()

    def move_bottom(self, dy=0):
        self.context.current_y += dy
        if not self.is_bottom or self.state != INTERPRETER_STATE_PROGRAM:
            self.pipe(self.CODE_BOTTOM)
            self.set_bottom()
        if dy != 0:
            self.pipe(lhymicro_distance(abs(dy)))
            self.check_bounds()

    def move_top(self, dy=0):
        self.context.current_y -= abs(dy)
        if not self.is_top or self.state != INTERPRETER_STATE_PROGRAM:
            self.pipe(self.CODE_TOP)
            self.set_top()
        if dy != 0:
            self.pipe(lhymicro_distance(abs(dy)))
            self.check_bounds()
