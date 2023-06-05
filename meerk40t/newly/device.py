"""
Newly Device
"""
from meerk40t.core.laserjob import LaserJob
from meerk40t.core.spoolers import Spooler
from meerk40t.core.units import UNITS_PER_INCH, ViewPort
from meerk40t.kernel import CommandSyntaxError, Service, signal_listener
from meerk40t.newly.driver import NewlyDriver


class NewlyDevice(Service, ViewPort):
    """
    Newly Device
    """

    def __init__(self, kernel, path, *args, choices=None, **kwargs):
        Service.__init__(self, kernel, path)
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
                        "type": 120,
                        "label": _("Corner Speed"),
                        "width": 133,
                        "editable": True,
                    },
                ],
                "style": "chart",
                "primary": "speed",
                "label": _("Speed Chart"),
                "tip": _("Raster speed to chart."),
            },
        ]
        self.register_choices("newly-speedchart", choices)

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
                "priority": "20",
                "nonzero": True,
            },
            {
                "attr": "home_bottom",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Home Bottom"),
                "tip": _("Indicates the device Home is on the bottom"),
                "subsection": "_50_Home position",
                "signals": "bedsize",
            },
            {
                "attr": "home_right",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Home Right"),
                "tip": _("Indicates the device Home is at the right side"),
                "subsection": "_50_Home position",
                "signals": "bedsize",
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
                "signals": "bedsize",
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
                "signals": "bedsize",
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
                "attr": "interpolate",
                "object": self,
                "default": 50,
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
                "tip": _("How what power level do we raster at?"),
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
                "subsection": "_50_Rect",
            },
            {
                "attr": "rect_power",
                "object": self,
                "default": 0.0,
                "type": float,
                "trailer": "/1000",
                "label": _("Rect Power"),
                "tip": _("Power usage for draw frame operation?"),
                "subsection": "_50_Rect",
            },
        ]
        self.register_choices("newly-global", choices)

        self.state = 0

        ViewPort.__init__(
            self,
            self.bedwidth,
            self.bedheight,
            native_scale_x=UNITS_PER_INCH / self.h_dpi,
            native_scale_y=UNITS_PER_INCH / self.v_dpi,
            origin_x=1.0 if self.home_right else 0.0,
            origin_y=1.0 if self.home_bottom else 0.0,
            flip_x=self.flip_x,
            flip_y=self.flip_y,
            swap_xy=self.swap_xy,
        )
        self.spooler = Spooler(self)
        self.driver = NewlyDriver(self)
        self.spooler.driver = self.driver

        self.add_service_delegate(self.spooler)

        self.viewbuffer = ""

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
        def usb_abort(command, channel, _, **kwargs):
            self.spooler.command("abort_retry", priority=1)

        @self.console_argument("filename", type=str)
        @self.console_command("save_job", help=_("save job export"), input_type="plan")
        def newly_save(channel, _, filename, data=None, **kwargs):
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
        def move_rect(file_index, **kwargs):
            self.driver.connection.move_frame(file_index)

        @self.console_argument("file_index", type=int)
        @self.console_command(
            "draw_frame",
            help=_("sends the newly draw_frame command"),
            all_arguments_required=True,
        )
        def draw_rect(file_index, **kwargs):
            self.driver.connection.draw_frame(file_index)

        @self.console_argument("file_index", type=int)
        @self.console_command(
            "replay",
            help=_("sends the file replay command"),
            all_arguments_required=True,
        )
        def replay(file_index, **kwargs):
            self.driver.connection.replay(file_index)

        @self.console_command(
            "viewport_update",
            hidden=True,
            help=_("Update newly flips for movement"),
        )
        def codes_update(**kwargs):
            self.realize()

    def service_attach(self, *args, **kwargs):
        self.realize()

    @signal_listener("flip_x")
    @signal_listener("flip_y")
    @signal_listener("swap_xy")
    @signal_listener("v_dpi")
    @signal_listener("h_dpi")
    def realize(self, origin=None, *args):
        self.width = self.bedwidth
        self.height = self.bedheight
        self.native_scale_x = UNITS_PER_INCH / self.h_dpi
        self.native_scale_y = UNITS_PER_INCH / self.v_dpi
        super().realize()
        self.space.update_bounds(0, 0, self.width, self.height)

    @property
    def current(self):
        """
        @return: the location in nm for the current known x value.
        """
        return self.device_to_scene_position(
            self.driver.native_x,
            self.driver.native_y,
        )

    @property
    def native(self):
        """
        @return: the location in device native units for the current known position.
        """
        return self.driver.native_x, self.driver.native_y
