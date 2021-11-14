import socket
import threading
import time

from meerk40t.core.spoolers import Spooler
from meerk40t.kernel import Service
from meerk40t.kernel import CommandMatchRejected

from meerk40t.svgelements import Length

from ..device.lasercommandconstants import *

from ..core.elements import MILS_IN_MM


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.add_service("device", LegacyDevice(kernel))
        kernel.register("output/file", FileOutput)
        kernel.register("output/tcp", TCPOutput)
    elif lifecycle == "boot":
        context = kernel.get_context("legacy")
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
        kernel.register_choices("bed_dim", choices)


class FileOutput:
    def __init__(self, filename, name=None):
        super().__init__()
        self.next = None
        self.prev = None
        self.filename = filename
        self._stream = None
        self.name = name

    def writable(self):
        return True

    def write(self, data):
        filename = self.filename.replace("?", "").replace(":", "")
        with open(
                filename, "ab" if isinstance(data, (bytes, bytearray)) else "a"
        ) as stream:
            stream.write(data)
            stream.flush()

    def __repr__(self):
        if self.name is not None:
            return "FileOutput('%s','%s')" % (self.filename, self.name)
        return "FileOutput(%s)" % self.filename

    def __len__(self):
        return 0

    realtime_write = write

    @property
    def type(self):
        return "file"


class TCPOutput:
    def __init__(self, context, address, port, name=None):
        super().__init__()
        self.context = context
        self.next = None
        self.prev = None
        self.address = address
        self.port = port
        self._stream = None
        self.name = name

        self.lock = threading.RLock()
        self.buffer = bytearray()
        self.thread = None

    def writable(self):
        return True

    def connect(self):
        try:
            self._stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._stream.connect((self.address, self.port))
            self.context.signal("tcp;status", "connected")
        except (ConnectionError, TimeoutError):
            self.disconnect()

    def disconnect(self):
        self.context.signal("tcp;status", "disconnected")
        self._stream.close()
        self._stream = None

    def write(self, data):
        self.context.signal("tcp;write", data)
        with self.lock:
            self.buffer += data
            self.context.signal("tcp;buffer", len(self.buffer))
        self._start()

    realtime_write = write

    def _start(self):
        if self.thread is None:
            self.thread = self.context.threaded(
                self._sending, thread_name="sender-%d" % self.port, result=self._stop
            )

    def _stop(self, *args):
        self.thread = None

    def _sending(self):
        tries = 0
        while True:
            try:
                if len(self.buffer):
                    if self._stream is None:
                        self.connect()
                        if self._stream is None:
                            return
                    with self.lock:
                        sent = self._stream.send(self.buffer)
                        del self.buffer[:sent]
                        self.context.signal("tcp;buffer", len(self.buffer))
                    tries = 0
                else:
                    tries += 1
                    time.sleep(0.1)
            except (ConnectionError, OSError):
                tries += 1
                self.disconnect()
                time.sleep(0.05)
            if tries >= 20:
                with self.lock:
                    if len(self.buffer) == 0:
                        break

    def __repr__(self):
        if self.name is not None:
            return "TCPOutput('%s:%s','%s')" % (self.address, self.port, self.name)
        return "TCPOutput('%s:%s')" % (self.address, self.port)

    def __len__(self):
        return len(self.buffer)

    @property
    def type(self):
        return "tcp"


