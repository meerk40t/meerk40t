"""
Moshi Device Plugin

Registers the needed classes for the moshi device.
"""

from meerk40t.moshi.device import MoshiDevice


def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]

    if lifecycle == "register":
        kernel.register("provider/device/moshi", MoshiDevice)
        _ = kernel.translation
        kernel.register_friendly_name("provider/device/moshi", _("CO2-Laser (Moshi-Board)"))
    if lifecycle == "preboot":
        suffix = "moshi"
        for d in kernel.derivable(suffix):
            kernel.root(f"service device start -p {d} {suffix}\n")
