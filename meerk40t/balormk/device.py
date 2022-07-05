import os
import re
import struct

from meerk40t.balormk.driver import BalorDriver
from meerk40t.core.spoolers import Spooler
from meerk40t.core.units import Angle, Length, ViewPort
from meerk40t.kernel import Service
from meerk40t.svgelements import Path, Point, Polygon, Matrix, Polyline


class ElementLightJob:
    def __init__(
        self,
        service,
        elements,
        travel_speed=None,
        jump_delay=200.0,
        simulation_speed=None,
        quantization=500,
        simulate=True,
    ):
        self.service = service
        self.elements = elements
        self.stopped = False
        self.travel_speed = travel_speed
        self.jump_delay = jump_delay
        self.simulation_speed = simulation_speed
        self.quantization = quantization
        self.simulate = simulate

    def stop(self):
        self.stopped = True

    def process(self, con):
        if self.stopped:
            return False
        if not self.elements:
            return False
        con.light_mode()

        x_offset = self.service.length(
            self.service.redlight_offset_x, axis=0, as_float=True
        )
        y_offset = self.service.length(
            self.service.redlight_offset_y, axis=1, as_float=True
        )
        jump_delay = self.jump_delay

        dark_delay = 8
        quantization = self.quantization
        rotate = Matrix()
        rotate.post_rotate(self.service.redlight_angle.radians, 0x8000, 0x8000)
        rotate.post_translate(x_offset, y_offset)

        con._light_speed = self.service.redlight_speed

        def mx_rotate(pt):
            if pt is None:
                return None
            return (
                pt[0] * rotate.a + pt[1] * rotate.c + 1 * rotate.e,
                pt[0] * rotate.b + pt[1] * rotate.d + 1 * rotate.f,
            )

        for e in self.elements:
            if self.stopped:
                return False
            x, y = e.point(0)
            x, y = self.service.scene_to_device_position(x, y)
            x, y = mx_rotate((x, y))
            x = int(x) & 0xFFFF
            y = int(y) & 0xFFFF
            if isinstance(e, (Polygon, Polyline)):
                con.dark(x, y, long=dark_delay, short=dark_delay)
                for pt in e:
                    if self.stopped:
                        return False
                    x, y = self.service.scene_to_device_position(*pt)
                    x, y = mx_rotate((x, y))
                    x = int(x) & 0xFFFF
                    y = int(y) & 0xFFFF
                    con.light(x, y, long=jump_delay, short=jump_delay)
                continue

            con.dark(x, y, long=dark_delay, short=dark_delay)
            for i in range(1, quantization + 1):
                if self.stopped:
                    return False
                x, y = e.point(i / float(quantization))
                x, y = self.service.scene_to_device_position(x, y)
                x, y = mx_rotate((x, y))
                x = int(x) & 0xFFFF
                y = int(y) & 0xFFFF
                con.light(x, y, long=jump_delay, short=jump_delay)
        con.light_off()
        return True


