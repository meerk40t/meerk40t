from Kernel import Device, Interpreter
from LaserCommandConstants import *
from zinglplotter import ZinglPlotter

STATE_ABORT = -1
STATE_DEFAULT = 0
STATE_CONCAT = 1
STATE_COMPACT = 2

"""
Ruida device is a stub-backend. It doesn't work as of yet, but should be able to be configured.
"""


class RuidaDevice(Device):
    """
    """
    def __init__(self, root, uid=''):
        Device.__init__(self, root, uid)
        self.uid = uid
        self.device_name = "Ruida"
        self.location_name = "STUB"

        # Device specific stuff. Fold into proper kernel commands or delegate to subclass.
        self._device_log = ''
        self.current_x = 0
        self.current_y = 0

        self.hold_condition = lambda e: False
        self.pipe = None
        self.interpreter = None
        self.spooler = None

    def __repr__(self):
        return "RuidaDevice(uid='%s')" % str(self.uid)


    @staticmethod
    def sub_register(device):
        device.register('module', 'RuidaInterpreter', RuidaInterpreter)

    def initialize(self, device, name=''):
        """
        Device initialize.

        :param device:
        :param name:
        :return:
        """
        self.uid = name


class RuidaInterpreter(Interpreter):
    def __init__(self, pipe):
        Interpreter.__init__(self,pipe=pipe)
        self.pipe = pipe
        self.is_relative = True
        self.laser = False
        self.speed = 30
        self.power = 1000
        self.step = 2
        self.extra_hold = None

    def set_speed(self, new_speed):
        self.speed = new_speed

    def set_power(self, new_power):
        self.power = new_power

    def set_step(self, new_step):
        self.step = new_step

    def initialize(self):
        self.device.setting(bool, "swap_xy", False)
        self.device.setting(bool, "flip_x", False)
        self.device.setting(bool, "flip_y", False)
        self.device.setting(bool, "home_right", False)
        self.device.setting(bool, "home_bottom", False)
        self.device.setting(int, "home_adjust_x", 0)
        self.device.setting(int, "home_adjust_y", 0)

    def laser_on(self):
        pass

    def laser_off(self):
        pass

    def default_mode(self):
        pass

    def move_relative(self, x, y):
        pass

    def move_absolute(self, x, y):
        pass

    def move(self, x, y):
        sx = self.device.current_x
        sy = self.device.current_y
        if self.is_relative:
            x += sx
            y += sy
        pass

    def home(self):
        pass

    def lock_rail(self):
        pass

    def unlock_rail(self):
        pass

    def command(self, command, values=None):
        if command == COMMAND_LASER_OFF:
            self.laser_off()
        elif command == COMMAND_LASER_ON:
            self.laser_on()
        elif command == COMMAND_RAPID_MOVE:
            self.default_mode()
            x, y = values
            self.move(x, y)
        elif command == COMMAND_SHIFT:
            x, y = values
            self.laser_off()
            self.move(x, y)
        elif command == COMMAND_MOVE:
            x, y = values
            sx = self.device.current_x
            sy = self.device.current_y
            self.move(x, y)
        elif command == COMMAND_CUT:
            x, y = values
            self.laser_on()
            self.move(x, y)
        elif command == COMMAND_HSTEP:
            # self.v_switch()
            pass
        elif command == COMMAND_VSTEP:
            # self.h_switch()
            pass
        elif command == COMMAND_HOME:
            self.home()
        elif command == COMMAND_LOCK:
            self.lock_rail()
        elif command == COMMAND_UNLOCK:
            self.unlock_rail()
        elif command == COMMAND_PLOT:
            path = values
            if len(path) == 0:
                return
            first_point = path.first_point
            self.move_absolute(first_point[0], first_point[1])
            for x, y, on in ZinglPlotter.plot_path(path):
                self.move_absolute(x, y)
        elif command == COMMAND_RASTER:
            raster = values
            for x, y, on in raster.plot():
                if on:
                    self.laser_on()
                else:
                    self.laser_off()
                self.move_absolute(x, y)
        elif command == COMMAND_CUT_QUAD:
            cx, cy, x, y, = values
            sx = self.device.current_x
            sy = self.device.current_y
            for x, y, on in ZinglPlotter.plot_quad_bezier(sx, sy, cx, cy, x, y):
                if on:
                    self.laser_on()
                else:
                    self.laser_off()
                self.move_absolute(x, y)
        elif command == COMMAND_CUT_CUBIC:
            c1x, c1y, c2x, c2y, ex, ey = values
            sx = self.device.current_x
            sy = self.device.current_y
            for x, y, on in ZinglPlotter.plot_cubic_bezier(sx, sy, c1x, c1y, c2x, c2y, ex, ey):
                if on:
                    self.laser_on()
                else:
                    self.laser_off()
                self.move_absolute(x, y)
        elif command == COMMAND_SET_SPEED:
            speed = values
            self.set_speed(speed)
        elif command == COMMAND_SET_POWER:
            power = values
            self.set_power(power)
        elif command == COMMAND_SET_STEP:
            step = values
            self.set_step(step)
        elif command == COMMAND_SET_D_RATIO:
            pass
        elif command == COMMAND_SET_DIRECTION:
            pass
        elif command == COMMAND_SET_INCREMENTAL:
            self.is_relative = True
        elif command == COMMAND_SET_ABSOLUTE:
            self.is_relative = False
        elif command == COMMAND_SET_POSITION:
            x, y = values
            self.device.current_x = x
            self.device.current_y = y
        elif command == COMMAND_MODE_COMPACT:
            pass
        elif command == COMMAND_MODE_DEFAULT:
            self.default_mode()
        elif command == COMMAND_MODE_COMPACT_SET:
            pass
        elif command == COMMAND_MODE_DEFAULT:
            pass
        elif command == COMMAND_MODE_CONCAT:
            pass
        elif command == COMMAND_WAIT:
            t = values
            self.next_run = t
        elif command == COMMAND_WAIT_BUFFER_EMPTY:
            self.extra_hold = lambda e: len(self.pipe) == 0
        elif command == COMMAND_BEEP:
            print('\a')  # Beep.
        elif command == COMMAND_FUNCTION:
            t = values
            if callable(t):
                t()
        elif command == COMMAND_SIGNAL:
            if isinstance(values, str):
                self.device.signal(values, None)
            elif len(values) >= 2:
                self.device.signal(values[0], *values[1:])
        elif command == COMMAND_CLOSE:
            self.default_mode()
        elif command == COMMAND_OPEN:
            self.state = STATE_DEFAULT
            self.device.signal('interpreter;mode', self.state)
        elif command == COMMAND_RESET:
            self.pipe.realtime_write(b'I*\n')
            self.state = STATE_DEFAULT
            self.device.signal('interpreter;mode', self.state)
        elif command == COMMAND_PAUSE:
            pass
        elif command == COMMAND_STATUS:
            pass
        elif command == COMMAND_RESUME:
            pass  # This command can't be processed since we should be paused.

    def realtime_command(self, command, values=None):
        if command == COMMAND_SET_SPEED:
            speed = values
            self.set_speed(speed)
        elif command == COMMAND_SET_POWER:
            power = values
            self.set_power(power)
        elif command == COMMAND_SET_STEP:
            step = values
            self.set_step(step)
        elif command == COMMAND_SET_D_RATIO:
            pass
        elif command == COMMAND_SET_POSITION:
            x, y = values
            self.device.current_x = x
            self.device.current_y = y
        elif command == COMMAND_RESET:
            pass
        elif command == COMMAND_PAUSE:
            pass
        elif command == COMMAND_STATUS:
            pass
        elif command == COMMAND_RESUME:
            pass

    def swizzle(self, b):
        b ^= (b >> 7) & 0xFF
        b ^= (b << 7) & 0xFF
        b ^= (b >> 7) & 0xFF
        b ^= 0xB0
        b ^= 0x38
        b = (b + 1) & 0xFF
        return b

    def unswizzle(self, b):
        b = (b - 1) & 0xFF
        b ^= 0xB0
        b ^= 0x38
        b ^= (b >> 7) & 0xFF
        b ^= (b << 7) & 0xFF
        b ^= (b >> 7) & 0xFF
        return b