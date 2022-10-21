import math
import socket
import threading
import time
from hashlib import md5

from meerk40t.core.spoolers import LaserJob, Spooler
from meerk40t.kernel import (
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
    CommandSyntaxError,
    Service,
)
from meerk40t.tools.zinglplotter import ZinglPlotter

from ..core.cutcode import (
    DwellCut,
    GotoCut,
    HomeCut,
    InputCut,
    OutputCut,
    SetOriginCut,
    WaitCut,
)
from ..core.parameters import Parameters
from ..core.plotplanner import PlotPlanner, grouped
from ..core.units import UNITS_PER_MIL, Length, ViewPort
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
    PLOT_RAPID,
    PLOT_SETTING,
)
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
    if lifecycle == "plugins":
        from .gui import gui as lhygui

        return [lhygui.plugin]

    if lifecycle == "register":
        kernel.register("provider/device/lhystudios", LihuiyuDevice)
        try:
            from meerk40t.lihuiyu.lihuiyuparser import EgvLoader
            kernel.register("load/EgvLoader", EgvLoader)
        except ImportError:
            pass
        try:
            from .lihuiyuemulator import LihuiyuEmulator
            kernel.register("emulator/lihuiyu", LihuiyuEmulator)
        except ImportError:
            pass
        try:
            from meerk40t.lihuiyu.lihuiyuparser import LihuiyuParser
            kernel.register("parser/egv", LihuiyuParser)
        except ImportError:
            pass
    if lifecycle == "preboot":
        suffix = "lhystudios"
        for d in kernel.derivable(suffix):
            kernel.root(f"service device start -p {d} {suffix}\n")


