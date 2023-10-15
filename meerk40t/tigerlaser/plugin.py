"""
Tiger Device Plugin
"""

from meerk40t.tigerlaser.device import TigerDevice


def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]

    if lifecycle == "register":
        kernel.register("provider/device/tiger", TigerDevice)
        _ = kernel.translation
        kernel.register(
            "dev_info/tiger-device",
            {
                "provider": "provider/device/tiger",
                "friendly_name": _("Tiger Example Laser"),
                "extended_info": _(
                    "Laser does nothing except says 'home!' when you home."
                ),
                "priority": 0,
                "family": _("Dummy Laser"),
                "family_priority": 9,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Tiger",
                    },
                ],
            },
        )
    if lifecycle == "preboot":
        suffix = "tiger"
        for d in kernel.derivable(suffix):
            kernel.root(f"service device start -p {d} {suffix}\n")
