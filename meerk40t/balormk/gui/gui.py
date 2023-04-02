def plugin(service, lifecycle):
    if lifecycle == "service":
        return "provider/device/balor"
    if lifecycle == "invalidate":
        return not service.has_feature("wx")
    if lifecycle == "added":
        # Needed to test wx import.
        import wx  # pylint: disable=unused-import

        from meerk40t.gui.icons import (
            icons8_center_of_gravity_50,
            icons8_computer_support_50,
            icons8_connected_50,
            icons8_flash_off_50,
            icons8_light_off_50,
            icons8_light_on_50,
            icons8_quick_mode_on_50,
        )

        from .balorconfig import BalorConfiguration
        from .balorcontroller import BalorController
        from .baloroperationproperties import BalorOperationPanel

        service.register("window/Controller", BalorController)
        service.register("window/Configuration", BalorConfiguration)

        service.register("winpath/Controller", service)
        service.register("winpath/Configuration", service)

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
            "button/device/Configuration",
            {
                "label": _("Config"),
                "icon": icons8_computer_support_50,
                "tip": _("Opens device-specific configuration window"),
                "action": lambda v: service("window toggle Configuration\n"),
            },
        )

        service.register("property/RasterOpNode/Balor", BalorOperationPanel)
        service.register("property/CutOpNode/Balor", BalorOperationPanel)
        service.register("property/EngraveOpNode/Balor", BalorOperationPanel)
        service.register("property/ImageOpNode/Balor", BalorOperationPanel)
        service.register("property/DotsOpNode/Balor", BalorOperationPanel)
        service.register("property/HatchOpNode/Balor", BalorOperationPanel)
        service.register(
            "button/control/Light_On",
            {
                "label": _("Galvo Light"),
                "icon": icons8_light_on_50,
                "tip": _("Runs outline on selection"),
                "identifier": "light_default",
                "multi": [
                    {
                        "identifier": "live",
                        "label": _("Live Bounds"),
                        "action": lambda e: service("select-light\n"),
                    },
                    {
                        "identifier": "live-full",
                        "label": _("Live Full"),
                        "icon": icons8_computer_support_50,
                        "action": lambda e: service("full-light\n"),
                    },
                    {
                        "identifier": "hull",
                        "label": _("Trace Hull"),
                        "action": lambda e: service("element* hull light\n"),
                    },
                    {
                        "identifier": "box",
                        "label": _("Trace Bounds"),
                        "action": lambda e: service("box light\n"),
                    },
                    {
                        "identifier": "ants",
                        "label": _("Trace Ants"),
                        "action": lambda e: service("element* ants light\n"),
                    },
                    {
                        "identifier": "full",
                        "label": _("Trace Full"),
                        "action": lambda e: service("element* path light\n"),
                    },
                ],
                "toggle": {
                    "label": _("Stop Tracing..."),
                    "icon": icons8_light_off_50,
                    "tip": _("Turn light off"),
                    "action": lambda v: service("stop\n"),
                    "signal": "light_simulate",
                },
            },
        )
        service.register(
            "button/control/Redlight",
            {
                "label": _("Red Dot On"),
                "icon": icons8_quick_mode_on_50,
                "tip": _("Turn Redlight On"),
                "action": lambda v: service("red on\n"),
                "toggle": {
                    "label": _("Red Dot Off"),
                    "action": lambda v: service("red off\n"),
                    "icon": icons8_flash_off_50,
                },
            },
        )
        service.register(
            "button/control/Center",
            {
                "label": _("Center"),
                "icon": icons8_center_of_gravity_50,
                "tip": _("Center selection on laserbed"),
                "action": lambda v: service("align bed group xy center center\n"),
            },
        )

        service.add_service_delegate(BalorGui(service))


class BalorGui:
    # Class stub.
    def __init__(self, context):
        self.context = context
