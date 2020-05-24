import threading

from CH341DriverBase import *
from Kernel import *
from LaserCommandConstants import *
from LaserSpeed import LaserSpeed
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
STATUS_PACKET_REJECTED = 207
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


class LhystudiosDevice(Device):
    """
    LhystudiosDevice instance. Serves as a device instance for a lhymicro-gl based device.
    """
    def __init__(self, root=None, uid=1):
        Device.__init__(self, root, uid)
        self.uid = uid
        self.device_name = "Lhystudios"
        self.location_name = "USB"
        self.current_x = 0
        self.current_y = 0

        # Device specific stuff. Fold into proper kernel commands or delegate to subclass.
        self.interpreter = None
        self.spooler = None

    def __repr__(self):
        return "LhystudiosDevice(uid='%s')" % str(self.uid)

    @staticmethod
    def sub_register(device):
        device.register('module', 'LhymicroInterpreter', LhymicroInterpreter)
        device.register('module', 'LhystudioController', LhystudioController)

    def initialize(self, device):
        """
        Device initialize.

        :param device:
        :param name:
        :return:
        """
        self.setting(int, 'usb_index', -1)
        self.setting(int, 'usb_bus', -1)
        self.setting(int, 'usb_address', -1)
        self.setting(int, 'usb_serial', -1)
        self.setting(int, 'usb_version', -1)

        self.setting(bool, 'mock', False)
        self.setting(bool, 'quit', False)
        self.setting(int, 'packet_count', 0)
        self.setting(int, 'rejected_count', 0)
        self.setting(bool, "autolock", True)
        self.setting(bool, "autohome", False)
        self.setting(bool, "autobeep", True)
        self.setting(bool, "autostart", True)

        self.setting(str, "board", 'M2')
        self.setting(bool, "rotary", False)
        self.setting(float, "scale_x", 1.0)
        self.setting(float, "scale_y", 1.0)
        self.setting(int, "_stepping_force", None)
        self.setting(float, "_acceleration_breaks", float("inf"))
        self.setting(int, "bed_width", 320)
        self.setting(int, "bed_height", 220)

        self.signal("bed_size", (self.bed_width, self.bed_height))

        self.control_instance_add("Emergency Stop", self.emergency_stop)
        self.control_instance_add("Debug Device", self._start_debugging)

        pipe = self.open('module', "LhystudioController", instance_name='pipe')
        self.open('module', "LhymicroInterpreter", instance_name='interpreter', pipe=pipe)
        self.open('module', "Spooler", instance_name='spooler')

    def halt(self, channel=None):
        self.spooler.clear_queue()
        self.emergency_stop()

    def emergency_stop(self):
        self.interpreter.realtime_command(REALTIME_RESET, 1)

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


