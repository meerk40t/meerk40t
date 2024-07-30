ROTARY_VIEW = False


def plugin(service, lifecycle):
    if lifecycle == "cli":
        service.set_feature("rotary")
    if lifecycle == "invalidate":
        return not service.has_feature("wx")
    if lifecycle == "service":
        # Responding to "service" makes this a service plugin for the specific services created via the provider
        # We are only a provider of lhystudios devices for now.
        return (
            "provider/device/lhystudios",
            "provider/device/grbl",
            "provider/device/balor",
            "provider/device/newly",
            "provider/device/moshi",
        )
    elif lifecycle == "added":
        from meerk40t.gui.icons import icon_rotary
        from meerk40t.rotary.gui.rotarysettings import RotarySettings

        _ = service._

        service.register("window/Rotary", RotarySettings)
        service.register(
            "button/device/Rotary",
            {
                "label": _("Rotary"),
                "icon": icon_rotary,
                "tip": _("Opens Rotary Window"),
                "action": lambda v: service.console("window toggle Rotary\n"),
            },
        )

        @service.console_command("rotaryview", help=_("Rotary View of Scene"))
        def toggle_rotary_view(*args, **kwargs):
            """
            Rotary Stretch/Unstretch of Scene based on values in rotary service
            """
            global ROTARY_VIEW
            rotary = service.rotary
            if ROTARY_VIEW:
                rotary(f"scene aspect {rotary.scale_x} {rotary.scale_y}\n")
            else:
                try:
                    rotary(
                        f"scene aspect {1.0 / rotary.scale_x} {1.0 / rotary.scale_y}\n"
                    )
                except ZeroDivisionError:
                    pass
            ROTARY_VIEW = not ROTARY_VIEW
