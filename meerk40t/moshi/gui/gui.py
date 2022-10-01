from meerk40t.kernel import signal_listener


def plugin(service, lifecycle):
    if lifecycle == "invalidate":
        return not service.has_feature("wx")
    if lifecycle == "service":
        return "provider/device/moshi"
    if lifecycle == "added":
        from meerk40t.gui.icons import (
            icons8_computer_support_50,
            icons8_connected_50,
            icons8_emergency_stop_button_50,
            icons8_pause_50,
        )
        from meerk40t.moshi.gui.moshicontrollergui import MoshiControllerGui
        from meerk40t.moshi.gui.moshidrivergui import MoshiDriverGui

        service.register("window/Controller", MoshiControllerGui)
        service.register("window/Configuration", MoshiDriverGui)

        service.register("winpath/Controller", service)
        service.register("winpath/Configuration", service)

        _ = service._

        service.register(
            "button/control/Controller",
            {
                "label": _("Controller"),
                "icon": icons8_connected_50,
                "tip": _("Opens Controller Window"),
                "action": lambda e: service("window toggle Controller\n"),
            },
        )
        service.register(
            "button/device/Configuration",
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
                "icon": icons8_emergency_stop_button_50,
                "tip": _("Pause the laser"),
                "action": lambda v: service("pause\n"),
            },
        )

        service.register(
            "button/control/Stop",
            {
                "label": _("Stop"),
                "icon": icons8_pause_50,
                "tip": _("Emergency stop the laser"),
                "action": lambda v: service("estop\n"),
            },
        )
        service.add_service_delegate(MoshiGui(service))

    if lifecycle == "assigned":
        service("window toggle Configuration\n")


class MoshiGui:
    def __init__(self, context):
        self.context = context

    @signal_listener("controller")
    def on_controller(self, origin, original_origin, *args):
        self.context("window open Controller\n")
