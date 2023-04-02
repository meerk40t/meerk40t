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
        )
        from .newlycontroller import NewlyController
        from .newlyconfig import NewlyConfiguration

        # from .operationproperties import NewlyOperationPanel

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

        # service.register("property/RasterOpNode/Newly", NewlyOperationPanel)
        # service.register("property/CutOpNode/Newly", NewlyOperationPanel)
        # service.register("property/EngraveOpNode/Newly", NewlyOperationPanel)
        # service.register("property/ImageOpNode/Newly", NewlyOperationPanel)
        # service.register("property/DotsOpNode/Newly", NewlyOperationPanel)
        # service.register("property/HatchOpNode/Newly", NewlyOperationPanel)

    if lifecycle == "service_attach":
        from meerk40t.gui.icons import (
            icons8_computer_support_50,
            icons8_connected_50,
            icons8_move_50,
            icons8_file_50,
            icons8_rectangular_50,
            icons8_play_50,
            icons8_circled_stop_50,
            icons8_circled_play_50,
        )

        _ = service.kernel.translation
        selected = service.setting(int, "file_index", 1)
        autoplay = service.setting(bool, "autoplay", True)
        service.register(
            "button/control/SelectFile",
            {
                "label": _("File {index}").format(index=selected),
                "icon": icons8_file_50,
                "tip": _("Select active file to use for machine."),
                "identifier": "file_index",
                "object": service,
                "priority": 1,
                "multi": [
                    {
                        "identifier": 1,
                        "label": _("File {index}").format(index=1),
                        "action": lambda v: service("select_file 1\n"),
                    },
                    {
                        "identifier": 2,
                        "label": _("File {index}").format(index=2),
                        "action": lambda v: service("select_file 2\n"),
                    },
                    {
                        "identifier": 3,
                        "label": _("File {index}").format(index=3),
                        "action": lambda v: service("select_file 3\n"),
                    },
                    {
                        "identifier": 4,
                        "label": _("File {index}").format(index=4),
                        "action": lambda v: service("select_file 4\n"),
                    },
                    {
                        "identifier": 5,
                        "label": _("File {index}").format(index=5),
                        "action": lambda v: service("select_file 5\n"),
                    },
                    {
                        "identifier": 6,
                        "label": _("File {index}").format(index=6),
                        "action": lambda v: service("select_file 6\n"),
                    },
                    {
                        "identifier": 7,
                        "label": _("File {index}").format(index=7),
                        "action": lambda v: service("select_file 7\n"),
                    },
                    {
                        "identifier": 8,
                        "label": _("File {index}").format(index=8),
                        "action": lambda v: service("select_file 8\n"),
                    },
                    {
                        "identifier": 9,
                        "label": _("File {index}").format(index=9),
                        "action": lambda v: service("select_file 9\n"),
                    },
                ],
            },
        )
        service.register(
            "button/control/AutoStart",
            {
                "label": _("Send Only"),
                "icon": icons8_circled_stop_50,
                "tip": _("Automatically start the device after send"),
                "toggle_attr": "autoplay",
                "object": service,
                "priority": 1,
                "toggle": {
                    "label": _("Send & Start"),
                    "icon": icons8_circled_play_50,
                    "signal": "autoplay",
                },
            },
        )
        service.register(
            "button/control/DrawFrame",
            {
                "label": _("Draw Frame"),
                "icon": icons8_rectangular_50,
                "tip": _(
                    "Draw a bounding rectangle of the object saved in the machine"
                ),
                "action": lambda v: service(
                    "draw_frame {index}\n".format(index=service.file_index)
                ),
                "priority": 3,
            },
        )
        service.register(
            "button/control/MoveFrame",
            {
                "label": _("Move Frame"),
                "icon": icons8_move_50,
                "tip": _(
                    "Move the bounding rectangle of the object saved in the machine"
                ),
                "action": lambda v: service(
                    "move_frame {index}\n".format(index=service.file_index)
                ),
                "priority": 4,
            },
        )
        service.register(
            "button/control/Replay",
            {
                "label": _("Replay"),
                "icon": icons8_play_50,
                "tip": _("Replay the file saved in the machine"),
                "action": lambda v: service(
                    "replay {index}\n".format(index=service.file_index)
                ),
                "priority": 5,
            },
        )
        service.add_service_delegate(NewlyGui(service))


class NewlyGui:
    # Class stub.
    def __init__(self, context):
        self.context = context
