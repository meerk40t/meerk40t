import threading

from CH341DriverBase import *
from Kernel import *
from LaserSpeed import LaserSpeed
from svgelements import *
from zinglplotter import ZinglPlotter

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

DIRECTION_FLAG_LEFT = 1  # Direction is flagged left rather than right.
DIRECTION_FLAG_TOP = 2  # Direction is flagged top rather than bottom.
DIRECTION_FLAG_X = 4  # X-stepper motor is engaged.
DIRECTION_FLAG_Y = 8  # Y-stepper motor is engaged.


class LhystudiosDevice(Modifier):
    """
    LhystudiosDevice instance. Serves as a device instance for a lhymicro-gl based device.
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        self.device_name = "Lhystudios"
        self.device_location = "USB"
        self.current_x = 0
        self.current_y = 0

        # Device specific stuff. Fold into proper kernel commands or delegate to subclass.
        self.interpreter = None
        self.spooler = None
        self.state = STATE_UNKNOWN

    def __repr__(self):
        return "LhystudiosDevice()"

    @staticmethod
    def sub_register(device):
        device.register('modifier/LhymicroInterpreter', LhymicroInterpreter)
        device.register('modifier/LhystudioController', LhystudioController)
        device.register('load/EgvLoader', EgvLoader)

    def execute_absolute_position(self, position_x, position_y):
        x_pos = Length(position_x).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
        y_pos = Length(position_y).value(ppi=1000.0, relative_length=self.context.bed_height * 39.3701)

        def move():
            yield COMMAND_SET_ABSOLUTE
            yield COMMAND_MODE_RAPID
            yield COMMAND_MOVE, int(x_pos), int(y_pos)

        return move

    def execute_relative_position(self, position_x, position_y):
        x_pos = Length(position_x).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
        y_pos = Length(position_y).value(ppi=1000.0, relative_length=self.context.bed_height * 39.3701)

        def move():
            yield COMMAND_SET_INCREMENTAL
            yield COMMAND_MODE_RAPID
            yield COMMAND_MOVE, int(x_pos), int(y_pos)
            yield COMMAND_SET_ABSOLUTE

        return move

    def attach(self, channel=None):
        context = self.context
        kernel = self.context._kernel
        _ = kernel.translation
        spooler = self.spooler

        def plus_laser(command, *args):
            kernel.active.spooler.job(COMMAND_LASER_ON)
        kernel.register('command/+laser', plus_laser)

        def minus_laser(command, *args):
            kernel.active.spooler.job(COMMAND_LASER_ON)
        kernel.register('command/-laser', minus_laser)

        def direction(command, *args):
            spooler = kernel.active.spooler
            active = kernel.active
            if spooler is None:
                yield _('Device has no spooler.')
                return
            if len(args) == 1:
                max_bed_height = active.bed_height * 39.3701
                max_bed_width = active.bed_width * 39.3701
                direction = command
                amount = args[0]
                if direction == 'right':
                    self.dx += Length(amount).value(ppi=1000.0, relative_length=max_bed_width)
                elif direction == 'left':
                    self.dx -= Length(amount).value(ppi=1000.0, relative_length=max_bed_width)
                elif direction == 'up':
                    self.dy -= Length(amount).value(ppi=1000.0, relative_length=max_bed_height)
                elif direction == 'down':
                    self.dy += Length(amount).value(ppi=1000.0, relative_length=max_bed_height)
                kernel.queue_command('jog')
        kernel.register('command/right', direction)
        kernel.register('command/left', direction)
        kernel.register('command/up', direction)
        kernel.register('command/down', direction)

        def jog(command, *args):
            if spooler is None:
                yield _('Device has no spooler.')
                return
            idx = int(self.dx)
            idy = int(self.dy)
            if idx == 0 and idy == 0:
                return
            if spooler.job_if_idle(self.execute_relative_position(idx, idy)):
                yield _('Position moved: %d %d') % (idx, idy)
                self.dx -= idx
                self.dy -= idy
            else:
                yield _('Busy Error')
        kernel.register('command/jog', jog)

        def move(command, *args):
            if spooler is None:
                yield _('Device has no spooler.')
                return
            if len(args) == 2:
                if not spooler.job_if_idle(self.execute_absolute_position(*args)):
                    yield _('Busy Error')
            else:
                yield _('Syntax Error')
        kernel.register('command/move', move)
        kernel.register('command/move_absolute', move)

        def move_relative(command, *args):
            if spooler is None:
                yield _('Device has no spooler.')
                return
            if len(args) == 2:
                if not spooler.job_if_idle(self.execute_relative_position(*args)):
                    yield _('Busy Error')
            else:
                yield _('Syntax Error')
        kernel.register('command/move_relative', move_relative)

        def home(command, *args):
            if spooler is None:
                yield _('Device has no spooler.')
                return
            spooler.job(COMMAND_HOME)
        kernel.register('command/home', home)

        def unlock(command, *args):
            if spooler is None:
                yield _('Device has no spooler.')
                return
            spooler.job(COMMAND_UNLOCK)
        kernel.register('command/unlock', unlock)

        def lock(command, *args):
            if spooler is None:
                yield _('Device has no spooler.')
                return
            spooler.job(COMMAND_LOCK)
        kernel.register('command/lock', lock)

        self.context.activate('modifier/LhystudioController')
        self.context.activate('modifier/LhymicroInterpreter', self.context)
        self.context.activate('modifier/Spooler')

        self.context.setting(str, 'device_name', 'Lhystudios')

        self.context.setting(bool, 'quit', False)
        self.context.quit = False

        self.context.setting(int, 'usb_index', -1)
        self.context.setting(int, 'usb_bus', -1)
        self.context.setting(int, 'usb_address', -1)
        self.context.setting(int, 'usb_serial', -1)
        self.context.setting(int, 'usb_version', -1)

        self.context.setting(bool, 'mock', False)
        self.context.setting(int, 'packet_count', 0)
        self.context.setting(int, 'rejected_count', 0)
        self.context.setting(bool, "autolock", True)
        self.context.setting(bool, "autohome", False)
        self.context.setting(bool, "autobeep", True)

        self.context.setting(str, "board", 'M2')
        self.context.setting(bool, "rotary", False)
        self.context.setting(float, "scale_x", 1.0)
        self.context.setting(float, "scale_y", 1.0)
        self.context.setting(int, "bed_width", 320)
        self.context.setting(int, "bed_height", 220)
        self.dx = 0
        self.dy = 0
        context.listen('interpreter;mode', self.on_mode_change)

        self.context.signal('bed_size', (self.context.bed_width, self.context.bed_height))


distance_lookup = [
    b'',
    b'a', b'b', b'c', b'd', b'e', b'f', b'g', b'h', b'i', b'j', b'k', b'l', b'm',
    b'n', b'o', b'p', b'q', b'r', b's', b't', b'u', b'v', b'w', b'x', b'y',
    b'|a', b'|b', b'|c', b'|d', b'|e', b'|f', b'|g', b'|h', b'|i', b'|j', b'|k', b'|l', b'|m',
    b'|n', b'|o', b'|p', b'|q', b'|r', b'|s', b'|t', b'|u', b'|v', b'|w', b'|x', b'|y', b'|z'
]


def lhymicro_distance(v):
    dist = b''
    if v >= 255:
        zs = int(v / 255)
        v %= 255
        dist += (b'z' * zs)
    if v >= 52:
        return dist + b'%03d' % v
    return dist + distance_lookup[v]


class LhymicroInterpreter(Interpreter, Job, Modifier):
    """
    LhymicroInterpreter provides Lhystudio specific coding for elements and sends it to the backend
    to write to the usb.
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        Interpreter.__init__(self, context=context)
        Job.__init__(self, name="Lhystudios-spool", process=self.process_spool, interval=0.01)
        self.CODE_RIGHT = b'B'
        self.CODE_LEFT = b'T'
        self.CODE_TOP = b'L'
        self.CODE_BOTTOM = b'R'
        self.CODE_ANGLE = b'M'
        self.CODE_LASER_ON = b'D'
        self.CODE_LASER_OFF = b'U'

        self.plot = None
        self.group_modulation = False

        self.next_x = None
        self.next_y = None
        self.max_x = None
        self.max_y = None
        self.min_x = None
        self.min_y = None
        self.start_x = None
        self.start_y = None
        self.is_paused = False

    def attach(self, channel=None):
        kernel = self.context._kernel
        _ = kernel.translation

        def pulse(command, *args):
            if len(args) == 0:
                yield _('Must specify a pulse time in milliseconds.')
                return
            try:
                value = float(args[0]) / 1000.0
            except ValueError:
                yield _('"%s" not a valid pulse time in milliseconds') % (args[0])
                return
            if value > 1.0:
                yield _('"%s" exceeds 1 second limit to fire a standing laser.') % (args[0])
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
                yield _('Pulse laser for %f milliseconds') % (value * 1000.0)
            else:
                yield _('Pulse laser failed: Busy')
            return
        kernel.register('command/pulse', pulse)

        def speed(command, *args):
            if len(args) == 0:
                yield _('Speed set at: %f mm/s') % self.speed
                return
            inc = False
            percent = False
            speed = args[0]
            if speed == "inc":
                speed = args[1]
                inc = True
            if speed.endswith('%'):
                speed = speed[:-1]
                percent = True
            try:
                s = float(speed)
            except ValueError:
                yield _('Not a valid speed or percent.')
                return
            if percent and inc:
                s = self.speed + self.speed * (s / 100.0)
            elif inc:
                s += self.speed
            elif percent:
                s = self.speed * (s / 100.0)
            self.set_speed(s)
            yield _('Speed set at: %f mm/s') % self.speed
        kernel.register('command/speed', speed)

        def power(command, *args):
            if len(args) == 0:
                yield _('Power set at: %d pulses per inch') % self.power
            else:
                try:
                    self.set_power(int(args[0]))
                except ValueError:
                    pass
        kernel.register('command/power', power)

        def acceleration(command, *args):
            if len(args) == 0:
                if self.acceleration is None:
                    yield _('Acceleration is set to default.')
                else:
                    yield _('Acceleration: %d') % self.acceleration

            else:
                try:
                    v = int(args[0])
                    if v not in (1, 2, 3, 4):
                        self.set_acceleration(None)
                        yield _('Acceleration is set to default.')
                        return
                    self.set_acceleration(v)
                    yield _('Acceleration: %d') % self.acceleration
                except ValueError:
                    yield _('Invalid Acceleration [1-4].')
                    return
        kernel.register('command/acceleration', acceleration)

        self.context.interpreter = self

        self.context.setting(int, 'current_x', 0)
        self.context.setting(int, 'current_y', 0)

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

        self.context.register('control/Realtime Pause_Resume', self.pause_resume)
        self.context.register('control/Realtime Pause', self.pause)
        self.context.register('control/Realtime Resume', self.resume)
        self.context.register('control/Update Codes', self.update_codes)
        self.context.schedule(self)

    def __repr__(self):
        return "LhymicroInterpreter()"

    def update_codes(self):
        if not self.context.swap_xy:
            self.CODE_RIGHT = b'B'
            self.CODE_LEFT = b'T'
            self.CODE_TOP = b'L'
            self.CODE_BOTTOM = b'R'
        else:
            self.CODE_RIGHT = b'R'
            self.CODE_LEFT = b'L'
            self.CODE_TOP = b'T'
            self.CODE_BOTTOM = b'B'
        if self.context.flip_x:
            q = self.CODE_LEFT
            self.CODE_LEFT = self.CODE_RIGHT
            self.CODE_RIGHT = q
        if self.context.flip_y:
            q = self.CODE_TOP
            self.CODE_TOP = self.CODE_BOTTOM
            self.CODE_BOTTOM = q

    def hold(self):
        """Holds the data flow if needed."""
        if self.extra_hold is not None:
            # Has an additional hold requirement.
            if self.extra_hold():
                return True
            else:
                self.extra_hold = None
        return self.context.buffer_limit and len(self.pipe) > self.context.buffer_max

    def execute(self):
        if self.hold():
            return
        while self.plot is not None:
            if self.hold():
                return
            sx = self.context.current_x
            sy = self.context.current_y
            try:
                x, y, on = next(self.plot)
                dx = x - sx
                dy = y - sy
                if self.raster_step != 0:
                    if self.is_prop(DIRECTION_FLAG_X):
                        if dy != 0:
                            if self.is_prop(DIRECTION_FLAG_TOP):
                                if abs(dy) > self.raster_step:
                                    self.ensure_finished_mode()
                                    self.move_relative(0, dy + self.raster_step)
                                    self.set_prop(DIRECTION_FLAG_X)
                                    self.unset_prop(DIRECTION_FLAG_Y)
                                    self.ensure_program_mode()
                                self.h_switch()
                            else:
                                if abs(dy) > self.raster_step:
                                    self.ensure_finished_mode()
                                    self.move_relative(0, dy - self.raster_step)
                                    self.set_prop(DIRECTION_FLAG_X)
                                    self.unset_prop(DIRECTION_FLAG_Y)
                                    self.ensure_program_mode()
                                self.h_switch()
                    elif self.is_prop(DIRECTION_FLAG_Y):
                        if dx != 0:
                            if self.is_prop(DIRECTION_FLAG_LEFT):
                                if abs(dx) > self.raster_step:
                                    self.ensure_finished_mode()
                                    self.move_relative(dx + self.raster_step, 0)
                                    self.set_prop(DIRECTION_FLAG_Y)
                                    self.unset_prop(DIRECTION_FLAG_X)
                                    self.ensure_program_mode()
                                self.v_switch()
                            else:
                                if abs(dx) > self.raster_step:
                                    self.ensure_finished_mode()
                                    self.move_relative(dx - self.raster_step, 0)
                                    self.set_prop(DIRECTION_FLAG_Y)
                                    self.unset_prop(DIRECTION_FLAG_X)
                                    self.ensure_program_mode()
                                self.v_switch()
                self.goto_octent_abs(x, y, on)
            except StopIteration:
                self.plot = None
                return
            except RuntimeError:
                self.plot = None
                return
        Interpreter.execute(self)

    def plot_path(self, path):
        """
        Set the self.plot object with the given path.

        If path is an SVGImage the path is the outline.

        :param path: svg object
        :return:
        """
        if isinstance(path, Shape) and not isinstance(path, Path):
            path = Path(path)
        if isinstance(path, SVGImage):
            bounds = path.bbox()
            p = Path()
            p.move([(bounds[0], bounds[1]),
                    (bounds[0], bounds[3]),
                    (bounds[2], bounds[1]),
                    (bounds[2], bounds[3])])
            self.plot_planner.add_path(p)
            self.plot = self.plot_planner
            return
        if len(path) == 0:
            return
        first_point = path.first_point
        self.move_absolute(first_point[0], first_point[1])
        self.plot_planner.add_path(path)
        self.plot = self.plot_planner

    def plot_raster(self, raster):
        self.plot_planner.add_plot(raster.plot())
        self.plot = self.plot_planner

    def set_directions(self, left, top, x_dir, y_dir):
        # Left, Top, X-Momentum, Y-Momentum
        self.properties = 0
        if left:
            self.set_prop(DIRECTION_FLAG_LEFT)
        if top:
            self.set_prop(DIRECTION_FLAG_TOP)
        if x_dir:
            self.set_prop(DIRECTION_FLAG_X)
        if y_dir:
            self.set_prop(DIRECTION_FLAG_Y)

    def pause_resume(self, *values):
        if self.is_paused:
            self.resume(*values)
        else:
            self.pause(*values)

    def pause(self, *values):
        self.pipe.realtime_write(b'PN!\n')
        self.is_paused = True

    def resume(self, *values):
        self.pipe.realtime_write(b'PN&\n')
        self.is_paused = False

    def reset(self):
        Interpreter.reset(self)
        self.pipe._buffer = b''
        self.pipe._queue = b''
        self.context.signal('pipe;buffer', 0)
        self.plot = None
        self.pipe.realtime_write(b'I*\n')
        self.laser = False
        self.properties = 0
        self.state = INTERPRETER_STATE_RAPID
        self.context.signal('interpreter;mode', self.state)
        self.is_paused = False

    def cut(self, x, y):
        self.goto(x, y, True)

    def cut_absolute(self, x, y):
        self.goto_absolute(x, y, True)

    def cut_relative(self, x, y):
        self.goto_relative(x, y, True)

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
            self.pipe.write(b'I')
            if dx != 0:
                self.goto_x(dx)
            if dy != 0:
                self.goto_y(dy)
            self.pipe.write(b'S1P\n')
            if not self.context.autolock:
                self.pipe.write(b'IS2P\n')
        elif self.state == INTERPRETER_STATE_PROGRAM:
            mx = 0
            my = 0
            for x, y, on in self.plot_planner.plot_cut(ZinglPlotter.plot_line(0, 0, dx, dy), cut, 0, 0):
                self.goto_octent(x - mx, y - my, on)
                mx = x
                my = y
        elif self.state == INTERPRETER_STATE_FINISH:
            if dx != 0:
                self.goto_x(dx)
            if dy != 0:
                self.goto_y(dy)
            self.pipe.write(b'N')
        self.check_bounds()
        self.context.signal('interpreter;position', (self.context.current_x, self.context.current_y,
                                                     self.context.current_x - dx, self.context.current_y - dy))

    def goto_octent_abs(self, x, y, on):
        dx = x - self.context.current_x
        dy = y - self.context.current_y
        self.goto_octent(dx, dy, on)

    def goto_octent(self, dx, dy, on):
        if on:
            self.laser_on()
        else:
            self.laser_off()
        if abs(dx) == abs(dy):
            if dx != 0:
                self.goto_angle(dx, dy)
        elif dx != 0:
            self.goto_x(dx)
        else:
            self.goto_y(dy)
        self.context.signal('interpreter;position', (self.context.current_x, self.context.current_y,
                                                     self.context.current_x - dx, self.context.current_y - dy))

    def set_speed(self, speed=None):
        change = False
        if self.speed != speed:
            change = True
            self.speed = speed
        if not change:
            return
        if self.state == INTERPRETER_STATE_PROGRAM:
            # Compact mode means it's currently slowed. To make the speed have an effect, compact must be exited.
            self.fly_switch_speed()

    def set_d_ratio(self, d_ratio=None):
        change = False
        if self.d_ratio != d_ratio:
            change = True
            self.d_ratio = d_ratio
        if not change:
            return
        if self.state == INTERPRETER_STATE_PROGRAM:
            # Compact mode means it's currently slowed. To make the speed have an effect, compact must be exited.
            self.fly_switch_speed()

    def set_acceleration(self, accel=None):
        change = False
        if self.acceleration != accel:
            change = True
            self.acceleration = accel
        if not change:
            return
        if self.state == INTERPRETER_STATE_PROGRAM:
            # Compact mode means it's currently slowed. To make the change have an effect, compact must be exited.
            self.fly_switch_speed()

    def set_step(self, step=None):
        change = False
        if self.raster_step != step:
            change = True
            self.raster_step = step
        if not change:
            return
        if self.state == INTERPRETER_STATE_PROGRAM:
            # Compact mode means it's currently slowed. To make the speed have an effect, compact must be exited.
            self.fly_switch_speed()

    def laser_off(self):
        if not self.laser:
            return False
        controller = self.pipe
        if self.state == INTERPRETER_STATE_RAPID:
            controller.write(b'I')
            controller.write(self.CODE_LASER_OFF)
            controller.write(b'S1P\n')
            if not self.context.autolock:
                controller.write(b'IS2P\n')
        elif self.state == INTERPRETER_STATE_PROGRAM:
            controller.write(self.CODE_LASER_OFF)
        elif self.state == INTERPRETER_STATE_FINISH:
            controller.write(self.CODE_LASER_OFF)
            controller.write(b'N')
        self.laser = False
        return True

    def laser_on(self):
        if self.laser:
            return False
        controller = self.pipe
        if self.state == INTERPRETER_STATE_RAPID:
            controller.write(b'I')
            controller.write(self.CODE_LASER_ON)
            controller.write(b'S1P\n')
            if not self.context.autolock:
                controller.write(b'IS2P\n')
        elif self.state == INTERPRETER_STATE_PROGRAM:
            controller.write(self.CODE_LASER_ON)
        elif self.state == INTERPRETER_STATE_FINISH:
            controller.write(self.CODE_LASER_ON)
            controller.write(b'N')
        self.laser = True
        return True

    def ensure_rapid_mode(self):
        if self.state == INTERPRETER_STATE_RAPID:
            return
        controller = self.pipe
        if self.state == INTERPRETER_STATE_FINISH:
            controller.write(b'S1P\n')
            if not self.context.autolock:
                controller.write(b'IS2P\n')
        elif self.state == INTERPRETER_STATE_PROGRAM:
            controller.write(b'FNSE-\n')
            self.reset_modes()
        self.state = INTERPRETER_STATE_RAPID
        self.context.signal('interpreter;mode', self.state)

    def fly_switch_speed(self):
        controller = self.pipe
        switch = b'@NSE'
        speed_code = LaserSpeed(
            self.context.board,
            self.speed,
            self.raster_step,
            d_ratio=self.d_ratio,
            acceleration=self.acceleration,
            fix_limit=True,
            fix_lows=True,
            fix_speeds=False,
            raster_horizontal=True).speedcode
        try:
            speed_code = bytes(speed_code)
        except TypeError:
            speed_code = bytes(speed_code, 'utf8')
        switch += speed_code
        switch += b'N'
        switch += self.code_declare_directions()
        switch += b'S1E'
        controller.write(switch)

    def ensure_finished_mode(self):
        if self.state == INTERPRETER_STATE_FINISH:
            return
        controller = self.pipe
        if self.state == INTERPRETER_STATE_PROGRAM:
            controller.write(b'@NSE')
            self.reset_modes()
        elif self.state == INTERPRETER_STATE_RAPID:
            controller.write(b'I')
        self.state = INTERPRETER_STATE_FINISH
        self.context.signal('interpreter;mode', self.state)

    def ensure_program_mode(self):
        if self.state == INTERPRETER_STATE_PROGRAM:
            return
        controller = self.pipe
        self.ensure_finished_mode()

        speed_code = LaserSpeed(
            self.context.board,
            self.speed,
            self.raster_step,
            d_ratio=self.d_ratio,
            acceleration=self.acceleration,
            fix_limit=True,
            fix_lows=True,
            fix_speeds=False,
            raster_horizontal=True).speedcode
        try:
            speed_code = bytes(speed_code)
        except TypeError:
            speed_code = bytes(speed_code, 'utf8')
        controller.write(speed_code)
        controller.write(b'N')
        self.declare_directions()
        controller.write(b'S1E')
        self.state = INTERPRETER_STATE_PROGRAM
        self.context.signal('interpreter;mode', self.state)

    def h_switch(self):
        controller = self.pipe
        if self.is_prop(DIRECTION_FLAG_LEFT):
            controller.write(self.CODE_RIGHT)
            self.unset_prop(DIRECTION_FLAG_LEFT)
        else:
            controller.write(self.CODE_LEFT)
            self.set_prop(DIRECTION_FLAG_LEFT)
        if self.is_prop(DIRECTION_FLAG_TOP):
            self.context.current_y -= self.raster_step
        else:
            self.context.current_y += self.raster_step
        self.laser = False

    def v_switch(self):
        controller = self.pipe
        if self.is_prop(DIRECTION_FLAG_TOP):
            controller.write(self.CODE_BOTTOM)
            self.unset_prop(DIRECTION_FLAG_TOP)
        else:
            controller.write(self.CODE_TOP)
            self.set_prop(DIRECTION_FLAG_TOP)
        if self.is_prop(DIRECTION_FLAG_LEFT):
            self.context.current_x -= self.raster_step
        else:
            self.context.current_x += self.raster_step
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
        controller = self.pipe
        self.ensure_rapid_mode()
        controller.write(b'IPP\n')
        old_x = self.context.current_x
        old_y = self.context.current_y
        self.context.current_x = x
        self.context.current_y = y
        self.reset_modes()
        self.state = INTERPRETER_STATE_RAPID
        adjust_x = self.context.home_adjust_x
        adjust_y = self.context.home_adjust_y
        if adjust_x != 0 or adjust_y != 0:
            # Perform post home adjustment.
            self.move_relative(adjust_x, adjust_y)
            # Erase adjustment
            self.context.current_x = x
            self.context.current_y = y

        self.context.signal('interpreter;mode', self.state)
        self.context.signal('interpreter;position', (self.context.current_x, self.context.current_y, old_x, old_y))

    def lock_rail(self):
        controller = self.pipe
        self.ensure_rapid_mode()
        controller.write(b'IS1P\n')

    def unlock_rail(self, abort=False):
        controller = self.pipe
        self.ensure_rapid_mode()
        controller.write(b'IS2P\n')

    def abort(self):
        controller = self.pipe
        controller.write(b'I\n')

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
        controller = self.pipe
        if abs(dx) != abs(dy):
            raise ValueError('abs(dx) must equal abs(dy)')
        self.set_prop(DIRECTION_FLAG_X)  # Set both on
        self.set_prop(DIRECTION_FLAG_Y)
        if dx > 0:  # Moving right
            if self.is_prop(DIRECTION_FLAG_LEFT):
                controller.write(self.CODE_RIGHT)
                self.unset_prop(DIRECTION_FLAG_LEFT)
        else:  # Moving left
            if not self.is_prop(DIRECTION_FLAG_LEFT):
                controller.write(self.CODE_LEFT)
                self.set_prop(DIRECTION_FLAG_LEFT)
        if dy > 0:  # Moving bottom
            if self.is_prop(DIRECTION_FLAG_TOP):
                controller.write(self.CODE_BOTTOM)
                self.unset_prop(DIRECTION_FLAG_TOP)
        else:  # Moving top
            if not self.is_prop(DIRECTION_FLAG_TOP):
                controller.write(self.CODE_TOP)
                self.set_prop(DIRECTION_FLAG_TOP)
        self.context.current_x += dx
        self.context.current_y += dy
        self.check_bounds()
        controller.write(self.CODE_ANGLE + lhymicro_distance(abs(dy)))

    def declare_directions(self):
        """Declare direction declares raster directions of left, top, with the primary momentum direction going last.
        You cannot declare a diagonal direction."""
        controller = self.pipe
        controller.write(self.code_declare_directions())

    def code_declare_directions(self):
        if self.is_prop(DIRECTION_FLAG_LEFT):
            x_dir = self.CODE_LEFT
        else:
            x_dir = self.CODE_RIGHT
        if self.is_prop(DIRECTION_FLAG_TOP):
            y_dir = self.CODE_TOP
        else:
            y_dir = self.CODE_BOTTOM
        if self.is_prop(DIRECTION_FLAG_X):  # FLAG_Y is assumed to be !FLAG_X
            return y_dir + x_dir
        else:
            return x_dir + y_dir

    @property
    def is_left(self):
        return self.is_prop(DIRECTION_FLAG_X) and \
               not self.is_prop(DIRECTION_FLAG_Y) and \
               self.is_prop(DIRECTION_FLAG_LEFT)

    @property
    def is_right(self):
        return self.is_prop(DIRECTION_FLAG_X) and \
               not self.is_prop(DIRECTION_FLAG_Y) and \
               not self.is_prop(DIRECTION_FLAG_LEFT)

    @property
    def is_top(self):
        return not self.is_prop(DIRECTION_FLAG_X) and \
               self.is_prop(DIRECTION_FLAG_Y) and \
               self.is_prop(DIRECTION_FLAG_TOP)

    @property
    def is_bottom(self):
        return not self.is_prop(DIRECTION_FLAG_X) and \
               self.is_prop(DIRECTION_FLAG_Y) and \
               not self.is_prop(DIRECTION_FLAG_TOP)

    @property
    def is_angle(self):
        return self.is_prop(DIRECTION_FLAG_Y) and \
               self.is_prop(DIRECTION_FLAG_X)

    def set_left(self):
        self.set_prop(DIRECTION_FLAG_X)
        self.unset_prop(DIRECTION_FLAG_Y)
        self.set_prop(DIRECTION_FLAG_LEFT)

    def set_right(self):
        self.set_prop(DIRECTION_FLAG_X)
        self.unset_prop(DIRECTION_FLAG_Y)
        self.unset_prop(DIRECTION_FLAG_LEFT)

    def set_top(self):
        self.unset_prop(DIRECTION_FLAG_X)
        self.set_prop(DIRECTION_FLAG_Y)
        self.set_prop(DIRECTION_FLAG_TOP)

    def set_bottom(self):
        self.unset_prop(DIRECTION_FLAG_X)
        self.set_prop(DIRECTION_FLAG_Y)
        self.unset_prop(DIRECTION_FLAG_TOP)

    def move_right(self, dx=0):
        controller = self.pipe
        self.context.current_x += dx
        if not self.is_right or self.state != INTERPRETER_STATE_PROGRAM:
            controller.write(self.CODE_RIGHT)
            self.set_right()
        if dx != 0:
            controller.write(lhymicro_distance(abs(dx)))
            self.check_bounds()

    def move_left(self, dx=0):
        controller = self.pipe
        self.context.current_x -= abs(dx)
        if not self.is_left or self.state != INTERPRETER_STATE_PROGRAM:
            controller.write(self.CODE_LEFT)
            self.set_left()
        if dx != 0:
            controller.write(lhymicro_distance(abs(dx)))
            self.check_bounds()

    def move_bottom(self, dy=0):
        controller = self.pipe
        self.context.current_y += dy
        if not self.is_bottom or self.state != INTERPRETER_STATE_PROGRAM:
            controller.write(self.CODE_BOTTOM)
            self.set_bottom()
        if dy != 0:
            controller.write(lhymicro_distance(abs(dy)))
            self.check_bounds()

    def move_top(self, dy=0):
        controller = self.pipe
        self.context.current_y -= abs(dy)
        if not self.is_top or self.state != INTERPRETER_STATE_PROGRAM:
            controller.write(self.CODE_TOP)
            self.set_top()
        if dy != 0:
            controller.write(lhymicro_distance(abs(dy)))
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
    0x00, 0x5E, 0xBC, 0xE2, 0x61, 0x3F, 0xDD, 0x83,
    0xC2, 0x9C, 0x7E, 0x20, 0xA3, 0xFD, 0x1F, 0x41,
    0x00, 0x9D, 0x23, 0xBE, 0x46, 0xDB, 0x65, 0xF8,
    0x8C, 0x11, 0xAF, 0x32, 0xCA, 0x57, 0xE9, 0x74]


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
        crc = crc_table[crc & 0x0f] ^ crc_table[16 + ((crc >> 4) & 0x0f)]
    return crc


