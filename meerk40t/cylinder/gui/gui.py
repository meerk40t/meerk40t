def plugin(service, lifecycle):
    if lifecycle == "cli":
        service.set_feature("cylinder")
    if lifecycle == "invalidate":
        return not service.has_feature("wx")
    if lifecycle == "service":
        # Responding to "service" makes this a service plugin for the specific services created via the provider
        return ("provider/device/balor",)
    elif lifecycle == "added":
        from meerk40t.cylinder.gui.cylindersettings import CylinderSettings
        from meerk40t.gui.icons import icon_barrel_distortion

        _ = service._

        service.register("window/Cylinder", CylinderSettings)
        service.register(
            "button/device/Cylinder",
            {
                "label": _("Cylinder"),
                "icon": icon_barrel_distortion,
                "tip": _("Opens Cylinder Window"),
                "action": lambda v: service.console("window toggle Cylinder\n"),
            },
        )