class LihuiyuDevice(Service, ViewPort):
    """
    LihuiyuDevice is driver for the M2 Nano and other classes of Lihuiyu boards.
    """

    def __init__(self, kernel, path, *args, **kwargs):
        Service.__init__(self, kernel, path)
        self.name = "LihuiyuDevice"
        _ = kernel.translation
        self.extension = "egv"

        choices = [
            {
                "attr": "bedwidth",
                "object": self,
                "default": "310mm",
                "type": str,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": "210mm",
                "type": str,
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
                    "Scale factor for the X-axis. Board units to actual physical units."
                ),
            },
            {
                "attr": "scale_y",
                "object": self,
                "default": 1.000,
                "type": float,
                "label": _("Y Scale Factor"),
                "tip": _(
                    "Scale factor for the Y-axis. Board units to actual physical units."
                ),
            },
        ]

        self.register_choices("bed_dim", choices)
        self.setting(bool, "swap_xy", False)
        self.setting(bool, "flip_x", False)
        self.setting(bool, "flip_y", False)
        self.setting(bool, "home_right", False)
        self.setting(bool, "home_bottom", False)
        # Tuple contains 4 value pairs: Speed Low, Speed High, Power Low, Power High, each with enabled, value
        self.setting(
            list, "dangerlevel_op_cut", (False, 0, False, 0, False, 0, False, 0)
        )
        self.setting(
            list, "dangerlevel_op_engrave", (False, 0, False, 0, False, 0, False, 0)
        )
        self.setting(
            list, "dangerlevel_op_hatch", (False, 0, False, 0, False, 0, False, 0)
        )
        self.setting(
            list, "dangerlevel_op_raster", (False, 0, False, 0, False, 0, False, 0)
        )
        self.setting(
            list, "dangerlevel_op_image", (False, 0, False, 0, False, 0, False, 0)
        )
        self.setting(
            list, "dangerlevel_op_dots", (False, 0, False, 0, False, 0, False, 0)
        )
        ViewPort.__init__(
            self,
            self.bedwidth,
            self.bedheight,
            user_scale_x=self.scale_x,
            user_scale_y=self.scale_y,
            native_scale_x=UNITS_PER_MIL,
            native_scale_y=UNITS_PER_MIL,
            flip_x=self.flip_x,
            flip_y=self.flip_y,
            swap_xy=self.swap_xy,
            origin_x=1.0 if self.home_right else 0.0,
            origin_y=1.0 if self.home_bottom else 0.0,
        )
        self.setting(bool, "opt_rapid_between", True)
        self.setting(int, "opt_jog_mode", 0)
        self.setting(int, "opt_jog_minimum", 256)
        self.setting(bool, "rapid_override", False)
        self.setting(float, "rapid_override_speed_x", 50.0)
        self.setting(float, "rapid_override_speed_y", 50.0)
        self.setting(bool, "plot_shift", False)

        self.setting(bool, "strict", False)
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

        self.setting(bool, "twitches", False)
        self.setting(bool, "nse_raster", False)
        self.setting(bool, "nse_stepraster", False)

        self.setting(bool, "scale_speed_enabled", False)
        self.setting(float, "scale_speed", 1.000)
        self.setting(bool, "max_speed_vector_enabled", False)
        self.setting(float, "max_speed_vector", 100.0)
        self.setting(bool, "max_speed_raster_enabled", False)
        self.setting(float, "max_speed_raster", 750.0)

        self.driver = LihuiyuDriver(self)
        self.spooler = Spooler(self, driver=self.driver)
        self.add_service_delegate(self.spooler)

        self.tcp = TCPOutput(self)
        self.add_service_delegate(self.tcp)

        self.controller = LihuiyuController(self)
        self.add_service_delegate(self.controller)

        self.driver.out_pipe = self.controller if not self.networked else self.tcp

        _ = self.kernel.translation

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
            if time > 1000.0:
                channel(
                    _(
                        '"{time}ms" exceeds 1 second limit to fire a standing laser.'
                    ).format(time=time)
                )
                try:
                    if not idonotlovemyhouse:
                        return
                except IndexError:
                    return

            def timed_fire():
                yield "wait_finish"
                yield "laser_on"
                yield "wait", time
                yield "laser_off"

            if self.spooler.is_idle:
                label = _("Pulse laser for {time}ms").format(time=time)
                self.spooler.laserjob(list(timed_fire()), label=label, helper=True)
                channel(label)
            else:
                channel(_("Pulse laser failed: Busy"))
            return

        @self.console_argument("speed", type=float, help=_("Set the movement speed"))
        @self.console_argument("dx", type=Length, help=_("change in x"))
        @self.console_argument("dy", type=Length, help=_("change in y"))
        @self.console_command(
            "move_at_speed",
            help=_("move_at_speed <speed> <dx> <dy>"),
            all_arguments_required=True,
        )
        def move_speed(channel, _, speed, dx, dy, **kwgs):
            def move_at_speed():
                yield "set", "speed", speed
                yield "program_mode"
                yield "move_rel", dx.length_mil, dy.length_mil
                yield "rapid_mode"

            if self.spooler.is_idle:
                self.spooler.laserjob(
                    list(move_at_speed()), label=f"move {dx} {dy} at {speed}", helper=True
                )
            else:
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
        @self.console_command(
            "speed", input_type="lihuiyu", help=_("Set current speed of driver.")
        )
        def speed(
            command, channel, _, data=None, speed=None, difference=False, **kwargs
        ):
            spooler, driver, output = data
            if speed is None:
                current_speed = driver.speed
                if current_speed is None:
                    channel(_("Speed is unset."))
                else:
                    channel(
                        _("Speed set at: {speed} mm/s").format(
                            speed=driver.settings.speed
                        )
                    )
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
                s = driver.speed + driver.speed * (s / 100.0)
            elif difference:
                s += driver.speed
            elif percent:
                s = driver.speed * (s / 100.0)
            driver.set("speed", s)
            channel(_("Speed set at: {speed} mm/s").format(speed=driver.speed))

        @self.console_argument("ppi", type=int, help=_("pulses per inch [0-1000]"))
        @self.console_command("power", help=_("Set Driver Power"))
        def power(command, channel, _, ppi=None, **kwargs):
            original_power = self.driver.power
            if ppi is None:
                if original_power is None:
                    channel(_("Power is not set."))
                else:
                    channel(
                        _("Power set at: {power} pulses per inch").format(
                            power=original_power
                        )
                    )
            else:
                self.driver.set("power", ppi)

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
                if self.driver.acceleration is None:
                    channel(_("Acceleration is set to default."))
                else:
                    channel(
                        _("Acceleration: {acceleration}").format(
                            acceleration=self.driver.acceleration
                        )
                    )

            else:
                try:
                    v = accel
                    if v not in (1, 2, 3, 4):
                        self.driver.set("acceleration", None)
                        channel(_("Acceleration is set to default."))
                        return
                    self.driver.set("acceleration", v)
                    channel(
                        _("Acceleration: {acceleration}").format(
                            acceleration=self.driver.acceleration
                        )
                    )
                except ValueError:
                    channel(_("Invalid Acceleration [1-4]."))
                    return

        @self.console_command(
            "viewport_update",
            hidden=True,
            help=_("Update m2nano codes for movement"),
        )
        def codes_update(**kwargs):
            self.realize()

        @self.console_command(
            "network_update",
            hidden=True,
            help=_("Updates network state for m2nano networked."),
        )
        def network_update(**kwargs):
            self.driver.out_pipe = self.controller if not self.networked else self.tcp

        @self.console_command(
            "status",
            help=_("abort waiting process on the controller."),
        )
        def realtime_status(channel, _, **kwargs):
            try:
                self.controller.update_status()
                channel(str(self.controller._status))
            except ConnectionError:
                channel(_("Could not check status, usb not connected."))

        @self.console_command(
            "continue",
            help=_("abort waiting process on the controller."),
        )
        def realtime_continue(**kwargs):
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
            channel(_("Lihuiyu Channel Aborted."))
            self.signal("pipe;running", False)

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
                self.rapid_override = True
                self.rapid_override_speed_x = rapid_x
                self.rapid_override_speed_y = rapid_y
                channel(
                    _("Rapid Limit: {max_x}, {max_y}").format(
                        max_x=self.rapid_override_speed_x,
                        max_y=self.rapid_override_speed_y,
                    )
                )
            else:
                self.rapid_override = False
                channel(_("Rapid Limit Off"))

        @self.console_argument("filename", type=str)
        @self.console_command("save_job", help=_("save job export"), input_type="plan")
        def egv_save(channel, _, filename, data=None, **kwargs):
            if filename is None:
                raise CommandSyntaxError
            try:
                with open(filename, "wb") as f:
                    f.write(b"Document type : LHYMICRO-GL file\n")
                    f.write(b"File version: 1.0.01\n")
                    f.write(b"Copyright: Unknown\n")
                    f.write(
                        bytes(
                            f"Creator-Software: {self.kernel.name} v{self.kernel.version}\n",
                            "utf-8",
                        )
                    )
                    f.write(b"\n")
                    f.write(b"%0%0%0%0%\n")
                    driver = LihuiyuDriver(self)
                    job = LaserJob(filename, list(data.plan), driver=driver)
                    driver.out_pipe = f
                    job.execute()

            except (PermissionError, IOError):
                channel(_("Could not save: {filename}").format(filename=filename))

        @self.console_argument("filename", type=str)
        @self.console_command(
            "egv_import",
            help=_("Lihuiyu Engrave Buffer Import. egv_import <egv_file>"),
        )
        def egv_import(channel, _, filename, **kwargs):
            if filename is None:
                raise CommandSyntaxError

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

            try:
                with open(filename, "r") as f:
                    skip_header(f)
                    while True:
                        data = f.read(1024)
                        if not data:
                            break
                        buffer = bytes(data, "utf8")
                        self.output.write(buffer)
                    self.output.write(b"\n")
            except (PermissionError, IOError, FileNotFoundError):
                channel(_("Could not load: {filename}").format(filename=filename))

        @self.console_argument("filename", type=str)
        @self.console_command(
            "egv_export",
            help=_("Lihuiyu Engrave Buffer Export. egv_export <egv_file>"),
        )
        def egv_export(channel, _, filename, **kwargs):
            if filename is None:
                raise CommandSyntaxError
            try:
                with open(filename, "w") as f:
                    f.write("Document type : LHYMICRO-GL file\n")
                    f.write("File version: 1.0.01\n")
                    f.write("Copyright: Unknown\n")
                    f.write(
                        f"Creator-Software: {self.kernel.name} v{self.kernel.version}\n"
                    )
                    f.write("\n")
                    f.write("%0%0%0%0%\n")
                    buffer = bytes(self.controller._buffer)
                    buffer += bytes(self.controller._queue)
                    f.write(buffer.decode("utf-8"))
            except (PermissionError, IOError):
                channel(_("Could not save: {filename}").format(filename=filename))

        @self.console_command(
            "egv",
            help=_("Lihuiyu Engrave Code Sender. egv <lhymicro-gl>"),
        )
        def egv(command, channel, _, remainder=None, **kwargs):
            if not remainder:
                channel("Lihuiyu Engrave Code Sender. egv <lhymicro-gl>")
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
                raise CommandSyntaxError
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
            channel(_("Lihuiyu Channel Started."))

        @self.console_command("hold", help=_("Hold Controller"))
        def pipe_pause(command, channel, _, **kwargs):
            self.controller.update_state(STATE_PAUSE)
            self.controller.pause()
            channel("Lihuiyu Channel Paused.")

        @self.console_command("resume", help=_("Resume Controller"))
        def pipe_resume(command, channel, _, **kwargs):
            self.controller.update_state(STATE_ACTIVE)
            self.controller.start()
            channel(_("Lihuiyu Channel Resumed."))

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
                server_name = f"lhyserver{self.path}"
                output = self.controller
                server = self.open_as("module/TCPServer", server_name, port=port)
                if quit:
                    self.close(server_name)
                    return
                channel(_("TCP Server for lihuiyu on port: {port}").format(port=port))
                if not silent:
                    console = kernel.channel("console")
                    server.events_channel.watch(console)
                    if watch:
                        server.data_channel.watch(console)
                channel(_("Watching Channel: {channel}").format(channel="server"))
                self.channel(f"{server_name}/recv").watch(output.write)
                channel(_("Attached: {output}").format(output=repr(output)))

            except OSError:
                channel(_("Server failed on port: {port}").format(port=port))
            except KeyError:
                channel(_("Server cannot be attached to any device."))
            return

        if self.has_feature("emulator/lihuiyu"):
            @self.console_command("lhyemulator", help=_("activate the lhyemulator."))
            def lhyemulator(channel, _, **kwargs):
                try:
                    self.open_as("emulator/lihuiyu", "lhyemulator")
                    channel(
                        _("Lihuiyu Emulator attached to {device}").format(device=str(self))
                    )
                except KeyError:
                    channel(_("Emulator cannot be attached to any device."))
                return

    @property
    def viewbuffer(self):
        return self.driver.out_pipe.viewbuffer

    @property
    def current(self):
        """
        @return: the location in scene units for the current known position.
        """
        return self.device_to_scene_position(self.driver.native_x, self.driver.native_y)

    @property
    def speed(self):
        return self.driver.speed

    @property
    def power(self):
        return self.driver.power

    @property
    def state(self):
        return self.driver.state

    @property
    def native(self):
        """
        @return: the location in device native units for the current known position.
        """
        return self.driver.native_x, self.driver.native_y

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


