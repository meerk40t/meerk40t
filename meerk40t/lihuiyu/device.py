import os
import platform
import socket
import threading
import time
from hashlib import md5

from meerk40t.core.spoolers import Spooler
from meerk40t.tools.zinglplotter import ZinglPlotter

from ..core.cutcode import CutCode, LaserSettings, RawCut
from ..core.plotplanner import grouped, PlotPlanner
from ..device.basedevice import (
    DRIVER_STATE_FINISH,
    DRIVER_STATE_MODECHANGE,
    DRIVER_STATE_PROGRAM,
    DRIVER_STATE_RAPID,
    DRIVER_STATE_RASTER,
    PLOT_AXIS,
    PLOT_DIRECTION,
    PLOT_FINISH,
    PLOT_JOG,
    PLOT_LEFT_UPPER,
    PLOT_RAPID,
    PLOT_RIGHT_LOWER,
    PLOT_SETTING,
    PLOT_START,
)
from ..device.lasercommandconstants import *
from ..kernel import (
    STATE_ACTIVE,
    STATE_BUSY,
    STATE_END,
    STATE_IDLE,
    STATE_INITIALIZE,
    STATE_PAUSE,
    STATE_SUSPEND,
    STATE_TERMINATE,
    STATE_UNKNOWN,
    STATE_WAIT,
    Module,
    Service,
)
from ..svgelements import Length
from .laserspeed import LaserSpeed

STATUS_BAD_STATE = 204
# 0xCC, 11001100
STATUS_OK = 206
# 0xCE, 11001110
STATUS_ERROR = 207
# 0xCF, 11001111
STATUS_FINISH = 236
# 0xEC, 11101100
STATUS_BUSY = 238
# 0xEE, 11101110
STATUS_POWER = 239


STATE_X_FORWARD_LEFT = (
    0b0000000000000001  # Direction is flagged left rather than right.
)
STATE_Y_FORWARD_TOP = 0b0000000000000010  # Direction is flagged top rather than bottom.
STATE_X_STEPPER_ENABLE = 0b0000000000000100  # X-stepper motor is engaged.
STATE_Y_STEPPER_ENABLE = 0b0000000000001000  # Y-stepper motor is engaged.
STATE_HORIZONTAL_MAJOR = 0b0000000000010000
REQUEST_X = 0b0000000000100000
REQUEST_X_FORWARD_LEFT = 0b0000000001000000  # Requested direction towards the left.
REQUEST_Y = 0b0000000010000000
REQUEST_Y_FORWARD_TOP = 0b0000000100000000  # Requested direction towards the top.
REQUEST_AXIS = 0b0000001000000000
REQUEST_HORIZONTAL_MAJOR = 0b0000010000000000  # Requested horizontal major axis.


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("provider/device/lhystudios", LihuiyuDevice)
        kernel.register("load/EgvLoader", EgvLoader)
        kernel.register("emulator/lhystudios", LhystudiosEmulator)
    if lifecycle == "preboot":
        suffix = "lhystudios"
        for d in kernel.root.derivable():
            if d.startswith(suffix):
                kernel.root(
                    "service device start -p {path} {suffix}\n".format(
                        path=d, suffix=suffix
                    )
                )
    if lifecycle == "boot":
        if not hasattr(kernel, "device"):
            # Nothing has yet established a device. Boot this device.
            kernel.root("service device start lhystudios\n")


