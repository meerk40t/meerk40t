"""
Moshiboard Device


Defines the interactions between the device service and the meerk40t's viewport.
Registers relevant commands and options.
"""
import meerk40t.constants as mkconst
from meerk40t.core.view import View
from meerk40t.device.devicechoices import get_effect_choices
from meerk40t.kernel import CommandSyntaxError, Service, signal_listener

from ..core.laserjob import LaserJob
from ..core.spoolers import Spooler
from ..core.units import Length
from ..device.mixins import Status
from .controller import MoshiController
from .driver import MoshiDriver


class MoshiDevice(Service, Status):
    """
    MoshiDevice is driver for the Moshiboard boards.
    """

    def __init__(self, kernel, path, *args, choices=None, **kwgs):
        Service.__init__(self, kernel, path)
        Status.__init__(self)
        self.name = "MoshiDevice"
        self.extension = "mos"
        if choices is not None:
            for c in choices:
                attr = c.get("attr")
                default = c.get("default")
                if attr is not None and default is not None:
                    setattr(self, attr, default)

        self.setting(bool, "opt_rapid_between", True)
        self.setting(int, "opt_jog_mode", 0)
        self.setting(int, "opt_jog_minimum", 256)

        self.setting(int, "usb_index", -1)
        self.setting(int, "usb_bus", -1)
        self.setting(int, "usb_address", -1)
        self.setting(int, "usb_version", -1)

        self.setting(bool, "enable_raster", True)

        self.setting(int, "packet_count", 0)
        self.setting(int, "rejected_count", 0)
        self.setting(int, "rapid_speed", 40)

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
                "signals": "device;renamed",
            },
            {
                "attr": "bedwidth",
                "object": self,
                "default": "330mm",
                "type": Length,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
                "section": "_00_General",
                "subsection": "_10_Dimensions",
                "nonzero": True,
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": "210mm",
                "type": Length,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
                "section": "_00_General",
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
                "section": "_00_General",
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
                "section": "_40_Laser Parameters",
                "subsection": "_05_Scale",
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
                "section": "_40_Laser Parameters",
                "subsection": "_05_Scale",
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
                "section": "_40_Laser Parameters",
                "subsection": "_20_User Offset",
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
                "section": "_40_Laser Parameters",
                "subsection": "_20_User Offset",
            },
            {
                "attr": "flip_x",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Flip X"),
                "tip": _("Flip the X axis for the device"),
                "section": "_40_Laser Parameters",
                "subsection": "_30_Flip Axis",
            },
            {
                "attr": "flip_y",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Flip Y"),
                "tip": _("Flip the Y axis for the device"),
                "section": "_40_Laser Parameters",
                "subsection": "_30_Flip Axis",
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
                "section": "_40_Laser Parameters",
                "subsection": "_30_Flip Axis",
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
                "section": "_40_Laser Parameters",
                "subsection": "_40_" + _("Home position"),
            },
            {
                "attr": "interp",
                "object": self,
                "default": 5,
                "type": int,
                "label": _("Curve Interpolation"),
                "tip": _("Distance of the curve interpolation in mils"),
                "section": "_20_Behaviour",
            },
            {
                "attr": "legacy_raster",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Use legacy raster method"),
                "tip": (
                    _(
                        "Active: Use legacy method (seems to work better at higher speeds, but has some artifacts)"
                    )
                    + "\n"
                    + _(
                        "Inactive: Use regular method (no artifacts but apparently more prone to stuttering at high speeds)"
                    )
                ),
                "section": "_20_Behaviour",
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
                "section": "_30_Interface",
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

        self.register_choices("moshi-effects", get_effect_choices(self))

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
        self.view = View(self.bedwidth, self.bedheight, dpi=1000.0)
        self.realize()
        self.state = 0

        self.driver = MoshiDriver(self)
        self.add_service_delegate(self.driver)

        self.controller = MoshiController(self)
        self.add_service_delegate(self.controller)

        self.spooler = Spooler(self, driver=self.driver)
        self.add_service_delegate(self.spooler)

        self.driver.out_pipe = self.controller.write
        self.driver.out_real = self.controller.realtime

        self.kernel.root.coolant.claim_coolant(self, self.device_coolant)

        _ = self.kernel.translation

        @self.console_command("usb_connect", help=_("Connect USB"))
        def usb_connect(command, channel, _, **kwargs):
            """
            Force USB Connection Event for Moshiboard
            """
            try:
                self.controller.open()
            except ConnectionRefusedError:
                channel("Connection Refused.")

        @self.console_command("usb_disconnect", help=_("Disconnect USB"))
        def usb_disconnect(command, channel, _, **kwargs):
            """
            Force USB Disconnect Event for Moshiboard
            """
            try:
                self.controller.close()
            except ConnectionError:
                channel("Usb is not connected.")

        @self.console_command("start", help=_("Start Pipe to Controller"))
        def pipe_start(command, channel, _, data=None, **kwargs):
            """
            Start output sending.
            """
            self.controller.update_state("active")
            self.controller.start()
            channel("Moshi Channel Started.")

        @self.console_command("hold", input_type="moshi", help=_("Hold Controller"))
        def pipe_pause(command, channel, _, **kwargs):
            """
            Pause output sending.
            """
            self.controller.update_state("pause")
            self.controller.pause()
            channel(_("Moshi Channel Paused."))
            self.signal("pause")

        @self.console_command("resume", input_type="moshi", help=_("Resume Controller"))
        def pipe_resume(command, channel, _, **kwargs):
            """
            Resume output sending.
            """
            self.controller.update_state("active")
            self.controller.start()
            channel(_("Moshi Channel Resumed."))
            self.signal("pause")

        @self.console_command(("estop", "abort"), help=_("Abort Job"))
        def pipe_abort(command, channel, _, **kwargs):
            """
            Abort output job. Usually due to the functionality of Moshiboards this will do
            nothing as the job will have already sent to the backend.
            """
            self.driver.reset()
            channel(_("Moshi Channel Aborted."))
            self.signal("pipe;running", False)

        @self.console_command(
            "status",
            input_type="moshi",
            help=_("Update moshiboard controller status"),
        )
        def realtime_status(channel, _, **kwargs):
            """
            Updates the CH341 Status information for the Moshiboard.
            """
            try:
                self.controller.update_status()
            except ConnectionError:
                channel(_("Could not check status, usb not connected."))

        @self.console_command(
            "continue",
            help=_("abort waiting process on the controller."),
        )
        def realtime_pause(**kwargs):
            """
            Abort the waiting process for Moshiboard. This is usually a wait from BUSY (207) state until the board
            reports its status as READY (205)
            """
            self.controller.abort_waiting = True

        @self.console_argument("filename", type=str)
        @self.console_command("save_job", help=_("save job export"), input_type="plan")
        def moshi_save(channel, _, filename, data=None, **kwargs):
            if filename is None:
                raise CommandSyntaxError
            try:
                with open(filename, "wb") as f:
                    driver = MoshiDriver(self)
                    job = LaserJob(filename, list(data.plan), driver=driver)
                    driver.out_pipe = f.write

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

    def service_attach(self, *args, **kwargs):
        self.realize()

    @property
    def viewbuffer(self):
        return self.controller.viewbuffer()

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

    @signal_listener("bedwidth")
    @signal_listener("bedheight")
    @signal_listener("scale_x")
    @signal_listener("scale_y")
    @signal_listener("flip_x")
    @signal_listener("flip_y")
    @signal_listener("swap_xy")
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
        self.view.transform(
            user_scale_x=self.scale_x,
            user_scale_y=self.scale_y,
            flip_x=self.flip_x,
            flip_y=self.flip_y,
            swap_xy=self.swap_xy,
            origin_x=home_dx,
            origin_y=home_dy,
        )
        self.view.realize()
        self.signal("view;realized")

    def get_raster_instructions(self):
        return {
            "split_crossover": True,
            "unsupported_opt": (
                mkconst.RASTER_GREEDY_H,
                mkconst.RASTER_GREEDY_V,
                mkconst.RASTER_SPIRAL,
            ),  # Greedy loses registration way too often to be reliable
            "gantry": True,
            "legacy": self.legacy_raster,
        }

    def cool_helper(self, choice_dict):
        self.kernel.root.coolant.coolant_choice_helper(self)(choice_dict)

    def location(self):
        return (
            "mock"
            if self.mock
            else f"usb {'auto' if self.usb_index < 0 else self.usb_index}"
        )
