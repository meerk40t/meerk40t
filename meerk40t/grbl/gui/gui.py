from meerk40t.gui.icons import icons8_info_50


def plugin(service, lifecycle):
    if lifecycle == "invalidate":
        try:
            import serial  # pylint: disable=unused-import
        except ImportError:
            return True
        return not service.has_feature("wx")
    if lifecycle == "service":
        return "provider/device/grbl"
    if lifecycle == "added":
        from meerk40t.grbl.gui.grblconfiguration import GRBLConfiguration
        from meerk40t.grbl.gui.grblserialcontroller import SerialController
        from meerk40t.gui.icons import (
            icons8_computer_support_50,
            icons8_connected_50,
            icons8_emergency_stop_button_50,
            icons8_pause_50,
        )

        service.register("window/Serial-Controller", SerialController)
        service.register("window/Configuration", GRBLConfiguration)

        service.register("winpath/Serial-Controller", service)
        service.register("winpath/Configuration", service)

        _ = service._

        service.register(
            "button/control/Controller",
            {
                "label": _("Serial Controller"),
                "icon": icons8_connected_50,
                "tip": _("Opens GRBL Serial Sender"),
                "action": lambda e: service("window toggle Serial-Controller\n"),
            },
        )
        service.register(
            "button/config/Configuration",
            {
                "label": _("Config"),
                "icon": icons8_computer_support_50,
                "tip": _("Opens device-specfic configuration window"),
                "action": lambda v: service("window toggle Configuration\n"),
            },
        )
        service.register(
            "button/control/Pause",
            {
                "label": _("Pause"),
                "icon": icons8_pause_50,
                "tip": _("Pause the laser"),
                "action": lambda v: service("pause\n"),
            },
        )

        service.register(
            "button/control/Stop",
            {
                "label": _("Stop"),
                "icon": icons8_emergency_stop_button_50,
                "tip": _("Emergency stop the laser"),
                "action": lambda v: service("estop\n"),
            },
        )

        service.register(
            "button/control/ClearAlarm",
            {
                "label": _("Clear Alarm"),
                "icon": icons8_info_50,
                "tip": _("Send a GRBL Clear Alarm command"),
                "action": lambda v: service("clear_alarm\n"),
            },
        )
        service.add_service_delegate(GRBLGui(service))


class GRBLGui:
    def __init__(self, context):
        self.context = context
        # This is a stub.