class LihuiyuDevice(Service):
    """
    LihuiyuDevice is driver for the M2 Nano and other classes of Lhystudios boards.
    """

    def __init__(self, kernel, path, *args, **kwargs):
        Service.__init__(self, kernel, path)
        self.name = "LihuiyuDevice"

        _ = kernel.translation

        choices = [
            {
                "attr": "bedwidth",
                "object": self,
                "default": 12205.0,
                "type": float,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": 8268.0,
                "type": float,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
            },
            {
                "attr": "scale_x",
                "object": self,
                "default": 1.000,
                "type": float,
                "label": _("X Scale Factor"),
                "tip": _(
                    "Scale factor for the X-axis. This defines the ratio of mils to steps. This is usually at 1:1 steps/mils but due to functional issues it can deviate and needs to be accounted for"
                ),
            },
            {
                "attr": "scale_y",
                "object": self,
                "default": 1.000,
                "type": float,
                "label": _("Y Scale Factor"),
                "tip": _(
                    "Scale factor for the Y-axis. This defines the ratio of mils to steps. This is usually at 1:1 steps/mils but due to functional issues it can deviate and needs to be accounted for"
                ),
            },
        ]
        self.register_choices("bed_dim", choices)

        # name_choice = [
        #     {
        #         "attr": "device_name",
        #         "object": context,
        #         "type": str,
        #         "label": _("What do you call this device?"),
        #         "tip": _(
        #             "Device name can be anything and will be used to identify this device in places where devices can be selected."
        #         )
        #     }
        # ]
        # self.register_choices("config", name_choice)

        # connection_choice = [
        #     {
        #         "attr": "connection",
        #         "object": context,
        #         "type": list,
        #         "choices": list(context.kernel.lookup("driver", "connections")),
        #         "label": _("How is the laser connected to this computer"),
        #         "tip": _(
        #             "Select the connection method used by this laser."
        #         )
        #     }
        # ]
        # network_choice = [
        #     {
        #         "attr": "network_address",
        #         "object": context,
        #         "type": str,
        #         "label": _("What is the address to the laser on the network?"),
        #         "tip": _(
        #             "IP address or address url of the machine with the laser."
        #         )
        #     }
        # ]
        # port_choice = [
        #     {
        #         "attr": "port",
        #         "object": context,
        #         "type": str,
        #         "label": _("What port is the laser located on?"),
        #         "tip": _(
        #             "TCP/IP port number 1:65535"
        #         )
        #     },
        # ]
        # home_choice = [
        #     {
        #         "attr": "home_position",
        #         "object": context,
        #         "default": 0,
        #         "type": tuple,
        #         "dimension": 2,
        #         "choices": (_("Top/Left"), _("Top/Right"), _("Bottom/Left"), _("Bottom/Right")),
        #         "label": _("Home Position for the laser"),
        #         "tip": _(
        #             "When the laser is homed what corner should it home to."
        #         ),
        #     },
        # ]
        self.setting(bool, "opt_rapid_between", True)
        self.setting(int, "opt_jog_mode", 0)
        self.setting(int, "opt_jog_minimum", 256)
        self.setting(bool, "strict", False)
        self.setting(bool, "swap_xy", False)
        self.setting(bool, "flip_x", False)
        self.setting(bool, "flip_y", False)
        self.setting(bool, "home_right", False)
        self.setting(bool, "home_bottom", False)
        self.setting(int, "home_adjust_x", 0)
        self.setting(int, "home_adjust_y", 0)
        self.setting(int, "buffer_max", 900)
        self.setting(bool, "buffer_limit", True)

        self.setting(bool, "autolock", True)

        self.setting(str, "board", "M2")
        self.setting(bool, "fix_speeds", False)

        self.setting(int, "usb_index", -1)
        self.setting(int, "usb_bus", -1)
        self.setting(int, "usb_address", -1)
        self.setting(int, "usb_version", -1)
        self.setting(bool, "mock", False)
        self.setting(bool, "show_usb_log", False)

        self.setting(bool, "networked", False)
        self.setting(int, "packet_count", 0)
        self.setting(int, "rejected_count", 0)
        self.setting(str, "serial", None)
        self.setting(bool, "serial_enable", False)

        self.setting(int, "port", 1022)
        self.setting(str, "address", "localhost")
        self.setting(str, "label", "m2nano")

        self.current_x = 0.0
        self.current_y = 0.0
        self.state = 0
        self.spooler = Spooler(self)
        self.driver = LhystudiosDriver(self)
        self.add_service_delegate(self.driver)

        self.settings = self.driver.settings

        self.tcp = TCPOutput(self)
        self.add_service_delegate(self.tcp)

        self.controller = LhystudiosController(self)
        self.add_service_delegate(self.controller)

        self.driver.spooler = self.spooler
        self.driver.output = self.controller if not self.networked else self.tcp

        self.viewbuffer = ""

        _ = self.kernel.translation

        @self.console_command(
            "spool",
            help=_("spool <command>"),
            regex=True,
            input_type=(None, "plan", "device"),
            output_type="spooler",
        )
        def spool(command, channel, _, data=None, remainder=None, **kwgs):
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
                channel(_("Spooler on device %s:" % str(self.label)))
                for s, op_name in enumerate(spooler.queue):
                    channel("%d: %s" % (s, op_name))
                channel(_("----------"))

            return "spooler", spooler

        @self.console_option(
            "idonotlovemyhouse",
            type=bool,
            action="store_true",
            help=_("override one second laser fire pulse duration"),
        )
        @self.console_argument("time", type=float, help=_("laser fire pulse duration"))
        @self.console_command(
            "pulse",
            help=_("pulse <time>: Pulse the laser in place."),
        )
        def pulse(command, channel, _, time=None, idonotlovemyhouse=False, **kwargs):
            if time is None:
                channel(_("Must specify a pulse time in milliseconds."))
                return
            value = time / 1000.0
            if value > 1.0:
                channel(
                    _('"%s" exceeds 1 second limit to fire a standing laser.') % value
                )
                try:
                    if not idonotlovemyhouse:
                        return
                except IndexError:
                    return

            def timed_fire():
                yield COMMAND_WAIT_FINISH
                yield COMMAND_LASER_ON
                yield COMMAND_WAIT, value
                yield COMMAND_LASER_OFF

            if self.spooler.job_if_idle(timed_fire):
                channel(_("Pulse laser for %f milliseconds") % (value * 1000.0))
            else:
                channel(_("Pulse laser failed: Busy"))
            return

        @self.console_argument("speed", type=float, help=_("Set the movement speed"))
        @self.console_argument("dx", type=Length, help=_("change in x"))
        @self.console_argument("dy", type=Length, help=_("change in y"))
        @self.console_command(
            "move_at_speed",
            help=_("move_at_speed <speed> <dx> <dy>"),
        )
        def move_speed(channel, _, speed, dx, dy, **kwgs):
            dx = Length(dx).value(ppi=1000.0, relative_length=self.bedwidth)
            dy = Length(dy).value(ppi=1000.0, relative_length=self.bedheight)

            def move_at_speed():
                yield COMMAND_SET_SPEED, speed
                yield COMMAND_MODE_PROGRAM
                x = self.current_x
                y = self.current_y
                yield COMMAND_MOVE, x + dx, y + dy
                yield COMMAND_MODE_RAPID

            if not self.spooler.job_if_idle(move_at_speed):
                channel(_("Busy"))
            return

        @self.console_option(
            "difference",
            "d",
            type=bool,
            action="store_true",
            help=_("Change speed by this amount."),
        )
        @self.console_argument("speed", type=str, help=_("Set the driver speed."))
        @self.console_command("speed", help=_("Set current speed of driver."))
        def speed(command, channel, _, speed=None, difference=False, **kwargs):
            original_speed = self.settings.speed
            if speed is None:
                if original_speed is None:
                    channel(_("Speed is not set."))
                else:
                    channel(_("Speed set at: %f mm/s") % original_speed)
                return
            if speed.endswith("%"):
                speed = speed[:-1]
                percent = True
            else:
                percent = False
            try:
                s = float(speed)
            except ValueError:
                channel(_("Not a valid speed or percent."))
                return
            if percent and difference:
                s = original_speed + original_speed * (s / 100.0)
            elif difference:
                s += original_speed
            elif percent:
                s = original_speed * (s / 100.0)
            self.driver.set_speed(s)
            channel(_("Speed set at: %f mm/s") % self.settings.speed)

        @self.console_argument("ppi", type=int, help=_("pulses per inch [0-1000]"))
        @self.console_command("power", help=_("Set Driver Power"))
        def power(command, channel, _, ppi=None, **kwargs):
            original_power = self.settings.power
            if ppi is None:
                if original_power is None:
                    channel(_("Power is not set."))
                else:
                    channel(_("Power set at: %d pulses per inch") % original_power)
            else:
                try:
                    self.driver.set_power(ppi)
                except ValueError:
                    pass

        @self.console_argument("accel", type=int, help=_("Acceleration amount [1-4]"))
        @self.console_command(
            "acceleration",
            help=_("Set Driver Acceleration [1-4]"),
        )
        def acceleration(channel, _, accel=None, **kwargs):
            """
            Lhymicro-gl speedcodes have a single character of either 1,2,3,4 which indicates
            the acceleration value of the laser. This is typically 1 below 25.4, 2 below 60,
            3 below 127, and 4 at any value greater than that. Manually setting this on the
            fly can be used to check the various properties of that mode.
            """
            if accel is None:
                if self.settings.acceleration is None:
                    channel(_("Acceleration is set to default."))
                else:
                    channel(_("Acceleration: %d") % self.settings.acceleration)

            else:
                try:
                    v = accel
                    if v not in (1, 2, 3, 4):
                        self.driver.set_acceleration(None)
                        channel(_("Acceleration is set to default."))
                        return
                    self.driver.set_acceleration(v)
                    channel(_("Acceleration: %d") % self.driver.settings.acceleration)
                except ValueError:
                    channel(_("Invalid Acceleration [1-4]."))
                    return

        @self.console_command(
            "code_update",
            hidden=True,
            help=_("Update m2nano codes for movement"),
        )
        def codes_update(**kwargs):
            self.driver.update_codes()

        @self.console_command(
            "network_update",
            hidden=True,
            help=_("Updates network state for m2nano networked."),
        )
        def network_update(**kwargs):
            self.driver.output = self.controller if not self.networked else self.tcp

        @self.console_command(
            "status",
            help=_("abort waiting process on the controller."),
        )
        def realtime_pause(channel, _, **kwargs):
            try:
                self.controller.update_status()
                channel(str(self.controller._status))
            except ConnectionError:
                channel(_("Could not check status, usb not connected."))

        @self.console_command(
            "continue",
            help=_("abort waiting process on the controller."),
        )
        def realtime_pause(**kwargs):
            self.controller.abort_waiting = True

        @self.console_command(
            "pause",
            help=_("realtime pause/resume of the machine"),
        )
        def realtime_pause(**kwargs):
            if self.driver.is_paused:
                self.driver.resume()
            else:
                self.driver.pause()

        @self.console_command(("estop", "abort"), help=_("Abort Job"))
        def pipe_abort(channel, _, **kwargs):
            self.driver.reset()
            channel(_("Lhystudios Channel Aborted."))

        @self.console_argument(
            "rapid_x", type=float, help=_("limit x speed for rapid.")
        )
        @self.console_argument(
            "rapid_y", type=float, help=_("limit y speed for rapid.")
        )
        @self.console_command(
            "rapid_override",
            help=_("limit speed of typical rapid moves."),
        )
        def rapid_override(channel, _, rapid_x=None, rapid_y=None, **kwargs):
            if rapid_x is not None:
                if rapid_y is None:
                    rapid_y = rapid_x
                self.driver.rapid_override = True
                self.driver.rapid_override_speed_x = rapid_x
                self.driver.rapid_override_speed_y = rapid_y
                channel(
                    _("Rapid Limit: %f, %f")
                    % (
                        self.driver.rapid_override_speed_x,
                        self.driver.rapid_override_speed_y,
                    )
                )
            else:
                self.driver.rapid_override = False
                channel(_("Rapid Limit Off"))

        @self.console_argument("filename", type=str)
        @self.console_command(
            "egv_import",
            help=_("Lhystudios Engrave Buffer Import. egv_import <egv_file>"),
        )
        def egv_import(filename, **kwargs):
            if filename is None:
                raise SyntaxError

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

            def skip_header(file):
                skip(file, "\n", 3)
                skip(file, "%", 5)

            with open(filename, "r") as f:
                skip_header(f)
                while True:
                    data = f.read(1024)
                    if not data:
                        break
                    buffer = bytes(data, "utf8")
                    self.output.write(buffer)
                self.output.write(b"\n")

        @self.console_argument("filename", type=str)
        @self.console_command(
            "egv_export",
            help=_("Lhystudios Engrave Buffer Export. egv_export <egv_file>"),
        )
        def egv_export(channel, _, filename, **kwargs):
            if filename is None:
                raise SyntaxError
            try:
                with open(filename, "w") as f:
                    f.write("Document type : LHYMICRO-GL file\n")
                    f.write("File version: 1.0.01\n")
                    f.write("Copyright: Unknown\n")
                    f.write(
                        "Creator-Software: %s v%s\n"
                        % (self.kernel.name, self.kernel.version)
                    )
                    f.write("\n")
                    f.write("%0%0%0%0%\n")
                    buffer = bytes(self.controller._buffer)
                    buffer += bytes(self.controller._queue)
                    f.write(buffer.decode("utf-8"))
            except (PermissionError, IOError):
                channel(_("Could not save: %s" % filename))

        @self.console_command(
            "egv",
            help=_("Lhystudios Engrave Code Sender. egv <lhymicro-gl>"),
        )
        def egv(command, channel, _, remainder=None, **kwargs):
            if not remainder:
                channel("Lhystudios Engrave Code Sender. egv <lhymicro-gl>")
            else:
                self.output.write(
                    bytes(remainder.replace("$", "\n").replace(" ", "\n"), "utf8")
                )

        @self.console_command(
            "challenge",
            help=_("Challenge code, challenge <serial number>"),
        )
        def challenge_egv(command, channel, _, remainder=None, **kwargs):
            if not remainder:
                raise SyntaxError
            else:
                challenge = bytearray.fromhex(
                    md5(bytes(remainder.upper(), "utf8")).hexdigest()
                )
                code = b"A%s\n" % challenge
                self.output.write(code)

        @self.console_command("start", help=_("Start Pipe to Controller"))
        def pipe_start(command, channel, _, **kwargs):
            self.controller.update_state(STATE_ACTIVE)
            self.controller.start()
            channel(_("Lhystudios Channel Started."))

        @self.console_command("hold", help=_("Hold Controller"))
        def pipe_pause(command, channel, _, **kwargs):
            self.controller.update_state(STATE_PAUSE)
            self.controller.pause()
            channel("Lhystudios Channel Paused.")

        @self.console_command("resume", help=_("Resume Controller"))
        def pipe_resume(command, channel, _, **kwargs):
            self.controller.update_state(STATE_ACTIVE)
            self.controller.start()
            channel(_("Lhystudios Channel Resumed."))

        @self.console_command("usb_connect", help=_("Connects USB"))
        def usb_connect(command, channel, _, **kwargs):
            try:
                self.controller.open()
                channel(_("Usb Connection Opened."))
            except ConnectionRefusedError:
                channel(_("Usb Connection Refused"))

        @self.console_command("usb_disconnect", help=_("Disconnects USB"))
        def usb_disconnect(command, channel, _, **kwargs):
            self.controller.close()
            channel(_("CH341 Closed."))

        @self.console_command("usb_reset", help=_("Reset USB device"))
        def usb_reset(command, channel, _, **kwargs):
            try:

                self.controller.usb_reset()
                channel(_("Usb Connection Reset"))
            except ConnectionError:
                channel(_("Usb Connection Error"))

        @self.console_command("usb_release", help=_("Release USB device"))
        def usb_release(command, channel, _, **kwargs):
            try:
                self.controller.usb_release()
                channel(_("Usb Connection Released"))
            except ConnectionError:
                channel(_("Usb Connection Error"))

        @self.console_command("usb_abort", help=_("Stops USB retries"))
        def usb_abort(command, channel, _, **kwargs):
            self.controller.abort_retry()

        @self.console_command("usb_continue", help=_("Continues USB retries"))
        def usb_continue(command, channel, _, **kwargs):
            self.controller.continue_retry()

        @self.console_option(
            "port", "p", type=int, default=23, help=_("port to listen on.")
        )
        @self.console_option(
            "silent",
            "s",
            type=bool,
            action="store_true",
            help=_("do not watch server channels"),
        )
        @self.console_option(
            "watch", "w", type=bool, action="store_true", help=_("watch send/recv data")
        )
        @self.console_option(
            "quit",
            "q",
            type=bool,
            action="store_true",
            help=_("shutdown current lhyserver"),
        )
        @self.console_command("lhyserver", help=_("activate the lhyserver."))
        def lhyserver(
            channel, _, port=23, silent=False, watch=False, quit=False, **kwargs
        ):
            try:
                server_name = "lhyserver%s" % self.path
                output = self.controller
                server = self.open_as("module/TCPServer", server_name, port=port)
                if quit:
                    self.close(server_name)
                    return
                channel(_("TCP Server for Lhystudios on port: %d" % port))
                if not silent:
                    console = kernel.channel("console")
                    server.events_channel.watch(console)
                    if watch:
                        server.data_channel.watch(console)
                channel(_("Watching Channel: %s") % "server")
                self.channel(
                    "{server_name}/recv".format(server_name=server_name)
                ).watch(output.write)
                channel(_("Attached: %s" % repr(output)))

            except OSError:
                channel(_("Server failed on port: %d") % port)
            except KeyError:
                channel(_("Server cannot be attached to any device."))
            return

        @self.console_command("lhyemulator", help=_("activate the lhyemulator."))
        def lhyemulator(channel, _, **kwargs):
            try:
                self.open_as("emulator/lhystudios", "lhyemulator")
                channel(_("Lhystudios Emulator attached to %s" % str(self)))
            except KeyError:
                channel(_("Emulator cannot be attached to any device."))
            return

    @property
    def output(self):
        """
        This is the controller in controller mode and the tcp in network mode.
        @return:
        """
        if self.networked:
            return self.tcp
        else:
            return self.controller


