
from .lhymicrointerpreter import LhymicroInterpreter
from .lhystudiocontroller import LhystudioController
from .lhystudioemulator import LhystudioEmulator, EgvLoader
from ..lasercommandconstants import *
from ...kernel import (
    Modifier,
    STATE_UNKNOWN,
)
from ...svgelements import Length


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
        kernel = context._kernel

        @context.console_command(
            "+laser", hidden=True, help="turn laser on in place"
        )
        def plus_laser(command, channel, _, args=tuple(), **kwargs):
            spooler = kernel.active_device.spooler
            spooler.job(COMMAND_LASER_ON)

        @context.console_command(
            "-laser", hidden=True, help="turn laser off in place"
        )
        def minus_laser(command, channel, _, args=tuple(), **kwargs):
            spooler = kernel.active_device.spooler
            spooler.job(COMMAND_LASER_ON)

        @context.console_argument("amount", type=Length, help="amount to move in the set direction.")
        @context.console_command(
            ("left", "right", "up", "down"), help="cmd <amount>"
        )
        def direction(command, channel, _, amount=None, args=tuple(), **kwargs):
            active = kernel.active_device
            spooler = active.spooler

            if spooler is None:
                channel(_("Device has no spooler."))
                return
            if amount is None:
                amount = Length("1mm")
            max_bed_height = active.bed_height * 39.3701
            max_bed_width = active.bed_width * 39.3701
            if command.endswith("right"):
                self.dx += amount.value(
                    ppi=1000.0, relative_length=max_bed_width
                )
            elif command.endswith("left"):
                self.dx -= amount.value(
                    ppi=1000.0, relative_length=max_bed_width
                )
            elif command.endswith("up"):
                self.dy -= amount.value(
                    ppi=1000.0, relative_length=max_bed_height
                )
            elif command.endswith("down"):
                self.dy += amount.value(
                    ppi=1000.0, relative_length=max_bed_height
                )
            kernel._console_queue("jog")

        @context.console_command(
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

        @context.console_argument("x", type=Length, help="change in x")
        @context.console_argument("y", type=Length, help="change in y")
        @context.console_command(
            ("move", "move_absolute"), help="move <x> <y>: move to position."
        )
        def move(command, channel, _, x, y, args=tuple(), **kwargs):
            spooler = kernel.active_device.spooler
            if y is None:
                raise SyntaxError
            if not spooler.job_if_idle(self.execute_absolute_position(x, y)):
                channel(_("Busy Error"))

        @context.console_argument("dx", type=Length, help="change in x")
        @context.console_argument("dy", type=Length, help="change in y")
        @context.console_command("move_relative", help="move_relative <dx> <dy>")
        def move_relative(command, channel, _, dx, dy, args=tuple(), **kwargs):
            spooler = kernel.active_device.spooler
            if dy is None:
                raise SyntaxError
            if not spooler.job_if_idle(self.execute_relative_position(dx, dy)):
                channel(_("Busy Error"))

        @context.console_command("home", help="home the laser")
        def home(command, channel, _, args=tuple(), **kwargs):
            spooler = kernel.active_device.spooler
            spooler.job(COMMAND_HOME)

        @context.console_command("unlock", help="unlock the rail")
        def unlock(command, channel, _, args=tuple(), **kwargs):
            spooler = kernel.active_device.spooler
            spooler.job(COMMAND_UNLOCK)

        @context.console_command("lock", help="lock the rail")
        def lock(command, channel, _, args=tuple(), **kwargs):
            spooler = kernel.active_device.spooler
            spooler.job(COMMAND_LOCK)

        context.setting(str, "device_name", "Lhystudios")

        context._quit = False

        context.setting(int, "usb_index", -1)
        context.setting(int, "usb_bus", -1)
        context.setting(int, "usb_address", -1)
        context.setting(int, "usb_serial", -1)
        context.setting(int, "usb_version", -1)

        context.setting(bool, "mock", False)
        context.setting(int, "packet_count", 0)
        context.setting(int, "rejected_count", 0)
        context.setting(bool, "autolock", True)

        context.setting(str, "board", "M2")
        context.setting(int, "bed_width", 310)
        context.setting(int, "bed_height", 210)
        context.setting(bool, "fix_speeds", False)
        self.dx = 0
        self.dy = 0

        context.open_as("module/LhystudioController", "pipe")
        context.open_as("module/LhystudioEmulator", "emulator")
        context.activate("modifier/LhymicroInterpreter", context)
        context.activate("modifier/Spooler")

        context.listen("interpreter;mode", self.on_mode_change)
        context.signal(
            "bed_size", (context.bed_width, context.bed_height)
        )

    def detach(self, *args, **kwargs):
        self.context.unlisten("interpreter;mode", self.on_mode_change)

    def on_mode_change(self, *args):
        self.dx = 0
        self.dy = 0
