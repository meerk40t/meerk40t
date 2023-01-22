"""
Galvo Device

Defines how the balor device interacts with the scene, and accepts data via the spooler.
"""
import os
import re
import struct

from meerk40t.balormk.driver import BalorDriver
from meerk40t.balormk.elementlightjob import ElementLightJob
from meerk40t.balormk.livefulllightjob import LiveFullLightJob
from meerk40t.balormk.liveselectionlightjob import LiveSelectionLightJob
from meerk40t.core.spoolers import Spooler
from meerk40t.core.units import Angle, Length, ViewPort
from meerk40t.kernel import Service, signal_listener
from meerk40t.svgelements import Path, Point, Polygon


class BalorDevice(Service, ViewPort):
    """
    The BalorDevice is a MeerK40t service for the device type. It should be the main method of interacting with
    the rest of meerk40t. It defines how the scene should look and contains a spooler which meerk40t will give jobs
    to. This class additionally defines commands which exist as console commands while this service is activated.
    """

    def __init__(self, kernel, path, *args, **kwargs):
        Service.__init__(self, kernel, path)
        self.name = "balor"
        self.job = None

        _ = kernel.translation
        self.register("frequency", (0, 1000))
        self.register(
            "format/op cut",
            "{danger}{defop}{enabled}{pass}{element_type} {speed}mm/s @{power} {frequency}kHz {colcode} {opstop}",
        )
        self.register(
            "format/op engrave",
            "{danger}{defop}{enabled}{pass}{element_type} {speed}mm/s @{power} {frequency}kHz {colcode} {opstop}",
        )
        self.register(
            "format/op hatch",
            "{danger}{defop}{enabled}{penpass}{pass}{element_type} {speed}mm/s @{power} {frequency}kHz {colcode} {opstop}",
        )
        self.register(
            "format/op raster",
            "{danger}{defop}{enabled}{pass}{element_type}{direction}{speed}mm/s @{power} {frequency}kHz {colcode} {opstop}",
        )
        self.register(
            "format/op image",
            "{danger}{defop}{enabled}{penvalue}{pass}{element_type}{direction}{speed}mm/s @{power} {frequency}kHz {colcode}",
        )
        self.register(
            "format/op dots",
            "{danger}{defop}{enabled}{pass}{element_type} {dwell_time}ms dwell {frequency}kHz {colcode} {opstop}",
        )
        self.register("format/util console", "{enabled}{command}")
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
        choices = [
            {
                "attr": "label",
                "object": self,
                "default": "balor-device",
                "type": str,
                "label": _("Label"),
                "tip": _("What is this device called."),
                "section": "_00_General",
                "priority": "10",
            },
            {
                "attr": "corfile_enabled",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Enable"),
                "tip": _("Use correction file?"),
                "section": "_00_General",
                "subsection": "Correction File",
            },
            {
                "attr": "corfile",
                "object": self,
                "default": None,
                "type": str,
                "style": "file",
                "wildcard": "*.cor",
                "conditional": (self, "corfile_enabled"),
                "label": _("File"),
                "tip": _("Provide a correction file for the machine"),
                "weight": 3,
                "section": "_00_General",
                "subsection": "Correction File",
            },
            {
                "attr": "lens_size",
                "object": self,
                "default": "110mm",
                "type": Length,
                "label": _("Width"),
                "tip": _("Lens Size"),
                "section": "_00_General",
                "priority": "20",
                "signals": "bedsize",
                "nonzero": True,
                # intentionally not bed_size
            },
            {
                "attr": "offset_x",
                "object": self,
                "default": "0mm",
                "type": Length,
                "label": _("X-Axis"),
                "tip": _("Offset in the X axis"),
                "section": "_10_Parameters",
                "subsection": "_25_Offset",
            },
            {
                "attr": "offset_y",
                "object": self,
                "default": "0mm",
                "type": Length,
                "label": _("Y-Axis"),
                "tip": _("Offset in the Y axis"),
                "section": "_10_Parameters",
                "subsection": "_25_Offset",
            },
            {
                "attr": "scale_x",
                "object": self,
                "default": "1.0",
                "type": float,
                "label": _("X-Axis"),
                "tip": _("Scale the X axis"),
                "section": "_10_Parameters",
                "subsection": "_20_Scale",
            },
            {
                "attr": "scale_y",
                "object": self,
                "default": "1.0",
                "type": float,
                "label": _("Y-Axis"),
                "tip": _("Scale the Y axis"),
                "section": "_10_Parameters",
                "subsection": "_20_Scale",
            },
            {
                "attr": "flip_x",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Flip X"),
                "tip": _("Flip the X axis for the Balor device"),
                "section": "_10_Parameters",
                "subsection": "_10_Axis corrections",
                "signals": "bedsize",
            },
            {
                "attr": "flip_y",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Flip Y"),
                "tip": _("Flip the Y axis for the Balor device"),
                "section": "_10_Parameters",
                "subsection": "_10_Axis corrections",
                "signals": "bedsize",
            },
            {
                "attr": "swap_xy",
                "object": self,
                "default": True,
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
                "attr": "footpedal_pin",
                "object": self,
                "default": 15,
                "type": int,
                "label": _("Footpedal"),
                "tip": _("What pin is your foot pedal hooked to on the GPIO"),
                "section": "_10_Parameters",
                "subsection": "_30_Pin-Index",
            },
            {
                "attr": "light_pin",
                "object": self,
                "default": 8,
                "type": int,
                "label": _("Redlight laser"),
                "tip": _("What pin is your redlight hooked to on the GPIO"),
                "section": "_10_Parameters",
                "subsection": "_30_Pin-Index",
            },
        ]
        self.register_choices("balor", choices)

        choices = [
            {
                "attr": "redlight_speed",
                "object": self,
                "default": "3000",
                "type": int,
                "label": _("Redlight travel speed"),
                "tip": _("Speed of the galvo when using the red laser."),
            },
            {
                "attr": "redlight_offset_x",
                "object": self,
                "default": "0mm",
                "type": Length,
                "label": _("X-Offset"),
                "tip": _("Offset the redlight positions by this amount in x"),
                "subsection": "Redlight-Offset",
            },
            {
                "attr": "redlight_offset_y",
                "object": self,
                "default": "0mm",
                "type": Length,
                "label": _("Y-Offset"),
                "tip": _("Offset the redlight positions by this amount in y"),
                "subsection": "Redlight-Offset",
            },
            {
                "attr": "redlight_angle",
                "object": self,
                "default": "0deg",
                "type": Angle,
                "label": _("Angle Offset"),
                "tip": _(
                    "Offset the redlight positions by this angle, curving around center"
                ),
                "subsection": "Redlight-Offset",
            },
            {
                "attr": "redlight_preferred",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Prefer redlight on"),
                "tip": _(
                    "Redlight preference will turn toggleable redlights on after a job completes."
                ),
                "priority": "0",
            },
        ]
        self.register_choices("balor-redlight", choices)

        choices = [
            {
                "attr": "default_power",
                "object": self,
                "default": 50.0,
                "type": float,
                "label": _("Laser Power"),
                "trailer": "%",
                "tip": _("How what power level do we cut at?"),
            },
            {
                "attr": "default_speed",
                "object": self,
                "default": 100.0,
                "type": float,
                "trailer": "mm/s",
                "label": _("Cut Speed"),
                "tip": _("How fast do we cut?"),
            },
            {
                "attr": "default_frequency",
                "object": self,
                "default": 30.0,
                "type": float,
                "trailer": "kHz",
                "label": _("Q Switch Frequency"),
                "tip": _("QSwitch Frequency value"),
            },
            {
                "attr": "default_rapid_speed",
                "object": self,
                "default": 2000.0,
                "type": float,
                "label": _("Travel Speed"),
                "trailer": "mm/s",
                "tip": _("How fast do we travel when not cutting?"),
            },
            {
                "attr": "pulse_width_enabled",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Enable"),
                "tip": _("Enable using Pulse Width (MOPA)"),
                "subsection": "Pulse Width",
            },
            {
                "attr": "default_pulse_width",
                "object": self,
                "default": 4,
                "type": int,
                "style": "combo",
                "choices": [
                    1,
                    2,
                    4,
                    6,
                    9,
                    13,
                    20,
                    30,
                    45,
                    55,
                    60,
                    80,
                    100,
                    150,
                    200,
                    250,
                ],
                "conditional": (self, "pulse_width_enabled"),
                "label": _("Set Pulse Width (ns)"),
                "trailer": "ns",
                "tip": _("Set the MOPA pulse width setting"),
                "subsection": "Pulse Width",
            },
        ]
        self.register_choices("balor-global", choices)

        choices = [
            {
                "attr": "delay_laser_on",
                "object": self,
                "default": 100.0,
                "type": float,
                "label": _("Laser On"),
                "trailer": "µs",
                "tip": _(
                    "Start delay (Start TC) at the beginning of each mark command"
                ),
                "section": "_10_General",
                "subsection": "Delays",
                "priority": "00",
            },
            {
                "attr": "delay_laser_off",
                "object": self,
                "default": 100.0,
                "type": float,
                "label": _("Laser Off"),
                "trailer": "µs",
                "tip": _(
                    "The delay time of the laser shutting down after marking finished"
                ),
                "section": "_10_General",
                "subsection": "Delays",
                "priority": "10",
            },
            {
                "attr": "delay_polygon",
                "object": self,
                "default": 100.0,
                "type": float,
                "label": _("Polygon Delay"),
                "trailer": "µs",
                "tip": _("Delay amount between different points in the path travel."),
                "section": "_10_General",
                "subsection": "Delays",
                "priority": "30",
            },
            {
                "attr": "delay_end",
                "object": self,
                "default": 300.0,
                "type": float,
                "label": _("End Delay"),
                "trailer": "µs",
                "tip": _("Delay amount for the end TC"),
                "section": "_10_General",
                "subsection": "Delays",
                "priority": "20",
            },
            {
                "attr": "delay_jump_long",
                "object": self,
                "default": 200.0,
                "type": float,
                "label": _("Long jump delay"),
                "trailer": "µs",
                "tip": _("Delay for a long jump distance"),
                "section": "_10_General",
                "subsection": "Jump-Settings",
            },
            {
                "attr": "delay_jump_short",
                "object": self,
                "default": 8,
                "type": float,
                "label": _("Short jump delay"),
                "trailer": "µs",
                "tip": _("Delay for a short jump distance"),
                "section": "_10_General",
                "subsection": "Jump-Settings",
            },
            {
                "attr": "delay_distance_long",
                "object": self,
                "default": "10mm",
                "type": Length,
                "label": _("Long jump distance"),
                "tip": _("Distance divide between long and short jump distances"),
                "section": "_10_General",
                "subsection": "Jump-Settings",
            },
            {
                "attr": "delay_openmo",
                "object": self,
                "default": 8.0,
                "type": float,
                "label": _("Open MO delay"),
                "trailer": "ms",
                "tip": _("OpenMO delay in ms"),
                "section": "_90_Other",
            },
        ]
        self.register_choices("balor-global-timing", choices)

        choices = [
            {
                "attr": "first_pulse_killer",
                "object": self,
                "default": 200,
                "type": int,
                "label": _("First Pulse Killer"),
                "trailer": "µs",
                "tip": _(
                    "First Pulse Killer (F.P.K): the lasting time for the first pulse suppress"
                ),
                "section": "First Pulse Killer",
                "hidden": 1,
            },
            {
                "attr": "pwm_half_period",
                "object": self,
                "default": 125,
                "type": int,
                "label": _("PWM Half Period"),
                "tip": _("Pulse Period: the frequency of the preionization signal"),
                "subsection": "Pulse-Width-Modulation",
                "hidden": 1,
            },
            {
                "attr": "pwm_pulse_width",
                "object": self,
                "default": 125,
                "type": int,
                "label": _("PWM Pulse Width"),
                "tip": _("Pulse Width: the pulse width of the preionization signal"),
                "subsection": "Pulse-Width-Modulation",
                "hidden": 1,
            },
            {
                "attr": "standby_param_1",
                "object": self,
                "default": 2000,
                "type": int,
                "label": _("Parameter 1"),
                "tip": _(""),
                "subsection": "Standby-Parameter",
                "hidden": 1,
            },
            {
                "attr": "standby_param_2",
                "object": self,
                "default": 20,
                "type": int,
                "label": _("Parameter 2"),
                "tip": _(""),
                "subsection": "Standby-Parameter",
                "hidden": 1,
            },
            {
                "attr": "timing_mode",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("Timing Mode"),
                "tip": _(""),
                "subsection": "Modes",
                "hidden": 1,
            },
            {
                "attr": "delay_mode",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("Delay Mode"),
                "tip": _(""),
                "subsection": "Modes",
                "hidden": 1,
            },
            {
                "attr": "laser_mode",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("Laser Mode"),
                "tip": _(""),
                "subsection": "Modes",
                "hidden": 1,
            },
            {
                "attr": "control_mode",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Control Mode"),
                "tip": _(""),
                "subsection": "Modes",
                "hidden": 1,
            },
            {
                "attr": "fpk2_p1",
                "object": self,
                "default": 0xFFB,
                "type": int,
                "label": _("Max Voltage"),
                "tip": _(""),
                "trailer": "V",
                "section": "First Pulse Killer",
                "subsection": "Parameters",
                "hidden": 1,
            },
            {
                "attr": "fpk2_p2",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("Min Voltage"),
                "trailer": "V",
                "tip": _(""),
                "section": "First Pulse Killer",
                "subsection": "Parameters",
                "hidden": 1,
            },
            {
                "attr": "fpk2_p3",
                "object": self,
                "default": 409,
                "type": int,
                "label": _("T1"),
                "trailer": "µs",
                "tip": _(""),
                "section": "First Pulse Killer",
                "subsection": "Parameters",
                "hidden": 1,
            },
            {
                "attr": "fpk2_p4",
                "object": self,
                "default": 100,
                "type": int,
                "label": _("T2"),
                "trailer": "µs",
                "tip": _(""),
                "section": "First Pulse Killer",
                "subsection": "Parameters",
                "hidden": 1,
            },
            {
                "attr": "fly_res_p1",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Param 1"),
                "tip": _(""),
                "subsection": "Fly Resolution",
                "hidden": 1,
            },
            {
                "attr": "fly_res_p2",
                "object": self,
                "default": 99,
                "type": int,
                "label": _("Param 2"),
                "tip": _(""),
                "subsection": "Fly Resolution",
                "hidden": 1,
            },
            {
                "attr": "fly_res_p3",
                "object": self,
                "default": 1000,
                "type": int,
                "label": _("Param 3"),
                "tip": _(""),
                "subsection": "Fly Resolution",
                "hidden": 1,
            },
            {
                "attr": "fly_res_p4",
                "object": self,
                "default": 25,
                "type": int,
                "label": _("Param 4"),
                "tip": _(""),
                "subsection": "Fly Resolution",
                "hidden": 1,
            },
        ]
        self.register_choices("balor-extra", choices)

        self.state = 0

        unit_size = float(Length(self.lens_size))
        galvo_range = 0xFFFF
        units_per_galvo = unit_size / galvo_range

        ViewPort.__init__(
            self,
            self.lens_size,
            self.lens_size,
            native_scale_x=units_per_galvo,
            native_scale_y=units_per_galvo,
            origin_x=1.0 if self.flip_x else 0.0,
            origin_y=1.0 if self.flip_y else 0.0,
            show_origin_x=0.5,
            show_origin_y=0.5,
            flip_x=self.flip_x,
            flip_y=self.flip_y,
            swap_xy=self.swap_xy,
        )
        self.spooler = Spooler(self)
        self.driver = BalorDriver(self)
        self.spooler.driver = self.driver

        self.add_service_delegate(self.spooler)

        self.viewbuffer = ""

        @self.console_option(
            "travel_speed", "t", type=float, help="Set the travel speed."
        )
        @self.console_option(
            "jump_delay",
            "d",
            type=float,
            default=200.0,
            help="Sets the jump delay for light travel moves",
        )
        @self.console_option(
            "simulation_speed",
            "m",
            type=float,
            help="sets the simulation speed for this operation",
        )
        @self.console_option(
            "quantization",
            "Q",
            type=int,
            default=500,
            help="Number of line segments to break this path into",
        )
        @self.console_command(
            ("light", "light-simulate"),
            input_type="shapes",
            help=_("runs light on events."),
        )
        def light(
            command,
            channel,
            _,
            travel_speed=None,
            jump_delay=200,
            simulation_speed=None,
            quantization=500,
            data=None,
            **kwgs,
        ):
            """
            Creates a shape based light job for use with the Galvo driver
            """
            if data is None:
                channel("Nothing sent")
                return
            if command == "light":
                self.job = ElementLightJob(
                    self,
                    data,
                    travel_speed=travel_speed,
                    jump_delay=jump_delay,
                    simulation_speed=simulation_speed,
                    quantization=quantization,
                    simulate=False,
                )
            else:
                self.job = ElementLightJob(
                    self,
                    data,
                    travel_speed=travel_speed,
                    jump_delay=jump_delay,
                    simulation_speed=simulation_speed,
                    quantization=quantization,
                    simulate=True,
                )
            self.spooler.send(self.job)

        @self.console_command(
            "select-light", help=_("Execute selection light idle job")
        )
        def select_light(**kwargs):
            """
            Start a live bounds job.
            """
            # Live Bounds Job.
            if self.job is not None:
                self.job.stop()
            self.job = LiveSelectionLightJob(self)
            self.spooler.send(self.job)

        @self.console_command("full-light", help=_("Execute full light idle job"))
        def full_light(**kwargs):
            if self.job is not None:
                self.job.stop()
            self.job = LiveFullLightJob(self)
            self.spooler.send(self.job)

        @self.console_command(
            "stop",
            help=_("stops the idle running job"),
        )
        def stoplight(command, channel, _, data=None, remainder=None, **kwgs):
            if self.job is None:
                channel("No job is currently set")
                return
            channel("Stopping idle job")
            self.job.stop()

        @self.console_command(
            "estop",
            help=_("stops the current job, deletes the spooler"),
            input_type=(None),
        )
        def estop(command, channel, _, data=None, remainder=None, **kwgs):
            channel("Stopping Job")
            if self.job is not None:
                self.job.stop()
            self.spooler.clear_queue()
            self.driver.set_abort()

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

        @self.console_option(
            "default",
            "d",
            help=_("Allow default list commands to persist within the raw command"),
            type=bool,
            action="store_true",
        )
        @self.console_option(
            "raw",
            "r",
            help=_("Data is explicitly little-ended hex from a data capture"),
            type=bool,
            action="store_true",
        )
        @self.console_option(
            "binary_in",
            "b",
            help=_("Read data is explicitly in binary"),
            type=bool,
            action="store_true",
        )
        @self.console_option(
            "binary_out",
            "B",
            help=_("Write data should be explicitly in binary"),
            type=bool,
            action="store_true",
        )
        @self.console_option(
            "short",
            "s",
            help=_("Export data is assumed short command only"),
            type=bool,
            action="store_true",
        )
        @self.console_option(
            "hard",
            "h",
            help=_("Do not send regular list protocol commands"),
            type=bool,
            action="store_true",
        )
        @self.console_option(
            "trim",
            "t",
            help=_("Trim the first number of characters"),
            type=int,
        )
        @self.console_option(
            "input", "i", type=str, default=None, help="input data for given file"
        )
        @self.console_option(
            "output", "o", type=str, default=None, help="output data to given file"
        )
        @self.console_command(
            "raw",
            help=_("sends raw galvo list command exactly as composed"),
        )
        def galvo_raw(
            channel,
            _,
            default=False,
            raw=False,
            binary_in=False,
            binary_out=False,
            short=False,
            hard=False,
            trim=0,
            input=None,
            output=None,
            remainder=None,
            **kwgs,
        ):
            """
            Raw for galvo performs raw actions and sends these commands directly to the laser.
            There are methods for reading and writing raw info from files in order to send that
            data. You can also use shorthand commands.
            """
            from meerk40t.balormk.controller import (
                list_command_lookup,
                single_command_lookup,
            )

            # Establish reverse lookup for string commands to binary command.
            reverse_lookup = {}
            for k in list_command_lookup:
                command_string = list_command_lookup[k]
                reverse_lookup[command_string] = k
                reverse_lookup[command_string.lower()[4:]] = k

            for k in single_command_lookup:
                command_string = single_command_lookup[k]
                reverse_lookup[command_string] = k
                reverse_lookup[command_string.lower()] = k

            if remainder is None and input is None:
                # "raw" was typed without any data or input file, so we list the permitted commands
                channel("Permitted List Commands:")
                for k in list_command_lookup:
                    command_string = list_command_lookup[k]
                    channel(f"{command_string.lower()[4:]} aka {k:04x}")
                channel("----------------------------")

                channel("Permitted Short Commands:")
                for k in single_command_lookup:
                    command_string = single_command_lookup[k]
                    channel(f"{command_string.lower()} aka {k:04x}")
                return

            if input is not None:
                # We were given an input file. We load that data, in either binary plain text.
                from os.path import exists

                if exists(input):
                    channel(f"Loading data from: {input}")
                    try:
                        if binary_in:
                            with open(input, "br") as f:
                                remainder = f.read().hex()
                        else:
                            with open(input) as f:
                                remainder = f.read()
                    except OSError:
                        channel("File could not be read.")
                else:
                    channel(f"The file at {os.path.realpath(input)} does not exist.")
                    return

            cmds = None
            if raw or binary_in:
                # Our data is 6 values int16le
                if trim:
                    # Used to cut off raw header data
                    remainder = remainder[trim:]
                try:
                    cmds = [
                        struct.unpack("<6H", bytearray.fromhex(remainder[i : i + 24]))
                        for i in range(0, len(remainder), 24)
                    ]
                    cmds = [
                        f"{v[0]:04x} {v[1]:04x} {v[2]:04x} {v[3]:04x} {v[4]:04x} {v[5]:04x}"
                        for v in cmds
                    ]
                except (struct.error, ValueError) as e:
                    channel(f"Data was declared raw but could not parse because '{e}'")

            if cmds is None:
                cmds = list(re.split(r"[,\n\r]", remainder))

            raw_commands = list()

            # Compile commands.
            for cmd_i, cmd in enumerate(cmds):
                cmd = cmd.strip()
                if not cmd:
                    continue

                values = [0] * 6
                byte_i = 0
                split_bytes = [b for b in cmd.split(" ") if b.strip()]
                if len(split_bytes) > 6:
                    channel(
                        f"Invalid command line {cmd_i}: {split_bytes} has more than six entries."
                    )
                    return
                for b in split_bytes:
                    v = None
                    convert = reverse_lookup.get(b)
                    if convert is not None:
                        v = int(convert)
                    else:
                        try:
                            p = struct.unpack(">H", bytearray.fromhex(b))
                            v = p[0]
                        except (ValueError, struct.error):
                            pass
                    if not isinstance(v, int):
                        channel(f'Compile error. Line #{cmd_i+1} value "{b}"')
                        return
                    values[byte_i] = v
                    byte_i += 1
                raw_commands.append(values)

            if output is not None:
                # Output to file
                channel(f"Writing data to: {output}")
                try:
                    if binary_out:
                        with open(output, "wb") as f:
                            for v in raw_commands:
                                b_data = struct.pack("<6H", *v)
                                f.write(b_data)
                    else:
                        lines = []
                        for v in raw_commands:
                            lines.append(
                                f"{list_command_lookup.get(v[0], f'{v[0]:04x}').ljust(20)} "
                                f"{v[1]:04x} {v[2]:04x} {v[3]:04x} {v[4]:04x} {v[5]:04x}\n"
                            )
                        with open(output, "w") as f:
                            f.writelines(lines)
                except OSError:
                    channel("File could not be written.")
                return  # If we output to file, we do not output to device.

            # OUTPUT TO DEVICE
            if hard:
                # Hard raw mode, disable any control values being sent.
                self.driver.connection.raw_mode()
                if not default:
                    self.driver.connection.raw_clear()
                for v in raw_commands:
                    command = v[0]
                    if command >= 0x8000:
                        self.driver.connection._list_write(*v)
                    else:
                        self.driver.connection._list_end()
                        self.driver.connection._command(*v)
                return

            if short:
                # Short mode only sending pure shorts.
                for v in raw_commands:
                    self.driver.connection.raw_write(*v)
                return

            # Hybrid mode. Sending list and short commands using the right mode changes.
            self.driver.connection.rapid_mode()
            self.driver.connection.program_mode()
            if not default:
                self.driver.connection.raw_clear()
            for v in raw_commands:
                command = v[0]
                if command >= 0x8000:
                    self.driver.connection.program_mode()
                    self.driver.connection._list_write(*v)
                else:
                    self.driver.connection.rapid_mode()
                    self.driver.connection._command(*v)
            self.driver.connection.rapid_mode()

        @self.console_argument("x", type=float, default=0.0)
        @self.console_argument("y", type=float, default=0.0)
        @self.console_command(
            "goto",
            help=_("send laser a goto command"),
        )
        def balor_goto(command, channel, _, x=None, y=None, remainder=None, **kwgs):
            if x is not None and y is not None:
                rx = int(0x8000 + x) & 0xFFFF
                ry = int(0x8000 + y) & 0xFFFF
                self.driver.connection.set_xy(rx, ry)

        @self.console_argument("off", type=str)
        @self.console_command(
            "red",
            help=_("Turns redlight on/off"),
        )
        def balor_on(command, channel, _, off=None, remainder=None, **kwgs):
            try:
                if off == "off":
                    reply = self.driver.connection.light_off()
                    self.driver.connection.write_port()
                    self.redlight_preferred = False
                    channel("Turning off redlight.")
                else:
                    reply = self.driver.connection.light_on()
                    self.driver.connection.write_port()
                    channel("Turning on redlight.")
                    self.redlight_preferred = True
            except ConnectionRefusedError:
                self.signal(
                    "warning",
                    _("Connection was aborted. Manual connection required."),
                    _("Not Connected"),
                )
                channel("Could not alter redlight. Connection is aborted.")

        @self.console_argument(
            "filename", type=str, default=None, help="filename or none"
        )
        @self.console_option(
            "default", "d", type=bool, action="store_true", help="restore to default"
        )
        @self.console_command(
            "force_correction",
            help=_("Resets the galvo laser"),
        )
        def force_correction(
            command, channel, _, filename=None, default=False, remainder=None, **kwgs
        ):
            if default:
                filename = self.corfile
                channel(f"Using default corfile: {filename}")
            if filename is None:
                self.driver.connection.write_correction_file(None)
                channel(f"Force set corrections to blank.")
            else:
                from os.path import exists

                if exists(filename):
                    channel(f"Force set corrections: {filename}")
                    self.driver.connection.write_correction_file(filename)
                else:
                    channel(f"The file at {os.path.realpath(filename)} does not exist.")

        @self.console_command(
            "softreboot",
            help=_("Resets the galvo laser"),
        )
        def galvo_reset(command, channel, _, remainder=None, **kwgs):
            self.driver.connection.init_laser()
            channel(f"Soft reboot: {self.label}")

        @self.console_option(
            "duration", "d", type=float, help=_("time to set/unset the port")
        )
        @self.console_argument("off", type=str)
        @self.console_argument("bit", type=int)
        @self.console_command(
            "port",
            help=_("Turns port on or off, eg. port off 8"),
            all_arguments_required=True,
        )
        def balor_port(command, channel, _, off, bit=None, duration=None, **kwgs):
            off = off == "off"
            if off:
                self.driver.connection.port_off(bit)
                self.driver.connection.write_port()
                channel(f"Turning off bit {bit}")
            else:
                self.driver.connection.port_on(bit)
                self.driver.connection.write_port()
                channel(f"Turning on bit {bit}")
            if duration is not None:
                if off:
                    self(f".timer 1 {duration} port on {bit}")
                else:
                    self(f".timer 1 {duration} port off {bit}")

        @self.console_command(
            "status",
            help=_("Sends status check"),
        )
        def balor_status(command, channel, _, remainder=None, **kwgs):
            reply = self.driver.connection.get_version()
            if reply is None:
                channel("Not connected, cannot get serial number.")
                return
            channel(f"Command replied: {reply}")
            for index, b in enumerate(reply):
                channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

        @self.console_command(
            "lstatus",
            help=_("Checks the list status."),
        )
        def balor_liststatus(command, channel, _, remainder=None, **kwgs):
            reply = self.driver.connection.get_list_status()
            if reply is None:
                channel("Not connected, cannot get serial number.")
                return
            channel(f"Command replied: {reply}")
            for index, b in enumerate(reply):
                channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

        @self.console_command(
            "mark_time",
            help=_("Checks the Mark Time."),
        )
        def balor_mark_time(command, channel, _, remainder=None, **kwgs):
            reply = self.driver.connection.get_mark_time()
            if reply is None:
                channel("Not connected, cannot get mark time.")
                return
            channel(f"Command replied: {reply}")
            for index, b in enumerate(reply):
                channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

        @self.console_command(
            "mark_count",
            help=_("Checks the Mark Count."),
        )
        def balor_mark_count(command, channel, _, remainder=None, **kwgs):
            reply = self.driver.connection.get_mark_count()
            if reply is None:
                channel("Not connected, cannot get mark count.")
                return
            channel(f"Command replied: {reply}")
            for index, b in enumerate(reply):
                channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

        @self.console_command(
            "axis_pos",
            help=_("Checks the Axis Position."),
        )
        def balor_axis_pos(command, channel, _, remainder=None, **kwgs):
            reply = self.driver.connection.get_axis_pos()
            if reply is None:
                channel("Not connected, cannot get axis position.")
                return
            channel(f"Command replied: {reply}")
            for index, b in enumerate(reply):
                channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

        @self.console_command(
            "user_data",
            help=_("Checks the User Data."),
        )
        def balor_user_data(command, channel, _, remainder=None, **kwgs):
            reply = self.driver.connection.get_user_data()
            if reply is None:
                channel("Not connected, cannot get user data.")
                return
            channel(f"Command replied: {reply}")
            for index, b in enumerate(reply):
                channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

        @self.console_command(
            "position_xy",
            help=_("Checks the Position XY"),
        )
        def balor_position_xy(command, channel, _, remainder=None, **kwgs):
            reply = self.driver.connection.get_position_xy()
            if reply is None:
                channel("Not connected, cannot get position xy.")
                return
            channel(f"Command replied: {reply}")
            for index, b in enumerate(reply):
                channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

        @self.console_command(
            "fly_speed",
            help=_("Checks the Fly Speed."),
        )
        def balor_fly_speed(command, channel, _, remainder=None, **kwgs):
            reply = self.driver.connection.get_fly_speed()
            if reply is None:
                channel("Not connected, cannot get fly speed.")
                return
            channel(f"Command replied: {reply}")
            for index, b in enumerate(reply):
                channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

        @self.console_command(
            "fly_wait_count",
            help=_("Checks the fiber config extend"),
        )
        def balor_fly_wait_count(command, channel, _, remainder=None, **kwgs):
            reply = self.driver.connection.get_fly_wait_count()
            if reply is None:
                channel("Not connected, cannot get fly weight count.")
                return
            channel(f"Command replied: {reply}")
            for index, b in enumerate(reply):
                channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

        @self.console_command(
            "fiber_st_mo_ap",
            help=_("Checks the fiber st mo ap"),
        )
        def balor_fiber_st_mo_ap(command, channel, _, remainder=None, **kwgs):
            reply = self.driver.connection.get_fiber_st_mo_ap()
            if reply is None:
                channel("Not connected, cannot get fiber_st_mo_ap.")
                return
            channel(f"Command replied: {reply}")
            for index, b in enumerate(reply):
                channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

        @self.console_command(
            "read_port",
            help=_("Checks the read_port"),
        )
        def balor_read_port(command, channel, _, remainder=None, **kwgs):
            reply = self.driver.connection.read_port()
            if reply is None:
                channel("Not connected, cannot get read port.")
                return
            channel(f"Command replied: {reply}")
            for index, b in enumerate(reply):
                channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

        @self.console_command(
            "input_port",
            help=_("Checks the input_port"),
        )
        def balor_input_port(command, channel, _, remainder=None, **kwgs):
            reply = self.driver.connection.get_input_port()
            if reply is None:
                channel("Not connected, cannot get input port.")
                return
            channel(f"Command replied: {reply}")
            for index, b in enumerate(reply):
                channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

        @self.console_command(
            "fiber_config_extend",
            help=_("Checks the fiber config extend"),
        )
        def balor_fiber_config_extend(command, channel, _, remainder=None, **kwgs):
            reply = self.driver.connection.get_fiber_config_extend()
            if reply is None:
                channel("Not connected, cannot get fiber config extend.")
                return
            channel(f"Command replied: {reply}")
            for index, b in enumerate(reply):
                channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

        @self.console_command(
            "serial_number",
            help=_("Checks the serial number."),
        )
        def balor_serial(command, channel, _, remainder=None, **kwgs):
            reply = self.driver.connection.get_serial_number()
            if reply is None:
                channel("Not connected, cannot get serial number.")
                return

            channel(f"Command replied: {reply}")
            for index, b in enumerate(reply):
                channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

        @self.console_argument("filename", type=str, default=None)
        @self.console_command(
            "correction",
            help=_("set the correction file"),
        )
        def set_corfile(command, channel, _, filename=None, remainder=None, **kwgs):
            if filename is None:
                file = self.corfile
                if file is None:
                    channel("No correction file set.")
                else:
                    channel(f"Correction file is set to: {self.corfile}")
                    from os.path import exists

                    if exists(file):
                        channel("Correction file exists!")
                    else:
                        channel("WARNING: Correction file does not exist.")
            else:
                from os.path import exists

                if exists(filename):
                    self.corfile = filename
                    self.signal("corfile", filename)
                else:
                    channel(f"The file at {os.path.realpath(filename)} does not exist.")
                    channel("Correction file was not set.")

        @self.console_command(
            "position",
            help=_("give the position of the selection box in galvos"),
        )
        def galvo_pos(command, channel, _, data=None, args=tuple(), **kwargs):
            """
            Draws an outline of the current shape.
            """
            bounds = self.elements.selected_area()
            if bounds is None:
                channel(_("Nothing Selected"))
                return
            x0, y0 = self.scene_to_device_position(bounds[0], bounds[1])
            x1, y1 = self.scene_to_device_position(bounds[2], bounds[3])
            channel(
                f"Top,Right: ({x0:.02f}, {y0:.02f}). Lower, Left: ({x1:.02f},{y1:.02f})"
            )

        @self.console_argument("lens_size", type=str, default=None)
        @self.console_command(
            "lens",
            help=_("set the lens size"),
        )
        def galvo_lens(
            command, channel, _, data=None, lens_size=None, args=tuple(), **kwargs
        ):
            """
            Sets lens size.
            """
            if lens_size is None:
                raise SyntaxError
            self.lens_size = lens_size
            self.width = lens_size
            self.height = lens_size
            self.signal("bedsize", (self.lens_size, self.lens_size))
            channel(f"Set Bed Size : ({self.lens_size}, {self.lens_size}).")

        @self.console_option(
            "count",
            "c",
            default=256,
            type=int,
            help="Number of instances of boxes to draw.",
        )
        @self.console_command(
            "box",
            help=_("outline the current selected elements"),
            output_type="shapes",
        )
        def shapes_selected(
            command, channel, _, count=256, data=None, args=tuple(), **kwargs
        ):
            """
            Draws an outline of the current shape.
            """
            bounds = self.elements.selected_area()
            if bounds is None:
                channel(_("Nothing Selected"))
                return
            xmin, ymin, xmax, ymax = bounds
            channel(_("Element bounds: {bounds}").format(bounds=str(bounds)))
            points = [
                (xmin, ymin),
                (xmax, ymin),
                (xmax, ymax),
                (xmin, ymax),
            ]
            if count > 1:
                points *= count
            return "shapes", [Polygon(*points)]

        @self.console_command(
            "hull",
            help=_("convex hull of the current selected elements"),
            input_type=(None, "elements"),
            output_type="shapes",
        )
        def shapes_hull(command, channel, _, data=None, args=tuple(), **kwargs):
            """
            Draws an outline of the current shape.
            """
            if data is None:
                data = list(self.elements.elems(emphasized=True))
            pts = []
            for e in data:
                if e.type == "elem image":
                    bounds = e.bounds
                    pts += [
                        (bounds[0], bounds[1]),
                        (bounds[0], bounds[3]),
                        (bounds[2], bounds[1]),
                        (bounds[2], bounds[3]),
                    ]
                elif e.type == "elem text":
                    continue  # We can't outline text.
                else:
                    try:
                        path = abs(Path(e.shape))
                    except AttributeError:
                        try:
                            path = abs(e.path)
                        except AttributeError:
                            continue
                    pts += [q for q in path.as_points()]
            hull = [p for p in Point.convex_hull(pts)]
            if len(hull) == 0:
                channel(_("No elements bounds to trace."))
                return
            hull.append(hull[0])  # loop
            return "shapes", [Polygon(*hull)]

        def ant_points(points, steps):
            points = list(points)
            movement = 1 + int(steps / 10)
            forward_steps = steps + movement
            pos = 0
            size = len(points)
            cycles = int(size / movement) + 1
            for cycle in range(cycles):
                for f in range(pos, pos + forward_steps, 1):
                    index = f % size
                    point = points[index]
                    yield point
                pos += forward_steps
                for f in range(pos, pos - steps, -1):
                    index = f % size
                    point = points[index]
                    yield point
                pos -= steps

        @self.console_option(
            "quantization",
            "q",
            default=50,
            type=int,
            help="Number of segments to break each path into.",
        )
        @self.console_command(
            "ants",
            help=_("Marching ants of the given element path."),
            input_type=(None, "elements"),
            output_type="shapes",
        )
        def element_ants(command, channel, _, data=None, quantization=50, **kwargs):
            """
            Draws an outline of the current shape.
            """
            if data is None:
                data = list(self.elements.elems(emphasized=True))
            points_list = []
            points = list()
            for e in data:
                try:
                    path = e.as_path()
                except AttributeError:
                    continue
                for i in range(0, quantization + 1):
                    x, y = path.point(i / float(quantization))
                    points.append((x, y))
                points_list.append(list(ant_points(points, int(quantization / 2))))
            return "shapes", [Polygon(*p) for p in points_list]

        @self.console_command(
            "viewport_update",
            hidden=True,
            help=_("Update balor flips for movement"),
        )
        def codes_update(**kwargs):
            self.realize()

    @signal_listener("flip_x")
    @signal_listener("flip_y")
    @signal_listener("swap_xy")
    def realize(self, origin=None, *args):
        self.width = self.lens_size
        self.height = self.lens_size
        super().realize()

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

    @property
    def calibration_file(self):
        return None
