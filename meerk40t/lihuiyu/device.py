"""
Lihuiyu Device

Registers the Device service for M2 Nano (and family), registering the relevant commands and provides the viewport for
the given device type.
"""

from hashlib import md5

from meerk40t.core.laserjob import LaserJob
from meerk40t.core.spoolers import Spooler
from meerk40t.kernel import CommandSyntaxError, Service, signal_listener

from ..core.units import UNITS_PER_MIL, Length, ViewPort
from .controller import LihuiyuController
from .driver import LihuiyuDriver
from .tcp_connection import TCPOutput


class LihuiyuDevice(Service, ViewPort):
    """
    LihuiyuDevice is driver for the M2 Nano and other classes of Lihuiyu boards.
    """

    def __init__(self, kernel, path, *args, choices=None, **kwargs):
        Service.__init__(self, kernel, path)
        self.name = "LihuiyuDevice"
        _ = kernel.translation
        self.extension = "egv"
        if choices is not None:
            for c in choices:
                attr = c.get("attr")
                default = c.get("default")
                if attr is not None and default is not None:
                    setattr(self, attr, default)
        choices = [
            {
                "attr": "bedwidth",
                "object": self,
                "default": "310mm",
                "type": Length,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
                "section": "_30_" + _("Laser Parameters"),
                "nonzero": True,
                "subsection": _("Bed Dimensions"),
                "signals": "bedsize",
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": "210mm",
                "type": Length,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
                "section": "_30_" + _("Laser Parameters"),
                "nonzero": True,
                "subsection": _("Bed Dimensions"),
                "signals": "bedsize",
            },
            {
                "attr": "user_scale_x",
                "object": self,
                "default": 1.000,
                "type": float,
                "label": _("X Scale Factor"),
                "tip": _(
                    "Scale factor for the X-axis. Board units to actual physical units."
                ),
                "section": "_30_" + _("Laser Parameters"),
                "subsection": _("User Scale Factor"),
                "nonzero": True,
            },
            {
                "attr": "user_scale_y",
                "object": self,
                "default": 1.000,
                "type": float,
                "label": _("Y Scale Factor"),
                "tip": _(
                    "Scale factor for the Y-axis. Board units to actual physical units."
                ),
                "section": "_30_" + _("Laser Parameters"),
                "subsection": _("User Scale Factor"),
                "nonzero": True,
            },
        ]
        self.register_choices("bed_dim", choices)

        choices = [
            {
                "attr": "label",
                "object": self,
                "default": "lihuiyu-device",
                "type": str,
                "label": _("Device Name"),
                "tip": _("The internal label to be used for this device"),
                "section": "_00_" + _("General"),
                "priority": "10",
                "signals": "device;renamed",
            },
            {
                "attr": "board",
                "object": self,
                "default": "M2",
                "type": str,
                "label": _("Board"),
                "style": "combosmall",
                "choices": ["M2", "M3", "B2", "M", "M1", "A", "B", "B1"],
                "tip": _(
                    "Select the board to use. This has an effects the speedcodes used."
                ),
                "section": "_10_" + _("Configuration"),
                "subsection": _("Board Setup"),
                "signals": "bedsize",
            },
            {
                "attr": "flip_x",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Flip X"),
                "tip": _("Flip the Right and Left commands sent to the controller"),
                "section": "_10_" + _("Configuration"),
                "subsection": _("X Axis"),
                "signals": "bedsize",
            },
            {
                "attr": "home_right",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Home Right"),
                "tip": _("Indicates the device Home is on the right"),
                "section": "_10_" + _("Configuration"),
                "subsection": _("X Axis"),
                "signals": "bedsize",
            },
            {
                "attr": "flip_y",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Flip Y"),
                "tip": _("Flip the Y axis for the Balor device"),
                "section": "_10_" + _("Configuration"),
                "subsection": _("Y Axis"),
                "signals": "bedsize",
            },
            {
                "attr": "home_bottom",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Home Bottom"),
                "tip": _("Indicates the device Home is on the bottom"),
                "section": "_10_" + _("Configuration"),
                "subsection": _("Y Axis"),
                "signals": "bedsize",
            },
            {
                "attr": "swap_xy",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Swap X and Y"),
                "tip": _(
                    "Swaps the X and Y axis. This happens before the FlipX and FlipY."
                ),
                "section": "_10_" + _("Configuration"),
                "subsection": "_10_" + _("Axis corrections"),
                "signals": "bedsize",
            },
        ]
        self.register_choices("bed_orientation", choices)

        choices = [
            {
                "attr": "autolock",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Automatically lock rail"),
                "tip": _("Lock rail after operations are finished."),
                "section": "_00_" + _("General Options"),
            },
            {
                "attr": "plot_phase_type",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Phase Type"),
                "tip": "",
                "section": "_00_" + _("General Options"),
            },
            {
                "attr": "plot_phase_value",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Phase Type"),
                "tip": "",
                "section": "_00_" + _("General Options"),
            },
            {
                "attr": "plot_shift",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Pulse Grouping"),
                "tip": "\n".join(
                    [
                        _(
                            "Pulse Grouping is an alternative means of reducing the incidence of stuttering, allowing you potentially to burn at higher speeds."
                        ),
                        "",
                        _(
                            "It works by swapping adjacent on or off bits to group on and off together and reduce the number of switches."
                        ),
                        "",
                        _(
                            'As an example, instead of X_X_ it will burn XX__ - because the laser beam is overlapping, and because a bit is only moved at most 1/1000", the difference should not be visible even under magnification.'
                        ),
                        _(
                            "Whilst the Pulse Grouping option in Operations are set for that operation before the job is spooled, and cannot be changed on the fly, this global Pulse Grouping option is checked as instructions are sent to the laser and can turned on and off during the burn process. Because the changes are believed to be small enough to be undetectable, you may wish to leave this permanently checked."
                        ),
                    ]
                ),
                "section": "_00_" + _("General Options"),
            },
            {
                "attr": "strict",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Strict"),
                "tip": _(
                    "Forces the device to enter and exit programmed speed mode from the same direction.\nThis may prevent devices like the M2-V4 and earlier from having issues. Not typically needed."
                ),
                "section": "_00_" + _("General Options"),
            },
            {
                "attr": "twitches",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Twitch Vectors"),
                "tip": _(
                    "Twitching is an unnecessary move in an unneeded direction at the start and end of travel moves between vector burns. "
                    "It is most noticeable when you are doing a number of small burns (e.g. stitch holes in leather). "
                    "A twitchless mode is now default in 0.7.6+ or later which results in a noticeable faster travel time. "
                    "This option allows you to turn on the previous mode if you experience problems."
                ),
                "section": "_00_" + _("General Options"),
            },
        ]
        self.register_choices("lhy-general", choices)

        choices = [
            {
                "attr": "opt_rapid_between",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Rapid Moves Between Objects"),
                "tip": _("Perform rapid moves between the objects"),
                "section": "_00_" + _("Rapid Jog"),
            },
            {
                "attr": "opt_jog_minimum",
                "object": self,
                "default": 256,
                "type": int,
                "label": _("Minimum Jog Distance"),
                "tip": _("Minimum travel distance before invoking a rapid jog move."),
                "conditional": (self, "opt_rapid_between"),
                "limited": True,
                "section": "_00_" + _("Rapid Jog"),
            },
            {
                "attr": "opt_jog_mode",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Jog Method"),
                "style": "radio",
                "choices": [_("Default"), _("Reset"), _("Finish")],
                "tip": _(
                    "Changes the method of jogging. Default are NSE jogs. Reset are @NSE jogs. Finished are @FNSE jogs followed by a wait."
                ),
                "section": "_00_" + _("Rapid Jog"),
            },
        ]
        self.register_choices("lhy-jog", choices)

        choices = [
            {
                "attr": "rapid_override",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Override Rapid Movements"),
                "tip": _("Perform rapid moves between the objects"),
                "section": "_00_" + _("Rapid Override"),
            },
            {
                "attr": "rapid_override_speed_x",
                "object": self,
                "default": 50.0,
                "type": float,
                "label": _("X Travel Speed:"),
                "tip": _("Minimum travel distance before invoking a rapid jog move."),
                "trailer": "mm/s",
                "conditional": (self, "rapid_override"),
                "section": "_00_" + _("Rapid Override"),
            },
            {
                "attr": "rapid_override_speed_y",
                "object": self,
                "default": 50.0,
                "type": float,
                "label": _("Y Travel Speed:"),
                "tip": _("Minimum travel distance before invoking a rapid jog move."),
                "trailer": "mm/s",
                "conditional": (self, "rapid_override"),
                "section": "_00_" + _("Rapid Override"),
            },
        ]
        self.register_choices("lhy-rapid-override", choices)

        choices = [
            {
                "attr": "fix_speeds",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Fix rated to actual speed"),
                "tip": _(
                    "Correct for speed invalidity. Lihuiyu Studios speeds are 92% of the correctly rated speed"
                ),
                "section": "_40_" + _("Speed"),
            },
        ]
        self.register_choices("lhy-speed", choices)

        choices = [
            {
                "attr": "rotary_active",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Rotary-Mode active"),
                "tip": _("Is the rotary mode active for this device"),
            },
            {
                "attr": "rotary_scale_x",
                "object": self,
                "default": 1.0,
                "type": float,
                "label": _("X-Scale"),
                "tip": _("Scale that needs to be applied to the X-Axis"),
                "conditional": (self, "rotary_active"),
                "subsection": _("Scale"),
            },
            {
                "attr": "rotary_scale_y",
                "object": self,
                "default": 1.0,
                "type": float,
                "label": _("Y-Scale"),
                "tip": _("Scale that needs to be applied to the Y-Axis"),
                "conditional": (self, "rotary_active"),
                "subsection": _("Scale"),
            },
            {
                "attr": "rotary_supress_home",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Ignore Home"),
                "tip": _("Ignore Home-Command"),
                "conditional": (self, "rotary_active"),
            },
            {
                "attr": "rotary_flip_x",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mirror X"),
                "tip": _("Mirror the elements on the X-Axis"),
                "conditional": (self, "rotary_active"),
                "subsection": _("Mirror Output"),
            },
            {
                "attr": "rotary_flip_y",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mirror Y"),
                "tip": _("Mirror the elements on the Y-Axis"),
                "conditional": (self, "rotary_active"),
                "subsection": _("Mirror Output"),
            },
        ]
        self.register_choices("rotary", choices)

        # This device prefers to display power level in ppi
        self.setting(bool, "use_percent_for_power_display", False)

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
            user_scale_x=self.user_scale_x,
            user_scale_y=self.user_scale_y,
            native_scale_x=UNITS_PER_MIL,
            native_scale_y=UNITS_PER_MIL,
            origin_x=1.0 if self.home_right else 0.0,
            origin_y=1.0 if self.home_bottom else 0.0,
            flip_x=self.flip_x,
            flip_y=self.flip_y,
            swap_xy=self.swap_xy,
            rotary_active=self.rotary_active,
            rotary_scale_x=self.rotary_scale_x,
            rotary_scale_y=self.rotary_scale_y,
            rotary_flip_x=self.rotary_flip_x,
            rotary_flip_y=self.rotary_flip_y,
        )
        self.setting(int, "buffer_max", 900)
        self.setting(bool, "buffer_limit", True)

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
                self.spooler.laserjob(
                    list(timed_fire()),
                    label=label,
                    helper=True,
                    outline=[self.native] * 4,
                )
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
                    outline=self.outline_move_relative(dx.length_mil, dy.length_mil),
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
            self.controller.update_state("active")
            self.controller.start()
            channel(_("Lihuiyu Channel Started."))

        @self.console_command("hold", help=_("Hold Controller"))
        def pipe_pause(command, channel, _, **kwargs):
            self.controller.update_state("pause")
            self.controller.pause()
            channel("Lihuiyu Channel Paused.")

        @self.console_command("resume", help=_("Resume Controller"))
        def pipe_resume(command, channel, _, **kwargs):
            self.controller.update_state("active")
            self.controller.start()
            channel(_("Lihuiyu Channel Resumed."))

        @self.console_command("usb_connect", help=_("Connects USB"))
        def usb_connect(command, channel, _, **kwargs):
            try:
                self.controller.open()
                channel(_("Usb Connection Opened."))
            except (ConnectionRefusedError, ConnectionError):
                # Refused is typical but inability to confirm serial would result in connection error.
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

    def service_attach(self, *args, **kwargs):
        self.realize()

    @signal_listener("rotary_scale_x")
    @signal_listener("rotary_scale_y")
    @signal_listener("rotary_active")
    @signal_listener("user_scale_x")
    @signal_listener("user_scale_y")
    @signal_listener("bedsize")
    @signal_listener("flip_x")
    @signal_listener("flip_y")
    @signal_listener("swap_xy")
    def realize(self, origin=None, *args):
        self.width = self.bedwidth
        self.height = self.bedheight
        super().realize()
        self.space.update_bounds(0, 0, self.width, self.height)

    def outline_move_relative(self, dx, dy):
        x, y = self.native
        new_x = x + dx
        new_y = y + dy
        min_x = min(x, new_x)
        min_y = min(y, new_y)
        max_x = max(x, new_x)
        max_y = max(y, new_y)
        return (min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)

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
