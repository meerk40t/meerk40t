


def plugin(service, lifecycle):
    if lifecycle == "service":
        return "provider/device/newly"
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

        from .newlycontroller import NewlyController
        from .newlyconfig import NewlyConfiguration
        from .operationproperties import NewlyOperationPanel

        service.register("window/Controller", NewlyController)
        service.register("window/Configuration", NewlyConfiguration)

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

        service.register("property/RasterOpNode/Newly", NewlyOperationPanel)
        service.register("property/CutOpNode/Newly", NewlyOperationPanel)
        service.register("property/EngraveOpNode/Newly", NewlyOperationPanel)
        service.register("property/ImageOpNode/Newly", NewlyOperationPanel)
        # service.register("property/DotsOpNode/Newly", NewlyOperationPanel)
        service.register("property/HatchOpNode/Newly", NewlyOperationPanel)

        service.add_service_delegate(NewlyGui(service))


class NewlyGui:
    # Class stub.
    def __init__(self, context):
        self.context = context
