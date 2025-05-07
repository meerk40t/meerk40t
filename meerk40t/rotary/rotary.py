import math

from meerk40t.core.units import Length
from meerk40t.kernel import lookup_listener, signal_listener
from meerk40t.svgelements import Matrix


def plugin(service, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]
    if lifecycle == "service":
        # Responding to "service" makes this a service plugin for the specific services created via the provider
        # We are only a provider of lhystudios devices for now.
        return (
            "provider/device/lhystudios",
            "provider/device/grbl",
            "provider/device/balor",
            "provider/device/newly",
            "provider/device/moshi",
        )
    elif lifecycle == "added":
        service.add_service_delegate(Rotary(service, 0))


class Rotary:
    """
    Rotary Class
    The `Rotary` class provides functionality for managing rotary settings and operations
    for a device. It supports two types of rotary modes: roller and chuck. The class
    registers configuration options, provides console commands, and listens to signals
    to handle changes in rotary settings.
    Attributes:
        index (int): The index of the rotary instance.
        service (object): The service object to which this rotary instance is attached.
    Methods:
        __init__(service, index=0, *args, **kwargs):
            Initializes the rotary instance, registers choices for rotary settings,
            and defines console commands.
        scale_x (property):
            Returns the X-axis scale factor if the roller rotary mode is active,
            otherwise returns 1.0.
        scale_y (property):
            Returns the Y-axis scale factor if the roller rotary mode is active,
            otherwise returns 1.0.
        active (property):
            Returns True if either roller or chuck rotary mode is active, otherwise False.
        flip_x (property):
            Returns True if the X-axis mirroring is enabled in roller rotary mode,
            otherwise False.
        flip_y (property):
            Returns True if the Y-axis mirroring is enabled in roller rotary mode,
            otherwise False.
        suppress_home (property):
            Returns True if the "Ignore Home" option is enabled, otherwise False.
        rotary_settings_changed(origin=None, *args):
            Signal listener that handles changes in rotary settings and forces the
            current device to realize the changes.
        realize(origin=None, *args):
            Signal listener that updates the device's view with the rotary settings
            when the device is realized.
        service_detach(*args, **kwargs):
            Placeholder method for detaching the service.
        service_attach(*args, **kwargs):
            Placeholder method for attaching the service.
        shutdown(*args, **kwargs):
            Placeholder method for shutting down the rotary service.
    Console Commands:
        rotary:
            Base command for rotary operations. Outputs the current rotary scale settings.
        rotaryscale:
            Applies the rotary scale to selected elements.
    Signal Listeners:
        - rotary_active_roller
        - rotary_scale_x
        - rotary_scale_y
        - rotary_active_chuck
        - rotary_flip_x
        - rotary_flip_y
        - view;realized
    Listeners ensure that changes in rotary settings are applied to the device and its view.
    Usage:
        This class is used as part of a service to manage rotary settings and operations
        for devices that support rotary functionality.
    """

    def __init__(self, service, index=0, *args, **kwargs):
        self.index = index
        self.service = service
        service.rotary = self
        self._rotary_active_chuck = False
        self._rotary_active_roller = False
        self.rotary_suppress_home = False
        self.rotary_scale_x = 1.0
        self.rotary_scale_y = 1.0
        self.rotary_microsteps_per_revolution = 6400
        self.object_diameter = Length("1cm")
        self.rotary_flip_x = False
        self.rotary_flip_y = False
        self.rotary_suppress_home = False
        self.rotary_reverse = False
        self.rotary_chuck_alignment_axis = 0
        self.rotary_chuck_offset = 0.5

        _ = service._
        choices = [
            {
                "attr": "rotary_active_roller",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Roller-Mode active"),
                "signals": "device;modified",
                "tip": _("Is the roller rotary mode active for this device"),
                "conditional": (service, "supports_rotary_roller"),
            },
            {
                "attr": "rotary_scale_x",
                "object": self,
                "default": 1.0,
                "type": float,
                "label": _("X-Scale"),
                "tip": _("Scale that needs to be applied to the X-Axis"),
                "conditional": (self, "rotary_active_roller"),
                "subsection": _("Scale"),
            },
            {
                "attr": "rotary_scale_y",
                "object": self,
                "default": 1.0,
                "type": float,
                "label": _("Y-Scale"),
                "tip": _("Scale that needs to be applied to the Y-Axis"),
                "conditional": (self, "rotary_active_roller"),
                "subsection": _("Scale"),
            },
            {
                "attr": "rotary_flip_x",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mirror X"),
                "tip": _("Mirror the elements on the X-Axis"),
                "conditional": (self, "rotary_active_roller"),
                "subsection": _("Mirror Output"),
            },
            {
                "attr": "rotary_flip_y",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mirror Y"),
                "tip": _("Mirror the elements on the Y-Axis"),
                "conditional": (self, "rotary_active_roller"),
                "subsection": _("Mirror Output"),
            },
        ]
        service.register_choices("rotary_roller", choices)

        choices = [
            {
                "attr": "rotary_active_chuck",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Chuck-Mode active"),
                "tip": _("Is the chuck rotary mode active for this device"),
                "signals": "device;modified",
                "conditional": (service, "supports_rotary_chuck"),
            },
            {
                "attr": "rotary_microsteps_per_revolution",
                "object": self,
                "default": False,
                "type": int,
                "label": _("Micro-Steps"),
                "tip": _("How many microsteps are required for a single revolution"),
                "style": "combosmall",
                "exclusive": False,
                "choices": (
                    200,
                    400,
                    800,
                    1600,
                    3200,
                    6400,
                    12800,
                    25600,
                    1000,
                    2000,
                    4000,
                    8000,
                    10000,
                    20000,
                    25000,
                ),
                "signals": "device;modified",
                "conditional": (self, "rotary_active_chuck"),
            },
            {
                "attr": "object_diameter",
                "object": self,
                "default": Length("1cm"),
                "type": Length,
                "label": _("Object-Diameter"),
                "tip": _("Diameter of the unit in the rotary chuck"),
                "signals": "device;modified",
                "conditional": (self, "rotary_active_chuck"),
            },
            {
                "attr": "rotary_reverse",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Reverse"),
                "tip": _("Reverse the rotation direction"),
                "conditional": (self, "rotary_active_chuck"),
                "subsection": _("Mirror Output"),
            },
            {
                "attr": "rotary_chuck_alignment_axis",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Aligned to axis"),
                "style": "option",
                "choices": (0, 1),
                "display": (
                    _("X-Axis"),
                    _("Y-Axis"),
                ),
                "tip": _(
                    "How is your rotary aligned: perpendicular to the X- or the Y-Axis?"
                ),
                "conditional": (self, "rotary_active_chuck"),
                "subsection": _("Orientation"),
            },
            {
                "attr": "rotary_chuck_offset",
                "object": self,
                "default": 0.5,
                "type": float,
                "label": _("Rotary position"),
                "tip": _(
                    "Where is the position of the rotary along the alignment axis?"
                ),
                "conditional": (self, "rotary_active_chuck"),
                "subsection": _("Orientation"),
            },
        ]
        service.register_choices("rotary_chuck", choices)

        choices = [
            {
                "attr": "rotary_suppress_home",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Ignore Home"),
                "tip": _("Ignore Home-Command"),
                "conditional": (self, "active"),
            },
        ]
        service.register_choices("rotary_common", choices)

        def show_rotary_settings(channel):
            """
            Show the rotary settings in the console.
            """
            # fmt: off
            if service.rotary.rotary_active_roller:
                channel(_("Rotary active: Roller-Mode"))
                channel(f"  Scale X: {service.rotary.rotary_scale_x:.3f}")
                channel(f"  Scale Y: {service.rotary.rotary_scale_y:.3f}")
                channel(f"  Flip X: {'Yes' if service.rotary.rotary_flip_x else 'No'}")
                channel(f"  Flip Y: {'Yes' if service.rotary.rotary_flip_y else 'No'}")
                channel(f"  Suppress Home: {'Yes' if service.rotary.suppress_home else 'No'}")
            elif service.rotary.rotary_active_chuck:
                channel(_("Rotary active: Chuck-Mode"))
                channel(f"  Microsteps per revolution: {service.rotary.rotary_microsteps_per_revolution}")
                channel(f"  Object Diameter: {Length(service.rotary.object_diameter).length_mm}")
                channel(f"  Reverse: {'Yes' if service.rotary.rotary_reverse else 'No'}")
                channel(f"  Suppress Home: {'Yes' if service.rotary.suppress_home else 'No'}")
                channel(f"  Aligned to axis: {'X-Axis' if service.rotary.rotary_chuck_alignment_axis == 0 else 'Y-Axis'}")
                zero_pos = Length(f"{service.rotary.rotary_chuck_offset*100}%", relative_length=service.view.width if service.rotary.rotary_chuck_alignment_axis == 0 else service.view.height)
                channel(f"  Rotary position: {service.rotary.rotary_chuck_offset*100:.1f}% ({zero_pos.length_mm})")
            else:
                channel(_("No rotary mode active."))
            # fmt: on

        @service.console_command(
            "rotary",
            help=_("Rotary base command"),
            output_type="rotary",
        )
        def rotary(command, channel, _, data=None, remainder=None, **kwargs):
            if remainder is None:
                channel("Valid commands: roller, chuck, off, settings")
            return "rotary", None

        @service.console_command(
            "off",
            help=_("Turn rotary off"),
            input_type="rotary",
            output_type="rotary",
        )
        def command_off(command, channel, _, data=None, **kwargs):
            service.rotary.rotary_active_roller = False
            service.rotary.rotary_active_chuck = False
            channel(_("Rotary mode deactivated."))
            service.device.realize()
            return "rotary", None

        @service.console_command(
            "roller",
            help=_("Turn rotary roller mode on"),
            input_type="rotary",
            output_type="rotary",
        )
        def command_roller(command, channel, _, data=None, **kwargs):
            if getattr(service, "supports_rotary_roller", False):
                service.rotary.rotary_active_roller = True
                service.rotary.rotary_active_chuck = False
                service.device.realize()
                show_rotary_settings(channel)
            else:
                channel(_("This device does not support a rotary roller mode."))
            return "rotary", None

        @service.console_command(
            "chuck",
            help=_("Turn rotary chuck mode on"),
            input_type="rotary",
            output_type="rotary",
        )
        def command_chuck(command, channel, _, data=None, **kwargs):
            if getattr(service, "supports_rotary_chuck", False):
                service.rotary.rotary_active_roller = False
                service.rotary.rotary_active_chuck = True
                service.device.realize()
                show_rotary_settings(channel)
            else:
                channel(_("This device does not support a rotary chuck mode."))
            return "rotary", None

        @service.console_command(
            "settings",
            help=_("Set/show individual rotary settings"),
            input_type="rotary",
            output_type="rotary",
        )
        def command_settings(command, channel, _, data=None, remainder=None, **kwargs):
            if remainder is not None:
                # Split the remainder into key-value pairs
                settings = remainder.split(",")
                for setting in settings:
                    try:
                        key, value = setting.split("=")
                        key = key.strip()
                        value = value.strip()
                        if hasattr(service.rotary, key):
                            setattr(service.rotary, key, value)
                            channel(f"Set {key} to {value}.")
                        else:
                            channel(f"Invalid setting: {key}.")
                    except ValueError:
                        channel(f"Invalid setting format: {setting}.")
            show_rotary_settings(channel)
            return "rotary", None

        @service.console_command(
            "rotaryscale", help=_("Rotary Scale selected elements")
        )
        def apply_rotary_scale(*args, **kwargs):
            sx = service.rotary_scale_x
            sy = service.rotary_scale_y
            x, y = service.device.current
            matrix = Matrix(f"scale({sx}, {sy}, {x}, {y})")
            for node in service.elements.elems():
                if hasattr(node, "rotary_scale"):
                    # This element is already scaled
                    return
                try:
                    node.rotary_scale = sx, sy
                    node.matrix *= matrix
                    node.modified()
                except AttributeError:
                    pass

    @property
    def rotary_active_roller(self):
        return self._rotary_active_roller

    @rotary_active_roller.setter
    def rotary_active_roller(self, value):
        self._rotary_active_roller = value
        if value:
            self._rotary_active_chuck = False

    @property
    def rotary_active_chuck(self):
        return self._rotary_active_chuck

    @rotary_active_chuck.setter
    def rotary_active_chuck(self, value):
        self._rotary_active_chuck = value
        if value:
            self._rotary_active_roller = False

    @property
    def scale_x(self):
        return self.rotary_scale_x if self.rotary_active_roller else 1.0

    @property
    def scale_y(self):
        return self.rotary_scale_y if self.rotary_active_roller else 1.0

    @property
    def active(self):
        return self.rotary_active_roller or self.rotary_active_chuck

    @property
    def flip_x(self):
        return self.rotary_flip_x if self.rotary_active_roller else False

    @property
    def flip_y(self):
        return self.rotary_flip_y if self.rotary_active_roller else False

    @property
    def suppress_home(self):
        return self.rotary_suppress_home

    @lookup_listener("service/device/active")
    @signal_listener("rotary_scale_x")
    @signal_listener("rotary_scale_y")
    @signal_listener("rotary_flip_x")
    @signal_listener("rotary_flip_y")
    @signal_listener("rotary_active_chuck")
    @signal_listener("rotary_active_roller")
    def rotary_settings_changed(self, origin=None, *args):
        """
        Rotary settings were changed. We force the current device to realize

        @param origin:
        @param args:
        @return:
        """
        if origin is not None and origin != self.service.path:
            return
        self.service.device.realize()

    @signal_listener("view;realized")
    def realize(self, origin=None, *args):
        """
        Realization of current device requires that device to be additionally updated with rotary
        @param origin:
        @param args:
        @return:
        """
        if not self.rotary_active_roller:
            return
        device = self.service.device
        device.view.scale(self.scale_x, self.scale_y)
        if self.rotary_flip_x:
            device.view.flip_x()
        if self.rotary_flip_y:
            device.view.flip_y()

    def service_detach(self, *args, **kwargs):
        pass

    def service_attach(self, *args, **kwargs):
        pass

    def shutdown(self, *args, **kwargs):
        pass