class LegacyDevice(Service):
    """
    Legacy Device governs the 0.7.x style device connections between spoolers, controllers, and output.

    Legacy Devices read the values in `devices` and boots the needed devices up, by running the lines found in
    device_*. These refer to local commands registered in the service.
    """

    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "legacy")

    @property
    def current_y(self):
        return self.default_driver().current_y

    @property
    def current_x(self):
        return self.default_driver().current_x

    @property
    def settings(self):
        return self.default_driver().settings

    @property
    def state(self):
        return self.default_driver().state

    @property
    def spooler(self):
        return self.default_spooler()

    @property
    def viewbuffer(self):
        return self.default_output().viewbuffer()

    @property
    def name(self):
        return "(%s -> %s -> %s)" % (
            self.default_spooler().name,
            self.default_driver().type,
            self.default_output().type,
        )

    def attach(self, *args, **kwargs):
        # self.register("plan/interrupt", interrupt)
        _ = self.kernel.translation
        self.setting(str, "active", "0")

        ########################
        # OUTPUT COMMANDS
        ########################

        @self.console_option("new", "n", type=str, help=_("new output type"))
        @self.console_command(
            "output",
            help=_("output<?> <command>"),
            regex=True,
            input_type=(None, "input", "driver"),
            output_type="output",
        )
        def output_base(
            command, channel, _, data=None, new=None, remainder=None, **kwgs
        ):
            input_driver = None
            if data is None:
                if len(command) > 6:
                    device_name = command[6:]
                    self.active = device_name
                else:
                    device_name = self.active
            else:
                input_driver, device_name = data

            output = self.get_or_make_output(device_name, new)

            if output is None:
                raise SyntaxError("No Output")

            self.signal("output", device_name, 1)

            if input_driver is not None:
                input_driver.next = output
                output.prev = input_driver

                input_driver.output = output
                output.input = input_driver
            elif remainder is None:
                pass

            return "output", (output, device_name)

        @self.console_argument("filename")
        @self.console_command(
            "outfile",
            help=_("outfile filename"),
            input_type=(None, "input", "driver"),
            output_type="output",
        )
        def output_outfile(command, channel, _, data=None, filename=None, **kwgs):
            if filename is None:
                raise SyntaxError("No file specified.")
            input_driver = None
            if data is None:
                if len(command) > 6:
                    device_name = command[6:]
                else:
                    device_name = self.active
            else:
                input_driver, device_name = data

            output = FileOutput(filename)
            self.put_output(device_name, output)

            if input_driver is not None:
                input_driver.next = output
                output.prev = input_driver

                input_driver.output = output
                output.input = input_driver
            return "output", (output, device_name)

        @self.console_argument("address", type=str, help=_("tcp address"))
        @self.console_argument("port", type=int, help=_("tcp/ip port"))
        @self.console_command(
            "tcp",
            help=_("network <address> <port>"),
            input_type=(None, "input", "driver"),
            output_type="output",
        )
        def output_tcp(command, channel, _, data=None, address=None, port=None, **kwgs):
            if port is None:
                raise SyntaxError(_("No address/port specified"))
            input_driver = None
            if data is None:
                if len(command) > 3:
                    device_name = command[3:]
                else:
                    device_name = self.active
            else:
                input_driver, device_name = data

            output = TCPOutput(self, address, port)
            self.put_output(device_name, output)

            if input_driver is not None:
                input_driver.next = output
                output.prev = input_driver

                input_driver.output = output
                output.input = input_driver
            return "output", (output, device_name)

        @self.console_command(
            "list",
            help=_("output<?> list, list current outputs"),
            input_type="output",
            output_type="output",
        )
        def output_list(command, channel, _, data_type=None, data=None, **kwgs):
            output, output_name = data
            channel(_("----------"))
            channel(_("Output:"))
            for i, pname in enumerate(self._outputs):
                channel("%d: %s" % (i, pname))
            channel(_("----------"))
            channel(_("Output %s: %s" % (output_name, str(output))))
            channel(_("----------"))
            return data_type, data

        @self.console_command(
            "type", help=_("list output types"), input_type="output"
        )
        def output_types(channel, _, **kwgs):
            channel(_("----------"))
            channel(_("Output types:"))
            for i, name in enumerate(self.match("output/", suffix=True)):
                channel("%d: %s" % (i + 1, name))
            channel(_("----------"))

        @self.console_argument(
            "port", type=int, help=_("Port of TCPOutput to change.")
        )
        @self.console_command(
            "port",
            help=_("change the port of the tcpdevice"),
            input_type="tcpout",
        )
        def tcpport(channel, _, port, data=None, **kwargs):
            spooler, input_driver, output = data
            old_port = output.port
            output.port = port
            channel(_("TCP port changed: %s -> %s" % (str(old_port), str(port))))

        ########################
        # DRIVERS COMMANDS
        ########################

        @self.console_option("new", "n", type=str, help=_("new driver type"))
        @self.console_command(
            "driver",
            help=_("driver<?> <command>"),
            regex=True,
            input_type=(None, "spooler"),
            output_type="driver",
        )
        def driver_base(
                command, channel, _, data=None, new=None, remainder=None, **kwgs
        ):
            spooler = None
            if data is None:
                if len(command) > 6:
                    device_name = command[6:]
                    self.active = device_name
                else:
                    device_name = self.active
            else:
                spooler, device_name = data

            driver = self.get_or_make_driver(device_name, new)
            if driver is None:
                raise SyntaxError("No Driver.")

            if spooler is not None:
                try:
                    driver.spooler = spooler
                    spooler.next = driver
                    driver.prev = spooler
                except AttributeError:
                    pass
            elif remainder is None:
                channel(_("----------"))
                channel(_("Driver:"))
                for i, drv in enumerate(self.match("device", suffix=True)):
                    channel("%d: %s" % (i, drv))
                channel(_("----------"))
                channel(_("Driver %s:" % device_name))
                channel(str(driver))
                channel(_("----------"))
            return "driver", (driver, device_name)

        @self.console_command(
            "list",
            help=_("driver<?> list"),
            input_type="driver",
            output_type="driver",
        )
        def driver_list(command, channel, _, data_type=None, data=None, **kwgs):
            driver_obj, name = data
            channel(_("----------"))
            channel(_("Driver:"))
            for i, drv in enumerate(self.match("device", suffix=True)):
                channel("%d: %s" % (i, drv))
            channel(_("----------"))
            channel(_("Driver %s:" % name))
            channel(str(driver_obj))
            channel(_("----------"))
            return data_type, data

        @self.console_command(
            "type",
            help=_("list driver types"),
            input_type="driver",
        )
        def list_type(channel, _, **kwgs):
            channel(_("----------"))
            channel(_("Drivers permitted:"))
            for i, name in enumerate(self.match("driver/", suffix=True)):
                channel("%d: %s" % (i + 1, name))
            channel(_("----------"))

        @self.console_command(
            "reset",
            help=_("driver<?> reset"),
            input_type="driver",
            output_type="driver",
        )
        def driver_reset(data_type=None, data=None, **kwargs):
            driver_obj, name = data
            driver_obj.reset()
            return data_type, data

        ########################
        # SPOOLER DEVICE COMMANDS
        ########################

        @self.console_option(
            "register",
            "r",
            type=bool,
            action="store_true",
            help=_("Register this device"),
        )
        @self.console_command(
            "spool",
            help=_("spool<?> <command>"),
            regex=True,
            input_type=(None, "plan", "device"),
            output_type="spooler",
        )
        def spool(
            command, channel, _, data=None, register=False, remainder=None, **kwgs
        ):
            if len(command) > 5:
                device_name = command[5:]
            else:
                if register:
                    device_context = self.get_context("devices")
                    index = 0
                    while hasattr(device_context, "device_%d" % index):
                        index += 1
                    device_name = str(index)
                else:
                    device_name = self.active
            if register:
                device_context = self.get_context("devices")
                setattr(
                    device_context,
                    "device_%s" % device_name,
                    ("spool%s -r " % device_name) + remainder + "\n",
                )

            spooler = self.get_or_make_spooler(device_name)
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
                channel(_("Spooler %s:" % device_name))
                for s, op_name in enumerate(spooler.queue):
                    channel("%d: %s" % (s, op_name))
                channel(_("----------"))

            return "spooler", (spooler, device_name)

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


        ########################
        # SPOOLER GENERAL COMMANDS
        ########################

        @self.console_argument("op", type=str, help=_("unlock, origin, home, etc"))
        @self.console_command(
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
                for plan_command, command_name, suffix in self.find("plan", op):
                    spooler.job(plan_command)
                    return data_type, data
            except (KeyError, IndexError):
                pass
            channel(_("No plan command found."))
            return data_type, data

        @self.console_command(
            "clear",
            help=_("spooler<?> clear"),
            input_type="spooler",
            output_type="spooler",
        )
        def spooler_clear(command, channel, _, data_type=None, data=None, **kwgs):
            spooler, device_name = data
            spooler.clear_queue()
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
                data = self.default_spooler(), self.active
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
                data = self.default_spooler(), self.active
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
                data = self.default_spooler(), self.active
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
                data = self.default_spooler(), self.active
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
                data = self.default_spooler(), self.active
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
                data = self.default_spooler(), self.active
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
                data = self.default_spooler(), self.active
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
                data = self.default_spooler(), self.active
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
                data = self.default_spooler(), self.active
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
                data = self.default_spooler(), self.active
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
                data = self.default_spooler(), self.active
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


        ########################
        # BASE DEVICE COMMANDS
        ########################

        @self.console_option(
            "out",
            "o",
            action="store_true",
            help=_("match on output rather than driver"),
        )
        @self.console_command(
            "dev",
            help=_("delegate commands to currently selected device by input/driver"),
            output_type="dev",
            hidden=True,
        )
        def dev(channel, _, remainder=None, out=False, **kwargs):
            try:
                spooler, input_driver, output = self.lookup("device", self.active)
            except TypeError:
                return
            if remainder is None:
                channel(
                    _(
                        "Device %s, %s, %s"
                        % (str(spooler), str(input_driver), str(output))
                    )
                )
            if out:
                if output is not None:
                    try:
                        t = output.type + "out"
                        return t, (spooler, input_driver, output)
                    except AttributeError:
                        pass
            elif input_driver is not None:
                try:
                    t = input_driver.type
                    return t, (spooler, input_driver, output)
                except AttributeError:
                    pass

            return "dev", (spooler, input_driver, output)

        @self.console_command(".+", regex=True, hidden=True)
        def virtual_dev(command, remainder=None, **kwargs):
            try:
                spooler, input_driver, output = self.lookup("device", self.active)
            except TypeError:
                raise CommandMatchRejected(_("No device selected."))

            if input_driver is not None:
                try:
                    t = input_driver.type
                    match = "command/%s/%s$" % (str(t), command)
                    match = "".join([i for i in match if i not in "(){}[]"])
                    for command_funct, command_name, suffix in self.find(match):
                        if command_funct is not None:
                            if remainder is not None:
                                self(".dev %s %s\n" % (command, remainder))
                            else:
                                self(".dev %s\n" % command)
                            return
                except AttributeError:
                    pass
            if output is not None:
                try:
                    t = output.type + "out"
                    match = "command/%s/%s" % (str(t), command)
                    match = "".join([i for i in match if i not in "(){}[]"])
                    for command_funct, command_name, sname in self.find(match):
                        if command_funct is not None:
                            if remainder is not None:
                                self(".dev -o %s %s\n" % (command, remainder))
                            else:
                                self(".dev -o %s\n" % command)
                            return
                except AttributeError:
                    pass
            raise CommandMatchRejected(_("No matching command."))

        @self.console_argument(
            "index", type=int, help=_("Index of device being activated")
        )
        @self.console_command(
            "activate",
            help=_("delegate commands to currently selected device"),
            input_type="device",
            output_type="device",
        )
        def device(channel, _, index, **kwargs):
            spools = list(self.match("device", suffix=True))
            self.active = spools[index]
            self.signal("active", index)
            channel(_("Activated device %s at index %d." % (self.active, index)))
            return "device", (None, str(index))

        @self.console_command(
            "device",
            help=_("device"),
            output_type="device",
        )
        def device(channel, _, remainder=None, **kwargs):
            device_context = self.get_context("devices")
            if remainder is None:
                channel(_("----------"))
                channel(_("Devices:"))
                index = 0
                while hasattr(device_context, "device_%d" % index):
                    line = getattr(device_context, "device_%d" % index)
                    channel("%d: %s" % (index, line))
                    index += 1
                channel("----------")
            return "device", (None, self.active)

        @self.console_command(
            "list",
            help=_("list devices"),
            input_type="device",
            output_type="device",
        )
        def list_devices(channel, _, data, **kwargs):
            device_context = self.get_context("devices")
            channel(_("----------"))
            channel(_("Devices:"))
            index = 0
            while hasattr(device_context, "device_%d" % index):
                line = getattr(device_context, "device_%d" % index)
                channel("%d: %s" % (index, line))
                index += 1
            channel("----------")
            return "device", data

        @self.console_argument("index", type=int, help=_("Index of device deleted"))
        @self.console_command(
            "delete",
            help=_("delete <index>"),
            input_type="device",
        )
        def delete(channel, _, index, **kwargs):
            spools = list(self.match("device", suffix=True))
            device_name = spools[index]

            device_context = self.get_context("devices")
            try:
                setattr(device_context, "device_%s" % device_name, "")
                device = self.lookup("device", device_name)
                if device is not None:
                    spooler, driver, output = device
                    if driver is not None:
                        try:
                            driver.shutdown()
                        except AttributeError:
                            pass
                    if output is not None:
                        try:
                            output.finalize()
                        except AttributeError:
                            pass
                self.register("device/%s" % device_name, [None, None, None])
            except (KeyError, ValueError):
                raise SyntaxError(_("Invalid device-string index."))

        ########################
        # LEGACY DEVICE BOOT SEQUENCE
        ########################

        device_context = self.get_context("devices")
        index = 0
        for d in device_context.kernel.keylist(device_context.path):
            suffix = d.split("/")[-1]
            if not suffix.startswith("device_"):
                continue
            line = device_context.setting(str, suffix, None)
            if line is not None and len(line):
                device_context(line + "\n")
                device_context.setting(str, "device_%d" % index, None)
            index += 1
        device_context._devices = index

        for i in range(5):
            self.get_or_make_spooler(str(i))

    def get_or_make_spooler(self, device_name):
        device = self.lookup("device", device_name)
        if device is None:
            device = [None, None, None]
            self.register("device/%s" % device_name, device)
        if device[0] is None:
            device[0] = Spooler(self, device_name)
        return device[0]

    def default_spooler(self):
        return self.get_or_make_spooler(self.active)

    def get_driver(self, driver_name, **kwargs):
        try:
            return self.lookup("device", driver_name)[1]
        except (TypeError, IndexError):
            return None

    def get_or_make_driver(self, device_name, driver_type=None, **kwargs):
        device = self.lookup("device", device_name)
        if device is None:
            device = [None, None, None]
            self.register("device/%s" % device_name, device)
        if device[1] is not None and driver_type is None:
            return device[1]
        try:
            for driver_class, itype, sname in self.find("driver", driver_type):
                driver = driver_class(self, device_name, **kwargs)
                device[1] = driver
                return driver
        except (KeyError, IndexError):
            return None

    def default_driver(self):
        return self.get_driver(self.active)

    def device(self):
        v = self.lookup("device", self.active)
        if v is None:
            return None, None, None
        return v

    def get_or_make_output(self, device_name, output_type=None, **kwargs):
        device = self.lookup("device", device_name)
        if device is None:
            device = [None, None, None]
            self.register("device/%s" % device_name, device)
        if device[2] is not None and output_type is None:
            return device[2]
        try:
            for output_class, itype, sname in self.find("output", output_type):
                output = output_class(self, device_name, **kwargs)
                device[2] = output
                return output
        except (KeyError, IndexError):
            return None

    def put_output(self, device_name, output):
        device = self.lookup("device", device_name)
        if device is None:
            device = [None, None, None]
            self.register("device/%s" % device_name, device)

        try:
            device[2] = output
        except (KeyError, IndexError):
            pass

    def default_output(self):
        return self.get_or_make_output(self.active)
