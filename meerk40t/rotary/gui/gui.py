ROTARY_VIEW = False


def plugin(rotary, lifecycle):
    if lifecycle == "invalidate":
        return not rotary.has_feature("wx")
    elif lifecycle == "module":
        # Responding to "module" makes this a module plugin for the specific module replied.
        return "module/Rotary"
    elif lifecycle == "module_open":
        context = rotary.context

        from meerk40t.gui.icons import icon_rotary
        from meerk40t.rotary.gui.rotarysettings import RotarySettings

        _ = context._

        context.register("window/Rotary", RotarySettings)
        context.register(
            "button/device/Rotary",
            {
                "label": _("Rotary"),
                "icon": icon_rotary,
                "tip": _("Opens Rotary Window"),
                "action": lambda v: context("window toggle Rotary\n"),
            },
        )

        @context.console_command("rotaryview", help=_("Rotary View of Scene"))
        def toggle_rotary_view(*args, **kwargs):
            """
            Rotary Stretch/Unstretch of Scene based on values in rotary service
            """
            global ROTARY_VIEW
            if ROTARY_VIEW:
                context(f"scene aspect {rotary.scale_x} {rotary.scale_y}\n")
            else:
                try:
                    context(
                        f"scene aspect {1.0 / rotary.scale_x} {1.0 / rotary.scale_y}\n"
                    )
                except ZeroDivisionError:
                    pass
            ROTARY_VIEW = not ROTARY_VIEW

    elif lifecycle == "module_close":
        context = rotary.context
        context.unregister("window/Rotary")
        context.unregister("button/device/Rotary")
    elif lifecycle == "shutdown":
        pass