def map_coordinates_to_rotary(
    x_coord: float,
    y_coord_input: float,
    cylinder_diameter: float,
    y_rotary_origin: float,
    hardware_microsteps_per_rev: int,
    virtual_microsteps_per_rev: int = None,
) -> tuple[float, int, float]:
    """
    Maps a Y-coordinate to a rotary axis position for a laser cutter.

    The X-coordinate remains unchanged. The Y-coordinate is mapped to an angular
    position on the cylinder's surface.

    Args:
        x_coord: The original X-coordinate from the flatbed.
        y_coord_input: The Y-coordinate from the flatbed.
        cylinder_diameter: The diameter of the cylinder on the rotary attachment.
                           Units must be consistent with y_coord_input and y_rotary_origin.
        y_rotary_origin: The Y-coordinate on the flatbed that corresponds to
                         angle 0 (the starting angle) on the rotary attachment.
        hardware_microsteps_per_rev: The total number of microsteps the rotary motor
                                     requires for one full 360-degree revolution
                                     (e.g., 6400).
        virtual_microsteps_per_rev: Optional. If provided, this defines a coarser
                                    segmentation for the rotary movement. The output
                                    rotation will be the closest step achievable within
                                    this virtual resolution (e.g., 1000). If None or
                                    not coarser than hardware resolution, hardware
                                    resolution is used.

    Returns:
        A tuple containing:
        - output_x_coord: The original X-coordinate (unchanged).
        - closest_rotation_hardware_steps: The calculated target microsteps for the
                                           rotary motor (integer). This value represents
                                           the absolute hardware step count from the
                                           zero-angle position. It can be positive
                                           (for y_coord_input > y_rotary_origin) or
                                           negative, and can exceed
                                           hardware_microsteps_per_rev if the mapped
                                           distance is greater than one circumference.
        - y_gap: The difference in length units (same as y_coord_input) between the
                 desired Y-position mapped onto the cylinder surface and the actual
                 Y-position achievable with the closest (virtual or hardware)
                 rotation step.
                 A positive gap means the achieved position is short of the target.
                 A negative gap means the achieved position is beyond the target.
    """

    if cylinder_diameter <= 0:
        raise ValueError("Cylinder diameter must be positive.")
    if hardware_microsteps_per_rev <= 0:
        raise ValueError("Hardware microsteps per revolution must be positive.")
    if virtual_microsteps_per_rev is not None and virtual_microsteps_per_rev <= 0:
        raise ValueError(
            "Virtual microsteps per revolution must be positive if provided."
        )

    output_x_coord = x_coord

    # 1. Calculate the effective Y-distance to be mapped onto the cylinder surface.
    # This is the arc length on the cylinder.
    y_on_surface_desired = y_coord_input - y_rotary_origin

    # 2. Calculate the circumference of the cylinder.
    circumference = math.pi * cylinder_diameter

    # Handle edge case of zero circumference (though diameter > 0 should prevent this).
    if circumference == 0:
        if y_on_surface_desired == 0:
            return output_x_coord, 0, 0.0
        else:
            # Cannot achieve a non-zero surface distance on a zero-circumference cylinder.
            # The gap is effectively the entire desired distance.
            return output_x_coord, 0, y_on_surface_desired

    # 3. Calculate the ideal target position in terms of hardware microsteps.
    # This can be a fractional value.
    # (desired_arc_length / total_arc_length_per_rev) * total_steps_per_rev
    target_exact_hardware_steps = (
        y_on_surface_desired / circumference
    ) * hardware_microsteps_per_rev

    # 4. Determine the closest achievable hardware steps, considering virtual resolution if specified.
    closest_rotation_hardware_steps: int

    use_virtual_resolution = (
        virtual_microsteps_per_rev is not None
        and 0 < virtual_microsteps_per_rev < hardware_microsteps_per_rev
    )

    if use_virtual_resolution:
        # a. Calculate the size of one "virtual step" in terms of hardware microsteps.
        hw_steps_per_virtual_step = (
            hardware_microsteps_per_rev / virtual_microsteps_per_rev
        )

        # b. Determine the target position in terms of virtual step units (can be fractional).
        # target_virtual_step_float = target_exact_hardware_steps / hw_steps_per_virtual_step
        # or equivalently:
        target_virtual_step_float = (
            y_on_surface_desired / circumference
        ) * virtual_microsteps_per_rev

        # c. Find the index of the closest integer virtual step.
        closest_virtual_step_index = round(target_virtual_step_float)

        # d. Convert this closest virtual step index back to the corresponding hardware step value.
        # This value represents the center of the chosen virtual step, rounded to the nearest
        # whole hardware microstep.
        closest_rotation_hardware_steps = int(
            round(closest_virtual_step_index * hw_steps_per_virtual_step)
        )
    else:
        # No virtual resolution is used, or it's not coarser than hardware resolution.
        # Round to the nearest physical hardware microstep.
        closest_rotation_hardware_steps = int(round(target_exact_hardware_steps))

    # 5. Calculate the actual Y-distance (arc length) achieved on the cylinder surface
    # by the `closest_rotation_hardware_steps`.
    achieved_y_on_surface = (
        closest_rotation_hardware_steps / hardware_microsteps_per_rev
    ) * circumference

    # 6. Calculate the gap.
    # This is the difference between the desired arc length and the achieved arc length.
    y_gap = y_on_surface_desired - achieved_y_on_surface

    return output_x_coord, closest_rotation_hardware_steps, y_gap


