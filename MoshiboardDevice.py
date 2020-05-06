from Kernel import *
from LaserCommandConstants import *
from zinglplotter import ZinglPlotter
from CH341DriverBase import *

"""
MoshiboardDevice is the backend for Moshiboard devices.

The device is primary composed of three main modules.

* A generic spooler to take in lasercode.
* An interpreter to convert lasercode into moshi-programs.
* A controller to send the data to the hardware using moshi protocols.

"""


class MoshiboardDevice(Device):
    """
    MoshiboardDevice instance. Connects the MeerK40t frontend to the Moshiboard backend.
    """
    def __init__(self, root, uid=''):
        Device.__init__(self, root, uid)
        self.uid = uid
        self.device_name = "Moshiboard"
        self.location_name = "USB"

        # Device specific stuff. Fold into proper kernel commands or delegate to subclass.
        self._device_log = ''
        self.current_x = 0
        self.current_y = 0

        self.hold_condition = lambda e: False
        self.pipe = None
        self.interpreter = None
        self.spooler = None

    def __repr__(self):
        return "MoshiboardDevice(uid='%s')" % str(self.uid)

    @staticmethod
    def sub_register(device):
        device.register('module', 'MoshiInterpreter', MoshiInterpreter)
        device.register('module', 'MoshiboardController', MoshiboardController)

    def initialize(self, device, name=''):
        """
        Device initialize.

        :param device:
        :param name:
        :return:
        """
        self.uid = name
        pipe = self.open('module', "MoshiboardController", instance_name='pipe')
        self.open('module', "MoshiInterpreter", instance_name='interpreter', pipe=pipe)
        self.open('module', "Spooler", instance_name='spooler')


class MoshiInterpreter(Interpreter):
    def __init__(self, pipe):
        Interpreter.__init__(self,pipe=pipe)
        self.pipe = pipe
        self.is_relative = True
        self.laser = False
        self.speed = 20
        self.power = 1000
        self.step = 2
        self.extra_hold = None

    def swizzle(self, b, p7, p6, p5, p4, p3, p2, p1, p0):
        return ((b >> 0) & 1) << p0 | ((b >> 1) & 1) << p1 | \
               ((b >> 2) & 1) << p2 | ((b >> 3) & 1) << p3 | \
               ((b >> 4) & 1) << p4 | ((b >> 5) & 1) << p5 | \
               ((b >> 6) & 1) << p6 | ((b >> 7) & 1) << p7

    def convert(self, q):
        if q & 1:
            return swizzle(q, 7, 6, 2, 4, 3, 5, 1, 0)
        else:
            return swizzle(q, 5, 1, 7, 2, 4, 3, 6, 0)

    def reconvert(self, q):
        for m in range(5):
            q = convert(q)
        return q

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
            self.move(x, y)
        elif command == COMMAND_CUT:
            x, y = values
            self.laser_on()
            self.move(x, y)
        elif command == COMMAND_HSTEP:
            pass
        elif command == COMMAND_VSTEP:
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
            pass
        elif command == COMMAND_RESET:
            pass
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


class MoshiboardController(Module, Pipe):
    def __init__(self, device=None, uid=''):
        Module.__init__(self, device=device)
        Pipe.__init__(self)
        self.usb_log = None
        self.driver = None
        self.status = [0] * 6
        self.usb_state = -1

    def initialize(self):
        self.usb_log = self.device.channel_open("usb")

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

    def log(self, info):
        update = str(info) + '\n'
        self.usb_log(update)

    def state_listener(self, code):
        if isinstance(code, int):
            self.usb_state = code
            name = get_name_for_status(code, translation=self.device.device_root.translation)
            self.log(name)
            self.device.signal("pipe;usb_state", code)
            self.device.signal("pipe;usb_status", name)
        else:
            self.log(str(code))

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
