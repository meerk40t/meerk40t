"""
GRBL Device

Defines the interactions between the device service and the meerk40t's viewport.
Registers relevant commands and options.
"""
from time import sleep

from meerk40t.kernel import CommandSyntaxError, Service

from ..core.laserjob import LaserJob
from ..core.spoolers import Spooler
from ..core.units import UNITS_PER_MIL, Length, ViewPort
from .controller import GrblController
from .driver import GRBLDriver


class GRBLDevice(Service, ViewPort):
    """
    GRBLDevice is driver for the Gcode Controllers
    """

    def __init__(self, kernel, path, *args, choices=None, **kwargs):
        self.permit_tcp = True
        self.permit_serial = True

        Service.__init__(self, kernel, path)
        self.name = "GRBLDevice"
        self.extension = "gcode"
        if choices is not None:
            for c in choices:
                attr = c.get("attr")
                default = c.get("default")
                if attr is not None and default is not None:
                    setattr(self, attr, default)

        # self.redlight_preferred = False

        self.setting(str, "label", path)
        _ = self._
        choices = [
            {
                "attr": "bedwidth",
                "object": self,
                "default": "235mm",
                "type": Length,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
                "subsection": "Dimensions",
                "signals": "bedsize",
                "nonzero": True,
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": "235mm",
                "type": Length,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
                "subsection": "Dimensions",
                "signals": "bedsize",
                "nonzero": True,
            },
            {
                "attr": "scale_x",
                "object": self,
                "default": 1.000,
                "type": float,
                "label": _("X-Axis"),
                "tip": _(
                    "Scale factor for the X-axis. Board units to actual physical units."
                ),
                "subsection": "Scale",
            },
            {
                "attr": "scale_y",
                "object": self,
                "default": 1.000,
                "type": float,
                "label": _("Y-Axis"),
                "tip": _(
                    "Scale factor for the Y-axis. Board units to actual physical units."
                ),
                "subsection": "Scale",
            },
            {
                "attr": "flip_x",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Flip X"),
                "tip": _(
                    "+X is standard for grbl but sometimes settings can flip that."
                ),
                "subsection": "_10_Flip Axis",
                "signals": "bedsize",
            },
            {
                "attr": "flip_y",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Flip Y"),
                "tip": _(
                    "-Y is standard for grbl but sometimes settings can flip that."
                ),
                "subsection": "_10_Flip Axis",
                "signals": "bedsize",
            },
            {
                "attr": "swap_xy",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Swap XY"),
                "tip": _(
                    "Swaps the X and Y axis. This happens before the FlipX and FlipY."
                ),
                "subsection": "_20_Axis corrections",
                "signals": "bedsize",
            },
            {
                "attr": "home_bottom",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Home Bottom"),
                "tip": _("Indicates the device Home is on the bottom"),
                "subsection": "_30_Home position",
                "signals": "bedsize",
            },
            {
                "attr": "home_right",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Home Right"),
                "tip": _("Indicates the device Home is at the right side"),
                "subsection": "_30_Home position",
                "signals": "bedsize",
            },
        ]
        self.register_choices("bed_dim", choices)
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
                "attr": "rotary_mirror_x",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mirror X"),
                "tip": _("Mirror the elements on the X-Axis"),
                "conditional": (self, "rotary_active"),
                "subsection": _("Mirror Output"),
            },
            {
                "attr": "rotary_mirror_y",
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

        self.settings = dict()
        self.state = 0

        def update(choice_dict):
            """
            Sets the choices and display of the serial_port values dynamically
            @param choice_dict:
            @return:
            """
            try:
                import serial.tools.list_ports

                ports = serial.tools.list_ports.comports()
                serial_interface = [x.device for x in ports]
                serial_interface_display = [str(x) for x in ports]

                choice_dict["choices"] = serial_interface
                choice_dict["display"] = serial_interface_display
            except ImportError:
                choice_dict["choices"] = ["UNCONFIGURED"]
                choice_dict["display"] = ["pyserial-not-installed"]

        choices = [
            {
                "attr": "serial_port",
                "object": self,
                "default": "UNCONFIGURED",
                "type": str,
                "style": "option",
                "label": "",
                "tip": _("What serial interface does this device connect to?"),
                "section": "_10_Serial Interface",
                "subsection": "_00_",
                "dynamic": update,
            },
            {
                "attr": "baud_rate",
                "object": self,
                "default": 115200,
                "type": int,
                "label": _("Baud Rate"),
                "tip": _("Baud Rate of the device"),
                "section": "_10_Serial Interface",
                "subsection": "_00_",
            },
        ]
        if self.permit_serial:
            self.register_choices("serial", choices)

        choices = [
            {
                "attr": "address",
                "object": self,
                "default": "localhost",
                "type": str,
                # "style": "address",
                "tip": _("What serial interface does this device connect to?"),
            },
            {
                "attr": "port",
                "object": self,
                "default": 23,
                "type": int,
                "label": _("Port"),
                "tip": _("TCP Port of the GRBL device"),
            },
        ]
        if self.permit_tcp:
            self.register_choices("tcp", choices)

        choices = [
            {
                "attr": "interface",
                "object": self,
                "default": "serial",
                "style": "combosmall",
                "choices": ["serial", "tcp", "mock"],
                "display": [_("Serial"), _("TCP-Network"), _("mock")],
                "type": str,
                "label": _("Interface Type"),
                "tip": _("Select the interface type for the grbl device"),
                "section": "_20_Protocol",
                "signals": "update_interface",
            },
        ]
        self.register_choices("interface", choices)

        choices = [
            {
                "attr": "label",
                "object": self,
                "default": "grbl",
                "type": str,
                "label": _("Label"),
                "tip": _("What is this device called."),
                "width": 250,
                "signals": "device;renamed",
            },
            {
                "attr": "buffer_mode",
                "object": self,
                "default": "buffered",
                "type": str,
                "style": "combo",
                "choices": ["buffered", "sync"],
                "label": _("Sending Protocol"),
                "tip": _(
                    "Buffered sends data as long as the planning buffer permits it being sent. Sync requires an 'ok' between each line sent."
                ),
                "section": "_20_Protocol",
                "subsection": "_00_",
            },
            {
                "attr": "planning_buffer_size",
                "object": self,
                "default": 128,
                "type": int,
                "label": _("Planning Buffer Size"),
                "tip": _("Size of Planning Buffer"),
                "section": "_20_Protocol",
                "subsection": "_00_",
            },
            {
                "attr": "interpolate",
                "object": self,
                "default": 50,
                "type": int,
                "label": _("Curve Interpolation"),
                "tip": _("Distance of the curve interpolation in mils"),
            },
            {
                "attr": "line_end",
                "object": self,
                "default": "CR",
                "type": str,
                "style": "combosmall",
                "choices": ["CR", "LF", "CRLF"],
                "label": _("Line Ending"),
                "tip": _(
                    "CR for carriage return (\\r), LF for line feed(\\n), CRLF for both"
                ),
                "section": "_20_Protocol",
            },
            {
                "attr": "limit_buffer",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Limit the controller buffer size"),
                "tip": _("Enables the controller buffer limit."),
                "section": "_30_Controller Buffer",
            },
            {
                "attr": "max_buffer",
                "object": self,
                "default": 200,
                "trailer": _("lines"),
                "type": int,
                "label": _("Controller Buffer"),
                "tip": _(
                    "This is the limit of the controller buffer size. Prevents full writing to the controller."
                ),
                "conditional": (self, "limit_buffer"),
                "section": "_30_Controller Buffer",
            },
        ]

        self.register_choices("grbl-connection", choices)

        choices = [
            {
                "attr": "use_m3",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Use M3"),
                "tip": _(
                    "Uses M3 rather than M4 for laser start (see GRBL docs for additional info)"
                ),
            },
            {
                "attr": "has_endstops",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Device has endstops"),
                "tip": _(
                    "If the device has endstops, then the laser can home itself to this position = physical home ($H)"
                ),
            },
            {
                "attr": "use_red_dot",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Simulate reddot"),
                "tip": _(
                    "If active then you can turn on the laser at a very low power to get a visual representation "
                    + "of the current position to help with focusing and positioning. Use with care!"
                ),
                "signals": "icons",  # Update ribbonbar if needed
            },
            {
                "attr": "red_dot_level",
                "object": self,
                "default": 3,
                "type": int,
                "style": "slider",
                "min": 0,
                "max": 50,
                "label": _("Reddot Laser strength"),
                "trailer": "%",
                "tip": _(
                    "Provide the power level of the red dot indicator, needs to be under the critical laser strength to not burn the material"
                ),
                "conditional": (self, "use_red_dot"),
            },
        ]
        self.register_choices("grbl-global", choices)

        self.driver = GRBLDriver(self)
        self.controller = GrblController(self)
        self.driver.out_pipe = self.controller.write
        self.driver.out_real = self.controller.realtime

        self.spooler = Spooler(self, driver=self.driver)

        self.add_service_delegate(self.controller)
        self.add_service_delegate(self.spooler)
        self.add_service_delegate(self.driver)

        self.viewbuffer = ""

        _ = self.kernel.translation

        if self.permit_serial:
            self._register_console_serial()

        @self.console_command(
            "gcode",
            help=_("Send raw gcode to the device"),
            input_type=None,
        )
        def gcode(command, channel, _, data=None, remainder=None, **kwgs):
            if remainder is not None:
                channel(remainder)
                self.driver(remainder + self.driver.line_end)  # , real=True)
                # self.channel("grbl/send")(remainder + self.driver.line_end)

        @self.console_command(
            "gcode_realtime",
            help=_("Send raw gcode to the device (via realtime channel)"),
            input_type=None,
        )
        def gcode_realtime(command, channel, _, data=None, remainder=None, **kwgs):
            if remainder is not None:
                channel(remainder)
                self.driver(remainder + self.driver.line_end, real=True)

        @self.console_command(
            "soft_reset",
            help=_("Send realtime soft reset gcode to the device"),
            input_type=None,
        )
        def soft_reset(command, channel, _, data=None, remainder=None, **kwgs):
            self.driver.reset()
            self.signal("pipe;running", False)

        @self.console_command(
            "estop",
            help=_("Send estop to the laser"),
            input_type=None,
        )
        def estop(command, channel, _, data=None, remainder=None, **kwgs):
            self.driver.reset()
            self.signal("pipe;running", False)

        @self.console_command(
            "clear_alarm",
            help=_("Send clear_alarm to the laser"),
            input_type=None,
        )
        def clear_alarm(command, channel, _, data=None, remainder=None, **kwgs):
            self.driver.clear_alarm()
            self.signal("pipe;running", False)

        @self.console_command(
            "pause",
            help=_("Send realtime soft pause/resume gcode to the device"),
            input_type=None,
        )
        def pause(command, channel, _, data=None, remainder=None, **kwgs):
            if self.driver.paused:
                self.driver.resume()
            else:
                self.driver.pause()
            self.signal("pause")

        @self.console_command(
            "resume",
            help=_("Send realtime resume gcode to the device"),
            input_type=None,
        )
        def resume(command, channel, _, data=None, remainder=None, **kwgs):
            self.driver.resume()
            self.signal("pause")

        @self.console_command(
            "viewport_update",
            hidden=True,
            help=_("Update grbl codes for movement"),
        )
        def codes_update(**kwargs):
            self.origin_x = 1.0 if self.home_right else 0.0
            self.origin_y = 1.0 if self.home_bottom else 0.0
            self.realize()

        @self.console_option(
            "strength", "s", type=int, help="Set the dot laser strength."
        )
        @self.console_argument("off", type=str)
        @self.console_command(
            "red",
            help=_("Turns redlight on/off"),
        )
        def red_dot_on(
            command, channel, _, off=None, strength=None, remainder=None, **kwgs
        ):
            if not self.use_red_dot:
                channel("Red Dot feature is not enabled, see config")
                # self.redlight_preferred = False
                return
            if not self.spooler.is_idle:
                channel("Won't interfere with a running job, abort...")
                return
            if strength is not None:
                if strength >= 0 and strength <= 100:
                    self.red_dot_level = strength
                    channel(f"Laser strength for red dot is now: {self.red_dot_level}%")
            if off == "off":
                self.driver.laser_off()
                # self.driver.grbl("G0")
                self.driver.move_mode = 0
                # self.redlight_preferred = False
                channel("Turning off redlight.")
                self.signal("grbl_red_dot", False)
            else:
                # self.redlight_preferred = True
                # self.driver.set("power", int(self.red_dot_level / 100 * 1000))
                self.driver._clean()
                self.driver.laser_on(
                    power=int(self.red_dot_level / 100 * 1000), speed=1000
                )
                # By default any move is a G0 move which will not activate the laser,
                # so we need to switch to G1 mode:
                self.driver.move_mode = 1
                # An arbitrary move to turn the laser really on!
                # self.driver.grbl("G1")
                channel("Turning on redlight.")
                self.signal("grbl_red_dot", True)

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
                self.driver.laser_on(power=1000, speed=1000)
                sleep(time / 1000)
                self.driver.laser_off()
                label = _("Pulse laser for {time}ms").format(time=time)
                channel(label)
            else:
                channel(_("Pulse laser failed: Busy"))
            return

        @self.console_argument("filename", type=str)
        @self.console_command("save_job", help=_("save job export"), input_type="plan")
        def gcode_save(channel, _, filename, data=None, **kwargs):
            if filename is None:
                raise CommandSyntaxError
            try:
                with open(filename, "w") as f:
                    # f.write(b"(MeerK40t)\n")
                    driver = GRBLDriver(self)
                    job = LaserJob(filename, list(data.plan), driver=driver)
                    driver.out_pipe = f.write
                    driver.out_real = f.write
                    job.execute()

            except (PermissionError, OSError):
                channel(_("Could not save: {filename}").format(filename=filename))

        @self.console_command(
            "grblinterpreter", help=_("activate the grbl interpreter.")
        )
        def lhyemulator(channel, _, **kwargs):
            try:
                self.open_as("interpreter/grbl", "grblinterpreter")
                channel(
                    _("Grbl Interpreter attached to {device}").format(device=str(self))
                )
            except KeyError:
                channel(_("Interpreter cannot be attached to any device."))
            return

    def _register_console_serial(self):
        _ = self.kernel.translation

        @self.console_argument("com")
        @self.console_option("baud", "b")
        @self.console_command(
            "serial",
            help=_("link the serial connection"),
            input_type=None,
        )
        def serial_connection(
            command,
            channel,
            _,
            data=None,
            com=None,
            baud=115200,
            remainder=None,
            **kwgs,
        ):
            if com is None:
                import serial.tools.list_ports

                ports = serial.tools.list_ports.comports()

                channel("Available COM ports")
                for x in ports:
                    channel(str(x))

    def location(self):
        if self.permit_tcp and self.interface == "tcp":
            return f"{self.address}:{self.port}"
        elif self.permit_serial and self.interface == "serial":
            return f"{self.serial_port.lower()}:{self.baud_rate}"
        else:
            return "mock"

    def service_attach(self, *args, **kwargs):
        self.realize()

    @property
    def current(self):
        """
        @return: the location in scene units for the current known x value.
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

    def realize(self, origin=None):
        self.width = self.bedwidth
        self.height = self.bedheight
        self.origin_x = 1.0 if self.home_right else 0.0
        self.origin_y = 1.0 if self.home_bottom else 0.0
        super().realize()
        self.space.update_bounds(0, 0, self.width, self.height)