class LhystudiosDriver:
    """
    LhystudiosDriver provides Lhystudios specific coding for elements and sends it to the backend
    to write to the usb.

    The interpret() ticks to process additional data.
    """

    def __init__(self, context, *args, **kwargs):
        self.context = context
        self.name = str(self.context)

        self.root_context = context.root
        self.settings = LaserSettings()

        self.next = None
        self.prev = None

        self.spooler = None
        self.output = None

        self.process_item = None
        self.spooled_item = None
        self.holds = []
        self.temp_holds = []

        self.current_x = 0
        self.current_y = 0

        context.setting(bool, "plot_shift", False)
        self.plot_planner = PlotPlanner(self.settings)
        self.plot_planner.force_shift = context.plot_shift
        self.plot = None

        self.state = DRIVER_STATE_RAPID
        self.properties = 0
        self.is_relative = False
        self.laser = False
        self.root_context.setting(bool, "opt_rapid_between", True)
        self.root_context.setting(int, "opt_jog_mode", 0)
        self.root_context.setting(int, "opt_jog_minimum", 127)
        context._quit = False

        self.rapid = self.root_context.opt_rapid_between
        self.jog = self.root_context.opt_jog_mode
        self.rapid_override = False
        self.rapid_override_speed_x = 50.0
        self.rapid_override_speed_y = 50.0
        self._thread = None
        self._shutdown = False
        self.last_fetch = None

        kernel = context._kernel
        _ = kernel.translation

        self.CODE_RIGHT = b"B"
        self.CODE_LEFT = b"T"
        self.CODE_TOP = b"L"
        self.CODE_BOTTOM = b"R"
        self.CODE_ANGLE = b"M"
        self.CODE_LASER_ON = b"D"
        self.CODE_LASER_OFF = b"U"

        self.is_paused = False
        self.context._buffer_size = 0

        def primary_hold():
            if self.output is None:
                return True

            buffer = len(self.output)
            if buffer is None:
                return False
            return self.context.buffer_limit and buffer > self.context.buffer_max

        self.holds.append(primary_hold)

        self.update_codes()
        self.max_x = self.current_x
        self.max_y = self.current_y
        self.min_x = self.current_x
        self.min_y = self.current_y
        self.context = context

    def __repr__(self):
        return "LhystudiosDriver(%s)" % self.name

    def update_codes(self):
        if not self.context.swap_xy:
            self.CODE_RIGHT = b"B"
            self.CODE_LEFT = b"T"
            self.CODE_TOP = b"L"
            self.CODE_BOTTOM = b"R"
        else:
            self.CODE_RIGHT = b"R"
            self.CODE_LEFT = b"L"
            self.CODE_TOP = b"T"
            self.CODE_BOTTOM = b"B"
        if self.context.flip_x:
            q = self.CODE_LEFT
            self.CODE_LEFT = self.CODE_RIGHT
            self.CODE_RIGHT = q
        if self.context.flip_y:
            q = self.CODE_TOP
            self.CODE_TOP = self.CODE_BOTTOM
            self.CODE_BOTTOM = q

    def plotplanner_process(self):
        """
        Processes any data in the plot planner. Getting all relevant (x,y,on) plot values and performing the cardinal
        movements. Or updating the laser state based on the settings of the cutcode.

        :return:
        """
        if self.plot is None:
            return False
        if self.hold():
            return True
        for x, y, on in self.plot:
            sx = self.current_x
            sy = self.current_y
            # print("x: %s, y: %s -- c: %s, %s" % (str(x), str(y), str(sx), str(sy)))
            on = int(on)
            if on > 1:
                # Special Command.
                if on & PLOT_FINISH:  # Plot planner is ending.
                    self.ensure_rapid_mode()
                    break
                elif on & PLOT_SETTING:  # Plot planner settings have changed.
                    p_set = self.plot_planner.settings
                    s_set = self.settings
                    if p_set.power != s_set.power:
                        self.set_power(p_set.power)
                    if (
                        p_set.raster_step != s_set.raster_step
                        or p_set.speed != s_set.speed
                        or s_set.implicit_d_ratio != p_set.implicit_d_ratio
                        or s_set.implicit_accel != p_set.implicit_accel
                    ):
                        self.set_speed(p_set.speed)
                        self.set_step(p_set.raster_step)
                        self.set_acceleration(p_set.implicit_accel)
                        self.set_d_ratio(p_set.implicit_d_ratio)
                    self.settings.set_values(p_set)
                elif on & PLOT_AXIS:  # Major Axis.
                    self.set_prop(REQUEST_AXIS)
                    if x == 0:  # X Major / Horizontal.
                        self.set_prop(REQUEST_HORIZONTAL_MAJOR)
                    else:  # Y Major / Vertical
                        self.unset_prop(REQUEST_HORIZONTAL_MAJOR)
                elif on & PLOT_DIRECTION:
                    self.set_prop(REQUEST_X)
                    self.set_prop(REQUEST_Y)
                    if x == 1:  # Moving Right. +x
                        self.unset_prop(REQUEST_X_FORWARD_LEFT)
                    else:  # Moving Left -x
                        self.set_prop(REQUEST_X_FORWARD_LEFT)
                    if y == 1:  # Moving Bottom +y
                        self.unset_prop(REQUEST_Y_FORWARD_TOP)
                    else:  # Moving Top. -y
                        self.set_prop(REQUEST_Y_FORWARD_TOP)
                elif on & (
                    PLOT_RAPID | PLOT_JOG
                ):  # Plot planner requests position change.
                    if on & PLOT_RAPID or self.state != DRIVER_STATE_PROGRAM:
                        # Perform a rapid position change. Always perform this for raster moves.
                        # DRIVER_STATE_RASTER should call this code as well.
                        self.ensure_rapid_mode()
                        self.move_absolute(x, y)
                    else:
                        # Jog is performable and requested. # We have not flagged our direction or state.
                        self.jog_absolute(x, y, mode=self.root_context.opt_jog_mode)
                continue
            dx = x - sx
            dy = y - sy
            step = self.settings.raster_step
            if step == 0:
                self.ensure_program_mode()
            else:
                self.ensure_raster_mode()
                if self.is_prop(STATE_X_STEPPER_ENABLE):
                    if dy != 0:
                        if self.is_prop(STATE_Y_FORWARD_TOP):
                            if abs(dy) > step:
                                self.ensure_finished_mode()
                                self.move_relative(0, dy + step)
                                self.set_prop(STATE_X_STEPPER_ENABLE)
                                self.unset_prop(STATE_Y_STEPPER_ENABLE)
                                self.ensure_raster_mode()
                        else:
                            if abs(dy) > step:
                                self.ensure_finished_mode()
                                self.move_relative(0, dy - step)
                                self.set_prop(STATE_X_STEPPER_ENABLE)
                                self.unset_prop(STATE_Y_STEPPER_ENABLE)
                                self.ensure_raster_mode()
                        self.h_switch()
                elif self.is_prop(STATE_Y_STEPPER_ENABLE):
                    if dx != 0:
                        if self.is_prop(STATE_X_FORWARD_LEFT):
                            if abs(dx) > step:
                                self.ensure_finished_mode()
                                self.move_relative(dx + step, 0)
                                self.set_prop(STATE_Y_STEPPER_ENABLE)
                                self.unset_prop(STATE_X_STEPPER_ENABLE)
                                self.ensure_raster_mode()
                        else:
                            if abs(dx) > step:
                                self.ensure_finished_mode()
                                self.move_relative(dx - step, 0)
                                self.set_prop(STATE_Y_STEPPER_ENABLE)
                                self.unset_prop(STATE_X_STEPPER_ENABLE)
                                self.ensure_raster_mode()
                        self.v_switch()
            self.goto_octent_abs(x, y, on & 1)
            if self.hold():
                return True
        self.plot = None
        return False

    def pause(self, *values):
        self.data_output(b"~PN!\n~")
        self.is_paused = True

    def resume(self, *values):
        self.data_output(b"~PN&\n~")
        self.is_paused = False

    def reset(self):
        if self.spooler is not None:
            self.spooler.clear_queue()
        self.plot_planner.clear()
        self.spooled_item = None
        self.temp_holds.clear()

        self.context.signal("pipe;buffer", 0)
        self.data_output(b"~I*\n~")
        self.laser = False
        self.properties = 0
        self.state = DRIVER_STATE_RAPID
        self.context.signal("driver;mode", self.state)
        self.is_paused = False

    def send_blob(self, blob_type, data):
        if blob_type == "egv":
            self.data_output(data)

    def cut(self, x, y):
        self.goto(x, y, True)

    def cut_absolute(self, x, y):
        self.goto_absolute(x, y, True)

    def cut_relative(self, x, y):
        self.goto_relative(x, y, True)

    def jog(self, x, y, **kwargs):
        if self.is_relative:
            self.jog_relative(x, y, **kwargs)
        else:
            self.jog_absolute(x, y, **kwargs)

    def jog_absolute(self, x, y, **kwargs):
        self.jog_relative(x - self.current_x, y - self.current_y, **kwargs)

    def jog_relative(self, dx, dy, mode=0):
        self.laser_off()
        dx = int(round(dx))
        dy = int(round(dy))
        if mode == 0:
            self._nse_jog_event(dx, dy)
        elif mode == 1:
            self.mode_shift_on_the_fly(dx, dy)
        else:
            # Finish-out Jog
            self.ensure_rapid_mode()
            self.move_relative(dx, dy)
            self.ensure_program_mode()

    def _nse_jog_event(self, dx=0, dy=0, speed=None):
        """
        NSE Jog events are performed from program or raster mode and skip out to rapid mode to perform
        a single jog command. This jog effect varies based on the horizontal vertical major setting and
        needs to counteract the jogged head according to those settings.

        NSE jogs will not change the underlying mode even though they temporarily switch into
        rapid mode. nse jogs are not done in raster mode.
        """
        dx = int(round(dx))
        dy = int(round(dy))
        original_state = self.state
        self.state = DRIVER_STATE_RAPID
        self.laser = False
        if self.is_prop(STATE_HORIZONTAL_MAJOR):
            if not self.is_left and dx >= 0:
                self.data_output(self.CODE_LEFT)
            if not self.is_right and dx <= 0:
                self.data_output(self.CODE_RIGHT)
        else:
            if not self.is_top and dy >= 0:
                self.data_output(self.CODE_TOP)
            if not self.is_bottom and dy <= 0:
                self.data_output(self.CODE_BOTTOM)
        self.data_output(b"N")
        if dy != 0:
            self.goto_y(dy)
        if dx != 0:
            self.goto_x(dx)
        if speed is not None:
            speed_code = LaserSpeed(
                self.context.board,
                self.settings.speed,
                self.settings.raster_step,
                d_ratio=self.settings.implicit_d_ratio,
                acceleration=self.settings.implicit_accel,
                fix_limit=True,
                fix_lows=True,
                fix_speeds=self.context.fix_speeds,
                raster_horizontal=True,
            ).speedcode
            self.data_output(bytes(speed_code, "utf8"))
        self.data_output(b"SE")
        self.declare_directions()
        self.state = original_state

    def move(self, x, y):
        self.goto(x, y, False)

    def move_absolute(self, x, y):
        self.goto_absolute(x, y, False)

    def move_relative(self, x, y):
        self.goto_relative(x, y, False)

    def goto(self, x, y, cut):
        """
        Goto a position within a cut.

        This depends on whether is_relative is set.

        :param x:
        :param y:
        :param cut:
        :return:
        """
        if self.is_relative:
            self.goto_relative(x, y, cut)
        else:
            self.goto_absolute(x, y, cut)

    def goto_absolute(self, x, y, cut):
        """
        Goto absolute x and y. With cut set or not set.

        :param x:
        :param y:
        :param cut:
        :return:
        """
        self.goto_relative(x - self.current_x, y - self.current_y, cut)

    def goto_relative(self, dx, dy, cut):
        """
        Goto relative dx, dy. With cut set or not set.

        :param dx:
        :param dy:
        :param cut:
        :return:
        """
        if abs(dx) == 0 and abs(dy) == 0:
            return
        dx = int(round(dx))
        dy = int(round(dy))
        if self.state == DRIVER_STATE_RAPID:
            if self.rapid_override and (dx != 0 or dy != 0):
                # Rapid movement override. Should make programmed jogs.
                self.set_acceleration(None)
                self.set_step(0)
                if dx != 0:
                    self.ensure_rapid_mode()
                    self.set_speed(self.rapid_override_speed_x)
                    self.ensure_program_mode()
                    self.goto_octent(dx, 0, cut)
                if dy != 0:
                    if self.rapid_override_speed_x != self.rapid_override_speed_y:
                        self.ensure_rapid_mode()
                        self.set_speed(self.rapid_override_speed_y)
                        self.ensure_program_mode()
                    self.goto_octent(0, dy, cut)
                self.ensure_rapid_mode()
            else:
                self.data_output(b"I")
                if dx != 0:
                    self.goto_x(dx)
                if dy != 0:
                    self.goto_y(dy)
                self.data_output(b"S1P\n")
                if not self.context.autolock:
                    self.data_output(b"IS2P\n")
        elif self.state == DRIVER_STATE_RASTER:
            # goto in raster, switches to program to recall this function.
            self.ensure_program_mode()
            self.goto_relative(dx, dy, cut)
            return
        elif self.state == DRIVER_STATE_PROGRAM:
            mx = 0
            my = 0
            line = list(grouped(ZinglPlotter.plot_line(0, 0, dx, dy)))
            for x, y in line:
                self.goto_octent(x - mx, y - my, cut)
                mx = x
                my = y
        elif self.state == DRIVER_STATE_FINISH:
            if dx != 0:
                self.goto_x(dx)
            if dy != 0:
                self.goto_y(dy)
            self.data_output(b"N")
        elif self.state == DRIVER_STATE_MODECHANGE:
            self.mode_shift_on_the_fly(dx, dy)
        self.check_bounds()
        self.context.signal(
            "driver;position",
            (self.current_x - dx, self.current_y - dy, self.current_x, self.current_y),
        )

    def goto_octent_abs(self, x, y, on):
        dx = x - self.current_x
        dy = y - self.current_y
        self.goto_octent(dx, dy, on)

    def goto_octent(self, dx, dy, on):
        if dx == 0 and dy == 0:
            return
        if on:
            self.laser_on()
        else:
            self.laser_off()
        if abs(dx) == abs(dy):
            if dx != 0:
                self.goto_angle(dx, dy)
        elif dx != 0:
            self.goto_x(dx)
            if dy != 0:
                raise ValueError(
                    "Not a valid diagonal or orthogonal movement. (dx=%s, dy=%s)"
                    % (str(dx), str(dy))
                )
        else:
            self.goto_y(dy)
            if dx != 0:
                raise ValueError(
                    "Not a valid diagonal or orthogonal movement. (dx=%s, dy=%s)"
                    % (str(dx), str(dy))
                )
        self.context.signal(
            "driver;position",
            (self.current_x - dx, self.current_y - dy, self.current_x, self.current_y),
        )

    def set_speed(self, speed=None):
        if self.settings.speed != speed:
            self.settings.speed = speed
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def set_d_ratio(self, dratio=None):
        if self.settings.dratio != dratio:
            self.settings.dratio = dratio
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def set_acceleration(self, accel=None):
        if self.settings.acceleration != accel:
            self.settings.acceleration = accel
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def set_step(self, step=None):
        if self.settings.raster_step != step:
            self.settings.raster_step = step
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def laser_off(self):
        if not self.laser:
            return False
        if self.state == DRIVER_STATE_RAPID:
            self.data_output(b"I")
            self.data_output(self.CODE_LASER_OFF)
            self.data_output(b"S1P\n")
            if not self.context.autolock:
                self.data_output(b"IS2P\n")
        elif self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
            self.data_output(self.CODE_LASER_OFF)
        elif self.state == DRIVER_STATE_FINISH:
            self.data_output(self.CODE_LASER_OFF)
            self.data_output(b"N")
        self.laser = False
        return True

    def laser_on(self):
        if self.laser:
            return False
        if self.state == DRIVER_STATE_RAPID:
            self.data_output(b"I")
            self.data_output(self.CODE_LASER_ON)
            self.data_output(b"S1P\n")
            if not self.context.autolock:
                self.data_output(b"IS2P\n")
        elif self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
            self.data_output(self.CODE_LASER_ON)
        elif self.state == DRIVER_STATE_FINISH:
            self.data_output(self.CODE_LASER_ON)
            self.data_output(b"N")
        self.laser = True
        return True

    def ensure_rapid_mode(self, *values):
        if self.state == DRIVER_STATE_RAPID:
            return
        if self.state == DRIVER_STATE_FINISH:
            self.data_output(b"S1P\n")
            if not self.context.autolock:
                self.data_output(b"IS2P\n")
        elif self.state in (
            DRIVER_STATE_PROGRAM,
            DRIVER_STATE_RASTER,
            DRIVER_STATE_MODECHANGE,
        ):
            self.data_output(b"FNSE-\n")
            self.laser = False
        self.state = DRIVER_STATE_RAPID
        self.context.signal("driver;mode", self.state)

    def mode_shift_on_the_fly(self, dx=0, dy=0):
        """
        Mode shift on the fly changes the current modes while in programmed or raster mode
        this exits with a @ command that resets the modes. A movement operation can be added after
        the speed code and before the return to into programmed or raster mode.

        This switch is often avoided because testing revealed some chance of a runaway during reset
        switching.

        If the raster step has been changed from zero this can result in shifting from program to raster mode
        """
        dx = int(round(dx))
        dy = int(round(dy))
        self.data_output(b"@NSE")
        self.state = DRIVER_STATE_RAPID
        speed_code = LaserSpeed(
            self.context.board,
            self.settings.speed,
            self.settings.raster_step,
            d_ratio=self.settings.implicit_d_ratio,
            acceleration=self.settings.implicit_accel,
            fix_limit=True,
            fix_lows=True,
            fix_speeds=self.context.fix_speeds,
            raster_horizontal=True,
        ).speedcode
        self.data_output(bytes(speed_code, "utf8"))
        if dx != 0:
            self.goto_x(dx)
        if dy != 0:
            self.goto_y(dy)
        self.data_output(b"N")
        self.set_requested_directions()
        self.data_output(self.code_declare_directions())
        self.data_output(b"S1E")
        if self.settings.raster_step == 0:
            self.state = DRIVER_STATE_PROGRAM
        else:
            self.state = DRIVER_STATE_RASTER

    def ensure_finished_mode(self, *values):
        if self.state == DRIVER_STATE_FINISH:
            return
        if self.state in (
            DRIVER_STATE_PROGRAM,
            DRIVER_STATE_RASTER,
            DRIVER_STATE_MODECHANGE,
        ):
            self.data_output(b"@NSE")
            self.laser = False
        elif self.state == DRIVER_STATE_RAPID:
            self.data_output(b"I")
        self.state = DRIVER_STATE_FINISH
        self.context.signal("driver;mode", self.state)

    def ensure_raster_mode(self, *values):
        if self.state == DRIVER_STATE_RASTER:
            return
        self.ensure_finished_mode()

        speed_code = LaserSpeed(
            self.context.board,
            self.settings.speed,
            self.settings.raster_step,
            d_ratio=self.settings.implicit_d_ratio,
            acceleration=self.settings.implicit_accel,
            fix_limit=True,
            fix_lows=True,
            fix_speeds=self.context.fix_speeds,
            raster_horizontal=True,
        ).speedcode
        self.data_output(bytes(speed_code, "utf8"))
        self.data_output(b"N")
        self.set_requested_directions()
        self.declare_directions()
        self.data_output(b"S1E")
        self.state = DRIVER_STATE_RASTER
        self.context.signal("driver;mode", self.state)

    def ensure_program_mode(self, *values):
        if self.state == DRIVER_STATE_PROGRAM:
            return
        self.ensure_finished_mode()

        speed_code = LaserSpeed(
            self.context.board,
            self.settings.speed,
            self.settings.raster_step,
            d_ratio=self.settings.implicit_d_ratio,
            acceleration=self.settings.implicit_accel,
            fix_limit=True,
            fix_lows=True,
            fix_speeds=self.context.fix_speeds,
            raster_horizontal=True,
        ).speedcode
        self.data_output(bytes(speed_code, "utf8"))
        self.data_output(b"N")
        self.set_requested_directions()
        self.declare_directions()
        self.data_output(b"S1E")
        self.state = DRIVER_STATE_PROGRAM
        self.context.signal("driver;mode", self.state)

    def h_switch(self):
        if self.is_prop(STATE_X_FORWARD_LEFT):
            self.data_output(self.CODE_RIGHT)
            self.unset_prop(STATE_X_FORWARD_LEFT)
        else:
            self.data_output(self.CODE_LEFT)
            self.set_prop(STATE_X_FORWARD_LEFT)
        if self.is_prop(STATE_Y_FORWARD_TOP):
            self.current_y -= self.settings.raster_step
        else:
            self.current_y += self.settings.raster_step
        self.laser = False

    def v_switch(self):
        if self.is_prop(STATE_Y_FORWARD_TOP):
            self.data_output(self.CODE_BOTTOM)
            self.unset_prop(STATE_Y_FORWARD_TOP)
        else:
            self.data_output(self.CODE_TOP)
            self.set_prop(STATE_Y_FORWARD_TOP)
        if self.is_prop(STATE_X_FORWARD_LEFT):
            self.current_x -= self.settings.raster_step
        else:
            self.current_x += self.settings.raster_step
        self.laser = False

    def calc_home_position(self):
        x = 0
        y = 0
        if self.context.home_right:
            x = int(self.context.device.bedwidth)
        if self.context.home_bottom:
            y = int(self.context.device.bedheight)
        return x, y

    def home(self, *values):
        x, y = self.calc_home_position()
        self.ensure_rapid_mode()
        self.data_output(b"IPP\n")
        old_x = self.current_x
        old_y = self.current_y
        self.current_x = x
        self.current_y = y
        self.reset_modes()
        self.state = DRIVER_STATE_RAPID
        adjust_x = self.context.home_adjust_x
        adjust_y = self.context.home_adjust_y
        try:
            adjust_x = int(values[0])
        except (ValueError, IndexError):
            pass
        try:
            adjust_y = int(values[1])
        except (ValueError, IndexError):
            pass
        if adjust_x != 0 or adjust_y != 0:
            # Perform post home adjustment.
            self.move_relative(adjust_x, adjust_y)
            # Erase adjustment
            self.current_x = x
            self.current_y = y

        self.context.signal("driver;mode", self.state)
        self.context.signal(
            "driver;position", (old_x, old_y, self.current_x, self.current_y)
        )

    def lock_rail(self):
        self.ensure_rapid_mode()
        self.data_output(b"IS1P\n")

    def unlock_rail(self, abort=False):
        self.ensure_rapid_mode()
        self.data_output(b"IS2P\n")

    def abort(self):
        self.data_output(b"I\n")

    def check_bounds(self):
        self.min_x = min(self.min_x, self.current_x)
        self.min_y = min(self.min_y, self.current_y)
        self.max_x = max(self.max_x, self.current_x)
        self.max_y = max(self.max_y, self.current_y)

    def reset_modes(self):
        self.laser = False
        self.properties = 0

    def goto_x(self, dx):
        if dx > 0:
            self.move_right(dx)
        else:
            self.move_left(dx)

    def goto_y(self, dy):
        if dy > 0:
            self.move_bottom(dy)
        else:
            self.move_top(dy)

    def goto_angle(self, dx, dy):
        if abs(dx) != abs(dy):
            raise ValueError("abs(dx) must equal abs(dy)")
        self.set_prop(STATE_X_STEPPER_ENABLE)  # Set both on
        self.set_prop(STATE_Y_STEPPER_ENABLE)
        if dx > 0:  # Moving right
            if self.is_prop(STATE_X_FORWARD_LEFT):
                self.data_output(self.CODE_RIGHT)
                self.unset_prop(STATE_X_FORWARD_LEFT)
        else:  # Moving left
            if not self.is_prop(STATE_X_FORWARD_LEFT):
                self.data_output(self.CODE_LEFT)
                self.set_prop(STATE_X_FORWARD_LEFT)
        if dy > 0:  # Moving bottom
            if self.is_prop(STATE_Y_FORWARD_TOP):
                self.data_output(self.CODE_BOTTOM)
                self.unset_prop(STATE_Y_FORWARD_TOP)
        else:  # Moving top
            if not self.is_prop(STATE_Y_FORWARD_TOP):
                self.data_output(self.CODE_TOP)
                self.set_prop(STATE_Y_FORWARD_TOP)
        self.current_x += dx
        self.current_y += dy
        self.check_bounds()
        self.data_output(self.CODE_ANGLE + lhymicro_distance(abs(dy)))

    def set_requested_directions(self):
        if self.context.strict:
            self.unset_prop(STATE_X_FORWARD_LEFT)
            self.unset_prop(STATE_Y_FORWARD_TOP)
            self.unset_prop(STATE_HORIZONTAL_MAJOR)
        else:
            if self.is_prop(REQUEST_X):
                if self.is_prop(REQUEST_X_FORWARD_LEFT):
                    self.set_prop(STATE_X_FORWARD_LEFT)
                else:
                    self.unset_prop(STATE_X_FORWARD_LEFT)
                self.unset_prop(REQUEST_X)
            if self.is_prop(REQUEST_Y):
                if self.is_prop(REQUEST_Y_FORWARD_TOP):
                    self.set_prop(STATE_Y_FORWARD_TOP)
                else:
                    self.unset_prop(STATE_Y_FORWARD_TOP)
                self.unset_prop(REQUEST_Y)
            if self.is_prop(REQUEST_AXIS):
                if self.is_prop(REQUEST_HORIZONTAL_MAJOR):
                    self.set_prop(STATE_HORIZONTAL_MAJOR)
                else:
                    self.unset_prop(STATE_HORIZONTAL_MAJOR)
                self.unset_prop(REQUEST_AXIS)

    def declare_directions(self):
        """Declare direction declares raster directions of left, top, with the primary momentum direction going last.
        You cannot declare a diagonal direction."""
        self.data_output(self.code_declare_directions())

    def code_declare_directions(self):
        x_dir = (
            self.CODE_LEFT if self.is_prop(STATE_X_FORWARD_LEFT) else self.CODE_RIGHT
        )
        y_dir = self.CODE_TOP if self.is_prop(STATE_Y_FORWARD_TOP) else self.CODE_BOTTOM
        if self.is_prop(STATE_HORIZONTAL_MAJOR):
            self.set_prop(STATE_X_STEPPER_ENABLE)
            self.unset_prop(STATE_Y_STEPPER_ENABLE)
            return y_dir + x_dir
        else:
            self.unset_prop(STATE_X_STEPPER_ENABLE)
            self.set_prop(STATE_Y_STEPPER_ENABLE)
            return x_dir + y_dir

    @property
    def is_left(self):
        return (
            self.is_prop(STATE_X_STEPPER_ENABLE)
            and not self.is_prop(STATE_Y_STEPPER_ENABLE)
            and self.is_prop(STATE_X_FORWARD_LEFT)
        )

    @property
    def is_right(self):
        return (
            self.is_prop(STATE_X_STEPPER_ENABLE)
            and not self.is_prop(STATE_Y_STEPPER_ENABLE)
            and not self.is_prop(STATE_X_FORWARD_LEFT)
        )

    @property
    def is_top(self):
        return (
            not self.is_prop(STATE_X_STEPPER_ENABLE)
            and self.is_prop(STATE_Y_STEPPER_ENABLE)
            and self.is_prop(STATE_Y_FORWARD_TOP)
        )

    @property
    def is_bottom(self):
        return (
            not self.is_prop(STATE_X_STEPPER_ENABLE)
            and self.is_prop(STATE_Y_STEPPER_ENABLE)
            and not self.is_prop(STATE_Y_FORWARD_TOP)
        )

    @property
    def is_angle(self):
        return self.is_prop(STATE_Y_STEPPER_ENABLE) and self.is_prop(
            STATE_X_STEPPER_ENABLE
        )

    def set_left(self):
        self.set_prop(STATE_X_STEPPER_ENABLE)
        self.unset_prop(STATE_Y_STEPPER_ENABLE)
        self.set_prop(STATE_X_FORWARD_LEFT)

    def set_right(self):
        self.set_prop(STATE_X_STEPPER_ENABLE)
        self.unset_prop(STATE_Y_STEPPER_ENABLE)
        self.unset_prop(STATE_X_FORWARD_LEFT)

    def set_top(self):
        self.unset_prop(STATE_X_STEPPER_ENABLE)
        self.set_prop(STATE_Y_STEPPER_ENABLE)
        self.set_prop(STATE_Y_FORWARD_TOP)

    def set_bottom(self):
        self.unset_prop(STATE_X_STEPPER_ENABLE)
        self.set_prop(STATE_Y_STEPPER_ENABLE)
        self.unset_prop(STATE_Y_FORWARD_TOP)

    def move_right(self, dx=0):
        self.current_x += dx
        if not self.is_right or self.state not in (
            DRIVER_STATE_PROGRAM,
            DRIVER_STATE_RASTER,
        ):
            self.data_output(self.CODE_RIGHT)
            self.set_right()
        if dx != 0:
            self.data_output(lhymicro_distance(abs(dx)))
            self.check_bounds()

    def move_left(self, dx=0):
        self.current_x -= abs(dx)
        if not self.is_left or self.state not in (
            DRIVER_STATE_PROGRAM,
            DRIVER_STATE_RASTER,
        ):
            self.data_output(self.CODE_LEFT)
            self.set_left()
        if dx != 0:
            self.data_output(lhymicro_distance(abs(dx)))
            self.check_bounds()

    def move_bottom(self, dy=0):
        self.current_y += dy
        if not self.is_bottom or self.state not in (
            DRIVER_STATE_PROGRAM,
            DRIVER_STATE_RASTER,
        ):
            self.data_output(self.CODE_BOTTOM)
            self.set_bottom()
        if dy != 0:
            self.data_output(lhymicro_distance(abs(dy)))
            self.check_bounds()

    def move_top(self, dy=0):
        self.current_y -= abs(dy)
        if not self.is_top or self.state not in (
            DRIVER_STATE_PROGRAM,
            DRIVER_STATE_RASTER,
        ):
            self.data_output(self.CODE_TOP)
            self.set_top()
        if dy != 0:
            self.data_output(lhymicro_distance(abs(dy)))
            self.check_bounds()

    ######################
    # ORIGINAL DRIVER CODE
    ######################

    def shutdown(self, *args, **kwargs):
        self._shutdown = True

    def added(self, origin=None, *args):
        if self._thread is None:

            def clear_thread(*a):
                self._shutdown = True

            self._thread = self.context.threaded(
                self._driver_threaded,
                result=clear_thread,
                thread_name="Driver(%s)" % self.context.path,
            )
            self._thread.stop = clear_thread

    def _driver_threaded(self, *args):
        """
        Fetch and Execute.

        :param args:
        :return:
        """
        while True:
            if self._shutdown:
                return
            if self.spooled_item is None:
                self._fetch_next_item_from_spooler()
            if self.spooled_item is None:
                # There is no data to interpret. Fetch Failed.
                if self.context._quit:
                    self.context("quit\n")
                    self._shutdown = True
                    return
                time.sleep(0.1)
            self._process_spooled_item()

    def _process_spooled_item(self):
        """
        Default Execution Cycle. If Held, we wait. Otherwise we process the spooler.

        Processes one item in the spooler. If the spooler item is a generator. Process one generated item.
        """
        if self.hold():
            time.sleep(0.01)
            return
        if self.plotplanner_process():
            return
        if self.spooled_item is None:
            return  # Fetch Next.

        # We have a spooled item to process.
        if self.command(self.spooled_item):
            self.spooled_item = None
            self.spooler.pop()
            return

        # We are dealing with an iterator/generator
        try:
            e = next(self.spooled_item)
            if not self.command(e):
                raise ValueError
        except StopIteration:
            # The spooled item is finished.
            self.spooled_item = None
            self.spooler.pop()

    def _fetch_next_item_from_spooler(self):
        """
        Fetches the next item from the spooler.

        :return:
        """
        if self.spooler is None:
            return  # Spooler does not exist.
        element = self.spooler.peek()

        if self.last_fetch is not None:
            self.context.channel("spooler")(
                "Time between fetches: %f" % (time.time() - self.last_fetch)
            )
            self.last_fetch = None

        if element is None:
            return  # Spooler is empty.

        self.last_fetch = time.time()

        # self.spooler.pop()
        if isinstance(element, int):
            self.spooled_item = (element,)
        elif isinstance(element, tuple):
            self.spooled_item = element
        else:
            self.rapid = self.root_context.opt_rapid_between
            self.jog = self.root_context.opt_jog_mode
            try:
                self.spooled_item = element.generate()
            except AttributeError:
                try:
                    self.spooled_item = element()
                except TypeError:
                    # This could be a text element, some unrecognized type.
                    return

    def command(self, command, *values):
        """Commands are middle language LaserCommandConstants there values are given."""
        if isinstance(command, tuple):
            values = command[1:]
            command = command[0]
        if not isinstance(command, int):
            return False  # Command type is not recognized.

        try:
            if command == COMMAND_LASER_OFF:
                self.laser_off()
            elif command == COMMAND_LASER_ON:
                self.laser_on()
            elif command == COMMAND_LASER_DISABLE:
                self.laser_disable()
            elif command == COMMAND_LASER_ENABLE:
                self.laser_enable()
            elif command == COMMAND_CUT:
                x, y = values
                self.cut(x, y)
            elif command == COMMAND_MOVE:
                x, y = values
                self.move(x, y)
            elif command == COMMAND_JOG:
                x, y = values
                self.jog(x, y, mode=0, min_jog=self.context.opt_jog_minimum)
            elif command == COMMAND_JOG_SWITCH:
                x, y = values
                self.jog(x, y, mode=1, min_jog=self.context.opt_jog_minimum)
            elif command == COMMAND_JOG_FINISH:
                x, y = values
                self.jog(x, y, mode=2, min_jog=self.context.opt_jog_minimum)
            elif command == COMMAND_HOME:
                self.home(*values)
            elif command == COMMAND_LOCK:
                self.lock_rail()
            elif command == COMMAND_UNLOCK:
                self.unlock_rail()
            elif command == COMMAND_PLOT:
                self.plot_plot(values[0])
            elif command == COMMAND_BLOB:
                self.send_blob(values[0], values[1])
            elif command == COMMAND_PLOT_START:
                self.plot_start()
            elif command == COMMAND_SET_SPEED:
                self.set_speed(values[0])
            elif command == COMMAND_SET_POWER:
                self.set_power(values[0])
            elif command == COMMAND_SET_PPI:
                self.set_ppi(values[0])
            elif command == COMMAND_SET_PWM:
                self.set_pwm(values[0])
            elif command == COMMAND_SET_STEP:
                self.set_step(values[0])
            elif command == COMMAND_SET_OVERSCAN:
                self.set_overscan(values[0])
            elif command == COMMAND_SET_ACCELERATION:
                self.set_acceleration(values[0])
            elif command == COMMAND_SET_D_RATIO:
                self.set_d_ratio(values[0])
            elif command == COMMAND_SET_DIRECTION:
                self.set_directions(values[0], values[1], values[2], values[3])
            elif command == COMMAND_SET_INCREMENTAL:
                self.set_incremental()
            elif command == COMMAND_SET_ABSOLUTE:
                self.set_absolute()
            elif command == COMMAND_SET_POSITION:
                self.set_position(values[0], values[1])
            elif command == COMMAND_MODE_RAPID:
                self.ensure_rapid_mode(*values)
            elif command == COMMAND_MODE_PROGRAM:
                self.ensure_program_mode(*values)
            elif command == COMMAND_MODE_RASTER:
                self.ensure_raster_mode(*values)
            elif command == COMMAND_MODE_FINISHED:
                self.ensure_finished_mode(*values)
            elif command == COMMAND_WAIT:
                self.wait(values[0])
            elif command == COMMAND_WAIT_FINISH:
                self.wait_finish()
            elif command == COMMAND_BEEP:
                OS_NAME = platform.system()
                if OS_NAME == "Windows":
                    try:
                        import winsound

                        for x in range(5):
                            winsound.Beep(2000, 100)
                    except Exception:
                        pass
                elif OS_NAME == "Darwin":  # Mac
                    os.system("afplay /System/Library/Sounds/Ping.aiff")
                else:  # Assuming other linux like system
                    print("\a")  # Beep.
            elif command == COMMAND_FUNCTION:
                if len(values) >= 1:
                    t = values[0]
                    if callable(t):
                        t()
            elif command == COMMAND_SIGNAL:
                if isinstance(values, str):
                    self.context.signal(values, None)
                elif len(values) >= 2:
                    self.context.signal(values[0], *values[1:])
        except AttributeError:
            pass
        return True

    def realtime_command(self, command, *values):
        """Asks for the execution of a realtime command. Unlike the spooled commands these
        return False if rejected and something else if able to be performed. These will not
        be queued. If rejected. They must be performed in realtime or cancelled.
        """
        try:
            if command == REALTIME_PAUSE:
                self.pause()
            elif command == REALTIME_RESUME:
                self.resume()
            elif command == REALTIME_RESET:
                self.reset()
            elif command == REALTIME_STATUS:
                self.status()
        except AttributeError:
            pass  # Method doesn't exist.

    def data_output(self, e):
        self.output.write(e)

    def hold(self):
        """
        Holds are criteria to use to pause the data interpretation. These halt the production of new data until the
        criteria is met. A hold is constant and will always halt the data while true. A temp_hold will be removed
        as soon as it does not hold the data.

        :return: Whether data interpretation should hold.
        """
        temp_hold = False
        fail_hold = False
        for i, hold in enumerate(self.temp_holds):
            if not hold():
                self.temp_holds[i] = None
                fail_hold = True
            else:
                temp_hold = True
        if fail_hold:
            self.temp_holds = [hold for hold in self.temp_holds if hold is not None]
        if temp_hold:
            return True
        for hold in self.holds:
            if hold():
                return True
        return False

    def laser_disable(self, *values):
        self.settings.laser_enabled = False

    def laser_enable(self, *values):
        self.settings.laser_enabled = True

    def plot_plot(self, plot):
        """
        :param plot:
        :return:
        """
        self.plot_planner.push(plot)

    def plot_start(self):
        if self.plot is None:
            self.plot = self.plot_planner.gen()

    def set_power(self, power=1000.0):
        self.settings.power = power
        if self.settings.power > 1000.0:
            self.settings.power = 1000.0
        if self.settings.power <= 0:
            self.settings.power = 0.0

    def set_ppi(self, power=1000.0):
        self.settings.power = power
        if self.settings.power > 1000.0:
            self.settings.power = 1000.0
        if self.settings.power <= 0:
            self.settings.power = 0.0

    def set_pwm(self, power=1000.0):
        self.settings.power = power
        if self.settings.power > 1000.0:
            self.settings.power = 1000.0
        if self.settings.power <= 0:
            self.settings.power = 0.0

    def set_overscan(self, overscan=None):
        self.settings.overscan = overscan

    def set_incremental(self, *values):
        self.is_relative = True

    def set_absolute(self, *values):
        self.is_relative = False

    def set_position(self, x, y):
        self.current_x = x
        self.current_y = y

    def wait(self, t):
        time.sleep(float(t))

    def wait_finish(self, *values):
        """Adds an additional holding requirement if the pipe has any data."""
        self.temp_holds.append(lambda: len(self.output) != 0)

    def status(self):
        parts = list()
        parts.append("x=%f" % self.current_x)
        parts.append("y=%f" % self.current_y)
        parts.append("speed=%f" % self.settings.speed)
        parts.append("power=%d" % self.settings.power)
        status = ";".join(parts)
        self.context.signal("driver;status", status)

    def set_prop(self, mask):
        self.properties |= mask

    def unset_prop(self, mask):
        self.properties &= ~mask

    def is_prop(self, mask):
        return bool(self.properties & mask)

    def toggle_prop(self, mask):
        if self.is_prop(mask):
            self.unset_prop(mask)
        else:
            self.set_prop(mask)

    @property
    def type(self):
        return "lhystudios"


