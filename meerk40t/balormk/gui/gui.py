from meerk40t.gui.icons import (
    icons8_computer_support_50,
    icons8_connected_50,
    icons8_emergency_stop_button_50,
    icons8_light_off_50,
    icons8_light_on_50,
    icons8_pause_50,
)
from meerk40t.kernel import signal_listener
from .balorcontroller import BalorController
from .balorconfig import BalorConfiguration
from .baloroperationproperties import BalorOperationPanel

try:
    import wx
except ImportError as e:
    from meerk40t.core.exceptions import Mk40tImportAbort

    raise Mk40tImportAbort("wxpython")


def plugin(service, lifecycle):
    if lifecycle == "service":
        return "provider/device/balor"

    if lifecycle == "added":
        service.register("window/Controller", BalorController)
        service.register("window/Configuration", BalorConfiguration)
        _ = service.kernel.translation

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
            "button/config/Configuration",
            {
                "label": _("Config"),
                "icon": icons8_computer_support_50,
                "tip": _("Opens device-specific configuration window"),
                "action": lambda v: service("window toggle Configuration\n"),
            },
        )

        def light_click(index=None):
            def light_program(event=None):
                service.setting(int, "light_default", 0)
                if index is not None:
                    service.light_default = index
                v = service.light_default
                if v == 0:
                    service("element* hull light loop\n")
                if v == 1:
                    service("box light loop\n")
                if v == 2:
                    service("element* ants light loop\n")
                if v == 3:
                    service("element* light loop\n")
                if v == 4:
                    service("element* light --speed loop\n")

            return light_program

        service.register("operationproperty/Balor", BalorOperationPanel)
        service.register(
            "button/control/Light_On",
            {
                "label": _("Galvo Light"),
                "icon": icons8_light_on_50,
                "tip": _("Runs outline on selection"),
                "action": light_click(),
                "alt-action": (
                    (_("Hull"), light_click(0)),
                    (_("Box"), light_click(1)),
                    (_("Ants"), light_click(2)),
                    (_("Full"), light_click(3)),
                    (_("Simulate"), light_click(4)),
                ),
            },
        )
        service.register(
            "button/control/Light_Off",
            {
                "label": _("No Galvo Light"),
                "icon": icons8_light_off_50,
                "tip": _("Turn light off"),
                "action": lambda v: service("stop\n"),
            },
        )
        service.add_service_delegate(BalorGui(service))


class BalorGui:
    # Class stub.
    def __init__(self, context):
        self.context = context
