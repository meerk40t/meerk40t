def plugin(service, lifecycle):
    if lifecycle == "invalidate":
        try:
            import serial  # pylint: disable=unused-import
        except ImportError:
            return True
        return not service.has_feature("wx")
    if lifecycle == "service":
        return "provider/device/grbl"

    if lifecycle == "assigned":
        service("window toggle Configuration\n")

    if lifecycle == "added":
        from meerk40t.grbl.gui.grblconfiguration import GRBLConfiguration
        from meerk40t.grbl.gui.grblcontroller import GRBLController
        from meerk40t.grbl.gui.grblhardwareconfig import GRBLHardwareConfig
        from meerk40t.grbl.gui.grbloperationconfig import GRBLAdvancedPanel
        from meerk40t.gui.icons import (
            icons8_computer_support,
            icons8_connected,
            icons8_emergency_stop_button,
            icons8_flash_off,
            icons8_flash_on,
            icons8_info,
            icons8_pause,
            icons8_home_filled,
        )

        service.register("window/GRBLController", GRBLController)
        service.register("winpath/GRBLController", service)

        service.register("window/Configuration", GRBLConfiguration)
        service.register("winpath/Configuration", service)

        service.register("window/GrblHardwareConfig", GRBLHardwareConfig)

        service.register("property/RasterOpNode/GRBL", GRBLAdvancedPanel)
        service.register("property/CutOpNode/GRBL", GRBLAdvancedPanel)
        service.register("property/EngraveOpNode/GRBL", GRBLAdvancedPanel)
        service.register("property/ImageOpNode/GRBL", GRBLAdvancedPanel)
        service.register("property/DotsOpNode/GRBL", GRBLAdvancedPanel)
        _ = service._

        service.register(
            "button/control/Controller",
            {
                "label": _("Controller"),
                "icon": icons8_connected,
                "tip": _("Opens Controller Window"),
                "help": "devicegrbl",
                "action": lambda v: service("window toggle GRBLController\n"),
            },
        )
        kernel = service.kernel
        if not (
            hasattr(kernel.args, "lock_device_config")
            and kernel.args.lock_device_config
        ):
            service.register(
                "button/device/Configuration",
                {
                    "label": _("Config"),
                    "icon": icons8_computer_support,
                    "tip": _("Opens device-specific configuration window"),
                    "help": "devicegrbl",
                    "action": lambda v: service("window toggle Configuration\n"),
                },
            )
        service.register(
            "button/control/Pause",
            {
                "label": _("Pause"),
                "icon": icons8_pause,
                "tip": _("Pause the laser"),
                "help": "devicegrbl",
                "action": lambda v: service("pause\n"),
            },
        )

        service.register(
            "button/control/Stop",
            {
                "label": _("Stop"),
                "icon": icons8_emergency_stop_button,
                "tip": _("Emergency stop the laser"),
                "help": "devicegrbl",
                "action": lambda v: service("estop\n"),
            },
        )

        def has_red_dot_enabled():
            # Does the current device have an active use_red_dot?
            res = False
            if hasattr(service, "use_red_dot"):
                if service.use_red_dot:
                    res = True
            return res

        service.register(
            "button/control/Redlight",
            {
                "label": _("Red Dot On"),
                "icon": icons8_flash_on,
                "tip": _("Turn Redlight On"),
                "help": "devicegrbl",
                "action": lambda v: service("red on\n"),
                "toggle": {
                    "label": _("Red Dot Off"),
                    "help": "devicegrbl",
                    "action": lambda v: service("red off\n"),
                    "icon": icons8_flash_off,
                    "signal": "grbl_red_dot",
                },
                "rule_enabled": lambda v: has_red_dot_enabled(),
            },
        )

        service.register(
            "button/control/ClearAlarm",
            {
                "label": _("Clear Alarm"),
                "icon": icons8_info,
                "tip": _("Send a GRBL Clear Alarm command"),
                "help": "devicegrbl",
                "action": lambda v: service("clear_alarm\n"),
            },
        )

        service.register(
            "button/control/GoHome",
            {
                "label": _("Home"),
                "icon": icons8_home_filled,
                "tip": _("Send laser to home position (right click: to physical home)"),
                "help": "devicegrbl",
                "action": lambda v: service("home\n"),
                "action_right": lambda v: service("physical_home\n"),
            },
        )
        service.add_service_delegate(GRBLGui(service))


class GRBLGui:
    def __init__(self, context):
        self.context = context
        # This is a stub.
