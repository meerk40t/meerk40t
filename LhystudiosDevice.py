import os
import threading

from CH341DriverBase import *
from Kernel import *
from LaserSpeed import LaserSpeed
from zinglplotter import ZinglPlotter
from svgelements import *

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
        self.device_location = "USB"
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
        device.register('load', 'EgvLoader', EgvLoader)

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

        self.signal('bed_size', (self.bed_width, self.bed_height))

        self.control_instance_add("Debug Device", self._start_debugging)

        pipe = self.open('module', "LhystudioController", instance_name='pipe')
        self.open('module', "LhymicroInterpreter", instance_name='interpreter', pipe=pipe)
        self.open('module', "Spooler", instance_name='spooler')

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
        self.pipe._buffer = b''
        self.pipe._queue = b''
        self.device.signal('pipe;buffer', 0)
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
    K40 Controller controls the Lhystudios boards sending any queued data to the USB when the signal is not busy.

    This is registered in the kernel as a module. Saving a few persistent settings like packet_count and registering
    a couple controls like Connect_USB.

    This is also a Pipe. Elements written to the Controller are sent to the USB to the matched device. Opening and
    closing of the pipe are dealt with internally. There are three primary monitor data channels. 'send', 'recv' and
    'usb'. They display the reading and writing of information to/from the USB and the USB connection log, providing
    information about the connecting and error status of the USB device.
    """

    def __init__(self, device=None, uid=''):
        Module.__init__(self, device=device)
        Pipe.__init__(self)
        self.usb_log = None
        self.state = STATE_UNKNOWN

        self._thread = None
        self._buffer = b''  # Threadsafe buffered commands to be sent to controller.
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

    def initialize(self):
        self.device.setting(int, 'packet_count', 0)
        self.device.setting(int, 'rejected_count', 0)

        self.device.control_instance_add("Connect_USB", self.open)
        self.device.control_instance_add("Disconnect_USB", self.close)
        self.device.control_instance_add("Status Update", self.update_status)
        self.usb_log = self.device.channel_open("usb", buffer=20)
        self.send_channel = self.device.channel_open('send')
        self.recv_channel = self.device.channel_open('recv')
        self.pipe_channel = self.device.channel_open('pipe')
        self.reset()

        def abort_wait():
            self.abort_waiting = True

        self.device.control_instance_add("Wait Abort", abort_wait)

        def pause_k40():
            self.state = STATE_PAUSE
            self.start()

        self.device.control_instance_add("Pause", pause_k40)

        def resume_k40():
            self.state = STATE_ACTIVE
            self.start()

        self.device.control_instance_add("Resume", resume_k40)

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
            self.driver.index = self.device.usb_index
            self.driver.bus = self.device.usb_bus
            self.driver.address = self.device.usb_address
            self.driver.serial = self.device.usb_serial
            self.driver.chipv = self.device.usb_version
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
        if self.state == STATE_PAUSE:
            self.state = STATE_ACTIVE
        return self

    def start(self):
        """
        Controller state change to Started.
        :return:
        """
        if self._thread is None or not self._thread.is_alive():
            self._thread = self.device.threaded(self._thread_data_send)
            self.update_state(STATE_INITIALIZE)

    def resume(self):
        if self.state == STATE_TERMINATE:
            # We cannot resume an aborted process without specifically calling reset.
            return
        if self.state == STATE_END:
            # Ended threats must call reset and start.
            return
        if self.state == STATE_PAUSE:
            self.update_state(STATE_ACTIVE)

    def pause(self):
        if self.state == STATE_TERMINATE:
            # We cannot pause an aborted process without specifically calling reset.
            return
        if self.state == STATE_END:
            # We don't allow this state change.
            return
        if self.state == STATE_INITIALIZE:
            self.start()
            self.update_state(STATE_PAUSE)
        if self.state == STATE_ACTIVE or self.state == STATE_IDLE:
            self.update_state(STATE_PAUSE)

    def abort(self):
        self._buffer = b''
        self._queue = b''
        self.device.signal('pipe;buffer', 0)
        self.update_state(STATE_TERMINATE)

    def reset(self):
        self.update_state(STATE_INITIALIZE)
        self.device.signal('pipe;thread', self.state)

    def stop(self):
        self.abort()

    def update_usb_state(self, code):
        """
        Process updated values for the usb status. Sending it to the usb channel and sending update signals.

        :param code: usb status code.
        :return:
        """
        if isinstance(code, int):
            self._usb_state = code
            name = get_name_for_status(code, translation=self.device.device_root.translation)
            self.usb_log(str(name))
            self.device.signal('pipe;usb_state', code)
            self.device.signal('pipe;usb_state_text', name)
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
                                               state_listener=self.update_usb_state)
            driver.open()
            chip_version = driver.get_chip_version()
            self.update_usb_state(INFO_USB_CHIP_VERSION | chip_version)
            self.device.signal('pipe;chipv', chip_version)
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
            self.device.signal('pipe;chipv', chip_version)
            self.update_usb_state(INFO_USB_DRIVER | STATE_DRIVER_CH341)
            self.update_usb_state(STATE_CONNECTED)
        except ConnectionRefusedError:
            self.driver = None

    def update_state(self, state):
        self.state = state
        if self.device is not None:
            self.device.signal('pipe;thread', self.state)

    def update_buffer(self):
        if self.device is not None:
            self.device.signal('pipe;buffer', len(self._buffer))

    def update_packet(self, packet):
        if self.device is not None:
            self.device.signal('pipe;packet', convert_to_list_bytes(packet))
            self.device.signal('pipe;packet_text', packet)
            self.send_channel(str(packet))

    def _thread_data_send(self):
        """
        Main threaded function to send data. While the controller is working the thread
        will be doing work in this function.
        """
        self._main_lock.acquire(True)
        self.count = 0
        if self.state == STATE_INITIALIZE:
            # If we are initialized. Change that to active since we're running.
            self.update_state(STATE_ACTIVE)
        while self.state != STATE_END and self.state != STATE_TERMINATE:
            if self.state == STATE_PAUSE or self.state == STATE_BUSY:
                # If we are paused just keep sleeping until the state changes.
                time.sleep(1)
                continue
            if self.state == STATE_ACTIVE or self.state == STATE_IDLE:
                try:
                    # We tried tried to process the queue.
                    queue_processed = self.process_queue()
                    self.refuse_counts = 0
                except ConnectionRefusedError:
                    # The attempt refused the connection.
                    self.refuse_counts += 1
                    time.sleep(3)  # 3 second sleep on failed connection attempt.
                    if self.refuse_counts >= self.max_attempts:
                        # We were refused too many times, kill the thread.
                        self.update_state(STATE_TERMINATE)
                        self.device.signal('pipe;error', self.refuse_counts)
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
                    if self.state != STATE_PAUSE and self.state != STATE_ACTIVE:
                        self.update_state(STATE_ACTIVE)
                    self.count = 0
                    continue
                else:
                    # No packet could be sent.
                    if self.state != STATE_PAUSE and self.state != STATE_IDLE:
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
            self._buffer = self._preempt + self._buffer
            self._preempt = b''
            self._preempt_lock.release()
            self.update_buffer()

        if len(self._buffer) == 0:
            return False

        # Find buffer of 30 or containing '\n'.
        find = self._buffer.find(b'\n', 0, 30)
        if find == -1:  # No end found.
            length = min(30, len(self._buffer))
        else:  # Line end found.
            length = min(30, len(self._buffer), find + 1)
        packet = self._buffer[:length]

        # edge condition of catching only pipe command without '\n'
        if packet.endswith((b'-', b'*', b'&', b'!')):
            packet += self._buffer[length:length + 1]
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
        if self.state == STATE_PAUSE:
            return False  # Abort due to pause.
        # Packet is prepared and ready to send.
        if self.device.mock:
            self.update_usb_state(STATE_DRIVER_MOCK)
        else:
            self.open()

        if len(packet) != 30 and len(packet) != 0:
            # We could only generate a partial packet, throw it back
            return False
        self.wait_until_accepting_packets()
        if self.state == STATE_PAUSE:
            return False  # Paused during packet fetch.
        self.send_packet(packet)
        attempts = 0
        status = 0
        while attempts < 300:  # 200 * 300 = 60,000 = 60 seconds.
            try:
                self.update_status()
                status = self._status[1]
                if status != 0:
                    break
            except ConnectionError:
                # we can't throw raise these, we must report that the packet was sent.
                attempts += 1
        if status == STATUS_PACKET_REJECTED:
            self.device.rejected_count += 1
            # The packet was rejected. The sent data was not accepted. Return False.
            return False
        elif status == 0:
            raise ConnectionError  # Broken pipe. 300 attempts. Could not confirm packet.
        if status == STATUS_FINISH and post_send_command == self.wait_finished:
            # The confirmation reply says we finished, and we were going to wait for that, so let's pass.
            post_send_command = None
        self.device.packet_count += 1  # Everything went off without a problem.

        # Packet was processed.
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
        if self.device.mock:
            time.sleep(0.04)
        else:
            packet = b'\x00' + packet + bytes([onewire_crc_lookup(packet)])
            self.driver.write(packet)
        self.update_packet(packet)

    def update_status(self):
        if self.device.mock:
            from random import randint
            if randint(0, 5) == 0:
                self._status = [255, STATUS_PACKET_REJECTED, 0, 0, 0, 1]
            else:
                self._status = [255, STATUS_OK, 0, 0, 0, 1]
            time.sleep(0.01)
        else:
            self._status = self.driver.get_status()
        if self.device is not None:
            self.device.signal('pipe;status', self._status)
            self.recv_channel(str(self._status))

    def wait_until_accepting_packets(self):
        i = 0
        while self.state != STATE_TERMINATE:
            self.update_status()
            status = self._status[1]
            if status == 0:
                raise ConnectionError
            # StateBitWAIT = 0x00002000, 204, 206, 207
            if status & 0x20 == 0:
                break
            time.sleep(0.05)
            if self.device is not None:
                self.device.signal('pipe;wait', STATUS_OK, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.

    def wait_finished(self):
        i = 0
        while True:
            self.update_status()
            if self.device.mock:  # Mock controller
                self._status = [255, STATUS_FINISH, 0, 0, 0, 1]
            status = self._status[1]
            if status == 0:
                raise ConnectionError
            if status == STATUS_PACKET_REJECTED:
                self.device.rejected_count += 1
            if status & 0x02 == 0:
                # StateBitPEMP = 0x00000200, Finished = 0xEC, 11101100
                break
            time.sleep(0.05)
            if self.device is not None:
                self.device.signal('pipe;wait', status, i)
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
