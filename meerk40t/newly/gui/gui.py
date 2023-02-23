
def plugin(service, lifecycle):
    if lifecycle == "service":
        return "provider/device/newly"
    if lifecycle == "invalidate":
        return not service.has_feature("wx")
    if lifecycle == "added":
        # Needed to test wx import.
        import wx  # pylint: disable=unused-import

        from meerk40t.gui.icons import (
            icons8_computer_support_50,
            icons8_connected_50,
            icons8_move_50,
            icons8_rectangular_50,
            icons8_play_50
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
        service.register("property/DotsOpNode/Newly", NewlyOperationPanel)
        service.register("property/HatchOpNode/Newly", NewlyOperationPanel)

        service.register(
            "button/control/DrawFrame",
            {
                "label": _("Draw Frame"),
                "icon": icons8_rectangular_50,
                "tip": _("Draw a bounding rectangle of the object saved in the machine"),
                "action": lambda v: service("draw_frame 1\n"),
            },
        )
        service.register(
            "button/control/MoveFrame",
            {
                "label": _("Move Frame"),
                "icon": icons8_move_50,
                "tip": _("Move the bounding rectangle of the object saved in the machine"),
                "action": lambda v: service("move_frame 1\n"),
            },
        )
        service.register(
            "button/control/Replay",
            {
                "label": _("Replay"),
                "icon": icons8_play_50,
                "tip": _("Replay the file saved in the machine"),
                "action": lambda v: service("replay 1\n"),
            },
        )
        service.add_service_delegate(NewlyGui(service))


class NewlyGui:
    # Class stub.
    def __init__(self, context):
        self.context = context
