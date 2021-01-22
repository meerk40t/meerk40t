from ..basedevice import Interpreter
from ...kernel import Module

"""
MoshiboardDevice is the backend for Moshiboard devices.

The device is primary composed of three main modules.

* A generic spooler to take in lasercode.
* An interpreter to convert lasercode into moshi-programs.
* A controller to send the data to the hardware using moshi protocols.

"""


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("disabled-device/Moshiboard", MoshiboardDevice)


class MoshiboardDevice:
    """
    MoshiboardDevice instance. Connects the MeerK40t frontend to the Moshiboard backend.
    """

    def __init__(self, root, uid=""):
        self.uid = uid
        self.device_name = "Moshiboard"
        self.location_name = "USB"

        # Device specific stuff. Fold into proper kernel commands or delegate to subclass.
        self._device_log = ""
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
        device.register("modifier/MoshiInterpreter", MoshiInterpreter)
        device.register("modifier/MoshiboardController", MoshiboardController)

    def initialize(self, device, channel=None):
        """
        Device initialize.

        :param device:
        :param name:
        :return:
        """
        device.activate("modifier/MoshiboardController")
        device.activate("modifier/MoshiInterpreter")
        device.activate("modifier/Spooler")


class MoshiInterpreter(Interpreter):
    def __init__(self, pipe):
        Interpreter.__init__(self)
        self.pipe = pipe
        self.is_relative = True
        self.laser = False
        self.speed = 20
        self.power = 1000
        self.step = 2
        self.extra_hold = None

    def swizzle(self, b, p7, p6, p5, p4, p3, p2, p1, p0):
        return (
            ((b >> 0) & 1) << p0
            | ((b >> 1) & 1) << p1
            | ((b >> 2) & 1) << p2
            | ((b >> 3) & 1) << p3
            | ((b >> 4) & 1) << p4
            | ((b >> 5) & 1) << p5
            | ((b >> 6) & 1) << p6
            | ((b >> 7) & 1) << p7
        )

    def convert(self, q):
        if q & 1:
            return self.swizzle(q, 7, 6, 2, 4, 3, 5, 1, 0)
        else:
            return self.swizzle(q, 5, 1, 7, 2, 4, 3, 6, 0)

    def reconvert(self, q):
        for m in range(5):
            q = self.convert(q)
        return q

    def set_speed(self, new_speed):
        self.speed = new_speed

    def set_power(self, new_power):
        self.power = new_power

    def set_step(self, new_step):
        self.step = new_step

    def initialize(self, channel=None):
        self.context.setting(bool, "swap_xy", False)
        self.context.setting(bool, "flip_x", False)
        self.context.setting(bool, "flip_y", False)
        self.context.setting(bool, "home_right", False)
        self.context.setting(bool, "home_bottom", False)
        self.context.setting(int, "home_adjust_x", 0)
        self.context.setting(int, "home_adjust_y", 0)

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
        sx = self.context.current_x
        sy = self.context.current_y
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


class MoshiboardController(Module):
    def __init__(self, context, path, uid=""):
        Module.__init__(self, context, path)
        self.usb_log = None
        self.driver = None
        self.status = [0] * 6
        self.usb_state = -1

    def initialize(self, *args, **kwargs):
        self.usb_log = self.context.channel("usb")

    def close(self):
        if self.driver is not None:
            self.driver.close()

    def log(self, info):
        update = str(info) + "\n"
        self.usb_log(update)
