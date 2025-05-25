"""
Newly Device
"""
from meerk40t.core.laserjob import LaserJob
from meerk40t.core.spoolers import Spooler
from meerk40t.core.units import Length
from meerk40t.core.view import View
from meerk40t.device.devicechoices import get_effect_choices
from meerk40t.device.mixins import Status
from meerk40t.kernel import CommandSyntaxError, Service, signal_listener
from meerk40t.newly.driver import NewlyDriver


class NewlyDevice(Service, Status):
    """
    Newly Device
    """

    def __init__(self, kernel, path, *args, choices=None, **kwargs):
        Service.__init__(self, kernel, path)
        Status.__init__(self)
        self.name = "newly"
        self.extension = "hpgl"
        self.job = None
        if choices is not None:
            for c in choices:
                attr = c.get("attr")
                default = c.get("default")
                if attr is not None and default is not None:
                    setattr(self, attr, default)

        _ = kernel.translation
        choices = [
            {
                "attr": "speedchart",
                "object": self,
                "default": [
                    {
                        "speed": 100,
                        "acceleration_length": 8,
                        "backlash": 0,
                        "corner_speed": 20,
                    },
                    {
                        "speed": 200,
                        "acceleration_length": 10,
                        "backlash": 0,
                        "corner_speed": 20,
                    },
                    {
                        "speed": 300,
                        "acceleration_length": 14,
                        "backlash": 0,
                        "corner_speed": 20,
                    },
                    {
                        "speed": 400,
                        "acceleration_length": 16,
                        "backlash": 0,
                        "corner_speed": 20,
                    },
                    {
                        "speed": 500,
                        "acceleration_length": 18,
                        "backlash": 0,
                        "corner_speed": 20,
                    },
                ],
                "type": list,
                "columns": [
                    {
                        "attr": "speed",
                        "type": int,
                        "label": _("Speed <="),
                        "width": 133,
                        "editable": True,
                    },
                    {
                        "attr": "acceleration_length",
                        "type": int,
                        "label": _("Acceleration Length"),
                        "width": 144,
                        "editable": True,
                    },
                    {
                        "attr": "backlash",
                        "type": int,
                        "label": _("Backlash"),
                        "width": 142,
                        "editable": True,
                    },
                    {
                        "attr": "corner_speed",
                        "type": int,
                        "label": _("Corner Speed"),
                        "width": 133,
                        "editable": True,
                    },
                ],
                "style": "chart",
                "primary": "speed",
                "allow_deletion": True,
                "allow_duplication": True,
                "label": _("Speed Chart"),
                "tip": _("Raster speed to chart."),
            },
        ]
        self.register_choices("newly-speedchart", choices)

        self.register_choices("newly-effects", get_effect_choices(self))

        choices = [
            {
                "attr": "label",
                "object": self,
                "default": "newly-device",
                "type": str,
                "label": _("Label"),
                "tip": _("What is this device called."),
                "section": "_00_General",
                "priority": "10",
            },
            {
                "attr": "bedwidth",
                "object": self,
                "default": "310mm",
                "type": str,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
                "section": "_00_General",
                "subsection": "_10_Dimensions",
                "priority": "20",
                "nonzero": True,
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": "210mm",
                "type": str,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
                "section": "_00_General",
                "subsection": "_10_Dimensions",
                "priority": "20",
                "nonzero": True,
            },
            {
                "attr": "laserspot",
                "object": self,
                "default": "0.3mm",
                "type": Length,
                "label": _("Laserspot"),
                "tip": _("Laser spot size"),
                "section": "_00_General",
                "subsection": "_10_Dimensions",
                "nonzero": True,
            },
            {
                "attr": "user_margin_x",
                "object": self,
                "default": 0,
                "type": str,
                "label": _("X-Margin"),
                "tip": _(
                    "Margin for the X-axis. This will be a kind of unused space at the left side."
                ),
                "section": "_10_Parameters",
                "subsection": "_45_User Offset",
            },
            {
                "attr": "user_margin_y",
                "object": self,
                "default": "0",
                "type": str,
                "label": _("Y-Margin"),
                "tip": _(
                    "Margin for the Y-axis. This will be a kind of unused space at the top."
                ),
                "section": "_10_Parameters",
                "subsection": "_45_User Offset",
            },
            {
                "attr": "home_corner",
                "object": self,
                "default": "auto",
                "type": str,
                "style": "combo",
                "choices": [
                    "auto",
                    "top-left",
                    "top-right",
                    "bottom-left",
                    "bottom-right",
                    "center",
                ],
                "label": _("Force Declared Home"),
                "tip": _("Override native home location"),
                "section": "_10_Parameters",
                "subsection": "_50_" + _("Home position"),
            },
            {
                "attr": "flip_x",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Flip X"),
                "tip": _("Flip the X axis for the device"),
                "section": "_10_Parameters",
                "subsection": "_10_Axis corrections",
            },
            {
                "attr": "flip_y",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Flip Y"),
                "tip": _("Flip the Y axis for the device"),
                "section": "_10_Parameters",
                "subsection": "_10_Axis corrections",
            },
            {
                "attr": "swap_xy",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Swap XY"),
                "tip": _("Swap the X and Y axis for the device"),
                "section": "_10_Parameters",
                "subsection": "_10_Axis corrections",
            },
            {
                "attr": "interp",
                "object": self,
                "default": 5,
                "type": int,
                "label": _("Curve Interpolation"),
                "section": "_10_Parameters",
                "tip": _("Number of curve interpolation points"),
            },
            {
                "attr": "mock",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Run mock-usb backend"),
                "tip": _(
                    "This starts connects to fake software laser rather than real one for debugging."
                ),
                "section": "_00_General",
                "priority": "30",
            },
            {
                "attr": "machine_index",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Machine index to select"),
                "tip": _(
                    "Which machine should we connect to? -- Leave at 0 if you have 1 machine."
                ),
                "section": "_00_General",
            },
            {
                "attr": "file_index",
                "object": self,
                "default": 0,
                "type": int,
                "style": "combo",
                "choices": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                "label": _("Output File"),
                "tip": _(
                    "File0 is default and instantly executes. The remaining files need to be sent and told to start"
                ),
                "section": "_30_Output",
                "signals": "newly_file_index",
            },
            {
                "attr": "autoplay",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Automatically Start"),
                "tip": _(
                    "Automatically start the job when the output file is sent. You can send without execution if this is unchecked."
                ),
                "section": "_30_Output",
                "signals": "newly_autoplay",
            },
            {
                "attr": "signal_updates",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Device Position"),
                "tip": _(
                    "Do you want to see some indicator about the current device position?"
                ),
                "section": "_95_" + _("Screen updates"),
                "signals": "restart",
            },
        ]
        self.register_choices("newly", choices)

        choices = [
            {
                "attr": "h_dpi",
                "object": self,
                "default": 1000,
                "type": float,
                "label": _("Horizontal DPI"),
                "tip": _("The Dots-Per-Inch across the X-axis"),
                "section": "_10_Parameters",
                "subsection": "_20_Axis DPI",
            },
            {
                "attr": "v_dpi",
                "object": self,
                "default": 1000,
                "type": float,
                "label": _("Vertical DPI"),
                "tip": _("The Dots-Per-Inch across the Y-axis"),
                "section": "_10_Parameters",
                "subsection": "_20_Axis DPI",
            },
            {
                "attr": "h_backlash",
                "object": self,
                "default": 0,
                "type": float,
                "label": _("Horizontal Backlash"),
                "tip": _("Backlash amount for the laser."),
                "trailer": "mm",
                "section": "_10_Parameters",
                "subsection": "_30_Backlash",
            },
            {
                "attr": "v_backlash",
                "object": self,
                "default": 0,
                "type": float,
                "label": _("Vertical Backlash"),
                "tip": _("Backlash amount for the laser."),
                "trailer": "mm",
                "section": "_10_Parameters",
                "subsection": "_30_Backlash",
            },
            {
                "attr": "max_power",
                "object": self,
                "default": 20.0,
                "type": float,
                "label": _("Max Power"),
                "trailer": "%",
                "tip": _(
                    "Maximum laser power, all other power will be a scale of this amount"
                ),
                "section": "_10_Parameters",
                "subsection": "_40_Power",
            },
            {
                "attr": "max_pulse_power",
                "object": self,
                "default": 65.0,
                "type": float,
                "label": _("Max Pulse Power"),
                "trailer": "%",
                "tip": _("What max power level should pulses be fired at?"),
                "section": "_10_Parameters",
                "subsection": "_45_Pulse",
            },
            {
                "attr": "pwm_enabled",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("PWM Power"),
                "tip": _("Power Width Modulation enabled for device."),
                "section": "_10_Parameters",
                "subsection": "_40_Power",
            },
            {
                "attr": "pwm_frequency",
                "object": self,
                "default": 2,
                "type": int,
                "style": "combo",
                "choices": [1, 2, 3, 4, 5, 10, 20, 50, 75, 100, 200, 255],
                "conditional": (self, "pwm_enabled"),
                "label": _("PWM Frequency"),
                "trailer": "khz",
                "tip": _(
                    "Set the frequency of the PWM, how often the pulse width cycles"
                ),
                "section": "_10_Parameters",
                "subsection": "_40_Power",
            },
            {
                "attr": "cut_dc",
                "object": self,
                "default": 100,
                "type": int,
                "label": _("Cut DC"),
                "tip": _("Set the current for the cut movements."),
                "section": "_10_Parameters",
                "subsection": "_40_Current",
            },
            {
                "attr": "move_dc",
                "object": self,
                "default": 100,
                "type": int,
                "label": _("Move DC"),
                "tip": _("Set the current for the regular movements."),
                "section": "_10_Parameters",
                "subsection": "_40_Current",
            },
            {
                "attr": "max_raster_jog",
                "object": self,
                "default": 15,
                "type": int,
                "label": _("Maximum Raster Jog"),
                "tip": _(
                    "Maximum distance allowed to be done during a raster step/jog"
                ),
                "section": "_10_Parameters",
                "subsection": "_50_Raster",
            },
        ]
        self.register_choices("newly-specific", choices)

        choices = [
            {
                "attr": "default_cut_speed",
                "object": self,
                "default": 15.0,
                "type": float,
                "trailer": "mm/s",
                "label": _("Cut Speed"),
                "tip": _("How fast do we cut?"),
                "subsection": "_10_Cut",
            },
            {
                "attr": "default_cut_power",
                "object": self,
                "default": 1000.0,
                "type": float,
                "label": _("Cut Power"),
                "trailer": "/1000",
                "tip": _("What power level do we cut at?"),
                "subsection": "_10_Cut",
            },
            {
                "attr": "default_on_delay",
                "object": self,
                "default": 0,
                "type": float,
                "trailer": "ms",
                "label": _("On Delay"),
                "tip": _("Delay for laser on?"),
                "subsection": "_20_Timings",
            },
            {
                "attr": "default_off_delay",
                "object": self,
                "default": 0,
                "type": float,
                "trailer": "ms",
                "label": _("Off Delay"),
                "tip": _("Delay for laser off?"),
                "subsection": "_20_Timings",
            },
            {
                "attr": "default_raster_speed",
                "object": self,
                "default": 200.0,
                "type": float,
                "trailer": "mm/s",
                "label": _("Raster Speed"),
                "tip": _("How fast do we raster?"),
                "subsection": "_30_Raster",
            },
            {
                "attr": "default_raster_power",
                "object": self,
                "default": 1000.0,
                "type": float,
                "label": _("Raster Power"),
                "trailer": "%",
                "tip": _("At what power level do we raster?"),
                "subsection": "_30_Raster",
            },
            {
                "attr": "moving_speed",
                "object": self,
                "default": 100.0,
                "type": float,
                "trailer": "mm/s",
                "label": _("Moving Speed"),
                "tip": _("Moving speed while not cutting?"),
                "subsection": "_40_Moving",
            },
            {
                "attr": "default_corner_speed",
                "object": self,
                "default": 20.0,
                "type": float,
                "trailer": "mm/s",
                "label": _("Corner Speed"),
                "tip": _("Speed to move from acceleration corner to corner?"),
                "subsection": "_40_Moving",
            },
            {
                "attr": "default_acceleration_distance",
                "object": self,
                "default": 8.0,
                "type": float,
                "trailer": "mm",
                "label": _("Acceleration Distance"),
                "tip": _("Distance to use to ramp up to speed for movement?"),
                "subsection": "_40_Moving",
            },
            {
                "attr": "rect_speed",
                "object": self,
                "default": 100.0,
                "type": float,
                "trailer": "mm/s",
                "label": _("Rect Speed"),
                "tip": _("Speed to perform frame trace?"),
                "subsection": "_50_Framing",
            },
            {
                "attr": "rect_power",
                "object": self,
                "default": 0.0,
                "type": float,
                "trailer": "/1000",
                "label": _("Rect Power"),
                "tip": _("Power usage for draw frame operation?"),
                "subsection": "_50_Framing",
            },
        ]
        self.register_choices("newly-global", choices)

        choices = [
            {
                "attr": "device_coolant",
                "object": self,
                "default": "",
                "type": str,
                "style": "option",
                "label": _("Coolant"),
                "tip": _(
                    "Does this device has a method to turn on / off a coolant associated to it?"
                ),
                "section": "_99_" + _("Coolant Support"),
                "dynamic": self.cool_helper,
                "signals": "coolant_changed",
            },
        ]
        self.register_choices("coolant", choices)

        # This device prefers to display power level in percent
        self.setting(bool, "use_percent_for_power_display", True)

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

        self.kernel.root.coolant.claim_coolant(self, self.device_coolant)

        self.state = 0
        self.view = View(
            self.bedwidth,
            self.bedheight,
            dpi_x=self.h_dpi,
            dpi_y=self.v_dpi,
        )
        self.realize()
        self.spooler = Spooler(self)
        self.driver = NewlyDriver(self)
        self.spooler.driver = self.driver

        self.add_service_delegate(self.spooler)

        self.viewbuffer = ""

        # Sort the entries for the rasterchart
        self.speedchart.sort(key=lambda x: x["speed"])

        @self.console_command(
            "estop",
            help=_("stops the current job, deletes the spooler"),
            input_type=None,
        )
        def estop(command, channel, _, data=None, remainder=None, **kwgs):
            channel("Stopping Job")
            if self.job is not None:
                self.job.stop()
            self.spooler.clear_queue()
            self.driver.reset()

        @self.console_command(
            "pause",
            help=_("Pauses the currently running job"),
        )
        def pause(command, channel, _, data=None, remainder=None, **kwgs):
            if self.driver.paused:
                channel("Resuming current job")
            else:
                channel("Pausing current job")
            self.driver.pause()
            self.signal("pause")

        @self.console_command(
            "resume",
            help=_("Resume the currently running job"),
        )
        def resume(command, channel, _, data=None, remainder=None, **kwgs):
            channel("Resume the current job")
            self.driver.resume()
            self.signal("pause")

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
        def pulse(command, channel, _, time=None, idonotlovemyhouse=False, **kwgs):
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
            if self.spooler.is_idle:
                self.spooler.command("pulse", time)
                channel(_("Pulse laser for {time} milliseconds").format(time=time))
            else:
                channel(_("Pulse laser failed: Busy"))
            return

        @self.console_command(
            "usb_connect",
            help=_("connect usb"),
        )
        def usb_connect(command, channel, _, data=None, remainder=None, **kwgs):
            self.spooler.command("connect", priority=1)

        @self.console_command(
            "usb_disconnect",
            help=_("connect usb"),
        )
        def usb_disconnect(command, channel, _, data=None, remainder=None, **kwgs):
            self.spooler.command("disconnect", priority=1)

        @self.console_command("usb_abort", help=_("Stops USB retries"))
        def usb_abort(command, channel, _, **kwgs):
            self.spooler.command("abort_retry", priority=1)

        @self.console_argument("filename", type=str)
        @self.console_command("save_job", help=_("save job export"), input_type="plan")
        def newly_save(channel, _, filename, data=None, **kwgs):
            if filename is None:
                raise CommandSyntaxError
            try:
                with open(filename, "wb") as f:
                    driver = NewlyDriver(self, force_mock=True)
                    job = LaserJob(
                        filename, list(data.plan), driver=driver, outline=data.outline
                    )

                    def write(index, data):
                        f.write(data)

                    driver.connection.connect_if_needed()
                    driver.connection.connection.write = write
                    driver.job_start(job)
                    job.execute()
                    driver.job_finish(job)

            except (PermissionError, OSError):
                channel(_("Could not save: {filename}").format(filename=filename))

        @self.console_command(
            "raw",
            help=_("sends raw data exactly as composed"),
        )
        def newly_raw(
            channel,
            _,
            remainder=None,
            **kwgs,
        ):
            """
            Raw for newly performs raw actions and sends these commands directly to the laser.
            """
            if remainder is not None:
                if "\\x" in remainder:
                    for i in range(256):
                        remainder = remainder.replace(f"\\x{i:02X}", chr(i))
                    self.driver.connection.raw(remainder)
                else:
                    self.driver.connection.raw(remainder)
                channel(f"Raw: {remainder}")

        @self.console_argument("file_index", type=int)
        @self.console_command(
            "move_frame",
            help=_("sends the newly move_frame command"),
            all_arguments_required=True,
        )
        def move_rect(file_index, **kwgs):
            try:
                self.driver.connection.move_frame(file_index)
            except ConnectionRefusedError:
                self.signal(
                    "warning",
                    _("Connection was aborted. Manual connection required."),
                    _("Not Connected"),
                )

        @self.console_argument("file_index", type=int)
        @self.console_command(
            "select_file",
            help=_("Sets the default file index to use"),
            all_arguments_required=True,
        )
        def set_file_index(
            command, channel, _, file_index=None, data=None, remainder=None, **kwgs
        ):
            old_value = self.file_index
            if file_index is None or file_index < 0 or file_index >= 10:
                file_index = 0
            self.file_index = file_index
            channel(
                f"File index was set to #{file_index} (previous value: {old_value})"
            )
            # Let propertypanels know that this value was updated
            self.signal("file_index", file_index, self)

        @self.console_argument("file_index", type=int)
        @self.console_command(
            "draw_frame",
            help=_("sends the newly draw_frame command"),
            all_arguments_required=True,
        )
        def draw_rect(file_index, **kwgs):
            try:
                self.driver.connection.draw_frame(file_index)
            except ConnectionRefusedError:
                self.signal(
                    "warning",
                    _("Connection was aborted. Manual connection required."),
                    _("Not Connected"),
                )

        @self.console_argument("file_index", type=int)
        @self.console_command(
            "replay",
            help=_("sends the file replay command"),
            all_arguments_required=True,
        )
        def replay(file_index, **kwgs):
            try:
                self.driver.connection.replay(file_index)
            except ConnectionRefusedError:
                self.signal(
                    "warning",
                    _("Connection was aborted. Manual connection required."),
                    _("Not Connected"),
                )

    @property
    def safe_label(self):
        """
        Provides a safe label without spaces or / which could cause issues when used in timer or other names.
        @return:
        """
        if not hasattr(self, "label"):
            return self.name
        name = self.label.replace(" ", "-")
        return name.replace("/", "-")

    def service_attach(self, *args, **kwargs):
        self.realize()

    @signal_listener("flip_x")
    @signal_listener("flip_y")
    @signal_listener("swap_xy")
    @signal_listener("v_dpi")
    @signal_listener("h_dpi")
    @signal_listener("home_corner")
    @signal_listener("user_margin_x")
    @signal_listener("user_margin_y")
    def realize(self, origin=None, *args):
        if origin is not None and origin != self.path:
            return
        corner = self.setting(str, "home_corner")
        home_dx = 0
        home_dy = 0
        if corner == "auto":
            pass
        elif corner == "top-left":
            home_dx = 1 if self.flip_x else 0
            home_dy = 1 if self.flip_y else 0
        elif corner == "top-right":
            home_dx = 0 if self.flip_x else 1
            home_dy = 1 if self.flip_y else 0
        elif corner == "bottom-left":
            home_dx = 1 if self.flip_x else 0
            home_dy = 0 if self.flip_y else 1
        elif corner == "bottom-right":
            home_dx = 0 if self.flip_x else 1
            home_dy = 0 if self.flip_y else 1
        elif corner == "center":
            home_dx = 0.5
            home_dy = 0.5
        self.view.set_dims(self.bedwidth, self.bedheight)
        self.view.set_margins(self.user_margin_x, self.user_margin_y)
        self.view.dpi_x = self.h_dpi
        self.view.dpi_y = self.v_dpi
        self.view.transform(
            flip_x=self.flip_x,
            flip_y=self.flip_y,
            swap_xy=self.swap_xy,
            origin_x=home_dx,
            origin_y=home_dy,
        )
        self.signal("view;realized")

    def location(self):
        return "mock" if self.mock else "usb"

    @property
    def current(self):
        """
        @return: the location in units for the current known position.
        """
        return self.view.iposition(self.driver.native_x, self.driver.native_y)

    @property
    def native(self):
        """
        @return: the location in device native units for the current known position.
        """
        return self.driver.native_x, self.driver.native_y

    def cool_helper(self, choice_dict):
        self.kernel.root.coolant.coolant_choice_helper(self)(choice_dict)