class LhystudiosController:
    """
    K40 Controller controls the Lhystudios boards sending any queued data to the USB when the signal is not busy.

    Opening and closing of the pipe are dealt with internally. There are three primary monitor data channels.
    'send', 'recv' and 'usb'. They display the reading and writing of information to/from the USB and the USB connection
    log, providing information about the connecting and error status of the USB device.
    """

    def __init__(self, context, *args, **kwargs):
        self.context = context
        self.state = STATE_UNKNOWN
        self.is_shutdown = False

        self._thread = None
        self._buffer = (
            bytearray()
        )  # Threadsafe buffered commands to be sent to controller.
        self._realtime_buffer = (
            bytearray()  # Threadsafe realtime buffered commands to be sent to the controller.
        )
        self._queue = bytearray()  # Thread-unsafe additional commands to append.
        self._preempt = (
            bytearray()
        )  # Thread-unsafe preempt commands to prepend to the buffer.
        self.context._buffer_size = 0
        self._queue_lock = threading.Lock()
        self._preempt_lock = threading.Lock()
        self._main_lock = threading.Lock()

        self._status = [0] * 6
        self._usb_state = -1

        self.connection = None
        self.max_attempts = 5
        self.refuse_counts = 0
        self.connection_errors = 0
        self.count = 0
        self.aborted_retries = False
        self.pre_ok = False
        self.realtime = False

        self.abort_waiting = False

        name = self.context.label
        self.pipe_channel = context.channel("%s/events" % name)
        self.usb_log = context.channel("%s/usb" % name, buffer_size=500)
        self.usb_send_channel = context.channel("%s/usb_send" % name)
        self.recv_channel = context.channel("%s/recv" % name)
        self.usb_log.watch(lambda e: context.signal("pipe;usb_status", e))
        self.ch341 = context.open("module/ch341", log=self.usb_log)
        self.reset()

    def viewbuffer(self):
        buffer = bytes(self._realtime_buffer) + bytes(self._buffer) + bytes(self._queue)
        try:
            buffer_str = buffer.decode()
        except ValueError:
            try:
                buffer_str = buffer.decode("utf8")
            except UnicodeDecodeError:
                buffer_str = str(buffer)
        except AttributeError:
            buffer_str = buffer
        return buffer_str

    def added(self):
        self.start()

    def service_detach(self):
        pass

    def shutdown(self, *args, **kwargs):
        if self._thread is not None:
            self.write(b"\x18\n")

    def __repr__(self):
        return "LhystudiosController(%s)" % str(self.context)

    def __len__(self):
        """Provides the length of the buffer of this device."""
        return len(self._buffer) + len(self._queue) + len(self._preempt)

    def open(self):
        self.pipe_channel("open()")
        if self.connection is None:
            self.connection = self.ch341.connect(
                driver_index=self.context.usb_index,
                chipv=self.context.usb_version,
                bus=self.context.usb_bus,
                address=self.context.usb_address,
                mock=self.context.mock,
            )
        else:
            try:
                self.connection.open()
            except AttributeError:
                raise ConnectionRefusedError("Mock Driver cannot connect with USB")

        if self.connection is None:
            raise ConnectionRefusedError("ch341 connect did not return a connection.")

    def close(self):
        self.pipe_channel("close()")
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def write(self, bytes_to_write):
        """
        Writes data to the queue, this will be moved into the buffer by the thread in a threadsafe manner.

        :param bytes_to_write: data to write to the queue.
        :return:
        """
        f = bytes_to_write.find(b"~")
        if f != -1:
            # ~ was found in bytes. We are in a realtime exception.
            self.realtime = True

            # All code prior to ~ is sent to normal write.
            queue_bytes = bytes_to_write[:f]
            if queue_bytes:
                self.write(queue_bytes)

            # All code after ~ is sent to realtime write.
            preempt_bytes = bytes_to_write[f + 1 :]
            if preempt_bytes:
                self.realtime_write(preempt_bytes)
            return self
        if self.realtime:
            # We are in a realtime exception that has not been terminated.
            self.realtime_write(bytes_to_write)
            return self

        self.pipe_channel("write(%s)" % str(bytes_to_write))
        self._queue_lock.acquire(True)
        self._queue += bytes_to_write
        self._queue_lock.release()
        self.start()
        self.update_buffer()
        return self

    def realtime_write(self, bytes_to_write):
        """
        Writes data to the preempting commands, this will be moved to the front of the buffer by the thread
        in a threadsafe manner.

        :param bytes_to_write: data to write to the front of the queue.
        :return:
        """
        f = bytes_to_write.find(b"~")
        if f != -1:
            # ~ was found in bytes. We are leaving realtime exception.
            self.realtime = False

            # All date prior to the ~ is sent to realtime write.
            preempt_bytes = bytes_to_write[:f]
            if preempt_bytes:
                self.realtime_write(preempt_bytes)

            # All data after ~ is sent back to normal write.
            queue_bytes = bytes_to_write[f + 1 :]
            if queue_bytes:
                self.write(queue_bytes)
            return self
        self.pipe_channel("realtime_write(%s)" % str(bytes_to_write))
        self._preempt_lock.acquire(True)
        self._preempt = bytearray(bytes_to_write) + self._preempt
        self._preempt_lock.release()
        self.start()
        self.update_buffer()
        return self

    def start(self):
        """
        Controller state change to Started.
        :return:
        """
        if self._thread is None or not self._thread.is_alive():
            self._thread = self.context.threaded(
                self._thread_data_send,
                thread_name="LhyPipe(%s)" % self.context.path,
                result=self.stop,
            )
            self._thread.stop = self.stop
            self.update_state(STATE_INITIALIZE)

    def _pause_busy(self):
        """
        BUSY can be called in a paused state to packet halt the controller.

        This can only be done from PAUSE..
        """
        if self.state != STATE_PAUSE:
            self.pause()
        if self.state == STATE_PAUSE:
            self.update_state(STATE_BUSY)

    def _resume_busy(self):
        """
        Resumes from a BUSY to restore the controller. This will return to a paused state.

        This can only be done from BUSY.
        """
        if self.state == STATE_BUSY:
            self.update_state(STATE_PAUSE)
            self.resume()

    def pause(self):
        """
        Pause simply holds the controller from sending any additional packets.

        If this state change is done from INITIALIZE it will start the processing.
        Otherwise it must be done from ACTIVE or IDLE.
        """
        if self.state == STATE_INITIALIZE:
            self.start()
            self.update_state(STATE_PAUSE)
        if self.state == STATE_ACTIVE or self.state == STATE_IDLE:
            self.update_state(STATE_PAUSE)

    def resume(self):
        """
        Resume can only be called from PAUSE.
        """
        if self.state == STATE_PAUSE:
            self.update_state(STATE_ACTIVE)

    def abort(self):
        self._buffer = bytearray()
        self._queue = bytearray()
        self.context.signal("pipe;buffer", 0)
        self.update_state(STATE_TERMINATE)

    def reset(self):
        self.update_state(STATE_INITIALIZE)

    def stop(self, *args):
        self.abort()
        try:
            if self._thread is not None:
                self._thread.join()  # Wait until stop completes before continuing.
            self._thread = None
        except RuntimeError:
            pass  # Stop called by current thread.

    def abort_retry(self):
        self.aborted_retries = True
        self.context.signal("pipe;state", "STATE_FAILED_SUSPENDED")

    def continue_retry(self):
        self.aborted_retries = False
        self.context.signal("pipe;state", "STATE_FAILED_RETRYING")

    def usb_release(self):
        if self.connection:
            self.connection.release()
        else:
            raise ConnectionError

    def usb_reset(self):
        if self.connection:
            self.connection.reset()
        else:
            raise ConnectionError

    def update_state(self, state):
        if state == self.state:
            return
        self.state = state
        if self.context is not None:
            self.context.signal("pipe;thread", self.state)

    def update_buffer(self):
        if self.context is not None:
            self.context._buffer_size = (
                len(self._realtime_buffer) + len(self._buffer) + len(self._queue)
            )
            self.context.signal("pipe;buffer", len(self))

    def update_packet(self, packet):
        self.context.signal("pipe;packet", convert_to_list_bytes(packet))
        self.context.signal("pipe;packet_text", packet)
        if self.usb_send_channel:
            self.usb_send_channel(packet)

    def _thread_data_send(self):
        """
        Main threaded function to send data. While the controller is working the thread
        will be doing work in this function.
        """
        self._main_lock.acquire(True)
        self.count = 0
        self.pre_ok = False
        self.is_shutdown = False
        while self.state != STATE_END and self.state != STATE_TERMINATE:
            if self.state == STATE_INITIALIZE:
                # If we are initialized. Change that to active since we're running.
                self.update_state(STATE_ACTIVE)
            if self.state in (STATE_PAUSE, STATE_BUSY, STATE_SUSPEND):
                # If we are paused just keep sleeping until the state changes.
                if len(self._realtime_buffer) == 0 and len(self._preempt) == 0:
                    # Only pause if there are no realtime commands to queue.
                    self.context.signal("pipe;running", False)
                    time.sleep(0.25)
                    continue
            if self.aborted_retries:
                self.context.signal("pipe;running", False)
                time.sleep(0.25)
                continue
            try:
                # We try to process the queue.
                queue_processed = self.process_queue()
                if self.refuse_counts:
                    self.context.signal("pipe;failing", 0)
                self.refuse_counts = 0
                if self.is_shutdown:
                    break  # Sometimes it could reset this and escape.
            except ConnectionRefusedError:
                # The attempt refused the connection.
                self.refuse_counts += 1
                self.pre_ok = False
                if self.refuse_counts >= 5:
                    self.context.signal("pipe;state", "STATE_FAILED_RETRYING")
                self.context.signal("pipe;failing", self.refuse_counts)
                self.context.signal("pipe;running", False)
                time.sleep(3)  # 3 second sleep on failed connection attempt.
                continue
            except ConnectionError:
                # There was an error with the connection, close it and try again.
                self.connection_errors += 1
                self.pre_ok = False

                self.context.signal("pipe;running", False)
                time.sleep(0.5)
                self.close()
                continue
            if queue_processed:
                # Packet was sent.
                if self.state not in (
                    STATE_PAUSE,
                    STATE_BUSY,
                    STATE_ACTIVE,
                    STATE_TERMINATE,
                ):
                    self.update_state(STATE_ACTIVE)
                self.count = 0
            else:
                # No packet could be sent.
                if self.state not in (
                    STATE_PAUSE,
                    STATE_BUSY,
                    STATE_BUSY,
                    STATE_TERMINATE,
                ):
                    self.update_state(STATE_IDLE)
                if self.count > 50:
                    self.count = 50
                time.sleep(0.02 * self.count)
                # will tick up to 1 second waits if there's never a queue.
                self.count += 1
            self.context.signal("pipe;running", queue_processed)
        self._thread = None
        self.is_shutdown = False
        self.update_state(STATE_END)
        self.pre_ok = False
        self.context.signal("pipe;running", False)
        self._main_lock.release()

    def process_queue(self):
        """
        Attempts to process the buffer/queue
        Will fail on ConnectionRefusedError at open, 'process_queue_pause = True' (anytime before packet sent),
        self._buffer is empty, or a failure to produce packet.

        Buffer will not be changed unless packet is successfully sent, or pipe commands are processed.

        The following are meta commands for the controller
        - : require wait finish at the end of the queue processing.
        * : clear the buffers, and abort the thread.
        ! : pause.
        & : resume.
        % : fail checksum, do not resend
        ~ : begin/end realtime exception (Note, these characters would be consumed during
                the write process and should not exist in the queue)
        \x18 : quit.

        :return: queue process success.
        """
        if len(self._queue):  # check for and append queue
            self._queue_lock.acquire(True)
            self._buffer += self._queue
            self._queue = bytearray()
            self._queue_lock.release()
            self.update_buffer()

        if len(self._preempt):  # check for and prepend preempt
            self._preempt_lock.acquire(True)
            self._realtime_buffer += self._preempt
            self._preempt = bytearray()
            self._preempt_lock.release()
            self.update_buffer()

        if len(self._realtime_buffer) > 0:
            buffer = self._realtime_buffer
            realtime = True
        else:
            if len(self._buffer) > 0:
                buffer = self._buffer
                realtime = False
            else:
                # The buffer and realtime buffers are empty. No packet creation possible.
                return False

        # Find buffer of 30 or containing '\n'.
        find = buffer.find(b"\n", 0, 30)
        if find == -1:  # No end found.
            length = min(30, len(buffer))
        else:  # Line end found.
            length = min(30, len(buffer), find + 1)
        packet = bytes(buffer[:length])

        # edge condition of catching only pipe command without '\n'
        if packet.endswith((b"-", b"*", b"&", b"!", b"#", b"%", b"\x18")):
            packet += buffer[length : length + 1]
            length += 1
        post_send_command = None
        default_checksum = True

        # find pipe commands.
        if packet.endswith(b"\n"):
            packet = packet[:-1]
            if packet.endswith(b"-"):  # wait finish
                packet = packet[:-1]
                post_send_command = self.wait_finished
            elif packet.endswith(b"*"):  # abort
                post_send_command = self.abort
                packet = packet[:-1]
            elif packet.endswith(b"&"):  # resume
                self._resume_busy()
                packet = packet[:-1]
            elif packet.endswith(b"!"):  # pause
                self._pause_busy()
                packet = packet[:-1]
            elif packet.endswith(b"%"):  # alt-checksum
                default_checksum = False
                packet = packet[:-1]
            elif packet.endswith(b"\x18"):
                self.state = STATE_TERMINATE
                self.is_shutdown = True
                packet = packet[:-1]
            if len(packet) != 0:
                if packet.endswith(b"#"):
                    packet = packet[:-1]
                    try:
                        c = packet[-1]
                    except IndexError:
                        c = b"F"  # Packet was simply #. We can do nothing.
                    packet += bytes([c]) * (30 - len(packet))  # Padding. '\n'
                else:
                    packet += b"F" * (30 - len(packet))  # Padding. '\n'
        if not realtime and self.state in (STATE_PAUSE, STATE_BUSY):
            return False  # Processing normal queue, PAUSE and BUSY apply.

        # Packet is prepared and ready to send. Open Channel.
        self.open()

        if len(packet) == 30:
            # We have a sendable packet.
            if not self.pre_ok:
                self.wait_until_accepting_packets()
            if default_checksum:
                packet = b"\x00" + packet + bytes([onewire_crc_lookup(packet)])
            else:
                packet = b"\x00" + packet + bytes([onewire_crc_lookup(packet) ^ 0xFF])
            self.connection.write(packet)
            self.pre_ok = False

            # Packet is sent, trying to confirm.
            status = 0
            flawless = True
            for attempts in range(300):
                # We'll try to confirm this at 300 times.
                try:
                    self.update_status()
                    status = self._status[1]
                except ConnectionError:
                    # Errors are ignored, must confirm packet.
                    flawless = False
                    continue
                if status == 0:
                    # We did not read a status.
                    continue
                elif status == STATUS_OK:
                    # Packet was fine.
                    self.pre_ok = True
                    break
                elif status == STATUS_BUSY:
                    # Busy. We still do not have our confirmation. BUSY comes before ERROR or OK.
                    continue
                elif status == STATUS_ERROR:
                    if not default_checksum:
                        break
                    self.context.rejected_count += 1
                    if flawless:  # Packet was rejected. The CRC failed.
                        return False
                    else:
                        # The channel had the error, assuming packet was actually good.
                        break
                elif status == STATUS_FINISH:
                    # We finished. If we were going to wait for that, we no longer need to.
                    if post_send_command == self.wait_finished:
                        post_send_command = None
                    continue  # This is not a confirmation.
            if status == 0:  # After 300 attempts we could only get status = 0.
                raise ConnectionError  # Broken pipe. 300 attempts. Could not confirm packet.
            self.context.packet_count += (
                1  # Our packet is confirmed or assumed confirmed.
            )
        else:
            if len(packet) != 0:
                # We could only generate a partial packet, throw it back
                return False
            # We have an empty packet of only commands. Continue work.

        # Packet was processed. Remove that data.
        if realtime:
            del self._realtime_buffer[:length]
        else:
            del self._buffer[:length]
        if len(packet) != 0:
            # Packet was completed and sent. Only then update the channel.
            self.update_packet(packet)
        self.update_buffer()

        if post_send_command is not None:
            # Post send command could be wait_finished, and might have a broken pipe.
            try:
                post_send_command()
            except ConnectionError:
                # We should have already sent the packet. So this should be fine.
                pass
        return True  # A packet was prepped and sent correctly.

    def update_status(self):
        try:
            self._status = self.connection.get_status()
        except AttributeError:
            # self.connection was closed by something.
            raise ConnectionError
        if self.context is not None:
            try:
                self.context.signal(
                    "pipe;status",
                    self._status,
                    get_code_string_from_code(self._status[1]),
                )
            except IndexError:
                pass
            if self.recv_channel:
                self.recv_channel(str(self._status))

    def wait_until_accepting_packets(self):
        i = 0
        while self.state != STATE_TERMINATE:
            self.update_status()
            status = self._status[1]
            if status == 0:
                raise ConnectionError
            if status == STATUS_OK:
                self.pre_ok = False
                break
            if status == STATUS_ERROR:
                break
            time.sleep(0.05)
            if self.context is not None:
                self.context.signal("pipe;wait", STATUS_OK, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.

    def wait_finished(self):
        i = 0
        original_state = self.state
        if self.state != STATE_PAUSE:
            self.pause()

        while True:
            if self.state != STATE_WAIT:
                self.update_state(STATE_WAIT)
            self.update_status()
            status = self._status[1]
            if status == 0:
                raise ConnectionError
            if status == STATUS_ERROR:
                self.context.rejected_count += 1
            if status & 0x02 == 0:
                # StateBitPEMP = 0x00000200, Finished = 0xEC, 11101100
                break
            if self.context is not None:
                self.context.signal("pipe;wait", status, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.
        self.update_state(original_state)

    @property
    def type(self):
        return "lhystudios"


class TCPOutput:
    def __init__(self, context, name=None):
        super().__init__()
        self.service = context
        self._stream = None
        self.name = name

        self.lock = threading.RLock()
        self.buffer = bytearray()
        self.thread = None

    def connect(self):
        try:
            self._stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._stream.connect((self.service.address, self.service.port))
            self.service.signal("tcp;status", "connected")
        except (ConnectionError, TimeoutError):
            self.disconnect()

    def disconnect(self):
        self.service.signal("tcp;status", "disconnected")
        self._stream.close()
        self._stream = None

    def write(self, data):
        self.service.signal("tcp;write", data)
        with self.lock:
            self.buffer += data
            self.service.signal("tcp;buffer", len(self.buffer))
        self._start()

    realtime_write = write

    def _start(self):
        if self.thread is None:
            self.thread = self.service.threaded(
                self._sending,
                thread_name="sender-%d" % self.service.port,
                result=self._stop,
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
                        self.service.signal("tcp;buffer", len(self.buffer))
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
            return "TCPOutput('%s:%s','%s')" % (
                self.service.address,
                self.service.port,
                self.name,
            )
        return "TCPOutput('%s:%s')" % (self.service.address, self.service.port)

    def __len__(self):
        return len(self.buffer)


class LhystudiosEmulator(Module):
    def __init__(self, device, path):
        Module.__init__(self, device, path)
        self.parser = LhystudiosParser()
        device.setting(bool, "fix_speeds", False)
        self.parser.fix_speeds = device.fix_speeds
        self.parser.channel = self.context.channel("lhy")

        def pos(p):
            if p is None:
                return
            x0, y0, x1, y1 = p
            self.context.signal("emulator;position", (x0, y0, x1, y1))

        self.parser.position = pos

    def __repr__(self):
        return "LhystudiosEmulator(%s)" % self.name

    def module_open(self, *args, **kwargs):
        context = self.context
        send = context.channel("%s/usb_send" % self.context.path)
        send.watch(self.parser.write_packet)

    def module_close(self, *args, **kwargs):
        context = self.context
        send = context.channel("%s/usb_send" % self.context.path)
        send.unwatch(self.parser.write_packet)


class LhystudiosParser:
    """
    LhystudiosParser parses LHYMicro-GL code with a state diagram. This should accurately reconstruct the values.
    When the position is changed it calls a self.position() function if one exists.
    """

    def __init__(self):
        self.channel = None
        self.position = None
        self.board = "M2"
        self.header_skipped = False
        self.count_lines = 0
        self.count_flag = 0
        self.settings = LaserSettings(speed=20.0, power=1000.0)

        self.small_jump = True
        self.speed_code = None

        self.x = 0.0
        self.y = 0.0
        self.number_value = None
        self.distance_x = 0
        self.distance_y = 0

        self.filename = ""

        self.laser = 0
        self.left = False
        self.top = False
        self.x_on = False
        self.y_on = False
        self.horizontal_major = False
        self.fix_speeds = False
        self.process = self.state_default

    @property
    def program_mode(self):
        return self.process == self.state_compact

    @property
    def default_mode(self):
        return self.process is self.state_default

    @property
    def raster_mode(self):
        return self.settings.raster_step != 0

    def new_file(self):
        self.header_skipped = False
        self.count_flag = 0
        self.count_lines = 0

    @staticmethod
    def remove_header(data):
        count_lines = 0
        count_flag = 0
        for i in range(len(data)):
            b = data[i]
            c = chr(b)
            if c == "\n":
                count_lines += 1
            elif c == "%":
                count_flag += 1
            if count_lines >= 3 and count_flag >= 5:
                return data[i:]

    def header_write(self, data):
        """
        Write data to the emulator including the header. This is intended for saved .egv files which include a default
        header.
        """
        if self.header_skipped:
            self.write(data)
        else:
            data = LhystudiosParser.remove_header(data)
            self.write(data)

    def append_distance(self, amount):
        if self.x_on:
            self.distance_x += amount
        if self.y_on:
            self.distance_y += amount

    def write_packet(self, packet):
        self.write(packet[1:31])

    def write(self, data):
        for b in data:
            c = chr(b)
            if c == "I":
                self.process = self.state_default
                continue
            self.process(b, c)

    def state_finish(self, b, c):
        if c in "NSEF":
            return
        if self.channel:
            self.channel("Finish State Unknown: %s" % c)

    def state_reset(self, b, c):
        if c in "@NSE":
            return
        else:
            self.process = self.state_default
            self.process(b, c)

    def state_jog(self, b, c):
        if c in "N":
            return
        else:
            self.process = self.state_default
            self.process(b, c)

    def state_pop(self, b, c):
        if c == "P":
            # Home sequence triggered.
            if self.position:
                self.position((self.x, self.y, 0, 0))
            self.x = 0
            self.y = 0
            self.laser = 0
            self.process = self.state_default
            return
        elif c == "F":
            return
        else:
            if self.channel:
                self.channel("Finish State Unknown: %s" % c)

    def state_speed(self, b, c):
        if c in "GCV01234567890":
            self.speed_code += c
            return
        speed = LaserSpeed(
            self.speed_code, board=self.board, fix_speeds=self.fix_speeds
        )
        self.settings.steps = speed.raster_step
        self.settings.speed = speed.speed
        if self.channel:
            self.channel("Setting Speed: %f" % self.settings.speed)
        self.speed_code = None

        self.process = self.state_default
        self.process(b, c)

    def state_switch(self, b, c):
        if c in "S012":
            if c == "1":
                self.horizontal_major = self.x_on
                if self.channel:
                    self.channel("Setting Axis.")
            return
        self.process = self.state_default
        self.process(b, c)

    def state_pause(self, b, c):
        if c in "NF":
            return
        if c == "P":
            self.process = self.state_resume
        else:
            self.process = self.state_compact
            self.process(b, c)

    def state_resume(self, b, c):
        if c in "NF":
            return
        self.process = self.state_compact
        self.process(b, c)

    def state_pad(self, b, c):
        if c == "F":
            return

    def state_execute(self, b, c):
        self.process = self.state_compact

    def state_distance(self, b, c):
        if c == "|":
            self.append_distance(25)
            self.small_jump = True
            return True
        elif ord("0") <= b <= ord("9"):
            if self.number_value is None:
                self.number_value = c
            else:
                self.number_value += c
            if len(self.number_value) >= 3:
                self.append_distance(int(self.number_value))
                self.number_value = None
            return True
        elif ord("a") <= b <= ord("y"):
            self.append_distance(b + 1 - ord("a"))
        elif c == "z":
            self.append_distance(26 if self.small_jump else 255)
        else:
            self.small_jump = False
            return False
        self.small_jump = False
        return True

    def execute_distance(self):
        if self.distance_x != 0 or self.distance_y != 0:
            dx = self.distance_x
            dy = self.distance_y
            if self.left:
                dx = -dx
            if self.top:
                dy = -dy
            self.distance_x = 0
            self.distance_y = 0

            ox = self.x
            oy = self.y

            self.x += dx
            self.y += dy

            if self.position:
                self.position((ox, oy, self.x, self.y))

            if self.channel:
                self.channel("Moving (%d %d) now at %d %d" % (dx, dy, self.x, self.y))

    def state_compact(self, b, c):
        if self.state_distance(b, c):
            return
        self.execute_distance()

        if c == "F":
            self.laser = 0
            if self.channel:
                self.channel("Finish")
            self.process = self.state_finish
            self.process(b, c)
            return
        elif c == "@":
            self.laser = 0
            if self.channel:
                self.channel("Reset")
            self.process = self.state_reset
            self.process(b, c)
            return
        elif c == "P":
            self.laser = 0
            if self.channel:
                self.channel("Pause")
            self.process = self.state_pause
        elif c == "N":
            if self.channel:
                self.channel("Jog")
            self.process = self.state_jog
            if self.position:
                self.position(None)
            self.process(b, c)
        elif c == "S":
            self.laser = 0
            if self.channel:
                self.channel("Switch")
            self.process = self.state_switch
            self.process(b, c)
        elif c == "E":
            self.laser = 0
            if self.channel:
                self.channel("Compact-Compact")
            self.process = self.state_execute
            if self.position:
                self.position(None)
            self.process(b, c)
        elif c == "B":
            self.left = False
            self.x_on = True
            self.y_on = False
            if self.channel:
                self.channel("Right")
        elif c == "T":
            self.left = True
            self.x_on = True
            self.y_on = False
            if self.channel:
                self.channel("Left")
        elif c == "R":
            self.top = False
            self.x_on = False
            self.y_on = True
            if self.channel:
                self.channel("Bottom")
        elif c == "L":
            self.top = True
            self.x_on = False
            self.y_on = True
            if self.channel:
                self.channel("Top")
        elif c == "M":
            self.x_on = True
            self.y_on = True
            if self.channel:
                a = "Top" if self.top else "Bottom"
                b = "Left" if self.left else "Right"
                self.channel("Diagonal %s %s" % (a, b))
        elif c == "U":
            self.laser = 0
        elif c == "D":
            self.laser = 1

    def state_default(self, b, c):
        if self.state_distance(b, c):
            return

        # Execute Commands.
        if c == "N":
            self.execute_distance()
        elif c == "F":
            if self.channel:
                self.channel("Finish")
            self.process = self.state_finish
            self.process(b, c)
            return
        elif c == "P":
            if self.channel:
                self.channel("Popping")
            self.process = self.state_pop
            return
        elif c in "CVG":
            if self.channel:
                self.channel("Speedcode")
            self.speed_code = ""
            self.process = self.state_speed
            self.process(b, c)
            return
        elif c == "S":
            self.execute_distance()
            if self.channel:
                self.channel("Switch")
            self.process = self.state_switch
            self.process(b, c)
        elif c == "E":
            if self.channel:
                self.channel("Compact")
            self.process = self.state_execute
            self.process(b, c)
        elif c == "B":
            self.left = False
            self.x_on = True
            self.y_on = False
            if self.channel:
                self.channel("Right")
        elif c == "T":
            self.left = True
            self.x_on = True
            self.y_on = False
            if self.channel:
                self.channel("Left")
        elif c == "R":
            self.top = False
            self.x_on = False
            self.y_on = True
            if self.channel:
                self.channel("Bottom")
        elif c == "L":
            self.top = True
            self.x_on = False
            self.y_on = True
            if self.channel:
                self.channel("Top")


class EGVBlob:
    def __init__(self, data: bytearray, name=None):
        self.name = name
        self.data = data
        self.operation = "blob"
        self._cutcode = None
        self._cut = None

    def __repr__(self):
        return "EGV(%s, %d bytes)" % (self.name, len(self.data))

    def as_cutobjects(self):
        parser = LhystudiosParser()
        self._cutcode = CutCode()
        self._cut = RawCut()

        def new_cut():
            if self._cut is not None and len(self._cut):
                self._cutcode.append(self._cut)
            self._cut = RawCut()
            self._cut.settings = LaserSettings(parser.settings)

        def position(p):
            if p is None or self._cut is None:
                new_cut()
                return

            from_x, from_y, to_x, to_y = p

            if parser.program_mode:
                if len(self._cut.plot) == 0:
                    self._cut.plot_append(int(from_x), int(from_y), parser.laser)
                self._cut.plot_append(int(to_x), int(to_y), parser.laser)
            else:
                new_cut()

        parser.position = position
        parser.header_write(self.data)

        cutcode = self._cutcode
        self._cut = None
        self._cutcode = None
        return cutcode

    def generate(self):
        yield COMMAND_BLOB, "egv", LhystudiosParser.remove_header(self.data)


class EgvLoader:
    @staticmethod
    def load_types():
        yield "Engrave Files", ("egv",), "application/x-egv"

    @staticmethod
    def load(kernel, elements_modifier, pathname, **kwargs):
        import os

        basename = os.path.basename(pathname)
        with open(pathname, "rb") as f:
            blob = EGVBlob(bytearray(f.read()), basename)
            op_branch = elements_modifier.get(type="branch ops")
            op_branch.add(blob, type="blob")
            kernel.root.close(basename)
        return True


def get_code_string_from_code(code):
    if code == STATUS_OK:
        return "OK"
    elif code == STATUS_BUSY:
        return "Busy"
    elif code == STATUS_ERROR:
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


distance_lookup = [
    b"",
    b"a",
    b"b",
    b"c",
    b"d",
    b"e",
    b"f",
    b"g",
    b"h",
    b"i",
    b"j",
    b"k",
    b"l",
    b"m",
    b"n",
    b"o",
    b"p",
    b"q",
    b"r",
    b"s",
    b"t",
    b"u",
    b"v",
    b"w",
    b"x",
    b"y",
    b"|a",
    b"|b",
    b"|c",
    b"|d",
    b"|e",
    b"|f",
    b"|g",
    b"|h",
    b"|i",
    b"|j",
    b"|k",
    b"|l",
    b"|m",
    b"|n",
    b"|o",
    b"|p",
    b"|q",
    b"|r",
    b"|s",
    b"|t",
    b"|u",
    b"|v",
    b"|w",
    b"|x",
    b"|y",
    b"|z",
]


def lhymicro_distance(v):
    dist = b""
    if v >= 255:
        zs = int(v / 255)
        v %= 255
        dist += b"z" * zs
    if v >= 52:
        return dist + b"%03d" % v
    return dist + distance_lookup[v]


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


crc_table = [
    0x00,
    0x5E,
    0xBC,
    0xE2,
    0x61,
    0x3F,
    0xDD,
    0x83,
    0xC2,
    0x9C,
    0x7E,
    0x20,
    0xA3,
    0xFD,
    0x1F,
    0x41,
    0x00,
    0x9D,
    0x23,
    0xBE,
    0x46,
    0xDB,
    0x65,
    0xF8,
    0x8C,
    0x11,
    0xAF,
    0x32,
    0xCA,
    0x57,
    0xE9,
    0x74,
]


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
        crc = crc_table[crc & 0x0F] ^ crc_table[16 + ((crc >> 4) & 0x0F)]
    return crc