class LiveSelectionLightJob:
    def __init__(
        self,
        service,
    ):
        self.service = service
        self.stopped = False
        self._current_points = None
        self._last_bounds = None

    def update_points(self, bounds):
        if bounds == self._last_bounds and self._current_points is not None:
            return self._current_points, False

        # Calculate rotate matrix.
        rotate = Matrix()
        rotate.post_rotate(self.service.redlight_angle.radians, 0x8000, 0x8000)
        x_offset = self.service.length(
            self.service.redlight_offset_x, axis=0, as_float=True
        )
        y_offset = self.service.length(
            self.service.redlight_offset_y, axis=1, as_float=True
        )
        rotate.post_translate(x_offset, y_offset)

        # Function for using rotate
        def mx_rotate(pt):
            if pt is None:
                return None
            return (
                pt[0] * rotate.a + pt[1] * rotate.c + 1 * rotate.e,
                pt[0] * rotate.b + pt[1] * rotate.d + 1 * rotate.f,
            )

        def crosshairs():
            margin = 5000
            points = [
                (0x8000, 0x8000),
                (0x8000 - margin, 0x8000),
                (0x8000, 0x8000),
                (0x8000, 0x8000 - margin),
                (0x8000, 0x8000),
                (0x8000 + margin, 0x8000),
                (0x8000, 0x8000),
                (0x8000, 0x8000 + margin),
                (0x8000, 0x8000),
            ]
            for i in range(len(points)):
                pt = points[i]
                x, y = mx_rotate(pt)
                x = int(x)
                y = int(y)
                points[i] = x, y
            return points

        if bounds is None:
            # bounds is None, default crosshair
            points = crosshairs()
        else:
            # Bounds exist
            xmin, ymin, xmax, ymax = bounds
            points = [
                (xmin, ymin),
                (xmax, ymin),
                (xmax, ymax),
                (xmin, ymax),
                (xmin, ymin),
            ]
            for i in range(len(points)):
                pt = points[i]
                x, y = self.service.scene_to_device_position(*pt)
                x, y = mx_rotate((x, y))
                x = int(x)
                y = int(y)
                if 0 <= x <= 0xFFFF and 0 <= y <= 0xFFFF:
                    points[i] = x, y
                else:
                    # Our bounds are not in frame.
                    points = crosshairs()
                    break
        self._current_points = points
        self._last_bounds = bounds
        return self._current_points, True

    def stop(self):
        self.stopped = True

    def process(self, con):
        if self.stopped:
            return False
        con.light_mode()

        jump_delay = self.service.delay_jump_long
        dark_delay = self.service.delay_jump_short
        con._light_speed = self.service.redlight_speed

        bounds = self.service.elements.selected_area()
        first_run = self._current_points is None
        points, update = self.update_points(bounds)
        if update and not first_run:
            con.abort()
            first_x = 0x8000
            first_y = 0x8000
            if len(points):
                first_x, first_y = points[0]
            con.goto_xy(first_x, first_y, distance=0xFFFF)
            con.light_mode()

        if self.stopped:
            return False
        #
        # x, y = points[0]
        # con.light(x, y, long=dark_delay, short=dark_delay)
        for pt in points:
            if self.stopped:
                return False
            con.light(*pt, long=jump_delay, short=jump_delay)
        return True


