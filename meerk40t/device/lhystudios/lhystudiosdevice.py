from ...kernel import STATE_UNKNOWN, Modifier
from ...svgelements import Length
from ..lasercommandconstants import *
from .lhymicrointerpreter import LhymicroInterpreter
from .lhystudiocontroller import LhystudioController
from .lhystudioemulator import EgvLoader, LhystudioEmulator


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


class LhystudiosDevice(Modifier):
    """
    LhystudiosDevice instance. Serves as a device instance for a lhymicro-gl based device.
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        context.device_name = "Lhystudios"
        context.device_location = "USB"
        self.state = STATE_UNKNOWN
        self.dx = 0
        self.dy = 0
        self.bed_dim = context.get_context("/")
        self.bed_dim.setting(int, "bed_width", 310)
        self.bed_dim.setting(int, "bed_height", 210)

    def __repr__(self):
        return "LhystudiosDevice()"

    @staticmethod
    def sub_register(device):
        device.register("modifier/LhymicroInterpreter", LhymicroInterpreter)
        device.register("module/LhystudioController", LhystudioController)
        device.register("module/LhystudioEmulator", LhystudioEmulator)
        device.register("load/EgvLoader", EgvLoader)

    def attach(self, *a, **kwargs):
        context = self.context
        root_context = context.get_context("/")
        kernel = context._kernel
        context.setting(str, "device_name", "Lhystudios")

        context._quit = False

        context.setting(int, "usb_index", -1)
        context.setting(int, "usb_bus", -1)
        context.setting(int, "usb_address", -1)
        context.setting(int, "usb_version", -1)

        context.setting(bool, "mock", False)
        context.setting(int, "packet_count", 0)
        context.setting(int, "rejected_count", 0)
        context.setting(bool, "autolock", True)

        context.setting(str, "board", "M2")
        context.setting(bool, "fix_speeds", False)

        self.dx = 0
        self.dy = 0

        context.open_as("module/LhystudioController", "pipe")
        context.open_as("module/LhystudioEmulator", "emulator")
        context.activate("modifier/LhymicroInterpreter", context)
        context.activate("modifier/Spooler")

        context.listen("interpreter;mode", self.on_mode_change)
        context.signal("bed_size", (self.bed_dim.bed_width, self.bed_dim.bed_height))

    def detach(self, *args, **kwargs):
        self.context.unlisten("interpreter;mode", self.on_mode_change)

    def on_mode_change(self, *args):
        self.dx = 0
        self.dy = 0
