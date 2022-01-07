from meerk40t.gui.icons import icons8_roll_50
from meerk40t.rotary.gui.rotarysettings import RotarySettings

try:
    import wx
except ImportError as e:
    from meerk40t.core.exceptions import Mk40tImportAbort

    raise Mk40tImportAbort("wxpython")


def plugin(kernel, lifecycle):
    # if lifecycle == "service":
    #     return "provider/camera/mk"
    if lifecycle == "register":
        _ = kernel.translation
        kernel.register("window/Rotary", RotarySettings)
        kernel.register(
            "button/config/Rotary",
            {
                "label": _("Rotary"),
                "icon": icons8_roll_50,
                "tip": _("Opens Rotary Window"),
                "action": lambda v: kernel.console(
                    "window toggle Rotary\n"
                ),
            },
        )
