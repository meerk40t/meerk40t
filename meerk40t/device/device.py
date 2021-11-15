import socket
import threading
import time

from meerk40t.core.spoolers import Spooler
from meerk40t.kernel import Service
from meerk40t.kernel import CommandMatchRejected

from meerk40t.svgelements import Length
from ..core.cutcode import LaserSettings

from ..device.lasercommandconstants import *


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.add_service("device", DefaultDevice(kernel))
    elif lifecycle == "boot":
        context = kernel.get_context("default_device")
        _ = context._
        choices = [
            {
                "attr": "bedwidth",
                "object": context,
                "default": 12205.0,
                "type": float,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
            },
            {
                "attr": "bedheight",
                "object": context,
                "default": 8268.0,
                "type": float,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
            },
            {
                "attr": "scale_x",
                "object": context,
                "default": 1.000,
                "type": float,
                "label": _("X Scale Factor"),
                "tip": _(
                    "Scale factor for the X-axis. This defines the ratio of mils to steps. This is usually at 1:1 steps/mils but due to functional issues it can deviate and needs to be accounted for"
                ),
            },
            {
                "attr": "scale_y",
                "object": context,
                "default": 1.000,
                "type": float,
                "label": _("Y Scale Factor"),
                "tip": _(
                    "Scale factor for the Y-axis. This defines the ratio of mils to steps. This is usually at 1:1 steps/mils but due to functional issues it can deviate and needs to be accounted for"
                ),
            },
        ]
        context.register_choices("bed_dim", choices)