class LhymicroInterpreter(Interpreter):
    """
    LhymicroInterpreter provides Lhystudio specific coding for elements and sends it to the backend to write to the usb
    the intent is that this class could be switched out for a different class and control a different type of laser if need
    be. The middle language of generated commands from the LaserNodes are able to be interpreted by a different driver
    or methodology.
    """

    def __init__(self, pipe):
        Interpreter.__init__(self, pipe=pipe)
        self.CODE_RIGHT = b'B'
        self.CODE_LEFT = b'T'
        self.CODE_TOP = b'L'
        self.CODE_BOTTOM = b'R'
        self.CODE_ANGLE = b'M'
        self.CODE_ON = b'D'
        self.CODE_OFF = b'U'

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

    def initialize(self):
        self.device.setting(bool, "swap_xy", False)
        self.device.setting(bool, "flip_x", False)
        self.device.setting(bool, "flip_y", False)
        self.device.setting(bool, "home_right", False)
        self.device.setting(bool, "home_bottom", False)
        self.device.setting(int, "home_adjust_x", 0)
        self.device.setting(int, "home_adjust_y", 0)
        self.device.setting(int, "buffer_max", 900)
        self.device.setting(bool, "buffer_limit", True)
        self.device.setting(int, "current_x", 0)
        self.device.setting(int, "current_y", 0)

        self.update_codes()

        current_x = self.device.current_x
        current_y = self.device.current_y
        self.next_x = current_x
        self.next_y = current_y
        self.max_x = current_x
        self.max_y = current_y
        self.min_x = current_x
        self.min_y = current_y
        self.start_x = current_x
        self.start_y = current_y

        self.device.add('control', "Realtime Pause_Resume", self.pause_resume)
        self.device.add('control', "Realtime Pause", self.pause)
        self.device.add('control', "Realtime Resume", self.resume)
        self.device.add('control', "Update Codes", self.update_codes)

    def __repr__(self):
        return "LhymicroInterpreter()"

    def update_codes(self):
        if not self.device.swap_xy:
            self.CODE_RIGHT = b'B'
            self.CODE_LEFT = b'T'
            self.CODE_TOP = b'L'
            self.CODE_BOTTOM = b'R'
        else:
            self.CODE_RIGHT = b'R'
            self.CODE_LEFT = b'L'
            self.CODE_TOP = b'T'
            self.CODE_BOTTOM = b'B'
        if self.device.flip_x:
            q = self.CODE_LEFT
            self.CODE_LEFT = self.CODE_RIGHT
            self.CODE_RIGHT = q
        if self.device.flip_y:
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
        return self.device.buffer_limit and len(self.pipe) > self.device.buffer_max

    def execute(self):
        if self.hold():
            return
        while self.plot is not None:
            if self.hold():
                return
            sx = self.device.current_x
            sy = self.device.current_y
            try:
                x, y, on = next(self.plot)
                dx = x - sx
                dy = y - sy
                if self.raster_step != 0:
                    if self.is_prop(DIRECTION_FLAG_X) and dy != 0:
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
                    elif self.is_prop(DIRECTION_FLAG_Y) and dx != 0:
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
                if on == 0:
                    self.laser_on()
                else:
                    self.laser_off()
                self.move_absolute(x, y)
            except StopIteration:
                self.plot = None
                return
            except RuntimeError:
                self.plot = None
                return
        Interpreter.execute(self)

    def plot_path(self, path):
        if len(path) == 0:
            return
        first_point = path.first_point
        self.move_absolute(first_point[0], first_point[1])
        sx = self.device.current_x
        sy = self.device.current_y
        self.pulse_modulation = True
        self.plot = self.group_plots(sx, sy, ZinglPlotter.plot_path(path))

    def plot_raster(self, raster):
        sx = self.device.current_x
        sy = self.device.current_y
        self.pulse_modulation = True
        self.plot = self.group_plots(sx, sy, self.ungroup_plots(raster.plot()))

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
        self.plot = None
        self.pipe.realtime_write(b'I*\n')
        self.state = INTERPRETER_STATE_RAPID
        self.device.signal('interpreter;mode', self.state)

    def move(self, x, y):
        self.pulse_modulation = self.laser
        sx = self.device.current_x
        sy = self.device.current_y

        if self.state == INTERPRETER_STATE_PROGRAM:
            if self.is_relative:
                x += sx
                y += sy
            self.plot = self.group_plots(sx, sy, ZinglPlotter.plot_line(sx, sy, x, y))
        else:
            if self.is_relative:
                self.move_relative(x, y)
            else:
                self.move_absolute(x, y)

    def move_absolute(self, x, y):
        self.move_relative(x - self.device.current_x, y - self.device.current_y)

    def move_relative(self, dx, dy):
        if abs(dx) == 0 and abs(dy) == 0:
            return
        dx = int(round(dx))
        dy = int(round(dy))
        if self.state == INTERPRETER_STATE_RAPID:
            self.pipe.write(b'I')
            if dx != 0:
                self.move_x(dx)
            if dy != 0:
                self.move_y(dy)
            self.pipe.write(b'S1P\n')
            if not self.device.autolock:
                self.pipe.write(b'IS2P\n')
        elif self.state == INTERPRETER_STATE_PROGRAM:
            if dx != 0 and dy != 0 and abs(dx) != abs(dy):
                for x, y, on in self.group_plots(self.device.current_x, self.device.current_y,
                                                 ZinglPlotter.plot_line(self.device.current_x, self.device.current_y,
                                                                        self.device.current_x + dx,
                                                                        self.device.current_y + dy)
                                                 ):
                    self.move_absolute(x, y)
            elif abs(dx) == abs(dy):
                self.move_angle(dx, dy)
            elif dx != 0:
                self.move_x(dx)
            else:
                self.move_y(dy)
        elif self.state == INTERPRETER_STATE_FINISH:
            if dx != 0:
                self.move_x(dx)
            if dy != 0:
                self.move_y(dy)
            self.pipe.write(b'N')
        self.check_bounds()
        self.device.signal('interpreter;position', (self.device.current_x, self.device.current_y,
                                                    self.device.current_x - dx, self.device.current_y - dy))

    def move_xy_line(self, delta_x, delta_y):
        """Strictly speaking if this happens it is because of a bug.
        Nothing should feed the writer this data. It's invalid.
        All moves should be diagonal or orthogonal.

        Zingl-Bresenham line draw algorithm"""

        dx = abs(delta_x)
        dy = -abs(delta_y)

        if delta_x > 0:
            sx = 1
        else:
            sx = -1
        if delta_y > 0:
            sy = 1
        else:
            sy = -1
        err = dx + dy  # error value e_xy
        x0 = 0
        y0 = 0
        while True:  # /* loop */
            if x0 == delta_x and y0 == delta_y:
                break
            mx = 0
            my = 0
            e2 = 2 * err
            if e2 >= dy:  # e_xy+e_y < 0
                err += dy
                x0 += sx
                mx += sx
            if e2 <= dx:  # e_xy+e_y < 0
                err += dx
                y0 += sy
                my += sy
            if abs(mx) == abs(my):
                self.move_angle(mx, my)
            elif mx != 0:
                self.move_x(mx)
            else:
                self.move_y(my)

    def set_speed(self, speed=None):
        change = False
        if self.speed != speed:
            change = True
            self.speed = speed
        if not change:
            return
        if self.state == INTERPRETER_STATE_PROGRAM:
            # Compact mode means it's currently slowed. To make the speed have an effect, compact must be exited.
            self.ensure_finished_mode()
            self.ensure_program_mode()

    def set_d_ratio(self, d_ratio=None):
        change = False
        if self.d_ratio != d_ratio:
            change = True
            self.d_ratio = d_ratio
        if not change:
            return
        if self.state == INTERPRETER_STATE_PROGRAM:
            # Compact mode means it's currently slowed. To make the speed have an effect, compact must be exited.
            self.ensure_finished_mode()
            self.ensure_program_mode()

    def set_acceleration(self, accel=None):
        change = False
        if self.acceleration != accel:
            change = True
            self.acceleration = accel
        if not change:
            return
        if self.state == INTERPRETER_STATE_PROGRAM:
            # Compact mode means it's currently slowed. To make the change have an effect, compact must be exited.
            self.ensure_finished_mode()
            self.ensure_program_mode()

    def set_step(self, step=None):
        change = False
        if self.raster_step != step:
            change = True
            self.raster_step = step
        if not change:
            return
        if self.state == INTERPRETER_STATE_PROGRAM:
            # Compact mode means it's currently slowed. To make the speed have an effect, compact must be exited.
            self.ensure_finished_mode()
            self.ensure_program_mode()

    def laser_off(self):
        if self.laser:
            return False
        controller = self.pipe
        if self.state == INTERPRETER_STATE_RAPID:
            controller.write(b'I')
            controller.write(self.CODE_ON)
            controller.write(b'S1P\n')
            if not self.device.autolock:
                controller.write(b'IS2P\n')
        elif self.state == INTERPRETER_STATE_PROGRAM:
            controller.write(self.CODE_ON)
        elif self.state == INTERPRETER_STATE_FINISH:
            controller.write(self.CODE_ON)
            controller.write(b'N')
        self.laser = True
        return True

    def laser_on(self):
        controller = self.pipe
        if not self.laser:
            return False
        if self.state == INTERPRETER_STATE_RAPID:
            controller.write(b'I')
            controller.write(self.CODE_OFF)
            controller.write(b'S1P\n')
            if not self.device.autolock:
                controller.write(b'IS2P\n')
        elif self.state == INTERPRETER_STATE_PROGRAM:
            controller.write(self.CODE_OFF)
        elif self.state == INTERPRETER_STATE_FINISH:
            controller.write(self.CODE_OFF)
            controller.write(b'N')
        self.laser = False
        return True

    def ensure_rapid_mode(self):
        if self.state == INTERPRETER_STATE_RAPID:
            return
        controller = self.pipe
        if self.state == INTERPRETER_STATE_FINISH:
            controller.write(b'S1P\n')
            if not self.device.autolock:
                controller.write(b'IS2P\n')
        elif self.state == INTERPRETER_STATE_PROGRAM:
            controller.write(b'FNSE-\n')
            self.reset_modes()
        self.state = INTERPRETER_STATE_RAPID
        self.device.signal('interpreter;mode', self.state)

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
        self.device.signal('interpreter;mode', self.state)

    def ensure_program_mode(self):
        if self.state == INTERPRETER_STATE_PROGRAM:
            return
        controller = self.pipe
        self.ensure_finished_mode()
        speed_code = LaserSpeed(
            self.device.board,
            self.speed,
            self.raster_step,
            d_ratio=self.d_ratio,
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
        self.device.signal('interpreter;mode', self.state)

    def h_switch(self):
        controller = self.pipe
        if self.is_prop(DIRECTION_FLAG_LEFT):
            controller.write(self.CODE_RIGHT)
            self.unset_prop(DIRECTION_FLAG_LEFT)
        else:
            controller.write(self.CODE_LEFT)
            self.set_prop(DIRECTION_FLAG_LEFT)
        if self.is_prop(DIRECTION_FLAG_TOP):
            self.device.current_y -= self.raster_step
        else:
            self.device.current_y += self.raster_step
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
            self.device.current_x -= self.raster_step
        else:
            self.device.current_x += self.raster_step
        self.laser = False

    def calc_home_position(self):
        x = 0
        y = 0
        if self.device.home_right:
            x = int(self.device.bed_width * 39.3701)
        if self.device.home_bottom:
            y = int(self.device.bed_height * 39.3701)
        return x, y

    def home(self):
        x, y = self.calc_home_position()
        controller = self.pipe
        self.ensure_rapid_mode()
        controller.write(b'IPP\n')
        old_x = self.device.current_x
        old_y = self.device.current_y
        self.device.current_x = x
        self.device.current_y = y
        self.reset_modes()
        self.state = INTERPRETER_STATE_RAPID
        adjust_x = self.device.home_adjust_x
        adjust_y = self.device.home_adjust_y
        if adjust_x != 0 or adjust_y != 0:
            # Perform post home adjustment.
            self.move_relative(adjust_x, adjust_y)
            # Erase adjustment
            self.device.current_x = x
            self.device.current_y = y

        self.device.signal('interpreter;mode', self.state)
        self.device.signal('interpreter;position', (self.device.current_x, self.device.current_y, old_x, old_y))

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
        self.min_x = min(self.min_x, self.device.current_x)
        self.min_y = min(self.min_y, self.device.current_y)
        self.max_x = max(self.max_x, self.device.current_x)
        self.max_y = max(self.max_y, self.device.current_y)

    def reset_modes(self):
        self.laser = False
        self.properties = 0

    def move_x(self, dx):
        if dx > 0:
            self.move_right(dx)
        else:
            self.move_left(dx)

    def move_y(self, dy):
        if dy > 0:
            self.move_bottom(dy)
        else:
            self.move_top(dy)

    def move_angle(self, dx, dy):
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
        self.device.current_x += dx
        self.device.current_y += dy
        self.check_bounds()
        controller.write(self.CODE_ANGLE + lhymicro_distance(abs(dy)))

    def declare_directions(self):
        """Declare direction declares raster directions of left, top, with the primary momentum direction going last.
        You cannot declare a diagonal direction."""
        controller = self.pipe

        if self.is_prop(DIRECTION_FLAG_LEFT):
            x_dir = self.CODE_LEFT
        else:
            x_dir = self.CODE_RIGHT
        if self.is_prop(DIRECTION_FLAG_TOP):
            y_dir = self.CODE_TOP
        else:
            y_dir = self.CODE_BOTTOM
        if self.is_prop(DIRECTION_FLAG_X):  # FLAG_Y is assumed to be !FLAG_X
            controller.write(y_dir + x_dir)
        else:
            controller.write(x_dir + y_dir)

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
        self.device.current_x += dx
        if not self.is_right or self.state != INTERPRETER_STATE_PROGRAM:
            controller.write(self.CODE_RIGHT)
            self.set_right()
        if dx != 0:
            controller.write(lhymicro_distance(abs(dx)))
            self.check_bounds()

    def move_left(self, dx=0):
        controller = self.pipe
        self.device.current_x -= abs(dx)
        if not self.is_left or self.state != INTERPRETER_STATE_PROGRAM:
            controller.write(self.CODE_LEFT)
            self.set_left()
        if dx != 0:
            controller.write(lhymicro_distance(abs(dx)))
            self.check_bounds()

    def move_bottom(self, dy=0):
        controller = self.pipe
        self.device.current_y += dy
        if not self.is_bottom or self.state != INTERPRETER_STATE_PROGRAM:
            controller.write(self.CODE_BOTTOM)
            self.set_bottom()
        if dy != 0:
            controller.write(lhymicro_distance(abs(dy)))
            self.check_bounds()

    def move_top(self, dy=0):
        controller = self.pipe
        self.device.current_y -= abs(dy)
        if not self.is_top or self.state != INTERPRETER_STATE_PROGRAM:
            controller.write(self.CODE_TOP)
            self.set_top()
        if dy != 0:
            controller.write(lhymicro_distance(abs(dy)))
            self.check_bounds()

    def ungroup_plots(self, generate):
        """
        Converts a generated x,y,on with long orthogonal steps into a generation of single steps.
        :param generate: generator creating long orthogonal steps.
        :return:
        """
        current_x = None
        current_y = None
        for next_x, next_y, on in generate:
            if current_x is None or current_y is None:
                current_x = next_x
                current_y = next_y
                yield current_x, current_y, on
                continue
            if next_x > current_x:
                dx = 1
            elif next_x < current_x:
                dx = -1
            else:
                dx = 0
            if next_y > current_y:
                dy = 1
            elif next_y < current_y:
                dy = -1
            else:
                dy = 0
            total_dx = next_x - current_x
            total_dy = next_y - current_y
            if total_dy * dx != total_dx * dy:
                raise ValueError("Must be uniformly diagonal or orthogonal: (%d, %d) is not." % (total_dx, total_dy))
            while current_x != next_x or current_y != next_y:
                current_x += dx
                current_y += dy
                yield current_x, current_y, on

    def group_plots(self, start_x, start_y, generate):
        """
        Converts a generated series of single stepped plots into grouped orthogonal/diagonal plots.
        Implements PPI power modulation
        :param start_x: Start x position
        :param start_y: Start y position
        :param generate: generator of single stepped plots
        :return:
        """
        last_x = start_x
        last_y = start_y
        last_on = 0
        dx = 0
        dy = 0
        x = None
        y = None
        for event in generate:
            try:
                x = event[0]
                y = event[1]
                plot_on = event[2]
            except IndexError:
                plot_on = 1
            if self.pulse_modulation:
                self.pulse_total += self.power * plot_on
                if self.group_modulation and last_on == 1:
                    # If we are group modulating and currently on, the threshold for additional on triggers is 500.
                    if self.pulse_total > 0.0:
                        on = 1
                        self.pulse_total -= 1000.0
                    else:
                        on = 0
                else:
                    if self.pulse_total >= 1000.0:
                        on = 1
                        self.pulse_total -= 1000.0
                    else:
                        on = 0
            else:
                on = int(round(plot_on))
            if x == last_x + dx and y == last_y + dy and on == last_on:
                last_x = x
                last_y = y
                continue
            yield last_x, last_y, last_on
            dx = x - last_x
            dy = y - last_y
            if abs(dx) > 1 or abs(dy) > 1:
                # An error here means the plotting routines are flawed and plotted data more than a pixel apart.
                # The bug is in the code that wrongly plotted the data, not here.
                raise ValueError("dx(%d) or dy(%d) exceeds 1" % (dx, dy))
            last_x = x
            last_y = y
            last_on = on
        yield last_x, last_y, last_on


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
    elif code == STATUS_PACKET_REJECTED:
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


class LhystudioController(Module, Pipe):
    """
    K40 Controller controls the primary Lhystudios boards sending any queued data to the USB when the signal is not
    busy.

    This is registered in the kernel as a module. Saving a few persistent settings like packet_count and registering
    a couple controls like Connect_USB.

    This is also a Pipe. Elements written to the Controller are sent to the USB to the matched device. Opening and
    closing of the pipe are dealt with internally. There are two primary monitor data channels. 'status' and 'log'
    elements monitoring this pipe will be updated on the status. Of the reading and writing of the connected information
    and the log will provide information about the connected and error status of the USB device.
    """

    def __init__(self, device=None, uid=''):
        Module.__init__(self, device=device)
        Pipe.__init__(self)
        self.usb_log = None
        self.debug_file = None
        self.state = THREAD_STATE_UNSTARTED

        self.buffer = b''  # Threadsafe buffered commands to be sent to controller.
        self.queue = b''  # Thread-unsafe additional commands to append.
        self.preempt = b''  # Thread-unsafe preempt commands to prepend to the buffer.
        self.queue_lock = threading.Lock()
        self.preempt_lock = threading.Lock()

        self.status = [0] * 6
        self.usb_state = -1

        self.driver = None
        self.max_attempts = 5
        self.refuse_counts = 0
        self.connection_errors = 0
        self.count = 0

        self.abort_waiting = False
        self.send_channel = None
        self.recv_channel = None
        self.process = self.write_buffer_to_usb
        self.interval = 0.05

    def initialize(self):
        self.device.setting(int, 'packet_count', 0)
        self.device.setting(int, 'rejected_count', 0)

        self.device.control_instance_add("Connect_USB", self.open)
        self.device.control_instance_add("Disconnect_USB", self.close)
        self.device.control_instance_add("Start", self.start)
        self.device.control_instance_add("Stop", self.stop)
        self.device.control_instance_add("Status Update", self.update_status)
        self.usb_log = self.device.channel_open("usb", buffer=20)
        self.send_channel = self.device.channel_open('send')
        self.recv_channel = self.device.channel_open('recv')
        self.reset()

        def abort_wait():
            self.abort_waiting = True

        self.device.control_instance_add("Wait Abort", abort_wait)

        def pause_k40():
            self.state = THREAD_STATE_PAUSED
            self.start()

        self.device.control_instance_add("Pause", pause_k40)

        def resume_k40():
            self.state = THREAD_STATE_STARTED
            self.start()

        self.device.control_instance_add("Resume", resume_k40)

    def __repr__(self):
        return "K40Controller()"

    def __len__(self):
        return len(self.buffer) + len(self.queue) + len(self.preempt)

    def write_buffer_to_usb(self):
        if self.state == THREAD_STATE_UNSTARTED:
            self.device.signal('pipe;thread', THREAD_STATE_STARTED)
            self.state = THREAD_STATE_STARTED
        if self.state == THREAD_STATE_PAUSED:
            self.next_run = 1
            return
        if self.state == THREAD_STATE_STARTED:
            try:
                queue_processed = self.process_queue()
                self.refuse_counts = 0
            except ConnectionRefusedError:
                self.refuse_counts += 1
                self.next_run = 3 # 3 second sleep on failed connection attempt.
                if self.refuse_counts >= self.max_attempts:
                    self.device.signal('pipe;thread', THREAD_STATE_ABORT)
                    self.state = THREAD_STATE_ABORT
                    self.device.signal('pipe;error', self.refuse_counts)
                return
            except ConnectionError:
                self.connection_errors += 1
                self.next_run = 0.5
                self.close()
                return
            if queue_processed:
                # Packet was sent.
                self.count = 0
            else:
                # No packet could be sent.
                if self.count > 5:
                    if self.device.quit:
                        self.device.signal('pipe;thread', THREAD_STATE_FINISHED)
                        self.state = THREAD_STATE_FINISHED
                        return
                if self.count > 50:
                    self.count = 50
                self.next_run = 0.02 * self.count  # will tick up to 1 second waits if process queue never works.
                self.count += 1

    def open(self):
        if self.driver is None:
            self.detect_driver_and_open()
        else:
            # Update criteria
            self.driver.index = self.device.usb_index
            self.driver.bus = self.device.usb_bus
            self.driver.address = self.device.usb_address
            self.driver.serial = self.device.usb_serial
            self.driver.chipv = self.device.usb_version
            self.driver.open()
        if self.driver is None:
            raise ConnectionRefusedError

    def close(self):
        if self.driver is not None:
            self.driver.close()

    def write(self, bytes_to_write):
        self.queue_lock.acquire(True)
        self.queue += bytes_to_write
        self.queue_lock.release()
        self.start()
        return self

    def realtime_write(self, bytes_to_write):
        """
        Preempting commands.
        Commands to be sent to the front of the buffer.
        """
        self.preempt_lock.acquire(True)
        self.preempt = bytes_to_write + self.preempt
        self.preempt_lock.release()
        self.start()
        if self.state == THREAD_STATE_PAUSED:
            self.state = THREAD_STATE_STARTED
        return self

    def state_listener(self, code):
        if isinstance(code, int):
            self.usb_state = code
            name = get_name_for_status(code, translation=self.device.device_root.translation)
            self.usb_log(str(name))
            self.device.signal("pipe;usb_state", code)
            self.device.signal("pipe;usb_status", name)
        else:
            self.usb_log(str(code))

    def detect_driver_and_open(self):
        index = self.device.usb_index
        bus = self.device.usb_bus
        address = self.device.usb_address
        serial = self.device.usb_serial
        chipv = self.device.usb_version

        try:
            from CH341LibusbDriver import CH341Driver
            self.driver = driver = CH341Driver(index=index, bus=bus, address=address, serial=serial, chipv=chipv,
                                               state_listener=self.state_listener)
            driver.open()
            chip_version = driver.get_chip_version()
            self.state_listener(INFO_USB_CHIP_VERSION | chip_version)
            self.device.signal("pipe;chipv", chip_version)
            self.state_listener(INFO_USB_DRIVER | STATE_DRIVER_LIBUSB)
            self.state_listener(STATE_CONNECTED)
            return
        except ConnectionRefusedError:
            self.driver = None
        except ImportError:
             self.state_listener(STATE_DRIVER_NO_LIBUSB)
        try:
            from CH341WindllDriver import CH341Driver
            self.driver = driver = CH341Driver(index=index, bus=bus, address=address, serial=serial, chipv=chipv,
                                               state_listener=self.state_listener)
            driver.open()
            chip_version = driver.get_chip_version()
            self.state_listener(INFO_USB_CHIP_VERSION | chip_version)
            self.device.signal("pipe;chipv", chip_version)
            self.state_listener(INFO_USB_DRIVER | STATE_DRIVER_CH341)
            self.state_listener(STATE_CONNECTED)
        except ConnectionRefusedError:
            self.driver = None

    def start(self):
        if self.state == THREAD_STATE_ABORT:
            # We cannot reset an aborted thread without specifically calling reset.
            return
        if self.state == THREAD_STATE_FINISHED:
            self.device.signal('pipe;thread', THREAD_STATE_UNSTARTED)
            self.reset()
        if self.state == THREAD_STATE_UNSTARTED:
            self.state = THREAD_STATE_STARTED
            self.schedule()

    def resume(self):
        self.state = THREAD_STATE_STARTED
        self.schedule()

    def pause(self):
        self.state = THREAD_STATE_PAUSED

    def abort(self):
        self.device.signal('pipe;thread', THREAD_STATE_ABORT)
        self.state = THREAD_STATE_ABORT
        self.buffer = b''
        self.queue = b''
        self.device.signal('pipe;buffer', 0)
        self.unschedule()

    def reset(self):
        self.device.signal('pipe;thread', THREAD_STATE_UNSTARTED)
        self.state = THREAD_STATE_UNSTARTED

    def stop(self):
        self.abort()

    def process_queue(self):
        """
        Attempts to process the buffer/queue
        Will fail on ConnectionRefusedError at open, 'process_queue_pause = True' (anytime before packet sent),
        self.buffer is empty, or a failure to produce packet.

        Buffer will not be changed unless packet is successfully sent, or pipe commands are processed.

        - : tells the system to require wait finish at the end of the queue processing.
        * : tells the system to clear the buffers, and abort the thread.
        ! : tells the system to pause.
        & : tells the system to resume.

        :return: queue process success.
        """
        if len(self.queue):  # check for and append queue
            self.queue_lock.acquire(True)
            self.buffer += self.queue
            self.queue = b''
            self.queue_lock.release()
            self.device.signal('pipe;buffer', len(self.buffer))

        if len(self.preempt):  # check for and prepend preempt
            self.preempt_lock.acquire(True)
            self.buffer = self.preempt + self.buffer
            self.preempt = b''
            self.preempt_lock.release()
        if len(self.buffer) == 0:
            return False

        # Find buffer of 30 or containing '\n'.
        find = self.buffer.find(b'\n', 0, 30)
        if find == -1:  # No end found.
            length = min(30, len(self.buffer))
        else:  # Line end found.
            length = min(30, len(self.buffer), find + 1)
        packet = self.buffer[:length]

        # edge condition of catching only pipe command without '\n'
        if packet.endswith((b'-', b'*', b'&', b'!')):
            packet += self.buffer[length:length + 1]
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
                self.resume()  # resume must be done before checking pause state.
                packet = packet[:-1]
            elif packet.endswith(b'!'):  # pause
                post_send_command = self.pause
                packet = packet[:-1]
            if len(packet) != 0:
                packet += b'F' * (30 - len(packet))  # Padding. '\n'
        if self.state == THREAD_STATE_PAUSED:
            return False  # Abort due to pause.

        # Packet is prepared and ready to send.
        if self.device.mock:
            self.state_listener(STATE_DRIVER_MOCK)
        else:
            self.open()

        if len(packet) == 30:
            # check that latest state is okay.
            try:
                self.wait_until_accepting_packets()
            except ConnectionError:
                return False  # Wait suffered connection error.

            if self.state == THREAD_STATE_PAUSED:
                return False  # Paused during packet fetch.

            try:
                self.send_packet(packet)
            except ConnectionError:
                return False  # Error exactly at packet send assumes no packet sent.
            attempts = 0
            status = 0
            while attempts < 300:  # 200 * 300 = 60,000 = 60 seconds.
                try:
                    self.update_status()
                    status = self.status[1]
                    break
                except ConnectionError:
                    attempts += 1
            if status == STATUS_PACKET_REJECTED:
                self.device.rejected_count += 1
                time.sleep(0.05)
                # The packet was rejected. The sent data was not accepted. Return False.
                return False
            if status == 0:
                raise ConnectionError  # Broken pipe.
            self.device.packet_count += 1  # Everything went off without a problem.
        else:
            if len(packet) != 0:  # packet isn't purely a commands len=0, or filled 30.
                return False  # This packet cannot be sent. Toss it back.

        # Packet was processed.
        self.buffer = self.buffer[length:]
        self.device.signal('pipe;buffer', len(self.buffer))

        if post_send_command is not None:
            # Post send command could be wait_finished, and might have a broken pipe.
            try:
                post_send_command()
            except ConnectionError:
                # We should have already sent the packet. So this should be fine.
                pass
        return True  # A packet was prepped and sent correctly.

    def send_packet(self, packet):
        if self.device.mock:
            time.sleep(0.04)
        else:
            packet = b'\x00' + packet + bytes([onewire_crc_lookup(packet)])
            self.driver.write(packet)
        self.device.signal("pipe;packet", convert_to_list_bytes(packet))
        self.device.signal("pipe;packet_text", packet)
        self.send_channel(str(packet))

    def update_status(self):
        if self.device.mock:
            self.status = [255, 206, 0, 0, 0, 1]
            time.sleep(0.01)
        else:
            self.status = self.driver.get_status()
        self.device.signal("pipe;status", self.status)
        self.recv_channel(str(self.status))

    def wait_until_accepting_packets(self):
        i = 0
        while self.state != THREAD_STATE_ABORT:
            self.update_status()
            status = self.status[1]
            if status == 0:
                raise ConnectionError
            # StateBitWAIT = 0x00002000, 204, 206, 207
            if status & 0x20 == 0:
                break
            time.sleep(0.05)
            self.device.signal("pipe;wait", STATUS_OK, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.

    def wait_finished(self):
        i = 0
        while True:
            self.update_status()
            if self.device.mock:  # Mock controller
                self.status = [255, STATUS_FINISH, 0, 0, 0, 1]
            status = self.status[1]
            if status == 0:
                raise ConnectionError
            if status == STATUS_PACKET_REJECTED:
                self.device.rejected_count += 1
            if status & 0x02 == 0:
                # StateBitPEMP = 0x00000200, Finished = 0xEC, 11101100
                break
            time.sleep(0.05)
            self.device.signal("pipe;wait", status, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.
