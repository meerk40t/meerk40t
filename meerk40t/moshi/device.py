"""
Moshiboard Device


Defines the interactions between the device service and the meerk40t's viewport.
Registers relevant commands and options.
"""

from meerk40t.kernel import STATE_ACTIVE, STATE_PAUSE, Service

from ..core.spoolers import Spooler
from ..core.units import UNITS_PER_MIL, ViewPort
from .controller import MoshiController
from .driver import MoshiDriver


class MoshiDevice(Service, ViewPort):
    """
    MoshiDevice is driver for the Moshiboard boards.
    """

    def __init__(self, kernel, path, *args, **kwargs):
        Service.__init__(self, kernel, path)
        self.name = "MoshiDevice"

        self.setting(bool, "opt_rapid_between", True)
        self.setting(int, "opt_jog_mode", 0)
        self.setting(int, "opt_jog_minimum", 256)

        self.setting(int, "usb_index", -1)
        self.setting(int, "usb_bus", -1)
        self.setting(int, "usb_address", -1)
        self.setting(int, "usb_version", -1)
        self.setting(bool, "mock", False)

        self.setting(bool, "home_right", False)
        self.setting(bool, "home_bottom", False)
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
            },
            {
                "attr": "bedwidth",
                "object": self,
                "default": "330mm",
                "type": str,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
                "section": "_10_Dimensions",
                "subsection": "Bed",
                "signals": "bedsize",
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": "210mm",
                "type": str,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
                "section": "_10_Dimensions",
                "subsection": "Bed",
                "signals": "bedsize",
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
                "signals": ("bedsize"),
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
                "signals": ("bedsize"),
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
            {
                "attr": "interpolate",
                "object": self,
                "default": 50,
                "type": int,
                "label": _("Curve Interpolation"),
                "tip": _("Distance of the curve interpolation in mils"),
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
        ]
        self.register_choices("bed_dim", choices)
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

        self.state = 0

        self.driver = MoshiDriver(self)
        self.add_service_delegate(self.driver)

        self.controller = MoshiController(self)
        self.add_service_delegate(self.controller)

        self.spooler = Spooler(self, driver=self.driver)
        self.add_service_delegate(self.spooler)

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
            self.controller.update_state(STATE_ACTIVE)
            self.controller.start()
            channel("Moshi Channel Started.")

        @self.console_command("hold", input_type="moshi", help=_("Hold Controller"))
        def pipe_pause(command, channel, _, **kwargs):
            """
            Pause output sending.
            """
            self.controller.update_state(STATE_PAUSE)
            self.controller.pause()
            channel(_("Moshi Channel Paused."))
            self.signal("pause")

        @self.console_command("resume", input_type="moshi", help=_("Resume Controller"))
        def pipe_resume(command, channel, _, **kwargs):
            """
            Resume output sending.
            """
            self.controller.update_state(STATE_ACTIVE)
            self.controller.start()
            channel(_("Moshi Channel Resumed."))
            self.signal("pause")

        @self.console_command(("estop", "abort"), help=_("Abort Job"))
        def pipe_abort(command, channel, _, **kwargs):
            """
            Abort output job. Usually due to the functionality of Moshiboards this will do
            nothing as the job will have already sent to the backend.
            """
            self.controller.estop()
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

    @property
    def viewbuffer(self):
        return self.controller.viewbuffer()

    @property
    def current(self):
        """
        @return: the location in units for the current known position.
        """
        return self.device_to_scene_position(self.driver.native_x, self.driver.native_y)

    @property
    def native(self):
        """
        @return: the location in device native units for the current known position.
        """
        return self.driver.native_x, self.driver.native_y

    def realize(self):
        self.width = self.bedwidth
        self.height = self.bedheight
        self.origin_x = 1.0 if self.home_right else 0.0
        self.origin_y = 1.0 if self.home_bottom else 0.0
        super().realize()
