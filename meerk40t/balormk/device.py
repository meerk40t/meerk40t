"""
Galvo Device

Defines how the balor device interacts with the scene, and accepts data via the spooler.
"""

from meerk40t.balormk.driver import BalorDriver
from meerk40t.core.spoolers import Spooler
from meerk40t.core.units import Angle, Length
from meerk40t.core.view import View
from meerk40t.device.devicechoices import get_effect_choices
from meerk40t.device.mixins import Status
from meerk40t.kernel import Service, signal_listener


class BalorDevice(Service, Status):
    """
    The BalorDevice is a MeerK40t service for the device type. It should be the main method of interacting with
    the rest of meerk40t. It defines how the scene should look and contains a spooler which meerk40t will give jobs
    to. This class additionally defines commands which exist as console commands while this service is activated.
    """

    def __init__(self, kernel, path, *args, choices=None, **kwargs):
        Service.__init__(self, kernel, path)
        Status.__init__(self)
        self.name = "balor"
        self.extension = "lmc"
        self.job = None
        if choices is not None:
            for c in choices:
                attr = c.get("attr")
                default = c.get("default")
                if attr is not None and default is not None:
                    setattr(self, attr, default)

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
                "signals": "device;renamed",
            },
            {
                "attr": "source",
                "object": self,
                "default": "fiber",
                "type": str,
                "style": "combo",
                "choices": ["fiber", "co2", "uv"],
                "label": _("Laser Source"),
                "tip": _("What type of laser is this?"),
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
                "subsection": "_00_",
                "priority": "20",
                "nonzero": True,
                # intentionally not bed_size
            },
            {
                "attr": "laserspot",
                "object": self,
                "default": "0.3mm",
                "type": Length,
                "label": _("Laserspot"),
                "tip": _("Laser spot size"),
                "section": "_00_General",
                "subsection": "_00_",
                "priority": "20",
                "nonzero": True,
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
                "default": True,
                "type": bool,
                "label": _("Flip Y"),
                "tip": _("Flip the Y axis for the device"),
                "section": "_10_Parameters",
                "subsection": "_10_Axis corrections",
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
                "attr": "rotate",
                "object": self,
                "default": 0,
                "type": int,
                "style": "combo",
                "trailer": "°",
                "choices": [
                    0,
                    90,
                    180,
                    270,
                ],
                "label": _("Rotate View"),
                "tip": _("Rotate the device field"),
                "section": "_10_Parameters",
                "subsection": "_10_Axis corrections",
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
                "section": "_10_Parameters",
                # _("User Offset")
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
                "section": "_10_Parameters",
                "subsection": "_30_User Offset",
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
                "subsection": "_10_Device Selection",
            },
            {
                "attr": "serial_enable",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Check serial no"),
                "tip": _("Does the machine need to have a specific serial number?"),
                "section": "_00_General",
                "subsection": "_10_Device Selection",
            },
            {
                "attr": "serial",
                "object": self,
                "default": "",
                "type": str,
                "tip": _("Does the machine need to have a specific serial number?"),
                "label": "",
                "section": "_00_General",
                "subsection": "_10_Device Selection",
                "conditional": (self, "serial_enable"),
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
                "signals": "balorpin",
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
                "signals": "balorpin",
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
        self.register_choices("balor", choices)

        self.register_choices("balor-effects", get_effect_choices(self))

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
                "tip": _("What power level do we cut at?"),
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
                "attr": "default_fpk",
                "object": self,
                "default": 10.0,
                "type": float,
                "trailer": "%",
                "label": _("First Pulse Killer"),
                "conditional": (self, "source", "co2"),
                "tip": _("Percent of First Pulse Killer for co2 source"),
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
                # "conditional": (self, "source", "fiber"),
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
            },
            {
                "attr": "pwm_half_period",
                "object": self,
                "default": 125,
                "type": int,
                "label": _("PWM Half Period"),
                "tip": _("Pulse Period: the frequency of the preionization signal"),
                "subsection": "Pulse-Width-Modulation",
            },
            {
                "attr": "pwm_pulse_width",
                "object": self,
                "default": 125,
                "type": int,
                "label": _("PWM Pulse Width"),
                "tip": _("Pulse Width: the pulse width of the preionization signal"),
                "subsection": "Pulse-Width-Modulation",
            },
            {
                "attr": "standby_param_1",
                "object": self,
                "default": 2000,
                "type": int,
                "label": _("Parameter 1"),
                # "tip": _(""),
                "subsection": "Standby-Parameter",
            },
            {
                "attr": "standby_param_2",
                "object": self,
                "default": 20,
                "type": int,
                "label": _("Parameter 2"),
                # "tip": _(""),
                "subsection": "Standby-Parameter",
            },
            {
                "attr": "timing_mode",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("Timing Mode"),
                # "tip": _(""),
                "subsection": "Modes",
            },
            {
                "attr": "delay_mode",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("Delay Mode"),
                # "tip": _(""),
                "subsection": "Modes",
            },
            {
                "attr": "laser_mode",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("Laser Mode"),
                # "tip": _(""),
                "subsection": "Modes",
            },
            {
                "attr": "control_mode",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Control Mode"),
                # "tip": _(""),
                "subsection": "Modes",
            },
            {
                "attr": "fpk2_p1",
                "object": self,
                "default": 0xFFB,
                "type": int,
                "label": _("Max Voltage"),
                # "tip": _(""),
                "trailer": "V",
                "section": "First Pulse Killer",
                "subsection": "Parameters",
            },
            {
                "attr": "fpk2_p2",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("Min Voltage"),
                "trailer": "V",
                # "tip": _(""),
                "section": "First Pulse Killer",
                "subsection": "Parameters",
            },
            {
                "attr": "fpk2_p3",
                "object": self,
                "default": 409,
                "type": int,
                "label": _("T1"),
                "trailer": "µs",
                # "tip": _(""),
                "section": "First Pulse Killer",
                "subsection": "Parameters",
            },
            {
                "attr": "fpk2_p4",
                "object": self,
                "default": 100,
                "type": int,
                "label": _("T2"),
                "trailer": "µs",
                # "tip": _(""),
                "section": "First Pulse Killer",
                "subsection": "Parameters",
            },
            {
                "attr": "fly_res_p1",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Param 1"),
                # "tip": _(""),
                "subsection": "Fly Resolution",
            },
            {
                "attr": "fly_res_p2",
                "object": self,
                "default": 99,
                "type": int,
                "label": _("Param 2"),
                # "tip": _(""),
                "subsection": "Fly Resolution",
            },
            {
                "attr": "fly_res_p3",
                "object": self,
                "default": 1000,
                "type": int,
                "label": _("Param 3"),
                # "tip": _(""),
                "subsection": "Fly Resolution",
            },
            {
                "attr": "fly_res_p4",
                "object": self,
                "default": 25,
                "type": int,
                "label": _("Param 4"),
                # "tip": _(""),
                "subsection": "Fly Resolution",
            },
            {
                "attr": "input_passes_required",
                "object": self,
                "default": 3,
                "type": int,
                "label": _("Input Signal Hold"),
                "tip": _(
                    "How long does the input operation need to hold for to count as a pass"
                ),
            },
            {
                "attr": "input_operation_hardware",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Input Operation Hardware"),
                "tip": _("Use hardware based input operation command"),
            },
        ]
        self.register_choices("balor-extra", choices)

        choices = [
            {
                "attr": "cf_1",
                "object": self,
                "default": "50",
                "type": float,
                "label": _("Corfile distance {index}").format(index=1),
                "section": _("Correction-Values"),
            },
            {
                "attr": "cf_2",
                "object": self,
                "default": "50",
                "type": float,
                "label": _("Corfile distance {index}").format(index=2),
                "section": _("Correction-Values"),
            },
            {
                "attr": "cf_3",
                "object": self,
                "default": "50",
                "type": float,
                "label": _("Corfile distance {index}").format(index=3),
                "section": _("Correction-Values"),
            },
            {
                "attr": "cf_4",
                "object": self,
                "default": "50",
                "type": float,
                "label": _("Corfile distance {index}").format(index=4),
                "section": _("Correction-Values"),
            },
            {
                "attr": "cf_5",
                "object": self,
                "default": "50",
                "type": float,
                "label": _("Corfile distance {index}").format(index=5),
                "section": _("Correction-Values"),
            },
            {
                "attr": "cf_6",
                "object": self,
                "default": "50",
                "type": float,
                "label": _("Corfile distance {index}").format(index=6),
                "section": _("Correction-Values"),
            },
            {
                "attr": "cf_7",
                "object": self,
                "default": "50",
                "type": float,
                "label": _("Corfile distance {index}").format(index=7),
                "section": _("Correction-Values"),
            },
            {
                "attr": "cf_8",
                "object": self,
                "default": "50",
                "type": float,
                "label": _("Corfile distance {index}").format(index=8),
                "section": _("Correction-Values"),
            },
            {
                "attr": "cf_9",
                "object": self,
                "default": "50",
                "type": float,
                "label": _("Corfile distance {index}").format(index=9),
                "section": _("Correction-Values"),
            },
            {
                "attr": "cf_10",
                "object": self,
                "default": "50",
                "type": float,
                "label": _("Corfile distance {index}").format(index=10),
                "section": _("Correction-Values"),
            },
            {
                "attr": "cf_11",
                "object": self,
                "default": "50",
                "type": float,
                "label": _("Corfile distance {index}").format(index=11),
                "section": _("Correction-Values"),
            },
            {
                "attr": "cf_12",
                "object": self,
                "default": "50",
                "type": float,
                "label": _("Corfile distance {index}").format(index=12),
                "section": _("Correction-Values"),
            },
        ]
        self.register_choices("balor-corfile", choices)
        self.kernel.root.coolant.claim_coolant(self, self.device_coolant)

        self.state = 0

        unit_size = float(Length(self.lens_size))
        galvo_range = 0xFFFF
        units_per_galvo = unit_size / galvo_range
        self.view = View(
            self.lens_size,
            self.lens_size,
            native_scale_x=units_per_galvo,
            native_scale_y=units_per_galvo,
        )
        self.realize()

        self.spooler = Spooler(self)
        self.driver = BalorDriver(self)
        self.spooler.driver = self.driver

        self.add_service_delegate(self.spooler)

        self.viewbuffer = ""
        self._simulate = False
        self.laser_status = "idle"

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

    @signal_listener("lens_size")
    @signal_listener("rotate")
    @signal_listener("flip_x")
    @signal_listener("flip_y")
    @signal_listener("swap_xy")
    @signal_listener("user_margin_x")
    @signal_listener("user_margin_y")
    def realize(self, origin=None, *args):
        if origin is not None and origin != self.path:
            return
        try:
            unit_size = float(Length(self.lens_size))
        except ValueError:
            return
        galvo_range = 0xFFFF
        units_per_galvo = unit_size / galvo_range

        self.view.set_dims(self.lens_size, self.lens_size)
        self.view.set_margins(self.user_margin_x, self.user_margin_y)
        self.view.set_native_scale(units_per_galvo, units_per_galvo)
        self.view.transform(
            flip_x=self.flip_x,
            flip_y=self.flip_y,
            swap_xy=self.swap_xy,
        )
        if self.rotate >= 90:
            self.view.rotate_cw()
        if self.rotate >= 180:
            self.view.rotate_cw()
        if self.rotate >= 270:
            self.view.rotate_cw()
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

    @property
    def calibration_file(self):
        return None

    @signal_listener("light_simulate")
    def simulate_state(self, origin, v=True):
        self._simulate = False

    def outline(self):
        if not self._simulate:
            self._simulate = True
            self("full-light\n")
        else:
            self._simulate = False
            self("stop\n")

    def cool_helper(self, choice_dict):
        self.kernel.root.coolant.coolant_choice_helper(self)(choice_dict)

    def location(self):
        """
        Returns the current connection type for the device.
        If the device is in mock mode, returns 'mock', otherwise returns 'usb'.
        """
        return "mock" if self.mock else "usb"