class LiveFullLightJob:
    def __init__(
        self,
        service,
    ):
        self.service = service
        self.stopped = False
        self.changed = False
        service.listen("emphasized", self.on_emphasis_changed)

    def stop(self):
        self.stopped = True
        self.service.unlisten("emphasized", self.on_emphasis_changed)

    def on_emphasis_changed(self, *args):
        self.changed = True

    def crosshairs(self, con):
        # Calculate rotate matrix.
        rotate = Matrix()
        rotate.post_rotate(self.service.redlight_angle.radians, 0x8000, 0x8000)
        x_offset = self.service.length(
            self.service.redlight_offset_x, axis=0, as_float=True
        )
        y_offset = self.service.length(
            self.service.redlight_offset_y, axis=1, as_float=True
        )
        rotate.post_translate(x_offset, y_offset)

        # Function for using rotate
        def mx_rotate(pt):
            if pt is None:
                return None
            return (
                pt[0] * rotate.a + pt[1] * rotate.c + 1 * rotate.e,
                pt[0] * rotate.b + pt[1] * rotate.d + 1 * rotate.f,
            )

        margin = 5000
        points = [
            (0x8000, 0x8000),
            (0x8000 - margin, 0x8000),
            (0x8000, 0x8000),
            (0x8000, 0x8000 - margin),
            (0x8000, 0x8000),
            (0x8000 + margin, 0x8000),
            (0x8000, 0x8000),
            (0x8000, 0x8000 + margin),
            (0x8000, 0x8000),
        ]
        for i in range(len(points)):
            pt = points[i]
            x, y = mx_rotate(pt)
            x = int(x)
            y = int(y)
            points[i] = x, y

        jump_delay = self.service.delay_jump_long
        dark_delay = self.service.delay_jump_short
        for pt in points:
            if self.stopped:
                return False
            con.light(*pt, long=jump_delay, short=dark_delay)
        return True

    def process(self, con):
        if self.stopped:
            return False
        if self.changed:
            self.changed = False
            con.abort()
            con.light_mode()
            con.goto_xy(0x8000, 0x8000)

        jump_delay = self.service.delay_jump_long
        dark_delay = self.service.delay_jump_short
        con._light_speed = self.service.redlight_speed

        con.light_mode()
        elements = list(self.service.elements.elems(emphasized=True))

        if not elements:
            return self.crosshairs(con)

        x_offset = self.service.length(
            self.service.redlight_offset_x, axis=0, as_float=True
        )
        y_offset = self.service.length(
            self.service.redlight_offset_y, axis=1, as_float=True
        )
        quantization = 50
        rotate = Matrix()
        rotate.post_rotate(self.service.redlight_angle.radians, 0x8000, 0x8000)
        rotate.post_translate(x_offset, y_offset)

        con._light_speed = self.service.redlight_speed

        def mx_rotate(pt):
            if pt is None:
                return None
            return (
                pt[0] * rotate.a + pt[1] * rotate.c + 1 * rotate.e,
                pt[0] * rotate.b + pt[1] * rotate.d + 1 * rotate.f,
            )

        for node in elements:
            if self.stopped:
                return False
            if self.changed:
                return True
            e = node.as_path()
            if not e:
                continue
            x, y = e.point(0)
            x, y = self.service.scene_to_device_position(x, y)
            x, y = mx_rotate((x, y))
            x = int(x) & 0xFFFF
            y = int(y) & 0xFFFF
            if isinstance(e, (Polygon, Polyline)):
                con.dark(x, y, long=dark_delay, short=dark_delay)
                for pt in e:
                    if self.stopped:
                        return False
                    if self.changed:
                        return True
                    x, y = self.service.scene_to_device_position(*pt)
                    x, y = mx_rotate((x, y))
                    x = int(x) & 0xFFFF
                    y = int(y) & 0xFFFF
                    con.light(x, y, long=jump_delay, short=jump_delay)
                continue

            con.dark(x, y, long=dark_delay, short=dark_delay)
            for i in range(1, quantization + 1):
                if self.stopped:
                    return False
                if self.changed:
                    return True
                x, y = e.point(i / float(quantization))
                x, y = self.service.scene_to_device_position(x, y)
                x, y = mx_rotate((x, y))
                x = int(x) & 0xFFFF
                y = int(y) & 0xFFFF
                con.light(x, y, long=jump_delay, short=jump_delay)
        con.light_off()
        return True


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

        self.register(
            "format/op cut",
            "{enabled}{pass}{element_type} {speed}mm/s @{power} {frequency}kHz",
        )
        self.register(
            "format/op engrave",
            "{enabled}{pass}{element_type} {speed}mm/s @{power} {frequency}kHz",
        )
        self.register(
            "format/op hatch",
            "{enabled}{penpass}{pass}{element_type} {speed}mm/s @{power} {frequency}kHz",
        )
        self.register(
            "format/op raster",
            "{enabled}{pass}{element_type}{direction}{speed}mm/s @{power} {frequency}kHz",
        )
        self.register(
            "format/op image",
            "{enabled}{penvalue}{pass}{element_type}{direction}{speed}mm/s @{power} {frequency}kHz",
        )
        self.register(
            "format/op dots",
            "{enabled}{pass}{element_type} {dwell_time}ms dwell {frequency}kHz",
        )
        self.register("format/util console", "{enabled}{command}")

        choices = [
            {
                "attr": "label",
                "object": self,
                "default": "balor-device",
                "type": str,
                "label": _("Label"),
                "tip": _("What is this device called."),
            },
            {
                "attr": "corfile_enabled",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Enable Correction File"),
                "tip": _("Use correction file?"),
            },
            {
                "attr": "corfile",
                "object": self,
                "default": None,
                "type": str,
                "style": "file",
                "wildcard": "*.cor",
                "conditional": (self, "corfile_enabled"),
                "label": _("Correction File"),
                "tip": _("Provide a correction file for the machine"),
            },
            {
                "attr": "lens_size",
                "object": self,
                "default": "110mm",
                "type": Length,
                "label": _("Width"),
                "tip": _("Lens Size"),
            },
            {
                "attr": "offset_x",
                "object": self,
                "default": "0mm",
                "type": Length,
                "label": _("Offset X"),
                "tip": _("Offset in the X axis"),
            },
            {
                "attr": "offset_y",
                "object": self,
                "default": "0mm",
                "type": Length,
                "label": _("Offset Y"),
                "tip": _("Offset in the Y axis"),
            },
            {
                "attr": "scale_x",
                "object": self,
                "default": "0",
                "type": float,
                "label": _("Scale X"),
                "tip": _("Scale the X axis"),
            },
            {
                "attr": "scale_y",
                "object": self,
                "default": "0",
                "type": float,
                "label": _("Scale Y"),
                "tip": _("Scale the Y axis"),
            },
            {
                "attr": "flip_x",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Flip X"),
                "tip": _("Flip the X axis for the Balor device"),
            },
            {
                "attr": "flip_y",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Flip Y"),
                "tip": _("Flip the Y axis for the Balor device"),
            },
            {
                "attr": "swap_xy",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Swap XY"),
                "tip": _("Swap the X and Y axis for the device"),
            },
            {
                "attr": "interpolate",
                "object": self,
                "default": 50,
                "type": int,
                "label": _("Curve Interpolation"),
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
            },
            {
                "attr": "footpedal_pin",
                "object": self,
                "default": 15,
                "type": int,
                "label": _("Pin Index of footpedal"),
                "tip": _("What pin is your foot pedal hooked to on the GPIO"),
            },
            {
                "attr": "light_pin",
                "object": self,
                "default": 8,
                "type": int,
                "label": _("Pin Index of redlight laser"),
                "tip": _("What pin is your redlight hooked to on the GPIO"),
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
                "label": _("Redlight X Offset"),
                "tip": _("Offset the redlight positions by this amount in x"),
            },
            {
                "attr": "redlight_offset_y",
                "object": self,
                "default": "0mm",
                "type": Length,
                "label": _("Redlight Y Offset"),
                "tip": _("Offset the redlight positions by this amount in y"),
            },
            {
                "attr": "redlight_angle",
                "object": self,
                "default": "0deg",
                "type": Angle,
                "label": _("Redlight Angle Offset"),
                "tip": _(
                    "Offset the redlight positions by this angle, curving around center"
                ),
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
                "tip": _("How what power level do we cut at?"),
            },
            {
                "attr": "default_speed",
                "object": self,
                "default": 100.0,
                "type": float,
                "label": _("Cut Speed"),
                "tip": _("How fast do we cut?"),
            },
            {
                "attr": "default_frequency",
                "object": self,
                "default": 30.0,
                "type": float,
                "label": _("Q Switch Frequency"),
                "tip": _("QSwitch Frequency value"),
            },
            {
                "attr": "default_rapid_speed",
                "object": self,
                "default": 2000.0,
                "type": float,
                "label": _("Travel Speed"),
                "tip": _("How fast do we travel when not cutting?"),
            },
            {
                "attr": "pulse_width_enabled",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Enable Pulse Width"),
                "tip": _("Enable using Pulse Width (MOPA)"),
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
                "tip": _("Set the MOPA pulse width setting"),
            },
        ]
        self.register_choices("balor-global", choices)

        choices = [
            {
                "attr": "delay_laser_on",
                "object": self,
                "default": 100.0,
                "type": float,
                "label": _("Laser On Delay"),
                "tip": _("Delay for the start of the laser"),
            },
            {
                "attr": "delay_laser_off",
                "object": self,
                "default": 100.0,
                "type": float,
                "label": _("Laser Off Delay"),
                "tip": _("Delay amount for the end of the laser"),
            },
            {
                "attr": "delay_polygon",
                "object": self,
                "default": 100.0,
                "type": float,
                "label": _("Polygon Delay"),
                "tip": _("Delay amount between different points in the path travel."),
            },
            {
                "attr": "delay_end",
                "object": self,
                "default": 300.0,
                "type": float,
                "label": _("End Delay"),
                "tip": _("Delay amount for the end TC"),
            },
            {
                "attr": "delay_jump_long",
                "object": self,
                "default": 200.0,
                "type": float,
                "label": _("Jump Delay (long)"),
                "tip": _("Delay for a long jump distance"),
            },
            {
                "attr": "delay_jump_short",
                "object": self,
                "default": 8,
                "type": float,
                "label": _("Jump Delay (short)"),
                "tip": _("Delay for a short jump distance"),
            },
            {
                "attr": "delay_distance_long",
                "object": self,
                "default": "10mm",
                "type": Length,
                "label": _("Long jump distance"),
                "tip": _("Distance divide between long and short jump distances"),
            },
            {
                "attr": "delay_openmo",
                "object": self,
                "default": 8.0,
                "type": float,
                "label": _("Open MO delay"),
                "tip": _("OpenMO delay in ms"),
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
                "tip": _("Unknown"),
            },
            {
                "attr": "pwm_half_period",
                "object": self,
                "default": 125,
                "type": int,
                "label": _("PWM Half Period"),
                "tip": _("Unknown"),
            },
            {
                "attr": "pwm_pulse_width",
                "object": self,
                "default": 125,
                "type": int,
                "label": _("PWM Pulse Width"),
                "tip": _("Unknown"),
            },
            {
                "attr": "standby_param_1",
                "object": self,
                "default": 2000,
                "type": int,
                "label": _("Standby Parameter 1"),
                "tip": _("Unknown"),
            },
            {
                "attr": "standby_param_2",
                "object": self,
                "default": 20,
                "type": int,
                "label": _("Standby Parameter 2"),
                "tip": _("Unknown"),
            },
            {
                "attr": "timing_mode",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("Timing Mode"),
                "tip": _("Unknown"),
            },
            {
                "attr": "delay_mode",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("Delay Mode"),
                "tip": _("Unknown"),
            },
            {
                "attr": "laser_mode",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("Laser Mode"),
                "tip": _("Unknown"),
            },
            {
                "attr": "control_mode",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Control Mode"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fpk2_p1",
                "object": self,
                "default": 0xFFB,
                "type": int,
                "label": _("First Pulse Killer, Parameter 1"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fpk2_p2",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("First Pulse Killer, Parameter 2"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fpk2_p3",
                "object": self,
                "default": 409,
                "type": int,
                "label": _("First Pulse Killer, Parameter 3"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fpk2_p4",
                "object": self,
                "default": 100,
                "type": int,
                "label": _("First Pulse Killer, Parameter 4"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fly_res_p1",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Fly Res, Parameter 1"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fly_res_p2",
                "object": self,
                "default": 99,
                "type": int,
                "label": _("Fly Res, Parameter 2"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fly_res_p3",
                "object": self,
                "default": 1000,
                "type": int,
                "label": _("Fly Res, Parameter 3"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fly_res_p4",
                "object": self,
                "default": 25,
                "type": int,
                "label": _("Fly Res, Parameter 4"),
                "tip": _("Unknown"),
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

        @self.console_command(
            "spool",
            help=_("spool <command>"),
            regex=True,
            input_type=(None, "plan", "device"),
            output_type="spooler",
        )
        def spool(
            command, channel, _, data=None, data_type=None, remainder=None, **kwgs
        ):
            """
            Registers the spool command for the Balor driver.
            """
            spooler = self.spooler
            if data is not None:
                # If plan data is in data, then we copy that and move on to next step.
                spooler.jobs(data.plan)
                channel(_("Spooled Plan."))
                self.signal("plan", data.name, 6)

            if remainder is None:
                channel(_("----------"))
                channel(_("Spoolers:"))
                for d, d_name in enumerate(self.match("device", suffix=True)):
                    channel("%d: %s" % (d, d_name))
                channel(_("----------"))
                channel(_("Spooler on device %s:" % str(self.label)))
                for s, op_name in enumerate(spooler.queue):
                    channel("%d: %s" % (s, op_name))
                channel(_("----------"))

            return "spooler", spooler

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
            self.spooler.job(("light_loop", self.job.process))

        @self.console_command(
            "select-light", help=_("Execute selection light idle job")
        )
        def select_light(**kwargs):
            if self.job is not None:
                self.job.stop()
            self.job = LiveSelectionLightJob(self)
            self.spooler.job(("light_loop", self.job.process))

        @self.console_command("full-light", help=_("Execute full light idle job"))
        def select_light(**kwargs):
            if self.job is not None:
                self.job.stop()
            self.job = LiveFullLightJob(self)
            self.spooler.job(("light_loop", self.job.process))

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
            self.spooler.set_idle(None)
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

        @self.console_command(
            "resume",
            help=_("Resume the currently running job"),
        )
        def resume(command, channel, _, data=None, remainder=None, **kwgs):
            channel("Resume the current job")
            self.driver.resume()

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
                    _('"%sms" exceeds 1 second limit to fire a standing laser.') % time
                )
                try:
                    if not idonotlovemyhouse:
                        return
                except IndexError:
                    return
            if self.spooler.job_if_idle(("pulse", time)):
                channel(_("Pulse laser for %f milliseconds") % time)
            else:
                channel(_("Pulse laser failed: Busy"))
            return

        @self.console_command(
            "usb_connect",
            help=_("connect usb"),
        )
        def usb_connect(command, channel, _, data=None, remainder=None, **kwgs):
            self.spooler.job("connect")

        @self.console_command(
            "usb_disconnect",
            help=_("connect usb"),
        )
        def usb_connect(command, channel, _, data=None, remainder=None, **kwgs):
            self.spooler.job("disconnect")

        @self.console_command("usb_abort", help=_("Stops USB retries"))
        def usb_abort(command, channel, _, **kwargs):
            self.spooler.job("abort_retry")

        @self.console_option(
            "default",
            "d",
            help=_("Allow default list commands to persist within the raw command"),
            type=bool,
            action="store_true",
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
        def galvo_raw(channel, _, default=False, input=None, output=None, remainder=None, **kwgs):
            from meerk40t.balormk.lmc_controller import list_command_lookup

            reverse_lookup = {}
            for k in list_command_lookup:
                command_string = list_command_lookup[k]
                reverse_lookup[command_string] = k
                reverse_lookup[command_string.lower()[4:]] = k

            if remainder is None and input is None:
                # List permitted commands.
                channel("Permitted Commands:")
                for k in list_command_lookup:
                    command_string = list_command_lookup[k]
                    channel(f"{command_string.lower()[4:]} aka {k:04x}")
                return

            if input is not None:
                from os.path import exists

                if exists(input):
                    channel(f"Loading data from: {input}")
                    try:
                        with open(input, "r") as f:
                            remainder = f.read()
                    except IOError:
                        pass
                else:
                    channel(f"The file at {os.path.realpath(input)} does not exist.")
                    return

            cmds = list(re.split("[,\n\r]", remainder))

            raw_commands = list()

            # Compile commands.
            for cmd_i, cmd in enumerate(cmds):
                cmd = cmd.strip()
                if not cmd:
                    continue

                values = [0] * 6
                byte_i = 0
                for b in cmd.split(" "):
                    if b == "":
                        # Double-Space
                        continue
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

            if output is None:
                # output to device.
                self.driver.connection.rapid_mode()
                self.driver.connection.program_mode()
                if not default:
                    self.driver.connection.raw_clear()
                for v in raw_commands:
                    self.driver.connection.raw_write(*v)
                self.driver.connection.rapid_mode()
            else:
                if output is not None:
                    channel(f"Writing data to: {output}")
                    try:
                        lines = []
                        for v in raw_commands:
                            lines.append(f"{list_command_lookup.get(v[0],f'{v[0]:04x}').ljust(20)} "
                                         f"{v[1]:04x} {v[2]:04x} {v[3]:04x} {v[4]:04x} {v[5]:04x}\n")
                        with open(output, "w") as f:
                            f.writelines(lines)
                            # f.write(remainder)
                    except IOError:
                        channel("File could not be written.")

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
            reply = self.driver.connection.init_laser()
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
        def balor_status(command, channel, _, remainder=None, **kwgs):
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
        def balor_status(command, channel, _, remainder=None, **kwgs):
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
        def balor_status(command, channel, _, remainder=None, **kwgs):
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
        def balor_status(command, channel, _, remainder=None, **kwgs):
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
        def balor_status(command, channel, _, remainder=None, **kwgs):
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
        def balor_status(command, channel, _, remainder=None, **kwgs):
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
        def balor_status(command, channel, _, remainder=None, **kwgs):
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
        def balor_status(command, channel, _, remainder=None, **kwgs):
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
        def balor_status(command, channel, _, remainder=None, **kwgs):
            reply = self.driver.connection.get_fiber_st_mo_ap()
            if reply is None:
                channel("Not connected, cannot get fiber_st_mo_ap.")
                return
            channel(f"Command replied: {reply}")
            for index, b in enumerate(reply):
                channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

        @self.console_command(
            "input_port",
            help=_("Checks the input_port"),
        )
        def balor_status(command, channel, _, remainder=None, **kwgs):
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
        def balor_status(command, channel, _, remainder=None, **kwgs):
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
                    channel(
                        "Correction file is set to: {file}".format(file=self.corfile)
                    )
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
                    channel(
                        "The file at {filename} does not exist.".format(
                            filename=os.path.realpath(filename)
                        )
                    )
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
            self.bedwidth = lens_size
            self.bedheight = lens_size

            channel(
                "Set Bed Size : ({sx}, {sy}).".format(
                    sx=self.bedwidth, sy=self.bedheight
                )
            )

            self.signal("bed_size")

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
        def element_outline(
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
            channel("Element bounds: {bounds}".format(bounds=str(bounds)))
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
        def element_outline(command, channel, _, data=None, args=tuple(), **kwargs):
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
    def calibration_file(self):
        return None
