import threading
import time

from ...core.cutcode import CutCode, LaserSettings
from ..lasercommandconstants import *
from .laserspeed import LaserSpeed
from ...kernel import (
    Modifier,
    STATE_UNKNOWN,
    Job,
    Module,
    STATE_ACTIVE,
    STATE_PAUSE,
    STATE_INITIALIZE,
    STATE_BUSY,
    STATE_IDLE,
    STATE_TERMINATE,
    STATE_END,
    STATE_WAIT,
)
from ..basedevice import (
    Interpreter,
    PLOT_FINISH,
    PLOT_SETTING,
    PLOT_AXIS,
    PLOT_DIRECTION,
    PLOT_RAPID,
    PLOT_JOG,
    INTERPRETER_STATE_PROGRAM,
    INTERPRETER_STATE_RAPID,
    INTERPRETER_STATE_FINISH,
    INTERPRETER_STATE_MODECHANGE,
)
from ...core.plotplanner import PlotPlanner
from ...svgelements import Length
from ...core.zinglplotter import ZinglPlotter


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("device/Lhystudios", LhystudiosDevice)


"""
LhystudiosDevice is the backend for all Lhystudio Devices.

The most common Lhystudio device is the M2 Nano.

The device is primary composed of three main modules.

* A spooler which is a generic device object that queues up device-agnostic Lasercode commands.
* An interpreter which takes lasercode and converts converts that data into laser states and lhymicro-gl code commands.
* A controller which deals with sending the specific code objects to the hardware device, in an acceptable protocol.

"""

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