class DefaultDevice(Service):
    """
    Default Device is a mock device service. It provides no actual device.

    Default Device simply provides the require attributes for a device.
    """

    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "default_device")
        self.name = "Default Device"
        self.current_x = 0.0
        self.current_y = 0.0
        self.settings = LaserSettings()
        self.state = 0
        self.spooler = Spooler(self, "default")
        self.viewbuffer = ""

    def attach(self, *args, **kwargs):
        _ = self.kernel.translation
        self.register("spooler/default", self.spooler)

        @self.console_command(
            "spool",
            help=_("spool <command>"),
            regex=True,
            input_type=(None, "plan", "device"),
            output_type="spooler",
        )
        def spool(
            command, channel, _, data=None, remainder=None, **kwgs
        ):
            spooler = self.spooler
            if data is not None:
                # If plan data is in data, then we copy that and move on to next step.
                spooler.jobs(data.plan)
                channel(_("Spooled Plan."))
                self.signal("plan", data.name, 6)

            if remainder is None:
                channel(_("----------"))
                channel(_("Spoolers:"))
                for d, d_name in enumerate(self.match("device", suffix=True)):
                    channel("%d: %s" % (d, d_name))
                channel(_("----------"))
                channel(_("Spooler %s:" % self.spooler.name))
                for s, op_name in enumerate(spooler.queue):
                    channel("%d: %s" % (s, op_name))
                channel(_("----------"))

            return "spooler", (spooler, self.name)

        @self.console_command(
            "list",
            help=_("spool<?> list"),
            input_type="spooler",
            output_type="spooler",
        )
        def spooler_list(command, channel, _, data_type=None, data=None, **kwgs):
            spooler, device_name = data
            channel(_("----------"))
            channel(_("Spoolers:"))
            for d, d_name in enumerate(self.match("device", suffix=True)):
                channel("%d: %s" % (d, d_name))
            channel(_("----------"))
            channel(_("Spooler %s:" % device_name))
            for s, op_name in enumerate(spooler.queue):
                channel("%d: %s" % (s, op_name))
            channel(_("----------"))
            return data_type, data

        def execute_absolute_position(position_x, position_y):
            x_pos = Length(position_x).value(
                ppi=1000.0, relative_length=self.bedwidth
            )
            y_pos = Length(position_y).value(
                ppi=1000.0, relative_length=self.bedheight
            )

            def move():
                yield COMMAND_SET_ABSOLUTE
                yield COMMAND_MODE_RAPID
                yield COMMAND_MOVE, int(x_pos), int(y_pos)

            return move

        def execute_relative_position(position_x, position_y):
            x_pos = Length(position_x).value(
                ppi=1000.0, relative_length=self.bedwidth
            )
            y_pos = Length(position_y).value(
                ppi=1000.0, relative_length=self.bedheight
            )

            def move():
                yield COMMAND_SET_INCREMENTAL
                yield COMMAND_MODE_RAPID
                yield COMMAND_MOVE, int(x_pos), int(y_pos)
                yield COMMAND_SET_ABSOLUTE

            return move

        @self.console_command(
            "+laser",
            hidden=True,
            input_type=("spooler", None),
            output_type="spooler",
            help=_("turn laser on in place"),
        )
        def plus_laser(data, **kwgs):
            if data is None:
                data = self.spooler, self.name
            spooler, device_name = data
            spooler.job(COMMAND_LASER_ON)
            return "spooler", data

        @self.console_command(
            "-laser",
            hidden=True,
            input_type=("spooler", None),
            output_type="spooler",
            help=_("turn laser off in place"),
        )
        def minus_laser(data, **kwgs):
            if data is None:
                data = self.spooler, self.name
            spooler, device_name = data
            spooler.job(COMMAND_LASER_OFF)
            return "spooler", data

        @self.console_argument(
            "amount", type=Length, help=_("amount to move in the set direction.")
        )
        @self.console_command(
            ("left", "right", "up", "down"),
            input_type=("spooler", None),
            output_type="spooler",
            help=_("cmd <amount>"),
        )
        def direction(command, channel, _, data=None, amount=None, **kwgs):
            if data is None:
                data = self.spooler, self.name
            spooler, device_name = data
            if amount is None:
                amount = Length("1mm")
            max_bed_height = self.bedheight
            max_bed_width = self.bedwidth
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
            self(".timer 1 0 spool%s jog\n" % device_name)
            return "spooler", data

        @self.console_option("force", "f", type=bool, action="store_true")
        @self.console_command(
            "jog",
            hidden=True,
            input_type="spooler",
            output_type="spooler",
            help=_("executes outstanding jog buffer"),
        )
        def jog(command, channel, _, data, force=False, **kwgs):
            if data is None:
                data = self.spooler, self.name
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

        @self.console_option("force", "f", type=bool, action="store_true")
        @self.console_argument("x", type=Length, help=_("change in x"))
        @self.console_argument("y", type=Length, help=_("change in y"))
        @self.console_command(
            ("move", "move_absolute"),
            input_type=("spooler", None),
            output_type="spooler",
            help=_("move <x> <y>: move to position."),
        )
        def move(channel, _, x, y, data=None, force=False, **kwgs):
            if data is None:
                data = self.spooler, self.name
            spooler, device_name = data
            if y is None:
                raise SyntaxError
            if force:
                spooler.job(execute_absolute_position(x, y))
            else:
                if not spooler.job_if_idle(execute_absolute_position(x, y)):
                    channel(_("Busy Error"))
            return "spooler", data

        @self.console_option("force", "f", type=bool, action="store_true")
        @self.console_argument("dx", type=Length, help=_("change in x"))
        @self.console_argument("dy", type=Length, help=_("change in y"))
        @self.console_command(
            "move_relative",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("move_relative <dx> <dy>"),
        )
        def move_relative(channel, _, dx, dy, data=None, force=False, **kwgs):
            if data is None:
                data = self.spooler, self.name
            spooler, device_name = data
            if dy is None:
                raise SyntaxError
            if force:
                spooler.job(execute_relative_position(dx, dy))
            else:
                if not spooler.job_if_idle(execute_relative_position(dx, dy)):
                    channel(_("Busy Error"))
            return "spooler", data

        @self.console_argument("x", type=Length, help=_("x offset"))
        @self.console_argument("y", type=Length, help=_("y offset"))
        @self.console_command(
            "home",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("home the laser"),
        )
        def home(x=None, y=None, data=None, **kwgs):
            if data is None:
                data = self.spooler, self.name
            spooler, device_name = data
            if x is not None and y is not None:
                x = x.value(ppi=1000.0, relative_length=self.bedwidth)
                y = y.value(ppi=1000.0, relative_length=self.bedheight)
                spooler.job(COMMAND_HOME, int(x), int(y))
                return "spooler", data
            spooler.job(COMMAND_HOME)
            return "spooler", data

        @self.console_command(
            "unlock",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("unlock the rail"),
        )
        def unlock(data=None, **kwgs):
            if data is None:
                data = self.spooler, self.name
            spooler, device_name = data
            spooler.job(COMMAND_UNLOCK)
            return "spooler", data

        @self.console_command(
            "lock",
            input_type=("spooler", None),
            output_type="spooler",
            help=_("lock the rail"),
        )
        def lock(data, **kwgs):
            if data is None:
                data = self.spooler, self.name
            spooler, device_name = data
            spooler.job(COMMAND_LOCK)
            return "spooler", data

        @self.console_command(
            "test_dot_and_home",
            input_type=("spooler", None),
            hidden=True,
        )
        def run_home_and_dot_test(data, **kwgs):
            if data is None:
                data = self.spooler, self.name
            spooler, device_name = data

            def home_dot_test():
                for i in range(25):
                    yield COMMAND_SET_ABSOLUTE
                    yield COMMAND_MODE_RAPID
                    yield COMMAND_HOME
                    yield COMMAND_LASER_OFF
                    yield COMMAND_WAIT_FINISH
                    yield COMMAND_MOVE, 3000, 3000
                    yield COMMAND_WAIT_FINISH
                    yield COMMAND_LASER_ON
                    yield COMMAND_WAIT, 0.05
                    yield COMMAND_LASER_OFF
                    yield COMMAND_WAIT_FINISH
                yield COMMAND_HOME
                yield COMMAND_WAIT_FINISH

            spooler.job(home_dot_test)

        @self.console_argument("transition_type", type=str)
        @self.console_command(
            "test_jog_transition",
            help="test_jog_transition <finish,jog,switch>",
            input_type=("spooler", None),
            hidden=True,
        )
        def run_jog_transition_test(data, transition_type, **kwgs):
            """ "
            The Jog Transition Test is intended to test the jogging
            """
            if transition_type == "jog":
                command = COMMAND_JOG
            elif transition_type == "finish":
                command = COMMAND_JOG_FINISH
            elif transition_type == "switch":
                command = COMMAND_JOG_SWITCH
            else:
                raise SyntaxError
            if data is None:
                data = self.spooler, self.name
            spooler, device_name = data

            def jog_transition_test():
                yield COMMAND_SET_ABSOLUTE
                yield COMMAND_MODE_RAPID
                yield COMMAND_HOME
                yield COMMAND_LASER_OFF
                yield COMMAND_WAIT_FINISH
                yield COMMAND_MOVE, 3000, 3000
                yield COMMAND_WAIT_FINISH
                yield COMMAND_LASER_ON
                yield COMMAND_WAIT, 0.05
                yield COMMAND_LASER_OFF
                yield COMMAND_WAIT_FINISH

                yield COMMAND_SET_SPEED, 10.0

                def pos(i):
                    if i < 3:
                        x = 200
                    elif i < 6:
                        x = -200
                    else:
                        x = 0
                    if i % 3 == 0:
                        y = 200
                    elif i % 3 == 1:
                        y = -200
                    else:
                        y = 0
                    return x, y

                for q in range(8):
                    top = q & 1
                    left = q & 2
                    x_val = q & 3
                    yield COMMAND_SET_DIRECTION, top, left, x_val, not x_val
                    yield COMMAND_MODE_PROGRAM
                    for j in range(9):
                        jx, jy = pos(j)
                        for k in range(9):
                            kx, ky = pos(k)
                            yield COMMAND_MOVE, 3000, 3000
                            yield COMMAND_MOVE, 3000 + jx, 3000 + jy
                            yield command, 3000 + jx + kx, 3000 + jy + ky
                    yield COMMAND_MOVE, 3000, 3000
                    yield COMMAND_MODE_RAPID
                    yield COMMAND_WAIT_FINISH
                    yield COMMAND_LASER_ON
                    yield COMMAND_WAIT, 0.05
                    yield COMMAND_LASER_OFF
                    yield COMMAND_WAIT_FINISH

            spooler.job(jog_transition_test)