class LihuiyuDriver(Parameters):
    """
    LihuiyuDriver provides Lihuiyu specific coding for elements and sends it to the backend
    to write to the usb.
    """

    def __init__(self, service, *args, **kwargs):
        super().__init__()
        self.service = service
        self.name = str(self.service)
        self._topward = False
        self._leftward = False
        self._x_engaged = False
        self._y_engaged = False
        self._horizontal_major = False

        self._request_leftward = None
        self._request_topward = None
        self._request_horizontal_major = None

        self.out_pipe = None

        self.process_item = None
        self.spooled_item = None
        self.holds = []
        self.temp_holds = []

        self.native_x = 0
        self.native_y = 0
        self.origin_x = 0
        self.origin_y = 0

        self.plot_planner = PlotPlanner(self.settings)
        self.plot_planner.force_shift = service.plot_shift
        self.plot_data = None

        self.current_steps = 0
        self.total_steps = 0
        self.dummy_planner = PlotPlanner(self.settings)

        self.state = DRIVER_STATE_RAPID
        self.properties = 0
        self.is_relative = False
        self.laser = False
        self._thread = None
        self._shutdown = False
        self.last_fetch = None

        self.CODE_RIGHT = b"B"
        self.CODE_LEFT = b"T"
        self.CODE_TOP = b"L"
        self.CODE_BOTTOM = b"R"
        self.CODE_ANGLE = b"M"
        self.CODE_LASER_ON = b"D"
        self.CODE_LASER_OFF = b"U"

        self.is_paused = False
        self.service._buffer_size = 0

        def primary_hold():
            if self.out_pipe is None:
                return True
            if hasattr(self.out_pipe, "is_shutdown") and self.out_pipe.is_shutdown:
                raise ConnectionAbortedError("Cannot hold for a shutdown pipe.")
            try:
                buffer = len(self.out_pipe)
            except TypeError:
                buffer = 0
            return self.service.buffer_limit and buffer > self.service.buffer_max

        self.holds.append(primary_hold)

        # Step amount expected of the current operation
        self.step = 0

        # Step amount is the current correctly set step amount in the controller.
        self.step_value_set = 0

        # Step index of the current step taken for unidirectional
        self.step_index = 0

        # Step total the count for fractional step amounts
        self.step_total = 0.0

    def __repr__(self):
        return f"LihuiyuDriver({self.name})"

    def __call__(self, e):
        self.out_pipe.write(e)

    def hold_work(self, priority):
        """
        Holds are criteria to use to pause the data interpretation. These halt the production of new data until the
        criteria is met. A hold is constant and will always halt the data while true. A temp_hold will be removed
        as soon as it does not hold the data.

        @return: Whether data interpretation should hold.
        """
        if priority > 0:
            # Don't hold realtime work.
            return False

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

    def pause(self, *values):
        """
        Asks that the laser be paused.

        @param args:
        @return:
        """
        self(b"~PN!\n~")
        self.is_paused = True

    def resume(self, *values):
        """
        Asks that the laser be resumed.

        To work this command should usually be put into the realtime work queue for the laser, without that it will
        be paused and unable to process the resume.

        @param args:
        @return:
        """
        self(b"~PN&\n~")
        self.is_paused = False

    def reset(self):
        """
        This command asks that this device be emergency stopped and reset. Usually that queue data from the spooler be
        deleted.

        Asks that the device resets, and clears all current work.

        @param args:
        @return:
        """
        self.service.spooler.clear_queue()
        self.plot_planner.clear()
        self.spooled_item = None
        self.temp_holds.clear()

        self.service.signal("pipe;buffer", 0)
        self(b"~I*\n~")
        self._reset_modes()
        self.state = DRIVER_STATE_RAPID
        self.service.signal("driver;mode", self.state)
        self.is_paused = False

    def abort(self):
        self(b"I\n")

    def blob(self, blob_type, data):
        """
        Blob sends a data blob. This is native code data of the give type. For example in a ruida device it might be a
        bunch of .rd code, or Lihuiyu device it could be .egv code. It's a method of sending pre-chewed data to the
        device.

        @param type:
        @param data:
        @return:
        """
        if blob_type == "egv":
            self(data)

    def move_ori(self, x, y):
        """
        Requests laser move to origin offset position x,y in physical units

        @param x:
        @param y:
        @return:
        """
        x, y = self.service.physical_to_device_position(x, y)
        self.rapid_mode()
        self._move_absolute(self.origin_x + int(x), self.origin_y + int(y))

    def move_abs(self, x, y):
        """
        Requests laser move to absolute position x, y in physical units

        @param x:
        @param y:
        @return:
        """
        x, y = self.service.physical_to_device_position(x, y)
        self.rapid_mode()
        self._move_absolute(int(x), int(y))

    def move_rel(self, dx, dy):
        """
        Requests laser move relative position dx, dy in physical units

        @param dx:
        @param dy:
        @return:
        """
        dx, dy = self.service.physical_to_device_length(dx, dy)
        self.rapid_mode()
        self._move_relative(dx, dy)

    def dwell(self, time_in_ms):
        """
        Requests that the laser fire in place for the given time period. This could be done in a series of commands,
        move to a location, turn laser on, wait, turn laser off. However, some drivers have specific laser-in-place
        commands so calling dwell is preferred.

        @param time_in_ms:
        @return:
        """
        self.rapid_mode()
        self.wait_finish()
        self.laser_on()  # This can't be sent early since these are timed operations.
        self.wait(time_in_ms)
        self.laser_off()

    def laser_off(self):
        """
        Turn laser off in place.

        @param values:
        @return:
        """
        if not self.laser:
            return False
        if self.state == DRIVER_STATE_RAPID:
            self(b"I")
            self(self.CODE_LASER_OFF)
            self(b"S1P\n")
            if not self.service.autolock:
                self(b"IS2P\n")
        elif self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
            self(self.CODE_LASER_OFF)
        elif self.state == DRIVER_STATE_FINISH:
            self(self.CODE_LASER_OFF)
            self(b"N")
        self.laser = False
        return True

    def laser_on(self):
        """
        Turn laser on in place.

        @param values:
        @return:
        """
        if self.laser:
            return False
        if self.state == DRIVER_STATE_RAPID:
            self(b"I")
            self(self.CODE_LASER_ON)
            self(b"S1P\n")
            if not self.service.autolock:
                self(b"IS2P\n")
        elif self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
            self(self.CODE_LASER_ON)
        elif self.state == DRIVER_STATE_FINISH:
            self(self.CODE_LASER_ON)
            self(b"N")
        self.laser = True
        return True

    def rapid_mode(self, *values):
        """
        Rapid mode sets the laser to rapid state. This is usually moving the laser around without it executing a large
        batch of commands.

        @param values:
        @return:
        """
        if self.state == DRIVER_STATE_RAPID:
            return
        if self.state == DRIVER_STATE_FINISH:
            self(b"S1P\n")
            if not self.service.autolock:
                self(b"IS2P\n")
        elif self.state in (
            DRIVER_STATE_PROGRAM,
            DRIVER_STATE_RASTER,
            DRIVER_STATE_MODECHANGE,
        ):
            self(b"FNSE-\n")
            self.laser = False
        self.state = DRIVER_STATE_RAPID
        self.service.signal("driver;mode", self.state)

    def finished_mode(self, *values):
        """
        Finished mode is after a large batch of jobs is done. A transition to finished may require the laser process
        all the data in the buffer.

        @param values:
        @return:
        """
        if self.state == DRIVER_STATE_FINISH:
            return
        if self.state in (
            DRIVER_STATE_PROGRAM,
            DRIVER_STATE_RASTER,
            DRIVER_STATE_MODECHANGE,
        ):
            self(b"@NSE")
            self.laser = False
        elif self.state == DRIVER_STATE_RAPID:
            self(b"I")
        self.state = DRIVER_STATE_FINISH
        self.service.signal("driver;mode", self.state)

    def raster_mode(self, *values):
        """
        Raster mode runs in either `G0xx` stepping mode or NSE stepping but is only intended to move horizontal or
        vertical rastering, usually at a high speed. Accel twitches are required for this mode.

        @param values:
        @return:
        """
        if self.state == DRIVER_STATE_RASTER:
            return
        self.finished_mode()
        self.program_mode()

    def program_mode(self, *values, dx=0, dy=0):
        """
        Vector Mode implies but doesn't discount rastering. Twitches are used if twitches is set to True.

        @param values: passed information from the driver command
        @param dx: change in dx that should be made while switching to program mode.
        @param dy: change in dy that should be made while switching to program mode.
        @return:
        """
        if self.state == DRIVER_STATE_PROGRAM:
            return
        self.finished_mode()

        instance_step = 0
        self.step_index = 0
        self.step = self.raster_step_x
        self.step_value_set = 0
        if self.settings.get("_raster_alt", False):
            pass
        elif self.service.nse_raster and not self.service.nse_stepraster:
            pass
        else:
            self.step_value_set = int(round(self.step))
            instance_step = self.step_value_set

        suffix_c = None
        if (
            not self.service.twitches or self.settings.get("_force_twitchless", False)
        ) and not self.step:
            suffix_c = True
        if self._request_leftward is not None:
            self._leftward = self._request_leftward
            self._request_leftward = None
        if self._request_topward is not None:
            self._topward = self._request_topward
            self._request_topward = None
        if self._request_horizontal_major is not None:
            self._horizontal_major = self._request_horizontal_major
            self._request_horizontal_major = None
        if self.service.strict:
            # Override requested or current values only use core initial values.
            self._leftward = False
            self._topward = False
            self._horizontal_major = False

        speed_code = LaserSpeed(
            self.service.board,
            self.speed,
            instance_step,
            d_ratio=self.implicit_d_ratio,
            acceleration=self.implicit_accel,
            fix_limit=True,
            fix_lows=True,
            suffix_c=suffix_c,
            fix_speeds=self.service.fix_speeds,
            raster_horizontal=self._horizontal_major,
        ).speedcode
        speed_code = bytes(speed_code, "utf8")
        self(speed_code)
        self._goto_xy(dx, dy)
        self(b"N")
        self(self._code_declare_directions())
        self(b"S1E")
        if self.step:
            self.state = DRIVER_STATE_RASTER
        else:
            self.state = DRIVER_STATE_PROGRAM
        self.service.signal("driver;mode", self.state)

    def home(self, *values):
        """
        Home the laser.

        @param values:
        @return:
        """
        self.rapid_mode()
        self(b"IPP\n")
        old_current = self.service.current
        self.native_x = 0
        self.native_y = 0
        self._reset_modes()
        self.state = DRIVER_STATE_RAPID
        self.service.signal("driver;mode", self.state)

        new_current = self.service.current
        self.service.signal(
            "driver;position",
            (old_current[0], old_current[1], new_current[0], new_current[1]),
        )

    def lock_rail(self):
        """
        For plotter-style lasers this should prevent the laser bar from moving.

        @return:
        """
        self.rapid_mode()
        self(b"IS1P\n")

    def unlock_rail(self, abort=False):
        """
        For plotter-style jobs this should free the laser head to be movable by the user.

        @return:
        """
        self.rapid_mode()
        self(b"IS2P\n")

    def laser_disable(self, *values):
        self.laser_enabled = False

    def laser_enable(self, *values):
        self.laser_enabled = True

    def plot(self, plot):
        """
        Gives the driver cutcode that should be plotted/performed.

        @param plot:
        @return:
        """
        if isinstance(plot, InputCut):
            self.plot_start()
            self.wait_finish()
            # We do not have any GPIO-output abilities
        elif isinstance(plot, OutputCut):
            self.plot_start()
            self.wait_finish()
            # We do not have any GPIO-input abilities
        elif isinstance(plot, DwellCut):
            self.plot_start()
            self.rapid_mode()
            start = plot.start
            self.move_abs(start[0], start[1])
            self.wait_finish()
            self.dwell(plot.dwell_time)
        elif isinstance(plot, WaitCut):
            self.plot_start()
            self.wait_finish()
            self.wait(plot.dwell_time)
        elif isinstance(plot, HomeCut):
            self.plot_start()
            self.wait_finish()
            self.home()
        elif isinstance(plot, GotoCut):
            self.plot_start()
            start = plot.start
            self.wait_finish()
            self._move_absolute(self.origin_x + start[0], self.origin_y + start[1])
        elif isinstance(plot, SetOriginCut):
            self.plot_start()
            if plot.set_current:
                x = self.native_x
                y = self.native_y
            else:
                x, y = plot.start
            self.set_origin(x, y)
        else:
            self.plot_planner.push(plot)
            # Mirror the stuff
            self.dummy_planner.push(plot)

    def plot_start(self):
        """
        Called at the end of plot commands to ensure the driver can deal with them all cutcode as a group, if this
        is needed by the driver.

        @return:
        """
        self.total_steps = 0
        self.current_steps = 0
        if self.plot_data is None:
            self.plot_data = self.plot_planner.gen()
            skip_calc = True
            if not skip_calc:
                assessment_start = time.time()
                dummy_data = list(self.dummy_planner.gen())
                self.total_steps += len(dummy_data)
                self.dummy_planner.clear()
                # print ("m2nano-Assessment done, Steps=%d - did take %.1f sec" % (self.total_steps, time.time()-assessment_start))

        self._plotplanner_process()

    def set(self, key, value):
        """
        Sets a laser parameter this could be speed, power, wobble, number_of_unicorns, or any unknown parameters for
        yet to be written drivers.

        @param key:
        @param value:
        @return:
        """
        if key == "power":
            self._set_power(value)
        if key == "ppi":
            self._set_power(value)
        if key == "pwm":
            self._set_power(value)
        if key == "overscan":
            self._set_overscan(value)
        if key == "acceleration":
            self._set_acceleration(value)
        if key == "relative":
            self.is_relative = value
        if key == "d_ratio":
            self._set_d_ratio(value)
        if key == "step":
            self._set_step(*value)

    def set_origin(self, x, y):
        """
        This should set the origin position.

        @param x:
        @param y:
        @return:
        """
        self.origin_x = x
        self.origin_y = y

    def wait(self, time_in_ms):
        """
        Wait asks that the work be stalled or current process held for the time time_in_ms in ms. If wait_finished is
        called first this will attempt to stall the machine while performing no work. If the driver in question permits
        waits to be placed within code this should insert waits into the current job. Returning instantly rather than
        holding the processes.

        @param time_in_ms:
        @return:
        """
        time.sleep(time_in_ms / 1000.0)

    def wait_finish(self, *values):
        """
        Wait finish should ensure that no additional commands be processed until the current buffer is completed. This
        does not necessarily imply a change in mode as "finished_mode" would require. Just that the buffer be completed
        before moving on.

        @param values:
        @return:
        """

        def temp_hold():
            try:
                return len(self.out_pipe) != 0
            except TypeError:
                return False

        self.temp_holds.append(temp_hold)

    def status(self):
        """
        Asks that this device status be updated.

        @return:
        """
        parts = list()
        parts.append(f"x={self.native_x}")
        parts.append(f"y={self.native_y}")
        parts.append(f"speed={self.speed}")
        parts.append(f"power={self.power}")
        status = ";".join(parts)
        self.service.signal("driver;status", status)

    def function(self, function):
        """
        This command asks that this function be executed at the appropriate time within the spooled cycle.

        @param function:
        @return:
        """
        function()

    def beep(self):
        """
        This command asks that a beep be executed at the appropriate time within the spooled cycle.

        @return:
        """
        self.service("beep\n")

    def console(self, value):
        """
        This asks that the console command be executed at the appropriate time within the spooled cycle.

        @param value: console command
        @return:
        """
        self.service(value)

    def signal(self, signal, *args):
        """
        This asks that this signal be broadcast.

        @param signal:
        @param args:
        @return:
        """
        self.service.signal(signal, *args)

    ######################
    # Property IO
    ######################

    @property
    def is_left(self):
        return self._x_engaged and not self._y_engaged and self._leftward

    @property
    def is_right(self):
        return self._x_engaged and not self._y_engaged and not self._leftward

    @property
    def is_top(self):
        return not self._x_engaged and self._y_engaged and self._topward

    @property
    def is_bottom(self):
        return not self._x_engaged and self._y_engaged and not self._topward

    @property
    def is_angle(self):
        return self._y_engaged and self._x_engaged

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

    ######################
    # PROTECTED DRIVER CODE
    ######################

    def _plotplanner_process(self):
        """
        Processes any data in the plot planner. Getting all relevant (x,y,on) plot values and performing the cardinal
        movements. Or updating the laser state based on the settings of the cutcode.

        @return:
        """
        if self.plot_data is None:
            return False
        for x, y, on in self.plot_data:
            self.current_steps += 1
            while self.hold_work(0):
                time.sleep(0.05)
            sx = self.native_x
            sy = self.native_y
            # print("x: %s, y: %s -- c: %s, %s" % (str(x), str(y), str(sx), str(sy)))
            on = int(on)
            if on > 1:
                # Special Command.
                if on & PLOT_FINISH:  # Plot planner is ending.
                    self.rapid_mode()
                    break
                elif on & PLOT_SETTING:  # Plot planner settings have changed.
                    p_set = Parameters(self.plot_planner.settings)
                    if p_set.power != self.power:
                        self._set_power(p_set.power)
                    if (
                        p_set.raster_step_x != self.raster_step_x
                        or p_set.raster_step_y != self.raster_step_y
                        or p_set.speed != self.speed
                        or self.implicit_d_ratio != p_set.implicit_d_ratio
                        or self.implicit_accel != p_set.implicit_accel
                    ):
                        self._set_speed(p_set.speed)
                        self._set_step(p_set.raster_step_x, p_set.raster_step_y)
                        self._set_acceleration(p_set.implicit_accel)
                        self._set_d_ratio(p_set.implicit_d_ratio)
                    self.settings.update(p_set.settings)
                elif on & PLOT_AXIS:  # Major Axis.
                    # 0 means X Major / Horizontal.
                    # 1 means Y Major / Vertical
                    self._request_horizontal_major = bool(x == 0)
                elif on & PLOT_DIRECTION:
                    # -1: Moving Left -x
                    # 1: Moving Right. +x
                    self._request_leftward = bool(x != 1)
                    # -1: Moving Bottom +y
                    # 1: Moving Top. -y
                    self._request_topward = bool(y != 1)
                elif on & (
                    PLOT_RAPID | PLOT_JOG
                ):  # Plot planner requests position change.
                    if on & PLOT_RAPID or self.state != DRIVER_STATE_PROGRAM:
                        # Perform a rapid position change. Always perform this for raster moves.
                        # DRIVER_STATE_RASTER should call this code as well.
                        self.rapid_mode()
                        self._move_absolute(x, y)
                    else:
                        # Jog is performable and requested. # We have not flagged our direction or state.
                        self._jog_absolute(x, y, mode=self.service.opt_jog_mode)
                continue
            dx = x - sx
            dy = y - sy
            step_x = self.raster_step_x
            step_y = self.raster_step_y
            if step_x == 0 and step_y == 0:
                # vector mode
                self.program_mode()
            else:
                self.raster_mode()
                if self._horizontal_major:
                    # Horizontal Rastering.
                    if self.service.nse_raster or self.settings.get(
                        "_raster_alt", False
                    ):
                        # Alt-Style Raster
                        if (dx > 0 and self._leftward) or (
                            dx < 0 and not self._leftward
                        ):
                            self._h_switch(dy)
                    else:
                        # Default Raster
                        if dy != 0:
                            self._h_switch_g(dy)
                else:
                    # Vertical Rastering.
                    if self.service.nse_raster or self.settings.get(
                        "_raster_alt", False
                    ):
                        # Alt-Style Raster
                        if (dy > 0 and self._topward) or (dy < 0 and not self._topward):
                            self._v_switch(dx)
                    else:
                        # Default Raster
                        if dx != 0:
                            self._v_switch_g(dx)
                # Update dx, dy (if changed by switches)
                dx = x - self.native_x
                dy = y - self.native_y
            self._goto_octent(dx, dy, on & 1)
        self.plot_data = None
        return False

    def _set_speed(self, speed=None):
        if self.speed != speed:
            self.speed = speed
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def _set_d_ratio(self, d_ratio=None):
        if self.dratio != d_ratio:
            self.dratio = d_ratio
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def _set_acceleration(self, accel=None):
        if self.acceleration != accel:
            self.acceleration = accel
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def _set_step(self, step_x=None, step_y=None):
        if self.raster_step_x != step_x or self.raster_step_y != step_y:
            self.raster_step_x = step_x
            self.raster_step_y = step_y
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def _set_power(self, power=1000.0):
        self.power = power
        if self.power > 1000.0:
            self.power = 1000.0
        if self.power <= 0:
            self.power = 0.0

    def _set_ppi(self, power=1000.0):
        self.power = power
        if self.power > 1000.0:
            self.power = 1000.0
        if self.power <= 0:
            self.power = 0.0

    def _set_pwm(self, power=1000.0):
        self.power = power
        if self.power > 1000.0:
            self.power = 1000.0
        if self.power <= 0:
            self.power = 0.0

    def _set_overscan(self, overscan=None):
        self.overscan = overscan

    def _cut(self, x, y):
        self._goto(x, y, True)

    def _jog(self, x, y, **kwargs):
        if self.is_relative:
            self._jog_relative(x, y, **kwargs)
        else:
            self._jog_absolute(x, y, **kwargs)

    def _jog_absolute(self, x, y, **kwargs):
        self._jog_relative(x - self.native_x, y - self.native_y, **kwargs)

    def _jog_relative(self, dx, dy, mode=0):
        self.laser_off()
        dx = int(round(dx))
        dy = int(round(dy))
        if mode == 0:
            self._nse_jog_event(dx, dy)
        elif mode == 1:
            self._mode_shift_on_the_fly(dx, dy)
        else:
            # Finish-out Jog
            self.rapid_mode()
            self._move_relative(dx, dy)
            self.program_mode()

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
        if self._horizontal_major:
            if not self.is_left and dx >= 0:
                self(self.CODE_LEFT)
            if not self.is_right and dx <= 0:
                self(self.CODE_RIGHT)
        else:
            if not self.is_top and dy >= 0:
                self(self.CODE_TOP)
            if not self.is_bottom and dy <= 0:
                self(self.CODE_BOTTOM)
        self(b"N")
        self._goto_xy(dx, dy)
        self(b"SE")
        self(self._code_declare_directions())
        self.state = original_state

    def _move(self, x, y):
        self._goto(x, y, False)

    def _move_absolute(self, x, y):
        self._goto_absolute(x, y, False)

    def _move_relative(self, x, y):
        self._goto_relative(x, y, False)

    def _goto(self, x, y, cut):
        """
        Goto a position within a cut.

        This depends on whether is_relative is set.

        @param x:
        @param y:
        @param cut:
        @return:
        """
        if self.is_relative:
            self._goto_relative(x, y, cut)
        else:
            self._goto_absolute(x, y, cut)

    def _goto_absolute(self, x, y, cut):
        """
        Goto absolute x and y. With cut set or not set.

        @param x:
        @param y:
        @param cut:
        @return:
        """
        self._goto_relative(x - self.native_x, y - self.native_y, cut)

    def _move_in_rapid_mode(self, dx, dy, cut):
        if self.service.rapid_override and (dx != 0 or dy != 0):
            # Rapid movement override. Should make programmed jogs.
            self._set_acceleration(None)
            self._set_step(0, 0)
            if dx != 0:
                self.rapid_mode()
                self._set_speed(self.service.rapid_override_speed_x)
                self.program_mode()
                self._goto_octent(dx, 0, cut)
            if dy != 0:
                if (
                    self.service.rapid_override_speed_x
                    != self.service.rapid_override_speed_y
                ):
                    self.rapid_mode()
                    self._set_speed(self.service.rapid_override_speed_y)
                    self.program_mode()
                self._goto_octent(0, dy, cut)
            self.rapid_mode()
        else:
            self(b"I")
            self._goto_xy(dx, dy)
            self(b"S1P\n")
            if not self.service.autolock:
                self(b"IS2P\n")

    def _commit_mode(self):
        # Unknown utility ported from deleted branch
        self(b"N")
        speed_code = LaserSpeed(
            self.service.board,
            self.speed,
            self.raster_step_x,
            d_ratio=self.implicit_d_ratio,
            acceleration=self.implicit_accel,
            fix_limit=True,
            fix_lows=True,
            fix_speeds=self.service.fix_speeds,
            raster_horizontal=True,
        ).speedcode
        speed_code = bytes(speed_code, "utf8")
        self(speed_code)
        self(b"SE")
        self.laser = False

    def _goto_relative(self, dx, dy, cut):
        """
        Goto relative dx, dy. With cut set or not set.

        @param dx:
        @param dy:
        @param cut:
        @return:
        """
        if abs(dx) == 0 and abs(dy) == 0:
            return
        dx = int(round(dx))
        dy = int(round(dy))
        old_current = self.service.current
        if self.state == DRIVER_STATE_RAPID:
            self._move_in_rapid_mode(dx, dy, cut)
        elif self.state == DRIVER_STATE_RASTER:
            # goto in raster, switches to program to recall this function.
            self.program_mode()
            self._goto_relative(dx, dy, cut)
            return
        elif self.state == DRIVER_STATE_PROGRAM:
            mx = 0
            my = 0
            line = list(grouped(ZinglPlotter.plot_line(0, 0, dx, dy)))
            for x, y in line:
                self._goto_octent(x - mx, y - my, cut)
                mx = x
                my = y
        elif self.state == DRIVER_STATE_FINISH:
            self._goto_xy(dx, dy)
            self(b"N")
        elif self.state == DRIVER_STATE_MODECHANGE:
            self._mode_shift_on_the_fly(dx, dy)

        new_current = self.service.current
        self.service.signal(
            "driver;position",
            (old_current[0], old_current[1], new_current[0], new_current[1]),
        )

    def _mode_shift_on_the_fly(self, dx=0, dy=0):
        """
        Mode-shift on the fly changes the current modes while in programmed or raster mode
        this exits with a @ command that resets the modes. A movement operation can be added after
        the speed code and before the return to into programmed or raster mode.

        This switch is often avoided because testing revealed some chance of a runaway during reset
        switching.

        If the raster step has been changed from zero this can result in shifting from program to raster mode
        """
        dx = int(round(dx))
        dy = int(round(dy))
        self(b"@NSE")
        self.laser = False
        self.state = DRIVER_STATE_RAPID
        self.program_mode(dx, dy)

    def _h_switch(self, dy: float):
        """
        NSE h_switches replace the mere reversal of direction with N<v><distance>SE

        If a G-value is set we should subtract that from the step for our movement. Since triggering NSE will cause
        that step to occur.

        @param dy: The amount along the directional axis we should move during this step.

        @return:
        """
        set_step = self.step_value_set
        if isinstance(set_step, tuple):
            set_step = set_step[self.step_index % len(set_step)]

        # correct for fractional stepping
        self.step_total += dy
        delta = math.trunc(self.step_total)
        self.step_total -= delta

        step_amount = -set_step if self._topward else set_step
        delta = delta - step_amount

        # We force reenforce directional move.
        if self._leftward:
            self(self.CODE_LEFT)
        else:
            self(self.CODE_RIGHT)
        self(b"N")
        if delta != 0:
            if delta < 0:
                self(self.CODE_TOP)
                self._topward = True
            else:
                self(self.CODE_BOTTOM)
                self._topward = False
            self(lhymicro_distance(abs(delta)))
            self.native_y += delta
        self(b"SE")
        self.native_y += step_amount

        self._leftward = not self._leftward
        self._x_engaged = True
        self._y_engaged = False
        self.laser = False
        self.step_index += 1

    def _v_switch(self, dx: float):
        """
        NSE v_switches replace the mere reversal of direction with N<h><distance>SE

        @param dx: The amount along the directional axis we should move during this step.

        @return:
        """
        set_step = self.step_value_set
        if isinstance(set_step, tuple):
            set_step = set_step[self.step_index % len(set_step)]

        # correct for fractional stepping
        self.step_total += dx
        delta = math.trunc(self.step_total)
        self.step_total -= delta

        step_amount = -set_step if self._leftward else set_step
        delta = delta - step_amount

        # We force reenforce directional move.
        if self._topward:
            self(self.CODE_TOP)
        else:
            self(self.CODE_BOTTOM)
        self(b"N")
        if delta != 0:
            if delta < 0:
                self(self.CODE_LEFT)
                self._leftward = True
            else:
                self(self.CODE_RIGHT)
                self._leftward = False
            self(lhymicro_distance(abs(delta)))
            self.native_x += delta
        self(b"SE")
        self.native_x += step_amount
        self._topward = not self._topward
        self._x_engaged = False
        self._y_engaged = True
        self.laser = False
        self.step_index += 1

    def _h_switch_g(self, dy: float):
        """
        Horizontal switch with a Gvalue set. The board will automatically step according to the step_value_set.

        @return:
        """
        set_step = self.step_value_set
        if isinstance(set_step, tuple):
            set_step = set_step[self.step_index % len(set_step)]

        # correct for fractional stepping
        self.step_total += dy
        delta = math.trunc(self.step_total)
        self.step_total -= delta

        step_amount = -set_step if self._topward else set_step
        delta = delta - step_amount
        if delta != 0:
            # Movement exceeds the standard raster step amount. Rapid relocate.
            self.finished_mode()
            self._move_relative(0, delta)
            self._x_engaged = True
            self._y_engaged = False
            self.raster_mode()

        # We reverse direction and step.
        if self._leftward:
            self(self.CODE_RIGHT)
            self._leftward = False
        else:
            self(self.CODE_LEFT)
            self._leftward = True
        self.native_y += step_amount
        self.laser = False
        self.step_index += 1

    def _v_switch_g(self, dx: float):
        """
        Vertical switch with a Gvalue set. The board will automatically step according to the step_value_set.

        @return:
        """
        set_step = self.step_value_set
        if isinstance(set_step, tuple):
            set_step = set_step[self.step_index % len(set_step)]

        # correct for fractional stepping
        self.step_total += dx
        delta = math.trunc(self.step_total)
        self.step_total -= delta

        step_amount = -set_step if self._leftward else set_step
        delta = delta - step_amount
        if delta != 0:
            # Movement exceeds the standard raster step amount. Rapid relocate.
            self.finished_mode()
            self._move_relative(delta, 0)
            self._y_engaged = True
            self._x_engaged = False
            self.raster_mode()

        # We reverse direction and step.
        if self._topward:
            self(self.CODE_BOTTOM)
            self._topward = False
        else:
            self(self.CODE_TOP)
            self._topward = True
        self.native_x += step_amount
        self.laser = False
        self.step_index += 1

    def _reset_modes(self):
        self.laser = False
        self._request_leftward = None
        self._request_topward = None
        self._request_horizontal_major = None
        self._topward = False
        self._leftward = False
        self._x_engaged = False
        self._y_engaged = False
        self._horizontal_major = False

    def _goto_xy(self, dx, dy):
        rapid = self.state not in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER)
        if dx != 0:
            self.native_x += dx
            if dx > 0:  # Moving right
                if not self.is_right or rapid:
                    self(self.CODE_RIGHT)
                    self._leftward = False
            else:  # Moving left
                if not self.is_left or rapid:
                    self(self.CODE_LEFT)
                    self._leftward = True
            self._x_engaged = True
            self._y_engaged = False
            self(lhymicro_distance(abs(dx)))
        if dy != 0:
            self.native_y += dy
            if dy > 0:  # Moving bottom
                if not self.is_bottom or rapid:
                    self(self.CODE_BOTTOM)
                    self._topward = False
            else:  # Moving top
                if not self.is_top or rapid:
                    self(self.CODE_TOP)
                    self._topward = True
            self._x_engaged = False
            self._y_engaged = True
            self(lhymicro_distance(abs(dy)))

    def _goto_octent(self, dx, dy, on):
        old_current = self.service.current
        if dx == 0 and dy == 0:
            return
        if on:
            self.laser_on()
        else:
            self.laser_off()
        if abs(dx) == abs(dy):
            self._x_engaged = True  # Set both on
            self._y_engaged = True
            if dx > 0:  # Moving right
                if self._leftward:
                    self(self.CODE_RIGHT)
                    self._leftward = False
            else:  # Moving left
                if not self._leftward:
                    self(self.CODE_LEFT)
                    self._leftward = True
            if dy > 0:  # Moving bottom
                if self._topward:
                    self(self.CODE_BOTTOM)
                    self._topward = False
            else:  # Moving top
                if not self._topward:
                    self(self.CODE_TOP)
                    self._topward = True
            self.native_x += dx
            self.native_y += dy
            self(self.CODE_ANGLE)
            self(lhymicro_distance(abs(dy)))
        else:
            self._goto_xy(dx, dy)

        new_current = self.service.current
        self.service.signal(
            "driver;position",
            (old_current[0], old_current[1], new_current[0], new_current[1]),
        )

    def _code_declare_directions(self):
        x_dir = self.CODE_LEFT if self._leftward else self.CODE_RIGHT
        y_dir = self.CODE_TOP if self._topward else self.CODE_BOTTOM
        if self._horizontal_major:
            self._x_engaged = True
            self._y_engaged = False
            return y_dir + x_dir
        else:
            self._x_engaged = False
            self._y_engaged = True
            return x_dir + y_dir