# Example Usage:
if __name__ == "__main__":
    # Setup parameters
    x_flat = 10.0  # mm
    cylinder_dia = 50.0  # mm
    y_origin_on_bed = 100.0  # mm (this Y value on bed is angle 0 for rotary)
    hw_steps = 6400  # microsteps per revolution for the rotary motor
    virtual_steps_coarse = 1000  # Coarser virtual resolution
    virtual_steps_fine = (
        8000  # Finer virtual resolution (will be ignored for coarsening)
    )

    # --- Test Case 1: Move a positive Y distance, no virtual resolution ---
    y_flat_1 = 120.0  # mm
    x_out_1, steps_out_1, gap_out_1 = map_coordinates_to_rotary(
        x_flat, y_flat_1, cylinder_dia, y_origin_on_bed, hw_steps
    )
    print(
        f"Rotary Mapping Test Cases for hw_steps={hw_steps}, center={y_origin_on_bed}"
    )
    print(f"Test Case 1 (No Virtual Resolution):")
    print(
        f"  Input Y: {y_flat_1}, Mapped Y (desired on surface): {y_flat_1 - y_origin_on_bed}"
    )
    print(
        f"  Output X: {x_out_1}, Rotary Steps: {steps_out_1}, Y Gap: {gap_out_1:.6f} mm"
    )
    print("-" * 30)

    # --- Test Case 2: Move a positive Y distance, with coarse virtual resolution ---
    y_flat_2 = 120.0  # mm
    x_out_2, steps_out_2, gap_out_2 = map_coordinates_to_rotary(
        x_flat, y_flat_2, cylinder_dia, y_origin_on_bed, hw_steps, virtual_steps_coarse
    )
    print(f"Test Case 2 (Coarse Virtual Resolution: {virtual_steps_coarse}):")
    print(
        f"  Input Y: {y_flat_2}, Mapped Y (desired on surface): {y_flat_2 - y_origin_on_bed}"
    )
    print(
        f"  Output X: {x_out_2}, Rotary Steps: {steps_out_2}, Y Gap: {gap_out_2:.6f} mm"
    )
    print("-" * 30)

    # --- Test Case 3: Move a negative Y distance, no virtual resolution ---
    y_flat_3 = 80.0  # mm
    x_out_3, steps_out_3, gap_out_3 = map_coordinates_to_rotary(
        x_flat, y_flat_3, cylinder_dia, y_origin_on_bed, hw_steps
    )
    print(f"Test Case 3 (Negative Y, No Virtual):")
    print(
        f"  Input Y: {y_flat_3}, Mapped Y (desired on surface): {y_flat_3 - y_origin_on_bed}"
    )
    print(
        f"  Output X: {x_out_3}, Rotary Steps: {steps_out_3}, Y Gap: {gap_out_3:.6f} mm"
    )
    print("-" * 30)

    # --- Test Case 4: Move a negative Y distance, with coarse virtual resolution ---
    y_flat_4 = 80.0  # mm
    x_out_4, steps_out_4, gap_out_4 = map_coordinates_to_rotary(
        x_flat, y_flat_4, cylinder_dia, y_origin_on_bed, hw_steps, virtual_steps_coarse
    )
    print(f"Test Case 4 (Negative Y, Coarse Virtual: {virtual_steps_coarse}):")
    print(
        f"  Input Y: {y_flat_4}, Mapped Y (desired on surface): {y_flat_4 - y_origin_on_bed}"
    )
    print(
        f"  Output X: {x_out_4}, Rotary Steps: {steps_out_4}, Y Gap: {gap_out_4:.6f} mm"
    )
    print("-" * 30)

    # --- Test Case 5: Zero Y displacement ---
    y_flat_5 = 100.0  # mm (same as y_origin_on_bed)
    x_out_5, steps_out_5, gap_out_5 = map_coordinates_to_rotary(
        x_flat, y_flat_5, cylinder_dia, y_origin_on_bed, hw_steps, virtual_steps_coarse
    )
    print(f"Test Case 5 (Zero Displacement, Coarse Virtual: {virtual_steps_coarse}):")
    print(
        f"  Input Y: {y_flat_5}, Mapped Y (desired on surface): {y_flat_5 - y_origin_on_bed}"
    )
    print(
        f"  Output X: {x_out_5}, Rotary Steps: {steps_out_5}, Y Gap: {gap_out_5:.6f} mm"
    )
    print("-" * 30)

    # --- Test Case 6: Virtual resolution finer than hardware (should use hardware) ---
    y_flat_6 = 120.0  # mm
    x_out_6, steps_out_6, gap_out_6 = map_coordinates_to_rotary(
        x_flat, y_flat_6, cylinder_dia, y_origin_on_bed, hw_steps, virtual_steps_fine
    )
    print(
        f"Test Case 6 (Virtual Resolution Finer ({virtual_steps_fine}), should behave as No Virtual):"
    )
    print(
        f"  Input Y: {y_flat_6}, Mapped Y (desired on surface): {y_flat_6 - y_origin_on_bed}"
    )
    print(
        f"  Output X: {x_out_6}, Rotary Steps: {steps_out_6}, Y Gap: {gap_out_6:.6f} mm"
    )
    # Compare with Test Case 1
    if steps_out_1 == steps_out_6 and abs(gap_out_1 - gap_out_6) < 1e-9:
        print("  (Matches Test Case 1 as expected)")
    else:
        print("  (Does NOT match Test Case 1, check logic)")
    print("-" * 30)

    # --- Test Case 7: Large Y displacement (more than one revolution) ---
    circumference = math.pi * cylinder_dia
    y_flat_7 = y_origin_on_bed + circumference * 1.5  # 1.5 revolutions
    x_out_7, steps_out_7, gap_out_7 = map_coordinates_to_rotary(
        x_flat, y_flat_7, cylinder_dia, y_origin_on_bed, hw_steps, virtual_steps_coarse
    )
    print(f"Test Case 7 (1.5 Revolutions, Coarse Virtual: {virtual_steps_coarse}):")
    print(f"  Desired surface travel: {circumference * 1.5:.2f} mm")
    print(
        f"  Input Y: {y_flat_7}, Mapped Y (desired on surface): {y_flat_7 - y_origin_on_bed:.2f}"
    )
    print(
        f"  Output X: {x_out_7}, Rotary Steps: {steps_out_7} (expected around {1.5 * virtual_steps_coarse * (hw_steps / virtual_steps_coarse):.0f}), Y Gap: {gap_out_7:.6f} mm"
    )
    expected_steps_approx = 1.5 * hw_steps  # rough check for no virtual
    expected_steps_virtual_approx = round((1.5 * virtual_steps_coarse)) * (
        hw_steps / virtual_steps_coarse
    )

    print(
        f"  (For comparison: 1.5 * {hw_steps} = {expected_steps_approx}, 1.5 * {virtual_steps_coarse} virtual steps ~ {round(expected_steps_virtual_approx)} hw steps )"
    )
    print("-" * 30)