class LhystudioController(Modifier, Pipe):
    """
    K40 Controller controls the Lhystudios boards sending any queued data to the USB when the signal is not busy.

    This is registered in the kernel as a module. Saving a few persistent settings like packet_count and registering
    a couple controls like Connect_USB.

    This is also a Pipe. Elements written to the Controller are sent to the USB to the matched device. Opening and
    closing of the pipe are dealt with internally. There are three primary monitor data channels. 'send', 'recv' and
    'usb'. They display the reading and writing of information to/from the USB and the USB connection log, providing
    information about the connecting and error status of the USB device.
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        Pipe.__init__(self)
        self.usb_log = None
        self.state = STATE_UNKNOWN

        self._thread = None
        self._buffer = b''  # Threadsafe buffered commands to be sent to controller.
        self._realtime_buffer = b''  # Threadsafe realtime buffered commands to be sent to the controller.
        self._queue = b''  # Thread-unsafe additional commands to append.
        self._preempt = b''  # Thread-unsafe preempt commands to prepend to the buffer.
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

        self.abort_waiting = False
        self.send_channel = None
        self.recv_channel = None
        self.pipe_channel = None

    def egv(self, command, *args):
        if len(args) == 0:
            yield "Lhystudios Engrave Code Sender. egv <lhymicro-gl>"
        else:
            self.write(bytes(args[0].replace('$', '\n'), "utf8"))

    def usb_connect(self, command, *args):
        try:
            self.open()
        except ConnectionRefusedError:
            yield "Connection Refused."

    def usb_disconnect(self, command, *args):
        if self.driver is not None:
            self.close()
        else:
            yield "Usb is not connected."

    def attach(self, channel=None):
        context = self.context
        self.context.register('command/egv', self.egv)
        self.context.register('command/usb_connect', self.usb_connect)
        self.context.register('command/usb_disconnect', self.usb_disconnect)

        context.pipe = self
        context.setting(int, 'packet_count', 0)
        context.setting(int, 'rejected_count', 0)

        context.register("control/Connect_USB", self.open)
        context.register("control/Disconnect_USB", self.close)
        context.register("control/Status Update", self.update_status)
        self.usb_log = context.channel_open("usb", buffer=20)
        self.send_channel = context.channel_open('send')
        self.recv_channel = context.channel_open('recv')
        self.pipe_channel = context.channel_open('pipe')
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

    def shutdown(self, channel=None):
        # Module.shutdown(channel=channel)
        pass

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
        return self

    def start(self):
        """
        Controller state change to Started.
        :return:
        """
        if self._thread is None or not self._thread.is_alive():
            self._thread = self.context._kernel.threaded(self._thread_data_send)
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
        self._buffer = b''
        self._queue = b''
        self.context.signal('pipe;buffer', 0)
        self.update_state(STATE_TERMINATE)

    def reset(self):
        self.update_state(STATE_INITIALIZE)
        self.context.signal('pipe;thread', self.state)

    def stop(self):
        self.abort()
        self._thread.join()  # Wait until stop completes before continuing.

    def update_usb_state(self, code):
        """
        Process updated values for the usb status. Sending it to the usb channel and sending update signals.

        :param code: usb status code.
        :return:
        """
        if isinstance(code, int):
            self._usb_state = code
            name = get_name_for_status(code, translation=self.context._kernel.translation)
            self.usb_log(str(name))
            self.context.signal('pipe;usb_state', code)
            self.context.signal('pipe;usb_state_text', name)
        else:
            self.usb_log(str(code))

    def detect_driver_and_open(self):
        index = self.context.usb_index
        bus = self.context.usb_bus
        address = self.context.usb_address
        serial = self.context.usb_serial
        chipv = self.context.usb_version

        try:
            from CH341LibusbDriver import CH341Driver
            self.driver = driver = CH341Driver(index=index, bus=bus, address=address, serial=serial, chipv=chipv,
                                               state_listener=self.update_usb_state)
            driver.open()
            chip_version = driver.get_chip_version()
            self.update_usb_state(INFO_USB_CHIP_VERSION | chip_version)
            self.context.signal('pipe;chipv', chip_version)
            self.update_usb_state(INFO_USB_DRIVER | STATE_DRIVER_LIBUSB)
            self.update_usb_state(STATE_CONNECTED)
            return
        except ConnectionRefusedError:
            self.driver = None
        except ImportError:
            self.update_usb_state(STATE_DRIVER_NO_LIBUSB)

        try:
            from CH341WindllDriver import CH341Driver
            self.driver = driver = CH341Driver(index=index, bus=bus, address=address, serial=serial, chipv=chipv,
                                               state_listener=self.update_usb_state)
            driver.open()
            chip_version = driver.get_chip_version()
            self.update_usb_state(INFO_USB_CHIP_VERSION | chip_version)
            self.context.signal('pipe;chipv', chip_version)
            self.update_usb_state(INFO_USB_DRIVER | STATE_DRIVER_CH341)
            self.update_usb_state(STATE_CONNECTED)
        except ConnectionRefusedError:
            self.driver = None

    def update_state(self, state):
        self.state = state
        if self.context is not None:
            self.context.signal('pipe;thread', self.state)

    def update_buffer(self):
        if self.context is not None:
            self.context.signal('pipe;buffer', len(self._realtime_buffer) + len(self._buffer))

    def update_packet(self, packet):
        if self.context is not None:
            self.context.signal('pipe;packet', convert_to_list_bytes(packet))
            self.context.signal('pipe;packet_text', packet)
            self.send_channel(str(packet))

    def _thread_data_send(self):
        """
        Main threaded function to send data. While the controller is working the thread
        will be doing work in this function.
        """
        self._main_lock.acquire(True)
        self.count = 0
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
            except ConnectionRefusedError:
                # The attempt refused the connection.
                self.refuse_counts += 1
                time.sleep(3)  # 3 second sleep on failed connection attempt.
                if self.refuse_counts >= self.max_attempts:
                    # We were refused too many times, kill the thread.
                    self.update_state(STATE_TERMINATE)
                    self.context.signal('pipe;error', self.refuse_counts)
                    break
                continue
            except ConnectionError:
                # There was an error with the connection, close it and try again.
                self.connection_errors += 1
                time.sleep(0.5)
                self.close()
                continue
            if queue_processed:
                # Packet was sent.
                if self.state not in (STATE_PAUSE, STATE_BUSY, STATE_ACTIVE, STATE_TERMINATE):
                    self.update_state(STATE_ACTIVE)
                self.count = 0
                continue
            else:
                # No packet could be sent.
                if self.state not in (STATE_PAUSE, STATE_BUSY, STATE_BUSY, STATE_TERMINATE):
                    self.update_state(STATE_IDLE)
                if self.count > 50:
                    self.count = 50
                time.sleep(0.02 * self.count)
                # will tick up to 1 second waits if there's never a queue.
                self.count += 1
        self._main_lock.release()
        self._thread = None
        self.update_state(STATE_END)

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
            self._queue = b''
            self._queue_lock.release()
            self.update_buffer()

        if len(self._preempt):  # check for and prepend preempt
            self._preempt_lock.acquire(True)
            self._realtime_buffer += self._preempt
            self._preempt = b''
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
        find = buffer.find(b'\n', 0, 30)
        if find == -1:  # No end found.
            length = min(30, len(buffer))
        else:  # Line end found.
            length = min(30, len(buffer), find + 1)
        packet = buffer[:length]

        # edge condition of catching only pipe command without '\n'
        if packet.endswith((b'-', b'*', b'&', b'!', b'#', b'\x18')):
            packet += buffer[length:length + 1]
            length += 1
        post_send_command = None

        # find pipe commands.
        if packet.endswith(b'\n'):
            packet = packet[:-1]
            if packet.endswith(b'-'):  # wait finish
                packet = packet[:-1]
                post_send_command = self.wait_finished
            elif packet.endswith(b'*'):  # abort
                post_send_command = self.abort
                packet = packet[:-1]
            elif packet.endswith(b'&'):  # resume
                self._resume_busy()
                packet = packet[:-1]
            elif packet.endswith(b'!'):  # pause
                self._pause_busy()
                packet = packet[:-1]
            elif packet.endswith(b'\x18'):
                self.state = STATE_TERMINATE
                packet = packet[:-1]
            if len(packet) != 0:
                if packet.endswith(b'#'):
                    packet = packet[:-1]
                    c = packet[-1]
                    packet += bytes([c]) * (30 - len(packet))  # Padding. '\n'
                else:
                    packet += b'F' * (30 - len(packet))  # Padding. '\n'
        if not realtime and self.state in (STATE_PAUSE, STATE_BUSY):
            return False  # Processing normal queue, PAUSE and BUSY apply.

        # Packet is prepared and ready to send. Open Channel.
        if self.context.mock:
            self.update_usb_state(STATE_DRIVER_MOCK)
        else:
            self.open()

        if len(packet) == 30:
            # We have a sendable packet.
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
            self.context.packet_count += 1  # Our packet is confirmed or assumed confirmed.
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
            packet = b'\x00' + packet + bytes([onewire_crc_lookup(packet)])
            self.driver.write(packet)
        self.update_packet(packet)

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
            self.context.signal('pipe;status', self._status)
            self.recv_channel(str(self._status))

    def wait_until_accepting_packets(self):
        i = 0
        while self.state != STATE_TERMINATE:
            self.update_status()
            status = self._status[1]
            if status == 0:
                raise ConnectionError
            if status == STATUS_OK or status == STATUS_ERROR:
                break
            time.sleep(0.05)
            if self.context is not None:
                self.context.signal('pipe;wait', STATUS_OK, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.

    def wait_finished(self):
        i = 0
        while True:
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
            time.sleep(0.05)
            if self.context is not None:
                self.context.signal('pipe;wait', status, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.


class EgvLoader:

    @staticmethod
    def load_types():
        yield "Engrave Files", ("egv",), "application/x-egv"

    @staticmethod
    def load(kernel, pathname, **kwargs):
        elements = []
        basename = os.path.basename(pathname)

        for event in parse_egv(pathname):
            path = event['path']
            path.stroke = Color('black')
            if len(path) > 0:
                elements.append(path)
                if 'speed' in event:
                    path.values['speed'] = event['speed']
            if 'raster' in event:
                raster = event['raster']
                image = raster.get_image()
                if image is not None:
                    elements.append(image)
                    if 'speed' in event:
                        image.values['speed'] = event['speed']
        return elements, pathname, basename


CMD_RIGHT = ord(b'B')
CMD_LEFT = ord(b'T')
CMD_TOP = ord(b'L')
CMD_BOTTOM = ord(b'R')

CMD_FINISH = ord(b'F')
CMD_ANGLE = ord(b'M')

CMD_RESET = ord(b'@')

CMD_ON = ord(b'D')
CMD_OFF = ord(b'U')
CMD_P = ord(b'P')
CMD_G = ord(b'G')
CMD_INTERRUPT = ord(b'I')
CMD_N = ord(b'N')
CMD_CUT = ord(b'C')
CMD_VELOCITY = ord(b'V')
CMD_S = ord(b'S')
CMD_E = ord(b'E')


class EgvParser:
    def __init__(self):
        self.command = None
        self.distance = 0
        self.number_value = 0

    @staticmethod
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

    def skip_header(self, file):
        self.skip(file, b'\n', 3)
        self.skip(file, b'%', 5)

    def parse(self, f):
        while True:
            b = f.read(1024)
            for byte in b:
                if isinstance(byte, str):
                    byte = ord(byte)  # Python 2.7
                value = byte
                if ord('0') <= value <= ord('9'):
                    self.append_digit(value - ord('0'))  # '0' = 0
                elif ord('a') <= value <= ord('y'):
                    self.append_distance(value - ord('a') + 1)  # 'a' = 1, not zero.
                elif ord('A') <= value <= ord('Z') or value == ord('@'):
                    if self.command is not None:
                        yield self.command, self.distance, self.number_value
                    self.distance = 0
                    self.number_value = 0
                    self.command = byte
                elif value == ord('z'):
                    self.append_distance(255)
                elif value == ord('|'):
                    self.append_distance(26)
            if len(b) == 0:
                return

    def append_digit(self, value):
        self.number_value *= 10
        self.number_value += value

    def append_distance(self, amount):
        self.distance += amount


class EgvRaster:
    def __init__(self):
        self.tiles = {}
        self.min_x = None
        self.min_y = None
        self.max_x = None
        self.max_y = None
        self.bytes = None

    def get_tile(self, x, y, create=True):
        tile_x = x
        tile_y = y
        tile_key = (tile_x & 0xFFFFF000) | (tile_y & 0xFFF)
        if tile_key in self.tiles:
            tile = self.tiles[tile_key]
        else:
            if not create:
                return None
            tile = [0] * (0xFFF + 1)
            self.tiles[tile_key] = tile
        return tile

    def __setitem__(self, key, value):
        x, y = key
        tile = self.get_tile(x, y, True)
        tindex = x & 0xFFF
        tile[tindex] = value
        if self.min_x is None or self.min_x > x:
            self.min_x = x
        if self.min_y is None or self.min_y > y:
            self.min_y = y
        if self.max_x is None or self.max_x < x:
            self.max_x = x
        if self.max_y is None or self.max_y < x:
            self.max_y = x
        self.bytes = None

    def __getitem__(self, item):
        x, y = item
        if self.min_x <= x <= self.max_x and self.min_y <= x <= self.max_y:
            tile = self.get_tile(x, y, False)
            if tile is None:
                return 0
            tindex = x & 0xFFF
            return tile[tindex]
        return 0

    @property
    def width(self):
        if self.max_x is None:
            return 0
        return self.max_x - self.min_x

    @property
    def height(self):
        if self.max_y is None:
            return 0
        return self.max_y - self.min_y

    @property
    def size(self):
        return self.width, self.height

    def get_image(self):
        from PIL import Image
        if self.bytes is None:
            b = bytearray(b'')
            if self.min_y is None and self.max_y is None and self.min_x is None and self.max_x is None:
                return None
            for y in range(self.min_y, self.max_y + 1):
                tile = self.get_tile(self.min_x, y, False)
                for x in range(self.min_x, self.max_x + 1):
                    tindex = x & 0xFFF
                    if tindex == 0:
                        tile = self.get_tile(x, y, False)
                    if tile is None or tile[tindex] == 0:
                        b.append(0xFF)
                    else:
                        b.append(0)
            self.bytes = bytes(b)
        image = Image.frombytes("L", self.size, self.bytes)
        return image


class EgvPlotter:
    def __init__(self, x=0, y=0):
        self.path = Path()
        self.raster = EgvRaster()
        self.x = x
        self.y = y
        self.cutting = False
        self.data = {'path': self.path}
        self.cut = self.vector_cut
        self.on = self.vector_on

    def vector_cut(self, dx, dy):
        if dx == 0 and dy == 0:
            return  # Just setting the directions.
        if self.cutting:
            self.path.line((self.x + dx, self.y + dy))
        else:
            self.path.move((self.x + dx, self.y + dy))
        self.x += dx
        self.y += dy

    def raster_cut(self, dx, dy):
        if dx == 0 and dy == 0:
            return  # Just setting the directions.
        if self.cutting:
            if dy == 0:
                for d in range(0, dx):
                    self.raster[self.x + d, self.y] = 1
        self.x += dx
        self.y += dy

    def set_raster(self, value):
        if value:
            self.cut = self.raster_cut
            self.on = self.raster_on
            self.data['raster'] = self.raster
        else:
            self.on = self.vector_on
            self.cut = self.vector_cut

    def vstep(self):
        self.raster_cut(0, self.data['step'])

    def off(self):
        self.cutting = False

    def vector_on(self):
        self.path.move((self.x, self.y))
        self.cutting = True

    def raster_on(self):
        self.cutting = True


def parse_egv(f, board="M2"):
    if isinstance(f, str):
        with open(f, "rb") as f:
            for element in parse_egv(f, board=board):
                yield element
        return

    egv_parser = EgvParser()
    egv_parser.skip_header(f)
    speed_code = None
    is_compact = False
    is_left = False
    is_top = False
    is_reset = False
    is_harmonic = False
    obj = EgvPlotter()

    for commands in egv_parser.parse(f):
        cmd = commands[0]
        distance = commands[1] + commands[2]
        if cmd is None:
            return
        elif cmd == CMD_RIGHT:  # move right
            obj.cut(distance, 0)
            if is_harmonic and is_left:
                obj.vstep()
            is_left = False
        elif cmd == CMD_LEFT:  # move left
            obj.cut(-distance, 0)
            if is_harmonic and not is_left:
                obj.vstep()
            is_left = True
        elif cmd == CMD_BOTTOM:  # move bottom
            obj.cut(0, distance)
            is_top = False
        elif cmd == CMD_TOP:  # move top
            obj.cut(0, -distance)
            is_top = True
        elif cmd == CMD_ANGLE:
            if is_left:
                distance_x = -distance
            else:
                distance_x = distance
            if is_top:
                distance_y = -distance
            else:
                distance_y = distance
            obj.cut(distance_x, distance_y)
        elif cmd == CMD_ON:  # laser on
            obj.on()
        elif cmd == CMD_OFF:  # laser off
            obj.off()
        elif cmd == CMD_S:  # slow
            if commands[2] == 1:
                is_reset = False
                is_compact = True
                yield obj.data
                obj = EgvPlotter(obj.x, obj.y)
                laser_speed = LaserSpeed(speed_code, board=board)
                speed = laser_speed.speed
                raster_step = laser_speed.raster_step
                obj.data['step'] = raster_step
                obj.data['speed'] = speed
                if raster_step != 0:
                    is_harmonic = True
                    obj.set_raster(True)
            else:
                if not is_compact and not is_reset:
                    is_compact = True  # We jumped out of compact, but then back in.
        elif cmd == CMD_N:
            if is_compact:
                is_compact = False
        elif cmd == CMD_FINISH or cmd == CMD_RESET:
            is_reset = True
            speed_code = None
            if is_compact:
                is_compact = False
                is_harmonic = False
                yield obj.data
                obj = EgvPlotter(obj.x, obj.y)
        elif cmd == CMD_CUT:  # Speed code element
            if speed_code is None:
                speed_code = ""
            speed_code += 'C'
        elif cmd == CMD_VELOCITY:  # Speed code element
            if speed_code is None:
                speed_code = ""
            speed_code += 'V%d' % commands[2]
        elif cmd == CMD_G:  # Speed code element
            value_g = commands[2]
            if speed_code is None:
                speed_code = ""
            speed_code += "G%03d" % value_g
        elif cmd == CMD_E:  # e command
            pass
        elif cmd == CMD_P:  # pop
            pass
        elif cmd == CMD_INTERRUPT:  # interrupt
            pass
    yield obj.data