class LhystudiosDevice(Modifier):
    """
    LhystudiosDevice instance. Serves as a device instance for a lhymicro-gl based device.
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        self.device_name = "Lhystudios"
        self.device_location = "USB"
        context.current_x = 0
        context.current_y = 0
        self.current_x = 0
        self.current_y = 0

        # Device specific stuff. Fold into proper kernel commands or delegate to subclass.
        self.interpreter = None
        self.spooler = None
        self.state = STATE_UNKNOWN
        self.dx = 0
        self.dy = 0

    def __repr__(self):
        return "LhystudiosDevice()"

    @staticmethod
    def sub_register(device):
        device.register("modifier/LhymicroInterpreter", LhymicroInterpreter)
        device.register("module/LhystudioController", LhystudioController)
        device.register("module/LhystudioEmulator", LhystudioEmulator)
        device.register("load/EgvLoader", EgvLoader)

    def execute_absolute_position(self, position_x, position_y):
        x_pos = Length(position_x).value(
            ppi=1000.0, relative_length=self.context.bed_width * 39.3701
        )
        y_pos = Length(position_y).value(
            ppi=1000.0, relative_length=self.context.bed_height * 39.3701
        )

        def move():
            yield COMMAND_SET_ABSOLUTE
            yield COMMAND_MODE_RAPID
            yield COMMAND_MOVE, int(x_pos), int(y_pos)

        return move

    def execute_relative_position(self, position_x, position_y):
        x_pos = Length(position_x).value(
            ppi=1000.0, relative_length=self.context.bed_width * 39.3701
        )
        y_pos = Length(position_y).value(
            ppi=1000.0, relative_length=self.context.bed_height * 39.3701
        )

        def move():
            yield COMMAND_SET_INCREMENTAL
            yield COMMAND_MODE_RAPID
            yield COMMAND_MOVE, int(x_pos), int(y_pos)
            yield COMMAND_SET_ABSOLUTE

        return move

    def attach(self, *a, **kwargs):
        context = self.context
        kernel = self.context._kernel

        @self.context.console_command(
            "+laser", hidden=True, help="turn laser on in place"
        )
        def plus_laser(command, channel, _, args=tuple(), **kwargs):
            spooler = kernel.active_device.spooler
            spooler.job(COMMAND_LASER_ON)

        @self.context.console_command(
            "-laser", hidden=True, help="turn laser off in place"
        )
        def minus_laser(command, channel, _, args=tuple(), **kwargs):
            spooler = kernel.active_device.spooler
            spooler.job(COMMAND_LASER_ON)

        @self.context.console_command(
            ("left", "right", "up", "down"), help="<direction> <amount>"
        )
        def direction(command, channel, _, args=tuple(), **kwargs):
            active = kernel.active_device
            spooler = active.spooler

            if spooler is None:
                channel(_("Device has no spooler."))
                return
            if len(args) == 0:
                amount = "1mm"
            else:
                amount = args[0]
            max_bed_height = active.bed_height * 39.3701
            max_bed_width = active.bed_width * 39.3701
            if command.endswith("right"):
                self.dx += Length(amount).value(
                    ppi=1000.0, relative_length=max_bed_width
                )
            elif command.endswith("left"):
                self.dx -= Length(amount).value(
                    ppi=1000.0, relative_length=max_bed_width
                )
            elif command.endswith("up"):
                self.dy -= Length(amount).value(
                    ppi=1000.0, relative_length=max_bed_height
                )
            elif command.endswith("down"):
                self.dy += Length(amount).value(
                    ppi=1000.0, relative_length=max_bed_height
                )
            kernel._console_queue("jog")

        @self.context.console_command(
            "jog", hidden=True, help="executes outstanding jog buffer"
        )
        def jog(command, channel, _, args=tuple(), **kwargs):
            spooler = kernel.active_device.spooler
            idx = int(self.dx)
            idy = int(self.dy)
            if idx == 0 and idy == 0:
                return
            if spooler.job_if_idle(self.execute_relative_position(idx, idy)):
                channel(_("Position moved: %d %d") % (idx, idy))
                self.dx -= idx
                self.dy -= idy
            else:
                channel(_("Busy Error"))

        @self.context.console_command(
            ("move", "move_absolute"), help="move <x> <y>: move to position."
        )
        def move(command, channel, _, args=tuple(), **kwargs):
            spooler = kernel.active_device.spooler
            if len(args) == 2:
                if not spooler.job_if_idle(self.execute_absolute_position(*args)):
                    channel(_("Busy Error"))
            else:
                channel(_("Syntax Error"))

        @self.context.console_command("move_relative", help="move_relative <dx> <dy>")
        def move_relative(command, channel, _, args=tuple(), **kwargs):
            spooler = kernel.active_device.spooler
            if len(args) == 2:
                if not spooler.job_if_idle(self.execute_relative_position(*args)):
                    channel(_("Busy Error"))
            else:
                channel(_("Syntax Error"))

        @self.context.console_command("home", help="home the laser")
        def home(command, channel, _, args=tuple(), **kwargs):
            spooler = kernel.active_device.spooler
            spooler.job(COMMAND_HOME)

        @self.context.console_command("unlock", help="unlock the rail")
        def unlock(command, channel, _, args=tuple(), **kwargs):
            spooler = kernel.active_device.spooler
            spooler.job(COMMAND_UNLOCK)

        @self.context.console_command("lock", help="lock the rail")
        def lock(command, channel, _, args=tuple(), **kwargs):
            spooler = kernel.active_device.spooler
            spooler.job(COMMAND_LOCK)

        self.context.setting(str, "device_name", "Lhystudios")

        self.context._quit = False

        self.context.setting(int, "usb_index", -1)
        self.context.setting(int, "usb_bus", -1)
        self.context.setting(int, "usb_address", -1)
        self.context.setting(int, "usb_serial", -1)
        self.context.setting(int, "usb_version", -1)

        self.context.setting(bool, "mock", False)
        self.context.setting(int, "packet_count", 0)
        self.context.setting(int, "rejected_count", 0)
        self.context.setting(bool, "autolock", True)

        self.context.setting(str, "board", "M2")
        self.context.setting(int, "bed_width", 310)
        self.context.setting(int, "bed_height", 210)
        self.context.setting(bool, "fix_speeds", False)
        self.dx = 0
        self.dy = 0

        self.context.open_as("module/LhystudioController", "pipe")
        self.context.open_as("module/LhystudioEmulator", "emulator")
        self.context.activate("modifier/LhymicroInterpreter", self.context)
        self.context.activate("modifier/Spooler")

        context.listen("interpreter;mode", self.on_mode_change)

        self.context.signal(
            "bed_size", (self.context.bed_width, self.context.bed_height)
        )

    def detach(self, *args, **kwargs):
        self.context.unlisten("interpreter;mode", self.on_mode_change)

    def on_mode_change(self, *args):
        self.dx = 0
        self.dy = 0


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
        kernel = self.context._kernel
        _ = kernel.translation

        @self.context.console_command(
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

        @self.context.console_command("speed", help="Set Speed in Interpreter.")
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

        @self.context.console_command("power", help="Set Interpreter Power")
        def power(command, channel, _, args=tuple(), **kwargs):
            if len(args) == 0:
                channel(_("Power set at: %d pulses per inch") % self.power)
            else:
                try:
                    self.set_power(int(args[0]))
                except ValueError:
                    pass

        @self.context.console_command(
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

        self.context.interpreter = self

        self.context.setting(int, "current_x", 0)
        self.context.setting(int, "current_y", 0)

        self.context.setting(bool, "strict", False)
        self.context.setting(bool, "swap_xy", False)
        self.context.setting(bool, "flip_x", False)
        self.context.setting(bool, "flip_y", False)
        self.context.setting(bool, "home_right", False)
        self.context.setting(bool, "home_bottom", False)
        self.context.setting(int, "home_adjust_x", 0)
        self.context.setting(int, "home_adjust_y", 0)
        self.context.setting(int, "buffer_max", 900)
        self.context.setting(bool, "buffer_limit", True)
        self.context.setting(int, "current_x", 0)
        self.context.setting(int, "current_y", 0)

        self.context.setting(bool, "opt_rapid_between", True)
        self.context.setting(int, "opt_jog_mode", 0)
        self.context.setting(int, "opt_jog_minimum", 127)

        self.update_codes()

        current_x = self.context.current_x
        current_y = self.context.current_y
        self.next_x = current_x
        self.next_y = current_y
        self.max_x = current_x
        self.max_y = current_y
        self.min_x = current_x
        self.min_y = current_y
        self.start_x = current_x
        self.start_y = current_y

        self.context.register("control/Realtime Pause_Resume", self.pause_resume)
        self.context.register("control/Realtime Pause", self.pause)
        self.context.register("control/Realtime Resume", self.resume)
        self.context.register("control/Update Codes", self.update_codes)

        self.context.get_context("/").listen(
            "lifecycle;ready", self.on_interpreter_ready
        )

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
                    self.jog_absolute(x, y, mode=self.context.opt_jog_mode)
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

    def pause_resume(self, *values):
        if self.is_paused:
            self.resume(*values)
        else:
            self.pause(*values)

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
        if self.context.home_right:
            x = int(self.context.bed_width * 39.3701)
        if self.context.home_bottom:
            y = int(self.context.bed_height * 39.3701)
        return x, y

    def home(self):
        x, y = self.calc_home_position()
        self.ensure_rapid_mode()
        self.pipe(b"IPP\n")
        old_x = self.context.current_x
        old_y = self.context.current_y
        self.context.current_x = x
        self.context.current_y = y
        self.laser = False
        self.properties = 0
        self.state = INTERPRETER_STATE_RAPID
        adjust_x = self.context.home_adjust_x
        adjust_y = self.context.home_adjust_y
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


class LhystudioController(Module):
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
        Module.__init__(self, context, name, channel)
        self.state = STATE_UNKNOWN
        self.is_shutdown = False

        self._thread = None
        self._buffer = b""  # Threadsafe buffered commands to be sent to controller.
        self._realtime_buffer = (
            b""  # Threadsafe realtime buffered commands to be sent to the controller.
        )
        self._queue = b""  # Thread-unsafe additional commands to append.
        self._preempt = b""  # Thread-unsafe preempt commands to prepend to the buffer.
        self.context._buffer_size = 0
        self._queue_lock = threading.Lock()
        self._preempt_lock = threading.Lock()
        self._main_lock = threading.Lock()

        self._status = [0] * 6
        self._usb_state = -1

        self.driver = None
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

        send = context.channel("%s/send" % name)
        send.watch(self.write)
        send.__len__ = lambda: len(self._buffer) + len(self._queue)
        context.channel("%s/send_realtime" % name).watch(self.realtime_write)

    def initialize(self, *args, **kwargs):
        context = self.context

        @self.context.console_argument("filename", type=str)
        @self.context.console_command(
            "egv_import", help="Lhystudios Engrave Buffer Import. egv_import <egv_file>"
        )
        def egv_import(command, channel, _, filename, args=tuple(), **kwargs):
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
                    self.write(buffer)
                self.write(b"\n")

        @self.context.console_argument("filename", type=str)
        @self.context.console_command(
            "egv_export", help="Lhystudios Engrave Buffer Export. egv_export <egv_file>"
        )
        def egv_export(command, channel, _, filename, args=tuple(), **kwargs):
            if filename is None:
                raise SyntaxError
            with open(filename, "w") as f:
                f.write("Document type : LHYMICRO-GL file\n")
                f.write("File version: 1.0.01\n")
                f.write("Copyright: Unknown\n")
                f.write("Creator-Software: MeerK40t v0.7.0\n")
                f.write("\n")
                f.write("%0%0%0%0%\n")
                buffer = self._buffer
                buffer += self._queue
                f.write(buffer.decode("utf-8"))

        @self.context.console_command(
            "egv", help="Lhystudios Engrave Code Sender. egv <lhymicro-gl>"
        )
        def egv(command, channel, _, args=tuple(), **kwargs):
            if len(args) == 0:
                channel("Lhystudios Engrave Code Sender. egv <lhymicro-gl>")
            else:
                self.write(bytes(args[0].replace("$", "\n"), "utf8"))

        @self.context.console_command("usb_connect", help="Connect USB")
        def usb_connect(command, channel, _, args=tuple(), **kwargs):
            try:
                self.open()
            except ConnectionRefusedError:
                channel("Connection Refused.")

        @self.context.console_command("usb_disconnect", help="Disconnect USB")
        def usb_disconnect(command, channel, _, args=tuple(), **kwargs):
            if self.driver is not None:
                self.close()
            else:
                channel("Usb is not connected.")

        @self.context.console_command("start", help="Start Pipe to Controller")
        def pipe_start(command, channel, _, args=tuple(), **kwargs):
            self.update_state(STATE_ACTIVE)
            self.start()
            channel("Lhystudios Channel Started.")

        @self.context.console_command("pause", help="Pause Controller")
        def pipe_pause(command, channel, _, args=tuple(), **kwargs):
            self.update_state(STATE_PAUSE)
            self.pause()
            channel("Lhystudios Channel Paused.")

        @self.context.console_command("resume", help="Resume Controller")
        def pipe_resume(command, channel, _, args=tuple(), **kwargs):
            self.update_state(STATE_ACTIVE)
            self.start()
            channel("Lhystudios Channel Resumed.")

        @self.context.console_command("abort", help="Abort Job")
        def pipe_abort(command, channel, _, args=tuple(), **kwargs):
            self.reset()
            channel("Lhystudios Channel Aborted.")

        context.setting(int, "packet_count", 0)
        context.setting(int, "rejected_count", 0)

        context.register("control/Connect_USB", self.open)
        context.register("control/Disconnect_USB", self.close)
        context.register("control/Status Update", self.update_status)
        self.reset()

        def abort_wait():
            self.abort_waiting = True

        context.register("control/Wait Abort", abort_wait)

        def pause_k40():
            self.update_state(STATE_PAUSE)
            self.start()

        context.register("control/Pause", pause_k40)

        def resume_k40():
            self.update_state(STATE_ACTIVE)
            self.start()

        context.register("control/Resume", resume_k40)

        self.context.get_context("/").listen(
            "lifecycle;ready", self.on_interpreter_ready
        )

    def detach(self, *args, **kwargs):
        self.context.get_context("/").unlisten(
            "lifecycle;ready", self.on_interpreter_ready
        )
        self.stop()

    def on_interpreter_ready(self, *args):
        self.start()

    def finalize(self, *args, **kwargs):
        if self._thread is not None:
            self.write(b"\x18\n")

    def __repr__(self):
        return "LhystudioController()"

    def __len__(self):
        """Provides the length of the buffer of this device."""
        return len(self._buffer) + len(self._queue) + len(self._preempt)

    def open(self):
        self.pipe_channel("open()")
        if self.driver is None:
            self.detect_driver_and_open()
        else:
            # Update criteria
            self.driver.index = self.context.usb_index
            self.driver.bus = self.context.usb_bus
            self.driver.address = self.context.usb_address
            self.driver.serial = self.context.usb_serial
            self.driver.chipv = self.context.usb_version
            self.driver.open()
        if self.driver is None:
            raise ConnectionRefusedError

    def close(self):
        self.pipe_channel("close()")
        if self.driver is not None:
            self.driver.close()

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
        self._preempt = bytes_to_write + self._preempt
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
            self._thread = self.context._kernel.threaded(
                self._thread_data_send, thread_name="LhyPipe(%s)" % (self.context._path)
            )
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
        self._buffer = b""
        self._queue = b""
        self.context.signal("pipe;buffer", 0)
        self.update_state(STATE_TERMINATE)

    def reset(self):
        self.update_state(STATE_INITIALIZE)

    def stop(self):
        self.abort()
        self._thread.join()  # Wait until stop completes before continuing.

    def detect_driver_and_open(self):
        index = self.context.usb_index
        bus = self.context.usb_bus
        address = self.context.usb_address
        serial = self.context.usb_serial
        chipv = self.context.usb_version
        _ = self.usb_log._

        def state(state_value):
            self.context.signal("pipe;state", state_value)

        try:
            from ..ch341libusbdriver import CH341Driver

            self.driver = driver = CH341Driver(
                index=index,
                bus=bus,
                address=address,
                serial=serial,
                chipv=chipv,
                channel=self.usb_log,
                state=state,
            )
            driver.open()
            chip_version = driver.get_chip_version()
            self.usb_log(_("CH341 Chip Version: %d") % chip_version)
            self.context.signal("pipe;chipv", chip_version)
            self.usb_log(_("Driver Detected: LibUsb"))
            state("STATE_CONNECTED")
            self.usb_log(_("Device Connected.\n"))
            return
        except ConnectionRefusedError:
            self.driver = None
        except ImportError:
            self.usb_log(_("PyUsb is not installed. Skipping."))

        try:
            from ..ch341windlldriver import CH341Driver

            self.driver = driver = CH341Driver(
                index=index,
                bus=bus,
                address=address,
                serial=serial,
                chipv=chipv,
                channel=self.usb_log,
                state=state,
            )
            driver.open()
            chip_version = driver.get_chip_version()
            self.usb_log(_("CH341 Chip Version: %d") % chip_version)
            self.context.signal("pipe;chipv", chip_version)
            self.usb_log(_("Driver Detected: CH341"))
            state("STATE_CONNECTED")
            self.usb_log(_("Device Connected.\n"))
            return
        except ConnectionRefusedError:
            self.driver = None
        except ImportError:
            self.usb_log(_("No Windll interfacing. Skipping."))

    def update_state(self, state):
        self.state = state
        if self.context is not None:
            self.context.signal("pipe;thread", self.state)

    def update_buffer(self):
        if self.context is not None:
            self.context._buffer_size = (
                len(self._realtime_buffer) + len(self._buffer) + len(self._queue)
            )
            self.context.signal("pipe;buffer", self.context._buffer_size)

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
            self._queue = b""
            self._queue_lock.release()
            self.update_buffer()

        if len(self._preempt):  # check for and prepend preempt
            self._preempt_lock.acquire(True)
            self._realtime_buffer += self._preempt
            self._preempt = b""
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
        packet = buffer[:length]

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
        if self.context.mock:
            _ = self.usb_log._
            self.usb_log(_("Using Mock Driver."))
        else:
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
        if self.context.mock:
            time.sleep(0.04)
        else:
            packet = b"\x00" + packet + bytes([onewire_crc_lookup(packet)])
            self.driver.write(packet)
        self.update_packet(packet)
        self.pre_ok = False

    def update_status(self):
        if self.context.mock:
            from random import randint

            if randint(0, 500) == 0:
                self._status = [255, STATUS_ERROR, 0, 0, 0, 1]
            else:
                self._status = [255, STATUS_OK, 0, 0, 0, 1]
            time.sleep(0.01)
        else:
            self._status = self.driver.get_status()
        if self.context is not None:
            self.context.signal("pipe;status", self._status)
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
            if self.context.mock:  # Mock controller
                self._status = [255, STATUS_FINISH, 0, 0, 0, 1]
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


class LhystudioEmulator(Module):
    def __init__(self, context, path):
        Module.__init__(self, context, path)
        self.board = "M2"
        self.header_skipped = False
        self.count_lines = 0
        self.count_flag = 0
        self.settings = LaserSettings()
        self.cutcode = CutCode()

        self.small_jump = True
        self.speed_code = None

        self.x = 0.0
        self.y = 0.0
        self.number_value = None
        self.distance_x = 0
        self.distance_y = 0

        self.filename = ""

        self.left = False
        self.top = False
        self.x_on = False
        self.y_on = False
        self.horizontal_major = False
        self.context.setting(bool, "fix_speeds", False)
        self.process = self.state_default

        send = context.channel("pipe/usb_send")
        send.watch(self.write_packet)

        self.channel = self.context.channel("lhy")

    def __repr__(self):
        return "LhystudioEmulator(%s, %d cuts)" % (self.name, len(self.cutcode))

    def generate(self):
        for cutobject in self.cutcode:
            yield COMMAND_PLOT, cutobject
        yield COMMAND_PLOT_START

    def new_file(self):
        self.header_skipped = False
        self.count_flag = 0
        self.count_lines = 0

    def header_write(self, data):
        if self.header_skipped:
            self.write(data)
        for i in range(len(data)):
            c = data[i]
            if c == b"\n":
                self.count_lines += 1
            elif c == b"%":
                self.count_flag += 1

            if self.count_lines >= 3 and self.count_flag >= 5:
                self.header_skipped = True
                self.write(data[i:])
                break

    def append_distance(self, amount):
        if self.x_on:
            self.distance_x += amount
        if self.y_on:
            self.distance_y += amount

    def write_packet(self, packet):
        self.write(packet[1:31])

    def write(self, data):
        for b in data:
            c = chr(b)
            if c == "I":
                self.process = self.state_default
                continue
            self.process(b, c)

    def state_finish(self, b, c):
        if c in "NSEF":
            return
        self.channel("Finish State Unknown: %s" % c)

    def state_reset(self, b, c):
        if c in "@NSE":
            return
        else:
            self.process = self.state_default
            self.process(b, c)

    def state_jog(self, b, c):
        if c in "N":
            return
        else:
            self.process = self.state_default
            self.process(b, c)

    def state_pop(self, b, c):
        if c == "P":
            # Home sequence triggered.
            self.context.signal("interpreter;position", (self.x, self.y, 0, 0))
            self.x = 0
            self.y = 0
            self.process = self.state_default
            return
        elif c == "F":
            return
        else:
            self.channel("Finish State Unknown: %s" % c)

    def state_speed(self, b, c):
        if c in "GCV01234567890":
            self.speed_code += c
            return
        speed = LaserSpeed(self.speed_code, fix_speeds=self.context.fix_speeds)
        self.settings.steps = speed.raster_step
        self.settings.speed = speed.speed
        self.channel("Setting Speed: %f" % self.settings.speed)
        self.speed_code = None

        self.process = self.state_default
        self.process(b, c)

    def state_switch(self, b, c):
        if c in "S012":
            if c == "1":
                self.horizontal_major = self.x_on
                self.channel("Setting Axis.")
            return
        self.process = self.state_default
        self.process(b, c)

    def state_pause(self, b, c):
        if c in "NF":
            return
        if c == "P":
            self.process = self.state_resume
        else:
            self.process = self.state_compact
            self.process(b, c)

    def state_resume(self, b, c):
        if c in "NF":
            return
        self.process = self.state_compact
        self.process(b, c)

    def state_pad(self, b, c):
        if c == "F":
            return

    def state_execute(self, b, c):
        self.process = self.state_compact

    def state_distance(self, b, c):
        if c == "|":
            self.append_distance(25)
            self.small_jump = True
            return True
        elif ord("0") <= b <= ord("9"):
            if self.number_value is None:
                self.number_value = c
            else:
                self.number_value += c
            if len(self.number_value) >= 3:
                self.append_distance(int(self.number_value))
                self.number_value = None
            return True
        elif ord("a") <= b <= ord("y"):
            self.append_distance(b + 1 - ord("a"))
        elif c == "z":
            self.append_distance(26 if self.small_jump else 255)
        else:
            self.small_jump = False
            return False
        self.small_jump = False
        return True

    def execute_distance(self):
        if self.distance_x != 0 or self.distance_y != 0:
            dx = self.distance_x
            dy = self.distance_y
            if self.left:
                dx = -dx
            if self.top:
                dy = -dy
            self.distance_x = 0
            self.distance_y = 0

            self.context.signal(
                "interpreter;position", (self.x, self.y, self.x + dx, self.y + dy)
            )
            self.x += dx
            self.y += dy
            self.channel("Moving (%d %d) now at %d %d" % (dx, dy, self.x, self.y))

    def state_compact(self, b, c):
        if self.state_distance(b, c):
            return
        self.execute_distance()

        if c == "F":
            self.channel("Finish")
            self.process = self.state_finish
            self.process(b, c)
            return
        elif c == "@":
            self.channel("Reset")
            self.process = self.state_reset
            self.process(b, c)
            return
        elif c == "P":
            self.channel("Pause")
            self.process = self.state_pause
        elif c == "N":
            self.channel("Jog")
            self.process = self.state_jog
            self.process(b, c)
        elif c == "S":
            self.channel("Switch")
            self.process = self.state_switch
            self.process(b, c)
        elif c == "E":
            self.channel("Compact-Compact")
            self.process = self.state_execute
            self.process(b, c)
        elif c == "B":
            self.left = False
            self.x_on = True
            self.y_on = False
        elif c == "T":
            self.left = True
            self.x_on = True
            self.y_on = False
        elif c == "R":
            self.top = False
            self.x_on = False
            self.y_on = True
        elif c == "L":
            self.top = True
            self.x_on = False
            self.y_on = True
        elif c == "M":
            self.x_on = True
            self.y_on = True

    def state_default(self, b, c):
        if self.state_distance(b, c):
            return

        # Execute Commands.
        if c == "N":
            self.execute_distance()
        elif c == "F":
            self.channel("Finish")
            self.process = self.state_finish
            self.process(b, c)
            return
        elif c == "P":
            self.channel("Popping")
            self.process = self.state_pop
            return
        elif c in "CVG":
            self.channel("Speedcode")
            self.speed_code = ""
            self.process = self.state_speed
            self.process(b, c)
            return
        elif c == "S":
            self.execute_distance()
            self.channel("Switch")
            self.process = self.state_switch
            self.process(b, c)
        elif c == "E":
            self.channel("Compact")
            self.process = self.state_execute
            self.process(b, c)
        elif c == "B":
            self.left = False
            self.x_on = True
            self.y_on = False
        elif c == "T":
            self.left = True
            self.x_on = True
            self.y_on = False
        elif c == "R":
            self.top = False
            self.x_on = False
            self.y_on = True
        elif c == "L":
            self.top = True
            self.x_on = False
            self.y_on = True


class EgvLoader:
    @staticmethod
    def load_types():
        yield "Engrave Files", ("egv",), "application/x-egv"

    @staticmethod
    def load(kernel, pathname, **kwargs):
        import os

        basename = os.path.basename(pathname)
        with open(pathname, "rb") as f:
            lhymicroemulator = kernel.get_context("/").open_as(
                "module/LhystudiosEmulator", basename
            )
            lhymicroemulator.write_header(f.read())
            return [lhymicroemulator.cutcode], None, None, pathname, basename
