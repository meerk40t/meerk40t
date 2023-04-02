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
        kernel.register(
            "dev_info/moshi-co2",
            {
                "provider": "provider/device/moshi",
                "friendly_name": _("CO2-Laser (Moshi-Board)"),
                "extended_info": _(
                    "Moshiboards MS10105 (V.4.XX) were popular around 2013, these communicate over USB via a CH341 Universal Interface Chip (same chip as M2-Nano). The boards are usually read and sport two large black heatsinks for their stepper motor chips."
                ),
                "priority": 0,
                "family": _("CO2-Laser"),
                "family_priority": 99,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Moshiboard",
                    },
                ],
            },
        )
    if lifecycle == "preboot":
        suffix = "moshi"
        for d in kernel.derivable(suffix):
            kernel.root(f"service device start -p {d} {suffix}\n")
