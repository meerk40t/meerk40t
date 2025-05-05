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
            # {
            #     "attr": "axis",
            #     "object": rotary,
            #     "default": 1,
            #     "type": int,
            #     "label": _("Rotary Axis:"),
            #     "tip": _("Which axis does the rotary use?"),
            # },
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
            {
                "attr": "rotary_flip_x",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mirror X"),
                "tip": _("Mirror the elements on the X-Axis"),
                "conditional": (self, "active"),
                "subsection": _("Mirror Output"),
            },
            {
                "attr": "rotary_flip_y",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mirror Y"),
                "tip": _("Mirror the elements on the Y-Axis"),
                "conditional": (self, "active"),
                "subsection": _("Mirror Output"),
            },
        ]
        service.register_choices("rotary_common", choices)

        def show_rotary_settings(channel):
            """
            Show the rotary settings in the console.
            """
            channel(_("Rotary Settings:"))
            if service.rotary.rotary_active_roller:
                channel(_("Roller-Mode"))
                channel(f"  Scale X: {service.rotary.rotary_scale_x:.3f}")
                channel(f"  Scale Y: {service.rotary.rotary_scale_y:.3f}")
                channel(f"  Flip X: {'Yes' if service.rotary.rotary_flip_x else 'No'}")
                channel(f"  Flip Y: {'Yes' if service.rotary.rotary_flip_y else 'No'}")
                channel(
                    f"  Suppress Home: {'Yes' if service.rotary.suppress_home else 'No'}"
                )
            if service.rotary.rotary_active_roller:
                channel(_("Chuck-Mode"))
                channel(
                    f"  Microsteps per revolution: {service.rotary.rotary_microsteps_per_revolution}"
                )
                channel(
                    f"  Object Diameter: {Length(service.object_diameter).length_mm}"
                )
                channel(f"  Flip X: {'Yes' if service.rotary.rotary_flip_x else 'No'}")
                channel(f"  Flip Y: {'Yes' if service.rotary.rotary_flip_y else 'No'}")
                channel(
                    f"  Suppress Home: {'Yes' if service.rotary.suppress_home else 'No'}"
                )

        @service.console_command(
            "rotary",
            help=_("Rotary base command"),
            output_type="rotary",
        )
        def rotary(command, channel, _, data=None, **kwargs):
            if command.lower() == "off":
                service.rotary.rotary_active_roller = False
                service.rotary.rotary_active_chuck = False
                channel(_("Rotary mode deactivated."))
                service.device.realize()
                return "rotary", None
            if command.lower() == "roller":
                service.rotary.rotary_active_roller = True
                service.rotary.rotary_active_chuck = False
                channel(_("Roller mode activated."))
                service.device.realize()
                return "rotary", None
            if command.lower() == "chuck":
                service.rotary.rotary_active_roller = False
                service.rotary.rotary_active_chuck = True
                channel(_("Chuck mode activated."))
                service.device.realize()
                return "rotary", None
            if command.lower() == "settings":
                show_rotary_settings(channel)
                return "rotary", None
            channel(_("Invalid command. Use 'off', 'roller', 'chuck', or 'settings'."))
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
