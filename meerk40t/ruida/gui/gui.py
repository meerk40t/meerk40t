def plugin(service, lifecycle):
    if lifecycle == "invalidate":
        return not service.has_feature("wx")
    if lifecycle == "service":
        return "provider/device/ruida"
    if lifecycle == "added":
        import wx

        from meerk40t.gui.icons import (
            icons8_computer_support,
            icons8_connected,
            icons8_info,
        )

        _ = service._

        service.register(
            "button/control/Controller",
            {
                "label": _("Controller"),
                "icon": icons8_connected,
                "tip": _("Opens Controller Window"),
                "action": lambda e: service("window toggle Controller\n"),
            },
        )
        kernel = service.kernel
        if not (hasattr(kernel.args, "lock_device_config") and kernel.args.lock_device_config):
            service.register(
                "button/device/Configuration",
                {
                    "label": _("Config"),
                    "icon": icons8_computer_support,
                    "tip": _("Opens device-specific configuration window"),
                    "action": lambda v: service("window toggle Configuration\n"),
                },
            )

        service.register(
            "button/control/FocusZ",
            {
                "label": _("Focus Z"),
                "icon": icons8_info,
                "tip": _("Send a Ruida FocusZ command"),
                "help": "deviceruida",
                "action": lambda v: service("focusz\n"),
            },
        )

        from meerk40t.ruida.gui.ruidaconfig import RuidaConfiguration
        from meerk40t.ruida.gui.ruidacontroller import RuidaController
        # from meerk40t.ruida.gui.ruidaoperationproperties import RuidaOperationPanel

        service.register("window/Controller", RuidaController)
        service.register("window/Configuration", RuidaConfiguration)

        service.register("winpath/Controller", service)
        service.register("winpath/Configuration", service)

        # service.register("property/RasterOpNode/Ruida", RuidaOperationPanel)
        # service.register("property/CutOpNode/Ruida", RuidaOperationPanel)
        # service.register("property/EngraveOpNode/Ruida", RuidaOperationPanel)
        # service.register("property/ImageOpNode/Ruida", RuidaOperationPanel)
        # service.register("property/DotsOpNode/Ruida", RuidaOperationPanel)

        service.add_service_delegate(RuidaGui(service))


class RuidaGui:
    def __init__(self, context):
        self.context = context
        # This is a stub.
