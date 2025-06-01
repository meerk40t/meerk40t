"""
GRBL Device

Defines the interactions between the device service and the meerk40t's viewport.
Registers relevant commands and options.
"""

from time import sleep

from meerk40t.device.devicechoices import get_effect_choices
from meerk40t.kernel import CommandSyntaxError, Service, signal_listener

from ..core.laserjob import LaserJob
from ..core.spoolers import Spooler
from ..core.units import MM_PER_INCH, Length
from ..core.view import View
from ..device.mixins import Status
from .controller import GrblController
from .driver import GRBLDriver


class GRBLDevice(Service, Status):
    """
    GRBLDevice is driver for the Gcode Controllers
    """

    def __init__(self, kernel, path, *args, choices=None, **kwargs):
        self.hardware_config = {}
        self.permit_tcp = True
        self.permit_ws = True
        self.permit_serial = True

        Service.__init__(self, kernel, path)
        Status.__init__(self)
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
                "attr": "bedwidth",
                "object": self,
                "default": "235mm",
                "type": Length,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
                "subsection": "_10_Dimensions",
                "nonzero": True,
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": "235mm",
                "type": Length,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
                "subsection": "_10_Dimensions",
                "nonzero": True,
            },
            {
                "attr": "laserspot",
                "object": self,
                "default": "0.3mm",
                "type": Length,
                "label": _("Laserspot"),
                "tip": _("Laser spot size"),
                "subsection": "_10_Dimensions",
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
                "subsection": "_20_Scale",
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
                "subsection": "_20_Scale",
            },
            {
                "attr": "user_margin_x",
                "object": self,
                "default": "0",
                "type": str,
                "label": _("X-Margin"),
                "tip": _(
                    "Margin for the X-axis. This will be a kind of unused space at the left side."
                ),
                "subsection": "_30_User Offset",
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
                "subsection": "_30_User Offset",
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
                "subsection": "_40_Flip Axis",
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
                "subsection": "_40_Flip Axis",
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
                "subsection": "_50_Axis corrections",
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
                "subsection": "_60_Home position",
            },
            {
                "attr": "supports_z_axis",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Supports Z-axis"),
                "tip": _("Does this device have a Z-axis?"),
                "subsection": "_70_Z-Axis support",
            },
            {
                "attr": "z_home_command",
                "object": self,
                "default": "$HZ",
                "type": str,
                "style": "combosmall",
                "choices": [
                    "$HZ",
                    "G28 Z",
                ],
                "exclusive": False,
                "label": _("Z-Homing"),
                "tip": _("Which command triggers the z-homing sequence"),
                "subsection": "_70_Z-Axis support",
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
        self.register_choices("bed_dim", choices)

        self.register_choices("grbl-effects", get_effect_choices(self))

        # This device prefers to display power level in percent
        self.setting(bool, "use_percent_for_power_display", True)
        # This device prefers to display speed in mm/min
        self.setting(bool, "use_mm_min_for_speed_display", False)

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
        self.view = View(
            self.bedwidth,
            self.bedheight,
            dpi_x=1000.0,
            dpi_y=1000.0,
        )
        self.view_mm = View(
            self.bedwidth,
            self.bedheight,
            dpi_x=MM_PER_INCH,
            dpi_y=MM_PER_INCH,
        )
        self.realize()
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

        from platform import system

        is_linux = system() == "Linux"
        choices = [
            {
                "attr": "serial_port",
                "object": self,
                "default": "UNCONFIGURED",
                "type": str,
                "style": "combosmall" if is_linux else "option",
                "label": "",
                "tip": _("What serial interface does this device connect to?"),
                "section": "_10_Serial Interface",
                "subsection": "_00_",
                "dynamic": update,
                "exclusive": not is_linux,
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
                "label": _("Address"),
                # "style": "address",
                "tip": _("IP address/host name of the GRBL device"),
                "signals": "update_interface",
            },
            {
                "attr": "port",
                "object": self,
                "default": 23,
                "type": int,
                "label": _("Port"),
                "tip": _("TCP Port of the GRBL device"),
                "lower": 0,
                "upper": 65535,
                "signals": "update_interface",
            },
        ]
        if self.permit_tcp:
            self.register_choices("tcp", choices)

        try:
            import websocket
        except ImportError:
            self.permit_ws = False
        choices = [
            {
                "attr": "address",
                "object": self,
                "default": "localhost",
                "type": str,
                "label": _("Address"),
                # "style": "address",
                "tip": _("IP address/host name of the GRBL device"),
                "signals": "update_interface",
            },
            {
                "attr": "port",
                "object": self,
                "default": 81,
                "type": int,
                "label": _("Port"),
                "tip": _("TCP Port of the device (usually 81)"),
                "lower": 0,
                "upper": 65535,
                "signals": "update_interface",
            },
        ]
        if self.permit_ws:
            self.register_choices("ws", choices)
        list_interfaces = []
        list_display = []
        if self.permit_serial:
            list_interfaces.append("serial")
            list_display.append(_("Serial"))
        if self.permit_tcp:
            list_interfaces.append("tcp")
            list_display.append(_("TCP-Network"))
        if self.permit_ws:
            list_interfaces.append("ws")
            list_display.append(_("WebSocket-Network"))
        list_interfaces.append("mock")
        list_display.append(_("Mock"))
        choices = [
            {
                "attr": "interface",
                "object": self,
                "default": "serial",
                "style": "combosmall",
                "choices": list_interfaces,
                "display": list_display,
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
                "attr": "use_m3",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Use M3"),
                "section": "_5_Config",
                "tip": _(
                    "Uses M3 rather than M4 for laser start (see GRBL docs for additional info)"
                ),
            },
            {
                "attr": "extended_alarm_clear",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Reset on 'Clear Alarm'"),
                "section": "_5_Config",
                "tip": _("Reset the controller too on a 'Clear Alarm' command"),
            },
            {
                "attr": "interp",
                "object": self,
                "default": 5,
                "type": int,
                "label": _("Curve Interpolation"),
                "section": "_5_Config",
                "tip": _("Distance of the curve interpolation in mils"),
            },
            {
                "attr": "has_endstops",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Device has endstops"),
                "section": "_5_Config",
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
                "section": "_10_Red Dot",
            },
            {
                "attr": "red_dot_level",
                "object": self,
                "default": 30,
                "type": int,
                "style": "slider",
                "min": 0,
                "max": 200,
                "label": _("Reddot Laser strength"),
                "trailer": "/1000",
                "tip": _(
                    "Provide the power level of the red dot indicator, needs to be under the critical laser strength to not burn the material"
                ),
                "conditional": (self, "use_red_dot"),
                "section": "_10_Red Dot",
            },
            {
                "attr": "max_vector_speed",
                "object": self,
                "default": 140,
                "type": float,
                "label": _("Max vector speed"),
                "trailer": "mm/s",
                "tip": _(
                    "What is the highest reliable speed your laser is able to perform vector operations, i.e. engraving or cutting.\n"
                    "You can finetune this in the Warning Sections of this configuration dialog."
                ),
                "section": "_20_" + _("Maximum speeds"),
                "subsection": "_10_",
            },
            {
                "attr": "max_raster_speed",
                "object": self,
                "default": 750,
                "type": float,
                "label": _("Max raster speed"),
                "trailer": "mm/s",
                "tip": _(
                    "What is the highest reliable speed your laser is able to perform raster or image operations.\n"
                    "You can finetune this in the Warning Sections of this configuration dialog."
                ),
                "section": "_20_" + _("Maximum speeds"),
                "subsection": "_10_",
            },
            {
                "attr": "rapid_speed",
                "object": self,
                "default": 600,
                "type": float,
                "label": _("Travel speed"),
                "trailer": "mm/s",
                "tip": _(
                    "What is the travel speed for your device to move from point to another."
                ),
                "section": "_25_" + _("Travel"),
                "subsection": "_10_",
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
        self.register_choices("grbl-advanced", choices)

        choices = [
            {
                "attr": "require_validator",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Require Validator"),
                "tip": _(
                    "Do not validate the connection without seeing the welcome message at start."
                ),
                "section": "_40_Validation",
            },
            {
                "attr": "welcome",
                "object": self,
                "default": "Grbl",
                "type": str,
                "label": _("Welcome Validator"),
                "tip": _(
                    "If for some reason the device needs a different welcome validator than 'Grbl' (default), for example, somewhat custom grbl-like firmware"
                ),
                "section": "_40_Validation",
            },
            {
                "attr": "reset_on_connect",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Reset on connect"),
                "tip": _(
                    "On connection, send the device a softreset message as soon as connection is established."
                ),
                "section": "_40_Validation",
            },
            {
                "attr": "boot_connect_sequence",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Check sequence on connect."),
                "tip": _("On connection, check the standard GRBL info for the device."),
                "section": "_40_Validation",
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
                "attr": "connect_delay",
                "object": self,
                "default": 0,
                "trailer": _("ms"),
                "type": int,
                "label": _("Post Connection Delay"),
                "tip": _(
                    "Delay the GRBL communications after initial connect. (Some slow boot devices may need this)"
                ),
                "section": "_40_Validation",
            },
            {
                "attr": "startup_commands",
                "object": self,
                "default": "",
                "type": str,
                "style": "multiline",
                "label": _("Startup commands"),
                "tip": _(
                    "Which commands should be sent to the device on a successful connect?"
                ),
                "section": "_40_Validation",
            },
        ]
        self.register_choices("protocol", choices)

        self.driver = GRBLDriver(self)
        self.controller = GrblController(self)
        self.driver.out_pipe = self.controller.write
        self.driver.out_real = self.controller.realtime

        self.spooler = Spooler(self, driver=self.driver)

        self.add_service_delegate(self.controller)
        self.add_service_delegate(self.spooler)
        self.add_service_delegate(self.driver)

        self.viewbuffer = ""
        self.kernel.root.coolant.claim_coolant(self, self.device_coolant)

        _ = self.kernel.translation

        if self.permit_serial:
            self._register_console_serial()

        @self.console_command(
            "z_home",
            help=_("Homes the z-Axis"),
            input_type=None,
        )
        def command_zhome(command, channel, _, data=None, remainder=None, **kwgs):
            if not self.supports_z_axis:
                channel(_("This device does not support a z-axis."))
                return
            zhome = self.z_home_command
            if not zhome:
                channel(_("There is no homing sequence defined."))
                return
            channel(_("Z-Homing..."))
            self.driver(zhome + self.driver.line_end)

        @self.console_argument("step", type=Length, help=_("Amount to move the z-axis"))
        @self.console_command(
            "z_move",
            help=_("Moves the z-Axis by the given amount"),
            input_type=None,
        )
        def command_zmove_rel(command, channel, _, data=None, step=None, **kwgs):
            if not self.supports_z_axis:
                channel(_("This device does not support a z-axis."))
                return
            if step is None:
                channel(_("No z-movement defined"))
                return
            # relative movement in mm
            gcode = f"G91 G21 Z{step.mm:.3f}"
            self.driver(gcode + self.driver.line_end)

        @self.console_argument("step", type=Length, help=_("New z-axis position"))
        @self.console_command(
            "z_move_to",
            help=_("Moves the z-Axis to the given position"),
            input_type=None,
        )
        def command_zmove_abs(command, channel, _, data=None, step=None, **kwgs):
            if not self.supports_z_axis:
                channel(_("This device does not support a z-axis."))
                return
            if step is None:
                channel(_("No z-movement defined"))
                return
            # absolute movement in mm
            gcode = f"G91 G20 Z{step.mm:.3f}"
            self.driver(gcode + self.driver.line_end)

        @self.console_command(
            ("gcode", "grbl"),
            help=_("Send raw gcode to the device"),
            input_type=None,
        )
        def gcode(command, channel, _, data=None, remainder=None, **kwgs):
            if remainder is not None:
                channel(remainder)
                self.driver(remainder + self.driver.line_end)  # , real=True)
                # self.channel("grbl/send")(remainder + self.driver.line_end)

        @self.console_command(
            ("gcode_realtime", "grbl_realtime"),
            help=_("Send raw gcode to the device (via realtime channel)"),
            input_type=None,
        )
        def gcode_realtime(command, channel, _, data=None, remainder=None, **kwgs):
            if remainder is not None:
                channel(remainder)
                self.driver(remainder + self.driver.line_end, real=True)

        @self.console_command(
            "grbl_validate",
            help=_("Force grbl validation for the connection"),
            input_type=None,
        )
        def grbl_validate(command, channel, _, data=None, remainder=None, **kwgs):
            channel(_("Forced grbl validation."))
            self.controller.force_validate()

        @self.console_command(
            "soft_reset",
            help=_("Send realtime soft reset gcode to the device"),
            input_type=None,
        )
        def soft_reset(command, channel, _, data=None, remainder=None, **kwgs):
            self.driver.reset()
            self.laser_status = "idle"

        @self.console_command(
            "estop",
            help=_("Send estop to the laser"),
            input_type=None,
        )
        def estop(command, channel, _, data=None, remainder=None, **kwgs):
            self.driver.reset()
            self.laser_status = "idle"

        @self.console_command(
            "clear_alarm",
            help=_("Send clear_alarm to the laser"),
            input_type=None,
        )
        def clear_alarm(command, channel, _, data=None, remainder=None, **kwgs):
            self.driver.clear_alarm()
            self.laser_status = "idle"

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

        @kernel.console_command(
            "+xforward",
            hidden=True,
        )
        def plus_x_forward(data, **kwgs):
            feed = 2000
            step = feed / 600
            self(f".timerright 0 0.1 .gcode $J=G91G21X{step}F{feed}")

        @kernel.console_command(
            "-xforward",
            hidden=True,
        )
        def minus_x_forward(data, **kwgs):
            self(".timerright -oq")
            # self.controller.realtime("\x85")

        @kernel.console_command(
            "+xbackward",
            hidden=True,
        )
        def plus_x_backward(data, **kwgs):
            feed = 2000
            step = feed / 600
            self(f".timerleft 0 0.1 .gcode $J=G91G21X-{step}F{feed}")

        @kernel.console_command(
            "-xbackward",
            hidden=True,
        )
        def minus_x_backward(data, **kwgs):
            self(".timerleft -oq")

        @kernel.console_command(
            "+yforward",
            hidden=True,
        )
        def plus_y_forward(data, **kwgs):
            feed = 2000
            step = feed / 600
            self(f".timertop 0 0.1 .gcode $J=G91G21Y{step}F{feed}")

        @kernel.console_command(
            "-yforward",
            hidden=True,
        )
        def minus_y_forward(data, **kwgs):
            self(".timertop -oq")
            # self.controller.realtime("\x85")

        @kernel.console_command(
            "+ybackward",
            hidden=True,
        )
        def plus_y_backward(data, **kwgs):
            feed = 2000
            step = feed / 600
            self(f".timerbottom 0 0.1 .gcode $J=G91G21Y-{step}F{feed}")

        @kernel.console_command(
            "-ybackward",
            hidden=True,
        )
        def minus_y_backward(data, **kwgs):
            self(".timerbottom -oq")
            # self.controller.realtime("\x85")

        @kernel.console_command(
            "grbl_binds",
            hidden=True,
        )
        def grbl_binds(data, **kwgs):
            self("bind a +xbackward")
            self("bind d +xforward")
            self("bind s +ybackward")
            self("bind w +yforward")

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
                if 0 <= strength <= 1000:
                    self.red_dot_level = strength
                    channel(
                        f"Laser strength for red dot is now: {self.red_dot_level/10.0}%"
                    )
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
                rapid_speed = self.setting(float, "rapid_speed", 600.0)
                self.driver.laser_on(power=int(self.red_dot_level), speed=rapid_speed)
                # By default, any move is a G0 move which will not activate the laser,
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
        def gcode_save(channel, _, filename, data=None, **kwgs):
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
        def grblinterpreter(channel, _, **kwgs):
            try:
                self.open_as("interpreter/grbl", "grblinterpreter")
                channel(
                    _("Grbl Interpreter attached to {device}").format(device=str(self))
                )
            except KeyError:
                channel(_("Interpreter cannot be attached to any device."))
            return

        @self.console_argument("index", type=int, help=_("macro to run (1-5)."))
        @self.console_command(
            "macro",
            help=_("Send a predefined macro to the device."),
        )
        def run_macro(command, channel, _, index=None, remainder=None, **kwargs):
            for idx in range(5):
                macrotext = self.setting(str, f"macro_{idx}", "")
            if index is None:
                for idx in range(5):
                    macrotext = self.setting(str, f"macro_{idx}", "")
                    channel(f"Content of macro {idx + 1}:")
                    for no, line in enumerate(macrotext.splitlines()):
                        channel(f"{no:2d}: {line}")
                return
            err = True
            try:
                macro_index = int(index) - 1
                if 0 <= macro_index <= 4:
                    err = False
            except ValueError:
                pass
            if err:
                channel(f"Invalid macro-number '{index}', valid: 1-5")
            if remainder is not None:
                remainder.strip()
            # channel(f"Remainder: {remainder}")
            if remainder:
                channel(f"Redefining macro {index} to:")
                macrotext = remainder.replace("|", "\n")
                for line in macrotext.splitlines():
                    channel(line)
                setattr(self, f"macro_{macro_index}", macrotext)
                return

            macrotext = self.setting(str, f"macro_{macro_index}", "")
            # channel(f"{macro_index}: {macrotext}")
            for line in macrotext.splitlines():
                channel(f"> {line}")
                if line.startswith("#"):
                    continue
                self.driver(f"{line}{self.driver.line_end}")

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
        if self.permit_ws and self.interface == "ws":
            return f"ws://{self.address}:{self.port}"
        elif self.permit_serial and self.interface == "serial":
            return f"{self.serial_port.lower()}:{self.baud_rate}"
        else:
            return "mock"

    def service_attach(self, *args, **kwargs):
        self.realize()

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

    @signal_listener("scale_x")
    @signal_listener("scale_y")
    @signal_listener("bedwidth")
    @signal_listener("bedheight")
    @signal_listener("home_corner")
    @signal_listener("flip_x")
    @signal_listener("flip_y")
    @signal_listener("swap_xy")
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
        self.view.transform(
            user_scale_x=self.scale_x,
            user_scale_y=self.scale_y,
            flip_x=self.flip_x,
            flip_y=self.flip_y,
            swap_xy=self.swap_xy,
            origin_x=home_dx,
            origin_y=home_dy,
        )

        self.view_mm.set_dims(self.bedwidth, self.bedheight)
        self.view_mm.transform(
            user_scale_x=self.scale_x,
            user_scale_y=self.scale_y,
            flip_x=self.flip_x,
            flip_y=self.flip_y,
            swap_xy=self.swap_xy,
            origin_x=home_dx,
            origin_y=home_dy,
        )

        # x, y = self.view.position(0, 0)
        # print (f"Test for 0,0 gives: {x:.2f}, {y:.2f}")
        # x, y = self.view.iposition(x, y)
        # print (f"Reverse gives: {x:.2f}, {y:.2f}")
        self.signal("view;realized")

    def cool_helper(self, choice_dict):
        self.kernel.root.coolant.coolant_choice_helper(self)(choice_dict)

    def get_raster_instructions(self):
        return {
            "gantry": True,
        }
