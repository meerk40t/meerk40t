from meerk40t.device.lasercommandconstants import COMMAND_LASER_OFF, COMMAND_SET_ABSOLUTE, COMMAND_MODE_RAPID, \
    COMMAND_MOVE, COMMAND_SET_INCREMENTAL, COMMAND_LASER_ON, COMMAND_HOME, COMMAND_UNLOCK, COMMAND_LOCK
from meerk40t.device.spooler import Spooler
from meerk40t.kernel import CommandMatchRejected, Modifier
from meerk40t.svgelements import Length

DRIVER_STATE_RAPID = 0
DRIVER_STATE_FINISH = 1
DRIVER_STATE_PROGRAM = 2
DRIVER_STATE_RASTER = 3
DRIVER_STATE_MODECHANGE = 4

PLOT_START = 2048
PLOT_FINISH = 256
PLOT_RAPID = 4
PLOT_JOG = 2
PLOT_SETTING = 128
PLOT_AXIS = 64
PLOT_DIRECTION = 32
PLOT_LEFT_UPPER = 512
PLOT_RIGHT_LOWER = 1024


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.add_modifier(Devices)


class Devices(Modifier):
    def __init__(self, kernel, *args, **kwargs):
        Modifier.__init__(self, kernel, "devices")

        for d in kernel.derivable(self.path):
            self.get_or_make_device(d)

        _ = self._

        @kernel.console_command(
            "device",
            regex=True,
            help=_("device"),
            input_type=None,
            output_type="device",
        )
        def device_base(command, channel, _, remainder=None, **kwargs):
            if len(command) > 6:
                device_name = command[6:]
                self.active = device_name
            else:
                try:
                    device_name = self.active.name
                except AttributeError:
                    channel(_("Active device not valid and no device specified"))
                    return
            dev = self.get_or_make_device(device_name)
            return "device", dev

        @kernel.console_command(
            "activate",
            help=_("delegate commands to currently selected device"),
            input_type="device",
            output_type="device",
        )
        def device(channel, _, data, **kwargs):
            self.active = data
            channel(_("Activated device %s." % data.name))
            return "device", data

        @kernel.console_command(
            "list",
            help=_("list devices"),
            input_type="device",
            output_type="device",
        )
        def list_devices(channel, _, data, **kwargs):
            device_context = kernel.get_context("devices")
            channel(_("----------"))
            channel(_("Devices:"))
            index = 0
            for d in device_context.derivable():
                channel("%d: %s" % (index, str(d)))
                index += 1
            channel("----------")
            return "device", data

        @kernel.console_command(
            "delete",
            help=_("delete"),
            input_type="device",
        )
        def delete(channel, _, data, **kwargs):
            self.shutdown_device(data)
            kernel.clear_persistent(data.path)

        @kernel.console_command(
            "spool",
            help=_("spool <command>"),
            regex=True,
            input_type=("device", "plan"),
            output_type="spooler",
        )
        def spool(
                command, channel, _, data=None, data_type=None, remainder=None, **kwgs
        ):
            if len(command) > 5:
                device_name = command[5:]
                self.active = device_name
            if data is not None and data_type == "plan":
                plan = data
                # If plan data is in data, then we copy that and move on to next step.
                if self.active is None:
                    data = self.active.spooler, self.active.name
                    data[0].jobs(plan.plan)
                    channel(_("Spooled Plan."))
                    self.signal("plan", plan.name, 6)
                data = self.active
            spooler = data.spooler

            if remainder is None:
                channel(_("----------"))
                channel(_("Spoolers:"))
                for d, d_name in enumerate(self.match("device", True)):
                    channel("%d: %s" % (d, d_name))
                channel(_("----------"))
                channel(_("Spooler %s:" % data.name))
                for s, op_name in enumerate(spooler.queue):
                    channel("%d: %s" % (s, op_name))
                channel(_("----------"))

            return "spooler", (spooler, data.name)

        @kernel.console_command(
            "list",
            help=_("spool<?> list"),
            input_type="spooler",
            output_type="spooler",
        )
        def spooler_list(command, channel, _, data_type=None, data=None, **kwgs):
            spooler, device_name = data
            channel(_("----------"))
            channel(_("Spoolers:"))
            for d, d_name in enumerate(self.match("device", True)):
                channel("%d: %s" % (d, d_name))
            channel(_("----------"))
            channel(_("Spooler %s:" % device_name))
            for s, op_name in enumerate(spooler.queue):
                channel("%d: %s" % (s, op_name))
            channel(_("----------"))
            return data_type, data

        @kernel.console_argument("op", type=str, help=_("unlock, origin, home, etc"))
        @kernel.console_command(
            "send",
            help=_("send a plan-command to the spooler"),
            input_type="spooler",
            output_type="spooler",
        )
        def spooler_send(
                command, channel, _, data_type=None, op=None, data=None, **kwgs
        ):
            spooler, device_name = data
            if op is None:
                raise SyntaxError
            try:
                for command_name in self.match("plan/%s" % op):
                    plan_command = self.registered[command_name]
                    spooler.job(plan_command)
                    return data_type, data
            except (KeyError, IndexError):
                pass
            channel(_("No plan command found."))
            return data_type, data

        @kernel.console_command(
            "clear",
            help=_("Clear the spooler"),
            input_type="spooler",
            output_type="spooler",
        )
        def spooler_clear(command, channel, _, data_type=None, data=None, **kwgs):
            spooler, device_name = data
            spooler.clear_queue()
            return data_type, data

        def execute_absolute_position(position_x, position_y):
            x_pos = Length(position_x).value(
                ppi=1000.0, relative_length=self.root.bed_width
            )
            y_pos = Length(position_y).value(
                ppi=1000.0, relative_length=self.root.bed_height
            )

            def move():
                yield COMMAND_SET_ABSOLUTE
                yield COMMAND_MODE_RAPID
                yield COMMAND_MOVE, int(x_pos), int(y_pos)

            return move

        def execute_relative_position(position_x, position_y):
            x_pos = Length(position_x).value(
                ppi=1000.0, relative_length=self.root.bed_width
            )
            y_pos = Length(position_y).value(
                ppi=1000.0, relative_length=self.root.bed_height
            )

            def move():
                yield COMMAND_SET_INCREMENTAL
                yield COMMAND_MODE_RAPID
                yield COMMAND_MOVE, int(x_pos), int(y_pos)
                yield COMMAND_SET_ABSOLUTE

            return move

        @kernel.console_command(
            "+laser",
            hidden=True,
            input_type=("spooler", None),
            output_type="spooler",
            help=_("turn laser on in place"),
        )
        def plus_laser(data, **kwgs):
            if data is None:
                if self.active is None:
                    data = self.active.spooler, self.active.name
                else:
                    return
            spooler, device_name = data
            spooler.job(COMMAND_LASER_ON)
            return "spooler", data

        @kernel.console_command(
            "-laser",
            hidden=True,
            input_type=("spooler", None),
            output_type="spooler",
            help=_("turn laser off in place"),
        )
        def minus_laser(data, **kwgs):
            if data is None:
                if self.active is None:
                    data = self.active.spooler, self.active.name
                else:
                    return
            spooler, device_name = data
            spooler.job(COMMAND_LASER_OFF)
            return "spooler", data

        @kernel.console_argument(
            "amount", type=Length, help=_("amount to move in the set direction.")
        )
        @kernel.console_command(
            ("left", "right", "up", "down"),
            input_type=("spooler", None),
            output_type="spooler",
            help=_("cmd <amount>"),
        )
        def direction(command, channel, _, data=None, amount=None, **kwgs):
            if data is None:
                if self.active is None:
                    data = self.active.spooler, self.active.name
                else:
                    return
            spooler, device_name = data
            if amount is None:
                amount = Length("1mm")
            max_bed_height = self.root.bed_height
            max_bed_width = self.root.bed_width
            if not hasattr(spooler, "_dx"):
                spooler._dx = 0
            if not hasattr(spooler, "_dy"):
                spooler._dy = 0
            if command.endswith("right"):
                spooler._dx += amount.value(ppi=1000.0, relative_length=max_bed_width)
            elif command.endswith("left"):
                spooler._dx -= amount.value(ppi=1000.0, relative_length=max_bed_width)
            elif command.endswith("up"):
                spooler._dy -= amount.value(ppi=1000.0, relative_length=max_bed_height)
            elif command.endswith("down"):
                spooler._dy += amount.value(ppi=1000.0, relative_length=max_bed_height)
            kernel.console(".timer 1 0 spool%s jog\n" % device_name)
            return "spooler", data

        @kernel.console_option("force", "f", type=bool, action="store_true")
        @kernel.console_command(
            "jog",
            hidden=True,
            input_type="spooler",
            output_type="spooler",
            help=_("executes outstanding jog buffer"),
        )
        def jog(command, channel, _, data, force=False, **kwgs):
            if data is None:
                if self.active is None:
                    data = self.active.spooler, self.active.name
                else:
                    return
            spooler, device_name = data
            try:
                idx = int(spooler._dx)
                idy = int(spooler._dy)
            except AttributeError:
                return
            if idx == 0 and idy == 0:
                return
            if force:
                spooler.job(execute_relative_position(idx, idy))
            else:
                if spooler.job_if_idle(execute_relative_position(idx, idy)):
                    channel(_("Position moved: %d %d") % (idx, idy))
                    spooler._dx -= idx
                    spooler._dy -= idy
                else:
                    channel(_("Busy Error"))
            return "spooler", data

        @kernel.console_option("force", "f", type=bool, action="store_true")
        @kernel.console_argument("x", type=Length, help=_("change in x"))
        @kernel.console_argument("y", type=Length, help=_("change in y"))
        @kernel.console_command(
            ("move", "move_absolute"),
            input_type=("spooler", None),
            output_type="spooler",
            help=_("move <x> <y>: move to position."),
        )
        def move(channel, _, x, y, data=None, force=False, **kwgs):
            if data is None:
                if self.active is None:
                    data = self.active.spooler, self.active.name
                else:
                    return
            spooler, device_name = data
            if y is None:
                raise SyntaxError
            if force:
                spooler.job(execute_absolute_position(x, y))
            else:
                if not spooler.job_if_idle(execute_absolute_position(x, y)):
                    channel(_("Busy Error"))
            return "spooler", data

        @kernel.console_option("force", "f", type=bool, action="store_true")
        @kernel.console_argument("dx", type=Length, help=_("change in x"))
        @kernel.console_argument("dy", type=Length, help=_("change in y"))
        @kernel.console_command(
            "move_relative",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("move_relative <dx> <dy>"),
        )
        def move_relative(channel, _, dx, dy, data=None, force=False, **kwgs):
            if data is None:
                if self.active is None:
                    data = self.active.spooler, self.active.name
                else:
                    return
            spooler, device_name = data
            if dy is None:
                raise SyntaxError
            if force:
                spooler.job(execute_relative_position(dx, dy))
            else:
                if not spooler.job_if_idle(execute_relative_position(dx, dy)):
                    channel(_("Busy Error"))
            return "spooler", data

        @kernel.console_argument("x", type=Length, help=_("x offset"))
        @kernel.console_argument("y", type=Length, help=_("y offset"))
        @kernel.console_command(
            "home",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("home the laser"),
        )
        def home(x=None, y=None, data=None, **kwgs):
            if data is None:
                if self.active is None:
                    data = self.active.spooler, self.active.name
                else:
                    return
            spooler, device_name = data
            if x is not None and y is not None:
                x = x.value(ppi=1000.0, relative_length=self.root.bed_width)
                y = y.value(ppi=1000.0, relative_length=self.root.bed_height)
                spooler.job(COMMAND_HOME, int(x), int(y))
                return "spooler", data
            spooler.job(COMMAND_HOME)
            return "spooler", data

        @kernel.console_command(
            "unlock",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("unlock the rail"),
        )
        def unlock(data=None, **kwgs):
            if data is None:
                if self.active is None:
                    data = self.active.spooler, self.active.name
                else:
                    return
            spooler, device_name = data
            spooler.job(COMMAND_UNLOCK)
            return "spooler", data

        @kernel.console_command(
            "lock",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("lock the rail"),
        )
        def lock(data, **kwgs):
            if data is None:
                if self.active is None:
                    data = self.active.spooler, self.active.name
                else:
                    return
            spooler, device_name = data
            spooler.job(COMMAND_LOCK)
            return "spooler", data

        for i in range(5):
            self.get_or_make_device(str(i))

    def get_or_make_device(self, device_name):
        device = self.derive(device_name)
        device.name = device_name
        driver_type = device.setting(str, "type", "lhystudios")
        autoboot = device.setting(bool, "boot", True)
        if not hasattr(device, "spooler"):
            device.spooler = Spooler(device, device_name)
        if not hasattr(device, "instance"):
            if driver_type is not None:
                device.driver_class = self.registered["driver/%s" % driver_type]
            else:
                device.driver_class = None

            if device.driver_class is not None and autoboot:
                device.instance = device.driver_class(self, device, driver_type)
            else:
                device.instance = None
        if device not in self.aspects:
            self.add_aspect(device)
        return device

    def shutdown_device(self, device):
        device.shutdown()
        device.instance.shutdown()
        self.aspects.remove(self.aspects.index(device))

    def available_devices(self):
        return list(self.derivable())

    def device_names(self):
        return [str(i) for i in self.derivable()]