class LihuiyuController:
    """
    K40 Controller controls the Lihuiyu boards sending any queued data to the USB when the signal is not busy.

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
        self.pipe_channel = context.channel(f"{name}/events")
        self.usb_log = context.channel(f"{name}/usb", buffer_size=500)
        self.usb_send_channel = context.channel(f"{name}/usb_send")
        self.recv_channel = context.channel(f"{name}/recv")
        self.usb_log.watch(lambda e: context.signal("pipe;usb_status", e))
        self.ch341 = context.open("module/ch341", log=self.usb_log)
        self.reset()

    @property
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
            self.realtime_write(b"\x18\n")

    def __repr__(self):
        return f"LihuiyuController({str(self.context)})"

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

        @param bytes_to_write: data to write to the queue.
        @return:
        """
        f = bytes_to_write.find(b"~")
        if f != -1:
            # ~ was found in bytes. We are in a realtime exception.
            self.realtime = True

            # All code prior to ~ is sent to write.
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

        self.pipe_channel(f"write({str(bytes_to_write)})")
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

        @param bytes_to_write: data to write to the front of the queue.
        @return:
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
        self.pipe_channel(f"realtime_write({str(bytes_to_write)})")
        self._preempt_lock.acquire(True)
        self._preempt = bytearray(bytes_to_write) + self._preempt
        self._preempt_lock.release()
        self.start()
        self.update_buffer()
        return self

    def start(self):
        """
        Controller state change to `Started`.
        @return:
        """

        if not self.is_shutdown and (
            self._thread is None or not self._thread.is_alive()
        ):
            self._thread = self.context.threaded(
                self._thread_data_send,
                thread_name=f"LhyPipe({self.context.path})",
                result=self.stop,
            )
            self._thread.stop = self.stop
            self.update_state(STATE_INITIALIZE)

    def _pause_busy(self):
        """
        BUSY can be called in a paused state to packet halt the controller.

        This can only be done from PAUSE.
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
        Otherwise, it must be done from ACTIVE or IDLE.
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
        self._realtime_buffer = bytearray()
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
                if self.is_shutdown:
                    break  # Sometimes it could reset this and escape.
                time.sleep(3)  # 3-second sleep on failed connection attempt.
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

        @return: queue process success.
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
                if self.state == STATE_TERMINATE:
                    return  # Abort all the processes was requested. This state change would be after clearing.
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
        except TimeoutError:
            self.disconnect()
            self.service.signal("tcp;status", "timeout connect")
        except ConnectionError:
            self.disconnect()
            self.service.signal("tcp;status", "connection error")
        except socket.gaierror as e:
            self.disconnect()
            self.service.signal("tcp;status", "address resolve error")
        except socket.herror as e:
            self.disconnect()
            self.service.signal("tcp;status", f"herror: {str(e)}")

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

    @property
    def viewbuffer(self):
        return self.buffer.decode("utf8")

    def _start(self):
        if self.thread is None:
            self.thread = self.service.threaded(
                self._sending,
                thread_name=f"sender-{self.service.port}",
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
            return (
                f"TCPOutput('{self.service.address}:{self.service.port}','{self.name}')"
            )
        return f"TCPOutput('{self.service.address}:{self.service.port}')"

    def __len__(self):
        return len(self.buffer)


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
        return f"UNK {code:02x}"


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
    if v < 0:
        raise ValueError("Cannot permit negative values.")
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

    @param line: line to be CRC'd
    @return: 8 bit crc of line.
    """
    crc = 0
    for i in range(0, 30):
        crc = line[i] ^ crc
        crc = crc_table[crc & 0x0F] ^ crc_table[16 + ((crc >> 4) & 0x0F)]
    return crc
