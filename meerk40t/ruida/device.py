"""
Ruida Device

Ruida device interfacing. We do not send or interpret ruida code, but we can emulate ruidacode into cutcode and read
ruida files (*.rd) and turn them likewise into cutcode.
"""
from meerk40t.core.view import View
from meerk40t.device.devicechoices import get_effect_choices
from meerk40t.kernel import CommandSyntaxError, Service, signal_listener

from ..core.laserjob import LaserJob
from ..core.spoolers import Spooler
from ..core.units import Length, uM_PER_INCH
from ..device.mixins import Status
from .driver import RuidaDriver
from .mock_connection import MockConnection
from .serial_connection import SerialConnection
from .tcp_connection import TCPConnection
from .udp_connection import UDPConnection


class RuidaDevice(Service):
    """
    RuidaDevice is driver for the Ruida Controllers
    """

    def __init__(self, kernel, path, *args, choices=None, **kwgs):
        Service.__init__(self, kernel, path)
        Status.__init__(self)
        self.name = "RuidaDevice"
        self.extension = "rd"

        if choices is not None:
            for c in choices:
                attr = c.get("attr")
                default = c.get("default")
                if attr is not None and default is not None:
                    setattr(self, attr, default)

        # self.setting(str, "label", path)

        _ = self._
        choices = [
            {
                "attr": "label",
                "object": self,
                "default": path,
                "type": str,
                "label": _("Label"),
                "tip": _("What is this device called."),
                "section": "_00_General",
                "priority": "10",
            },
            {
                "attr": "bedwidth",
                "object": self,
                "default": "24in",
                "type": Length,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
                "nonzero": True,
                "section": "_10_" + _("Configuration"),
                "subsection": "_10_Dimensions",
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": "16in",
                "type": Length,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
                "nonzero": True,
                "section": "_10_" + _("Configuration"),
                "subsection": "_10_Dimensions",
            },
            {
                "attr": "laserspot",
                "object": self,
                "default": "0.3mm",
                "type": Length,
                "label": _("Laserspot"),
                "tip": _("Laser spot size"),
                "section": "_10_" + _("Configuration"),
                "subsection": "_10_Dimensions",
                "nonzero": True,
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
                "section": "_10_" + _("Configuration"),
                "subsection": "_20_User Scale",
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
                "section": "_10_" + _("Configuration"),
                "subsection": "_20_User Scale",
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
                # _("User Offset")
                "section": "_10_" + _("Configuration"),
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
                "section": "_10_" + _("Configuration"),
                "subsection": "_30_User Offset",
            },
            {
                "attr": "flip_x",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Flip X"),
                "tip": _("Flip the X axis for the device"),
                "section": "_10_" + _("Configuration"),
                "subsection": "_40_Axis corrections",
            },
            {
                "attr": "flip_y",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Flip Y"),
                "tip": _("Flip the Y axis for the device"),
                "section": "_10_" + _("Configuration"),
                "subsection": "_40_Axis corrections",
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
                "section": "_10_" + _("Configuration"),
                "subsection": "_50_" + _("Home position"),
            },
            {
                "attr": "interpolate",
                "object": self,
                "default": 500,
                "type": int,
                "trailer": "μm",
                "label": _("Curve Interpolation"),
                "section": "_10_Parameters",
                "tip": _("Native units interpolation points."),
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
        choices = [
            {
                "attr": "default_power",
                "object": self,
                "default": 20.0,
                "type": float,
                "label": _("Laser Power"),
                "trailer": "%",
                "tip": _("What power level do we cut at?"),
            },
            {
                "attr": "default_speed",
                "object": self,
                "default": 40.0,
                "type": float,
                "trailer": "mm/s",
                "label": _("Cut Speed"),
                "tip": _("How fast do we cut?"),
            },
        ]
        self.register_choices("ruida-global", choices)

        self.register_choices("ruida-effects", get_effect_choices(self))

        choices = [
            {
                "attr": "magic",
                "object": self,
                "default": 0x88,
                "type": int,
                "label": _("Swizzle Magic Number"),
                "tip": _("Swizzle value to communicate with laser."),
            },
        ]
        self.register_choices("ruida-magic", choices)

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
        self.register_choices("serial", choices)

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

        self.setting(str, "interface", "usb")
        self.setting(int, "packet_count", 0)
        self.setting(str, "serial", None)
        self.setting(str, "address", "localhost")

        self.driver = RuidaDriver(self)

        self.spooler = Spooler(self, driver=self.driver)
        self.add_service_delegate(self.spooler)
        self.add_service_delegate(self.driver)
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
        self.view = View(self.bedwidth, self.bedheight, dpi=uM_PER_INCH)
        self.realize()
        self.state = 0

        self.viewbuffer = ""

        _ = self.kernel.translation

        self.interface_mock = MockConnection(self)
        self.interface_udp = UDPConnection(self)
        self.interface_tcp = TCPConnection(self)
        self.interface_usb = SerialConnection(self)
        self.active_interface = None

        self.kernel.root.coolant.claim_coolant(self, self.device_coolant)

        @self.console_command(
            "interface_update",
            hidden=True,
            help=_("Updates interface state for the device."),
        )
        def interface_update(command, channel, _, data=None, **kwargs):
            if self.interface == "mock":
                self.active_interface = self.interface_mock
                self.driver.controller.write = self.interface_mock.write
            elif self.interface == "udp":
                self.active_interface = self.interface_udp
                self.driver.controller.write = self.interface_udp.write
            elif self.interface == "tcp":
                # Special tcp out to lightburn bridge et al.
                self.active_interface = self.interface_tcp
                self.driver.controller.write = self.interface_tcp.write
            elif self.interface == "usb":
                self.active_interface = self.interface_usb
                self.driver.controller.write = self.interface_usb.write

        @self.console_command(("estop", "abort"), help=_("Abort Job"))
        def pipe_abort(command, channel, _, data=None, **kwargs):
            self.driver.reset()
            channel(_("Emergency Stop."))
            self.signal("pipe;running", False)

        @self.console_command(
            "pause",
            help=_("realtime pause/resume of the machine"),
        )
        def realtime_pause(command, channel, _, data=None, **kwargs):
            if self.driver.paused:
                self.driver.resume()
            else:
                self.driver.pause()
            self.signal("pause")

        @self.console_command(
            "ruida_connect",
            hidden=True,
            help=_("Connects to the device."),
        )
        def ruida_connect(command, channel, _, data=None, **kwargs):
            if not self.connected:
                try:
                    self.active_interface.open()
                except Exception as e:
                    channel(f"Could not establish the connection: {e}")

        @self.console_command(
            "ruida_disconnect",
            hidden=True,
            help=_("Disconnects from the device."),
        )
        def ruida_disconnect(command, channel, _, data=None, **kwargs):
            if self.connected:
                self.active_interface.close()
                channel("Connection closed")

        @self.console_command(
            "focusz",
            hidden=True,
            help=_("Initiates a FocusZ Operation"),
        )
        def focusz(command, channel, _, data=None, **kwargs):
            self.driver.focusz()

        @kernel.console_command(
            "+xforward",
            hidden=True,
        )
        def plus_x_forward(command, channel, _, data=None, **kwgs):
            pipe = self.driver.controller.write
            job = self.driver.controller.job
            job.keydown_x_right(pipe)

        @kernel.console_command(
            "-xforward",
            hidden=True,
        )
        def minus_x_forward(command, channel, _, data=None, **kwgs):
            pipe = self.driver.controller.write
            job = self.driver.controller.job
            job.keyup_x_right(pipe)

        @kernel.console_command(
            "+xbackward",
            hidden=True,
        )
        def plus_x_backward(data, **kwgs):
            pipe = self.driver.controller.write
            job = self.driver.controller.job
            job.keydown_x_left(pipe)

        @kernel.console_command(
            "-xbackward",
            hidden=True,
        )
        def minus_x_backward(data, **kwgs):
            pipe = self.driver.controller.write
            job = self.driver.controller.job
            job.keyup_x_left(pipe)

        @kernel.console_command(
            "+yforward",
            hidden=True,
        )
        def plus_y_forward(data, **kwgs):
            pipe = self.driver.controller.write
            job = self.driver.controller.job
            job.keydown_y_bottom(pipe)

        @kernel.console_command(
            "-yforward",
            hidden=True,
        )
        def minus_y_forward(data, **kwgs):
            pipe = self.driver.controller.write
            job = self.driver.controller.job
            job.keyup_y_bottom(pipe)

        @kernel.console_command(
            "+ybackward",
            hidden=True,
        )
        def plus_y_backward(data, **kwgs):
            pipe = self.driver.controller.write
            job = self.driver.controller.job
            job.keydown_y_top(pipe)

        @kernel.console_command(
            "-ybackward",
            hidden=True,
        )
        def minus_y_backward(data, **kwgs):
            pipe = self.driver.controller.write
            job = self.driver.controller.job
            job.keyup_y_top(pipe)

        @kernel.console_command(
            "+zforward",
            hidden=True,
        )
        def plus_z_forward(data, **kwgs):
            pipe = self.driver.controller.write
            job = self.driver.controller.job
            job.keydown_z_down(pipe)

        @kernel.console_command(
            "-zforward",
            hidden=True,
        )
        def minus_z_backward(data, **kwgs):
            pipe = self.driver.controller.write
            job = self.driver.controller.job
            job.keyup_z_down(pipe)

        @kernel.console_command(
            "+zbackward",
            hidden=True,
        )
        def plus_z_backward(data, **kwgs):
            pipe = self.driver.controller.write
            job = self.driver.controller.job
            job.keydown_z_up(pipe)

        @kernel.console_command(
            "-zbackward",
            hidden=True,
        )
        def minus_z_backward(data, **kwgs):
            pipe = self.driver.controller.write
            job = self.driver.controller.job
            job.keyup_z_up(pipe)

        @kernel.console_command(
            "ruida_binds",
            hidden=True,
        )
        def ruida_binds(data, **kwgs):
            self("bind a +xbackward")
            self("bind d +xforward")
            self("bind s +ybackward")
            self("bind w +yforward")

        @self.console_argument("filename", type=str)
        @self.console_option(
            "magic",
            "m",
            type=int,
            default=-1,
            help=_("magic number used to encode the file"),
        )
        @self.console_command("save_job", help=_("save job export"), input_type="plan")
        def ruida_save(channel, _, filename, magic, data=None, **kwargs):
            if filename is None:
                raise CommandSyntaxError
            try:
                with open(filename, "wb") as f:
                    if magic == -1:
                        magic = self.magic
                    driver = RuidaDriver(self)
                    job = LaserJob(filename, list(data.plan), driver=driver)

                    driver.controller.write = f.write
                    driver.controller.job.set_magic(magic)

                    driver.job_start(job)
                    job.execute()
                    driver.job_finish(job)

            except (PermissionError, OSError):
                channel(_("Could not save: {filename}").format(filename=filename))

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

    @property
    def tcp_address(self):
        return self.address

    @property
    def tcp_port(self):
        return 5005

    def location(self):
        if self.interface == "mock":
            return "mock"
        elif self.interface == "udp":
            return "udp, port 40200"
        elif self.interface == "tcp":
            return f"tcp {self.tcp_address}:{self.tcp_port}"
        elif self.interface == "usb":
            return f"usb: {self.serial_port}"
        return f"undefined {self.interface}"

    @property
    def has_endstops(self):
        return True

    @property
    def connected(self):
        if self.active_interface:
            return self.active_interface.connected
        return False

    @property
    def is_connecting(self):
        if self.active_interface:
            return self.active_interface.is_connecting
        return False

    def abort_connect(self):
        if self.active_interface:
            self.active_interface.abort_connect()

    def set_disable_connect(self, should_disable):
        pass

    def service_attach(self, *args, **kwargs):
        self.realize()
        self(".interface_update\n")  # Need to establish initial interface pipes.

    @signal_listener("magic")
    def update_magic(self, origin, *args):
        self.driver.controller.job.set_magic(self.magic)

    @signal_listener("scale_x")
    @signal_listener("scale_y")
    @signal_listener("bedwidth")
    @signal_listener("bedheight")
    @signal_listener("flip_x")
    @signal_listener("flip_y")
    @signal_listener("home_corner")
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
        self.signal("view;realized")

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
