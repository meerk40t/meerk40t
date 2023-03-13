"""
Lihuiyu Device

Registers the Device service for M2 Nano (and family), registering the relevant commands and provides the viewport for
the given device type.
"""

from hashlib import md5

from meerk40t.core.laserjob import LaserJob
from meerk40t.core.spoolers import Spooler
from meerk40t.kernel import STATE_ACTIVE, STATE_PAUSE, CommandSyntaxError, Service

from ..core.units import UNITS_PER_MIL, Length, ViewPort
from .controller import LihuiyuController
from .driver import LihuiyuDriver
from .tcp_connection import TCPOutput


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
        width = float(Length(self.bedwidth))
        height = float(Length(self.bedheight))
        ViewPort.__init__(
            self,
            scene1=(width, 0),
            scene2=(0, 0),
            scene3=(0, height),
            scene4=(width, height),
            laser1=(UNITS_PER_MIL / width, 0),
            laser2=(0, 0),
            laser3=(0, UNITS_PER_MIL / height),
            laser4=(UNITS_PER_MIL / width, UNITS_PER_MIL / height),
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
                    list(move_at_speed()),
                    label=f"move {dx} {dy} at {speed}",
                    helper=True,
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
            pass

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
            if self.driver.paused:
                self.driver.resume()
            else:
                self.driver.pause()
            self.signal("pause")

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

            except (PermissionError, OSError):
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
                with open(filename) as f:
                    skip_header(f)
                    while True:
                        data = f.read(1024)
                        if not data:
                            break
                        buffer = bytes(data, "utf8")
                        self.output.write(buffer)
                    self.output.write(b"\n")
            except (PermissionError, OSError, FileNotFoundError):
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
            except (PermissionError, OSError):
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
            try:
                self.controller.close()
                channel(_("CH341 Closed."))
            except ConnectionError:
                channel(_("Usb Connection Error"))

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
        @kernel.console_option(
            "verbose",
            "v",
            type=bool,
            action="store_true",
            help=_("watch server channels"),
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
            channel, _, port=23, verbose=False, watch=False, quit=False, **kwargs
        ):
            """
            The lhyserver provides for an open TCP on a specific port. Any data sent to this port will be sent directly
            to the lihuiyu laser. This is how the tcp-connection sends data to the laser if that option is used. This
            requires an additional computer such a raspberry pi doing the interfacing.
            """
            try:
                server_name = f"lhyserver{self.path}"
                output = self.controller
                server = self.open_as("module/TCPServer", server_name, port=port)
                if quit:
                    self.close(server_name)
                    return
                channel(_("TCP Server for lihuiyu on port: {port}").format(port=port))
                if verbose:
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

        if self.has_feature("interpreter/lihuiyu"):

            @self.console_command(
                "lhyinterpreter", help=_("activate the lhyinterpreter.")
            )
            def lhyinterpreter(channel, _, **kwargs):
                try:
                    self.open_as("interpreter/lihuiyu", "lhyinterpreter")
                    channel(
                        _("Lihuiyu interpreter attached to {device}").format(
                            device=str(self)
                        )
                    )
                except KeyError:
                    channel(_("Intepreter cannot be attached to any device."))
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

    def update_dimensions(self, x0, y0, x1, y1):
        width = x1 - x0
        height = y1 - y0
        scene1 = (x1, y0)
        scene2 = (x0, y0)
        scene3 = (x0, y1)
        scene4 = (x1, y1)
        self.update_scene(scene1, scene2, scene3, scene4)
        laser1 = (UNITS_PER_MIL / width, 0)
        laser2 = (0, 0)
        laser3 = (0, UNITS_PER_MIL / height)
        laser4 = (UNITS_PER_MIL / width, UNITS_PER_MIL / height)
        self.update_laser(laser1, laser2, laser3, laser4)

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
